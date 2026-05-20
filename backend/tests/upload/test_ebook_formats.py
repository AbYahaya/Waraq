"""Phase 5 sub-batch K-3 — e-book upload formats.

Covers four layers:

1. `waraq.upload.file_type` — EPUB/MOBI/AZW/AZW3/DJVU added to the
   enum + suffix map; `is_direct_text_format` returns True for the
   four e-book direct-text formats and False for DjVu (which is
   raster-shaped). `count_pages` for DjVu uses `djvused` and raises
   `DjvuToolsMissing` cleanly when absent.
2. `waraq.upload.text_extraction.extract_paragraphs` — EPUB via
   ebooklib spine iteration; MOBI/AZW/AZW3 via the `mobi` lib's
   HTML extract.
3. `waraq.upload.service.finalize_upload` direct-text branch — EPUB
   upload materializes one Page (`ocr_status=GO`) + Block + Segments
   per paragraph; SCAN-PO `format=epub` + `skip_ocr=true`.
4. `waraq.ocr.page_runner._rasterize_page` — DjVu branch invokes
   `ddjvu`; refuses direct-text e-book formats with `PageOcrError`.

DjVu end-to-end finalize is NOT exercised in tests here because no
`djvulibre-bin` is installed on the test host. The detection /
page-count / rasterize paths cleanly raise `DjvuToolsMissing` and
`PageOcrError` when the tool is absent; that's what gets asserted.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project
from waraq.ocr.page_runner import PageOcrError, _rasterize_page
from waraq.schemas import Block, Page, ProvenanceObject, Segment
from waraq.schemas.enums import BlockClass, OcrStatus, POType
from waraq.upload import finalize_upload, start_upload
from waraq.upload.file_type import (
    DjvuToolsMissing,
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
# Fixture helpers — build EPUBs in-memory via ebooklib
# ---------------------------------------------------------------------


def _epub_bytes(chapters: list[tuple[str, list[str]]]) -> bytes:
    """Build a minimal EPUB. `chapters` = list of (title, paragraphs)."""
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("test-id-1")
    book.set_title("Test Book")
    book.set_language("en")

    items: list = []
    for i, (title, paragraphs) in enumerate(chapters):
        body = "".join(f"<p>{p}</p>" for p in paragraphs)
        chapter = epub.EpubHtml(
            title=title,
            file_name=f"ch{i}.xhtml",
            lang="en",
            content=(
                f"<html><head><title>{title}</title></head>"
                f"<body><h1>{title}</h1>{body}</body></html>"
            ),
        )
        book.add_item(chapter)
        items.append(chapter)
    book.spine = items
    book.toc = tuple(items)

    # NavMap + NCX scaffolding to satisfy strict EPUB validators.
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    buf = BytesIO()
    epub.write_epub(buf, book)
    return buf.getvalue()


def _empty_epub_bytes() -> bytes:
    """EPUB with one chapter that has no paragraphs — to exercise the
    EmptyDocument path."""
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("test-id-empty")
    book.set_title("Empty")
    book.set_language("en")
    ch = epub.EpubHtml(
        title="Empty",
        file_name="ch0.xhtml",
        lang="en",
        content="<html><body><p>   </p></body></html>",
    )
    book.add_item(ch)
    book.spine = [ch]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    buf = BytesIO()
    epub.write_epub(buf, book)
    return buf.getvalue()


# ---------------------------------------------------------------------
# file_type — suffix routing + DJVU + is_direct_text classification
# ---------------------------------------------------------------------


class TestDetectFormatEbooks:
    def test_epub_by_suffix(self) -> None:
        # EPUB shares ZIP magic with DOCX/ODT; suffix-authoritative.
        assert detect_format(filename="x.epub", head_bytes=b"PK\x03\x04stuff") == UploadFormat.EPUB

    def test_mobi_by_suffix(self) -> None:
        assert detect_format(filename="x.mobi", head_bytes=b"BOOKMOBI") == UploadFormat.MOBI

    def test_azw_by_suffix(self) -> None:
        assert detect_format(filename="x.azw", head_bytes=b"") == UploadFormat.AZW

    def test_azw3_by_suffix(self) -> None:
        assert detect_format(filename="x.azw3", head_bytes=b"") == UploadFormat.AZW3

    def test_djvu_by_suffix(self) -> None:
        # DjVu real magic starts with `AT&TFORM` but we don't check it
        # in v1.0 — suffix is reliable enough for this format.
        assert (
            detect_format(filename="x.djvu", head_bytes=b"AT&TFORM\x00\x00\x00\x10DJVU")
            == UploadFormat.DJVU
        )

    def test_djv_alias(self) -> None:
        assert detect_format(filename="x.djv", head_bytes=b"") == UploadFormat.DJVU


class TestIsDirectTextFormatEbooks:
    def test_djvu_is_not_direct_text(self) -> None:
        # DjVu is raster-shaped: it goes through `_finalize_binary` and
        # OCR via `ddjvu`, NOT through paragraph extraction.
        assert is_direct_text_format(UploadFormat.DJVU) is False

    def test_epub_mobi_azw_azw3_are_direct_text(self) -> None:
        for fmt in (
            UploadFormat.EPUB,
            UploadFormat.MOBI,
            UploadFormat.AZW,
            UploadFormat.AZW3,
        ):
            assert is_direct_text_format(fmt) is True, fmt

    def test_image_and_direct_text_predicates_stay_disjoint(self) -> None:
        for fmt in UploadFormat:
            assert not (is_direct_text_format(fmt) and is_image_format(fmt)), fmt


class TestCountPagesDjvu:
    def test_raises_djvu_tools_missing_when_djvused_absent(self, tmp_path: Path) -> None:
        # The test host doesn't have djvulibre-bin. `djvused` not on
        # PATH → DjvuToolsMissing with the install hint.
        p = tmp_path / "x.djvu"
        p.write_bytes(b"AT&TFORM\x00\x00\x00\x10DJVU")
        with pytest.raises(DjvuToolsMissing, match="djvused"):
            count_pages(path=p, fmt=UploadFormat.DJVU)


# ---------------------------------------------------------------------
# EPUB paragraph extraction
# ---------------------------------------------------------------------


class TestExtractEpub:
    def test_paragraphs_in_spine_order(self, tmp_path: Path) -> None:
        p = tmp_path / "x.epub"
        p.write_bytes(
            _epub_bytes(
                [
                    ("Chapter 1", ["First chapter paragraph."]),
                    (
                        "Chapter 2",
                        ["Second chapter paragraph one.", "Second chapter paragraph two."],
                    ),
                ]
            )
        )
        out = extract_paragraphs(path=p, fmt=UploadFormat.EPUB)
        # Each chapter title (<h1>) becomes its own block-level
        # paragraph too — accept any superset that includes our
        # body paragraphs in spine order.
        assert "First chapter paragraph." in out
        assert "Second chapter paragraph one." in out
        assert "Second chapter paragraph two." in out
        # Spine order: chapter 1's body must appear before chapter 2's.
        i1 = out.index("First chapter paragraph.")
        i2 = out.index("Second chapter paragraph one.")
        assert i1 < i2

    def test_arabic_text_preserved(self, tmp_path: Path) -> None:
        p = tmp_path / "x.epub"
        p.write_bytes(_epub_bytes([("Sura", ["بسم الله الرحمن الرحيم", "الحمد لله رب العالمين"])]))
        out = extract_paragraphs(path=p, fmt=UploadFormat.EPUB)
        assert "بسم الله الرحمن الرحيم" in out
        assert "الحمد لله رب العالمين" in out

    def test_empty_epub_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "x.epub"
        p.write_bytes(_empty_epub_bytes())
        with pytest.raises(EmptyDocument):
            extract_paragraphs(path=p, fmt=UploadFormat.EPUB)

    def test_malformed_epub_raises_text_extraction_error(self, tmp_path: Path) -> None:
        p = tmp_path / "x.epub"
        # Looks like a ZIP but is not a valid EPUB.
        p.write_bytes(b"PK\x03\x04not-an-epub")
        with pytest.raises(TextExtractionError):
            extract_paragraphs(path=p, fmt=UploadFormat.EPUB)


# ---------------------------------------------------------------------
# MOBI / AZW / AZW3 — error-path coverage (real MOBI generation needs
# Calibre and is heavyweight; we exercise the import-time + parse-fail
# paths deterministically)
# ---------------------------------------------------------------------


class TestExtractMobiFamily:
    def test_malformed_mobi_raises_text_extraction_error(self, tmp_path: Path) -> None:
        p = tmp_path / "x.mobi"
        p.write_bytes(b"not-a-real-mobi-file")
        with pytest.raises(TextExtractionError):
            extract_paragraphs(path=p, fmt=UploadFormat.MOBI)

    def test_malformed_azw_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "x.azw"
        p.write_bytes(b"not-a-real-azw")
        with pytest.raises(TextExtractionError):
            extract_paragraphs(path=p, fmt=UploadFormat.AZW)

    def test_malformed_azw3_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "x.azw3"
        p.write_bytes(b"not-a-real-azw3")
        with pytest.raises(TextExtractionError):
            extract_paragraphs(path=p, fmt=UploadFormat.AZW3)


class TestExtractRejectsNonEbook:
    def test_djvu_raises(self, tmp_path: Path) -> None:
        # DjVu is NOT a direct-text format — must raise.
        p = tmp_path / "x.djvu"
        p.write_bytes(b"AT&TFORM")
        with pytest.raises(TextExtractionError):
            extract_paragraphs(path=p, fmt=UploadFormat.DJVU)


# ---------------------------------------------------------------------
# End-to-end finalize: EPUB direct-text upload
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
class TestFinalizeEpub:
    async def test_epub_materializes_segments_in_spine_order(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        _, pages = await _upload_one_chunk(
            db_session,
            project.project_uuid,
            filename="book.epub",
            data=_epub_bytes(
                [
                    ("Ch1", ["Alpha paragraph."]),
                    ("Ch2", ["Beta paragraph.", "Gamma paragraph."]),
                ]
            ),
        )
        assert len(pages) == 1
        page_q = await db_session.execute(select(Page).where(Page.page_uuid == pages[0].page_uuid))
        page = page_q.scalar_one()
        assert page.ocr_status == OcrStatus.GO

        block_q = await db_session.execute(select(Block).where(Block.page_uuid == page.page_uuid))
        block = block_q.scalar_one()
        assert block.block_type == BlockClass.MAIN_TEXT.value

        seg_q = await db_session.execute(
            select(Segment)
            .where(Segment.block_uuid == block.block_uuid)
            .order_by(Segment.satz_index.asc())
        )
        texts = [s.text_content for s in seg_q.scalars()]
        # Spine order preserved across body paragraphs.
        assert "Alpha paragraph." in texts
        assert "Beta paragraph." in texts
        assert "Gamma paragraph." in texts
        assert texts.index("Alpha paragraph.") < texts.index("Beta paragraph.")
        assert texts.index("Beta paragraph.") < texts.index("Gamma paragraph.")

        # SCAN-PO: format=epub, skip_ocr=true.
        po_q = await db_session.execute(
            select(ProvenanceObject)
            .where(ProvenanceObject.po_type == POType.SCAN.value)
            .where(ProvenanceObject.scope_uuid == page.page_uuid)
        )
        po = po_q.scalar_one()
        assert po.payload["format"] == "epub"
        assert po.payload["skip_ocr"] is True

    async def test_empty_epub_raises_empty_document(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        with pytest.raises(EmptyDocument):
            await _upload_one_chunk(
                db_session,
                project.project_uuid,
                filename="empty.epub",
                data=_empty_epub_bytes(),
            )


# ---------------------------------------------------------------------
# Rasterizer — DjVu branch refuses cleanly without ddjvu;
# direct-text e-book formats are refused outright.
# ---------------------------------------------------------------------


class TestRasterizeDjvu:
    def test_djvu_without_ddjvu_raises_page_ocr_error(self, tmp_path: Path) -> None:
        # ddjvu not on PATH in the test host → PageOcrError with the
        # install hint.
        p = tmp_path / "x.djvu"
        p.write_bytes(b"AT&TFORM\x00\x00\x00\x10DJVU")
        with pytest.raises(PageOcrError, match="ddjvu"):
            _rasterize_page(p, UploadFormat.DJVU, 1, dpi=200)


class TestRasterizeRefusesEbookDirectText:
    def test_epub_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "x.epub"
        p.write_bytes(b"PK\x03\x04")
        with pytest.raises(PageOcrError, match="direct-text"):
            _rasterize_page(p, UploadFormat.EPUB, 1, dpi=200)

    def test_mobi_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "x.mobi"
        p.write_bytes(b"BOOKMOBI")
        with pytest.raises(PageOcrError, match="direct-text"):
            _rasterize_page(p, UploadFormat.MOBI, 1, dpi=200)

    def test_azw3_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "x.azw3"
        p.write_bytes(b"")
        with pytest.raises(PageOcrError, match="direct-text"):
            _rasterize_page(p, UploadFormat.AZW3, 1, dpi=200)
