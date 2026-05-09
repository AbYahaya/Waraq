"""Release gate endpoints (T-6.1.1).

- GET  /projects/{project_uuid}/release-gate              — evaluate gate
- POST /projects/{project_uuid}/release-gate/confirm-warning — freigabe_mit_warnung DE
- POST /projects/{project_uuid}/release-gate/start-translation — uebersetzungsstart DE
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, HTTPException, status

from waraq.api._ownership import owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import ReleaseGateConfirmRequest, ReleaseGateResponse
from waraq.release_gate import (
    GateNotInWarningState,
    GateNotReady,
    GateState,
    confirm_translation_with_warning,
    evaluate_gate,
    start_translation,
)

router = APIRouter(prefix="/projects/{project_uuid}/release-gate", tags=["release-gate"])


@router.get("", response_model=ReleaseGateResponse)
async def evaluate(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> ReleaseGateResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    result = await evaluate_gate(session=session, project_uuid=project_uuid)
    requires_confirmation = (
        result.state == GateState.BLOCKIERT
        and len(result.blocking_reasons) == 1
        and "freigabe_mit_warnung" in result.blocking_reasons[0]
    )
    return ReleaseGateResponse(
        state=result.state.value,
        blocking_reasons=list(result.blocking_reasons),
        warnings=list(result.warnings),
        requires_confirmation=requires_confirmation,
    )


@router.post("/confirm-warning", status_code=status.HTTP_201_CREATED)
async def confirm_warning(
    project_uuid: _uuid.UUID,
    req: ReleaseGateConfirmRequest,
    session: DbSession,
    current: CurrentAccount,
) -> dict[str, str]:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    try:
        de = await confirm_translation_with_warning(
            session=session,
            project_uuid=project_uuid,
            actor_uuid=current.account_uuid,
            content={"note": req.note} if req.note else None,
        )
    except GateNotInWarningState as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"decision_event_uuid": str(de.decision_event_uuid)}


@router.post("/start-translation", status_code=status.HTTP_201_CREATED)
async def start_translation_decision(
    project_uuid: _uuid.UUID,
    req: ReleaseGateConfirmRequest,
    session: DbSession,
    current: CurrentAccount,
) -> dict[str, str]:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    try:
        de = await start_translation(
            session=session,
            project_uuid=project_uuid,
            actor_uuid=current.account_uuid,
            content={"note": req.note} if req.note else None,
        )
    except GateNotReady as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"decision_event_uuid": str(de.decision_event_uuid)}
