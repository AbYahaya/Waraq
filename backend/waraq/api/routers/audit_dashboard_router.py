"""Sub-batch N — Project audit dashboard HTTP surface.

Two endpoints, both auth-gated and ownership-checked:

  - GET /projects/{project_uuid}/audit/summary
        One-shot summary card — counts/distributions across pages,
        OCR confidence, engine agreement, cross-check situations,
        open Befunde + consistency findings + conflicts.

  - GET /projects/{project_uuid}/audit/attention?filter=...
        Filterable per-segment attention list. Each row carries
        page/block/segment refs + filter-specific detail dict.
        Frontend renders rows with links to the canonical per-segment
        review surfaces (OCR-Review, segment workspace, audit
        resolution UI). NO write paths from this surface — read-only
        per the §2.6 "no new domain concepts" scope decision.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select

from waraq.api._ownership import owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.audit_dashboard import (
    AttentionFilter,
    list_attention_segments,
    list_ocr_review_decisions,
    segment_audit_detail,
    summarize_project,
)
from waraq.decisions import create_decision_event
from waraq.ocr.diff_explainer import (
    OcrDifferenceExplainerError,
    OcrDifferenceExplainerUnconfigured,
    explain_ocr_difference_with_openai,
)
from waraq.schemas import Block, Page, Segment
from waraq.schemas.enums import DecisionSource, ScopeType

router = APIRouter(prefix="/projects", tags=["audit-dashboard"])


# ---------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------


class OcrStatusDistributionResponse(BaseModel):
    ausstehend: int
    in_review: int
    go: int
    go_with_warning: int
    no_go: int


class ConfidenceDistributionResponse(BaseModel):
    accepted: int
    deficient: int
    critical: int
    unknown_or_unscored: int
    no_ocr: int


class EngineAgreementDistributionResponse(BaseModel):
    exact_match: int
    skeleton_equal: int
    divergent: int
    single_engine: int
    engine_error: int
    none_recorded: int


class CrossCheckDistributionResponse(BaseModel):
    agreement: int
    auto_correction: int
    substantive_deviation: int
    ambiguity: int
    check_failed: int
    not_translated: int


class BefundDistributionResponse(BaseModel):
    kritisch: int
    hoch: int
    mittel: int


class ProjectAuditSummaryResponse(BaseModel):
    project_uuid: _uuid.UUID
    total_pages: int
    total_segments: int
    page_ocr_status: OcrStatusDistributionResponse
    ocr_confidence: ConfidenceDistributionResponse
    engine_agreement: EngineAgreementDistributionResponse
    cross_check: CrossCheckDistributionResponse
    open_befunde: BefundDistributionResponse
    open_konsistenz_befunde: int
    open_conflicts: int


class AttentionItemResponse(BaseModel):
    project_uuid: _uuid.UUID
    page_uuid: _uuid.UUID
    page_index: int
    block_uuid: _uuid.UUID
    block_index: int
    satz_uuid: _uuid.UUID
    satz_index: int
    filter_matched: str  # AttentionFilter.value
    detail: dict[str, Any]


class AttentionListResponse(BaseModel):
    items: list[AttentionItemResponse]


class OcrReviewDecisionResponse(BaseModel):
    decision_event_uuid: _uuid.UUID
    page_uuid: _uuid.UUID
    page_index: int
    satz_uuid: _uuid.UUID | None = None
    decision_type: str
    content: dict[str, Any]
    created_at: Any


class OcrReviewDecisionListResponse(BaseModel):
    items: list[OcrReviewDecisionResponse]


class OcrAttentionDecisionRequest(BaseModel):
    action: str
    reason: str | None = None
    filter_matched: str | None = None
    details: dict[str, Any] | None = None


class OcrAttentionDecisionResponse(BaseModel):
    decision_event_uuid: _uuid.UUID
    decision_type: str


class OcrDifferenceExplanationRequest(BaseModel):
    gemini_text: str
    openai_text: str


class OcrDifferenceExplanationResponse(BaseModel):
    provider: str
    model: str
    summary: str
    recommended_reading: str
    confidence: float
    normalization_notes: list[str]
    line_differences: list[dict[str, Any]]
    character_differences: list[dict[str, str]]


# ---------------------------------------------------------------------
# N-2 — segment detail (expandable row payload)
# ---------------------------------------------------------------------


class EngineReadingResponse(BaseModel):
    engine: str
    text: str | None
    text_chars: int
    confidence: float | None
    error_class: str | None
    is_current: bool


class BefundDetailResponse(BaseModel):
    befund_uuid: _uuid.UUID
    regelkennung: str
    schweregrad: str
    verstossklasse: str
    detection_context: dict[str, Any]


class SegmentAuditDetailResponse(BaseModel):
    satz_uuid: _uuid.UUID
    page_index: int
    block_index: int
    satz_index: int
    current_text: str | None
    ocr_engine_agreement: str | None
    ocr_confidence_score: float | None
    ocr_confidence_class: str | None
    ocr_engines: list[EngineReadingResponse]
    ocr_engines_have_text: bool
    translation_situation: str | None
    translation_target_text: str | None
    translation_primary_engine: str | None
    translation_check_engine: str | None
    translation_primary_output: str | None
    translation_check_output: str | None
    translation_check_error: str | None
    open_befunde: list[BefundDetailResponse]
    open_conflicts_count: int


# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------


@router.get(
    "/{project_uuid}/audit/summary",
    response_model=ProjectAuditSummaryResponse,
)
async def get_audit_summary(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> ProjectAuditSummaryResponse:
    project = await owned_project_or_404(session, project_uuid, current.account_uuid)
    summary = await summarize_project(session=session, project_uuid=project.project_uuid)
    return ProjectAuditSummaryResponse(
        project_uuid=summary.project_uuid,
        total_pages=summary.total_pages,
        total_segments=summary.total_segments,
        page_ocr_status=OcrStatusDistributionResponse(
            ausstehend=summary.page_ocr_status.ausstehend,
            in_review=summary.page_ocr_status.in_review,
            go=summary.page_ocr_status.go,
            go_with_warning=summary.page_ocr_status.go_with_warning,
            no_go=summary.page_ocr_status.no_go,
        ),
        ocr_confidence=ConfidenceDistributionResponse(
            accepted=summary.ocr_confidence.accepted,
            deficient=summary.ocr_confidence.deficient,
            critical=summary.ocr_confidence.critical,
            unknown_or_unscored=summary.ocr_confidence.unknown_or_unscored,
            no_ocr=summary.ocr_confidence.no_ocr,
        ),
        engine_agreement=EngineAgreementDistributionResponse(
            exact_match=summary.engine_agreement.exact_match,
            skeleton_equal=summary.engine_agreement.skeleton_equal,
            divergent=summary.engine_agreement.divergent,
            single_engine=summary.engine_agreement.single_engine,
            engine_error=summary.engine_agreement.engine_error,
            none_recorded=summary.engine_agreement.none_recorded,
        ),
        cross_check=CrossCheckDistributionResponse(
            agreement=summary.cross_check.agreement,
            auto_correction=summary.cross_check.auto_correction,
            substantive_deviation=summary.cross_check.substantive_deviation,
            ambiguity=summary.cross_check.ambiguity,
            check_failed=summary.cross_check.check_failed,
            not_translated=summary.cross_check.not_translated,
        ),
        open_befunde=BefundDistributionResponse(
            kritisch=summary.open_befunde.kritisch,
            hoch=summary.open_befunde.hoch,
            mittel=summary.open_befunde.mittel,
        ),
        open_konsistenz_befunde=summary.open_konsistenz_befunde,
        open_conflicts=summary.open_conflicts,
    )


@router.get(
    "/{project_uuid}/audit/attention",
    response_model=AttentionListResponse,
)
async def get_attention_list(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
    filter: list[str] | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> AttentionListResponse:
    project = await owned_project_or_404(session, project_uuid, current.account_uuid)
    parsed: list[AttentionFilter] | None = None
    if filter:
        # Drop unknown filter strings silently (defensive — keeps the
        # endpoint stable against frontend version drift).
        parsed = []
        for raw in filter:
            try:
                parsed.append(AttentionFilter(raw))
            except ValueError:
                continue
        if not parsed:
            parsed = None  # nothing recognized → fall back to "all filters"
    items = await list_attention_segments(
        session=session,
        project_uuid=project.project_uuid,
        filters=parsed,
        limit=limit,
    )
    return AttentionListResponse(
        items=[
            AttentionItemResponse(
                project_uuid=it.project_uuid,
                page_uuid=it.page_uuid,
                page_index=it.page_index,
                block_uuid=it.block_uuid,
                block_index=it.block_index,
                satz_uuid=it.satz_uuid,
                satz_index=it.satz_index,
                filter_matched=it.filter_matched.value,
                detail=it.detail,
            )
            for it in items
        ]
    )


@router.get(
    "/{project_uuid}/audit/ocr-review-decisions",
    response_model=OcrReviewDecisionListResponse,
)
async def get_ocr_review_decisions(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
    limit: int = Query(default=200, ge=1, le=1000),
) -> OcrReviewDecisionListResponse:
    project = await owned_project_or_404(session, project_uuid, current.account_uuid)
    items = await list_ocr_review_decisions(
        session=session,
        project_uuid=project.project_uuid,
        limit=limit,
    )
    return OcrReviewDecisionListResponse(
        items=[
            OcrReviewDecisionResponse(
                decision_event_uuid=it.decision_event_uuid,
                page_uuid=it.page_uuid,
                page_index=it.page_index,
                satz_uuid=it.satz_uuid,
                decision_type=it.decision_type,
                content=it.content,
                created_at=it.created_at,
            )
            for it in items
        ]
    )


@router.post(
    "/{project_uuid}/audit/segments/{satz_uuid}/ocr-attention-decision",
    response_model=OcrAttentionDecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def decide_ocr_attention_item(
    project_uuid: _uuid.UUID,
    satz_uuid: _uuid.UUID,
    req: OcrAttentionDecisionRequest,
    session: DbSession,
    current: CurrentAccount,
) -> OcrAttentionDecisionResponse:
    project = await owned_project_or_404(session, project_uuid, current.account_uuid)
    result = await session.execute(
        select(Segment, Block, Page)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Segment.satz_uuid == satz_uuid)
        .where(Page.project_uuid == project.project_uuid)
        .where(Page.active.is_(True))
        .where(Block.active.is_(True))
        .where(Segment.active.is_(True))
    )
    row = result.first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segment not found in this project",
        )

    action_to_decision = {
        "ignore": "ocr_attention_ignored",
        "delete": "ocr_attention_deleted",
        "mark_unresolved": "ocr_attention_mark_unresolved",
        "supersede": "ocr_attention_superseded_by_rerun",
    }
    decision_type = action_to_decision.get(req.action)
    if decision_type is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="action must be one of: ignore, delete, mark_unresolved, supersede",
        )

    _segment, _block, page = row
    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=satz_uuid,
        decision_type=decision_type,
        decision_source=DecisionSource.OCR_REVIEW,
        actor_uuid=current.account_uuid,
        content={
            "reason": req.reason,
            "filter_matched": req.filter_matched,
            "page_uuid": str(page.page_uuid),
            "page_index": page.page_index,
            "details": req.details or {},
        },
    )
    return OcrAttentionDecisionResponse(
        decision_event_uuid=de.decision_event_uuid,
        decision_type=de.decision_type,
    )


@router.post(
    "/{project_uuid}/audit/segments/{satz_uuid}/ocr-difference-explanation",
    response_model=OcrDifferenceExplanationResponse,
)
async def explain_ocr_difference(
    project_uuid: _uuid.UUID,
    satz_uuid: _uuid.UUID,
    req: OcrDifferenceExplanationRequest,
    session: DbSession,
    current: CurrentAccount,
) -> OcrDifferenceExplanationResponse:
    project = await owned_project_or_404(session, project_uuid, current.account_uuid)
    result = await session.execute(
        select(Segment, Block, Page)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Segment.satz_uuid == satz_uuid)
        .where(Page.project_uuid == project.project_uuid)
        .where(Page.active.is_(True))
        .where(Block.active.is_(True))
        .where(Segment.active.is_(True))
    )
    if result.first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segment not found in this project",
        )
    try:
        explanation = await explain_ocr_difference_with_openai(
            gemini_text=req.gemini_text,
            openai_text=req.openai_text,
        )
    except OcrDifferenceExplainerUnconfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except OcrDifferenceExplainerError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI OCR difference explanation failed: {exc}",
        )
    return OcrDifferenceExplanationResponse(**explanation)


@router.get(
    "/{project_uuid}/audit/segments/{satz_uuid}/detail",
    response_model=SegmentAuditDetailResponse,
)
async def get_segment_detail(
    project_uuid: _uuid.UUID,
    satz_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> SegmentAuditDetailResponse:
    """N-2: per-segment expandable-row detail. Returns the latest OCR-PO
    engines (with per-engine `text` when persisted; legacy OCR-POs
    pre-N-2 carry only `text_chars` → `ocr_engines_have_text=False`),
    Stage-2 agreement label, Stage-3 confidence + class, latest
    cross-check situation + translation target, open Befunde for the
    segment, and open conflict count.

    Ownership check: the segment must live under a project owned by
    `current`. 404 if either constraint fails — same opacity as the
    project endpoint to avoid leaking segment existence.
    """
    project = await owned_project_or_404(session, project_uuid, current.account_uuid)
    detail = await segment_audit_detail(
        session=session,
        project_uuid=project.project_uuid,
        satz_uuid=satz_uuid,
    )
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segment not found in this project",
        )
    return SegmentAuditDetailResponse(
        satz_uuid=detail.satz_uuid,
        page_index=detail.page_index,
        block_index=detail.block_index,
        satz_index=detail.satz_index,
        current_text=detail.current_text,
        ocr_engine_agreement=detail.ocr_engine_agreement,
        ocr_confidence_score=detail.ocr_confidence_score,
        ocr_confidence_class=detail.ocr_confidence_class,
        ocr_engines=[
            EngineReadingResponse(
                engine=e.engine,
                text=e.text,
                text_chars=e.text_chars,
                confidence=e.confidence,
                error_class=e.error_class,
                is_current=e.is_current,
            )
            for e in detail.ocr_engines
        ],
        ocr_engines_have_text=detail.ocr_engines_have_text,
        translation_situation=detail.translation_situation,
        translation_target_text=detail.translation_target_text,
        translation_primary_engine=detail.translation_primary_engine,
        translation_check_engine=detail.translation_check_engine,
        translation_primary_output=detail.translation_primary_output,
        translation_check_output=detail.translation_check_output,
        translation_check_error=detail.translation_check_error,
        open_befunde=[
            BefundDetailResponse(
                befund_uuid=b.befund_uuid,
                regelkennung=b.regelkennung,
                schweregrad=b.schweregrad,
                verstossklasse=b.verstossklasse,
                detection_context=b.detection_context,
            )
            for b in detail.open_befunde
        ],
        open_conflicts_count=detail.open_conflicts_count,
    )
