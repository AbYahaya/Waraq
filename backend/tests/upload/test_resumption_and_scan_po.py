"""T-3.1.2 — Resumption + SCAN-PO tests.

Three layers:
1. Checkpoint-per-chunk audit trail (Abkürzung 9 spirit).
2. get_upload_status correctness + UploadNotFound.
3. Real-restart resume (commit + fresh engine + continue) and SCAN-PO writes
   via PROVENANCE-Kern (one PO per Page, page-scoped, canonical payload).
"""

from __future__ import annotations

import io
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

import pytest
import pytest_asyncio
from pypdf import PdfWriter
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from waraq.identity import new_uuid
from waraq.jobs import read_checkpoints
from waraq.schemas import (
    Checkpoint,
    Job,
    Page,
    Project,
    ProvenanceObject,
)
from waraq.schemas.enums import JobState, POType, ScopeType
from waraq.upload import (
    UploadNotFound,
    UploadStatus,
    append_chunk,
    finalize_upload,
    get_upload_status,
    start_upload,
)

# --- Helpers (shared shape with T-3.1.1) ---------------------------------


def _make_pdf_bytes(num_pages: int) -> bytes:
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
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
        name="resumption-test",
    )
    session.add(project)
    await session.flush()
    return project


@pytest_asyncio.fixture
async def isolated_uploads_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    from waraq.db import session as db_session_module

    db_session_module.get_settings.cache_clear()
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))
    yield tmp_path
    db_session_module.get_settings.cache_clear()


# --- Layer 1: checkpoint-per-chunk ----------------------------------------


@pytest.mark.asyncio
class TestT_3_1_2_ChunkCheckpoints:
    async def test_each_chunk_writes_a_checkpoint(
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

        for i, c in enumerate(chunks):
            await append_chunk(session=db_session, upload_job=job, chunk_index=i, chunk_data=c)

        cps = await read_checkpoints(session=db_session, job=job)
        assert len(cps) == len(chunks)
        for i, cp in enumerate(cps):
            assert cp.step == f"chunk_{i}_received"
            assert cp.payload["chunk_index"] == i
            assert cp.payload["chunk_bytes"] == len(chunks[i])

    async def test_failed_append_does_not_write_checkpoint(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        project = await _seed_project(db_session)
        job = await start_upload(
            session=db_session,
            project=project,
            original_filename="x.pdf",
            total_chunks=3,
            total_size_bytes=300,
        )
        from waraq.upload import ChunkOutOfOrder

        with pytest.raises(ChunkOutOfOrder):
            await append_chunk(
                session=db_session, upload_job=job, chunk_index=2, chunk_data=b"x" * 100
            )

        cps = await read_checkpoints(session=db_session, job=job)
        assert cps == []


# --- Layer 2: get_upload_status -------------------------------------------


@pytest.mark.asyncio
class TestT_3_1_2_GetUploadStatus:
    async def test_returns_zero_received_at_start(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        project = await _seed_project(db_session)
        job = await start_upload(
            session=db_session,
            project=project,
            original_filename="x.pdf",
            total_chunks=4,
            total_size_bytes=4000,
        )

        status = await get_upload_status(session=db_session, job_uuid=job.job_uuid)
        assert isinstance(status, UploadStatus)
        assert status.job_uuid == job.job_uuid
        assert status.state == JobState.PENDING
        assert status.received_chunks == 0
        assert status.total_chunks == 4
        assert status.expected_next_chunk == 0

    async def test_returns_progress_mid_upload(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        project = await _seed_project(db_session)
        pdf = _make_pdf_bytes(1)
        chunks = _chunk_bytes(pdf, chunk_size=100)
        job = await start_upload(
            session=db_session,
            project=project,
            original_filename="x.pdf",
            total_chunks=len(chunks),
            total_size_bytes=len(pdf),
        )

        # Send half the chunks.
        half = len(chunks) // 2
        for i in range(half):
            await append_chunk(
                session=db_session, upload_job=job, chunk_index=i, chunk_data=chunks[i]
            )

        status = await get_upload_status(session=db_session, job_uuid=job.job_uuid)
        assert status.state == JobState.RUNNING
        assert status.received_chunks == half
        assert status.expected_next_chunk == half

    async def test_returns_none_when_complete(
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
        for i, c in enumerate(chunks):
            await append_chunk(session=db_session, upload_job=job, chunk_index=i, chunk_data=c)

        status = await get_upload_status(session=db_session, job_uuid=job.job_uuid)
        assert status.received_chunks == status.total_chunks
        assert status.expected_next_chunk is None

    async def test_raises_for_unknown_job_uuid(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        bogus = new_uuid()
        with pytest.raises(UploadNotFound) as exc:
            await get_upload_status(session=db_session, job_uuid=bogus)
        assert exc.value.job_uuid == bogus

    async def test_raises_when_job_is_not_an_upload(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        # Create a non-upload Job directly.
        not_upload = Job(
            job_uuid=new_uuid(),
            job_type="ocr_baseline",
            state=JobState.PENDING.value,
            payload={},
        )
        db_session.add(not_upload)
        await db_session.flush()

        with pytest.raises(UploadNotFound):
            await get_upload_status(session=db_session, job_uuid=not_upload.job_uuid)


# --- Layer 3: SCAN-PO writes via PROVENANCE-Kern --------------------------


@pytest.mark.asyncio
class TestT_3_1_2_ScanProvenance:
    async def _full_upload(
        self, session: AsyncSession, num_pages: int
    ) -> tuple[Project, Job, list[Page]]:
        project = await _seed_project(session)
        pdf = _make_pdf_bytes(num_pages)
        chunks = _chunk_bytes(pdf, chunk_size=256)
        job = await start_upload(
            session=session,
            project=project,
            original_filename=f"{num_pages}_page.pdf",
            total_chunks=len(chunks),
            total_size_bytes=len(pdf),
        )
        for i, c in enumerate(chunks):
            await append_chunk(session=session, upload_job=job, chunk_index=i, chunk_data=c)
        pages = await finalize_upload(session=session, upload_job=job)
        return project, job, pages

    async def test_one_scan_po_per_page(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        _, _, pages = await self._full_upload(db_session, num_pages=4)

        for page in pages:
            result = await db_session.execute(
                select(ProvenanceObject).where(
                    ProvenanceObject.scope_type == ScopeType.PAGE.value,
                    ProvenanceObject.scope_uuid == page.page_uuid,
                    ProvenanceObject.po_type == POType.SCAN.value,
                )
            )
            pos = result.scalars().all()
            assert len(pos) == 1, f"Page {page.page_index} has {len(pos)} SCAN-POs, expected 1"

    async def test_scan_po_payload_carries_canonical_fields(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        _, job, pages = await self._full_upload(db_session, num_pages=2)
        page = pages[0]

        po = (
            await db_session.execute(
                select(ProvenanceObject).where(
                    ProvenanceObject.scope_uuid == page.page_uuid,
                    ProvenanceObject.po_type == POType.SCAN.value,
                )
            )
        ).scalar_one()

        assert po.payload["upload_job_uuid"] == str(job.job_uuid)
        assert po.payload["page_index_in_source"] == page.page_index
        assert po.payload["format"] == "pdf"
        assert "source_file_path" in po.payload
        assert "source_sha256" in po.payload
        # SHA-256 hex is 64 chars.
        assert len(po.payload["source_sha256"]) == 64

    async def test_all_scan_pos_share_the_same_source_sha256(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        _, _, pages = await self._full_upload(db_session, num_pages=3)
        sha_values: set[str] = set()
        for page in pages:
            po = (
                await db_session.execute(
                    select(ProvenanceObject).where(
                        ProvenanceObject.scope_uuid == page.page_uuid,
                        ProvenanceObject.po_type == POType.SCAN.value,
                    )
                )
            ).scalar_one()
            sha_values.add(po.payload["source_sha256"])
        assert len(sha_values) == 1, "All pages from the same source share one sha256"

    async def test_finalize_result_includes_source_sha256(
        self, db_session: AsyncSession, isolated_uploads_dir: Path
    ) -> None:
        _, job, _ = await self._full_upload(db_session, num_pages=1)
        assert job.result is not None
        assert "source_sha256" in job.result
        assert len(job.result["source_sha256"]) == 64


# --- Layer 4: real-restart resume (Abkürzung 9 spirit) -------------------


@pytest.mark.asyncio
class TestT_3_1_2_RealRestartResume:
    """Mirrors the T-2.1.2 restart-survival pattern: phase 1 commits a
    partial upload, phase 2 opens a fresh engine and resumes via
    get_upload_status, phase 3 cleans up.

    Files-on-disk persistence is exercised here too — chunks written before
    the simulated restart must still be on disk after the new engine opens."""

    async def test_partial_upload_resumes_via_get_upload_status(
        self, isolated_uploads_dir: Path
    ) -> None:
        from tests.conftest import _test_database_url

        url = _test_database_url()
        project_uuid = new_uuid()
        pdf = _make_pdf_bytes(2)
        chunks = _chunk_bytes(pdf, chunk_size=256)
        # Pre-allocate the job_uuid so we can reference it across engines.
        job_uuid: object = None  # set in phase 1

        # --- Phase 1: partial upload + commit + tear engine down --------
        from tests.conftest import seed_account_uuid

        account_uuid = new_uuid()
        engine_a = create_async_engine(url, future=True)
        sm_a = async_sessionmaker(bind=engine_a, class_=AsyncSession, expire_on_commit=False)
        try:
            async with sm_a() as session, session.begin():
                await seed_account_uuid(session, account_uuid)
                project = Project(
                    project_uuid=project_uuid,
                    account_uuid=account_uuid,
                    name="restart-resume-test",
                )
                session.add(project)
                await session.flush()

                job = await start_upload(
                    session=session,
                    project=project,
                    original_filename="restart.pdf",
                    total_chunks=len(chunks),
                    total_size_bytes=len(pdf),
                )
                job_uuid = job.job_uuid

                # Send first half.
                half = len(chunks) // 2
                for i in range(half):
                    await append_chunk(
                        session=session, upload_job=job, chunk_index=i, chunk_data=chunks[i]
                    )
        finally:
            await engine_a.dispose()

        # --- Phase 2: fresh engine, ask where we are, resume + finalize --
        engine_b = create_async_engine(url, future=True)
        sm_b = async_sessionmaker(bind=engine_b, class_=AsyncSession, expire_on_commit=False)
        try:
            async with sm_b() as session, session.begin():
                status = await get_upload_status(session=session, job_uuid=job_uuid)  # type: ignore[arg-type]
                assert status.expected_next_chunk == len(chunks) // 2
                assert status.state == JobState.RUNNING

                # Reload the Job and continue.
                job = await session.get(Job, job_uuid)
                assert job is not None
                for i in range(status.expected_next_chunk, len(chunks)):
                    await append_chunk(
                        session=session, upload_job=job, chunk_index=i, chunk_data=chunks[i]
                    )

                pages = await finalize_upload(session=session, upload_job=job)
                assert len(pages) == 2
                assert job.state == JobState.COMPLETED.value
        finally:
            await engine_b.dispose()

        # --- Phase 3: cleanup so we don't pollute the dev DB ------------
        engine_c = create_async_engine(url, future=True)
        sm_c = async_sessionmaker(bind=engine_c, class_=AsyncSession, expire_on_commit=False)
        try:
            async with sm_c() as session, session.begin():
                # Pages and POs first (FK ordering), then upload Job, then Project.
                page_uuids = (
                    (
                        await session.execute(
                            select(Page.page_uuid).where(Page.project_uuid == project_uuid)
                        )
                    )
                    .scalars()
                    .all()
                )
                if page_uuids:
                    await session.execute(
                        delete(ProvenanceObject).where(ProvenanceObject.scope_uuid.in_(page_uuids))
                    )
                await session.execute(delete(Checkpoint).where(Checkpoint.job_uuid == job_uuid))
                await session.execute(delete(Page).where(Page.project_uuid == project_uuid))
                await session.execute(delete(Job).where(Job.project_uuid == project_uuid))
                await session.execute(delete(Project).where(Project.project_uuid == project_uuid))
                from waraq.schemas import Account

                await session.execute(delete(Account).where(Account.account_uuid == account_uuid))
        finally:
            await engine_c.dispose()


# --- Layer 5: keep the architectural invariants honest -------------------


class TestT_3_1_2_AbkurzungSeven_GuardStillHolds:
    """After T-3.1.2, the upload service legitimately imports `create_po`.
    What's still forbidden is the schema bypass: importing `ProvenanceObject`
    or from `waraq.schemas.provenance` directly."""

    FORBIDDEN_MODULES: ClassVar[set[str]] = {"waraq.schemas.provenance"}
    FORBIDDEN_NAMES: ClassVar[set[str]] = {"ProvenanceObject"}

    def test_upload_service_still_does_not_bypass_provenance_kern(self) -> None:
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
