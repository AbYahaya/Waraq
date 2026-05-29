"""TOC detection + edit service — see module docstring for canonical scope."""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, field
from enum import StrEnum
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

    if rows:
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
                    target_heading=text_state.target_text,
                )
            )
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
        )

    # Canonical §2.1 fallback: one entry per active page.
    fallback_entries = [
        TocEntry(
            page_index=p.page_index,
            page_uuid=p.page_uuid,
            level=1,
            ar_text=f"صفحة {p.page_index}",
            de_text=f"Page {p.page_index}",
            satz_uuid=None,
            block_uuid=None,
            line_key=f"page:{p.page_uuid}",
            target_page_index=p.page_index,
            target_page_uuid=p.page_uuid,
            status="fallback",
            target_heading=f"Page {p.page_index}",
        )
        for p in pages
    ]
    fallback_lines = _lines_from_entries(fallback_entries, source_kind="fallback_page")
    fallback_entries, fallback_lines = await _apply_toc_review_decisions(
        session=session,
        project_uuid=project_uuid,
        entries=fallback_entries,
        ocr_lines=fallback_lines,
    )
    visible_fallback_entries = [entry for entry in fallback_entries if entry.is_toc_entry]
    confirmation = await _latest_toc_confirmation(session=session, project_uuid=project_uuid)
    confirmed = _confirmation_applies(
        confirmation,
        fallback_kind=TocFallbackKind.PAGE_BY_PAGE,
            detected_heading_count=len(
                [entry for entry in visible_fallback_entries if entry.manual]
            ),
        page_count=len(pages),
        attention_reasons=[],
    )
    return TocResult(
        entries=visible_fallback_entries,
        ocr_lines=fallback_lines,
        fallback_kind=TocFallbackKind.PAGE_BY_PAGE,
        detected_heading_count=len(
            [entry for entry in visible_fallback_entries if entry.manual]
        ),
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
    "confirm_toc_final_review",
    "detect_toc",
    "edit_toc_entry_heading",
    "record_toc_entry_decision",
    "record_toc_export_settings",
    "record_toc_line_decision",
    "record_toc_redetect_request",
]
