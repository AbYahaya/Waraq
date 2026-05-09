"""Conflict endpoints — list open conflicts and resolve via the three paths.

Per Sprint 1 §2 / DBB Abkürzung 6: glossary never wins silently against
locked Segment — applying glossary to a locked segment goes through
`detect_conflict` and then must be resolved by user via one of three
paths. The detection happens in the rule_binding flow; this router
exposes the resolution surface.
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.api._ownership import (
    owned_page_or_404,
    owned_project_or_404,
    owned_segment_or_404,
)
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import ConflictResolveRequest, ConflictResponse
from waraq.conflicts import (
    ConflictAlreadyResolved,
    ConflictResolutionPathInvalid,
    get_open_conflicts_for_page,
    get_open_conflicts_for_project,
    get_open_conflicts_for_segment,
    resolve_with_glossary_change,
    resolve_with_local_exception,
    resolve_with_lock_release,
)
from waraq.lock import ConfirmationContext, LockConfirmationRequired
from waraq.schemas import ConflictInstance, Segment

router = APIRouter(tags=["conflicts"])


async def _owned_conflict_or_404(
    session: AsyncSession,
    conflict_uuid: _uuid.UUID,
    account_uuid: _uuid.UUID,
) -> ConflictInstance:
    conflict: ConflictInstance | None = await session.get(ConflictInstance, conflict_uuid)
    if conflict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found")
    # Ownership: walk up via segment.
    await owned_segment_or_404(session, conflict.satz_uuid, account_uuid)
    return conflict


@router.get("/segments/{satz_uuid}/conflicts", response_model=list[ConflictResponse])
async def list_segment_conflicts(
    satz_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> list[ConflictResponse]:
    await owned_segment_or_404(session, satz_uuid, current.account_uuid)
    rows = await get_open_conflicts_for_segment(session=session, satz_uuid=satz_uuid)
    return [ConflictResponse.model_validate(c) for c in rows]


@router.get("/pages/{page_uuid}/conflicts", response_model=list[ConflictResponse])
async def list_page_conflicts(
    page_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> list[ConflictResponse]:
    await owned_page_or_404(session, page_uuid, current.account_uuid)
    rows = await get_open_conflicts_for_page(session=session, page_uuid=page_uuid)
    return [ConflictResponse.model_validate(c) for c in rows]


@router.get("/projects/{project_uuid}/conflicts", response_model=list[ConflictResponse])
async def list_project_conflicts(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> list[ConflictResponse]:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    rows = await get_open_conflicts_for_project(session=session, project_uuid=project_uuid)
    return [ConflictResponse.model_validate(c) for c in rows]


@router.post("/conflicts/{conflict_uuid}/resolve/local-exception", response_model=ConflictResponse)
async def resolve_local_exception(
    conflict_uuid: _uuid.UUID,
    req: ConflictResolveRequest,
    session: DbSession,
    current: CurrentAccount,
) -> ConflictResponse:
    conflict = await _owned_conflict_or_404(session, conflict_uuid, current.account_uuid)
    try:
        await resolve_with_local_exception(
            session=session,
            conflict=conflict,
            actor_uuid=current.account_uuid,
            content={"note": req.note} if req.note else None,
        )
    except ConflictAlreadyResolved as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ConflictResponse.model_validate(conflict)


class _GlossaryChangeBody(ConflictResolveRequest):
    """Body for the glossar_anpassen path."""

    new_concept_id: _uuid.UUID


@router.post("/conflicts/{conflict_uuid}/resolve/glossary-change", response_model=ConflictResponse)
async def resolve_glossary_change(
    conflict_uuid: _uuid.UUID,
    req: _GlossaryChangeBody,
    session: DbSession,
    current: CurrentAccount,
) -> ConflictResponse:
    conflict = await _owned_conflict_or_404(session, conflict_uuid, current.account_uuid)
    try:
        await resolve_with_glossary_change(
            session=session,
            conflict=conflict,
            new_concept_id=req.new_concept_id,
            actor_uuid=current.account_uuid,
            content={"note": req.note} if req.note else None,
        )
    except ConflictAlreadyResolved as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ConflictResponse.model_validate(conflict)


@router.post("/conflicts/{conflict_uuid}/resolve/lock-release", response_model=ConflictResponse)
async def resolve_lock_release(
    conflict_uuid: _uuid.UUID,
    req: ConflictResolveRequest,
    session: DbSession,
    current: CurrentAccount,
) -> ConflictResponse:
    conflict = await _owned_conflict_or_404(session, conflict_uuid, current.account_uuid)
    segment: Segment | None = await session.get(Segment, conflict.satz_uuid)
    if segment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    confirmation = ConfirmationContext(
        confirmed_by=current.account_uuid,
        note=req.confirmation_note or "",
    )
    try:
        await resolve_with_lock_release(
            session=session,
            conflict=conflict,
            segment=segment,
            confirmation=confirmation,
            actor_uuid=current.account_uuid,
            content={"note": req.note} if req.note else None,
        )
    except LockConfirmationRequired as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ConflictResolutionPathInvalid as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ConflictAlreadyResolved as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ConflictResponse.model_validate(conflict)
