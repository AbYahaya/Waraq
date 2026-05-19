"""OpenAI-backed Translator factory for HTTP-scope translation runs.

The canonical translation service (`waraq.translation.service`) is
engine-agnostic — it accepts any `Translator` callable. This module
provides the concrete OpenAI binding the M5 HTTP path needs so the UI
can drive translation end-to-end without spinning a worker.

Read-only with respect to project state — it just calls the OpenAI
chat-completions API and returns the translated string. Provenance
writing is the orchestrator's job.
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable

from waraq.canon_rules import apply_all as apply_canon_rules
from waraq.translation.service import TranslationContext
from waraq.translation.line_protocol import (
    build_tagged_translation_input,
    parse_tagged_translation_output,
    split_tagged_translation_input,
)

Translator = Callable[[str, TranslationContext], Awaitable[str]]


class OpenAITranslatorUnconfigured(RuntimeError):
    """`OPENAI_API_KEY` not present in the environment when a translator
    was requested. Surfaces as a 503 from the run endpoint so the UI can
    flag it cleanly."""


# Per Dokument 1 §2.2 the model output must follow several mandatory
# product-logic rules. We instruct the LLM to avoid violations up-front
# (defense-in-depth) and post-process every response through
# `waraq.canon_rules.apply_all` (deterministic system mechanism, the
# canonical guarantor).
_DEFAULT_SYSTEM_PROMPT = (
    "You translate classical Arabic Islamic texts into German. "
    "Mandatory output rules:\n"
    "- Swiss German spelling (ss not ß).\n"
    "- Western digits everywhere (0–9), never Arabic-Indic digits.\n"
    "- EI2 transliteration with Q (instead of Ḳ) and J (instead of Dj).\n"
    "- Religious formulas as Unicode glyphs ﷺ ﷻ when applicable.\n"
    "- Preserve Qurʾān citations and Hadith Isnād structure.\n"
    "- Standalone page numbers, folio markers, and pagination artifacts must be kept as-is.\n"
    "- Running headers and page titles should be treated as headers, not as prose.\n"
    "- Never answer with commentary such as 'cannot translate'; always return only the best text output for the input span.\n"
    "- Input lines may be prefixed with tags like [[L0001]]. You must return every tag exactly once and in order.\n"
    "- For lines that are only page numbers or pagination markers, copy the tagged line's text exactly instead of translating it.\n"
    "- If a source line is blank, return the same tag with no translated prose for that line.\n"
    "Return ONLY the translated text — no commentary."
)


def make_openai_translator(
    *,
    model: str | None = None,
    system_prompt: str | None = None,
) -> Translator:
    """Build an OpenAI-backed translator.

    Reads `OPENAI_API_KEY` from the environment at call time (not at
    module import) so test harnesses can populate it lazily. Raises
    `OpenAITranslatorUnconfigured` if the key is missing.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise OpenAITranslatorUnconfigured(
            "OPENAI_API_KEY not set; cannot build translator. Set the "
            "environment variable (or backend/.env) and restart the "
            "backend process."
        )
    # Per Dokument 1 §3.6 the canonical Primary is `gpt-4o`. The env
    # override exists for cost-sensitive test runs only.
    chosen_model = model or os.environ.get("OPENAI_TRANSLATION_MODEL", "gpt-4o")
    chosen_system = system_prompt or _DEFAULT_SYSTEM_PROMPT

    from openai import AsyncOpenAI

    # Bound the SDK so a misbehaving network surfaces fast instead of
    # silently eating minutes per chunk on connect retries. The values
    # are deliberately tight: 30s connect/read, single retry. Per-segment
    # latency dominates the synchronous translation loop, so a stuck
    # call here blocks every subsequent segment.
    timeout_s = float(os.environ.get("OPENAI_HTTP_TIMEOUT", "30"))
    max_retries = int(os.environ.get("OPENAI_MAX_RETRIES", "1"))
    protocol_attempts = max(1, int(os.environ.get("TRANSLATION_LINE_PROTOCOL_MAX_ATTEMPTS", "2")))
    batch_max_lines = max(1, int(os.environ.get("TRANSLATION_BATCH_MAX_LINES", "20")))
    batch_max_chars = max(200, int(os.environ.get("TRANSLATION_BATCH_MAX_CHARS", "2500")))
    client = AsyncOpenAI(api_key=api_key, timeout=timeout_s, max_retries=max_retries)

    async def _translate(source_text: str, context: TranslationContext) -> str:
        # Build the system prompt with the §3.6 chunk brief (glossary +
        # entity hits relevant to this chunk) and the §3.6 upstream
        # window (semantic summary).
        prompt_blocks: list[str] = [chosen_system]

        brief = context.chunk_brief
        if brief is not None and not brief.is_empty:
            if brief.glossary_hits:
                # §4.17 — annotate first-vs-subsequent so the model
                # formats first-occurrence terms with the parenthetical
                # Arabic and a brief footnote.
                lines = []
                for h in brief.glossary_hits:
                    if h.is_first_occurrence:
                        lines.append(
                            f"  - {h.surface_form} → {h.gloss}  "
                            f"[FIRST OCCURRENCE — render as: "
                            f'"{h.gloss} ({h.surface_form}) '
                            f'[Anm.: brief explanation of the term]"]'
                        )
                    else:
                        lines.append(
                            f"  - {h.surface_form} → {h.gloss}  "
                            f'[subsequent occurrence — use "{h.gloss}" alone]'
                        )
                prompt_blocks.append(
                    "TERMINOLOGY (use these exact German renderings — Tier 1 "
                    "system rules per §4.12.1, glossary precedence is "
                    "mandatory):\n" + "\n".join(lines)
                )
            if brief.entity_hits:
                lines = [
                    f"  - {h.surface_form} ({h.category})"
                    + (f" — {h.short_bio[:120]}" if h.short_bio else "")
                    for h in brief.entity_hits
                ]
                prompt_blocks.append(
                    "NAMED ENTITIES (use the canonical Arabic spelling "
                    "transliterated into German per EI2):\n" + "\n".join(lines)
                )
            # §4.17 "no glossary hit" — surface untracked candidates so
            # the LLM emits the AI-footnote pattern when it judges any
            # of them to be a technical term. We cap at 16 to bound
            # the prompt budget; longer chunks naturally surface fewer
            # standalone candidates anyway.
            if brief.untracked_term_candidates:
                cands = brief.untracked_term_candidates[:16]
                lines = [f"  - {c.surface_form}" for c in cands]
                prompt_blocks.append(
                    "POTENTIAL TECHNICAL TERMS NOT IN GLOSSARY (§4.17 — "
                    "when you treat any of these as a technical term, render "
                    'on first occurrence as: "{German rendering} '
                    "({Arabic original}) [Anm.: brief explanation; "
                    'Source: AI]"; subsequent occurrences use the German '
                    "rendering alone. If a candidate is NOT a technical "
                    "term, translate normally — no footnote):\n" + "\n".join(lines)
                )

        if context.upstream_window:
            recent = "\n".join(f"  - {entry}" for entry in context.upstream_window[-3:])
            prompt_blocks.append(
                "RECENT TRANSLATION CONTEXT (last 3 segments, for stylistic continuity):\n" + recent
            )

        if context.page_context is not None:
            page_context = context.page_context
            full_source = page_context.get("full_source_text")
            block_type = page_context.get("current_block_type")
            page_index = page_context.get("page_index")
            current_idx = page_context.get("current_segment_index")
            prompt_blocks.append(
                "PAGE-LEVEL SOURCE CONTEXT (the current input is only one span from this page; "
                "use the surrounding page flow to preserve context, but translate ONLY the current input):\n"
                f"- Page index: {page_index}\n"
                f"- Current span position on page: {current_idx}\n"
                f"- Current block type: {block_type}\n"
                f"- Full page OCR text:\n{full_source}"
            )

        full_system_prompt = "\n\n".join(prompt_blocks)

        tagged = build_tagged_translation_input(source_text)
        batches = split_tagged_translation_input(
            tagged,
            max_lines=batch_max_lines,
            max_chars=batch_max_chars,
        )
        normalized_output_lines: list[str] = []
        last_exc: Exception | None = None
        for batch in batches:
            for _attempt in range(1, protocol_attempts + 1):
                try:
                    resp = await client.chat.completions.create(
                        model=chosen_model,
                        messages=[
                            {"role": "system", "content": full_system_prompt},
                            {"role": "user", "content": batch.prompt_text},
                        ],
                        temperature=0,
                    )
                    raw_output = (resp.choices[0].message.content or "").strip()
                    translated_lines = parse_tagged_translation_output(raw_output, batch)
                    normalized_output_lines.extend(
                        [
                            apply_canon_rules(line)
                            if line != source_line.source_text or source_line.kind == "text"
                            else line
                            for line, source_line in zip(translated_lines, batch.lines, strict=True)
                        ]
                    )
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
            if last_exc is not None:
                raise last_exc
        return "\n".join(normalized_output_lines)

    return _translate


__all__ = [
    "OpenAITranslatorUnconfigured",
    "Translator",
    "make_openai_translator",
]
