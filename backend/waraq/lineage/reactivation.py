"""T-4.2.2 — Reactivation of inactive UUIDs on re-segmentation.

Per Sprint 1 §2: "before any new UUID issuance, the LINEAGE service queries
inactive UUIDs in scope and reactivates (`active = false → true`) when
re-segmentation produces a Segment that plausibly matches a previously
inactive one. Plausibility heuristic: text overlap above a configurable
threshold AND positional proximity within the same Block; configurable,
never hard-coded."

R-S1-04 / R-S1-02: every threshold here lives on `ReactivationConfig`; no
hard-coded constants. Calibration after Gold-Corpus tests is config change,
not code change.

The reactivation path also writes a LINEAGE_EVENT-PO via PROVENANCE-Kern with
the reactivated UUID in both `herkunft_uuid[]` and `ziel_uuid[]` so the
downstream history (Sprint 6) sees the continuity across the inactivation→
reactivation gap.
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.eventing import log_event
from waraq.provenance import create_po
from waraq.schemas import ProvenanceObject, Segment
from waraq.schemas.enums import POType, ScopeType


@dataclass(frozen=True, kw_only=True, slots=True)
class ReactivationConfig:
    """Configurable plausibility heuristic for reactivation.

    Per Sprint 1 §2 / R-S1-04: thresholds must be configurable, never hard-
    coded. Concrete calibration values are post-Gold-Corpus work; the
    canonical interface here is the threshold pair.

    Attributes:
        text_overlap_min: Minimum word-token Jaccard similarity required
            between the inactive Segment's `text_content` and the candidate
            text. Range [0.0, 1.0]; 1.0 = identical token set; 0.0 = no
            shared tokens. A reactivation match requires `>=` this value.
        position_window: Maximum absolute difference between the candidate's
            `satz_index` and the inactive Segment's `satz_index` within the
            same Block. 0 = exact same index; 1 = ±1 neighbour; etc.
    """

    text_overlap_min: float
    position_window: int

    def __post_init__(self) -> None:
        if not 0.0 <= self.text_overlap_min <= 1.0:
            raise ValueError(f"text_overlap_min must be in [0.0, 1.0]; got {self.text_overlap_min}")
        if self.position_window < 0:
            raise ValueError(f"position_window must be >= 0; got {self.position_window}")


def _jaccard_word_overlap(a: str, b: str) -> float:
    """Word-token Jaccard similarity. Case-insensitive, whitespace-split.

    Empty/no-overlap sets return 0.0. Identical sets return 1.0.
    """
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a and not tokens_b:
        return 0.0
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(tokens_a & tokens_b) / len(union)


async def find_reactivation_candidate(
    *,
    session: AsyncSession,
    block_uuid: _uuid.UUID,
    candidate_text: str,
    candidate_satz_index: int,
    config: ReactivationConfig,
) -> Segment | None:
    """Search for a previously inactive Segment in `block_uuid` that
    plausibly corresponds to the candidate.

    Returns the best-matching inactive Segment, or None. "Best" = highest
    Jaccard similarity above the threshold among all inactive Segments
    within the position window. None means: no plausible match — caller
    should issue a fresh `new_uuid()` for the candidate.

    The selection is deterministic: ties resolved by lowest `satz_index`
    distance to the candidate, then by smallest `satz_uuid` lexicographic
    order, so behavior is repeatable across restarts.
    """
    result = await session.execute(
        select(Segment).where(
            Segment.block_uuid == block_uuid,
            Segment.active.is_(False),
        )
    )
    inactive_segments = list(result.scalars())
    if not inactive_segments:
        return None

    best: tuple[float, int, str, Segment] | None = None
    for seg in inactive_segments:
        if abs(seg.satz_index - candidate_satz_index) > config.position_window:
            continue
        seg_text = seg.text_content or ""
        overlap = _jaccard_word_overlap(seg_text, candidate_text)
        if overlap < config.text_overlap_min:
            continue
        # Sort by: highest overlap (negate so max sorts first), then smallest
        # index distance, then smallest UUID for determinism.
        rank = (
            -overlap,
            abs(seg.satz_index - candidate_satz_index),
            str(seg.satz_uuid),
        )
        candidate_tuple = (rank[0], rank[1], rank[2], seg)
        if best is None or candidate_tuple < best:
            best = candidate_tuple

    return best[3] if best is not None else None


async def reactivate_segment(
    *,
    session: AsyncSession,
    segment: Segment,
) -> ProvenanceObject:
    """Flip `active = false → true` and write the LINEAGE_EVENT-PO recording
    the reactivation.

    Per Sprint 1 §2: payload references the reactivated UUID in both
    `herkunft_uuid[]` and `ziel_uuid[]` so history queries see continuity
    across the disappearance gap. `match_kind` is `"reactivation"`.

    Caller is responsible for having found the right `segment` — typically
    via `find_reactivation_candidate`. Calling this on an already-active
    segment raises (the operation is intended for the inactive-→active
    transition only).
    """
    if segment.active:
        raise ValueError(
            f"reactivate_segment expected an inactive Segment; "
            f"satz_uuid={segment.satz_uuid} is already active=True"
        )

    segment.active = True
    await session.flush()

    po = await create_po(
        session=session,
        po_type=POType.LINEAGE_EVENT,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=segment.satz_uuid,
        payload={
            "match_kind": "reactivation",
            "automatisch": True,
            "herkunft_uuid": [str(segment.satz_uuid)],
            "ziel_uuid": [str(segment.satz_uuid)],
        },
        author_uuid=None,
    )
    await log_event(
        session=session,
        operation_type="lineage_reactivation",
        scope_type=ScopeType.SEGMENT,
        scope_uuid=segment.satz_uuid,
        result={"po_uuid": str(po.po_uuid), "match_kind": "reactivation"},
    )
    return po
