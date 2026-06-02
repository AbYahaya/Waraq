"""Phase 3 sub-batch E — TOC HTTP endpoints (§2.1 Phase 4 UX rows).

Endpoints:
- GET  /projects/{project_uuid}/toc           — auto-detected TOC + fallback marker
- PUT  /toc/entries/{satz_uuid}               — edit AR and/or DE heading text
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from waraq.api._ownership import owned_project_or_404, owned_segment_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.canon_rules import apply_all as apply_canon_rules
from waraq.invariant.exceptions import H1H2Violation
from waraq.notifications.events import notify_project_event, project_workspace_url
from waraq.toc import (
    confirm_toc_final_review,
    confirm_toc_translated_review,
    detect_toc,
    edit_toc_entry_heading,
    record_toc_entry_decision,
    record_toc_export_settings,
    record_toc_line_decision,
    record_toc_redetect_request,
    record_toc_source_decision,
)

router = APIRouter(tags=["toc"])


class TocEntryDto(BaseModel):
    page_index: int
    page_uuid: _uuid.UUID
    level: int
    ar_text: str
    de_text: str
    satz_uuid: _uuid.UUID | None
    block_uuid: _uuid.UUID | None
    line_key: str
    target_page_index: int | None
    target_page_uuid: _uuid.UUID | None
    status: str
    is_toc_entry: bool
    manual: bool
    protected: bool
    target_heading: str | None


class TocOcrLineDto(BaseModel):
    line_key: str
    page_index: int
    page_uuid: _uuid.UUID
    line_no: int
    text: str
    is_toc_entry: bool
    manual: bool
    protected: bool
    satz_uuid: _uuid.UUID | None
    block_uuid: _uuid.UUID | None
    source_kind: str


class TocSourceCandidateDto(BaseModel):
    page_index: int
    page_uuid: _uuid.UUID
    score: float
    reason: str
    selected: bool


class TocResponse(BaseModel):
    entries: list[TocEntryDto]
    ocr_lines: list[TocOcrLineDto]
    fallback_kind: str
    detected_heading_count: int
    page_count: int
    workflow_state: str
    requires_attention: bool
    attention_reasons: list[str]
    confirmation_state: str
    confirmed_at: str | None
    confirmed_by_decision_event_uuid: _uuid.UUID | None
    export_settings_summary: dict[str, str | int | bool]
    source_candidates: list[TocSourceCandidateDto]
    selected_source_page_indices: list[int]
    source_selection_state: str
    translated_review_required: bool
    translated_review_state: str
    translated_review_confirmed_at: str | None


@router.get("/projects/{project_uuid}/toc", response_model=TocResponse)
async def get_project_toc(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> TocResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    result = await detect_toc(session=session, project_uuid=project_uuid)
    return TocResponse(
        entries=[
            TocEntryDto(
                page_index=e.page_index,
                page_uuid=e.page_uuid,
                level=e.level,
                ar_text=e.ar_text,
                de_text=e.de_text,
                satz_uuid=e.satz_uuid,
                block_uuid=e.block_uuid,
                line_key=e.line_key,
                target_page_index=e.target_page_index,
                target_page_uuid=e.target_page_uuid,
                status=e.status,
                is_toc_entry=e.is_toc_entry,
                manual=e.manual,
                protected=e.protected,
                target_heading=e.target_heading,
            )
            for e in result.entries
        ],
        ocr_lines=[
            TocOcrLineDto(
                line_key=line.line_key,
                page_index=line.page_index,
                page_uuid=line.page_uuid,
                line_no=line.line_no,
                text=line.text,
                is_toc_entry=line.is_toc_entry,
                manual=line.manual,
                protected=line.protected,
                satz_uuid=line.satz_uuid,
                block_uuid=line.block_uuid,
                source_kind=line.source_kind,
            )
            for line in result.ocr_lines
        ],
        fallback_kind=result.fallback_kind.value,
        detected_heading_count=result.detected_heading_count,
        page_count=result.page_count,
        workflow_state=result.workflow_state.value,
        requires_attention=result.requires_attention,
        attention_reasons=result.attention_reasons,
        confirmation_state=result.confirmation_state,
        confirmed_at=result.confirmed_at,
        confirmed_by_decision_event_uuid=result.confirmed_by_decision_event_uuid,
        export_settings_summary=result.export_settings_summary,
        source_candidates=[
            TocSourceCandidateDto(
                page_index=candidate.page_index,
                page_uuid=candidate.page_uuid,
                score=candidate.score,
                reason=candidate.reason,
                selected=candidate.selected,
            )
            for candidate in result.source_candidates
        ],
        selected_source_page_indices=result.selected_source_page_indices,
        source_selection_state=result.source_selection_state,
        translated_review_required=result.translated_review_required,
        translated_review_state=result.translated_review_state,
        translated_review_confirmed_at=result.translated_review_confirmed_at,
    )


class TocConfirmRequest(BaseModel):
    note: str | None = None


class TocSourceDecisionRequest(BaseModel):
    action: str
    page_indices: list[int] = []


class TocConfirmResponse(BaseModel):
    decision_event_uuid: _uuid.UUID
    workflow_state: str


@router.post(
    "/projects/{project_uuid}/toc/translated-review/confirm",
    response_model=TocConfirmResponse,
)
async def confirm_project_translated_toc(
    project_uuid: _uuid.UUID,
    req: TocConfirmRequest,
    session: DbSession,
    current: CurrentAccount,
) -> TocConfirmResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    decision = await confirm_toc_translated_review(
        session=session,
        project_uuid=project_uuid,
        actor_uuid=current.account_uuid,
        note=req.note,
    )
    result = await detect_toc(session=session, project_uuid=project_uuid)
    return TocConfirmResponse(
        decision_event_uuid=decision.decision_event_uuid,
        workflow_state=result.workflow_state.value,
    )


@router.post(
    "/projects/{project_uuid}/toc/confirm",
    response_model=TocConfirmResponse,
)
async def confirm_project_toc(
    project_uuid: _uuid.UUID,
    req: TocConfirmRequest,
    session: DbSession,
    current: CurrentAccount,
) -> TocConfirmResponse:
    project = await owned_project_or_404(session, project_uuid, current.account_uuid)
    decision = await confirm_toc_final_review(
        session=session,
        project_uuid=project_uuid,
        actor_uuid=current.account_uuid,
        note=req.note,
    )
    result = await detect_toc(session=session, project_uuid=project_uuid)
    await notify_project_event(
        session=session,
        project=project,
        kind="toc_final_review_confirmed",
        severity="success",
        title=f"TOC review confirmed — {project.name}",
        body="The table-of-contents workflow has been confirmed for export.",
        target_url=project_workspace_url(project.project_uuid),
        action_label="Open project",
    )
    return TocConfirmResponse(
        decision_event_uuid=decision.decision_event_uuid,
        workflow_state=result.workflow_state.value,
    )


class TocLineDecisionRequest(BaseModel):
    action: str
    line_key: str
    text: str | None = None
    first_text: str | None = None
    second_text: str | None = None
    new_line_key: str | None = None


class TocDecisionResponse(BaseModel):
    decision_event_uuid: _uuid.UUID
    workflow_state: str


@router.post(
    "/projects/{project_uuid}/toc/source-decision",
    response_model=TocDecisionResponse,
)
async def save_toc_source_decision(
    project_uuid: _uuid.UUID,
    req: TocSourceDecisionRequest,
    session: DbSession,
    current: CurrentAccount,
) -> TocDecisionResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    if req.action not in {"confirm_source_pages", "set_source_pages", "no_toc", "auto"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown TOC source action")
    decision = await record_toc_source_decision(
        session=session,
        project_uuid=project_uuid,
        actor_uuid=current.account_uuid,
        action=req.action,
        page_indices=req.page_indices,
    )
    result = await detect_toc(session=session, project_uuid=project_uuid)
    return TocDecisionResponse(
        decision_event_uuid=decision.decision_event_uuid,
        workflow_state=result.workflow_state.value,
    )


@router.post(
    "/projects/{project_uuid}/toc/line-decision",
    response_model=TocDecisionResponse,
)
async def save_toc_line_decision(
    project_uuid: _uuid.UUID,
    req: TocLineDecisionRequest,
    session: DbSession,
    current: CurrentAccount,
) -> TocDecisionResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    if req.action not in {"correct", "split", "merge_next", "mark_toc", "mark_not_toc"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown TOC line action")
    payload = req.model_dump(exclude={"action", "line_key"}, exclude_none=True)
    decision = await record_toc_line_decision(
        session=session,
        project_uuid=project_uuid,
        actor_uuid=current.account_uuid,
        action=req.action,
        line_key=req.line_key,
        payload=payload,
    )
    result = await detect_toc(session=session, project_uuid=project_uuid)
    return TocDecisionResponse(
        decision_event_uuid=decision.decision_event_uuid,
        workflow_state=result.workflow_state.value,
    )


class TocEntryDecisionRequest(BaseModel):
    action: str
    line_key: str
    level: int | None = None
    ar_text: str | None = None
    de_text: str | None = None
    target_page_index: int | None = None
    target_page_uuid: _uuid.UUID | None = None
    target_heading: str | None = None


@router.post(
    "/projects/{project_uuid}/toc/entry-decision",
    response_model=TocDecisionResponse,
)
async def save_toc_entry_decision(
    project_uuid: _uuid.UUID,
    req: TocEntryDecisionRequest,
    session: DbSession,
    current: CurrentAccount,
) -> TocDecisionResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    if req.action not in {"add_from_source", "confirm_match", "relink_page", "set_level"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown TOC entry action")
    payload = req.model_dump(exclude={"action"}, exclude_none=True)
    decision = await record_toc_entry_decision(
        session=session,
        project_uuid=project_uuid,
        actor_uuid=current.account_uuid,
        action=req.action,
        payload=payload,
    )
    result = await detect_toc(session=session, project_uuid=project_uuid)
    return TocDecisionResponse(
        decision_event_uuid=decision.decision_event_uuid,
        workflow_state=result.workflow_state.value,
    )


class TocExportSettingsRequest(BaseModel):
    toc_position: str
    header_heading_level: int
    chapter_break_heading_level: int
    display_arabic_chapter_headings: bool
    navigation_depth: int


@router.put(
    "/projects/{project_uuid}/toc/export-settings",
    response_model=TocDecisionResponse,
)
async def save_toc_export_settings(
    project_uuid: _uuid.UUID,
    req: TocExportSettingsRequest,
    session: DbSession,
    current: CurrentAccount,
) -> TocDecisionResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    decision = await record_toc_export_settings(
        session=session,
        project_uuid=project_uuid,
        actor_uuid=current.account_uuid,
        settings=req.model_dump(),
    )
    result = await detect_toc(session=session, project_uuid=project_uuid)
    return TocDecisionResponse(
        decision_event_uuid=decision.decision_event_uuid,
        workflow_state=result.workflow_state.value,
    )


@router.post(
    "/projects/{project_uuid}/toc/redetect",
    response_model=TocDecisionResponse,
)
async def redetect_project_toc(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> TocDecisionResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    decision = await record_toc_redetect_request(
        session=session,
        project_uuid=project_uuid,
        actor_uuid=current.account_uuid,
    )
    result = await detect_toc(session=session, project_uuid=project_uuid)
    return TocDecisionResponse(
        decision_event_uuid=decision.decision_event_uuid,
        workflow_state=result.workflow_state.value,
    )


class TocEntryEditRequest(BaseModel):
    ar_text: str | None = None
    de_text: str | None = None


class TocEntryEditResponse(BaseModel):
    rev_uuid: _uuid.UUID
    satz_uuid: _uuid.UUID


@router.put(
    "/toc/entries/{satz_uuid}",
    response_model=TocEntryEditResponse,
)
async def edit_toc_entry(
    satz_uuid: _uuid.UUID,
    req: TocEntryEditRequest,
    session: DbSession,
    current: CurrentAccount,
) -> TocEntryEditResponse:
    """Edit a TOC heading entry's AR and/or DE text.

    §2.2 auto-normalize is applied to both halves before persistence
    (consistent with the manual-edit segment router).
    """
    if req.ar_text is None and req.de_text is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="at least one of ar_text / de_text must be supplied",
        )
    await owned_segment_or_404(session, satz_uuid, current.account_uuid)
    new_ar = apply_canon_rules(req.ar_text) if req.ar_text is not None else None
    new_de = apply_canon_rules(req.de_text) if req.de_text is not None else None
    try:
        rev = await edit_toc_entry_heading(
            session=session,
            satz_uuid=satz_uuid,
            new_ar_text=new_ar,
            new_de_text=new_de,
            actor_uuid=current.account_uuid,
        )
    except H1H2Violation as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Segment is locked ({exc!s})",
        ) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return TocEntryEditResponse(rev_uuid=rev.rev_uuid, satz_uuid=satz_uuid)
