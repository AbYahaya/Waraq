"""Phase 3 sub-batch D — review-side HTTP endpoints.

Endpoints:
- GET /pages/{page_uuid}/difficulty                 — per-page difficulty report
- GET /projects/{project_uuid}/difficulty           — project-aggregate difficulty
- GET /projects/{project_uuid}/guided-review/queue  — guided review queue

Read-only — these surface aggregations for the UI's difficulty-report
panel + guided-review walker. Resolution flows through the existing
per-finding services.
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel

from waraq.api._ownership import owned_page_or_404, owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.difficulty import (
    compute_page_difficulty,
    compute_project_difficulty,
)
from waraq.guided_review import build_review_queue

router = APIRouter(tags=["review"])


class DifficultyBreakdownDto(BaseModel):
    audit_kritisch: int
    audit_hoch: int
    audit_mittel: int
    konsistenz_kritisch: int
    konsistenz_other: int
    hadith_h_2: int
    hadith_h_1: int
    ocr_error_kritisch: int
    ocr_error_hoch: int
    ocr_error_mittel: int
    locked_segment_manual_local: int
    locked_segment_manual_editorial: int


class DifficultyReportDto(BaseModel):
    scope: str
    scope_uuid: _uuid.UUID
    score: float
    segment_count: int
    breakdown: DifficultyBreakdownDto


@router.get("/pages/{page_uuid}/difficulty", response_model=DifficultyReportDto)
async def page_difficulty(
    page_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> DifficultyReportDto:
    await owned_page_or_404(session, page_uuid, current.account_uuid)
    rep = await compute_page_difficulty(session=session, page_uuid=page_uuid)
    return DifficultyReportDto(
        scope=rep.scope,
        scope_uuid=rep.scope_uuid,
        score=rep.score,
        segment_count=rep.segment_count,
        breakdown=DifficultyBreakdownDto(**asdict(rep.breakdown)),
    )


@router.get("/projects/{project_uuid}/difficulty", response_model=DifficultyReportDto)
async def project_difficulty(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> DifficultyReportDto:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    rep = await compute_project_difficulty(session=session, project_uuid=project_uuid)
    return DifficultyReportDto(
        scope=rep.scope,
        scope_uuid=rep.scope_uuid,
        score=rep.score,
        segment_count=rep.segment_count,
        breakdown=DifficultyBreakdownDto(**asdict(rep.breakdown)),
    )


class GuidedReviewItemDto(BaseModel):
    kind: str
    finding_uuid: _uuid.UUID
    tier: str
    severity: str
    detected_at: str
    satz_uuid: _uuid.UUID | None
    page_uuid: _uuid.UUID | None


class GuidedReviewQueueDto(BaseModel):
    items: list[GuidedReviewItemDto]
    total: int
    by_tier: dict[str, int]


@router.get(
    "/projects/{project_uuid}/guided-review/queue",
    response_model=GuidedReviewQueueDto,
)
async def guided_review_queue(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> GuidedReviewQueueDto:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    queue = await build_review_queue(session=session, project_uuid=project_uuid)
    return GuidedReviewQueueDto(
        items=[
            GuidedReviewItemDto(
                kind=it.kind.value,
                finding_uuid=it.finding_uuid,
                tier=it.tier.value,
                severity=it.severity,
                detected_at=it.detected_at.isoformat(),
                satz_uuid=it.satz_uuid,
                page_uuid=it.page_uuid,
            )
            for it in queue.items
        ],
        total=queue.total,
        by_tier=queue.by_tier,
    )
