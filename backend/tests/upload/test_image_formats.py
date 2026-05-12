"""Phase 5 sub-batch K-1 — image upload formats.

Covers four orthogonal layers:

1. `waraq.upload.file_type.detect_format` — suffix + magic-byte
   resolution + `UnsupportedFormat` on neither.
2. `waraq.upload.file_type.count_pages` — single-image = 1; multi-page
   TIFF = N; PDF = pypdf count.
3. End-to-end `finalize_upload` for single-image + multi-page TIFF —
   correct number of Page rows materialized + SCAN-POs carry the
   right `format` value.
4. `waraq.ocr.page_runner._rasterize_page` — image branch returns
   non-empty PNG bytes; TIFF frame extraction picks the right frame.

HEIC tests use the `pillow-heif` opener registered by
`waraq.upload`'s module-level side-effect.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project
from waraq.ocr.page_runner import _rasterize_page
from waraq.schemas import ProvenanceObject
from waraq.schemas.enums import POType
from waraq.upload import finalize_upload, start_upload
from waraq.upload.file_type import (
    UnsupportedFormat,
    UploadFormat,
    count_pages,
    detect_format,
    is_image_format,
)
from waraq.upload.service import _source_path, append_chunk

# ---------------------------------------------------------------------
# Fixture helpers — build images in-memory so tests are hermetic.
# ---------------------------------------------------------------------


def _png_bytes(size: tuple[int, int] = (64, 64), color: str = "white") -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes(size: tuple[int, int] = (64, 64)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, "white").save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def _webp_bytes(size: tuple[int, int] = (64, 64)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, "white").save(buf, format="WEBP")
    return buf.getvalue()


def _tiff_bytes(n_frames: int = 1, size: tuple[int, int] = (64, 64)) -> bytes:
    """Multi-frame TIFF — n_frames pages."""
    frames = [Image.new("RGB", size, c) for c in (["white", "black", "red"][:n_frames])]
    while len(frames) < n_frames:
        frames.append(Image.new("RGB", size, "gray"))
    buf = BytesIO()
    frames[0].save(buf, format="TIFF", save_all=True, append_images=frames[1:])
    return buf.getvalue()


def _heic_bytes(size: tuple[int, int] = (64, 64)) -> bytes:
    """HEIC via pillow-heif's encoder. Skipped if pillow-heif missing."""
    try:
        import pillow_heif  # noqa: F401
    except ImportError:
        pytest.skip("pillow-heif not installed; HEIC tests unreachable")
    buf = BytesIO()
    Image.new("RGB", size, "white").save(buf, format="HEIF")
    return buf.getvalue()


# ---------------------------------------------------------------------
# detect_format — suffix + magic resolution
# ---------------------------------------------------------------------


class TestDetectFormat:
    def test_pdf_by_magic(self) -> None:
        assert detect_format(filename="x.bin", head_bytes=b"%PDF-1.7\n") == UploadFormat.PDF

    def test_jpeg_by_magic(self) -> None:
        assert (
            detect_format(filename="x.bin", head_bytes=_jpeg_bytes()[:16]) == UploadFormat.JPEG
        )

    def test_png_by_magic(self) -> None:
        assert (
            detect_format(filename="x.bin", head_bytes=_png_bytes()[:16]) == UploadFormat.PNG
        )

    def test_tiff_by_magic_little_endian(self) -> None:
        assert (
            detect_format(filename="x.bin", head_bytes=b"II*\x00\x00\x00\x00\x00")
            == UploadFormat.TIFF
        )

    def test_tiff_by_magic_big_endian(self) -> None:
        assert (
            detect_format(filename="x.bin", head_bytes=b"MM\x00*\x00\x00\x00\x00")
            == UploadFormat.TIFF
        )

    def test_webp_by_magic(self) -> None:
        head = b"RIFF\x00\x00\x00\x00WEBPVP8 "
        assert detect_format(filename="x.bin", head_bytes=head) == UploadFormat.WEBP

    def test_webp_riff_without_webp_brand_not_matched(self) -> None:
        # RIFF<size>WAVE is a WAV file; we don't accept it.
        with pytest.raises(UnsupportedFormat):
            detect_format(
                filename="x.bin",
                head_bytes=b"RIFF\x00\x00\x00\x00WAVEfmt ",
            )

    def test_heic_by_magic_box_brand(self) -> None:
        head = b"\x00\x00\x00\x20ftypheic\x00\x00\x00\x00mif1heic"
        assert detect_format(filename="x.bin", head_bytes=head) == UploadFormat.HEIC

    def test_heic_brand_msf1_also_accepted(self) -> None:
        head = b"\x00\x00\x00\x20ftypmsf1\x00\x00\x00\x00"
        assert detect_format(filename="x.bin", head_bytes=head) == UploadFormat.HEIC

    def test_unknown_suffix_unknown_magic_raises(self) -> None:
        # `.exe` is outside the canon §2.1 supported set entirely
        # (never PDF, image, document, e-book, or archive); its bytes
        # match no recognized magic signature.
        with pytest.raises(UnsupportedFormat):
            detect_format(filename="x.exe", head_bytes=b"MZ\x90\x00")

    def test_suffix_only_resolution_when_magic_short(self) -> None:
        # Empty / short file → magic match fails, suffix wins.
        assert detect_format(filename="x.jpg", head_bytes=b"") == UploadFormat.JPEG

    def test_magic_wins_over_misnamed_suffix(self) -> None:
        # `book.pdf` whose body is actually a JPEG — magic must win.
        assert (
            detect_format(filename="book.pdf", head_bytes=_jpeg_bytes()[:16])
            == UploadFormat.JPEG
        )

    def test_jpeg_jpg_extensions_alias(self) -> None:
        assert detect_format(filename="x.jpg", head_bytes=b"") == UploadFormat.JPEG
        assert detect_format(filename="x.jpeg", head_bytes=b"") == UploadFormat.JPEG

    def test_tiff_tif_extensions_alias(self) -> None:
        assert detect_format(filename="x.tif", head_bytes=b"") == UploadFormat.TIFF
        assert detect_format(filename="x.tiff", head_bytes=b"") == UploadFormat.TIFF


# ---------------------------------------------------------------------
# count_pages — multi-page TIFF + single-image semantics
# ---------------------------------------------------------------------


class TestCountPages:
    def test_jpeg_is_one_page(self, tmp_path: Path) -> None:
        p = tmp_path / "x.jpg"
        p.write_bytes(_jpeg_bytes())
        assert count_pages(path=p, fmt=UploadFormat.JPEG) == 1

    def test_png_is_one_page(self, tmp_path: Path) -> None:
        p = tmp_path / "x.png"
        p.write_bytes(_png_bytes())
        assert count_pages(path=p, fmt=UploadFormat.PNG) == 1

    def test_webp_is_one_page(self, tmp_path: Path) -> None:
        p = tmp_path / "x.webp"
        p.write_bytes(_webp_bytes())
        assert count_pages(path=p, fmt=UploadFormat.WEBP) == 1

    def test_single_page_tiff(self, tmp_path: Path) -> None:
        p = tmp_path / "x.tif"
        p.write_bytes(_tiff_bytes(n_frames=1))
        assert count_pages(path=p, fmt=UploadFormat.TIFF) == 1

    def test_multi_page_tiff_three_frames(self, tmp_path: Path) -> None:
        p = tmp_path / "x.tif"
        p.write_bytes(_tiff_bytes(n_frames=3))
        assert count_pages(path=p, fmt=UploadFormat.TIFF) == 3

    def test_heic_is_one_page(self, tmp_path: Path) -> None:
        p = tmp_path / "x.heic"
        p.write_bytes(_heic_bytes())
        assert count_pages(path=p, fmt=UploadFormat.HEIC) == 1


class TestIsImageFormat:
    def test_pdf_is_not_image(self) -> None:
        assert is_image_format(UploadFormat.PDF) is False

    def test_every_other_format_is_image(self) -> None:
        for fmt in (
            UploadFormat.JPEG,
            UploadFormat.PNG,
            UploadFormat.TIFF,
            UploadFormat.HEIC,
            UploadFormat.WEBP,
        ):
            assert is_image_format(fmt) is True, fmt


# ---------------------------------------------------------------------
# End-to-end finalize: image upload materializes the right rows
# ---------------------------------------------------------------------


async def _upload_one_chunk(
    session: AsyncSession,
    project_uuid,
    *,
    filename: str,
    data: bytes,
):
    """Helper: drive the chunked upload service with a single chunk.
    Returns the finalized Page list."""
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
class TestFinalizeImageUpload:
    async def test_jpeg_materializes_one_page(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        job, pages = await _upload_one_chunk(
            db_session,
            project.project_uuid,
            filename="scan.jpg",
            data=_jpeg_bytes(),
        )
        assert len(pages) == 1
        assert pages[0].page_index == 1
        # SCAN-PO records the format.
        po = await db_session.execute(
            select(ProvenanceObject)
            .where(ProvenanceObject.po_type == POType.SCAN.value)
            .where(ProvenanceObject.scope_uuid == pages[0].page_uuid)
        )
        scan_po = po.scalar_one()
        assert scan_po.payload["format"] == "jpeg"
        _ = job

    async def test_png_materializes_one_page(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        _, pages = await _upload_one_chunk(
            db_session,
            project.project_uuid,
            filename="scan.png",
            data=_png_bytes(),
        )
        assert len(pages) == 1

    async def test_multi_page_tiff_materializes_n_pages(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        _, pages = await _upload_one_chunk(
            db_session,
            project.project_uuid,
            filename="book.tif",
            data=_tiff_bytes(n_frames=3),
        )
        assert len(pages) == 3
        assert [p.page_index for p in pages] == [1, 2, 3]
        # All three SCAN-POs share the same source path; each records
        # its own page_index_in_source.
        for page in pages:
            po = await db_session.execute(
                select(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.SCAN.value)
                .where(ProvenanceObject.scope_uuid == page.page_uuid)
            )
            scan_po = po.scalar_one()
            assert scan_po.payload["format"] == "tiff"
            assert scan_po.payload["page_index_in_source"] == page.page_index

    async def test_webp_materializes_one_page(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        _, pages = await _upload_one_chunk(
            db_session,
            project.project_uuid,
            filename="scan.webp",
            data=_webp_bytes(),
        )
        assert len(pages) == 1
        po = await db_session.execute(
            select(ProvenanceObject)
            .where(ProvenanceObject.po_type == POType.SCAN.value)
            .where(ProvenanceObject.scope_uuid == pages[0].page_uuid)
        )
        scan_po = po.scalar_one()
        assert scan_po.payload["format"] == "webp"

    async def test_heic_materializes_one_page(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        _, pages = await _upload_one_chunk(
            db_session,
            project.project_uuid,
            filename="phone-scan.heic",
            data=_heic_bytes(),
        )
        assert len(pages) == 1
        po = await db_session.execute(
            select(ProvenanceObject)
            .where(ProvenanceObject.po_type == POType.SCAN.value)
            .where(ProvenanceObject.scope_uuid == pages[0].page_uuid)
        )
        scan_po = po.scalar_one()
        assert scan_po.payload["format"] == "heic"

    async def test_unsupported_format_returns_415_at_finalize(
        self, db_session: AsyncSession
    ) -> None:
        from waraq.upload.file_type import UnsupportedFormat

        project = await seed_project(db_session)
        # `.exe` is outside canon §2.1's supported set entirely.
        # Finalize must raise `UnsupportedFormat` (router → HTTP 415).
        with pytest.raises(UnsupportedFormat):
            await _upload_one_chunk(
                db_session,
                project.project_uuid,
                filename="program.exe",
                data=b"MZ\x90\x00fake-pe-header",
            )


# ---------------------------------------------------------------------
# Rasterizer — image branch returns PNG bytes; TIFF picks the right frame
# ---------------------------------------------------------------------


class TestRasterizeImage:
    def test_jpeg_rasterize_returns_png(self, tmp_path: Path) -> None:
        p = tmp_path / "x.jpg"
        p.write_bytes(_jpeg_bytes())
        out = _rasterize_page(p, UploadFormat.JPEG, 1, dpi=200)
        # PNG signature at byte 0.
        assert out[:8] == b"\x89PNG\r\n\x1a\n"

    def test_png_rasterize_passthrough(self, tmp_path: Path) -> None:
        p = tmp_path / "x.png"
        p.write_bytes(_png_bytes())
        out = _rasterize_page(p, UploadFormat.PNG, 1, dpi=200)
        # Even passthrough re-encodes via PIL → still PNG.
        assert out[:8] == b"\x89PNG\r\n\x1a\n"

    def test_tiff_frame_one(self, tmp_path: Path) -> None:
        p = tmp_path / "x.tif"
        p.write_bytes(_tiff_bytes(n_frames=3))
        out = _rasterize_page(p, UploadFormat.TIFF, 1, dpi=200)
        assert out[:8] == b"\x89PNG\r\n\x1a\n"

    def test_tiff_frame_three_distinct_from_frame_one(self, tmp_path: Path) -> None:
        p = tmp_path / "x.tif"
        p.write_bytes(_tiff_bytes(n_frames=3))
        f1 = _rasterize_page(p, UploadFormat.TIFF, 1, dpi=200)
        f3 = _rasterize_page(p, UploadFormat.TIFF, 3, dpi=200)
        # Different frames → different PNG bytes (white vs gray fill).
        assert f1 != f3

    def test_tiff_out_of_range_raises(self, tmp_path: Path) -> None:
        from waraq.ocr.page_runner import PageOcrError

        p = tmp_path / "x.tif"
        p.write_bytes(_tiff_bytes(n_frames=2))
        with pytest.raises(PageOcrError):
            _rasterize_page(p, UploadFormat.TIFF, 99, dpi=200)

    def test_single_image_with_wrong_page_index_raises(self, tmp_path: Path) -> None:
        from waraq.ocr.page_runner import PageOcrError

        p = tmp_path / "x.jpg"
        p.write_bytes(_jpeg_bytes())
        with pytest.raises(PageOcrError):
            _rasterize_page(p, UploadFormat.JPEG, 2, dpi=200)


# Silence unused-import lint for `_source_path` which the helper
# above relies on transitively via `_upload_one_chunk`.
_ = _source_path
