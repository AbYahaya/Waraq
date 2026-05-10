"""§4.16.6 — Hadith verification run persistence.

Per §4.16.6 the four-level data model:
  - Level 1: passage anchor (block + segment + ocr-rev UUIDs)
  - Level 2: single-source readings → `HadithSingleSourceResult` rows
  - Level 3: aggregate result → one `HadithAggregateResult` per run
  - Level 4: user-decision overlay → existing `decision_event_uuid`
    pointers; no own table

This module wires Phase 2F-B's `compute_consensus` to those tables:
`run_verification_round` takes a list of `HadithCandidateHit` candidates
+ the passage anchor, runs the consensus engine, and writes:

  1. ONE `HadithAggregateResult` row carrying the chosen reference
     matn + reference vocalization + V-0/V-1/V-2 class + the full
     consensus summary in `consensus_summary` JSONB.
  2. ONE `HadithSingleSourceResult` row per input candidate, all
     pointing back at the aggregate via `aggregate_uuid`.

Re-running on the same passage (a "new verification round" per
§4.16.6) writes a fresh aggregate UUID; the prior aggregate flips to
`is_aktiv = false` AND points `superseded_by_uuid` at the new one.
Old Single-source rows stay attached to the old aggregate (immutable
per §4.9 E-10).
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.hadith.consensus import (
    ConsensusResult,
    HadithCandidateHit,
    compute_consensus,
)
from waraq.identity import new_uuid
from waraq.schemas import HadithAggregateResult, HadithSingleSourceResult


@dataclass(frozen=True, slots=True)
class VerificationRunOutcome:
    """The DB-side result of one `run_verification_round` call."""

    aggregate_uuid: _uuid.UUID
    consensus: ConsensusResult
    single_source_uuids: list[_uuid.UUID]
    superseded_aggregate_uuid: _uuid.UUID | None


async def run_verification_round(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    satz_uuid: _uuid.UUID,
    block_uuid: _uuid.UUID,
    ocr_rev_uuid: _uuid.UUID | None,
    candidates: list[HadithCandidateHit],
    run_uuid: str | None = None,
) -> VerificationRunOutcome:
    """Run consensus on `candidates`, persist results, supersede priors.

    Args:
        candidates: at least one. Empty list raises (consensus engine
            already raises ValueError).
        run_uuid: optional caller-supplied tag. When None, a fresh
            UUID string is generated. Stored on the aggregate row as
            `run_uuid` for cross-run comparisons.
    """
    consensus = compute_consensus(candidates)
    run_id = run_uuid or str(new_uuid())

    # §4.16.6 supersession: a new verification round on the same
    # passage flips the prior active aggregate to is_aktiv=false AND
    # points its superseded_by_uuid at the new aggregate. Old Level-2
    # rows stay attached to the old aggregate (immutable).
    prior_aggregate = (
        await session.execute(
            select(HadithAggregateResult)
            .where(HadithAggregateResult.satz_uuid == satz_uuid)
            .where(HadithAggregateResult.is_aktiv.is_(True))
        )
    ).scalar_one_or_none()
    superseded_uuid: _uuid.UUID | None = None
    if prior_aggregate is not None:
        superseded_uuid = prior_aggregate.aggregate_uuid

    aggregate = HadithAggregateResult(
        aggregate_uuid=new_uuid(),
        satz_uuid=satz_uuid,
        block_uuid=block_uuid,
        ocr_rev_uuid=ocr_rev_uuid,
        project_uuid=project_uuid,
        run_uuid=run_id,
        reference_matn=consensus.reference_matn,
        reference_matn_source_uuid=None,  # Set below after writing single-sources.
        reference_vocalization=consensus.reference_vocalization,
        reference_vocalization_source_uuid=None,
        vokalisierungsklasse=consensus.vokalisierungsklasse.value,
        vokalisierungs_konflikt=consensus.vokalisierungs_konflikt,
        consensus_summary=consensus.consensus_summary,
        is_aktiv=True,
        superseded_by_uuid=None,
    )
    session.add(aggregate)
    await session.flush()

    # Write Level-2 Single-source rows; record the chosen-source UUIDs
    # for the aggregate's reference_matn_source_uuid /
    # reference_vocalization_source_uuid.
    single_source_uuids: list[_uuid.UUID] = []
    matn_winner_uuid: _uuid.UUID | None = None
    voc_winner_uuid: _uuid.UUID | None = None
    for idx, candidate in enumerate(candidates):
        ss_uuid = new_uuid()
        single_source_uuids.append(ss_uuid)
        session.add(
            HadithSingleSourceResult(
                single_source_uuid=ss_uuid,
                aggregate_uuid=aggregate.aggregate_uuid,
                source_name=candidate.source_name,
                quellen_rolle=candidate.quellen_rolle.value,
                matn_text=candidate.matn_arabic,
                matn_vocalized=candidate.matn_vocalized,
                raw_payload=candidate.raw_payload,
                website_uebersetzung=_extract_website_uebersetzung(candidate),
            )
        )
        if idx == consensus.reference_matn_source_index:
            matn_winner_uuid = ss_uuid
        if idx == consensus.reference_vocalization_source_index:
            voc_winner_uuid = ss_uuid

    # Patch the aggregate's reference UUIDs now that the Level-2 rows exist.
    aggregate.reference_matn_source_uuid = matn_winner_uuid
    aggregate.reference_vocalization_source_uuid = voc_winner_uuid
    await session.flush()

    # Now flip the prior aggregate (if any) to inactive + point forward.
    if prior_aggregate is not None:
        prior_aggregate.is_aktiv = False
        prior_aggregate.superseded_by_uuid = aggregate.aggregate_uuid
        await session.flush()

    return VerificationRunOutcome(
        aggregate_uuid=aggregate.aggregate_uuid,
        consensus=consensus,
        single_source_uuids=single_source_uuids,
        superseded_aggregate_uuid=superseded_uuid,
    )


def _extract_website_uebersetzung(
    candidate: HadithCandidateHit,
) -> list[dict[str, str]]:
    """§4.16.8 — pull `website_uebersetzung` from the candidate's
    `raw_payload` if present. Sources that publish parallel
    translations (sunnah.com `hadithEnglish`, etc.) carry them in
    raw payload; this collector normalizes them into the canonical
    `[{"lang": <iso>, "text": <translation>}]` shape.

    Comparison/provenance only per canon — never influences matn
    consensus or reference vocalization.
    """
    out: list[dict[str, str]] = []
    payload = candidate.raw_payload
    # sunnah.com convention: hadithEnglish.
    eng = payload.get("hadithEnglish")
    if isinstance(eng, str) and eng:
        out.append({"lang": "en", "text": eng})
    # Generic convention: payload may already have a website_uebersetzung
    # list (e.g., when the upstream source is itself an aggregator).
    raw = payload.get("website_uebersetzung")
    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict):
                lang = entry.get("lang")
                text = entry.get("text")
                if isinstance(lang, str) and isinstance(text, str) and text:
                    out.append({"lang": lang, "text": text})
    return out


__all__ = ["VerificationRunOutcome", "run_verification_round"]
