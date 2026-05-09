"""Glossary endpoints — lookup, list, create, update.

Project-bound entries are scoped to a project owned by the current account.
Account-bound entries are scoped to the current account directly.
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from waraq.api._ownership import owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import (
    GlossaryEntryCreateRequest,
    GlossaryEntryResponse,
    GlossaryEntryUpdateRequest,
    GlossaryLookupRequest,
    GlossaryLookupResponse,
)
from waraq.glossary import (
    NO_ENTRY,
    BindingLevel,
    InvalidBindingScope,
    SurfaceFormAlreadyExists,
    create_entry,
    get_entry,
    lookup,
    update_entry,
)
from waraq.schemas import Concept

router = APIRouter(prefix="/glossary", tags=["glossary"])


@router.post("/lookup", response_model=GlossaryLookupResponse)
async def lookup_entry(
    req: GlossaryLookupRequest,
    session: DbSession,
    current: CurrentAccount,
) -> GlossaryLookupResponse:
    # Enforce ownership: project_uuid must belong to caller; account_uuid
    # must equal caller's account.
    if req.project_uuid is not None:
        await owned_project_or_404(session, req.project_uuid, current.account_uuid)
    if req.account_uuid is not None and req.account_uuid != current.account_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="account_uuid must match the authenticated account",
        )
    try:
        result = await lookup(
            session=session,
            surface_form=req.surface_form,
            project_uuid=req.project_uuid,
            account_uuid=req.account_uuid,
        )
    except InvalidBindingScope as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result is NO_ENTRY:
        return GlossaryLookupResponse(found=False, concept_id=None)
    assert isinstance(result, _uuid.UUID)
    return GlossaryLookupResponse(found=True, concept_id=result)


@router.post("/entries", response_model=GlossaryEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_glossary_entry(
    req: GlossaryEntryCreateRequest,
    session: DbSession,
    current: CurrentAccount,
) -> GlossaryEntryResponse:
    binding = BindingLevel(req.binding_level)
    if binding == BindingLevel.PROJECT:
        if req.project_uuid is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="binding_level='project' requires project_uuid",
            )
        await owned_project_or_404(session, req.project_uuid, current.account_uuid)
        account_uuid_for_create: _uuid.UUID | None = None
        project_uuid_for_create: _uuid.UUID | None = req.project_uuid
    else:
        # account binding
        target_account = req.account_uuid or current.account_uuid
        if target_account != current.account_uuid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="account_uuid must match the authenticated account",
            )
        account_uuid_for_create = current.account_uuid
        project_uuid_for_create = None

    try:
        concept, _de = await create_entry(
            session=session,
            canonical_label=req.canonical_label,
            language=req.language,
            binding_level=binding,
            project_uuid=project_uuid_for_create,
            account_uuid=account_uuid_for_create,
            gloss=req.gloss,
            actor_uuid=current.account_uuid,
        )
    except SurfaceFormAlreadyExists as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidBindingScope as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return GlossaryEntryResponse.model_validate(concept)


@router.patch("/entries/{concept_id}", response_model=GlossaryEntryResponse)
async def update_glossary_entry(
    concept_id: _uuid.UUID,
    req: GlossaryEntryUpdateRequest,
    session: DbSession,
    current: CurrentAccount,
) -> GlossaryEntryResponse:
    concept = await get_entry(session=session, concept_id=concept_id)
    if concept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")
    # Ownership: project-bound → owner of project; account-bound → owner of account
    if concept.binding_level == BindingLevel.PROJECT.value:
        assert concept.project_uuid is not None
        await owned_project_or_404(session, concept.project_uuid, current.account_uuid)
    else:
        if concept.account_uuid != current.account_uuid:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")

    if req.canonical_label is None and req.gloss is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of canonical_label / gloss must be provided",
        )
    try:
        await update_entry(
            session=session,
            concept=concept,
            canonical_label=req.canonical_label,
            gloss=req.gloss,
            actor_uuid=current.account_uuid,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return GlossaryEntryResponse.model_validate(concept)


@router.get("/entries", response_model=list[GlossaryEntryResponse])
async def list_glossary_entries(
    session: DbSession,
    current: CurrentAccount,
    project_uuid: _uuid.UUID | None = None,
) -> list[GlossaryEntryResponse]:
    """List entries visible to the caller. Defaults to account-bound entries
    for the caller; pass `project_uuid` to add project-bound entries for
    that project."""
    if project_uuid is not None:
        await owned_project_or_404(session, project_uuid, current.account_uuid)

    stmt = select(Concept).where(Concept.active.is_(True))
    if project_uuid is not None:
        from sqlalchemy import and_, or_

        stmt = stmt.where(
            or_(
                and_(
                    Concept.binding_level == BindingLevel.PROJECT.value,
                    Concept.project_uuid == project_uuid,
                ),
                and_(
                    Concept.binding_level == BindingLevel.ACCOUNT.value,
                    Concept.account_uuid == current.account_uuid,
                ),
            )
        )
    else:
        stmt = stmt.where(
            Concept.binding_level == BindingLevel.ACCOUNT.value,
            Concept.account_uuid == current.account_uuid,
        )
    result = await session.execute(stmt)
    return [GlossaryEntryResponse.model_validate(c) for c in result.scalars()]
