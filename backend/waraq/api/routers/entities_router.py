"""Entity endpoints — §4.19 reference data CRUD + lookup."""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, or_, select

from waraq.api._ownership import owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import (
    EntityCreateRequest,
    EntityResponse,
    EntityUpdateRequest,
    GlossaryLookupRequest,
    GlossaryLookupResponse,
)
from waraq.entities import (
    NO_ENTITY,
    EntityCategory,
    EntityLabelAlreadyExists,
    InvalidEntityScope,
    create_entity,
    get_entity,
    lookup_entity,
    update_entity,
)
from waraq.glossary import BindingLevel
from waraq.schemas import Entity

router = APIRouter(prefix="/entities", tags=["entities"])


@router.post("/lookup", response_model=GlossaryLookupResponse)
async def lookup_an_entity(
    req: GlossaryLookupRequest,
    session: DbSession,
    current: CurrentAccount,
) -> GlossaryLookupResponse:
    if req.project_uuid is not None:
        await owned_project_or_404(session, req.project_uuid, current.account_uuid)
    if req.account_uuid is not None and req.account_uuid != current.account_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="account_uuid must match the authenticated account",
        )
    try:
        result = await lookup_entity(
            session=session,
            surface_form=req.surface_form,
            project_uuid=req.project_uuid,
            account_uuid=req.account_uuid,
        )
    except InvalidEntityScope as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result is NO_ENTITY:
        return GlossaryLookupResponse(found=False, concept_id=None)
    assert isinstance(result, _uuid.UUID)
    return GlossaryLookupResponse(found=True, concept_id=result)


@router.post("", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
async def create_an_entity(
    req: EntityCreateRequest,
    session: DbSession,
    current: CurrentAccount,
) -> EntityResponse:
    binding = BindingLevel(req.binding_level)
    category = EntityCategory(req.category)
    if binding == BindingLevel.PROJECT:
        if req.project_uuid is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="binding_level='project' requires project_uuid",
            )
        await owned_project_or_404(session, req.project_uuid, current.account_uuid)
        project_uuid_for_create: _uuid.UUID | None = req.project_uuid
        account_uuid_for_create: _uuid.UUID | None = None
    else:
        target = req.account_uuid or current.account_uuid
        if target != current.account_uuid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="account_uuid must match the authenticated account",
            )
        project_uuid_for_create = None
        account_uuid_for_create = current.account_uuid
    try:
        entity, _de = await create_entity(
            session=session,
            category=category,
            canonical_label=req.canonical_label,
            language=req.language,
            binding_level=binding,
            project_uuid=project_uuid_for_create,
            account_uuid=account_uuid_for_create,
            short_bio=req.short_bio,
            actor_uuid=current.account_uuid,
        )
    except EntityLabelAlreadyExists as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidEntityScope as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return EntityResponse.model_validate(entity)


@router.patch("/{entity_id}", response_model=EntityResponse)
async def update_an_entity(
    entity_id: _uuid.UUID,
    req: EntityUpdateRequest,
    session: DbSession,
    current: CurrentAccount,
) -> EntityResponse:
    entity = await get_entity(session=session, entity_id=entity_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    if entity.binding_level == BindingLevel.PROJECT.value:
        assert entity.project_uuid is not None
        await owned_project_or_404(session, entity.project_uuid, current.account_uuid)
    else:
        if entity.account_uuid != current.account_uuid:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    if req.canonical_label is None and req.short_bio is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of canonical_label / short_bio must be provided",
        )
    try:
        await update_entity(
            session=session,
            entity=entity,
            canonical_label=req.canonical_label,
            short_bio=req.short_bio,
            actor_uuid=current.account_uuid,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return EntityResponse.model_validate(entity)


@router.get("", response_model=list[EntityResponse])
async def list_entities(
    session: DbSession,
    current: CurrentAccount,
    project_uuid: _uuid.UUID | None = Query(default=None),
    category: str | None = Query(default=None),
) -> list[EntityResponse]:
    if project_uuid is not None:
        await owned_project_or_404(session, project_uuid, current.account_uuid)
    stmt = select(Entity).where(Entity.active.is_(True))
    if project_uuid is not None:
        stmt = stmt.where(
            or_(
                and_(
                    Entity.binding_level == BindingLevel.PROJECT.value,
                    Entity.project_uuid == project_uuid,
                ),
                and_(
                    Entity.binding_level == BindingLevel.ACCOUNT.value,
                    Entity.account_uuid == current.account_uuid,
                ),
            )
        )
    else:
        stmt = stmt.where(
            Entity.binding_level == BindingLevel.ACCOUNT.value,
            Entity.account_uuid == current.account_uuid,
        )
    if category is not None:
        stmt = stmt.where(Entity.category == category)
    result = await session.execute(stmt)
    return [EntityResponse.model_validate(e) for e in result.scalars()]
