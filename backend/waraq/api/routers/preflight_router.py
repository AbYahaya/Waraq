"""M5 closeout — Preflight HTTP endpoints.

Wraps `waraq.preflight` so the M4 UI can drive the four canonical
Pflichtfragen + final evaluation entirely through HTTP.

Flow expected by the UI:
1. POST /projects/{uuid}/preflight/runs                        — open run
2. POST /projects/{uuid}/preflight/runs/{run_uuid}/pflichtfragen
   (×4, one per frage_index 1..4)
3. POST /projects/{uuid}/preflight/runs/{run_uuid}/evaluate    — final state

The router is read-only with respect to project state; all writes
happen through the service layer (Decision Events, Log-Einträge,
Job state transitions per the canonical service implementation).
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from waraq.api._ownership import owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.preflight import (
    PFLICHTFRAGE_COUNT,
    PreflightError,
    confirm_pflichtfrage,
    evaluate_preflight,
    start_preflight_run,
)
from waraq.preflight.service import JOB_TYPE as PREFLIGHT_JOB_TYPE
from waraq.schemas import Job

router = APIRouter(tags=["preflight"])


class PreflightRunResponse(BaseModel):
    run_uuid: _uuid.UUID
    state: str


class PflichtfrageConfirmRequest(BaseModel):
    frage_index: int = Field(ge=1, le=PFLICHTFRAGE_COUNT)
    frage_key: str = Field(min_length=1, max_length=128)
    answer: dict[str, Any] = Field(default_factory=dict)


class PflichtfrageConfirmResponse(BaseModel):
    decision_event_uuid: _uuid.UUID
    frage_index: int


class PreflightEvaluateResponse(BaseModel):
    run_uuid: _uuid.UUID
    state: str
    blocking_reasons: list[str]
    open_warning_slots: list[str]
    konfigurationsschicht_complete: bool
    pflichtfrage_active_count: int
    p_03_kritisch_befund_uuids: list[_uuid.UUID]
    p_04_hoch_befund_uuids: list[_uuid.UUID]
    w_01_mittel_befund_uuids: list[_uuid.UUID]
    w_02_konsistenz_befund_uuids: list[_uuid.UUID]
    w_03_formatvorlagen_finding_keys: list[str]
    hadith_h2_status_uuids: list[_uuid.UUID]
    hadith_h1_status_uuids: list[_uuid.UUID]


async def _resolve_run_or_404(
    *, session: DbSession, project_uuid: _uuid.UUID, run_uuid: _uuid.UUID
) -> Job:
    job: Job | None = await session.get(Job, run_uuid)
    if job is None or job.job_type != PREFLIGHT_JOB_TYPE or job.project_uuid != project_uuid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preflight run not found")
    return job


@router.post(
    "/projects/{project_uuid}/preflight/runs",
    response_model=PreflightRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def open_preflight_run(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> PreflightRunResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    job = await start_preflight_run(session=session, project_uuid=project_uuid)
    return PreflightRunResponse(run_uuid=job.job_uuid, state=job.state)


@router.post(
    "/projects/{project_uuid}/preflight/runs/{run_uuid}/pflichtfragen",
    response_model=PflichtfrageConfirmResponse,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_one_pflichtfrage(
    project_uuid: _uuid.UUID,
    run_uuid: _uuid.UUID,
    req: PflichtfrageConfirmRequest,
    session: DbSession,
    current: CurrentAccount,
) -> PflichtfrageConfirmResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    await _resolve_run_or_404(session=session, project_uuid=project_uuid, run_uuid=run_uuid)
    try:
        de = await confirm_pflichtfrage(
            session=session,
            project_uuid=project_uuid,
            preflight_run_uuid=run_uuid,
            frage_index=req.frage_index,
            frage_key=req.frage_key,
            answer=req.answer,
            actor_uuid=current.account_uuid,
        )
    except PreflightError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PflichtfrageConfirmResponse(
        decision_event_uuid=de.decision_event_uuid, frage_index=req.frage_index
    )


@router.post(
    "/projects/{project_uuid}/preflight/runs/{run_uuid}/evaluate",
    response_model=PreflightEvaluateResponse,
)
async def evaluate_preflight_run(
    project_uuid: _uuid.UUID,
    run_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> PreflightEvaluateResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    job = await _resolve_run_or_404(session=session, project_uuid=project_uuid, run_uuid=run_uuid)
    evaluation = await evaluate_preflight(
        session=session, project_uuid=project_uuid, preflight_run=job
    )
    return PreflightEvaluateResponse(
        run_uuid=run_uuid,
        state=evaluation.state.value,
        blocking_reasons=[r.value for r in evaluation.blocking_reasons],
        open_warning_slots=[s.value for s in evaluation.open_warning_slots],
        konfigurationsschicht_complete=evaluation.konfigurationsschicht_complete,
        pflichtfrage_active_count=evaluation.pflichtfrage_active_count,
        p_03_kritisch_befund_uuids=list(evaluation.p_03_kritisch_befund_uuids),
        p_04_hoch_befund_uuids=list(evaluation.p_04_hoch_befund_uuids),
        w_01_mittel_befund_uuids=list(evaluation.w_01_mittel_befund_uuids),
        w_02_konsistenz_befund_uuids=list(evaluation.w_02_konsistenz_befund_uuids),
        w_03_formatvorlagen_finding_keys=list(evaluation.w_03_formatvorlagen_finding_keys),
        hadith_h2_status_uuids=list(evaluation.hadith_h2_status_uuids),
        hadith_h1_status_uuids=list(evaluation.hadith_h1_status_uuids),
    )
