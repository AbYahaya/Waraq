"""Production wiring for the Stage-3 OCR-side AI validators.

Sub-batch G (sub-batch D follow-up) ships the actual GPT-4o + Gemini
2.5 Pro callables that satisfy the `AiValidator` shape declared in
`waraq.ocr.stage3_ai`. The harness in sub-batch D ran with the
neutral default; production now wires the real LLMs.

Both validators:
  - Lazy-import their SDK (so hosts without it can still import the
    module / fall back to the neutral stub).
  - Read the API key at call time from environment (`OPENAI_API_KEY`
    / `GOOGLE_AI_API_KEY` — same env vars the translation pipeline
    already uses).
  - Return a `Stage3AiValidatorUnconfigured` raise when the key is
    missing — the consensus driver wraps every validator in `_safe`
    and converts the raise into an `error_class` verdict, so the
    Stage-3 score still aggregates honestly without crashing the
    OCR job.
  - Bound the call with a short timeout (15s) so a stuck request
    doesn't pin a per-page OCR for minutes.

Prompt design
-------------
We ask the model: "rate plausibility of this Arabic OCR text in
[0, 1]; flag any specific issue". The model returns JSON we parse.
If the response can't be parsed, we record the parse error in
`correction_note` and use the neutral 0.5 — same canon-honest path
as missing-data signals elsewhere in §3.4.

The prompt is intentionally narrow + instructs JSON-only output, so
small parse-fragility risks are bounded. A future hardened version
could use OpenAI's structured-output or function-calling features;
the v1.0 path uses plain JSON to keep the contract uniform across
the two providers (Gemini's structured output API differs).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass

from waraq.ocr.stage3_ai import (
    NEUTRAL_SCORE,
    AiEngineVerdict,
    AiValidator,
)

logger = logging.getLogger(__name__)

# Wall-clock cap for one validator call. Chosen to be tight enough
# that a hung request doesn't dominate per-block OCR time, loose
# enough that GPT-4o's first-token latency on a long block fits.
_VALIDATOR_TIMEOUT_S: float = 15.0


_SYSTEM_PROMPT = (
    "You are an OCR plausibility validator for classical Arabic Islamic "
    "texts. Given an OCR candidate, judge how plausible it is as a "
    "fragment of valid classical Arabic. Output STRICT JSON, exactly: "
    '{"confidence": <float in [0, 1]>, "issue": <short string or null>}. '
    "Use confidence near 1.0 for clean, well-formed Arabic; near 0.0 for "
    "obvious garbage; near 0.5 when uncertain. The 'issue' field SHOULD be "
    "a short note when you reduce confidence (e.g., 'mid-word truncation', "
    "'unbalanced bracket', 'apparent diacritic confusion'); null when "
    "confidence is high. Never return prose outside the JSON object."
)


class Stage3AiValidatorUnconfigured(RuntimeError):
    """Raised when a production validator is built but the required API
    key is not in the environment. The consensus driver catches this
    and records `error_class` on the verdict, falling back to the
    neutral signal."""


@dataclass(frozen=True, kw_only=True, slots=True)
class _ParsedVerdict:
    confidence: float
    issue: str | None
    parse_error: str | None  # populated when JSON parse failed


def _parse_response(raw: str) -> _ParsedVerdict:
    """Parse the LLM's JSON response. Returns a neutral verdict when
    the output is malformed — never raises."""
    text = raw.strip()
    # Some models wrap JSON in ```json ... ``` fences.
    if text.startswith("```"):
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            text = text[first_brace : last_brace + 1]
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        return _ParsedVerdict(
            confidence=NEUTRAL_SCORE,
            issue=None,
            parse_error=f"json_decode_error: {exc!s}"[:200],
        )
    raw_conf = obj.get("confidence", NEUTRAL_SCORE)
    try:
        confidence = float(raw_conf)
    except (TypeError, ValueError):
        return _ParsedVerdict(
            confidence=NEUTRAL_SCORE,
            issue=None,
            parse_error=f"non_numeric_confidence: {raw_conf!r}"[:200],
        )
    confidence = max(0.0, min(1.0, confidence))
    issue = obj.get("issue")
    if issue is not None and not isinstance(issue, str):
        issue = str(issue)
    return _ParsedVerdict(
        confidence=confidence,
        issue=(issue or None),
        parse_error=None,
    )


def make_openai_ocr_validator(
    *,
    model: str | None = None,
) -> AiValidator:
    """Build a production GPT-4o OCR-plausibility validator.

    Args:
        model: Optional override; defaults to `OPENAI_OCR_VALIDATOR_MODEL`
            env var or "gpt-4o". Per §3.6 OCR consensus the canonical
            partner is `gpt-4o`.

    Raises:
        Stage3AiValidatorUnconfigured: when `OPENAI_API_KEY` is empty.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise Stage3AiValidatorUnconfigured(
            "OPENAI_API_KEY not set; cannot build production OCR validator."
        )
    chosen_model = model or os.environ.get("OPENAI_OCR_VALIDATOR_MODEL", "gpt-4o")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=api_key,
        timeout=_VALIDATOR_TIMEOUT_S,
        max_retries=int(os.environ.get("OPENAI_MAX_RETRIES", "1")),
    )

    async def _validate(candidate_text: str, ctx: dict[str, str]) -> AiEngineVerdict:
        block_hint = ctx.get("block_class", "main_text")
        user_msg = (
            f"Block class: {block_hint}\n"
            f"OCR candidate:\n{candidate_text}\n\n"
            "Return strict JSON only."
        )
        try:
            resp = await asyncio.wait_for(
                client.chat.completions.create(
                    model=chosen_model,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0,
                ),
                timeout=_VALIDATOR_TIMEOUT_S,
            )
        except Exception as exc:
            # Surface as error_class on the verdict via the consensus
            # driver's safe wrapper. We don't catch here so the safe
            # wrapper sees a clean exception; logging happens there too.
            raise exc
        raw = (resp.choices[0].message.content or "").strip()
        parsed = _parse_response(raw)
        note = parsed.issue
        if parsed.parse_error is not None:
            note = parsed.parse_error
        return AiEngineVerdict(
            engine=f"openai/{chosen_model}",
            confidence=parsed.confidence,
            correction_note=note,
        )

    return _validate


def make_gemini_ocr_validator(
    *,
    model: str | None = None,
) -> AiValidator:
    """Build a production Gemini 2.5 Pro OCR-plausibility validator.

    Args:
        model: Optional override; defaults to `GEMINI_OCR_VALIDATOR_MODEL`
            env var or "gemini-2.5-pro".

    Raises:
        Stage3AiValidatorUnconfigured: when `GOOGLE_AI_API_KEY` is empty.
    """
    api_key = os.environ.get("GOOGLE_AI_API_KEY")
    if not api_key:
        raise Stage3AiValidatorUnconfigured(
            "GOOGLE_AI_API_KEY not set; cannot build production OCR validator."
        )
    chosen_model = model or os.environ.get("GEMINI_OCR_VALIDATOR_MODEL", "gemini-2.5-pro")

    from google import genai

    client = genai.Client(api_key=api_key)

    async def _validate(candidate_text: str, ctx: dict[str, str]) -> AiEngineVerdict:
        block_hint = ctx.get("block_class", "main_text")
        full_prompt = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"Block class: {block_hint}\n"
            f"OCR candidate:\n{candidate_text}\n\n"
            "Return strict JSON only."
        )

        def _call_sync() -> str:
            response = client.models.generate_content(
                model=chosen_model,
                contents=[full_prompt],  # type: ignore[arg-type]
            )
            return (response.text or "").strip()

        # The google-genai client is sync; offload to a thread + bound
        # the wall clock.
        raw = await asyncio.wait_for(
            asyncio.to_thread(_call_sync),
            timeout=_VALIDATOR_TIMEOUT_S,
        )
        parsed = _parse_response(raw)
        note = parsed.issue
        if parsed.parse_error is not None:
            note = parsed.parse_error
        return AiEngineVerdict(
            engine=f"google/{chosen_model}",
            confidence=parsed.confidence,
            correction_note=note,
        )

    return _validate


__all__ = [
    "Stage3AiValidatorUnconfigured",
    "make_gemini_ocr_validator",
    "make_openai_ocr_validator",
]
