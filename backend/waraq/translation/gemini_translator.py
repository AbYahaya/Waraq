"""Gemini-backed Translator factory for the §3.6 Check role.

Per Dokument 1 §3.6 the canonical Check model is Gemini 2.5 Pro,
parallel to the OpenAI Primary (GPT-4o). The Check pass produces a
counter-translation that the cross-check orchestrator compares to the
Primary; the Check is *not* a fallback.

Mirrors `openai_translator.py` deliberately — same `Translator`
signature, same chunk-brief injection from §3.6 chunk rules, same
post-translation canon-rule pass per §2.2. The only difference is the
backend SDK (google-genai instead of openai).

Async via `asyncio.to_thread` so the event loop stays free during the
Gemini call.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable

from waraq.canon_rules import apply_all as apply_canon_rules
from waraq.db.session import get_settings
from waraq.translation.service import TranslationContext

Translator = Callable[[str, TranslationContext], Awaitable[str]]


class GeminiTranslatorUnconfigured(RuntimeError):
    """`GOOGLE_AI_API_KEY` not present when a translator was requested.
    Surfaces as 503 from the cross-check translator if Check is
    requested but unavailable."""


_DEFAULT_SYSTEM_PROMPT = (
    "You translate classical Arabic Islamic texts into German. "
    "Mandatory output rules:\n"
    "- Swiss German spelling (ss not ß).\n"
    "- Western digits everywhere (0–9), never Arabic-Indic digits.\n"
    "- EI2 transliteration with Q (instead of Ḳ) and J (instead of Dj).\n"
    "- Religious formulas as Unicode glyphs ﷺ ﷻ when applicable.\n"
    "- Preserve Qurʾān citations and Hadith Isnād structure.\n"
    "Return ONLY the translated text — no commentary."
)


def make_gemini_translator(
    *,
    model: str | None = None,
    system_prompt: str | None = None,
) -> Translator:
    """Build a Gemini-backed translator.

    Reads `GOOGLE_AI_API_KEY` from settings at call time. Raises
    `GeminiTranslatorUnconfigured` if missing.
    """
    settings = get_settings()
    api_key = settings.google_ai_api_key or os.environ.get("GOOGLE_AI_API_KEY", "")
    if not api_key:
        raise GeminiTranslatorUnconfigured(
            "GOOGLE_AI_API_KEY not set; cannot build Gemini translator. Set "
            "the environment variable (or backend/.env) and restart the "
            "backend process."
        )
    chosen_model = model or settings.gemini_translation_model
    chosen_system = system_prompt or _DEFAULT_SYSTEM_PROMPT

    # Same fail-fast bounding as the OpenAI translator. Gemini's SDK
    # doesn't expose a per-call timeout cleanly, so we wrap the sync
    # call in `asyncio.wait_for` below.
    timeout_s = float(os.environ.get("GEMINI_HTTP_TIMEOUT", "60"))

    async def _translate(source_text: str, context: TranslationContext) -> str:
        # Build the system prompt with the §3.6 chunk brief and upstream
        # window, identical structure to the OpenAI translator so both
        # engines see the same instructions and context.
        prompt_blocks: list[str] = [chosen_system]

        brief = context.chunk_brief
        if brief is not None and not brief.is_empty:
            if brief.glossary_hits:
                # §4.17 first-occurrence formatting — same structure as the
                # OpenAI translator so both engines emit comparable output.
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

        if context.upstream_window:
            recent = "\n".join(f"  - {entry}" for entry in context.upstream_window[-3:])
            prompt_blocks.append(
                "RECENT TRANSLATION CONTEXT (last 3 segments, for stylistic continuity):\n" + recent
            )

        full_system_prompt = "\n\n".join(prompt_blocks)

        # Gemini's Generate Content API takes a single combined input;
        # we prepend the system instructions to the user text. Lazy
        # import so the SDK isn't loaded by tests that monkeypatch.
        from google import genai

        client = genai.Client(api_key=api_key)
        combined = f"{full_system_prompt}\n\n---\n\nSOURCE:\n{source_text}"

        def _call_sync() -> str:
            response = client.models.generate_content(
                model=chosen_model,
                contents=combined,
            )
            return (response.text or "").strip()

        raw_output = await asyncio.wait_for(asyncio.to_thread(_call_sync), timeout=timeout_s)
        # Same deterministic post-translation canonization as the OpenAI
        # path — both engines converge on canonical output.
        return apply_canon_rules(raw_output)

    return _translate


__all__ = [
    "GeminiTranslatorUnconfigured",
    "Translator",
    "make_gemini_translator",
]
