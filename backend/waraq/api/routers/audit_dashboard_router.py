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

from waraq.api._ownership import owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.audit_dashboard import (
    AttentionFilter,
    list_attention_segments,
    segment_audit_detail,
    summarize_project,
)

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


# ---------------------------------------------------------------------
# N-2 — segment detail (expandable row payload)
# ---------------------------------------------------------------------


class EngineReadingResponse(BaseModel):
    engine: str
    text: str | None
    text_chars: int
    confidence: float | None
    error_class: str | None


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
    summary = await summarize_project(
        session=session, project_uuid=project.project_uuid
    )
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
            )
            for e in detail.ocr_engines
        ],
        ocr_engines_have_text=detail.ocr_engines_have_text,
        translation_situation=detail.translation_situation,
        translation_target_text=detail.translation_target_text,
        translation_primary_engine=detail.translation_primary_engine,
        translation_check_engine=detail.translation_check_engine,
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
