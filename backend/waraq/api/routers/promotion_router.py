"""Promotion endpoints (Stufen 1-2). T-7.3.1.

- POST /projects/{project_uuid}/promotion/observations  — record Stufe 1
- POST /projects/{project_uuid}/promotion/aggregate     — Stufe 1 → 2
- GET  /projects/{project_uuid}/promotion/musterkandidaten — list

No `bestaetige_stilregel` endpoint here: that lives in T-7.3.2 (Sprint 3 / M5)
and is the only path Stufe 2 → bestätigte Stilregel per H-7. This router has
no auto-promotion surface.
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, HTTPException, status

from waraq.api._ownership import owned_project_or_404, owned_segment_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import (
    MusterkandidatResponse,
    PromotionAggregateRequest,
    PromotionObservationCreateRequest,
)
from waraq.promotion import (
    SourceClass,
    aggregate_into_musterkandidaten,
    list_musterkandidaten,
    record_observation,
)
from waraq.schemas import Revision

router = APIRouter(prefix="/projects/{project_uuid}/promotion", tags=["promotion"])


@router.post("/observations", status_code=status.HTTP_201_CREATED)
async def post_observation(
    project_uuid: _uuid.UUID,
    req: PromotionObservationCreateRequest,
    session: DbSession,
    current: CurrentAccount,
) -> dict[str, str]:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    revision: Revision | None = await session.get(Revision, req.revision_uuid)
    if revision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")
    segment = await owned_segment_or_404(session, revision.satz_uuid, current.account_uuid)
    try:
        obs = await record_observation(
            session=session,
            revision=revision,
            segment=segment,
            project_uuid=project_uuid,
            prior_translation=req.prior_translation,
            user_correction=req.user_correction,
            source_text=req.source_text,
            terminology_bindings=dict(req.terminology_bindings)
            if req.terminology_bindings
            else None,
            source_class=SourceClass(req.source_class),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"observation_uuid": str(obs.observation_uuid)}


@router.post("/aggregate", response_model=list[MusterkandidatResponse])
async def aggregate(
    project_uuid: _uuid.UUID,
    req: PromotionAggregateRequest,
    session: DbSession,
    current: CurrentAccount,
) -> list[MusterkandidatResponse]:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    rows = await aggregate_into_musterkandidaten(
        session=session,
        project_uuid=project_uuid,
        threshold=req.threshold,
    )
    return [MusterkandidatResponse.model_validate(r) for r in rows]


@router.get("/musterkandidaten", response_model=list[MusterkandidatResponse])
async def list_kandidaten(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> list[MusterkandidatResponse]:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    rows = await list_musterkandidaten(session=session, project_uuid=project_uuid)
    return [MusterkandidatResponse.model_validate(r) for r in rows]
