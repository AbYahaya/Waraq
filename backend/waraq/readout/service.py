"""T-10.1.1 + T-10.1.2 — Sprint 6 canonical readout service.

Six pure-read functions, all chronologically ordered, all strictly
scope-trennend. None writes to any table.

Scope discipline (Sprint 6 §A HG-S6-1..5):

- `get_pos_for_segment`: ONLY POs with `(scope_type='segment',
  scope_uuid=satz_uuid)`. Page-scoped POs (SCAN-PO from T-3.1.2) and
  project-scoped POs (EXPORT_EVENT) are NEVER returned here.
- `get_export_events_for_segment`: lookup is strictly via
  `revision_snapshot[]` JSONB membership of any of the segment's
  Revision rows' `rev_uuid`. The query enumerates Revisions FK'd to
  the segment (covering reactivation cycles per Sprint 1 T-4.2.2),
  collects their UUIDs as strings, and asks Postgres for EXPORT_EVENTs
  whose payload `revision_snapshot` JSONB array overlaps. **No
  segment-FK on EXPORT_EVENT exists; no such shortcut may be
  introduced** (R-S6-01).
- `get_page_readout`: ONLY page-scoped DEs. Decision Events about
  Segments belonging to the page (segment-scoped DEs with
  `scope_type='segment'`) are NEVER returned (R-S6-04).
- `get_project_readout`: ONLY project-scoped DEs + EXPORT_EVENT POs
  with `project_uuid` matching. Account-scoped DEs are excluded per
  Dokument 2 §2D gebundener Resthinweis (R-S6-05). Log-Eintrag rows
  are excluded (R-S6-06).
- `get_log_entries`: Log-Eintrag rows only. Never appears in any
  segment/page/project readout (R-S6-06).
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.schemas import (
    DecisionEvent,
    LogEntry,
    ProvenanceObject,
    Revision,
    Segment,
)
from waraq.schemas.enums import POType, ScopeType

# --- result models --------------------------------------------------------


@dataclass(frozen=True, kw_only=True, slots=True)
class SegmentExportEventRef:
    """An EXPORT_EVENT-PO that the segment participated in.

    Per Sprint 6 §2 / Get-Export-Events-Werkweite-Referenz-Marker-Test:
    every entry is structurally marked `als_werkweite_referenz=True`
    so the UI / downstream consumer cannot mistake the EXPORT_EVENT
    for a segment-eigener PO.
    """

    po: ProvenanceObject
    als_werkweite_referenz: bool = True


@dataclass(frozen=True, kw_only=True, slots=True)
class SegmentReadout:
    satz_uuid: _uuid.UUID
    revisions: list[Revision] = field(default_factory=list)
    decision_events: list[DecisionEvent] = field(default_factory=list)
    provenance_objects: list[ProvenanceObject] = field(default_factory=list)
    export_event_refs: list[SegmentExportEventRef] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True, slots=True)
class PageReadout:
    page_uuid: _uuid.UUID
    decision_events: list[DecisionEvent] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True, slots=True)
class ProjectReadout:
    project_uuid: _uuid.UUID
    decision_events: list[DecisionEvent] = field(default_factory=list)
    export_events: list[ProvenanceObject] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True, slots=True)
class LogEntryFilter:
    scope_uuid: _uuid.UUID | None = None
    operation_type: str | None = None
    start: datetime | None = None
    end: datetime | None = None


# --- T-10.1.1: segment-scoped readouts ------------------------------------


async def get_pos_for_segment(
    *,
    session: AsyncSession,
    satz_uuid: _uuid.UUID,
) -> list[ProvenanceObject]:
    """Per Sprint 6 §2 / Get-Pos-For-Segment-Scope-Filter-Test: ONLY
    POs with `scope_type=segment` AND `scope_uuid=satz_uuid`.

    Page-scoped POs (e.g., SCAN-PO from T-3.1.2 anchored at the
    segment's page) are excluded. Project-scoped POs (e.g.,
    EXPORT_EVENT) are excluded. The function is read-only.
    """
    result = await session.execute(
        select(ProvenanceObject)
        .where(ProvenanceObject.scope_type == ScopeType.SEGMENT.value)
        .where(ProvenanceObject.scope_uuid == satz_uuid)
        .order_by(ProvenanceObject.created_at.asc())
    )
    return list(result.scalars())


async def _enumerate_segment_revision_uuids(
    *, session: AsyncSession, satz_uuid: _uuid.UUID
) -> list[_uuid.UUID]:
    """Every Revision row ever associated with this Segment.

    Covers reactivation cycles per Sprint 1 T-4.2.2 — a Segment that
    was inactivated and reactivated retains its Revision history (FKs
    to satz_uuid persist; H-5 forbids deletion). The export lookup
    walks this full set so no EXPORT_EVENT is missed.
    """
    result = await session.execute(select(Revision.rev_uuid).where(Revision.satz_uuid == satz_uuid))
    return list(result.scalars())


async def get_export_events_for_segment(
    *,
    session: AsyncSession,
    satz_uuid: _uuid.UUID,
) -> list[SegmentExportEventRef]:
    """Per Sprint 6 §2 / Get-Export-Events-For-Segment-Via-Snapshot-Test:
    lookup is **strictly** via `revision_snapshot[]` JSONB membership.

    For each EXPORT_EVENT-PO, the payload `revision_snapshot` is a
    JSONB array of revision-UUID strings (per Sprint 5 T-9.2.1
    payload). We collect every Revision FK'd to the segment (active or
    historical), stringify the UUIDs, and check JSONB membership.

    Lineage discipline (R-S6-02 / Get-Export-Events-For-Segment-
    Lineage-Aware-Test): a reactivated Segment still has every
    historical `Revision.rev_uuid` accessible; we walk all of them.
    Pre-inactivation EXPORT_EVENTs and post-reactivation EXPORT_EVENTs
    both surface, in chronological order.

    Each return entry carries `als_werkweite_referenz=True` per
    Get-Export-Events-Werkweite-Referenz-Marker-Test.
    """
    rev_uuids = await _enumerate_segment_revision_uuids(session=session, satz_uuid=satz_uuid)
    if not rev_uuids:
        return []

    rev_uuid_strings = [str(u) for u in rev_uuids]

    # Pull EXPORT_EVENT-POs in chronological order; filter Python-side
    # for snapshot membership. The set of EXPORT_EVENTs is bounded by
    # the project's export attempts and stays small in practice.
    result = await session.execute(
        select(ProvenanceObject)
        .where(ProvenanceObject.po_type == POType.EXPORT_EVENT.value)
        .order_by(ProvenanceObject.created_at.asc())
    )
    refs: list[SegmentExportEventRef] = []
    for po in result.scalars():
        snapshot = (po.payload or {}).get("revision_snapshot") or []
        if not isinstance(snapshot, list):
            continue
        if any(rev_str in snapshot for rev_str in rev_uuid_strings):
            refs.append(SegmentExportEventRef(po=po, als_werkweite_referenz=True))
    return refs


async def get_segment_readout(
    *,
    session: AsyncSession,
    satz_uuid: _uuid.UUID,
) -> SegmentReadout:
    """Aggregate the four canonical Sprint 6 §2 segment-history kinds:
    segment-scoped Revisions + segment-scoped Decision Events +
    segment-scoped POs + EXPORT_EVENT werkweite Referenzen.

    Excludes: page-/block-/project-/account-scoped DEs, Log-Eintrag rows,
    POs of any other scope (per the four-endpoint cross-pollination
    invariant Sprint 6 §A HG-S6-4).
    """
    revisions = list(
        (
            await session.execute(
                select(Revision)
                .where(Revision.satz_uuid == satz_uuid)
                .order_by(Revision.created_at.asc())
            )
        ).scalars()
    )
    decision_events = list(
        (
            await session.execute(
                select(DecisionEvent)
                .where(DecisionEvent.scope_type == ScopeType.SEGMENT.value)
                .where(DecisionEvent.scope_uuid == satz_uuid)
                .order_by(DecisionEvent.created_at.asc())
            )
        ).scalars()
    )
    pos = await get_pos_for_segment(session=session, satz_uuid=satz_uuid)
    export_refs = await get_export_events_for_segment(session=session, satz_uuid=satz_uuid)
    return SegmentReadout(
        satz_uuid=satz_uuid,
        revisions=revisions,
        decision_events=decision_events,
        provenance_objects=pos,
        export_event_refs=export_refs,
    )


# --- T-10.1.2: page- and project-scoped readouts --------------------------


async def get_page_readout(
    *,
    session: AsyncSession,
    page_uuid: _uuid.UUID,
) -> PageReadout:
    """Per Sprint 6 §2 / Get-Page-History-Page-Scoped-Only-Test +
    Get-Page-History-No-Segment-Events-Test: ONLY page-scoped DEs.

    Decision Events about Segments belonging to the page are NEVER
    returned. The page history is the page-level history only — R-S6-04
    names the collapse-to-all-events-of-scope as the named structural
    failure mode.
    """
    decisions = list(
        (
            await session.execute(
                select(DecisionEvent)
                .where(DecisionEvent.scope_type == ScopeType.PAGE.value)
                .where(DecisionEvent.scope_uuid == page_uuid)
                .order_by(DecisionEvent.created_at.asc())
            )
        ).scalars()
    )
    return PageReadout(page_uuid=page_uuid, decision_events=decisions)


async def get_project_readout(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> ProjectReadout:
    """Per Sprint 6 §2: project-scoped DEs + EXPORT_EVENT POs (direct
    via `project_uuid` from EXPORT_EVENT.scope_uuid, NOT via snapshot
    lookup — the project owns its EXPORT_EVENTs directly).

    Excludes (R-S6-05 + Sprint 6 §2):
    - segment-, page-, block-, account-scoped Decision Events.
    - Log-Eintrag rows.
    - any PO except EXPORT_EVENT.
    """
    decisions = list(
        (
            await session.execute(
                select(DecisionEvent)
                .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
                .where(DecisionEvent.scope_uuid == project_uuid)
                .order_by(DecisionEvent.created_at.asc())
            )
        ).scalars()
    )
    export_events = list(
        (
            await session.execute(
                select(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.EXPORT_EVENT.value)
                .where(ProvenanceObject.scope_uuid == project_uuid)
                .order_by(ProvenanceObject.created_at.asc())
            )
        ).scalars()
    )
    return ProjectReadout(
        project_uuid=project_uuid,
        decision_events=decisions,
        export_events=export_events,
    )


# --- T-10.2.1 / Ereignis-Log endpoint backing -----------------------------


async def get_log_entries(
    *,
    session: AsyncSession,
    filter_: LogEntryFilter | None = None,
) -> list[LogEntry]:
    """Per Sprint 6 §2 / Endpoint-Ereignis-Log-Only-Logs-Test: returns
    Log-Eintrag rows only. Optional filter narrows by scope_uuid /
    operation_type / time range.

    Read-only. Does NOT write a Log-Eintrag for the read operation
    itself (R-S6-10 / Endpoint-Read-Only-Test).
    """
    stmt = select(LogEntry).order_by(LogEntry.created_at.asc())
    if filter_ is not None:
        if filter_.scope_uuid is not None:
            stmt = stmt.where(LogEntry.scope_uuid == filter_.scope_uuid)
        if filter_.operation_type is not None:
            stmt = stmt.where(LogEntry.operation_type == filter_.operation_type)
        if filter_.start is not None:
            stmt = stmt.where(LogEntry.created_at >= filter_.start)
        if filter_.end is not None:
            stmt = stmt.where(LogEntry.created_at <= filter_.end)
    result = await session.execute(stmt)
    return list(result.scalars())


# Silence unused-import warning for Segment (kept for type clarity in the
# segment-readout flow even though we don't construct Segment rows here).
_: Any = Segment


__all__ = [
    "LogEntryFilter",
    "PageReadout",
    "ProjectReadout",
    "SegmentExportEventRef",
    "SegmentReadout",
    "get_export_events_for_segment",
    "get_log_entries",
    "get_page_readout",
    "get_pos_for_segment",
    "get_project_readout",
    "get_segment_readout",
]
