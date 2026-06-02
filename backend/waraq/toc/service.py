"""TOC detection + edit service — see module docstring for canonical scope."""

from __future__ import annotations

import uuid as _uuid
import re
from dataclasses import dataclass, field
from enum import StrEnum
from difflib import SequenceMatcher
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.decisions import create_decision_event
from waraq.invariant.enums import OperationMode
from waraq.revision.service import create_revision
from waraq.schemas import Block, DecisionEvent, Page, Revision, Segment
from waraq.schemas.enums import ChangeSource, DecisionSource, ScopeType
from waraq.text_state import (
    join_source_target_text,
    resolve_segment_text_state,
)

# Per `waraq.ocr_export.docx_builder._BLOCK_TYPE_STYLE`:
#   UE → Heading 1, HD → Heading 2.
# These two are the v1.0 TOC-relevant block types. The other block
# types (main_text / MT / FN / QR / RN) are not chapter-marker
# candidates.
HEADING_BLOCK_TYPES: Final[dict[str, int]] = {
    "UE": 1,
    "HD": 2,
}


class TocFallbackKind(StrEnum):
    """Why the TocResult uses fallback entries instead of detected ones."""

    NONE = "none"  # Headings detected — entries are real.
    SOURCE_PAGES = "source_pages"  # Entries parsed from confirmed/detected TOC source pages.
    PAGE_BY_PAGE = "page_by_page"  # No headings; canonical §2.1 fallback.


class TocWorkflowState(StrEnum):
    """UI-facing TOC workflow state."""

    NO_PAGES = "no_pages"
    NO_TOC_DETECTED = "no_toc_detected"
    TOC_DETECTED = "toc_detected"
    TOC_REQUIRES_ATTENTION = "toc_requires_attention"
    FINAL_REVIEW_CONFIRMED = "final_review_confirmed"


@dataclass(slots=True)
class TocEntry:
    """One row in the TOC.

    `level` is 1 (UE) or 2 (HD) for detected entries; 1 for fallback
    page-by-page entries.

    `satz_uuid` and `block_uuid` are None when the entry is a fallback
    (no segment exists to attach the heading to). When the entry IS a
    real heading segment, both are populated and the resolver UI uses
    them to dispatch heading edits to the right `create_revision`
    target.

    `ar_text` / `de_text` are the AR-source + DE-translation halves of
    the segment's `text_content` (split on the `\\n---\\n` separator).
    Either may be empty when the segment hasn't been translated yet.
    """

    page_index: int
    page_uuid: _uuid.UUID
    level: int
    ar_text: str
    de_text: str
    satz_uuid: _uuid.UUID | None = None
    block_uuid: _uuid.UUID | None = None
    line_key: str = ""
    target_page_index: int | None = None
    target_page_uuid: _uuid.UUID | None = None
    status: str = "verify"
    is_toc_entry: bool = True
    manual: bool = False
    protected: bool = False
    target_heading: str | None = None


@dataclass(slots=True)
class TocOcrLine:
    """Reviewable source OCR line used by the TOC review station."""

    line_key: str
    page_index: int
    page_uuid: _uuid.UUID
    line_no: int
    text: str
    is_toc_entry: bool
    manual: bool = False
    protected: bool = False
    satz_uuid: _uuid.UUID | None = None
    block_uuid: _uuid.UUID | None = None
    source_kind: str = "detected_heading"


@dataclass(slots=True)
class TocSourceCandidate:
    page_index: int
    page_uuid: _uuid.UUID
    score: float
    reason: str
    selected: bool = False


@dataclass(slots=True)
class TocResult:
    """Project-wide TOC + fallback marker."""

    entries: list[TocEntry]
    fallback_kind: TocFallbackKind
    ocr_lines: list[TocOcrLine] = field(default_factory=list)
    detected_heading_count: int = 0
    page_count: int = 0
    workflow_state: TocWorkflowState = TocWorkflowState.NO_PAGES
    requires_attention: bool = False
    attention_reasons: list[str] = field(default_factory=list)
    confirmation_state: str = "unconfirmed"
    confirmed_at: str | None = None
    confirmed_by_decision_event_uuid: _uuid.UUID | None = None
    export_settings_summary: dict[str, str | int | bool] = field(default_factory=dict)
    source_candidates: list[TocSourceCandidate] = field(default_factory=list)
    selected_source_page_indices: list[int] = field(default_factory=list)
    source_selection_state: str = "auto"
    translated_review_required: bool = False
    translated_review_state: str = "not_required"
    translated_review_confirmed_at: str | None = None


async def detect_toc(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> TocResult:
    """Build the project TOC by scanning heading-typed blocks.

    No-headings → canonical §2.1 fallback (one entry per active page).
    """
    result = await session.execute(
        select(Page, Block, Segment)
        .join(Block, Block.page_uuid == Page.page_uuid)
        .join(Segment, Segment.block_uuid == Block.block_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(Page.active.is_(True))
        .where(Segment.active.is_(True))
        .where(Block.block_type.in_(list(HEADING_BLOCK_TYPES.keys())))
        .order_by(Page.page_index.asc(), Block.block_index.asc(), Segment.satz_index.asc())
    )
    rows = list(result.all())

    page_count_q = await session.execute(
        select(Page)
        .where(Page.project_uuid == project_uuid)
        .where(Page.active.is_(True))
        .order_by(Page.page_index.asc())
    )
    pages: list[Page] = list(page_count_q.scalars())

    export_settings = await _latest_export_settings_summary(
        session=session, project_uuid=project_uuid
    )

    heading_entries = await _heading_entries_from_rows(session=session, rows=rows)
    page_texts = await _page_texts(session=session, pages=pages)
    source_decision = await _latest_toc_source_decision(
        session=session, project_uuid=project_uuid
    )
    source_mode, selected_source_indices = _source_selection_from_decision(source_decision)
    source_candidates = _detect_source_candidates(pages=pages, page_texts=page_texts)
    if source_mode == "auto" and source_candidates:
        selected_source_indices = _contiguous_candidate_range(source_candidates)
    _add_manual_source_candidates(
        candidates=source_candidates,
        pages=pages,
        selected_source_indices=selected_source_indices,
    )
    for candidate in source_candidates:
        candidate.selected = candidate.page_index in selected_source_indices
    has_translation = await _project_has_translation(session=session, project_uuid=project_uuid)

    if selected_source_indices:
        entries, ocr_lines = _entries_from_source_pages(
            pages=pages,
            page_texts=page_texts,
            source_page_indices=selected_source_indices,
            heading_entries=heading_entries,
        )
        entries, ocr_lines = await _apply_toc_review_decisions(
            session=session,
            project_uuid=project_uuid,
            entries=entries,
            ocr_lines=ocr_lines,
        )
        visible_entries = [entry for entry in entries if entry.is_toc_entry]
        attention_reasons = _attention_reasons(visible_entries)
        confirmation = await _latest_toc_confirmation(
            session=session, project_uuid=project_uuid
        )
        confirmed = _confirmation_applies(
            confirmation,
            fallback_kind=TocFallbackKind.SOURCE_PAGES,
            detected_heading_count=len(visible_entries),
            page_count=len(pages),
            attention_reasons=attention_reasons,
        )
        translated_required = has_translation and bool(visible_entries)
        translated_confirmation = await _latest_translated_toc_confirmation(
            session=session, project_uuid=project_uuid
        )
        translated_confirmed = _confirmation_applies(
            translated_confirmation,
            fallback_kind=TocFallbackKind.SOURCE_PAGES,
            detected_heading_count=len(visible_entries),
            page_count=len(pages),
            attention_reasons=attention_reasons,
        )
        return TocResult(
            entries=visible_entries,
            ocr_lines=ocr_lines,
            fallback_kind=TocFallbackKind.SOURCE_PAGES,
            detected_heading_count=len(visible_entries),
            page_count=len(pages),
            workflow_state=(
                TocWorkflowState.FINAL_REVIEW_CONFIRMED
                if confirmed
                else (
                    TocWorkflowState.TOC_REQUIRES_ATTENTION
                    if attention_reasons
                    else TocWorkflowState.TOC_DETECTED
                )
            ),
            requires_attention=bool(attention_reasons),
            attention_reasons=attention_reasons,
            confirmation_state="confirmed" if confirmed else "unconfirmed",
            confirmed_at=(
                confirmation.created_at.isoformat()
                if confirmed and confirmation and confirmation.created_at
                else None
            ),
            confirmed_by_decision_event_uuid=(
                confirmation.decision_event_uuid if confirmed and confirmation else None
            ),
            export_settings_summary=export_settings,
            source_candidates=source_candidates,
            selected_source_page_indices=selected_source_indices,
            source_selection_state=source_mode,
            translated_review_required=translated_required,
            translated_review_state=(
                "not_required"
                if not translated_required
                else "confirmed"
                if translated_confirmed
                else "unconfirmed"
            ),
            translated_review_confirmed_at=(
                translated_confirmation.created_at.isoformat()
                if translated_confirmed and translated_confirmation and translated_confirmation.created_at
                else None
            ),
        )

    if source_mode == "no_toc":
        confirmation = await _latest_toc_confirmation(session=session, project_uuid=project_uuid)
        confirmed = _confirmation_applies(
            confirmation,
            fallback_kind=TocFallbackKind.PAGE_BY_PAGE,
            detected_heading_count=0,
            page_count=len(pages),
            attention_reasons=[],
        )
        return TocResult(
            entries=[],
            ocr_lines=[],
            fallback_kind=TocFallbackKind.PAGE_BY_PAGE,
            detected_heading_count=0,
            page_count=len(pages),
            workflow_state=(
                TocWorkflowState.FINAL_REVIEW_CONFIRMED
                if confirmed
                else TocWorkflowState.NO_TOC_DETECTED
            ),
            requires_attention=False,
            attention_reasons=[],
            confirmation_state="confirmed" if confirmed else "unconfirmed",
            confirmed_at=(
                confirmation.created_at.isoformat()
                if confirmed and confirmation and confirmation.created_at
                else None
            ),
            confirmed_by_decision_event_uuid=(
                confirmation.decision_event_uuid if confirmed and confirmation else None
            ),
            export_settings_summary=export_settings,
            source_candidates=source_candidates,
            selected_source_page_indices=[],
            source_selection_state=source_mode,
            translated_review_required=False,
            translated_review_state="not_required",
        )

    if rows:
        entries = list(heading_entries)
        ocr_lines = _lines_from_entries(entries)
        entries, ocr_lines = await _apply_toc_review_decisions(
            session=session,
            project_uuid=project_uuid,
            entries=entries,
            ocr_lines=ocr_lines,
        )
        visible_entries = [entry for entry in entries if entry.is_toc_entry]
        attention_reasons = _attention_reasons(visible_entries)
        confirmation = await _latest_toc_confirmation(
            session=session, project_uuid=project_uuid
        )
        confirmed = _confirmation_applies(
            confirmation,
            fallback_kind=TocFallbackKind.NONE,
            detected_heading_count=len(visible_entries),
            page_count=len(pages),
            attention_reasons=attention_reasons,
        )
        translated_required = has_translation and bool(visible_entries)
        translated_confirmation = await _latest_translated_toc_confirmation(
            session=session, project_uuid=project_uuid
        )
        translated_confirmed = _confirmation_applies(
            translated_confirmation,
            fallback_kind=TocFallbackKind.NONE,
            detected_heading_count=len(visible_entries),
            page_count=len(pages),
            attention_reasons=attention_reasons,
        )
        return TocResult(
            entries=visible_entries,
            ocr_lines=ocr_lines,
            fallback_kind=TocFallbackKind.NONE,
            detected_heading_count=len(visible_entries),
            page_count=len(pages),
            workflow_state=(
                TocWorkflowState.FINAL_REVIEW_CONFIRMED
                if confirmed
                else (
                    TocWorkflowState.TOC_REQUIRES_ATTENTION
                    if attention_reasons
                    else TocWorkflowState.TOC_DETECTED
                )
            ),
            requires_attention=bool(attention_reasons),
            attention_reasons=attention_reasons,
            confirmation_state="confirmed" if confirmed else "unconfirmed",
            confirmed_at=(
                confirmation.created_at.isoformat()
                if confirmed and confirmation and confirmation.created_at
                else None
            ),
            confirmed_by_decision_event_uuid=(
                confirmation.decision_event_uuid if confirmed and confirmation else None
            ),
            export_settings_summary=export_settings,
            source_candidates=source_candidates,
            selected_source_page_indices=[],
            source_selection_state=source_mode,
            translated_review_required=translated_required,
            translated_review_state=(
                "not_required"
                if not translated_required
                else "confirmed"
                if translated_confirmed
                else "unconfirmed"
            ),
            translated_review_confirmed_at=(
                translated_confirmation.created_at.isoformat()
                if translated_confirmed and translated_confirmation and translated_confirmation.created_at
                else None
            ),
        )

    # Canonical fallback remains available, but it is no longer expanded into
    # one noisy row per page until the user explicitly confirms "No TOC".
    confirmation = await _latest_toc_confirmation(session=session, project_uuid=project_uuid)
    confirmed = _confirmation_applies(
        confirmation,
        fallback_kind=TocFallbackKind.PAGE_BY_PAGE,
        detected_heading_count=0,
        page_count=len(pages),
        attention_reasons=[],
    )
    return TocResult(
        entries=[],
        ocr_lines=[],
        fallback_kind=TocFallbackKind.PAGE_BY_PAGE,
        detected_heading_count=0,
        page_count=len(pages),
        workflow_state=(
            TocWorkflowState.NO_PAGES
            if not pages
            else (
                TocWorkflowState.FINAL_REVIEW_CONFIRMED
                if confirmed
                else TocWorkflowState.NO_TOC_DETECTED
            )
        ),
        requires_attention=False,
        attention_reasons=[],
        confirmation_state="confirmed" if confirmed else "unconfirmed",
        confirmed_at=(
            confirmation.created_at.isoformat()
            if confirmed and confirmation and confirmation.created_at
            else None
        ),
        confirmed_by_decision_event_uuid=(
            confirmation.decision_event_uuid if confirmed and confirmation else None
        ),
        export_settings_summary=export_settings,
        source_candidates=source_candidates,
        selected_source_page_indices=[],
        source_selection_state=source_mode,
        translated_review_required=False,
        translated_review_state="not_required",
    )


async def record_toc_line_decision(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    action: str,
    line_key: str,
    actor_uuid: _uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> DecisionEvent:
    """Persist a source OCR-line decision for the TOC review workflow."""
    content = {"action": action, "line_key": line_key}
    if payload:
        content.update(_json_safe(payload))
    return await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        decision_type="toc_line_decision",
        decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        actor_uuid=actor_uuid,
        content=content,
    )


async def record_toc_entry_decision(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    action: str,
    actor_uuid: _uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> DecisionEvent:
    """Persist a structured TOC-entry decision."""
    content = {"action": action}
    if payload:
        content.update(_json_safe(payload))
    return await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        decision_type="toc_entry_decision",
        decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        actor_uuid=actor_uuid,
        content=content,
    )


async def record_toc_export_settings(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    settings: dict[str, str | int | bool],
    actor_uuid: _uuid.UUID | None = None,
) -> DecisionEvent:
    """Persist TOC/export behavior settings chosen in the TOC review."""
    return await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        decision_type="toc_export_settings_saved",
        decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        actor_uuid=actor_uuid,
        content={"settings": _json_safe(settings)},
    )


async def record_toc_redetect_request(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    actor_uuid: _uuid.UUID | None = None,
) -> DecisionEvent:
    """Record that the reviewer asked to re-run TOC detection."""
    return await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        decision_type="toc_redetect_requested",
        decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        actor_uuid=actor_uuid,
        content={"manual_decisions_preserved": True},
    )


async def record_toc_source_decision(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    action: str,
    page_indices: list[int] | None = None,
    actor_uuid: _uuid.UUID | None = None,
) -> DecisionEvent:
    """Persist the user's TOC source-page choice."""
    return await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        decision_type="toc_source_decision",
        decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        actor_uuid=actor_uuid,
        content={
            "action": action,
            "page_indices": list(page_indices or []),
        },
    )


async def confirm_toc_translated_review(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    actor_uuid: _uuid.UUID | None = None,
    note: str | None = None,
) -> DecisionEvent:
    """Record Phase 6 translated TOC review confirmation."""
    result = await detect_toc(session=session, project_uuid=project_uuid)
    return await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        decision_type="toc_translated_review_confirmed",
        decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        actor_uuid=actor_uuid,
        content={
            "note": note,
            "fallback_kind": result.fallback_kind.value,
            "detected_heading_count": result.detected_heading_count,
            "page_count": result.page_count,
            "attention_reasons": result.attention_reasons,
            "workflow_state_at_confirmation": result.workflow_state.value,
        },
    )


async def toc_structure_blocks_translation(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> str | None:
    result = await detect_toc(session=session, project_uuid=project_uuid)
    if result.workflow_state in {
        TocWorkflowState.TOC_DETECTED,
        TocWorkflowState.TOC_REQUIRES_ATTENTION,
    }:
        return "TOC structural review must be confirmed before translation."
    return None


async def toc_translated_review_blocks_export(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> str | None:
    result = await detect_toc(session=session, project_uuid=project_uuid)
    if result.translated_review_required and result.translated_review_state != "confirmed":
        return "Final translated TOC review must be confirmed before export."
    return None


async def confirm_toc_final_review(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    actor_uuid: _uuid.UUID | None = None,
    note: str | None = None,
) -> DecisionEvent:
    """Record the user's final TOC/fallback review decision."""
    result = await detect_toc(session=session, project_uuid=project_uuid)
    decision = await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        decision_type="toc_final_review_confirmed",
        decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        actor_uuid=actor_uuid,
        content={
            "note": note,
            "fallback_kind": result.fallback_kind.value,
            "detected_heading_count": result.detected_heading_count,
            "page_count": result.page_count,
            "attention_reasons": result.attention_reasons,
            "workflow_state_at_confirmation": result.workflow_state.value,
        },
    )
    return decision


def _attention_reasons(entries: list[TocEntry]) -> list[str]:
    reasons: list[str] = []
    missing_de = [entry for entry in entries if not entry.de_text.strip()]
    missing_ar = [entry for entry in entries if not entry.ar_text.strip()]
    if missing_de:
        reasons.append(f"{len(missing_de)} heading(s) have no translated title yet.")
    if missing_ar:
        reasons.append(f"{len(missing_ar)} heading(s) have no Arabic title.")
    return reasons


def _entry_status(ar_text: str, de_text: str) -> str:
    if not ar_text.strip():
        return "missing"
    if not de_text.strip():
        return "verify"
    return "verified"


async def _heading_entries_from_rows(
    *, session: AsyncSession, rows: list[tuple[Page, Block, Segment]]
) -> list[TocEntry]:
    entries: list[TocEntry] = []
    for page, block, segment in rows:
        text_state = await resolve_segment_text_state(session=session, segment=segment)
        line_key = f"segment:{segment.satz_uuid}"
        entries.append(
            TocEntry(
                page_index=page.page_index,
                page_uuid=page.page_uuid,
                level=HEADING_BLOCK_TYPES[block.block_type],
                ar_text=text_state.source_text,
                de_text=text_state.target_text,
                satz_uuid=segment.satz_uuid,
                block_uuid=block.block_uuid,
                line_key=line_key,
                target_page_index=page.page_index,
                target_page_uuid=page.page_uuid,
                status=_entry_status(text_state.source_text, text_state.target_text),
                target_heading=text_state.source_text or text_state.target_text,
            )
        )
    return entries


async def _page_texts(
    *, session: AsyncSession, pages: list[Page]
) -> dict[_uuid.UUID, str]:
    if not pages:
        return {}
    result = await session.execute(
        select(Page, Block, Segment)
        .join(Block, Block.page_uuid == Page.page_uuid)
        .join(Segment, Segment.block_uuid == Block.block_uuid)
        .where(Page.page_uuid.in_([page.page_uuid for page in pages]))
        .where(Segment.active.is_(True))
        .order_by(Page.page_index.asc(), Block.block_index.asc(), Segment.satz_index.asc())
    )
    chunks: dict[_uuid.UUID, list[str]] = {page.page_uuid: [] for page in pages}
    for page, _block, segment in result.all():
        text_state = await resolve_segment_text_state(session=session, segment=segment)
        text = text_state.source_text or segment.text_content or ""
        if text.strip():
            chunks.setdefault(page.page_uuid, []).append(text.strip())
    return {page_uuid: "\n".join(parts) for page_uuid, parts in chunks.items()}


_TOC_TITLE_RE = re.compile(
    r"(?:فهرس|الفهرس|المحتويات|فهرست|contents|table\s+of\s+contents)",
    flags=re.IGNORECASE,
)
_DOT_LEADER_RE = re.compile(r"(?:\.{2,}|…{1,}|ـ{2,}|-{2,})")
_LINE_END_PAGE_RE = re.compile(r"([0-9٠-٩۰-۹]{1,4})\s*$")


def _detect_source_candidates(
    *, pages: list[Page], page_texts: dict[_uuid.UUID, str]
) -> list[TocSourceCandidate]:
    candidates: list[TocSourceCandidate] = []
    for page in pages:
        text = page_texts.get(page.page_uuid, "")
        lines = _nonempty_lines(text)
        if not lines:
            continue
        page_number_lines = sum(1 for line in lines if _LINE_END_PAGE_RE.search(line))
        dot_lines = sum(1 for line in lines if _DOT_LEADER_RE.search(line))
        title_hit = bool(_TOC_TITLE_RE.search(text))
        short_lines = sum(1 for line in lines if len(line) <= 90)
        score = 0.0
        reasons: list[str] = []
        if title_hit:
            score += 0.45
            reasons.append("TOC title")
        ratio = page_number_lines / max(1, len(lines))
        if page_number_lines >= 4 and ratio >= 0.35:
            score += min(0.35, ratio * 0.5)
            reasons.append("many line-ending page numbers")
        if dot_lines >= 2:
            score += 0.15
            reasons.append("dot leaders")
        if len(lines) >= 6 and short_lines / max(1, len(lines)) >= 0.7:
            score += 0.1
            reasons.append("dense short-line list")
        if score >= 0.35:
            candidates.append(
                TocSourceCandidate(
                    page_index=page.page_index,
                    page_uuid=page.page_uuid,
                    score=round(min(score, 1.0), 2),
                    reason=", ".join(reasons) or "TOC-like layout",
                )
            )
    return _include_adjacent_candidates(candidates=candidates, pages=pages)


def _include_adjacent_candidates(
    *, candidates: list[TocSourceCandidate], pages: list[Page]
) -> list[TocSourceCandidate]:
    by_index = {candidate.page_index: candidate for candidate in candidates}
    page_by_index = {page.page_index: page for page in pages}
    for candidate in list(candidates):
        for neighbor_index in (candidate.page_index - 1, candidate.page_index + 1):
            if neighbor_index in by_index or neighbor_index not in page_by_index:
                continue
            by_index[neighbor_index] = TocSourceCandidate(
                page_index=neighbor_index,
                page_uuid=page_by_index[neighbor_index].page_uuid,
                score=max(0.35, round(candidate.score - 0.2, 2)),
                reason=f"adjacent to TOC-like page {candidate.page_index}",
            )
    return sorted(by_index.values(), key=lambda item: item.page_index)


def _add_manual_source_candidates(
    *,
    candidates: list[TocSourceCandidate],
    pages: list[Page],
    selected_source_indices: list[int],
) -> None:
    by_index = {candidate.page_index for candidate in candidates}
    page_by_index = {page.page_index: page for page in pages}
    for page_index in selected_source_indices:
        if page_index in by_index or page_index not in page_by_index:
            continue
        candidates.append(
            TocSourceCandidate(
                page_index=page_index,
                page_uuid=page_by_index[page_index].page_uuid,
                score=1.0,
                reason="manually selected TOC source page",
                selected=True,
            )
        )
    candidates.sort(key=lambda item: item.page_index)


def _contiguous_candidate_range(candidates: list[TocSourceCandidate]) -> list[int]:
    if not candidates:
        return []
    ordered = sorted(candidates, key=lambda item: item.page_index)
    groups: list[list[TocSourceCandidate]] = []
    current: list[TocSourceCandidate] = []
    for candidate in ordered:
        if not current or candidate.page_index == current[-1].page_index + 1:
            current.append(candidate)
        else:
            groups.append(current)
            current = [candidate]
    if current:
        groups.append(current)
    best = max(groups, key=lambda group: (sum(item.score for item in group), len(group)))
    return [item.page_index for item in best if item.score >= 0.35]


def _entries_from_source_pages(
    *,
    pages: list[Page],
    page_texts: dict[_uuid.UUID, str],
    source_page_indices: list[int],
    heading_entries: list[TocEntry],
) -> tuple[list[TocEntry], list[TocOcrLine]]:
    page_by_index = {page.page_index: page for page in pages}
    lines: list[TocOcrLine] = []
    entries: list[TocEntry] = []
    for page_index in source_page_indices:
        page = page_by_index.get(page_index)
        if page is None:
            continue
        page_lines = _nonempty_lines(page_texts.get(page.page_uuid, ""))
        if not page_lines:
            lines.append(
                TocOcrLine(
                    line_key=f"toc_source:{page.page_uuid}:empty",
                    page_index=page.page_index,
                    page_uuid=page.page_uuid,
                    line_no=len(lines) + 1,
                    text="No OCR text found on this selected TOC source page.",
                    is_toc_entry=False,
                    source_kind="toc_source_page_empty",
                )
            )
            continue
        for line_no, raw_line in enumerate(page_lines, start=1):
            line_key = f"toc_source:{page.page_uuid}:{line_no}"
            heading_text, target_page = _parse_toc_line(raw_line)
            is_toc = target_page is not None or bool(_TOC_TITLE_RE.search(raw_line))
            line = TocOcrLine(
                line_key=line_key,
                page_index=page.page_index,
                page_uuid=page.page_uuid,
                line_no=len(lines) + 1,
                text=raw_line,
                is_toc_entry=is_toc,
                source_kind="toc_source_page",
            )
            lines.append(line)
            if not is_toc or _TOC_TITLE_RE.fullmatch(raw_line.strip()):
                continue
            target = _match_target_heading(
                heading_text=heading_text,
                target_page_index=target_page,
                heading_entries=heading_entries,
            )
            status = _source_entry_status(target_page, target, pages)
            entries.append(
                TocEntry(
                    page_index=page.page_index,
                    page_uuid=page.page_uuid,
                    level=_guess_level(raw_line),
                    ar_text=heading_text or raw_line,
                    de_text=target.de_text if target else "",
                    satz_uuid=target.satz_uuid if target else None,
                    block_uuid=target.block_uuid if target else None,
                    line_key=line_key,
                    target_page_index=target_page,
                    target_page_uuid=target.page_uuid if target else _page_uuid_for_index(pages, target_page),
                    status=status,
                    is_toc_entry=True,
                    target_heading=(target.ar_text or target.de_text) if target else None,
                )
            )
    return entries, lines


def _nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.replace("\r\n", "\n").splitlines() if line.strip()]


def _parse_toc_line(line: str) -> tuple[str, int | None]:
    match = _LINE_END_PAGE_RE.search(line)
    if not match:
        return line.strip(), None
    page_number = _to_int(match.group(1))
    heading = line[: match.start()].strip()
    heading = _DOT_LEADER_RE.sub(" ", heading)
    heading = re.sub(r"\s+", " ", heading).strip()
    return heading, page_number


def _to_int(value: str) -> int | None:
    digits = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
    normalized = value.translate(digits)
    try:
        return int(normalized)
    except ValueError:
        return None


def _guess_level(line: str) -> int:
    stripped = line.strip()
    if re.match(r"^(?:[0-9٠-٩۰-۹]+[.)-]|\([0-9٠-٩۰-۹]+\))", stripped):
        return 2
    if len(stripped) <= 45:
        return 1
    return 2


def _match_target_heading(
    *,
    heading_text: str,
    target_page_index: int | None,
    heading_entries: list[TocEntry],
) -> TocEntry | None:
    if target_page_index is None:
        return None
    nearby = [
        entry
        for entry in heading_entries
        if entry.page_index in {target_page_index - 1, target_page_index, target_page_index + 1}
    ]
    if not nearby:
        return None
    if not heading_text.strip():
        return nearby[0]
    return max(
        nearby,
        key=lambda entry: SequenceMatcher(
            None,
            _norm_match_text(heading_text),
            _norm_match_text(entry.ar_text or entry.de_text),
        ).ratio(),
    )


def _norm_match_text(value: str) -> str:
    return re.sub(r"\s+", " ", _DOT_LEADER_RE.sub(" ", value)).strip().lower()


def _source_entry_status(
    target_page_index: int | None, target: TocEntry | None, pages: list[Page]
) -> str:
    if target_page_index is None:
        return "missing"
    if _page_uuid_for_index(pages, target_page_index) is None:
        return "mismatch"
    if target is None:
        return "verify"
    return "verified"


def _page_uuid_for_index(pages: list[Page], page_index: int | None) -> _uuid.UUID | None:
    if page_index is None:
        return None
    page = next((item for item in pages if item.page_index == page_index), None)
    return page.page_uuid if page else None


def _lines_from_entries(
    entries: list[TocEntry], *, source_kind: str = "detected_heading"
) -> list[TocOcrLine]:
    return [
        TocOcrLine(
            line_key=entry.line_key,
            page_index=entry.page_index,
            page_uuid=entry.page_uuid,
            line_no=index + 1,
            text=entry.ar_text or entry.de_text or f"Page {entry.page_index}",
            is_toc_entry=entry.is_toc_entry,
            manual=entry.manual,
            protected=entry.protected,
            satz_uuid=entry.satz_uuid,
            block_uuid=entry.block_uuid,
            source_kind=source_kind,
        )
        for index, entry in enumerate(entries)
    ]


async def _apply_toc_review_decisions(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    entries: list[TocEntry],
    ocr_lines: list[TocOcrLine],
) -> tuple[list[TocEntry], list[TocOcrLine]]:
    decisions = await _toc_review_decisions(session=session, project_uuid=project_uuid)
    for decision in decisions:
        content = decision.content or {}
        if decision.decision_type == "toc_line_decision":
            _apply_line_decision(entries=entries, lines=ocr_lines, content=content)
        elif decision.decision_type == "toc_entry_decision":
            _apply_entry_decision(entries=entries, lines=ocr_lines, content=content)
    for index, line in enumerate(ocr_lines):
        line.line_no = index + 1
    for entry in entries:
        if entry.target_page_index is None:
            entry.target_page_index = entry.page_index
        if entry.target_page_uuid is None:
            entry.target_page_uuid = entry.page_uuid
        if not entry.status:
            entry.status = _entry_status(entry.ar_text, entry.de_text)
    return entries, ocr_lines


def _apply_line_decision(
    *,
    entries: list[TocEntry],
    lines: list[TocOcrLine],
    content: dict[str, Any],
) -> None:
    action = str(content.get("action") or "")
    line_key = str(content.get("line_key") or "")
    if not line_key:
        return
    line = _find_line(lines, line_key)
    entry = _find_entry(entries, line_key)
    if action == "correct" and line is not None:
        text = str(content.get("text") or "")
        line.text = text
        line.manual = True
        line.protected = True
        if entry is not None:
            entry.ar_text = text
            entry.manual = True
            entry.protected = True
            entry.status = _entry_status(entry.ar_text, entry.de_text)
    elif action == "split" and line is not None:
        first_text = str(content.get("first_text") or line.text)
        second_text = str(content.get("second_text") or "")
        new_line_key = str(content.get("new_line_key") or f"{line_key}:split")
        line.text = first_text
        line.manual = True
        line.protected = True
        line_index = lines.index(line)
        lines.insert(
            line_index + 1,
            TocOcrLine(
                line_key=new_line_key,
                page_index=line.page_index,
                page_uuid=line.page_uuid,
                line_no=line.line_no + 1,
                text=second_text,
                is_toc_entry=False,
                manual=True,
                protected=True,
                source_kind="manual_split",
            ),
        )
        if entry is not None:
            entry.ar_text = first_text
            entry.manual = True
            entry.protected = True
    elif action == "merge_next" and line is not None:
        index = lines.index(line)
        if index + 1 >= len(lines):
            return
        next_line = lines.pop(index + 1)
        line.text = f"{line.text} {next_line.text}".strip()
        line.manual = True
        line.protected = True
        if entry is not None:
            entry.ar_text = line.text
            entry.manual = True
            entry.protected = True
    elif action in {"mark_toc", "mark_not_toc"} and line is not None:
        is_toc = action == "mark_toc"
        line.is_toc_entry = is_toc
        line.manual = True
        line.protected = True
        if entry is not None:
            entry.is_toc_entry = is_toc
            entry.manual = True
            entry.protected = True


def _apply_entry_decision(
    *,
    entries: list[TocEntry],
    lines: list[TocOcrLine],
    content: dict[str, Any],
) -> None:
    action = str(content.get("action") or "")
    line_key = str(content.get("line_key") or "")
    if action == "confirm_match":
        entry = _find_entry(entries, line_key)
        if entry is not None:
            entry.status = "verified"
            entry.manual = True
            entry.protected = True
        return
    if action == "relink_page":
        entry = _find_entry(entries, line_key)
        if entry is not None:
            target_page_index = content.get("target_page_index")
            target_page_uuid = content.get("target_page_uuid")
            entry.target_page_index = (
                int(target_page_index) if target_page_index is not None else entry.target_page_index
            )
            entry.target_page_uuid = (
                _uuid.UUID(str(target_page_uuid))
                if target_page_uuid
                else entry.target_page_uuid
            )
            entry.status = "verify"
            entry.manual = True
            entry.protected = True
        return
    if action == "set_level":
        entry = _find_entry(entries, line_key)
        if entry is not None:
            level = int(content.get("level") or entry.level)
            entry.level = max(1, min(6, level))
            entry.manual = True
            entry.protected = True
        return
    if action != "add_from_source":
        return
    if not line_key or _find_entry(entries, line_key) is not None:
        return
    line = _find_line(lines, line_key)
    if line is None:
        return
    level = int(content.get("level") or 1)
    target_page_index = int(content.get("target_page_index") or line.page_index)
    target_page_uuid_raw = content.get("target_page_uuid")
    target_page_uuid = (
        _uuid.UUID(str(target_page_uuid_raw)) if target_page_uuid_raw else line.page_uuid
    )
    line.is_toc_entry = True
    line.manual = True
    line.protected = True
    entries.append(
        TocEntry(
            page_index=line.page_index,
            page_uuid=line.page_uuid,
            level=level,
            ar_text=str(content.get("ar_text") or line.text),
            de_text=str(content.get("de_text") or ""),
            satz_uuid=None,
            block_uuid=None,
            line_key=line_key,
            target_page_index=target_page_index,
            target_page_uuid=target_page_uuid,
            status="verify",
            is_toc_entry=True,
            manual=True,
            protected=True,
            target_heading=str(content.get("target_heading") or ""),
        )
    )


def _find_line(lines: list[TocOcrLine], line_key: str) -> TocOcrLine | None:
    return next((line for line in lines if line.line_key == line_key), None)


def _find_entry(entries: list[TocEntry], line_key: str) -> TocEntry | None:
    return next((entry for entry in entries if entry.line_key == line_key), None)


async def _toc_review_decisions(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> list[DecisionEvent]:
    result = await session.execute(
        select(DecisionEvent)
        .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
        .where(DecisionEvent.scope_uuid == project_uuid)
        .where(DecisionEvent.decision_source == DecisionSource.PREFLIGHT_CONFIRMATION.value)
        .where(
            DecisionEvent.decision_type.in_(
                ["toc_line_decision", "toc_entry_decision"]
            )
        )
        .order_by(DecisionEvent.created_at.asc())
    )
    return list(result.scalars())


async def _latest_export_settings_summary(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> dict[str, str | int | bool]:
    result = await session.execute(
        select(DecisionEvent)
        .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
        .where(DecisionEvent.scope_uuid == project_uuid)
        .where(DecisionEvent.decision_source == DecisionSource.PREFLIGHT_CONFIRMATION.value)
        .where(DecisionEvent.decision_type == "toc_export_settings_saved")
        .order_by(DecisionEvent.created_at.desc())
        .limit(1)
    )
    decision = result.scalar_one_or_none()
    if decision is None:
        return _export_settings_summary()
    settings = (decision.content or {}).get("settings")
    if not isinstance(settings, dict):
        return _export_settings_summary()
    return {
        "toc_position": settings.get("toc_position", "front"),
        "header_heading_level": settings.get("header_heading_level", 1),
        "chapter_break_heading_level": settings.get("chapter_break_heading_level", 1),
        "display_arabic_chapter_headings": settings.get(
            "display_arabic_chapter_headings", True
        ),
        "navigation_depth": settings.get("navigation_depth", 3),
    }


async def _latest_toc_source_decision(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> DecisionEvent | None:
    result = await session.execute(
        select(DecisionEvent)
        .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
        .where(DecisionEvent.scope_uuid == project_uuid)
        .where(DecisionEvent.decision_source == DecisionSource.PREFLIGHT_CONFIRMATION.value)
        .where(DecisionEvent.decision_type == "toc_source_decision")
        .order_by(DecisionEvent.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _source_selection_from_decision(
    decision: DecisionEvent | None,
) -> tuple[str, list[int]]:
    if decision is None:
        return "auto", []
    content = decision.content or {}
    action = str(content.get("action") or "")
    if action == "no_toc":
        return "no_toc", []
    raw_indices = content.get("page_indices")
    if action in {"confirm_source_pages", "set_source_pages"} and isinstance(raw_indices, list):
        indices = sorted(
            {
                int(value)
                for value in raw_indices
                if isinstance(value, int) or str(value).isdigit()
            }
        )
        return "manual" if indices else "auto", indices
    return "auto", []


async def _latest_toc_confirmation(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> DecisionEvent | None:
    result = await session.execute(
        select(DecisionEvent)
        .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
        .where(DecisionEvent.scope_uuid == project_uuid)
        .where(DecisionEvent.decision_source == DecisionSource.PREFLIGHT_CONFIRMATION.value)
        .where(DecisionEvent.decision_type == "toc_final_review_confirmed")
        .order_by(DecisionEvent.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _latest_translated_toc_confirmation(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> DecisionEvent | None:
    result = await session.execute(
        select(DecisionEvent)
        .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
        .where(DecisionEvent.scope_uuid == project_uuid)
        .where(DecisionEvent.decision_source == DecisionSource.PREFLIGHT_CONFIRMATION.value)
        .where(DecisionEvent.decision_type == "toc_translated_review_confirmed")
        .order_by(DecisionEvent.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _project_has_translation(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> bool:
    result = await session.execute(
        select(Revision.rev_uuid)
        .join(Segment, Segment.satz_uuid == Revision.satz_uuid)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(Revision.change_source == ChangeSource.RE_TRANSLATE.value)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


def _confirmation_applies(
    decision: DecisionEvent | None,
    *,
    fallback_kind: TocFallbackKind,
    detected_heading_count: int,
    page_count: int,
    attention_reasons: list[str],
) -> bool:
    if decision is None:
        return False
    content = decision.content or {}
    return (
        content.get("fallback_kind") == fallback_kind.value
        and content.get("detected_heading_count") == detected_heading_count
        and content.get("page_count") == page_count
        and content.get("attention_reasons") == attention_reasons
    )


def _export_settings_summary() -> dict[str, str | int | bool]:
    return {
        "toc_position": "Configured during Translate & export preflight.",
        "header_heading_level": "Configured during Translate & export preflight.",
        "chapter_break_heading_level": "Configured during Translate & export preflight.",
        "display_arabic_chapter_headings": "Configured during Translate & export preflight.",
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, _uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


async def edit_toc_entry_heading(
    *,
    session: AsyncSession,
    satz_uuid: _uuid.UUID,
    new_ar_text: str | None = None,
    new_de_text: str | None = None,
    actor_uuid: _uuid.UUID | None = None,
) -> Revision:
    """Edit the AR and/or DE half of a TOC heading segment.

    Writes a single Revision via `create_revision`; the unedited side
    is preserved verbatim. Refuses calls that touch a fallback page-
    by-page entry — that signature requires `satz_uuid` and the
    fallback entries don't have one.

    Raises:
        LookupError: when `satz_uuid` doesn't resolve.
        ValueError: when neither `new_ar_text` nor `new_de_text` is given.
    """
    if new_ar_text is None and new_de_text is None:
        raise ValueError("at least one of new_ar_text / new_de_text must be supplied")

    segment: Segment | None = await session.get(Segment, satz_uuid)
    if segment is None:
        raise LookupError(f"segment {satz_uuid!r} not found")

    text_state = await resolve_segment_text_state(session=session, segment=segment)
    current_ar, current_de = text_state.source_text, text_state.target_text
    final_ar = new_ar_text if new_ar_text is not None else current_ar
    final_de = new_de_text if new_de_text is not None else current_de
    final_text = join_source_target_text(final_ar, final_de)

    revision = await create_revision(
        session=session,
        segment=segment,
        after_text=final_text,
        change_source=ChangeSource.MANUAL,
        operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
        author_uuid=actor_uuid,
    )
    return revision


# Silence unused-warning for re-exported items.
_ = field

__all__ = [
    "HEADING_BLOCK_TYPES",
    "TocEntry",
    "TocFallbackKind",
    "TocResult",
    "TocWorkflowState",
    "confirm_toc_translated_review",
    "confirm_toc_final_review",
    "detect_toc",
    "edit_toc_entry_heading",
    "record_toc_entry_decision",
    "record_toc_export_settings",
    "record_toc_line_decision",
    "record_toc_redetect_request",
    "record_toc_source_decision",
    "toc_structure_blocks_translation",
    "toc_translated_review_blocks_export",
]
