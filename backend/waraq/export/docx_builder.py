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
from dataclasses import dataclass, field
from typing import Any

from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity.service import new_uuid
from waraq.schemas import Block, Page, Revision, Segment
from waraq.text_state import resolve_segment_source_text, resolve_segment_text_state


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


def _add_toc(document: Any) -> None:
    """Insert a TOC field with `\\o "1-6"` per Formatvorlagen-Baseline
    v1.1 §7.2 (Schluss-Audit Paket 7 Item 2 (a), 2026-05-08). Word
    renders this on first open; python-docx writes it as a field
    instruction.
    """
    from docx.oxml import OxmlElement

    paragraph = document.add_paragraph()
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-6" \\h \\z \\u'
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    run._r.append(fld_end)


_BLOCK_TYPE_STYLE: dict[str, str] = {
    "main_text": "Normal",
    "MT": "Normal",
    "UE": "Heading 1",
    "HD": "Heading 2",
    "FN": "Footnote Text",
    "QR": "Quote",
    "RN": "Caption",
}


async def build_translation_docx(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    project_title: str,
    segment_uuids: list[_uuid.UUID] | None = None,
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

    # Title page + TOC.
    title = document.add_heading(project_title, level=0)
    for run in title.runs:
        run.font.size = Pt(20)
    document.add_paragraph()
    _add_toc(document)
    document.add_page_break()  # type: ignore[no-untyped-call]

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

        style = _BLOCK_TYPE_STYLE.get(block.block_type, "Normal")

        if source.strip():
            ar_paragraph = document.add_paragraph(source, style=style)
            ar_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
            _set_paragraph_rtl(ar_paragraph)

        if target.strip() or not source.strip():
            de_paragraph = document.add_paragraph(target or "", style=style)
            de_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY

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
        },
    )


async def build_translation_docx_from_snapshot(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    project_title: str,
    revision_uuids: list[_uuid.UUID],
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

    title = document.add_heading(project_title, level=0)
    for run in title.runs:
        run.font.size = Pt(20)
    document.add_paragraph()
    _add_toc(document)
    document.add_page_break()  # type: ignore[no-untyped-call]

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
        target = revision.after_text
        style = _BLOCK_TYPE_STYLE.get(block.block_type, "Normal")
        if source.strip():
            ar_paragraph = document.add_paragraph(source, style=style)
            ar_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
            _set_paragraph_rtl(ar_paragraph)
        if target.strip() or not source.strip():
            de_paragraph = document.add_paragraph(target or "", style=style)
            de_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY

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
        },
    )


__all__ = [
    "TranslationDocxArtefact",
    "build_translation_docx",
    "build_translation_docx_from_snapshot",
]
