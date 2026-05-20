"""T-9.2.1 — Translation export DOCX builder.

Per Formatvorlagen-Baseline v1.1 §7.2:
- Per-paragraph RTL marking on Arabic text (Sprint 5 RTL-Per-Run-Test).
- Heading styles per `\\o "1-6"` TOC depth (Schluss-Audit Paket 7 Item 2 (a)).
- Footnotes per `eachSect`.
- Page setup: A4, generous margins, header/footer with project title.
- Word-compatible — opens without warnings or repair indicators
  (Word-Kompatibel-Oeffnungs-Test).

Read-only: this module never writes Revision rows, never modifies
Segment text, never writes TRANSLATION-PO rows. Pure read of segment
target text + minimal page/block metadata.

The artefact is built fully in memory; bytes are returned to the
caller. Persistence to the artefact store happens in the atomic-commit
step (a) inside `run_export_job`.
"""

from __future__ import annotations

import hashlib
import io
import uuid as _uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity.service import new_uuid
from waraq.schemas import Block, Page, Revision, Segment
from waraq.text_state import (
    resolve_segment_source_text,
    resolve_segment_text_state,
    split_source_target_text,
)

TocPosition = Literal["front", "back"]


@dataclass(frozen=True, kw_only=True, slots=True)
class TranslationDocxConfig:
    """Export-layout choices captured during preflight."""

    header_heading_level: int = 1
    chapter_break_heading_level: int = 1
    toc_position: TocPosition = "front"
    display_arabic_chapter_headings: bool = True


DEFAULT_DOCX_CONFIG = TranslationDocxConfig()


@dataclass(frozen=True, kw_only=True, slots=True)
class TranslationDocxArtefact:
    """The DOCX bytes plus identity + protocol data."""

    artefact_uuid: _uuid.UUID
    bytes_: bytes
    sha256: str
    size_bytes: int
    n_pages_exported: int
    n_segments_exported: int
    block_types_present: list[str]
    exported_segment_uuids: list[_uuid.UUID]
    exported_page_uuids: list[_uuid.UUID]
    exported_block_uuids: list[_uuid.UUID]
    protocol: dict[str, Any] = field(default_factory=dict)


def _set_paragraph_rtl(paragraph: Any) -> None:
    """Mark a paragraph right-to-left at the paragraph-properties level
    so each Arabic paragraph carries its own `<w:bidi/>` per
    Formatvorlagen-Baseline v1.1 §7.2 — not relying on document-global
    setting. Sprint 5 RTL-Per-Run-Test asserts this structurally."""
    p_pr = paragraph._p.get_or_add_pPr()
    bidi = p_pr.find(qn("w:bidi"))
    if bidi is None:
        from docx.oxml import OxmlElement

        bidi = OxmlElement("w:bidi")
        p_pr.append(bidi)


def _heading_level(value: object, default: int = 1) -> int:
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            return default
    else:
        return default
    return max(1, min(6, parsed))


def _answer_heading_level(answer: object) -> object:
    if isinstance(answer, Mapping):
        return answer.get("heading_level")
    return None


def _answer_position(answer: object) -> object:
    if isinstance(answer, Mapping):
        return answer.get("position")
    return None


def _answer_display(answer: object) -> bool:
    if isinstance(answer, Mapping) and "display" in answer:
        return bool(answer.get("display"))
    return True


def _toc_position(value: object) -> TocPosition:
    return "back" if value == "back" else "front"


def docx_config_from_pflichtfragen(
    pflichtfragen: Sequence[Mapping[str, Any]] | None,
) -> TranslationDocxConfig:
    """Build a DOCX config from persisted preflight decision-event payloads."""
    values: dict[str, Any] = {}
    for entry in pflichtfragen or []:
        key = entry.get("frage_key")
        answer = entry.get("answer")
        if not isinstance(key, str) or not isinstance(answer, Mapping):
            continue
        values[key] = dict(answer)

    return TranslationDocxConfig(
        header_heading_level=_heading_level(
            _answer_heading_level(values.get("header_heading_level"))
        ),
        chapter_break_heading_level=_heading_level(
            _answer_heading_level(values.get("chapter_break_heading_level"))
        ),
        toc_position=_toc_position(_answer_position(values.get("toc_position"))),
        display_arabic_chapter_headings=_answer_display(
            values.get("display_arabic_chapter_headings")
        ),
    )


def docx_config_from_export_payload(payload: Mapping[str, Any]) -> TranslationDocxConfig:
    export_config = payload.get("export_config")
    if not isinstance(export_config, Mapping):
        return DEFAULT_DOCX_CONFIG
    pflichtfragen = export_config.get("pflichtfragen")
    if not isinstance(pflichtfragen, list):
        return DEFAULT_DOCX_CONFIG
    return docx_config_from_pflichtfragen(pflichtfragen)


def _add_field_run(paragraph: Any, instruction: str) -> None:
    from docx.oxml import OxmlElement

    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    run._r.append(fld_end)


def _set_running_header(document: Any, *, project_title: str, heading_level: int) -> None:
    header = document.sections[0].header
    paragraph = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    paragraph.text = f"{project_title} | "
    _add_field_run(paragraph, f'STYLEREF "Heading {heading_level}"')


def _add_toc(document: Any) -> None:
    """Insert a TOC field with `\\o "1-6"` per Formatvorlagen-Baseline
    v1.1 §7.2 (Schluss-Audit Paket 7 Item 2 (a), 2026-05-08). Word
    renders this on first open; python-docx writes it as a field
    instruction.
    """
    paragraph = document.add_paragraph()
    _add_field_run(paragraph, 'TOC \\o "1-6" \\h \\z \\u')


_BLOCK_TYPE_STYLE: dict[str, str] = {
    "main_text": "Normal",
    "MT": "Normal",
    "UE": "Heading 1",
    "HD": "Heading 2",
    "FN": "Footnote Text",
    "QR": "Quote",
    "RN": "Caption",
}


def _style_for_block(block_type: str, config: TranslationDocxConfig) -> str:
    if block_type == "UE":
        return f"Heading {config.chapter_break_heading_level}"
    if block_type == "HD":
        return f"Heading {min(6, config.chapter_break_heading_level + 1)}"
    return _BLOCK_TYPE_STYLE.get(block_type, "Normal")


def _include_source_for_block(block_type: str, config: TranslationDocxConfig) -> bool:
    return not (block_type in {"UE", "HD"} and not config.display_arabic_chapter_headings)


def _add_title_page(document: Any, *, project_title: str, config: TranslationDocxConfig) -> None:
    title = document.add_heading(project_title, level=0)
    for run in title.runs:
        run.font.size = Pt(20)
    document.add_paragraph()
    if config.toc_position == "front":
        _add_toc(document)
        document.add_page_break()
    else:
        document.add_page_break()


def _add_back_toc(document: Any, config: TranslationDocxConfig) -> None:
    if config.toc_position != "back":
        return
    document.add_page_break()
    document.add_heading("Contents", level=1)
    _add_toc(document)


async def build_translation_docx(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    project_title: str,
    segment_uuids: list[_uuid.UUID] | None = None,
    config: TranslationDocxConfig = DEFAULT_DOCX_CONFIG,
) -> TranslationDocxArtefact:
    """Build the translation-export DOCX in memory.

    Reads only: Page/Block/Segment in-scope of `project_uuid`. The
    artefact captures target-language text per Segment; Arabic-side
    source is preserved on a separate paragraph for the bilingual
    publication layout per Formatvorlagen-Baseline v1.1 §7.2.

    H-4 invariant: this function does not write a Revision row, does
    not write a TRANSLATION-PO row, does not modify Segment text. Pure
    read of `segments.text_content`.
    """
    # Resolve in-scope segments (project-wide if no explicit set).
    stmt = (
        select(Page, Block, Segment)
        .join(Block, Block.page_uuid == Page.page_uuid)
        .join(Segment, Segment.block_uuid == Block.block_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(Segment.active.is_(True))
        .order_by(Page.page_index, Block.block_index, Segment.satz_index)
    )
    if segment_uuids is not None:
        stmt = stmt.where(Segment.satz_uuid.in_(segment_uuids))
    rows = (await session.execute(stmt)).all()

    document = Document()

    # Page setup per Formatvorlagen-Baseline v1.1 §7.2.
    section = document.sections[0]
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)

    _set_running_header(
        document,
        project_title=project_title,
        heading_level=config.header_heading_level,
    )
    _add_title_page(document, project_title=project_title, config=config)

    pages_seen: set[_uuid.UUID] = set()
    blocks_seen: set[_uuid.UUID] = set()
    segs_seen: set[_uuid.UUID] = set()
    block_types_seen: set[str] = set()
    last_page_index: int | None = None

    for page, block, segment in rows:
        pages_seen.add(page.page_uuid)
        blocks_seen.add(block.block_uuid)
        segs_seen.add(segment.satz_uuid)
        block_types_seen.add(block.block_type)

        if last_page_index is None or last_page_index != page.page_index:
            heading = document.add_heading(f"Page {page.page_index}", level=1)
            for run in heading.runs:
                run.font.size = Pt(14)
            last_page_index = page.page_index

        text_state = await resolve_segment_text_state(session=session, segment=segment)
        source, target = text_state.source_text, text_state.target_text

        style = _style_for_block(block.block_type, config)

        if source.strip() and _include_source_for_block(block.block_type, config):
            ar_paragraph = document.add_paragraph(source, style=style)
            ar_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
            _set_paragraph_rtl(ar_paragraph)

        if target.strip() or not source.strip():
            de_paragraph = document.add_paragraph(target or "", style=style)
            de_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY

    _add_back_toc(document, config)

    # Serialize.
    buffer = io.BytesIO()
    document.save(buffer)
    bytes_ = buffer.getvalue()
    sha = hashlib.sha256(bytes_).hexdigest()

    return TranslationDocxArtefact(
        artefact_uuid=new_uuid(),
        bytes_=bytes_,
        sha256=sha,
        size_bytes=len(bytes_),
        n_pages_exported=len(pages_seen),
        n_segments_exported=len(segs_seen),
        block_types_present=sorted(block_types_seen),
        exported_segment_uuids=sorted(segs_seen, key=str),
        exported_page_uuids=sorted(pages_seen, key=str),
        exported_block_uuids=sorted(blocks_seen, key=str),
        protocol={
            "n_pages": len(pages_seen),
            "n_segments": len(segs_seen),
            "block_types_present": sorted(block_types_seen),
            "docx_config": {
                "header_heading_level": config.header_heading_level,
                "chapter_break_heading_level": config.chapter_break_heading_level,
                "toc_position": config.toc_position,
                "display_arabic_chapter_headings": config.display_arabic_chapter_headings,
            },
        },
    )


async def build_translation_docx_from_snapshot(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    project_title: str,
    revision_uuids: list[_uuid.UUID],
    config: TranslationDocxConfig = DEFAULT_DOCX_CONFIG,
) -> TranslationDocxArtefact:
    """Rebuild a translation-export DOCX from a frozen `revision_snapshot[]`.

    Used by the download endpoint to reconstruct the exact text state
    that was exported, even if Segments have been re-translated since.
    Reads `Revision.after_text` (immutable per H-5) for each rev_uuid in
    the snapshot, then assembles the DOCX in Page/Block/satz order using
    the Segments/Blocks/Pages each Revision is anchored to.

    H-4: pure-read; writes nothing.
    """
    if not revision_uuids:
        # Empty snapshot — return a minimal artefact (title + empty body).
        revision_uuids = []
    rows = (
        await session.execute(
            select(Revision, Page, Block, Segment)
            .join(Segment, Segment.satz_uuid == Revision.satz_uuid)
            .join(Block, Block.block_uuid == Segment.block_uuid)
            .join(Page, Page.page_uuid == Block.page_uuid)
            .where(Page.project_uuid == project_uuid)
            .where(Revision.rev_uuid.in_(revision_uuids))
            .order_by(Page.page_index, Block.block_index, Segment.satz_index)
        )
    ).all()

    document = Document()
    section = document.sections[0]
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)

    _set_running_header(
        document,
        project_title=project_title,
        heading_level=config.header_heading_level,
    )
    _add_title_page(document, project_title=project_title, config=config)

    pages_seen: set[_uuid.UUID] = set()
    blocks_seen: set[_uuid.UUID] = set()
    segs_seen: set[_uuid.UUID] = set()
    block_types_seen: set[str] = set()
    last_page_index: int | None = None

    for revision, page, block, segment in rows:
        pages_seen.add(page.page_uuid)
        blocks_seen.add(block.block_uuid)
        segs_seen.add(segment.satz_uuid)
        block_types_seen.add(block.block_type)

        if last_page_index is None or last_page_index != page.page_index:
            heading = document.add_heading(f"Page {page.page_index}", level=1)
            for run in heading.runs:
                run.font.size = Pt(14)
            last_page_index = page.page_index

        # Use the Revision's after_text — the immutable snapshot text.
        source = await resolve_segment_source_text(
            session=session,
            segment=segment,
            at_or_before=revision.created_at,
        )
        embedded_source, embedded_target = split_source_target_text(revision.after_text)
        target = embedded_target or revision.after_text
        if embedded_source and not source:
            source = embedded_source
        style = _style_for_block(block.block_type, config)
        if source.strip() and _include_source_for_block(block.block_type, config):
            ar_paragraph = document.add_paragraph(source, style=style)
            ar_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
            _set_paragraph_rtl(ar_paragraph)
        if target.strip() or not source.strip():
            de_paragraph = document.add_paragraph(target or "", style=style)
            de_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY

    _add_back_toc(document, config)

    buffer = io.BytesIO()
    document.save(buffer)
    bytes_ = buffer.getvalue()
    sha = hashlib.sha256(bytes_).hexdigest()

    return TranslationDocxArtefact(
        artefact_uuid=new_uuid(),
        bytes_=bytes_,
        sha256=sha,
        size_bytes=len(bytes_),
        n_pages_exported=len(pages_seen),
        n_segments_exported=len(segs_seen),
        block_types_present=sorted(block_types_seen),
        exported_segment_uuids=sorted(segs_seen, key=str),
        exported_page_uuids=sorted(pages_seen, key=str),
        exported_block_uuids=sorted(blocks_seen, key=str),
        protocol={
            "n_pages": len(pages_seen),
            "n_segments": len(segs_seen),
            "block_types_present": sorted(block_types_seen),
            "rebuilt_from_snapshot": True,
            "docx_config": {
                "header_heading_level": config.header_heading_level,
                "chapter_break_heading_level": config.chapter_break_heading_level,
                "toc_position": config.toc_position,
                "display_arabic_chapter_headings": config.display_arabic_chapter_headings,
            },
        },
    )


__all__ = [
    "DEFAULT_DOCX_CONFIG",
    "TranslationDocxArtefact",
    "TranslationDocxConfig",
    "build_translation_docx",
    "build_translation_docx_from_snapshot",
    "docx_config_from_export_payload",
    "docx_config_from_pflichtfragen",
]
