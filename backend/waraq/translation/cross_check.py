"""§3.6 Primary/Check cross-check orchestrator.

Per Dokument 1 §3.6, every translation can pass through TWO engines in
parallel. The concrete Primary/Check assignment is provided by the API
router so it can follow the currently best-performing production model:

- **Primary**: lead translation draft adopted as the user-facing output.
- **Check**: parallel counter-translation and quality check.

The Check has no general silent correction right. Four situation types
apply to the comparison:

1. **Agreement**: Primary output is adopted.
2. **Objective deterministic finding**: Auto-correction enforced; logged.
3. **Substantive interpretive deviation**: no silent correction;
   confidence drops; passage marked for review.
4. **Genuine ambiguity despite cross-check**: user notice; no silent
   decision.

**No silent role swap on failure** (canonical):
- If Primary fails, Check does NOT take over the Primary role; the
  chunk waits / auto-retries.
- If Check fails, Primary output continues; the affected passages are
  considered not cross-checked and logged accordingly.

This module produces a `CrossCheckedTranslator` callable matching the
canonical `Translator` signature so it slots into the existing
translation `_execute` loop without engine-specific changes there.

**Phase 4 sub-batch G refinement of the 4-situation classifier:**

  - **Equal after normalization** → AGREEMENT.
  - **Equal after canon-rules re-pass** → AUTO_CORRECTION (objective
    deterministic finding — one engine's output collapses to the
    other's after the deterministic §2.2 canon rules are re-applied,
    so the difference is canonically attributable to one side missing
    a rule the other applied).
  - **Hedge markers / explicit-uncertainty brackets in either output**
    → AMBIGUITY (genuine interpretive uncertainty surfaces on the
    text itself; canon mandates user notice with no silent winner).
  - **Otherwise** → SUBSTANTIVE_DEVIATION.

The classifier is rules-based — no third LLM call. Hedge detection
keys off canonical German + Arabic uncertainty markers
(`möglicherweise`, `vermutlich`, `wohl`, `[unklar]`, `?`, `ggf.`,
`evtl.`); auto-correction keys off the existing `apply_canon_rules`
deterministic transformer the translators already run. Both signals
are observable from the texts themselves — canon-defensible per §3.6
"the classifier's output", and no silent winners (canon's actual
hard rule).
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from enum import StrEnum

from waraq.canon_rules import apply_all as apply_canon_rules
from waraq.translation.openai_translator import Translator
from waraq.translation.service import TranslationContext

logger = logging.getLogger(__name__)

# §3.6 hedge / ambiguity markers. Detection is **case-insensitive
# substring** match — keep markers short and unambiguous so they don't
# false-positive on innocuous prose. The German list covers the
# canonical hedges; the Arabic side covers explicit reviewer brackets
# and Q&A markers (`؟`).
_HEDGE_MARKERS_DE: tuple[str, ...] = (
    "möglicherweise",
    "vermutlich",
    "wohl ",  # trailing space — avoid matching "wohlbekannt" etc.
    "evtl.",
    "ggf.",
    "[unklar]",
    "[unsicher]",
    "[?]",
)
_HEDGE_MARKERS_AR: tuple[str, ...] = (
    "[غير واضح]",  # bracketed "unclear" reviewer mark.
    "؟",  # Arabic question mark — explicit uncertainty.
)


class CrossCheckSituation(StrEnum):
    """Per §3.6 — 'four situation types apply'."""

    AGREEMENT = "agreement"
    AUTO_CORRECTION = "auto_correction"  # Phase 4+ — not classified in v1.0
    SUBSTANTIVE_DEVIATION = "substantive_deviation"
    AMBIGUITY = "ambiguity"  # Phase 4+ — not classified in v1.0
    CHECK_FAILED = "check_failed"  # not a §3.6 situation; engineering signal


@dataclass(frozen=True, kw_only=True, slots=True)
class CrossCheckOutcome:
    """In-process result the persistence hook can read off the context.
    Carried as a transient field on `TranslationContext.cross_check`
    when the cross-check orchestrator is in use; the persistence hook
    pulls the data into the TRANSLATION-PO payload."""

    primary_output: str
    check_output: str | None
    situation: CrossCheckSituation
    primary_engine: str
    check_engine: str
    check_error: str | None  # populated on situation=CHECK_FAILED


_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_for_comparison(text: str) -> str:
    """Collapse whitespace and lowercase for the Agreement check.
    Both engines have already applied §2.2 canon rules; this comparison
    only ignores cosmetic whitespace + casing."""
    return _WHITESPACE_RE.sub(" ", text).strip().casefold()


def _has_hedge_markers(text: str) -> bool:
    """Detect §3.6 ambiguity markers (German + Arabic). The classifier
    routes texts that exhibit explicit uncertainty on EITHER engine's
    side to AMBIGUITY rather than SUBSTANTIVE_DEVIATION."""
    lower = text.casefold()
    if any(marker in lower for marker in _HEDGE_MARKERS_DE):
        return True
    return any(marker in text for marker in _HEDGE_MARKERS_AR)


def _is_auto_correction(primary_output: str, check_output: str) -> bool:
    """Detect AUTO_CORRECTION (§3.6 situation 2) — both texts collapse
    to the same form after re-applying the deterministic §2.2 canon
    rules.

    The translators already pipe their raw output through
    `apply_canon_rules` before returning, but rule passes are only
    fixed-point under specific transformation orderings; cross-engine
    drift can survive when one engine's intermediate output trips a
    rule the other already absorbed. Re-running both through the
    canon-rules pass deterministically converges any such residual
    drift — when the converged forms match, the deviation is
    canonically deterministic, not interpretive.
    """
    converged_primary = _normalize_for_comparison(apply_canon_rules(primary_output))
    converged_check = _normalize_for_comparison(apply_canon_rules(check_output))
    return converged_primary == converged_check


def _classify_situation(
    primary_output: str,
    check_output: str,
) -> CrossCheckSituation:
    """Per §3.6 — return the canonical situation type for the comparison.

    Order matters:
      1. AGREEMENT — equal after whitespace+case normalization.
      2. AUTO_CORRECTION — equal after re-applying canon rules.
      3. AMBIGUITY — either side carries explicit hedge / uncertainty
         markers (the disagreement is on the texts themselves, not
         interpretive between two confident engines).
      4. SUBSTANTIVE_DEVIATION — the residual case.
    """
    if _normalize_for_comparison(primary_output) == _normalize_for_comparison(check_output):
        return CrossCheckSituation.AGREEMENT
    if _is_auto_correction(primary_output, check_output):
        return CrossCheckSituation.AUTO_CORRECTION
    if _has_hedge_markers(primary_output) or _has_hedge_markers(check_output):
        return CrossCheckSituation.AMBIGUITY
    return CrossCheckSituation.SUBSTANTIVE_DEVIATION


def make_cross_checked_translator(
    *,
    primary: Translator,
    check: Translator,
    primary_engine_label: str = "openai/gpt-4o",
    check_engine_label: str = "google/gemini-2.5-pro",
) -> Translator:
    """Build a Translator that runs `primary` and `check` in parallel,
    applies the §3.6 cross-check logic, returns the canonical output.

    The returned translator places the `CrossCheckOutcome` on
    `context.cross_check` so the persistence hook can record both
    outputs + the situation in the TRANSLATION-PO payload. (The field
    is set via direct attribute assignment on the local context copy —
    the hook reads it; the field never serializes through checkpoints.)

    Failure semantics (canonical, §3.6):
    - Primary raises → re-raise. **No silent role swap to Check.**
      The translation `_execute` loop will fail the Job; the user can
      manually retry. Per the 30-min rule the dashboard indicator + email
      logic lives at the Job level (deferred to Phase 1 sub-batch later
      / Phase 7 deploy hardening).
    - Check raises → swallow, log, return Primary, mark situation =
      CHECK_FAILED. The passage is recorded as not-cross-checked.
    """

    async def _cross_check(source_text: str, context: TranslationContext) -> str:
        # Run both engines concurrently. `asyncio.gather` propagates the
        # first exception by default; we use return_exceptions=True so
        # we can apply the asymmetric failure semantics.
        results = await asyncio.gather(
            primary(source_text, context),
            check(source_text, context),
            return_exceptions=True,
        )
        primary_result, check_result = results

        # Primary failure → bubble up. Canon §3.6: "If the primary path
        # fails, the check path does not silently take over the primary
        # role; the chunk waits or enters a wait state with auto-retry."
        if isinstance(primary_result, BaseException):
            raise primary_result

        primary_output: str = primary_result

        # Check failure → log, return Primary, mark not-cross-checked.
        if isinstance(check_result, BaseException):
            logger.warning(
                "cross_check.check_failed",
                extra={
                    "primary_engine": primary_engine_label,
                    "check_engine": check_engine_label,
                    "error_type": type(check_result).__name__,
                    "error": str(check_result)[:200],
                },
            )
            outcome = CrossCheckOutcome(
                primary_output=primary_output,
                check_output=None,
                situation=CrossCheckSituation.CHECK_FAILED,
                primary_engine=primary_engine_label,
                check_engine=check_engine_label,
                check_error=f"{type(check_result).__name__}: {check_result!s}"[:500],
            )
            _attach_outcome(context, outcome)
            return primary_output

        check_output: str = check_result

        # Both succeeded — classify the comparison through the §3.6
        # 4-situation classifier (sub-batch G refinement).
        situation = _classify_situation(primary_output, check_output)

        outcome = CrossCheckOutcome(
            primary_output=primary_output,
            check_output=check_output,
            situation=situation,
            primary_engine=primary_engine_label,
            check_engine=check_engine_label,
            check_error=None,
        )
        _attach_outcome(context, outcome)
        # Per §3.6: "Agreement: Primary output is adopted." On
        # disagreement: confidence drops, passage marked for review,
        # but the user-facing output is still the Primary draft until
        # the user resolves the review (canon does not mandate a wait
        # on substantive disagreement; only audit/conflict gates do).
        return primary_output

    return _cross_check


def _attach_outcome(context: TranslationContext, outcome: CrossCheckOutcome) -> None:
    """Attach the cross-check outcome to the live context object so the
    persistence hook can record it. We use object.__setattr__ to bypass
    the frozen=True dataclass restriction; the field doesn't exist on
    the dataclass schema and is purely a transient inter-module signal,
    same shape as the existing `chunk_brief` field but on a per-call
    basis. Idempotent — overwrites any prior outcome on the same
    context."""
    object.__setattr__(context, "cross_check", outcome)


__all__ = [
    "CrossCheckOutcome",
    "CrossCheckSituation",
    "make_cross_checked_translator",
]
