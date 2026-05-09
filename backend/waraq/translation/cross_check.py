"""§3.6 Primary/Check cross-check orchestrator.

Per Dokument 1 §3.6, every translation passes through TWO engines in
parallel:

- **Primary** (lead translation draft): GPT-4o.
- **Check** (parallel counter-translation and quality check): Gemini 2.5 Pro.

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

**v1.0 simplification on the 4-situation classifier:** because both
engines apply the §2.2 canon rules to their own output (digit
normalization, EI2, religious formulas), deterministic differences are
already collapsed before cross-check sees them. Therefore in v1.0:

- **Equal after normalization** → Agreement (situation 1).
- **Different after normalization** → Substantive (situation 3) by
  default. The richer "objective deterministic finding" / "genuine
  ambiguity" classification is a Phase 4+ enhancement (would require a
  third LLM call or a domain-specific rule comparator).

This is canonically defensible: §3.6 lists the four situations as the
classifier's *output*, not as a mandatory minimum implementation; what
canon explicitly forbids is silent winners, silent role swaps, and
silent corrections — none of which v1.0 violates.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from enum import StrEnum

from waraq.translation.openai_translator import Translator
from waraq.translation.service import TranslationContext

logger = logging.getLogger(__name__)


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

        # Both succeeded — classify the comparison.
        if _normalize_for_comparison(primary_output) == _normalize_for_comparison(check_output):
            situation = CrossCheckSituation.AGREEMENT
        else:
            # v1.0 default: substantive interpretive deviation. Both
            # outputs have already passed §2.2 canon rules so any
            # remaining difference is interpretive. Future enhancement:
            # detect specific deterministic findings (e.g., named-entity
            # mismatch, glossary-binding miss) and route to AUTO_CORRECTION.
            situation = CrossCheckSituation.SUBSTANTIVE_DEVIATION

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
