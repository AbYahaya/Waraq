"""T-3.1.1 + T-3.1.2 — Chunked upload, page materialization, resumption, SCAN-PO.

Service layer for receiving a multi-chunk file upload (PDF), materializing one
Page row per physical PDF page, and writing one SCAN-PO per Page through
PROVENANCE-Kern.

Three-call flow:

    job = await start_upload(session=..., project=..., original_filename=...,
                              total_chunks=5, total_size_bytes=12345)
    for i, chunk in enumerate(chunks):
        await append_chunk(session=..., upload_job=job,
                           chunk_index=i, chunk_data=chunk)
    pages = await finalize_upload(session=..., upload_job=job)

After a process restart, the resume entrypoint is `get_upload_status`:

    status = await get_upload_status(session=..., job_uuid=job_uuid)
    if status.expected_next_chunk is not None:
        # client resumes from status.expected_next_chunk
        ...

Discipline:
- SCAN-PO writes go through PROVENANCE-Kern (`create_po`), not via direct
  `session.add(ProvenanceObject(...))`. Abkürzung 7 enforced by the AST
  guard test in tests/upload/test_chunked_upload.py — `ProvenanceObject` is
  forbidden as an import; `create_po` is the canonical entrypoint.
- Job state transitions go through `waraq.jobs` services — not direct
  `job.state = ...` mutations.
- Page UUIDs come from `new_uuid()` (IDENTITY service).
- Files land under `{uploads_dir}/{project_uuid}/{job_uuid}/source<ext>`,
  with `uploads_dir` gitignored.
- Each `append_chunk` writes a Checkpoint (audit trail per Abkürzung 9 spirit).
  Job.payload is the primary recovery state; checkpoints are durable history.

Atomicity: caller owns the DB transaction. Filesystem writes are NOT
transactional — append_chunk writes to disk immediately, mirroring the
checkpoint-restart-survival contract from T-2.1.2.
"""

from __future__ import annotations

import hashlib
import uuid as _uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from waraq.db.session import get_settings
from waraq.identity.service import new_uuid
from waraq.jobs import complete_job, start_job, write_checkpoint
from waraq.provenance import create_po
from waraq.schemas import Job, Page, Project
from waraq.schemas.enums import JobState, POType, ScopeType
from waraq.upload.exceptions import (
    ChunkOutOfOrder,
    IncompleteUpload,
    UploadNotFound,
    UploadSizeMismatch,
)

JOB_TYPE = "upload"


def _upload_dir(upload_job: Job) -> Path:
    """Per-upload directory: {uploads_dir}/{project_uuid}/{job_uuid}."""
    base = Path(get_settings().uploads_dir)
    return base / str(upload_job.project_uuid) / str(upload_job.job_uuid)


def _source_path(upload_job: Job) -> Path:
    """Path to the assembled source file. Extension preserved from original_filename."""
    payload = upload_job.payload
    suffix = Path(payload["original_filename"]).suffix
    return _upload_dir(upload_job) / f"source{suffix}"


def _count_pdf_pages(path: Path) -> int:
    # Lazy import so tests that don't touch PDFs aren't slowed by it.
    from pypdf import PdfReader

    reader = PdfReader(path)
    return len(reader.pages)


def _compute_sha256(path: Path) -> str:
    """Streaming SHA-256 of a file. Bounded memory regardless of file size."""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(64 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


@dataclass(frozen=True, slots=True)
class UploadStatus:
    """Resume-time view of an upload Job's progress.

    `expected_next_chunk` is None when the upload is complete (received_chunks
    == total_chunks); otherwise it's the chunk_index the client should send
    next. `state` is the current Job state.
    """

    job_uuid: _uuid.UUID
    state: JobState
    received_chunks: int
    total_chunks: int
    expected_next_chunk: int | None


async def start_upload(
    *,
    session: AsyncSession,
    project: Project,
    original_filename: str,
    total_chunks: int,
    total_size_bytes: int,
) -> Job:
    """Begin a chunked upload. Creates a Job in PENDING state and the
    per-upload directory on disk.

    The Job's payload carries upload metadata:
        - original_filename: client-supplied filename (informational)
        - total_chunks: declared chunk count for client-server agreement
        - total_size_bytes: declared total size for end-of-upload validation
        - received_chunks: monotonically increasing counter (starts at 0)
    """
    job = Job(
        job_uuid=new_uuid(),
        job_type=JOB_TYPE,
        state=JobState.PENDING.value,
        project_uuid=project.project_uuid,
        payload={
            "original_filename": original_filename,
            "total_chunks": total_chunks,
            "total_size_bytes": total_size_bytes,
            "received_chunks": 0,
        },
    )
    session.add(job)
    await session.flush()

    _upload_dir(job).mkdir(parents=True, exist_ok=True)
    return job


async def append_chunk(
    *,
    session: AsyncSession,
    upload_job: Job,
    chunk_index: int,
    chunk_data: bytes,
) -> Job:
    """Append `chunk_data` to the upload file. Validates chunk_index ordering.

    On the first chunk, transitions the Job from PENDING → RUNNING via the
    canonical state-machine service.
    """
    payload: dict[str, Any] = upload_job.payload
    expected = payload["received_chunks"]
    if chunk_index != expected:
        raise ChunkOutOfOrder(expected=expected, received=chunk_index)

    source = _source_path(upload_job)
    source.parent.mkdir(parents=True, exist_ok=True)
    with source.open("ab") as f:
        f.write(chunk_data)

    payload["received_chunks"] = expected + 1
    flag_modified(upload_job, "payload")

    if upload_job.state == JobState.PENDING.value:
        await start_job(session=session, job=upload_job)
    else:
        await session.flush()

    # Write a Checkpoint for this chunk receipt. Audit trail per Abkürzung 9.
    # Job.payload is the primary recovery state; checkpoints are durable
    # history of each chunk-receipt event.
    await write_checkpoint(
        session=session,
        job=upload_job,
        step=f"chunk_{chunk_index}_received",
        payload={"chunk_index": chunk_index, "chunk_bytes": len(chunk_data)},
    )
    return upload_job


async def get_upload_status(*, session: AsyncSession, job_uuid: _uuid.UUID) -> UploadStatus:
    """Look up an upload Job's progress for resume after a process restart.

    Raises `UploadNotFound` if no Job with that UUID exists or the Job is
    not an upload (different `job_type`).
    """
    job = await session.get(Job, job_uuid)
    if job is None or job.job_type != JOB_TYPE:
        raise UploadNotFound(job_uuid=job_uuid)

    payload = job.payload
    received = payload["received_chunks"]
    total = payload["total_chunks"]
    expected_next = received if received < total else None
    return UploadStatus(
        job_uuid=job_uuid,
        state=JobState(job.state),
        received_chunks=received,
        total_chunks=total,
        expected_next_chunk=expected_next,
    )


async def finalize_upload(*, session: AsyncSession, upload_job: Job) -> list[Page]:
    """Close the upload, validate, materialize Page rows, complete the Job.

    Validations:
        - All declared chunks arrived (received_chunks == total_chunks).
        - Bytes on disk match total_size_bytes.

    Materialization: counts PDF pages with pypdf and inserts one Page row per
    physical page, page_index 1..N.

    Job transitions RUNNING → COMPLETED with a result payload describing the
    upload (page_count, file_path, sha256 deferred to T-3.1.2's SCAN-PO).
    """
    payload: dict[str, Any] = upload_job.payload
    received = payload["received_chunks"]
    total = payload["total_chunks"]
    if received != total:
        raise IncompleteUpload(received=received, total=total)

    source = _source_path(upload_job)
    actual_size = source.stat().st_size
    if actual_size != payload["total_size_bytes"]:
        raise UploadSizeMismatch(declared=payload["total_size_bytes"], actual=actual_size)

    page_count = _count_pdf_pages(source)
    pages: list[Page] = []
    for i in range(1, page_count + 1):
        page = Page(
            page_uuid=new_uuid(),
            project_uuid=upload_job.project_uuid,
            page_index=i,
        )
        session.add(page)
        pages.append(page)
    await session.flush()

    # T-3.1.2: SCAN-PO per Page via PROVENANCE-Kern. Page-scoped per CAB §5.3.
    # Computed once because the source file is the same for every page.
    source_sha256 = _compute_sha256(source)
    file_format = Path(payload["original_filename"]).suffix.lstrip(".").lower()
    for page in pages:
        await create_po(
            session=session,
            po_type=POType.SCAN,
            scope_type=ScopeType.PAGE,
            scope_uuid=page.page_uuid,
            payload={
                "source_file_path": str(source),
                "source_sha256": source_sha256,
                "page_index_in_source": page.page_index,
                "upload_job_uuid": str(upload_job.job_uuid),
                "format": file_format,
            },
        )

    await complete_job(
        session=session,
        job=upload_job,
        result={
            "page_count": page_count,
            "file_path": str(source),
            "size_bytes": actual_size,
            "source_sha256": source_sha256,
        },
    )
    return pages
