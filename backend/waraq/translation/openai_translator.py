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

from waraq.translation.service import TranslationContext

Translator = Callable[[str, TranslationContext], Awaitable[str]]


class OpenAITranslatorUnconfigured(RuntimeError):
    """`OPENAI_API_KEY` not present in the environment when a translator
    was requested. Surfaces as a 503 from the run endpoint so the UI can
    flag it cleanly."""


_DEFAULT_SYSTEM_PROMPT = (
    "You translate classical Arabic Islamic texts into German. "
    "Use Swiss German spelling (ss not ß). Preserve Qurʾān citations "
    "and Hadith Isnād structure. Return ONLY the translated text — "
    "no commentary, no transliteration."
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
    chosen_model = model or os.environ.get("OPENAI_TRANSLATION_MODEL", "gpt-4o-mini")
    chosen_system = system_prompt or _DEFAULT_SYSTEM_PROMPT

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)

    async def _translate(source_text: str, context: TranslationContext) -> str:
        _ = context  # canonical signature; engine doesn't use it for v1.0
        resp = await client.chat.completions.create(
            model=chosen_model,
            messages=[
                {"role": "system", "content": chosen_system},
                {"role": "user", "content": source_text},
            ],
            temperature=0,
        )
        return (resp.choices[0].message.content or "").strip()

    return _translate


__all__ = [
    "OpenAITranslatorUnconfigured",
    "Translator",
    "make_openai_translator",
]
