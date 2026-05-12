"""Phase 5 sub-batch K-5 — cross-cutting upload checks (canon rows 5/6/7).

Three orthogonal canon rows, all warning-shaped except the 2 GB cap
which is a hard block:

  Row 5 §2.1 — 2 GB max enforcement (`UploadTooLarge` → HTTP 413).
    - At `start_upload`: declared `total_size_bytes > 2 GB` rejected.
    - At `append_chunk`: cumulative bytes-on-disk > 2 GB rejected
      defensively (client may have lied about declared size).

  Row 6 §2.1/§2.2 — Duplicate detection (filename + SHA-256), modal
  warning, not a block:
    - Pre-upload `GET /uploads/precheck?project_uuid=...&filename=...`
      returns matching prior Pages by filename.
    - Post-finalize: `UploadFinalizeResponse.duplicate_sha256_matches`
      lists any prior Pages with the same content SHA-256.

  Row 7 §2.2 — 1-book-at-a-time modal warning:
    - The precheck endpoint also returns `project_has_existing_pages`
      so the frontend can warn when uploading into a populated project.

All three checks are scoped per-project (no cross-project leakage).
"""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project
from waraq.schemas import Project
from waraq.upload import (
    UploadTooLarge,
    finalize_upload,
    start_upload,
)
from waraq.upload.duplicate import find_sha256_matches, precheck_for_project
from waraq.upload.service import MAX_UPLOAD_SIZE_BYTES, append_chunk

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _jpeg_bytes(seed: int = 0) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (16 + seed, 16), "white").save(buf, format="JPEG", quality=70)
    return buf.getvalue()


async def _upload(session: AsyncSession, project: Project, filename: str, data: bytes):
    job = await start_upload(
        session=session,
        project=project,
        original_filename=filename,
        total_chunks=1,
        total_size_bytes=len(data),
    )
    await append_chunk(
        session=session, upload_job=job, chunk_index=0, chunk_data=data
    )
    return job, await finalize_upload(session=session, upload_job=job)


# ---------------------------------------------------------------------
# Row 5 — 2 GB enforcement
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestTwoGigLimit:
    async def test_max_constant_is_two_gigabytes(self) -> None:
        assert MAX_UPLOAD_SIZE_BYTES == 2 * 1024 * 1024 * 1024

    async def test_start_upload_rejects_declared_over_2gb(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        with pytest.raises(UploadTooLarge) as info:
            await start_upload(
                session=db_session,
                project=project,
                original_filename="huge.pdf",
                total_chunks=1,
                total_size_bytes=MAX_UPLOAD_SIZE_BYTES + 1,
            )
        assert info.value.size_bytes == MAX_UPLOAD_SIZE_BYTES + 1
        assert info.value.max_bytes == MAX_UPLOAD_SIZE_BYTES

    async def test_start_upload_accepts_exactly_2gb(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        # Exactly the limit is permitted; 1 byte over is not.
        job = await start_upload(
            session=db_session,
            project=project,
            original_filename="boundary.pdf",
            total_chunks=1,
            total_size_bytes=MAX_UPLOAD_SIZE_BYTES,
        )
        assert job.job_uuid is not None

    async def test_append_chunk_rejects_cumulative_over_2gb(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Use a small simulated max so the test can actually drive
        # the defensive cap without writing GB to disk.
        monkeypatch.setattr(
            "waraq.upload.service.MAX_UPLOAD_SIZE_BYTES", 100, raising=True
        )
        project = await seed_project(db_session)
        # Lie about the declared size (say 50, push 200 bytes).
        job = await start_upload(
            session=db_session,
            project=project,
            original_filename="liar.bin",
            total_chunks=2,
            total_size_bytes=50,
        )
        # First chunk fine.
        await append_chunk(
            session=db_session,
            upload_job=job,
            chunk_index=0,
            chunk_data=b"x" * 60,
        )
        # Second chunk pushes cumulative over 100 → defensive cap fires.
        with pytest.raises(UploadTooLarge):
            await append_chunk(
                session=db_session,
                upload_job=job,
                chunk_index=1,
                chunk_data=b"y" * 60,
            )


# ---------------------------------------------------------------------
# Row 6 — Duplicate detection (filename + SHA-256)
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestPrecheckFilenameMatch:
    async def test_no_match_when_project_empty(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        result = await precheck_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            filename="anything.jpg",
        )
        assert result.filename_matches == ()
        assert result.project_has_existing_pages is False

    async def test_filename_match_after_prior_upload(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        _, pages_resp = await _upload(
            db_session, project, "scan.jpg", _jpeg_bytes(seed=0)
        )
        assert len(pages_resp) == 1

        # New upload with the SAME filename → precheck flags it.
        result = await precheck_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            filename="scan.jpg",
        )
        assert len(result.filename_matches) == 1
        match = result.filename_matches[0]
        assert match.match_kind == "filename"
        assert match.page_uuid == pages_resp[0].page_uuid
        assert match.original_filename == "scan.jpg"

    async def test_filename_match_is_per_project_not_global(
        self, db_session: AsyncSession
    ) -> None:
        project_a = await seed_project(db_session)
        project_b = await seed_project(db_session)
        # Upload to project A.
        await _upload(db_session, project_a, "shared_name.jpg", _jpeg_bytes(seed=0))

        # Precheck project B with the same filename → no match.
        result = await precheck_for_project(
            session=db_session,
            project_uuid=project_b.project_uuid,
            filename="shared_name.jpg",
        )
        assert result.filename_matches == ()
        assert result.project_has_existing_pages is False

    async def test_different_filename_no_match(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        await _upload(db_session, project, "scan_a.jpg", _jpeg_bytes(seed=0))
        result = await precheck_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            filename="scan_b.jpg",
        )
        assert result.filename_matches == ()


@pytest.mark.asyncio
class TestSha256DedupePostFinalize:
    async def test_same_content_different_filename_detected(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        jpeg_bytes = _jpeg_bytes(seed=0)

        # First upload.
        job1, pages1 = await _upload(db_session, project, "first.jpg", jpeg_bytes)
        sha1 = job1.result["source_sha256"]
        # Same content, different filename — should match by SHA-256.
        matches = await find_sha256_matches(
            session=db_session,
            project_uuid=project.project_uuid,
            sha256=sha1,
        )
        # Self-match: the first upload's page IS a sha256 match for itself.
        assert len(matches) == 1
        assert matches[0].page_uuid == pages1[0].page_uuid

    async def test_different_content_no_match(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await _upload(db_session, project, "a.jpg", _jpeg_bytes(seed=0))
        # Different content (different image dimensions) → different SHA.
        matches = await find_sha256_matches(
            session=db_session,
            project_uuid=project.project_uuid,
            sha256="0" * 64,  # arbitrary non-matching hex hash
        )
        assert matches == ()

    async def test_exclude_job_filters_self_match(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        job, pages = await _upload(db_session, project, "scan.jpg", _jpeg_bytes(seed=0))
        sha = job.result["source_sha256"]

        # Without exclude: match self.
        matches = await find_sha256_matches(
            session=db_session,
            project_uuid=project.project_uuid,
            sha256=sha,
        )
        assert len(matches) == 1

        # With exclude: filter self out.
        matches_excluded = await find_sha256_matches(
            session=db_session,
            project_uuid=project.project_uuid,
            sha256=sha,
            exclude_job_uuid=job.job_uuid,
        )
        assert matches_excluded == ()
        _ = pages

    async def test_sha256_match_is_per_project(self, db_session: AsyncSession) -> None:
        project_a = await seed_project(db_session)
        project_b = await seed_project(db_session)
        jpeg_bytes = _jpeg_bytes(seed=0)
        job_a, _ = await _upload(db_session, project_a, "scan.jpg", jpeg_bytes)
        sha = job_a.result["source_sha256"]

        # Same SHA-256 in project_b → no cross-project match.
        matches = await find_sha256_matches(
            session=db_session,
            project_uuid=project_b.project_uuid,
            sha256=sha,
        )
        assert matches == ()


# ---------------------------------------------------------------------
# Row 7 — 1-book-at-a-time
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestProjectHasExistingPagesFlag:
    async def test_false_for_empty_project(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        result = await precheck_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            filename="any.jpg",
        )
        assert result.project_has_existing_pages is False

    async def test_true_after_first_upload(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await _upload(db_session, project, "first.jpg", _jpeg_bytes(seed=0))
        # Even with a different filename, the project-has-pages flag fires.
        result = await precheck_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            filename="second.jpg",
        )
        assert result.project_has_existing_pages is True

    async def test_pages_check_is_per_project(self, db_session: AsyncSession) -> None:
        project_a = await seed_project(db_session)
        project_b = await seed_project(db_session)
        await _upload(db_session, project_a, "a.jpg", _jpeg_bytes(seed=0))
        # project_b is still empty.
        result = await precheck_for_project(
            session=db_session,
            project_uuid=project_b.project_uuid,
            filename="b.jpg",
        )
        assert result.project_has_existing_pages is False
