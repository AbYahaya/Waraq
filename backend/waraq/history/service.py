"""M2 closeout — lightweight history queries.

Per MILESTONES.md M2 client list ("History tracking (segment, page,
project)"). Read-side aggregations across the existing event tables. The
full canonical readout (Sprint 6 / WS-10 / T-10.x.x) is out of scope here —
this module returns the raw row sets per scope without further joining or
unified-timeline merging. UI / M4 can present the merged view.

Discipline (Sprint 6 §6 R-S6-09 / DBB §B Abkürzung 8): LINEAGE_EVENT-POs
must NOT surface as Decision Events in any history. They're in
`provenance_objects`, not `decision_events`, so this is structurally
enforced; the type signatures here keep that separation visible.

Per-scope aggregation:

- **Segment history** — Revisions (FK satz_uuid), Decision Events
  (scope_type=segment AND scope_uuid=satz_uuid), Provenance Objects
  (scope_type=segment AND scope_uuid=satz_uuid), Log Entries
  (scope_uuid=satz_uuid). LINEAGE_EVENT-POs anchored at the segment do
  appear under provenance_objects (correct: they're POs, not DEs).
- **Page history** — all segment histories under the page + page-scoped
  Decision Events / POs / Log Entries + the OCR error instances on the
  page.
- **Project history** — page histories aggregated + project-scoped
  Decision Events / POs / Log Entries + Konsistenz-Befunde + open conflict
  instances under the project.
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.schemas import (
    Block,
    ConflictInstance,
    DecisionEvent,
    KonsistenzBefund,
    LogEntry,
    OcrErrorInstance,
    Page,
    ProvenanceObject,
    Revision,
    Segment,
)
from waraq.schemas.enums import ScopeType


@dataclass(frozen=True, kw_only=True, slots=True)
class SegmentHistory:
    satz_uuid: _uuid.UUID
    revisions: list[Revision] = field(default_factory=list)
    decision_events: list[DecisionEvent] = field(default_factory=list)
    provenance_objects: list[ProvenanceObject] = field(default_factory=list)
    log_entries: list[LogEntry] = field(default_factory=list)
    conflict_instances: list[ConflictInstance] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True, slots=True)
class PageHistory:
    page_uuid: _uuid.UUID
    segments: list[SegmentHistory] = field(default_factory=list)
    page_decision_events: list[DecisionEvent] = field(default_factory=list)
    page_provenance_objects: list[ProvenanceObject] = field(default_factory=list)
    page_log_entries: list[LogEntry] = field(default_factory=list)
    ocr_error_instances: list[OcrErrorInstance] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True, slots=True)
class ProjectHistory:
    project_uuid: _uuid.UUID
    pages: list[PageHistory] = field(default_factory=list)
    project_decision_events: list[DecisionEvent] = field(default_factory=list)
    project_provenance_objects: list[ProvenanceObject] = field(default_factory=list)
    project_log_entries: list[LogEntry] = field(default_factory=list)
    konsistenz_befunde: list[KonsistenzBefund] = field(default_factory=list)


# --- segment-level --------------------------------------------------------


async def get_segment_history(
    *,
    session: AsyncSession,
    satz_uuid: _uuid.UUID,
) -> SegmentHistory:
    """Read-side aggregation of all events anchored at `satz_uuid`.

    Includes the segment's own conflict instances (resolved + open) and
    LINEAGE_EVENT-POs that touched it. Returns a frozen dataclass; rows
    are ordered by their natural created_at / detected_at timestamps.
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
    provenance_objects = list(
        (
            await session.execute(
                select(ProvenanceObject)
                .where(ProvenanceObject.scope_type == ScopeType.SEGMENT.value)
                .where(ProvenanceObject.scope_uuid == satz_uuid)
                .order_by(ProvenanceObject.created_at.asc())
            )
        ).scalars()
    )
    log_entries = list(
        (
            await session.execute(
                select(LogEntry)
                .where(LogEntry.scope_uuid == satz_uuid)
                .order_by(LogEntry.created_at.asc())
            )
        ).scalars()
    )
    conflicts = list(
        (
            await session.execute(
                select(ConflictInstance)
                .where(ConflictInstance.satz_uuid == satz_uuid)
                .order_by(ConflictInstance.detected_at.asc())
            )
        ).scalars()
    )
    return SegmentHistory(
        satz_uuid=satz_uuid,
        revisions=revisions,
        decision_events=decision_events,
        provenance_objects=provenance_objects,
        log_entries=log_entries,
        conflict_instances=conflicts,
    )


# --- page-level -----------------------------------------------------------


async def get_page_history(
    *,
    session: AsyncSession,
    page_uuid: _uuid.UUID,
) -> PageHistory:
    """Aggregates all segment histories under the page + page-scoped events
    + OCR error instances on the page."""
    # Resolve segments under this page.
    seg_uuids = list(
        (
            await session.execute(
                select(Segment.satz_uuid)
                .join(Block, Block.block_uuid == Segment.block_uuid)
                .where(Block.page_uuid == page_uuid)
                .order_by(Segment.satz_index.asc())
            )
        ).scalars()
    )
    segment_histories = [
        await get_segment_history(session=session, satz_uuid=sid) for sid in seg_uuids
    ]

    page_decisions = list(
        (
            await session.execute(
                select(DecisionEvent)
                .where(DecisionEvent.scope_type == ScopeType.PAGE.value)
                .where(DecisionEvent.scope_uuid == page_uuid)
                .order_by(DecisionEvent.created_at.asc())
            )
        ).scalars()
    )
    page_pos = list(
        (
            await session.execute(
                select(ProvenanceObject)
                .where(ProvenanceObject.scope_type == ScopeType.PAGE.value)
                .where(ProvenanceObject.scope_uuid == page_uuid)
                .order_by(ProvenanceObject.created_at.asc())
            )
        ).scalars()
    )
    page_logs = list(
        (
            await session.execute(
                select(LogEntry)
                .where(LogEntry.scope_uuid == page_uuid)
                .where(LogEntry.scope_type == ScopeType.PAGE.value)
                .order_by(LogEntry.created_at.asc())
            )
        ).scalars()
    )
    ocr_errors = list(
        (
            await session.execute(
                select(OcrErrorInstance)
                .where(OcrErrorInstance.page_uuid == page_uuid)
                .order_by(OcrErrorInstance.detected_at.asc())
            )
        ).scalars()
    )

    return PageHistory(
        page_uuid=page_uuid,
        segments=segment_histories,
        page_decision_events=page_decisions,
        page_provenance_objects=page_pos,
        page_log_entries=page_logs,
        ocr_error_instances=ocr_errors,
    )


# --- project-level --------------------------------------------------------


async def get_project_history(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> ProjectHistory:
    """Aggregates all page histories under the project + project-scoped
    events + Konsistenz-Befunde."""
    page_uuids = list(
        (
            await session.execute(
                select(Page.page_uuid)
                .where(Page.project_uuid == project_uuid)
                .order_by(Page.page_index.asc())
            )
        ).scalars()
    )
    page_histories = [await get_page_history(session=session, page_uuid=pid) for pid in page_uuids]

    project_decisions = list(
        (
            await session.execute(
                select(DecisionEvent)
                .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
                .where(DecisionEvent.scope_uuid == project_uuid)
                .order_by(DecisionEvent.created_at.asc())
            )
        ).scalars()
    )
    project_pos = list(
        (
            await session.execute(
                select(ProvenanceObject)
                .where(ProvenanceObject.scope_type == ScopeType.PROJECT.value)
                .where(ProvenanceObject.scope_uuid == project_uuid)
                .order_by(ProvenanceObject.created_at.asc())
            )
        ).scalars()
    )
    project_logs = list(
        (
            await session.execute(
                select(LogEntry)
                .where(LogEntry.scope_uuid == project_uuid)
                .where(LogEntry.scope_type == ScopeType.PROJECT.value)
                .order_by(LogEntry.created_at.asc())
            )
        ).scalars()
    )
    befunde = list(
        (
            await session.execute(
                select(KonsistenzBefund)
                .where(KonsistenzBefund.project_uuid == project_uuid)
                .order_by(KonsistenzBefund.detected_at.asc())
            )
        ).scalars()
    )

    return ProjectHistory(
        project_uuid=project_uuid,
        pages=page_histories,
        project_decision_events=project_decisions,
        project_provenance_objects=project_pos,
        project_log_entries=project_logs,
        konsistenz_befunde=befunde,
    )
