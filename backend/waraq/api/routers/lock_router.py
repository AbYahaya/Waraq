"""Lock endpoints — set / release segment lock_flag.

Set: `level ∈ {manual_local, manual_editorial}`.
Release manual_editorial requires explicit confirmation (a non-empty
ConfirmationContext); release manual_local does not.
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, HTTPException, status

from waraq.api._ownership import owned_segment_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import LockReleaseRequest, LockResponse, LockSetRequest
from waraq.invariant.enums import LockFlag
from waraq.lock import (
    ConfirmationContext,
    LockAlreadyAtTargetState,
    LockConfirmationRequired,
    LockInvalidLevel,
    release_lock,
    set_lock,
)

router = APIRouter(prefix="/segments/{satz_uuid}/lock", tags=["lock"])


@router.post("", response_model=LockResponse, status_code=status.HTTP_201_CREATED)
async def set_segment_lock(
    satz_uuid: _uuid.UUID,
    req: LockSetRequest,
    session: DbSession,
    current: CurrentAccount,
) -> LockResponse:
    segment = await owned_segment_or_404(session, satz_uuid, current.account_uuid)
    try:
        de, _po = await set_lock(
            session=session,
            segment=segment,
            level=LockFlag(req.level),
            actor_uuid=current.account_uuid,
            content={"note": req.note} if req.note else None,
        )
    except LockAlreadyAtTargetState as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except LockInvalidLevel as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LockResponse(
        satz_uuid=segment.satz_uuid,
        lock_flag=segment.lock_flag.value,
        decision_event_uuid=de.decision_event_uuid,
    )


@router.delete("", response_model=LockResponse)
async def release_segment_lock(
    satz_uuid: _uuid.UUID,
    req: LockReleaseRequest,
    session: DbSession,
    current: CurrentAccount,
) -> LockResponse:
    segment = await owned_segment_or_404(session, satz_uuid, current.account_uuid)
    confirmation: ConfirmationContext | None = None
    if segment.lock_flag == LockFlag.MANUAL_EDITORIAL:
        confirmation = ConfirmationContext(
            confirmed_by=current.account_uuid,
            note=req.note or "",
        )
    try:
        de, _po = await release_lock(
            session=session,
            segment=segment,
            confirmation=confirmation,
            actor_uuid=current.account_uuid,
            content={"note": req.note} if req.note else None,
        )
    except LockConfirmationRequired as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except LockAlreadyAtTargetState as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return LockResponse(
        satz_uuid=segment.satz_uuid,
        lock_flag=segment.lock_flag.value,
        decision_event_uuid=de.decision_event_uuid,
    )
