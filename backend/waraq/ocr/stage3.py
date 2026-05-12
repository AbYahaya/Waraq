"""§3.4 Stage-3 — three-track consensus aggregator.

Combines four signals into a single Stage-3 confidence:

  1. Stage-2 multi-engine agreement (`waraq.ocr.consensus`)
  2. Rule-based grammar plausibility (`waraq.ocr.stage3_rules`)
  3. Statistical Shamela Mode-A plausibility
     (`waraq.ocr.stage3_statistical`)
  4. AI-based consensus from GPT-4o + Gemini 2.5 Pro
     (`waraq.ocr.stage3_ai`)

Per §3.4 "no winner — confidence drops on disagreement → review",
the aggregator never picks ONE track to overrule the others. All
four contribute. v1.0 weights:

  - Stage-2 agreement: 0.35
  - Rule-based:         0.20
  - Statistical:        0.20
  - AI consensus:       0.25

These sum to 1.0. They are deliberately documented in module
constants so an empirical recalibration in Phase 7 (Gold-Corpus) is
a one-line change. The Stage-2-agreement signal is mapped to a [0, 1]
score by `_stage2_agreement_score` below — exact_match → 1.0,
skeleton_equal → 0.85, single_engine → 0.65, divergent → 0.40,
engine_error → 0.20.

Disagreement collapse
---------------------
Per §3.4 the canonical rule is "confidence drops on disagreement".
When the Stage-2 signal is `divergent` AND any of the three other
tracks signals < 0.5, the aggregate is multiplied by 0.7 — same
collapse factor as the AI-track's internal disagreement penalty.
The collapse is canon-defensible (matching §3.6 cross-checked
translation) and not silent — `divergence_penalty_applied: True`
lands on the OCR-PO so audit can review.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.ocr.consensus import (
    AGREEMENT_DIVERGENT,
    AGREEMENT_ENGINE_ERROR,
    AGREEMENT_EXACT_MATCH,
    AGREEMENT_SINGLE_ENGINE,
    AGREEMENT_SKELETON_EQUAL,
    ConsensusResult,
)
from waraq.ocr.stage3_ai import (
    AiValidator,
    Stage3AiResult,
    run_ai_consensus,
)
from waraq.ocr.stage3_rules import (
    DiacritizerFn,
    MorphologyAnalyzableFn,
    Stage3RuleResult,
    rule_based_score,
)
from waraq.ocr.stage3_statistical import (
    Stage3StatisticalResult,
    statistical_score,
)
from waraq.schemas.enums import BlockClass

# v1.0 weights — sum to 1.0. Phase 7 gold-corpus recalibration target.
W_STAGE2: float = 0.35
W_RULES: float = 0.20
W_STATISTICAL: float = 0.20
W_AI: float = 0.25

# Disagreement collapse factor — applied to the weighted aggregate
# when Stage-2 reports `divergent` AND any other track flags low
# plausibility (< 0.5).
DIVERGENCE_COLLAPSE: float = 0.7
LOW_TRACK_THRESHOLD: float = 0.5


@dataclass(frozen=True, kw_only=True, slots=True)
class Stage3Result:
    """Final Stage-3 consensus output. Persisted on the OCR-PO payload
    via `run_ocr_job`'s `engine_breakdown` + new `stage3` payload key.

    Attributes:
        confidence: [0, 1] aggregated score.
        stage2_score: Mapped Stage-2 agreement → [0, 1].
        rule_result: Full rule-based breakdown (CAMeL + Mishkal).
        statistical_result: Full statistical breakdown (Shamela hits).
        ai_result: Full AI-consensus breakdown (GPT-4o + Gemini Pro).
        divergence_penalty_applied: True iff the disagreement collapse
            factor was applied to the aggregate.
    """

    confidence: float
    stage2_score: float
    rule_result: Stage3RuleResult
    statistical_result: Stage3StatisticalResult
    ai_result: Stage3AiResult
    divergence_penalty_applied: bool


def _stage2_agreement_score(consensus: ConsensusResult) -> float:
    """Map the Stage-2 agreement label to a [0, 1] score."""
    label = consensus.agreement
    if label == AGREEMENT_EXACT_MATCH:
        return 1.0
    if label == AGREEMENT_SKELETON_EQUAL:
        return 0.85
    if label == AGREEMENT_SINGLE_ENGINE:
        return 0.65
    if label == AGREEMENT_DIVERGENT:
        return 0.40
    if label == AGREEMENT_ENGINE_ERROR:
        return 0.20
    return 0.50


async def aggregate_stage3(
    *,
    session: AsyncSession,
    candidate_text: str,
    block_class: BlockClass,
    stage2: ConsensusResult,
    morphology_fn: MorphologyAnalyzableFn | None = None,
    diacritizer_fn: DiacritizerFn | None = None,
    openai_validator: AiValidator | None = None,
    gemini_validator: AiValidator | None = None,
) -> Stage3Result:
    """Run all three Stage-3 tracks (rule + statistical + AI) and
    combine with the Stage-2 result into a final confidence.

    Adapter callables are pluggable. Defaults use the production
    adapters (CAMeL + Mishkal + neutral AI stub); tests inject
    deterministic stubs.

    The Stage-2 ConsensusResult is required input — sub-batch C
    produces it. Stage-3 explicitly does NOT re-run Stage-2 engines.
    """
    rule_result = rule_based_score(
        candidate_text,
        morphology_fn=morphology_fn,
        diacritizer_fn=diacritizer_fn,
    )
    statistical_result = await statistical_score(
        session=session,
        candidate_text=candidate_text,
        block_class=block_class,
    )
    ai_context = {
        "block_class": block_class.value,
    }
    ai_result = await run_ai_consensus(
        candidate_text=candidate_text,
        context=ai_context,
        openai_validator=openai_validator,
        gemini_validator=gemini_validator,
    )

    stage2_score = _stage2_agreement_score(stage2)
    weighted = (
        W_STAGE2 * stage2_score
        + W_RULES * rule_result.score
        + W_STATISTICAL * statistical_result.score
        + W_AI * ai_result.score
    )

    divergence_penalty = False
    if stage2.agreement == AGREEMENT_DIVERGENT:
        any_low = (
            rule_result.score < LOW_TRACK_THRESHOLD
            or statistical_result.score < LOW_TRACK_THRESHOLD
            or ai_result.score < LOW_TRACK_THRESHOLD
        )
        if any_low:
            weighted *= DIVERGENCE_COLLAPSE
            divergence_penalty = True

    confidence = max(0.0, min(1.0, weighted))
    return Stage3Result(
        confidence=confidence,
        stage2_score=stage2_score,
        rule_result=rule_result,
        statistical_result=statistical_result,
        ai_result=ai_result,
        divergence_penalty_applied=divergence_penalty,
    )


__all__ = [
    "DIVERGENCE_COLLAPSE",
    "LOW_TRACK_THRESHOLD",
    "W_AI",
    "W_RULES",
    "W_STAGE2",
    "W_STATISTICAL",
    "Stage3Result",
    "aggregate_stage3",
]
