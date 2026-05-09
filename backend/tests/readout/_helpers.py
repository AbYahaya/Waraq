"""Shared seed helpers for Sprint 6 readout tests."""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy.ext.asyncio import AsyncSession

from tests.export._helpers import seed_project_with_account, seed_segment_with_revision
from waraq.decisions import create_decision_event
from waraq.export import ExportConfig, run_export_job
from waraq.identity import new_uuid
from waraq.preflight import (
    PFLICHTFRAGE_COUNT,
    confirm_pflichtfrage,
    evaluate_preflight,
    start_preflight_run,
)
from waraq.provenance import create_po
from waraq.schemas import DecisionEvent, ProvenanceObject, Segment
from waraq.schemas.enums import DecisionSource, POType, ScopeType

__all__ = [
    "seed_de",
    "seed_export_event",
    "seed_po",
    "seed_project_with_account",
    "seed_segment_export",
    "seed_segment_with_revision",
]


async def seed_de(
    session: AsyncSession,
    *,
    scope_type: ScopeType,
    scope_uuid: _uuid.UUID,
    decision_source: DecisionSource,
    decision_type: str = "test_event",
) -> DecisionEvent:
    return await create_decision_event(
        session=session,
        scope_type=scope_type,
        scope_uuid=scope_uuid,
        decision_type=decision_type,
        decision_source=decision_source,
    )


async def seed_po(
    session: AsyncSession,
    *,
    po_type: POType,
    scope_type: ScopeType,
    scope_uuid: _uuid.UUID,
    payload: dict | None = None,
) -> ProvenanceObject:
    return await create_po(
        session=session,
        po_type=po_type,
        scope_type=scope_type,
        scope_uuid=scope_uuid,
        payload=payload or {},
    )


async def seed_export_event(
    session: AsyncSession,
    *,
    project_uuid: _uuid.UUID,
    revision_snapshot: list[_uuid.UUID],
    extra_payload: dict | None = None,
) -> ProvenanceObject:
    """Synthetic EXPORT_EVENT-PO with a controlled `revision_snapshot[]`.

    Bypasses `run_export_job` so tests can inject specific snapshot
    contents (e.g., to exercise lineage-aware lookups against snapshots
    that contain pre-inactivation rev_uuids).
    """
    payload: dict = {
        "export_uuid": str(new_uuid()),
        "project_uuid": str(project_uuid),
        "revision_snapshot": [str(u) for u in revision_snapshot],
        "active_decision_event_uuids": [],
        "gate_mode": "exportierbar",
        "export_warnings": [],
        "export_attempt_id": str(new_uuid()),
        "filename": "synthetic.docx",
        "format": "docx",
        "sha256": "0" * 64,
        "size_bytes": 0,
    }
    if extra_payload:
        payload.update(extra_payload)
    return await create_po(
        session=session,
        po_type=POType.EXPORT_EVENT,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        payload=payload,
    )


async def seed_segment_export(
    session: AsyncSession,
    *,
    project,
    account_uuid: _uuid.UUID,
    segment: Segment,
) -> ProvenanceObject:
    """Run a real `run_export_job` — used to verify the read layer
    against the actual EXPORT_EVENT shape produced in Sprint 5."""
    run = await start_preflight_run(session=session, project_uuid=project.project_uuid)
    for i in range(1, PFLICHTFRAGE_COUNT + 1):
        await confirm_pflichtfrage(
            session=session,
            project_uuid=project.project_uuid,
            preflight_run_uuid=run.job_uuid,
            frage_index=i,
            frage_key=f"frage_{i}",
            answer={"value": "yes"},
        )
    ev = await evaluate_preflight(
        session=session, project_uuid=project.project_uuid, preflight_run=run
    )
    assert ev.state.value == "exportierbar"
    config = ExportConfig(
        project_uuid=project.project_uuid,
        account_uuid=account_uuid,
        project_title="readout-test",
        current_export_attempt_id=str(new_uuid()),
        preflight_run=run,
    )
    result = await run_export_job(session=session, config=config)
    return result.export_event_po
