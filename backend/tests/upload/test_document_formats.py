"""Phase 5 sub-batch K-2 — direct-text upload formats.

Covers four orthogonal layers:

1. `waraq.upload.file_type` — DOCX/ODT/TXT/XML/HTML formats added to
   the enum + suffix map; `is_direct_text_format` predicate; `count_pages`
   returns 1 for all five.
2. `waraq.upload.text_extraction.extract_paragraphs` — per-format
   paragraph extraction; UTF-8 decode fallback; `EmptyDocument` /
   `TextExtractionError` on bad input.
3. `waraq.upload.service.finalize_upload` direct-text branch — for
   each format: one Page (ocr_status=GO), one Block (MAIN_TEXT, RTL),
   N Segments with text via Revisions (change_source=OCR), SCAN-PO
   payload with `skip_ocr: true`.
4. `waraq.ocr.page_runner._rasterize_page` — refuses direct-text
   formats with `PageOcrError`.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project
from waraq.ocr.page_runner import PageOcrError, _rasterize_page
from waraq.schemas import Block, Page, ProvenanceObject, Revision, Segment
from waraq.schemas.enums import BlockClass, ChangeSource, OcrStatus, POType
from waraq.upload import finalize_upload, start_upload
from waraq.upload.file_type import (
    UploadFormat,
    count_pages,
    detect_format,
    is_direct_text_format,
    is_image_format,
)
from waraq.upload.service import append_chunk
from waraq.upload.text_extraction import (
    EmptyDocument,
    TextExtractionError,
    extract_paragraphs,
)

# ---------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------


def _docx_bytes(paragraphs: list[str]) -> bytes:
    from docx import Document

    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _odt_bytes(paragraphs: list[str]) -> bytes:
    from odf.opendocument import OpenDocumentText
    from odf.text import P

    doc = OpenDocumentText()
    for p in paragraphs:
        elem = P(text=p)
        doc.text.addElement(elem)
    buf = BytesIO()
    doc.write(buf)
    return buf.getvalue()


def _txt_bytes(paragraphs: list[str]) -> bytes:
    return "\n\n".join(paragraphs).encode("utf-8")


def _xml_bytes(paragraphs: list[str]) -> bytes:
    body = "\n".join(f"<p>{p}</p>" for p in paragraphs)
    return f'<?xml version="1.0" encoding="UTF-8"?><doc>{body}</doc>'.encode()


def _html_bytes(paragraphs: list[str]) -> bytes:
    body = "\n".join(f"<p>{p}</p>" for p in paragraphs)
    return (
        "<!DOCTYPE html><html><head><title>x</title>"
        f"<style>body{{color:red;}}</style></head><body>{body}</body></html>"
    ).encode()


# ---------------------------------------------------------------------
# file_type — DOCX/ODT/TXT/XML/HTML suffix routing
# ---------------------------------------------------------------------


class TestDetectFormatDocs:
    def test_docx_by_suffix(self) -> None:
        # DOCX shares ZIP magic with ODT/EPUB; suffix is authoritative.
        assert (
            detect_format(filename="x.docx", head_bytes=b"PK\x03\x04stuff")
            == UploadFormat.DOCX
        )

    def test_odt_by_suffix(self) -> None:
        assert (
            detect_format(filename="x.odt", head_bytes=b"PK\x03\x04stuff")
            == UploadFormat.ODT
        )

    def test_txt_by_suffix(self) -> None:
        assert detect_format(filename="x.txt", head_bytes=b"hello") == UploadFormat.TXT

    def test_xml_by_suffix(self) -> None:
        assert (
            detect_format(filename="x.xml", head_bytes=b"<?xml version='1.0'?><doc/>")
            == UploadFormat.XML
        )

    def test_html_by_suffix(self) -> None:
        assert (
            detect_format(filename="x.html", head_bytes=b"<!DOCTYPE html>") == UploadFormat.HTML
        )

    def test_htm_alias(self) -> None:
        assert detect_format(filename="x.htm", head_bytes=b"") == UploadFormat.HTML

    def test_suffix_wins_for_doc_group_even_with_pdf_magic(self) -> None:
        # Hypothetical pathological case: file named book.docx that
        # happens to start with %PDF-. Suffix authoritative for the
        # direct-text group means we trust the suffix; the file would
        # then fail at extraction time (python-docx raises), which is
        # the correct behaviour.
        assert (
            detect_format(filename="book.docx", head_bytes=b"%PDF-1.7\n")
            == UploadFormat.DOCX
        )


class TestIsDirectTextFormat:
    def test_pdf_not_direct_text(self) -> None:
        assert is_direct_text_format(UploadFormat.PDF) is False

    def test_image_group_not_direct_text(self) -> None:
        for fmt in (
            UploadFormat.JPEG,
            UploadFormat.PNG,
            UploadFormat.TIFF,
            UploadFormat.HEIC,
            UploadFormat.WEBP,
        ):
            assert is_direct_text_format(fmt) is False, fmt

    def test_all_doc_formats_are_direct_text(self) -> None:
        for fmt in (
            UploadFormat.DOCX,
            UploadFormat.ODT,
            UploadFormat.TXT,
            UploadFormat.XML,
            UploadFormat.HTML,
        ):
            assert is_direct_text_format(fmt) is True, fmt

    def test_direct_text_and_image_are_disjoint(self) -> None:
        for fmt in UploadFormat:
            assert not (is_direct_text_format(fmt) and is_image_format(fmt)), fmt


class TestCountPagesDocs:
    def test_docx_single_page(self, tmp_path: Path) -> None:
        p = tmp_path / "x.docx"
        p.write_bytes(_docx_bytes(["a", "b", "c"]))
        assert count_pages(path=p, fmt=UploadFormat.DOCX) == 1

    def test_txt_single_page(self, tmp_path: Path) -> None:
        p = tmp_path / "x.txt"
        p.write_bytes(b"hello\n\nworld")
        assert count_pages(path=p, fmt=UploadFormat.TXT) == 1


# ---------------------------------------------------------------------
# Paragraph extraction
# ---------------------------------------------------------------------


class TestExtractDocx:
    def test_paragraphs_in_order(self, tmp_path: Path) -> None:
        p = tmp_path / "x.docx"
        p.write_bytes(_docx_bytes(["First.", "Second.", "Third."]))
        assert extract_paragraphs(path=p, fmt=UploadFormat.DOCX) == [
            "First.",
            "Second.",
            "Third.",
        ]

    def test_empty_docx_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "x.docx"
        p.write_bytes(_docx_bytes([]))
        with pytest.raises(EmptyDocument):
            extract_paragraphs(path=p, fmt=UploadFormat.DOCX)

    def test_whitespace_only_paragraphs_filtered(self, tmp_path: Path) -> None:
        p = tmp_path / "x.docx"
        p.write_bytes(_docx_bytes(["Real text", "   ", "", "More text"]))
        assert extract_paragraphs(path=p, fmt=UploadFormat.DOCX) == [
            "Real text",
            "More text",
        ]


class TestExtractOdt:
    def test_paragraphs_in_order(self, tmp_path: Path) -> None:
        p = tmp_path / "x.odt"
        p.write_bytes(_odt_bytes(["One.", "Two.", "Three."]))
        assert extract_paragraphs(path=p, fmt=UploadFormat.ODT) == [
            "One.",
            "Two.",
            "Three.",
        ]


class TestExtractTxt:
    def test_blank_line_paragraph_split(self, tmp_path: Path) -> None:
        p = tmp_path / "x.txt"
        p.write_bytes(b"First paragraph.\n\nSecond paragraph.\n\nThird.")
        assert extract_paragraphs(path=p, fmt=UploadFormat.TXT) == [
            "First paragraph.",
            "Second paragraph.",
            "Third.",
        ]

    def test_crlf_line_endings_normalized(self, tmp_path: Path) -> None:
        p = tmp_path / "x.txt"
        p.write_bytes(b"One.\r\n\r\nTwo.")
        assert extract_paragraphs(path=p, fmt=UploadFormat.TXT) == ["One.", "Two."]

    def test_utf8_decode_fallback_on_bad_bytes(self, tmp_path: Path) -> None:
        p = tmp_path / "x.txt"
        # Mix of utf-8 + latin-1 byte that's invalid in utf-8.
        p.write_bytes(b"hello\n\n\xff\xfeworld")
        # Should not raise — falls back to errors='replace'.
        result = extract_paragraphs(path=p, fmt=UploadFormat.TXT)
        assert len(result) == 2
        assert result[0] == "hello"

    def test_arabic_utf8_passes_through(self, tmp_path: Path) -> None:
        p = tmp_path / "x.txt"
        p.write_bytes("بسم الله\n\nالرحمن الرحيم".encode())
        assert extract_paragraphs(path=p, fmt=UploadFormat.TXT) == [
            "بسم الله",
            "الرحمن الرحيم",
        ]


class TestExtractXml:
    def test_strips_tags_keeps_text(self, tmp_path: Path) -> None:
        p = tmp_path / "x.xml"
        p.write_bytes(_xml_bytes(["Alpha", "Beta", "Gamma"]))
        out = extract_paragraphs(path=p, fmt=UploadFormat.XML)
        assert "Alpha" in out
        assert "Beta" in out
        assert "Gamma" in out

    def test_malformed_xml_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "x.xml"
        p.write_bytes(b"<doc><p>unclosed")
        with pytest.raises(TextExtractionError):
            extract_paragraphs(path=p, fmt=UploadFormat.XML)


class TestExtractHtml:
    def test_strips_tags_keeps_text(self, tmp_path: Path) -> None:
        p = tmp_path / "x.html"
        p.write_bytes(_html_bytes(["Alpha", "Beta"]))
        out = extract_paragraphs(path=p, fmt=UploadFormat.HTML)
        assert "Alpha" in out
        assert "Beta" in out

    def test_skips_script_and_style(self, tmp_path: Path) -> None:
        p = tmp_path / "x.html"
        p.write_bytes(_html_bytes(["Real content"]))
        # The fixture includes <style>body{color:red;}</style>; that
        # CSS text must NOT appear in extracted paragraphs.
        out = extract_paragraphs(path=p, fmt=UploadFormat.HTML)
        joined = " ".join(out)
        assert "Real content" in joined
        assert "color:red" not in joined

    def test_decodes_html_entities(self, tmp_path: Path) -> None:
        p = tmp_path / "x.html"
        p.write_bytes(b"<html><body><p>caf&eacute; &amp; tea</p></body></html>")
        out = extract_paragraphs(path=p, fmt=UploadFormat.HTML)
        assert "café & tea" in " ".join(out)

    def test_inline_tags_flow_inside_paragraph(self, tmp_path: Path) -> None:
        p = tmp_path / "x.html"
        p.write_bytes(b"<html><body><p>Hello <b>bold</b> world</p></body></html>")
        out = extract_paragraphs(path=p, fmt=UploadFormat.HTML)
        # The text from <b>bold</b> should land inside the surrounding
        # <p>, not as its own paragraph.
        assert any("Hello" in s and "bold" in s and "world" in s for s in out)


class TestExtractParagraphsRejectsNonText:
    def test_pdf_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "x.pdf"
        p.write_bytes(b"%PDF-1.7\n")
        with pytest.raises(TextExtractionError):
            extract_paragraphs(path=p, fmt=UploadFormat.PDF)

    def test_jpeg_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "x.jpg"
        p.write_bytes(b"\xff\xd8\xff")
        with pytest.raises(TextExtractionError):
            extract_paragraphs(path=p, fmt=UploadFormat.JPEG)


# ---------------------------------------------------------------------
# End-to-end finalize: direct-text branch materializes the right rows
# ---------------------------------------------------------------------


async def _upload_one_chunk(
    session: AsyncSession,
    project_uuid,
    *,
    filename: str,
    data: bytes,
):
    from waraq.schemas import Project

    project = await session.get(Project, project_uuid)
    assert project is not None
    job = await start_upload(
        session=session,
        project=project,
        original_filename=filename,
        total_chunks=1,
        total_size_bytes=len(data),
    )
    await append_chunk(
        session=session,
        upload_job=job,
        chunk_index=0,
        chunk_data=data,
    )
    return job, await finalize_upload(session=session, upload_job=job)


@pytest.mark.asyncio
class TestFinalizeDirectText:
    async def test_txt_materializes_page_block_and_segments(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        _, pages = await _upload_one_chunk(
            db_session,
            project.project_uuid,
            filename="notes.txt",
            data=b"First paragraph.\n\nSecond paragraph.\n\nThird.",
        )

        # One Page, ocr_status = GO.
        assert len(pages) == 1
        page_q = await db_session.execute(select(Page).where(Page.page_uuid == pages[0].page_uuid))
        page = page_q.scalar_one()
        assert page.ocr_status == OcrStatus.GO

        # One Block, MAIN_TEXT.
        block_q = await db_session.execute(
            select(Block).where(Block.page_uuid == page.page_uuid)
        )
        blocks = list(block_q.scalars())
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockClass.MAIN_TEXT.value

        # Three Segments, each with text + a Revision.
        seg_q = await db_session.execute(
            select(Segment)
            .where(Segment.block_uuid == blocks[0].block_uuid)
            .order_by(Segment.satz_index.asc())
        )
        segments = list(seg_q.scalars())
        assert [s.text_content for s in segments] == [
            "First paragraph.",
            "Second paragraph.",
            "Third.",
        ]
        for segment in segments:
            assert segment.current_rev_uuid is not None
            rev_q = await db_session.execute(
                select(Revision).where(Revision.rev_uuid == segment.current_rev_uuid)
            )
            rev = rev_q.scalar_one()
            assert rev.change_source == ChangeSource.OCR

        # SCAN-PO records skip_ocr + format + paragraph_count.
        po_q = await db_session.execute(
            select(ProvenanceObject)
            .where(ProvenanceObject.po_type == POType.SCAN.value)
            .where(ProvenanceObject.scope_uuid == page.page_uuid)
        )
        po = po_q.scalar_one()
        assert po.payload["format"] == "txt"
        assert po.payload["skip_ocr"] is True
        assert po.payload["paragraph_count"] == 3

    async def test_docx_materializes_segments(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        _, pages = await _upload_one_chunk(
            db_session,
            project.project_uuid,
            filename="essay.docx",
            data=_docx_bytes(["Paragraph one.", "Paragraph two."]),
        )
        assert len(pages) == 1
        page_q = await db_session.execute(select(Page).where(Page.page_uuid == pages[0].page_uuid))
        page = page_q.scalar_one()
        block_q = await db_session.execute(select(Block).where(Block.page_uuid == page.page_uuid))
        block = block_q.scalar_one()
        seg_q = await db_session.execute(
            select(Segment)
            .where(Segment.block_uuid == block.block_uuid)
            .order_by(Segment.satz_index.asc())
        )
        segments = list(seg_q.scalars())
        assert [s.text_content for s in segments] == ["Paragraph one.", "Paragraph two."]

    async def test_odt_materializes_segments(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        _, pages = await _upload_one_chunk(
            db_session,
            project.project_uuid,
            filename="essay.odt",
            data=_odt_bytes(["O1.", "O2.", "O3."]),
        )
        assert len(pages) == 1
        page_q = await db_session.execute(select(Page).where(Page.page_uuid == pages[0].page_uuid))
        page = page_q.scalar_one()
        block_q = await db_session.execute(select(Block).where(Block.page_uuid == page.page_uuid))
        block = block_q.scalar_one()
        seg_q = await db_session.execute(
            select(Segment)
            .where(Segment.block_uuid == block.block_uuid)
            .order_by(Segment.satz_index.asc())
        )
        assert [s.text_content for s in seg_q.scalars()] == ["O1.", "O2.", "O3."]

    async def test_xml_materializes_segments(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        _, pages = await _upload_one_chunk(
            db_session,
            project.project_uuid,
            filename="doc.xml",
            data=_xml_bytes(["Alpha", "Beta", "Gamma"]),
        )
        assert len(pages) == 1
        page_q = await db_session.execute(select(Page).where(Page.page_uuid == pages[0].page_uuid))
        page = page_q.scalar_one()
        block_q = await db_session.execute(select(Block).where(Block.page_uuid == page.page_uuid))
        block = block_q.scalar_one()
        seg_q = await db_session.execute(
            select(Segment).where(Segment.block_uuid == block.block_uuid)
        )
        texts = [s.text_content for s in seg_q.scalars()]
        # All three paragraphs landed (order may vary by ET traversal,
        # but the set should match).
        assert set(texts) == {"Alpha", "Beta", "Gamma"}

    async def test_html_materializes_segments(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        _, pages = await _upload_one_chunk(
            db_session,
            project.project_uuid,
            filename="article.html",
            data=_html_bytes(["First H paragraph.", "Second H paragraph."]),
        )
        assert len(pages) == 1
        page_q = await db_session.execute(select(Page).where(Page.page_uuid == pages[0].page_uuid))
        page = page_q.scalar_one()
        block_q = await db_session.execute(select(Block).where(Block.page_uuid == page.page_uuid))
        block = block_q.scalar_one()
        seg_q = await db_session.execute(
            select(Segment).where(Segment.block_uuid == block.block_uuid)
        )
        texts = [s.text_content for s in seg_q.scalars() if s.text_content]
        # Both paragraphs present (script/style content must be absent).
        joined = " | ".join(texts)
        assert "First H paragraph." in joined
        assert "Second H paragraph." in joined

    async def test_empty_txt_raises_empty_document(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        with pytest.raises(EmptyDocument):
            await _upload_one_chunk(
                db_session,
                project.project_uuid,
                filename="empty.txt",
                data=b"   \n\n   ",
            )

    async def test_malformed_xml_raises_text_extraction_error(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        with pytest.raises(TextExtractionError):
            await _upload_one_chunk(
                db_session,
                project.project_uuid,
                filename="bad.xml",
                data=b"<doc><p>unclosed",
            )


# ---------------------------------------------------------------------
# Rasterizer — refuses direct-text formats
# ---------------------------------------------------------------------


class TestRasterizeRefusesDirectText:
    def test_docx_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "x.docx"
        p.write_bytes(_docx_bytes(["a"]))
        with pytest.raises(PageOcrError, match="direct-text"):
            _rasterize_page(p, UploadFormat.DOCX, 1, dpi=200)

    def test_txt_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "x.txt"
        p.write_bytes(b"hello")
        with pytest.raises(PageOcrError, match="direct-text"):
            _rasterize_page(p, UploadFormat.TXT, 1, dpi=200)

    def test_html_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "x.html"
        p.write_bytes(b"<p>x</p>")
        with pytest.raises(PageOcrError, match="direct-text"):
            _rasterize_page(p, UploadFormat.HTML, 1, dpi=200)
