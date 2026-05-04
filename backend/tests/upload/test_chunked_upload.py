"""T-3.1.1 — Chunked upload + page materialization tests.

Three layers:
1. Pure validation tests (no DB, no FS) — exception classes carry the
   right context.
2. Integration with rollback fixture — start/append/finalize round-trip
   against live Postgres. Filesystem writes go to a tmp_path per test.
3. Page materialization correctness — N-page PDF produces exactly N Pages
   with page_index 1..N and the right project_uuid.
"""

from __future__ import annotations

import io
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

import pytest
import pytest_asyncio
from pypdf import PdfWriter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.schemas import Job, Page, Project
from waraq.schemas.enums import JobState
from waraq.upload import (
    ChunkOutOfOrder,
    IncompleteUpload,
    UploadSizeMismatch,
    append_chunk,
    finalize_upload,
    start_upload,
)

# --- Helpers ---------------------------------------------------------------


def _make_pdf_bytes(num_pages: int, *, page_size: tuple[float, float] = (612, 792)) -> bytes:
    """Generate a minimal in-memory PDF with `num_pages` blank pages.

    page_size defaults to US Letter (612x792 pt). Specifying it lets us keep
    test fixtures small and deterministic."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=page_size[0], height=page_size[1])
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _chunk_bytes(data: bytes, chunk_size: int) -> list[bytes]:
    return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]


async def _seed_project(session: AsyncSession) -> Project:
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(
        project_uuid=new_uuid(),
        account_uuid=account_uuid,
        name="upload-test-project",
    )
    session.add(project)
    await session.flush()
    return project


@pytest_asyncio.fixture
async def isolated_uploads_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """Redirect uploads_dir to a per-test tmp_path so filesystem writes are
    isolated and auto-cleaned by pytest. Clears the lru_cache on Settings so
    the override takes effect."""
    from waraq.db import session as db_session_module

    db_session_module.get_settings.cache_clear()
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))
    yield tmp_path
    db_session_module.get_settings.cache_clear()


# --- Layer 1: pure exception classes --------------------------------------


class TestT_3_1_1_Exceptions:
    def test_chunk_out_of_order_carries_context(self) -> None:
        exc = ChunkOutOfOrder(expected=3, received=5)
        assert exc.expected == 3
        assert exc.received == 5
        assert "3" in str(exc) and "5" in str(exc)

    def test_incomplete_upload_carries_context(self) -> None:
        exc = IncompleteUpload(received=2, total=5)
        assert exc.received == 2
        assert exc.total == 5

    def test_size_mismatch_carries_context(self) -> None:
        exc = UploadSizeMismatch(declared=1000, actual=997)
        assert exc.declared == 1000
        assert exc.actual == 997


# --- Layer 2: integration ---------------------------------------------------


@pytest.mark.asyncio
class TestT_3_1_1_StartUpload:
    async def test_creates_pending_job_with_canonical_payload(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        project = await _seed_project(db_session)

        job = await start_upload(
            session=db_session,
            project=project,
            original_filename="kitab.pdf",
            total_chunks=4,
            total_size_bytes=8192,
        )

        assert job.state == JobState.PENDING.value
        assert job.job_type == "upload"
        assert job.project_uuid == project.project_uuid
        assert job.payload == {
            "original_filename": "kitab.pdf",
            "total_chunks": 4,
            "total_size_bytes": 8192,
            "received_chunks": 0,
        }

    async def test_creates_per_upload_directory_on_disk(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        project = await _seed_project(db_session)
        job = await start_upload(
            session=db_session,
            project=project,
            original_filename="x.pdf",
            total_chunks=1,
            total_size_bytes=10,
        )
        expected_dir = isolated_uploads_dir / str(project.project_uuid) / str(job.job_uuid)
        assert expected_dir.is_dir()


@pytest.mark.asyncio
class TestT_3_1_1_AppendChunk:
    async def test_first_chunk_transitions_pending_to_running(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        project = await _seed_project(db_session)
        pdf = _make_pdf_bytes(1)
        job = await start_upload(
            session=db_session,
            project=project,
            original_filename="single.pdf",
            total_chunks=1,
            total_size_bytes=len(pdf),
        )
        assert job.state == JobState.PENDING.value

        await append_chunk(session=db_session, upload_job=job, chunk_index=0, chunk_data=pdf)
        assert job.state == JobState.RUNNING.value
        assert job.payload["received_chunks"] == 1

    async def test_writes_chunk_bytes_to_disk(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        project = await _seed_project(db_session)
        pdf = _make_pdf_bytes(2)
        chunks = _chunk_bytes(pdf, chunk_size=200)
        job = await start_upload(
            session=db_session,
            project=project,
            original_filename="two_pages.pdf",
            total_chunks=len(chunks),
            total_size_bytes=len(pdf),
        )
        for i, c in enumerate(chunks):
            await append_chunk(session=db_session, upload_job=job, chunk_index=i, chunk_data=c)

        source_path = (
            isolated_uploads_dir / str(project.project_uuid) / str(job.job_uuid) / "source.pdf"
        )
        assert source_path.read_bytes() == pdf

    async def test_rejects_out_of_order_chunk(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        project = await _seed_project(db_session)
        job = await start_upload(
            session=db_session,
            project=project,
            original_filename="x.pdf",
            total_chunks=3,
            total_size_bytes=30,
        )
        # Send chunk 2 first when chunk 0 was expected.
        with pytest.raises(ChunkOutOfOrder) as exc:
            await append_chunk(
                session=db_session, upload_job=job, chunk_index=2, chunk_data=b"x" * 10
            )
        assert exc.value.expected == 0
        assert exc.value.received == 2
        # State unchanged after refusal.
        assert job.payload["received_chunks"] == 0

    async def test_rejects_chunk_replay(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        project = await _seed_project(db_session)
        pdf = _make_pdf_bytes(1)
        job = await start_upload(
            session=db_session,
            project=project,
            original_filename="x.pdf",
            total_chunks=2,
            total_size_bytes=len(pdf),
        )
        await append_chunk(session=db_session, upload_job=job, chunk_index=0, chunk_data=pdf[:100])
        # Replay chunk 0 instead of advancing to chunk 1.
        with pytest.raises(ChunkOutOfOrder) as exc:
            await append_chunk(
                session=db_session, upload_job=job, chunk_index=0, chunk_data=pdf[:100]
            )
        assert exc.value.expected == 1
        assert exc.value.received == 0


@pytest.mark.asyncio
class TestT_3_1_1_FinalizeUpload:
    async def _full_upload(
        self,
        session: AsyncSession,
        *,
        num_pages: int,
        chunk_size: int = 256,
    ) -> tuple[Project, Job, bytes]:
        project = await _seed_project(session)
        pdf = _make_pdf_bytes(num_pages)
        chunks = _chunk_bytes(pdf, chunk_size)
        job = await start_upload(
            session=session,
            project=project,
            original_filename=f"{num_pages}_pages.pdf",
            total_chunks=len(chunks),
            total_size_bytes=len(pdf),
        )
        for i, c in enumerate(chunks):
            await append_chunk(session=session, upload_job=job, chunk_index=i, chunk_data=c)
        return project, job, pdf

    async def test_materializes_one_page_per_pdf_page(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        project, job, _ = await self._full_upload(db_session, num_pages=5)

        pages = await finalize_upload(session=db_session, upload_job=job)

        assert len(pages) == 5
        assert [p.page_index for p in pages] == [1, 2, 3, 4, 5]
        for p in pages:
            assert p.project_uuid == project.project_uuid

    async def test_pages_are_persisted_with_unique_uuids(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        project, job, _ = await self._full_upload(db_session, num_pages=3)
        await finalize_upload(session=db_session, upload_job=job)

        loaded = (
            (
                await db_session.execute(
                    select(Page)
                    .where(Page.project_uuid == project.project_uuid)
                    .order_by(Page.page_index)
                )
            )
            .scalars()
            .all()
        )
        assert len(loaded) == 3
        assert len({p.page_uuid for p in loaded}) == 3

    async def test_completes_job_with_result_payload(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        _, job, pdf = await self._full_upload(db_session, num_pages=2)
        await finalize_upload(session=db_session, upload_job=job)

        assert job.state == JobState.COMPLETED.value
        assert job.result is not None
        assert job.result["page_count"] == 2
        assert job.result["size_bytes"] == len(pdf)
        assert job.result["file_path"].endswith("source.pdf")

    async def test_rejects_when_chunks_incomplete(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        project = await _seed_project(db_session)
        pdf = _make_pdf_bytes(1)
        chunks = _chunk_bytes(pdf, chunk_size=200)
        job = await start_upload(
            session=db_session,
            project=project,
            original_filename="x.pdf",
            total_chunks=len(chunks),
            total_size_bytes=len(pdf),
        )
        # Send only half the chunks.
        for i, c in enumerate(chunks[: len(chunks) // 2]):
            await append_chunk(session=db_session, upload_job=job, chunk_index=i, chunk_data=c)

        with pytest.raises(IncompleteUpload) as exc:
            await finalize_upload(session=db_session, upload_job=job)
        assert exc.value.received == len(chunks) // 2
        assert exc.value.total == len(chunks)
        # No pages materialized on refusal.
        assert job.state != JobState.COMPLETED.value

    async def test_rejects_when_size_mismatches(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        project = await _seed_project(db_session)
        pdf = _make_pdf_bytes(1)
        # Lie about total_size_bytes — say it's 1MB when actual is len(pdf).
        job = await start_upload(
            session=db_session,
            project=project,
            original_filename="x.pdf",
            total_chunks=1,
            total_size_bytes=1_000_000,
        )
        await append_chunk(session=db_session, upload_job=job, chunk_index=0, chunk_data=pdf)

        with pytest.raises(UploadSizeMismatch) as exc:
            await finalize_upload(session=db_session, upload_job=job)
        assert exc.value.declared == 1_000_000
        assert exc.value.actual == len(pdf)


# --- Layer 3: Abkürzung 7 reminder ----------------------------------------


class TestT_3_1_1_AbkurzungSeven_DoesNotBypassProvenanceKern:
    """Abkürzung 7: Upload-Handler must NOT write SCAN-PO directly.

    After T-3.1.2 the upload service legitimately calls `create_po` (the
    canonical PROVENANCE-Kern entrypoint). What's still forbidden: importing
    the schema model `ProvenanceObject` or the schema module
    `waraq.schemas.provenance` directly — that would be the bypass."""

    FORBIDDEN_MODULES: ClassVar[set[str]] = {"waraq.schemas.provenance"}
    FORBIDDEN_NAMES: ClassVar[set[str]] = {"ProvenanceObject"}

    def test_upload_service_does_not_import_provenance(self) -> None:
        import ast
        import inspect as inspect_mod

        from waraq.upload import service as upload_service_module

        tree = ast.parse(inspect_mod.getsource(upload_service_module))

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module not in self.FORBIDDEN_MODULES, (
                    f"upload service imports forbidden module: {node.module}"
                )
                for alias in node.names:
                    assert alias.name not in self.FORBIDDEN_NAMES, (
                        f"upload service imports forbidden name: {alias.name}"
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in self.FORBIDDEN_MODULES, (
                        f"upload service imports forbidden module: {alias.name}"
                    )
