"""§4.16.1 — Two-tier source-orchestration: Mandatory → Extended.

Per Dokument 1 §4.16.1:

  Mandatory set (fully searched on every hadith verification run):
    - P-1: sunnah.com (API)
    - P-2: Shamela (local)
    - P-3: dorar.net

  Extended set (automatically activated when the mandatory set yields
  no robust hit; can also be triggered manually by the user at any time):
    - E-1: islamweb.net  (suspended)
    - E-2: جَامِعُ السُّنَّةِ النَّبَوِيَّة  (suspended)
    - E-3: المكتبة الوقفية  (suspended)
    - E-4: جَامِعُ الكُتُبِ التِّسْعَة  (suspended)
    - E-5: مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة  (active, special role)

Per §4.16.2:
  "As long as E-1, E-2, E-3, and E-4 are factually suspended, when the
  extended set is automatically activated, in practice exclusively
  E-5 in the described special role is effective."

This module orchestrates the two-tier flow:

1. Run the Mandatory set (caller supplies P-1/P-2/P-3 candidates).
2. If the Mandatory consensus yields no **robust hit**, OR the user
   manually triggers it, escalate to the Extended set.
3. Re-run consensus on the combined Mandatory + Extended candidates.
4. Return outcome with full provenance (which mandatory hits were
   used, which extended hits were used, why escalation triggered).

**Robust hit predicate** (calibration-deferred per §4.16.3):
  - Composite score ≥ `_ROBUST_HIT_SCORE_THRESHOLD` (v1.0 = 0.7),
    AND
  - Carriage by ≥ `_ROBUST_HIT_MIN_CARRIAGE` other mandatory sources
    (v1.0 = 1; canonically the §4.16.3 "carriage by multiple sources"
    dimension drives this — a singleton hit isn't robust).

Concrete thresholds are calibration territory; the structural shape
(score-and-carriage gate, escalation on-failure) is canonical.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from waraq.hadith.consensus import (
    ConsensusResult,
    HadithCandidateHit,
    compute_consensus,
)
from waraq.hadith.extended_sources import (
    ExtendedFetcher,
    default_extended_fetchers,
    get_extended_source,
    is_active,
)

# Robust-hit thresholds — v1.0 implementation choices, calibration-deferred.
# 0.6 chosen so that two mandatory sources agreeing on a Sahih matn with
# collection labels (composite ≈ 0.667 in the equal-weighted scoring)
# count as robust without needing the author-named-source dimension. Both
# knobs are tunable per §4.16.3 "Concrete rates ... remain open".
_ROBUST_HIT_SCORE_THRESHOLD = 0.6
_ROBUST_HIT_MIN_CARRIAGE = 1


EscalationReason = Literal[
    "no_mandatory_candidates",
    "no_robust_hit",
    "manual",
]


@dataclass(frozen=True, slots=True)
class TwoTierVerificationOutcome:
    """Result of one §4.16.1 two-tier verification pass."""

    consensus: ConsensusResult | None
    mandatory_hits: list[HadithCandidateHit]
    extended_hits: list[HadithCandidateHit]
    extended_set_triggered: bool
    extended_trigger_reason: EscalationReason | None
    extended_sources_invoked: list[str] = field(default_factory=list)


async def run_two_tier_verification(
    *,
    mandatory_hits: list[HadithCandidateHit],
    query: str,
    extended_fetchers: dict[str, ExtendedFetcher] | None = None,
    manually_trigger_extended: bool = False,
    robust_hit_score_threshold: float = _ROBUST_HIT_SCORE_THRESHOLD,
    robust_hit_min_carriage: int = _ROBUST_HIT_MIN_CARRIAGE,
) -> TwoTierVerificationOutcome:
    """§4.16.1 two-tier verification.

    Args:
        mandatory_hits: candidates from P-1/P-2/P-3. Caller is responsible
            for fetching from sunnah.com, dorar.net, and Shamela; this
            orchestrator only sequences the consensus + escalation.
        query: query string to pass to extended-source fetchers (matn
            text, citation snippet, or whatever the upstream extended
            source consumes).
        extended_fetchers: mapping `source_id → async fetcher`. When
            None, uses `default_extended_fetchers()` — which provides
            no-op fetchers for E-1..E-4 (suspended per canon) and a
            v1.0 stub for E-5 that returns no hits until the §4.16.2
            Official Live API integration ships.
        manually_trigger_extended: per §4.16.1 "can also be triggered
            manually by the user at any time" — when True, bypass the
            robust-hit predicate and run extended set unconditionally.

    The fetcher mapping pattern lets tests inject deterministic stubs
    AND lets future Official-API integrations drop in for E-5 without
    touching the orchestrator.
    """
    fetchers = extended_fetchers if extended_fetchers is not None else default_extended_fetchers()

    # Step 1 — Mandatory consensus.
    mandatory_consensus: ConsensusResult | None = None
    if mandatory_hits:
        mandatory_consensus = compute_consensus(mandatory_hits)

    # Step 2 — escalation predicate.
    triggered = False
    reason: EscalationReason | None = None
    if manually_trigger_extended:
        triggered = True
        reason = "manual"
    elif not mandatory_hits:
        triggered = True
        reason = "no_mandatory_candidates"
    elif not _is_robust_hit(
        mandatory_consensus,
        score_threshold=robust_hit_score_threshold,
        min_carriage=robust_hit_min_carriage,
    ):
        triggered = True
        reason = "no_robust_hit"

    # Step 3 — Extended fetch (only when triggered).
    extended_hits: list[HadithCandidateHit] = []
    extended_invoked: list[str] = []
    if triggered:
        for source_id, fetcher in fetchers.items():
            # Per §4.16.1 + §4.16.2: suspended sources are documented
            # but inactive — call them so the structural shape is
            # observed, but they return no hits.
            hits = await fetcher(query)
            extended_hits.extend(hits)
            if hits or is_active(source_id):
                # Record which sources we attempted (active ones AND
                # any suspended ones that surprised us with hits — for
                # audit visibility).
                extended_invoked.append(source_id)

    # Step 4 — Final consensus over combined hits. When no hits at all,
    # consensus is None.
    all_hits = mandatory_hits + extended_hits
    final_consensus = compute_consensus(all_hits) if all_hits else None

    return TwoTierVerificationOutcome(
        consensus=final_consensus,
        mandatory_hits=mandatory_hits,
        extended_hits=extended_hits,
        extended_set_triggered=triggered,
        extended_trigger_reason=reason,
        extended_sources_invoked=extended_invoked,
    )


def _is_robust_hit(
    consensus: ConsensusResult | None,
    *,
    score_threshold: float,
    min_carriage: int,
) -> bool:
    """v1.0 robust-hit predicate: composite score above threshold AND
    carriage by enough other mandatory sources.

    Both knobs are calibration-deferred; the structural shape (score-
    and-carriage AND-gate) is the §4.16.3 canon expression."""
    if consensus is None or not consensus.ranking:
        return False
    winner = consensus.ranking[0]
    return (
        winner.composite_score >= score_threshold
        and winner.dimensions.carriage_count >= min_carriage
    )


__all__ = [
    "EscalationReason",
    "TwoTierVerificationOutcome",
    "run_two_tier_verification",
]


# Re-export for ergonomic import path.
def _re_export_for_docs() -> None:
    """Marker for tooling — actual exports listed in __all__ above."""

    _ = (get_extended_source,)
