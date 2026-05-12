"""§3.4 / §3.6 Stage-3 AI track — GPT-4o + Gemini 2.5 Pro OCR
plausibility consensus.

Per §3.4: "Stage 3 AI-based (GPT-4o + Gemini 2.5 Pro consensus; no
winner — confidence drops on disagreement → review)". This module
runs both LLMs in parallel and asks each one to validate the
Stage-2-consensus OCR text. Each engine returns a [0, 1] confidence
+ optional correction note. Disagreement collapses confidence;
agreement preserves it.

This is **OCR-side validation**, distinct from the translation-side
GPT-4o + Gemini cross-check that ships in `waraq.translation.cross_check`.
The translation cross-check operates on the AR→DE *translation*; this
module operates on the AR *OCR* output to ask "does this Arabic look
plausibly correct given the surrounding context?".

Pluggability
------------
`run_ai_consensus` accepts two `AiValidator` callables. Production
wires real OpenAI + Gemini extractors; tests pass deterministic
stubs. The default validator is `_neutral_validator` returning a
neutral 0.5 with no corrections — keeps the Stage-3 aggregator green
on hosts where neither API key is configured (canon-honest: no signal).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True, slots=True)
class AiEngineVerdict:
    """One LLM's validation result for an OCR candidate.

    Attributes:
        engine: Free-form identifier (e.g. ``"openai/gpt-4o"``,
            ``"google/gemini-2.5-pro"``). Persisted on the OCR-PO so
            audit can disambiguate.
        confidence: [0, 1] — how plausible the engine thinks the
            candidate is.
        correction_note: Optional short reason text the LLM returned
            when it found something off (e.g. "diacritic mismatch").
            Never an auto-applied correction (H-1/H-2 + §2.2 forbid).
        error_class: When the LLM call failed, the exception class
            name. `confidence` is then the neutral 0.5 fallback.
    """

    engine: str
    confidence: float
    correction_note: str | None = None
    error_class: str | None = None


@dataclass(frozen=True, kw_only=True, slots=True)
class Stage3AiResult:
    """Output of the AI consensus pass.

    Attributes:
        score: [0, 1] aggregate confidence after agreement collapse.
        agreement: One of ``"agree"`` (both engines within tolerance),
            ``"disagree"`` (gap > tolerance), ``"single_engine"``
            (only one returned), ``"no_engine"`` (neither returned).
        verdicts: Per-engine breakdown. JSON-serializable for OCR-PO
            payload.
    """

    score: float
    agreement: str
    verdicts: tuple[AiEngineVerdict, ...]


# Validator signature — `(candidate_text, context) -> verdict`. The
# `context` dict carries optional surrounding-page text + block class
# so the LLM can ground its judgement.
AiValidator = Callable[[str, dict[str, str]], Awaitable[AiEngineVerdict]]


# Disagreement tolerance in [0, 1]. Engines closer than this delta
# count as "agree"; further apart triggers the confidence collapse.
DISAGREEMENT_DELTA: float = 0.20

# Neutral signal — same convention as the rule-based / statistical
# tracks. Used when no engine returned anything usable.
NEUTRAL_SCORE: float = 0.50


async def _neutral_validator(_candidate: str, _ctx: dict[str, str]) -> AiEngineVerdict:
    """Default Stage-3 AI validator that returns a neutral signal —
    used when no real validator is configured."""
    return AiEngineVerdict(
        engine="neutral-stub",
        confidence=NEUTRAL_SCORE,
        correction_note=None,
        error_class=None,
    )


def _classify_agreement(verdicts: tuple[AiEngineVerdict, ...]) -> str:
    """Compute the `agreement` label across engine verdicts."""
    successful = tuple(v for v in verdicts if v.error_class is None)
    if len(successful) == 0:
        return "no_engine"
    if len(successful) == 1:
        return "single_engine"
    delta = abs(successful[0].confidence - successful[1].confidence)
    return "agree" if delta <= DISAGREEMENT_DELTA else "disagree"


def _aggregate_score(verdicts: tuple[AiEngineVerdict, ...], agreement: str) -> float:
    """Confidence aggregation rule (v1.0):

    - no_engine        → NEUTRAL_SCORE
    - single_engine    → that engine's confidence
    - agree            → arithmetic mean
    - disagree         → mean × 0.7 (collapse-on-disagreement
                         per §3.4 "confidence drops on disagreement")
    """
    successful = [v for v in verdicts if v.error_class is None]
    if not successful:
        return NEUTRAL_SCORE
    if len(successful) == 1:
        return successful[0].confidence
    mean = sum(v.confidence for v in successful) / len(successful)
    if agreement == "disagree":
        return max(0.0, mean * 0.7)
    return mean


async def run_ai_consensus(
    *,
    candidate_text: str,
    context: dict[str, str] | None = None,
    openai_validator: AiValidator | None = None,
    gemini_validator: AiValidator | None = None,
) -> Stage3AiResult:
    """Run both Stage-3 AI validators in parallel and aggregate.

    Args:
        candidate_text: The Stage-2-consensus text to validate.
        context: Optional context fields (e.g. ``{"block_class":
            "main_text", "surrounding_text": "..."}``). Passed
            verbatim to each validator.
        openai_validator: GPT-4o validator. Defaults to a neutral stub.
        gemini_validator: Gemini 2.5 Pro validator. Defaults to a
            neutral stub.

    Empty candidate text short-circuits to ``no_engine`` — there's
    nothing to validate.
    """
    text = candidate_text.strip()
    if not text:
        return Stage3AiResult(
            score=NEUTRAL_SCORE,
            agreement="no_engine",
            verdicts=(),
        )

    ctx = context if context is not None else {}
    openai_fn = openai_validator if openai_validator is not None else _neutral_validator
    gemini_fn = gemini_validator if gemini_validator is not None else _neutral_validator

    async def _safe(fn: AiValidator, label: str) -> AiEngineVerdict:
        try:
            return await fn(text, ctx)
        except Exception as exc:
            return AiEngineVerdict(
                engine=label,
                confidence=NEUTRAL_SCORE,
                correction_note=None,
                error_class=type(exc).__name__,
            )

    verdicts_list = await asyncio.gather(
        _safe(openai_fn, "openai/gpt-4o"),
        _safe(gemini_fn, "google/gemini-2.5-pro"),
    )
    verdicts = tuple(verdicts_list)
    agreement = _classify_agreement(verdicts)
    score = _aggregate_score(verdicts, agreement)
    return Stage3AiResult(score=score, agreement=agreement, verdicts=verdicts)


__all__ = [
    "DISAGREEMENT_DELTA",
    "NEUTRAL_SCORE",
    "AiEngineVerdict",
    "AiValidator",
    "Stage3AiResult",
    "run_ai_consensus",
]
