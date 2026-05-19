"""History endpoints — read-side rollups for segment / page / project.

Returns ORM rows serialized to dicts. The dict shapes are not contractual
beyond their PK columns and a few descriptive fields. Sprint 6's full
canonical readout (T-10.x.x) is M5 work; these are the lightweight reads
that M4's UI consumes for segment/page/project history sidebars.
"""

from __future__ import annotations

import dataclasses
import uuid as _uuid
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase

from waraq.api._ownership import (
    owned_page_or_404,
    owned_project_or_404,
    owned_segment_or_404,
)
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.history import get_page_history, get_project_history, get_segment_history
from waraq.schemas import ProjectQuranPassage

router = APIRouter(tags=["history"])


def _orm_to_dict(row: DeclarativeBase) -> dict[str, Any]:
    """Convert an ORM instance to a JSON-safe dict via its column attrs.
    Datetimes become ISO strings, UUIDs become strings, enums become their
    values, JSONB stays as-is."""
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


def _segment_history_to_dict(h: Any) -> dict[str, Any]:
    return {
        "satz_uuid": str(h.satz_uuid),
        "revisions": [_orm_to_dict(r) for r in h.revisions],
        "decision_events": [_orm_to_dict(d) for d in h.decision_events],
        "provenance_objects": [_orm_to_dict(p) for p in h.provenance_objects],
        "log_entries": [_orm_to_dict(le) for le in h.log_entries],
        "conflict_instances": [_orm_to_dict(c) for c in h.conflict_instances],
    }


async def _latest_quran_passage_for_segment(
    session: DbSession,
    *,
    satz_uuid: _uuid.UUID,
) -> dict[str, Any] | None:
    row = (
        await session.execute(
            select(ProjectQuranPassage)
            .where(ProjectQuranPassage.satz_uuid == satz_uuid)
            .where(ProjectQuranPassage.state != "rejected")
            .order_by(ProjectQuranPassage.detected_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return _orm_to_dict(row)


@router.get("/segments/{satz_uuid}/history")
async def segment_history(
    satz_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> dict[str, Any]:
    await owned_segment_or_404(session, satz_uuid, current.account_uuid)
    h = await get_segment_history(session=session, satz_uuid=satz_uuid)
    payload = _segment_history_to_dict(h)
    payload["quran_passage"] = await _latest_quran_passage_for_segment(session, satz_uuid=satz_uuid)
    return payload


@router.get("/pages/{page_uuid}/history")
async def page_history(
    page_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> dict[str, Any]:
    await owned_page_or_404(session, page_uuid, current.account_uuid)
    h = await get_page_history(session=session, page_uuid=page_uuid)
    return {
        "page_uuid": str(h.page_uuid),
        "segments": [_segment_history_to_dict(s) for s in h.segments],
        "page_decision_events": [_orm_to_dict(d) for d in h.page_decision_events],
        "page_provenance_objects": [_orm_to_dict(p) for p in h.page_provenance_objects],
        "page_log_entries": [_orm_to_dict(le) for le in h.page_log_entries],
        "ocr_error_instances": [_orm_to_dict(o) for o in h.ocr_error_instances],
    }


@router.get("/projects/{project_uuid}/history")
async def project_history(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> dict[str, Any]:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    h = await get_project_history(session=session, project_uuid=project_uuid)
    return {
        "project_uuid": str(h.project_uuid),
        "pages": [
            {
                "page_uuid": str(p.page_uuid),
                "segments": [_segment_history_to_dict(s) for s in p.segments],
                "page_decision_events": [_orm_to_dict(d) for d in p.page_decision_events],
                "page_provenance_objects": [_orm_to_dict(po) for po in p.page_provenance_objects],
                "page_log_entries": [_orm_to_dict(le) for le in p.page_log_entries],
                "ocr_error_instances": [_orm_to_dict(o) for o in p.ocr_error_instances],
            }
            for p in h.pages
        ],
        "project_decision_events": [_orm_to_dict(d) for d in h.project_decision_events],
        "project_provenance_objects": [_orm_to_dict(po) for po in h.project_provenance_objects],
        "project_log_entries": [_orm_to_dict(le) for le in h.project_log_entries],
        "konsistenz_befunde": [_orm_to_dict(k) for k in h.konsistenz_befunde],
    }


# Silence unused-import warning for dataclasses (kept for future extensions).
_ = dataclasses
