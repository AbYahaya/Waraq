"""T-9.2.1 — `revision_snapshot[]` and `active_decision_event_uuids[]`
filling rules per Sprint 5 §2.

Per OCR Text Export Endfassung v1.3 §3 analog: the EXPORT_EVENT is a
snapshot of the work's effective state at job start. Two arrays carry
the snapshot:

1. `revision_snapshot[]` — the `current_rev_uuid` of every active
   in-scope Segment at job start. Read from `segments.current_rev_uuid`,
   NOT from the `revisions` table. Inactive Segments excluded.
   Out-of-scope Segments excluded.

2. `active_decision_event_uuids[]` — the union of:
   - Decision Events whose `decision_source` is in the positive
     allowlist AND whose `(scope_type, scope_uuid)` matches one of
     five canonical scope branches (segment | page | block | project
     | account).
   - `preflight_confirmation` events of the CURRENT export attempt
     only, filtered by `related_export_attempt_id`.

The allowlist excludes:
- `export_confirmation` — OCR-export-specific per §4.10. Including it
  in translation EXPORT_EVENT is a category error (R-S5-04).
- `style_management` — Stilprofil-Versionierung deferred per CR-3
  (R-S5-05). Revisited when the F-family is built.
"""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.schemas import Block, DecisionEvent, Page, Segment
from waraq.schemas.enums import DecisionSource, ScopeType

# Per Sprint 5 §2 §"`active_decision_event_uuids[]` filling rule
# (positive allowlist)". The seven allowed decision_source values for
# translation EXPORT_EVENT (preflight_confirmation is handled
# separately because of the per-attempt binding).
ALLOWLISTED_DECISION_SOURCES: frozenset[str] = frozenset(
    {
        DecisionSource.OCR_REVIEW.value,
        DecisionSource.LOCK_MANAGEMENT.value,
        DecisionSource.CONFLICT_RESOLUTION.value,
        DecisionSource.TRANSLATION_PIPELINE.value,
        DecisionSource.AUDIT_RESOLUTION.value,
        DecisionSource.CONSISTENCY_RESOLUTION.value,
        DecisionSource.GLOSSARY_MANAGEMENT.value,
    }
)


async def _resolve_segment_set(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    segment_uuids: list[_uuid.UUID] | None,
) -> tuple[list[Segment], list[_uuid.UUID], list[_uuid.UUID]]:
    """Return (segments, page_uuids, block_uuids) for the in-scope
    active Segments of `project_uuid`.

    If `segment_uuids` is provided, the result is filtered to that
    explicit set (used for sub-project export scopes). Otherwise the
    full project's active segments are returned. Inactive Segments
    are excluded in either case.

    Segment has no direct `project_uuid` column; project linkage is
    Segment → Block → Page → Project. We join through to filter at
    SQL level.
    """
    stmt = (
        select(Segment, Block.block_uuid, Page.page_uuid)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(Segment.active.is_(True))
    )
    if segment_uuids is not None:
        stmt = stmt.where(Segment.satz_uuid.in_(segment_uuids))
    rows = (await session.execute(stmt)).all()

    segments: list[Segment] = []
    pages: set[_uuid.UUID] = set()
    blocks: set[_uuid.UUID] = set()
    for seg, block_id, page_id in rows:
        segments.append(seg)
        pages.add(page_id)
        blocks.add(block_id)
    return segments, sorted(pages, key=str), sorted(blocks, key=str)


async def collect_revision_snapshot(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    segment_uuids: list[_uuid.UUID] | None = None,
) -> tuple[list[_uuid.UUID], list[_uuid.UUID], list[_uuid.UUID], list[_uuid.UUID]]:
    """Build `revision_snapshot[]` per Sprint 5 §2.

    Reads from `segments.current_rev_uuid` (NOT from the `revisions`
    table — Revision-Snapshot-Segments-Join-Test). Excludes:
    - Inactive Segments (Revision-Snapshot-Inaktive-Excluded-Test).
    - Segments with `current_rev_uuid IS NULL` (no revision yet).
    - Segments outside the explicit `segment_uuids` scope, when given
      (Revision-Snapshot-Outside-Scope-Excluded-Test).

    Returns
    -------
    `(revision_snapshot, segment_uuids_in_snapshot, page_uuids,
       block_uuids)`. The page/block UUID lists are sidecars used by
    `collect_active_decision_event_uuids` for the scope-coverage join.
    """
    segments, page_uuids, block_uuids = await _resolve_segment_set(
        session=session, project_uuid=project_uuid, segment_uuids=segment_uuids
    )
    revs: list[_uuid.UUID] = []
    seg_uuids_in_snapshot: list[_uuid.UUID] = []
    for seg in segments:
        if seg.current_rev_uuid is None:
            continue
        revs.append(seg.current_rev_uuid)
        seg_uuids_in_snapshot.append(seg.satz_uuid)
    return revs, seg_uuids_in_snapshot, page_uuids, block_uuids


async def collect_active_decision_event_uuids(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    account_uuid: _uuid.UUID,
    segment_uuids: list[_uuid.UUID],
    page_uuids: list[_uuid.UUID],
    block_uuids: list[_uuid.UUID],
    current_export_attempt_id: str,
) -> list[_uuid.UUID]:
    """Build `active_decision_event_uuids[]` per Sprint 5 §2.

    The positive-allowlist rule: a Decision Event is included iff
    (a) `decision_source` is in `ALLOWLISTED_DECISION_SOURCES` AND
        `(scope_type, scope_uuid)` matches one of the five canonical
        scope branches (segment in `segment_uuids` / page in
        `page_uuids` / block in `block_uuids` / project ==
        `project_uuid` / account == `account_uuid`),
    OR
    (b) `decision_source = preflight_confirmation` AND
        `related_export_attempt_id == current_export_attempt_id`.

    Both arms additionally require `is_superseded = false` if the
    column exists (per OCR Endfassung v1.3 §3 analog). v1.0 does NOT
    yet carry an `is_superseded` column on `decision_events` — the
    field is reserved per Dokument 1 §4.11 and treated as `false`
    everywhere here. M5+ may flip a row to superseded; the snapshot
    rule is forward-compatible.

    The function returns a stable-sorted list (order = scan order),
    making test assertions reproducible.
    """
    # Arm (a): allowlist + scope-coverage join.
    seg_set = set(segment_uuids)
    page_set = set(page_uuids)
    block_set = set(block_uuids)

    arm_a = await session.execute(
        select(DecisionEvent).where(DecisionEvent.decision_source.in_(ALLOWLISTED_DECISION_SOURCES))
    )
    out: list[_uuid.UUID] = []
    seen: set[_uuid.UUID] = set()
    for de in arm_a.scalars():
        st = de.scope_type
        su = de.scope_uuid
        if (
            (st == ScopeType.SEGMENT.value and su in seg_set)
            or (st == ScopeType.PAGE.value and su in page_set)
            or (st == ScopeType.BLOCK.value and su in block_set)
            or (st == ScopeType.PROJECT.value and su == project_uuid)
            or (st == ScopeType.ACCOUNT.value and su == account_uuid)
        ):
            include = True
        else:
            include = False
        if include and de.decision_event_uuid not in seen:
            out.append(de.decision_event_uuid)
            seen.add(de.decision_event_uuid)

    # Arm (b): preflight_confirmation events of the current attempt.
    arm_b = await session.execute(
        select(DecisionEvent)
        .where(DecisionEvent.decision_source == DecisionSource.PREFLIGHT_CONFIRMATION.value)
        .where(DecisionEvent.related_export_attempt_id == current_export_attempt_id)
    )
    for de in arm_b.scalars():
        if de.decision_event_uuid in seen:
            continue
        out.append(de.decision_event_uuid)
        seen.add(de.decision_event_uuid)

    return out


__all__ = [
    "ALLOWLISTED_DECISION_SOURCES",
    "collect_active_decision_event_uuids",
    "collect_revision_snapshot",
]
