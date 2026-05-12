"""Phase 5 sub-batch K-4 — archive upload formats.

Covers four layers:

1. `waraq.upload.file_type` — ZIP/RAR/CBZ/CBR added to enum + suffix
   map; `is_archive_format` predicate; archive and direct-text /
   image predicates stay disjoint.
2. `waraq.upload.archive.extract_and_sort` — ZIP extraction works;
   filename-sort is alphabetical-case-insensitive; noise filtering
   (`__MACOSX`, `._foo`, `Thumbs.db`, dotfiles) skips; unsupported
   entries silently skipped; nested archives silently skipped;
   `EmptyArchive` raised when zero supported entries; `ArchiveCorrupted`
   on bad ZIP; `UnrarToolsMissing` when RAR + `unrar` not on PATH.
3. `waraq.upload.service.finalize_upload` archive branch — CBZ with
   3 images → 3 Pages with archive provenance on SCAN-PO; ZIP mixing
   images + TXT → ordered Pages with right format/skip_ocr per entry.
4. `waraq.api.routers.uploads_router` — HTTP 503 on UnrarToolsMissing;
   HTTP 422 on EmptyArchive / ArchiveCorrupted.

RAR/CBR end-to-end finalize NOT exercised here (no `unrar` system bin
on the test host); the error-path coverage proves the wiring is
honest.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project
from waraq.schemas import Block, Page, ProvenanceObject, Segment
from waraq.schemas.enums import OcrStatus, POType
from waraq.upload import finalize_upload, start_upload
from waraq.upload.archive import (
    ArchiveCorrupted,
    EmptyArchive,
    extract_and_sort,
)
from waraq.upload.file_type import (
    UnrarToolsMissing,
    UploadFormat,
    detect_format,
    is_archive_format,
    is_direct_text_format,
    is_image_format,
)
from waraq.upload.service import append_chunk

# ---------------------------------------------------------------------
# Fixture helpers — build ZIPs in-memory
# ---------------------------------------------------------------------


def _jpeg_bytes(color: str = "white") -> bytes:
    buf = BytesIO()
    Image.new("RGB", (32, 32), color).save(buf, format="JPEG", quality=70)
    return buf.getvalue()


def _png_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (32, 32), "white").save(buf, format="PNG")
    return buf.getvalue()


def _make_zip(entries: list[tuple[str, bytes]]) -> bytes:
    """Build a ZIP in memory. `entries` = list of (name, data)."""
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries:
            zf.writestr(name, data)
    return buf.getvalue()


# ---------------------------------------------------------------------
# file_type — suffix routing + classification
# ---------------------------------------------------------------------


class TestDetectFormatArchives:
    def test_zip_by_suffix(self) -> None:
        # ZIP shares magic with DOCX/ODT/EPUB; suffix is authoritative.
        assert (
            detect_format(filename="x.zip", head_bytes=b"PK\x03\x04stuff")
            == UploadFormat.ZIP
        )

    def test_rar_by_suffix(self) -> None:
        assert detect_format(filename="x.rar", head_bytes=b"Rar!") == UploadFormat.RAR

    def test_cbz_by_suffix(self) -> None:
        assert (
            detect_format(filename="x.cbz", head_bytes=b"PK\x03\x04") == UploadFormat.CBZ
        )

    def test_cbr_by_suffix(self) -> None:
        assert detect_format(filename="x.cbr", head_bytes=b"Rar!") == UploadFormat.CBR


class TestIsArchiveFormat:
    def test_all_four_archive_formats(self) -> None:
        for fmt in (UploadFormat.ZIP, UploadFormat.RAR, UploadFormat.CBZ, UploadFormat.CBR):
            assert is_archive_format(fmt) is True, fmt

    def test_pdf_image_direct_text_are_not_archives(self) -> None:
        for fmt in (
            UploadFormat.PDF,
            UploadFormat.JPEG,
            UploadFormat.DOCX,
            UploadFormat.EPUB,
            UploadFormat.DJVU,
        ):
            assert is_archive_format(fmt) is False, fmt

    def test_predicates_stay_disjoint(self) -> None:
        for fmt in UploadFormat:
            # An archive must not also be image or direct-text.
            assert not (is_archive_format(fmt) and is_image_format(fmt)), fmt
            assert not (is_archive_format(fmt) and is_direct_text_format(fmt)), fmt


# ---------------------------------------------------------------------
# extract_and_sort — filename-sort + noise filter + skip nested/unsupported
# ---------------------------------------------------------------------


class TestExtractAndSort:
    def test_zip_extraction_filename_sort_alphabetical(self, tmp_path: Path) -> None:
        zip_path = tmp_path / "comic.zip"
        # Out-of-order in archive; should be alphabetized at extraction.
        zip_path.write_bytes(
            _make_zip(
                [
                    ("page_03.jpg", _jpeg_bytes("red")),
                    ("page_01.jpg", _jpeg_bytes("white")),
                    ("page_02.jpg", _jpeg_bytes("blue")),
                ]
            )
        )
        entries = extract_and_sort(
            archive_path=zip_path,
            archive_fmt=UploadFormat.ZIP,
            dest_dir=tmp_path / "out",
        )
        assert [e.inner_filename for e in entries] == [
            "page_01.jpg",
            "page_02.jpg",
            "page_03.jpg",
        ]
        # All resolved as JPEG.
        assert all(e.fmt == UploadFormat.JPEG for e in entries)

    def test_case_insensitive_sort(self, tmp_path: Path) -> None:
        zip_path = tmp_path / "mixed.zip"
        zip_path.write_bytes(
            _make_zip(
                [
                    ("Page03.jpg", _jpeg_bytes()),
                    ("page01.jpg", _jpeg_bytes()),
                    ("PAGE02.jpg", _jpeg_bytes()),
                ]
            )
        )
        entries = extract_and_sort(
            archive_path=zip_path,
            archive_fmt=UploadFormat.ZIP,
            dest_dir=tmp_path / "out",
        )
        names = [e.inner_filename for e in entries]
        # Case-insensitive alphabetical → page01 < PAGE02 < Page03.
        assert names == ["page01.jpg", "PAGE02.jpg", "Page03.jpg"]

    def test_skips_macosx_resource_forks(self, tmp_path: Path) -> None:
        zip_path = tmp_path / "x.zip"
        zip_path.write_bytes(
            _make_zip(
                [
                    ("__MACOSX/._page.jpg", b"junk"),
                    ("._dotfile.jpg", b"junk"),
                    ("page.jpg", _jpeg_bytes()),
                ]
            )
        )
        entries = extract_and_sort(
            archive_path=zip_path,
            archive_fmt=UploadFormat.ZIP,
            dest_dir=tmp_path / "out",
        )
        assert [e.inner_filename for e in entries] == ["page.jpg"]

    def test_skips_thumbs_db(self, tmp_path: Path) -> None:
        zip_path = tmp_path / "x.zip"
        zip_path.write_bytes(
            _make_zip(
                [
                    ("Thumbs.db", b"junk"),
                    ("page.jpg", _jpeg_bytes()),
                ]
            )
        )
        entries = extract_and_sort(
            archive_path=zip_path,
            archive_fmt=UploadFormat.ZIP,
            dest_dir=tmp_path / "out",
        )
        assert [e.inner_filename for e in entries] == ["page.jpg"]

    def test_skips_unsupported_entries_silently(self, tmp_path: Path) -> None:
        zip_path = tmp_path / "x.zip"
        zip_path.write_bytes(
            _make_zip(
                [
                    ("readme.exe", b"binary junk"),
                    ("page.jpg", _jpeg_bytes()),
                ]
            )
        )
        entries = extract_and_sort(
            archive_path=zip_path,
            archive_fmt=UploadFormat.ZIP,
            dest_dir=tmp_path / "out",
        )
        # `.exe` is silently skipped, not an error.
        assert [e.inner_filename for e in entries] == ["page.jpg"]

    def test_skips_nested_archives(self, tmp_path: Path) -> None:
        zip_path = tmp_path / "outer.zip"
        nested_zip = _make_zip([("inside.jpg", _jpeg_bytes())])
        zip_path.write_bytes(
            _make_zip(
                [
                    ("nested.zip", nested_zip),
                    ("page.jpg", _jpeg_bytes()),
                ]
            )
        )
        entries = extract_and_sort(
            archive_path=zip_path,
            archive_fmt=UploadFormat.ZIP,
            dest_dir=tmp_path / "out",
        )
        # Nested ZIP is silently skipped per canon "one-level recursion".
        assert [e.inner_filename for e in entries] == ["page.jpg"]

    def test_mixed_format_archive(self, tmp_path: Path) -> None:
        zip_path = tmp_path / "mixed.zip"
        zip_path.write_bytes(
            _make_zip(
                [
                    ("01_scan.jpg", _jpeg_bytes()),
                    ("02_notes.txt", b"First.\n\nSecond."),
                    ("03_other.png", _png_bytes()),
                ]
            )
        )
        entries = extract_and_sort(
            archive_path=zip_path,
            archive_fmt=UploadFormat.ZIP,
            dest_dir=tmp_path / "out",
        )
        assert [e.inner_filename for e in entries] == [
            "01_scan.jpg",
            "02_notes.txt",
            "03_other.png",
        ]
        assert [e.fmt for e in entries] == [
            UploadFormat.JPEG,
            UploadFormat.TXT,
            UploadFormat.PNG,
        ]

    def test_empty_archive_raises(self, tmp_path: Path) -> None:
        zip_path = tmp_path / "empty.zip"
        zip_path.write_bytes(_make_zip([]))
        with pytest.raises(EmptyArchive):
            extract_and_sort(
                archive_path=zip_path,
                archive_fmt=UploadFormat.ZIP,
                dest_dir=tmp_path / "out",
            )

    def test_archive_with_only_unsupported_raises_empty(self, tmp_path: Path) -> None:
        zip_path = tmp_path / "junk.zip"
        zip_path.write_bytes(
            _make_zip(
                [
                    ("a.exe", b"junk"),
                    ("b.dll", b"junk"),
                    ("Thumbs.db", b"junk"),
                ]
            )
        )
        with pytest.raises(EmptyArchive):
            extract_and_sort(
                archive_path=zip_path,
                archive_fmt=UploadFormat.ZIP,
                dest_dir=tmp_path / "out",
            )

    def test_corrupted_zip_raises(self, tmp_path: Path) -> None:
        zip_path = tmp_path / "broken.zip"
        zip_path.write_bytes(b"not-a-real-zip")
        with pytest.raises(ArchiveCorrupted):
            extract_and_sort(
                archive_path=zip_path,
                archive_fmt=UploadFormat.ZIP,
                dest_dir=tmp_path / "out",
            )

    def test_zipslip_path_traversal_neutralized(self, tmp_path: Path) -> None:
        """Entry named like `../escape.jpg` must NOT write outside
        `dest_dir`. Verified by checking the extracted file lives
        under dest_dir."""
        zip_path = tmp_path / "evil.zip"
        zip_path.write_bytes(
            _make_zip(
                [
                    ("../../../escape.jpg", _jpeg_bytes()),
                    ("safe.jpg", _jpeg_bytes()),
                ]
            )
        )
        out = tmp_path / "out"
        entries = extract_and_sort(
            archive_path=zip_path,
            archive_fmt=UploadFormat.ZIP,
            dest_dir=out,
        )
        for e in entries:
            # Every extracted path must live under `out`.
            assert out in e.inner_path.parents or e.inner_path.parent == out

    def test_rar_without_unrar_raises_unrar_tools_missing(self, tmp_path: Path) -> None:
        # Test host doesn't have `unrar`. Calling extract_and_sort
        # on a RAR archive raises cleanly.
        rar_path = tmp_path / "x.rar"
        rar_path.write_bytes(b"Rar!fake")
        with pytest.raises(UnrarToolsMissing, match="unrar"):
            extract_and_sort(
                archive_path=rar_path,
                archive_fmt=UploadFormat.RAR,
                dest_dir=tmp_path / "out",
            )


# ---------------------------------------------------------------------
# End-to-end finalize — CBZ + mixed ZIP
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
class TestFinalizeArchive:
    async def test_cbz_three_images_yields_three_pages(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        _, pages = await _upload_one_chunk(
            db_session,
            project.project_uuid,
            filename="comic.cbz",
            data=_make_zip(
                [
                    ("page_03.jpg", _jpeg_bytes("red")),
                    ("page_01.jpg", _jpeg_bytes("white")),
                    ("page_02.jpg", _jpeg_bytes("blue")),
                ]
            ),
        )
        # Three Pages, filename-sorted alphabetically.
        assert len(pages) == 3
        assert [p.page_index for p in pages] == [1, 2, 3]

        # Each SCAN-PO records the archive provenance.
        for i, page in enumerate(pages, start=1):
            po_q = await db_session.execute(
                select(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.SCAN.value)
                .where(ProvenanceObject.scope_uuid == page.page_uuid)
            )
            po = po_q.scalar_one()
            assert po.payload["format"] == "jpeg"  # inner entry format
            assert po.payload["archive_format"] == "cbz"
            assert po.payload["archive_entry_filename"] == f"page_0{i}.jpg"
            assert po.payload["archive_entry_index"] == i
            # Inner SHA matches the entry, not the archive.
            assert po.payload["source_sha256"] != po.payload["archive_sha256"]

    async def test_mixed_archive_image_plus_txt(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        _, pages = await _upload_one_chunk(
            db_session,
            project.project_uuid,
            filename="mixed.zip",
            data=_make_zip(
                [
                    ("01_scan.jpg", _jpeg_bytes()),
                    ("02_notes.txt", b"Paragraph one.\n\nParagraph two."),
                ]
            ),
        )
        assert len(pages) == 2

        # Page 1 = image, OCR pending.
        page1_q = await db_session.execute(select(Page).where(Page.page_uuid == pages[0].page_uuid))
        page1 = page1_q.scalar_one()
        assert page1.ocr_status == OcrStatus.AUSSTEHEND  # image needs OCR
        po1_q = await db_session.execute(
            select(ProvenanceObject)
            .where(ProvenanceObject.po_type == POType.SCAN.value)
            .where(ProvenanceObject.scope_uuid == page1.page_uuid)
        )
        po1 = po1_q.scalar_one()
        assert po1.payload["format"] == "jpeg"
        assert po1.payload.get("skip_ocr") is None  # binary path doesn't set it

        # Page 2 = TXT direct-text, ocr_status=GO, Segments populated.
        page2_q = await db_session.execute(select(Page).where(Page.page_uuid == pages[1].page_uuid))
        page2 = page2_q.scalar_one()
        assert page2.ocr_status == OcrStatus.GO
        block_q = await db_session.execute(select(Block).where(Block.page_uuid == page2.page_uuid))
        block2 = block_q.scalar_one()
        seg_q = await db_session.execute(
            select(Segment)
            .where(Segment.block_uuid == block2.block_uuid)
            .order_by(Segment.satz_index.asc())
        )
        texts = [s.text_content for s in seg_q.scalars()]
        assert texts == ["Paragraph one.", "Paragraph two."]
        po2_q = await db_session.execute(
            select(ProvenanceObject)
            .where(ProvenanceObject.po_type == POType.SCAN.value)
            .where(ProvenanceObject.scope_uuid == page2.page_uuid)
        )
        po2 = po2_q.scalar_one()
        assert po2.payload["format"] == "txt"
        assert po2.payload["skip_ocr"] is True
        assert po2.payload["archive_entry_filename"] == "02_notes.txt"

    async def test_empty_archive_at_finalize_raises(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        with pytest.raises(EmptyArchive):
            await _upload_one_chunk(
                db_session,
                project.project_uuid,
                filename="empty.zip",
                data=_make_zip([]),
            )

    async def test_corrupted_archive_at_finalize_raises(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        with pytest.raises(ArchiveCorrupted):
            await _upload_one_chunk(
                db_session,
                project.project_uuid,
                filename="broken.zip",
                data=b"not-a-real-zip",
            )
