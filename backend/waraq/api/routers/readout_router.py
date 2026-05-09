"""T-10.2.1 — Sprint 6 four scope-separated history endpoints.

Per Sprint 6 §2 + §A HG-S6-4 (Endpoint-No-Cross-Pollination invariant):
each endpoint returns ONLY its own scope's events. The four endpoints
share a strict invariant — no two endpoints overlap in their result
sets, with one documented exception: EXPORT_EVENT-POs appear in both
Segmenthistorie (as werkweite Referenz, marked
`als_werkweite_referenz=True`) AND Projekthistorie (as werks-eigene
Entität). The structural marker distinguishes the two presentations.

Distinct from `history_router.py` (M2 lightweight aggregate, used by
the M4 UI sidebar). The two routers coexist:
- `/segments/{u}/history`, `/pages/{u}/history`, `/projects/{u}/history`
  → M2 aggregate (denormalized).
- `/history/segment/{u}`, `/history/page/{u}`, `/history/project/{u}`,
  `/history/log` → Sprint 6 canonical scope-trennende reads.

All four endpoints are pure-read; none writes (R-S6-10).
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy.orm import DeclarativeBase

from waraq.api._ownership import (
    owned_page_or_404,
    owned_project_or_404,
    owned_segment_or_404,
)
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.readout import (
    LogEntryFilter,
    SegmentExportEventRef,
    get_log_entries,
    get_page_readout,
    get_project_readout,
    get_segment_readout,
)

router = APIRouter(prefix="/history", tags=["readout"])


def _orm_to_dict(row: DeclarativeBase) -> dict[str, Any]:
    """Convert an ORM row to a JSON-safe dict via column attrs."""
    out: dict[str, Any] = {}
    for col in row.__table__.columns:
        value = getattr(row, col.name)
        if isinstance(value, _uuid.UUID):
            out[col.name] = str(value)
        elif isinstance(value, datetime):
            out[col.name] = value.isoformat()
        elif isinstance(value, Enum):
            out[col.name] = value.value
        else:
            out[col.name] = value
    return out


def _export_ref_to_dict(ref: SegmentExportEventRef) -> dict[str, Any]:
    return {
        "po": _orm_to_dict(ref.po),
        "als_werkweite_referenz": ref.als_werkweite_referenz,
    }


# --- Segmenthistorie -------------------------------------------------------


@router.get("/segment/{satz_uuid}")
async def segmenthistorie(
    satz_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> dict[str, Any]:
    """Per Sprint 6 §2 / Endpoint-Segmenthistorie-Vollstaendigkeit-Test:
    segment-scoped Revisions + DEs + POs + EXPORT_EVENT werkweite
    Referenzen.

    Excludes (per Endpoint-Segmenthistorie-Excludes-* tests):
    - page-, block-, project-, account-scoped Decision Events.
    - Log-Eintrag rows.
    """
    await owned_segment_or_404(session, satz_uuid, current.account_uuid)
    r = await get_segment_readout(session=session, satz_uuid=satz_uuid)
    return {
        "satz_uuid": str(r.satz_uuid),
        "revisions": [_orm_to_dict(rev) for rev in r.revisions],
        "decision_events": [_orm_to_dict(de) for de in r.decision_events],
        "provenance_objects": [_orm_to_dict(po) for po in r.provenance_objects],
        "export_event_refs": [_export_ref_to_dict(ref) for ref in r.export_event_refs],
    }


# --- Seitenhistorie --------------------------------------------------------


@router.get("/page/{page_uuid}")
async def seitenhistorie(
    page_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> dict[str, Any]:
    """Per Sprint 6 §2 / Endpoint-Seitenhistorie-Page-Scoped-Only-Test:
    ONLY page-scoped Decision Events.

    Excludes (per Endpoint-Seitenhistorie-Excludes-* tests):
    - segment-scoped DEs of Segments belonging to the page.
    - segment-scoped Revision-UUIDs.
    - EXPORT_EVENT references.
    - Log-Eintrag rows.
    - all POs.
    """
    await owned_page_or_404(session, page_uuid, current.account_uuid)
    r = await get_page_readout(session=session, page_uuid=page_uuid)
    return {
        "page_uuid": str(r.page_uuid),
        "decision_events": [_orm_to_dict(de) for de in r.decision_events],
    }


# --- Projekthistorie -------------------------------------------------------


@router.get("/project/{project_uuid}")
async def projekthistorie(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> dict[str, Any]:
    """Per Sprint 6 §2 / Endpoint-Projekthistorie-Project-Scoped-DEs-And-
    Export-Events-Test: project-scoped DEs + EXPORT_EVENT POs only.

    Excludes (per Endpoint-Projekthistorie-Excludes-* tests):
    - segment-, page-, block-scoped Decision Events.
    - account-scoped Decision Events (R-S6-05 — gebundener Resthinweis
      per Dokument 2 §2D).
    - Log-Eintrag rows.
    - all POs except EXPORT_EVENT.
    """
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    r = await get_project_readout(session=session, project_uuid=project_uuid)
    return {
        "project_uuid": str(r.project_uuid),
        "decision_events": [_orm_to_dict(de) for de in r.decision_events],
        "export_events": [_orm_to_dict(po) for po in r.export_events],
    }


# --- Ereignis-Log ----------------------------------------------------------


@router.get("/log")
async def ereignis_log(
    session: DbSession,
    current: CurrentAccount,
    scope_uuid: _uuid.UUID | None = Query(default=None),
    operation_type: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
) -> dict[str, Any]:
    """Per Sprint 6 §2 / Endpoint-Ereignis-Log-Only-Logs-Test: Log-Eintrag
    rows only.

    Optional query filters: `scope_uuid`, `operation_type`, time
    range. Results in chronological order.

    Excludes everything else — Log-Eintrag rows NEVER appear in
    Segmenthistorie / Seitenhistorie / Projekthistorie endpoints
    (Endpoint-Ereignis-Log-No-Other-Histories-Test).

    Authentication only — log is project-cross-cutting; we trust the
    bearer-authenticated session at this layer. Per-scope ownership
    filtering is the caller's responsibility via `scope_uuid`.
    """
    _ = current  # auth is enforced via DI; current isn't used for filter
    rows = await get_log_entries(
        session=session,
        filter_=LogEntryFilter(
            scope_uuid=scope_uuid,
            operation_type=operation_type,
            start=start,
            end=end,
        ),
    )
    return {
        "log_entries": [_orm_to_dict(le) for le in rows],
    }
