"""§4.16 — full hadith verification: orchestrator → Level-2/3 persistence.

Sub-batch I (Phase 2 closeout) wires the two halves of hadith
verification together into one canonical entry point. The pieces:

  - `waraq.hadith.orchestrator.run_two_tier_verification` runs the
    two-tier mandatory + extended consensus pass and returns a
    `TwoTierVerificationOutcome`.
  - `waraq.hadith.aggregation.run_verification_round` persists the
    Level-2 (`HadithSingleSourceResult`) + Level-3
    (`HadithAggregateResult`) rows, supersedes the prior active
    aggregate, returns a `VerificationRunOutcome`.

`run_full_hadith_verification` sequences both inside one async session
scope so the orchestrator's consensus + the persisted rows land in the
same transaction. Callers (HTTP routes, batch jobs) get a single
`FullHadithVerificationOutcome` carrying everything they need for audit
+ UI display.

Pure orchestration — no schema changes; reuses the canonical Level-2
and Level-3 tables shipped in Phase 2A.

§4.16.6 supersession + immutability: handled by the underlying
`run_verification_round`. The full-verification helper does NOT
inactivate or rewrite anything itself.
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.hadith.aggregation import VerificationRunOutcome, run_verification_round
from waraq.hadith.consensus import HadithCandidateHit
from waraq.hadith.extended_sources import ExtendedFetcher
from waraq.hadith.orchestrator import (
    TwoTierVerificationOutcome,
    run_two_tier_verification,
)


@dataclass(frozen=True, slots=True)
class FullHadithVerificationOutcome:
    """Complete output of one full hadith verification pass.

    Attributes:
        two_tier: The orchestrator's two-tier consensus output —
            mandatory_hits, extended_hits, escalation reason, etc.
        run: The DB persistence outcome — aggregate UUID, single-source
            UUIDs, superseded prior aggregate UUID. None when the
            two-tier pass produced zero candidates (no DB write
            happens — there's nothing to persist).
    """

    two_tier: TwoTierVerificationOutcome
    run: VerificationRunOutcome | None = field(default=None)


async def run_full_hadith_verification(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    satz_uuid: _uuid.UUID,
    block_uuid: _uuid.UUID,
    ocr_rev_uuid: _uuid.UUID | None,
    mandatory_hits: list[HadithCandidateHit],
    query: str,
    extended_fetchers: dict[str, ExtendedFetcher] | None = None,
    manually_trigger_extended: bool = False,
    robust_hit_score_threshold: float = 0.85,
    robust_hit_min_carriage: int = 2,
    run_uuid: str | None = None,
) -> FullHadithVerificationOutcome:
    """End-to-end §4.16 verification: two-tier consensus + persistence.

    Sequences (in one session):
      1. `run_two_tier_verification` — consensus + escalation across
         mandatory + extended sources.
      2. `run_verification_round` — persist Level-2 / Level-3 rows,
         supersede prior aggregate.

    The persistence step is skipped when the two-tier pass produced
    zero candidates total — there's nothing to write. The returned
    `FullHadithVerificationOutcome.run` is None in that case; callers
    can render "no candidates" UI without special-casing exceptions.

    Caller owns the transaction. On any DB error the caller's commit
    rolls back and neither the aggregate nor the single-source rows
    are persisted (canon §4.16.6 atomicity).
    """
    two_tier = await run_two_tier_verification(
        mandatory_hits=mandatory_hits,
        query=query,
        extended_fetchers=extended_fetchers,
        manually_trigger_extended=manually_trigger_extended,
        robust_hit_score_threshold=robust_hit_score_threshold,
        robust_hit_min_carriage=robust_hit_min_carriage,
    )

    all_hits = list(two_tier.mandatory_hits) + list(two_tier.extended_hits)
    if not all_hits:
        return FullHadithVerificationOutcome(two_tier=two_tier, run=None)

    run = await run_verification_round(
        session=session,
        project_uuid=project_uuid,
        satz_uuid=satz_uuid,
        block_uuid=block_uuid,
        ocr_rev_uuid=ocr_rev_uuid,
        candidates=all_hits,
        run_uuid=run_uuid,
    )
    return FullHadithVerificationOutcome(two_tier=two_tier, run=run)


__all__ = [
    "FullHadithVerificationOutcome",
    "run_full_hadith_verification",
]
