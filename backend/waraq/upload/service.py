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
from waraq.invariant.enums import LockFlag, OperationMode
from waraq.jobs import complete_job, start_job, write_checkpoint
from waraq.provenance import create_po
from waraq.revision import create_revision
from waraq.schemas import Block, Job, Page, Project, Segment
from waraq.schemas.enums import (
    BlockClass,
    ChangeSource,
    JobState,
    OcrStatus,
    POType,
    ReadingDirection,
    ScopeType,
)
from waraq.upload.archive import (
    ArchiveEntry,
    extract_and_sort,
)
from waraq.upload.exceptions import (
    ChunkOutOfOrder,
    IncompleteUpload,
    UploadNotFound,
    UploadSizeMismatch,
    UploadTooLarge,
)
from waraq.upload.file_type import (
    UploadFormat,
    count_pages,
    detect_format,
    is_archive_format,
    is_direct_text_format,
)
from waraq.upload.text_extraction import (
    EmptyDocument,
    TextExtractionError,
    extract_paragraphs,
)

JOB_TYPE = "upload"

# Canon §2.1 Phase 5 K-5: hard maximum per upload. 2 GB = 2 * 1024**3.
# Enforced at start_upload (declared size) and defensively at
# append_chunk (cumulative bytes on disk).
MAX_UPLOAD_SIZE_BYTES = 2 * 1024 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class _ArchiveContext:
    """Per-entry provenance recorded on SCAN-PO when a Page comes from
    inside an archive. Used by the K-4 archive recursion to preserve
    the audit trail: each Page knows which archive entry produced it
    + the archive's identity."""

    archive_source_path: str
    archive_sha256: str
    archive_format: str
    archive_entry_filename: str
    archive_entry_index: int


def _upload_dir(upload_job: Job) -> Path:
    """Per-upload directory: {uploads_dir}/{project_uuid}/{job_uuid}."""
    base = Path(get_settings().uploads_dir)
    return base / str(upload_job.project_uuid) / str(upload_job.job_uuid)


def _source_path(upload_job: Job) -> Path:
    """Path to the assembled source file. Extension preserved from original_filename."""
    payload = upload_job.payload
    suffix = Path(payload["original_filename"]).suffix
    return _upload_dir(upload_job) / f"source{suffix}"


def _compute_sha256(path: Path) -> str:
    """Streaming SHA-256 of a file. Bounded memory regardless of file size."""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(64 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _read_head(path: Path, *, n: int) -> bytes:
    """Read the first `n` bytes of a file — used for magic-byte sniffing
    at finalize time. Bounded; the file may be smaller than `n`."""
    with path.open("rb") as f:
        return f.read(n)


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

    Raises:
        UploadTooLarge: declared total exceeds canon §2.1 2 GB max.
    """
    # K-5 row 5: hard 2 GB ceiling per canon §2.1. Reject up front
    # before any chunks transit, so a 5 GB upload doesn't waste bytes
    # before finalize.
    if total_size_bytes > MAX_UPLOAD_SIZE_BYTES:
        raise UploadTooLarge(size_bytes=total_size_bytes, max_bytes=MAX_UPLOAD_SIZE_BYTES)

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

    # K-5 row 5: defensive cumulative cap. Client might have lied
    # about `total_size_bytes` at start; cumulative bytes-on-disk
    # is the authoritative measure. Refuses any chunk that pushes
    # the upload past 2 GB.
    cumulative_size = source.stat().st_size
    if cumulative_size > MAX_UPLOAD_SIZE_BYTES:
        raise UploadTooLarge(size_bytes=cumulative_size, max_bytes=MAX_UPLOAD_SIZE_BYTES)

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

    # K-1 — detect the upload format from filename + magic bytes. Reject
    # anything outside the canon §2.1 supported set at finalize time
    # rather than at chunk time (the chunk transport is bytes-agnostic).
    head = _read_head(source, n=64)
    upload_format = detect_format(filename=payload["original_filename"], head_bytes=head)
    source_sha256 = _compute_sha256(source)

    if is_archive_format(upload_format):
        # K-4 — ZIP/RAR/CBZ/CBR: extract entries, filename-sort,
        # recurse into each supported entry via the per-format helper.
        pages = await _finalize_archive(
            session=session,
            upload_job=upload_job,
            source=source,
            source_sha256=source_sha256,
            upload_format=upload_format,
        )
    elif is_direct_text_format(upload_format):
        # K-2 + K-3 direct-text — DOCX/ODT/TXT/XML/HTML/EPUB/MOBI/AZW/AZW3:
        # extract paragraphs at upload time and materialize Segments
        # directly, bypassing the OCR pipeline. One Page (ocr_status=GO
        # since there's no OCR to review), one Block (MAIN_TEXT), N
        # Segments (one per paragraph).
        pages = await _finalize_direct_text(
            session=session,
            upload_job=upload_job,
            source=source,
            source_sha256=source_sha256,
            upload_format=upload_format,
        )
    else:
        # K-1 + canonical PDF + K-3 DjVu — binary formats go through the
        # OCR pipeline. Materialize empty Pages (one per logical page);
        # Block + Segment rows are created lazily at OCR time by
        # `_ensure_blocks_and_segments` in `page_runner`.
        pages = await _finalize_binary(
            session=session,
            upload_job=upload_job,
            source=source,
            source_sha256=source_sha256,
            upload_format=upload_format,
        )

    await complete_job(
        session=session,
        job=upload_job,
        result={
            "page_count": len(pages),
            "file_path": str(source),
            "size_bytes": actual_size,
            "source_sha256": source_sha256,
        },
    )
    return pages


async def _finalize_binary(
    *,
    session: AsyncSession,
    upload_job: Job,
    source: Path,
    source_sha256: str,
    upload_format: UploadFormat,
    archive_context: _ArchiveContext | None = None,
    page_index_offset: int = 0,
) -> list[Page]:
    """K-1 + PDF + DjVu finalize branch: empty Page rows + SCAN-POs.
    Block + Segment provisioning happens lazily at OCR time.

    `archive_context` is set when this entry came from inside a K-4
    archive — its fields are added to each SCAN-PO so the audit trail
    records the archive provenance. `page_index_offset` shifts the
    materialized Page indices so archive entries don't all start at
    page_index=1 (each entry continues the project-wide sequence).
    """
    page_count = count_pages(path=source, fmt=upload_format)
    pages: list[Page] = []
    for i in range(1, page_count + 1):
        page = Page(
            page_uuid=new_uuid(),
            project_uuid=upload_job.project_uuid,
            page_index=page_index_offset + i,
        )
        session.add(page)
        pages.append(page)
    await session.flush()

    for page in pages:
        payload: dict[str, Any] = {
            "source_file_path": str(source),
            "source_sha256": source_sha256,
            "page_index_in_source": page.page_index - page_index_offset,
            "upload_job_uuid": str(upload_job.job_uuid),
            "format": upload_format.value,
        }
        if archive_context is not None:
            payload.update(
                {
                    "archive_source_path": archive_context.archive_source_path,
                    "archive_sha256": archive_context.archive_sha256,
                    "archive_format": archive_context.archive_format,
                    "archive_entry_filename": archive_context.archive_entry_filename,
                    "archive_entry_index": archive_context.archive_entry_index,
                }
            )
        await create_po(
            session=session,
            po_type=POType.SCAN,
            scope_type=ScopeType.PAGE,
            scope_uuid=page.page_uuid,
            payload=payload,
        )
    return pages


async def _finalize_direct_text(
    *,
    session: AsyncSession,
    upload_job: Job,
    source: Path,
    source_sha256: str,
    upload_format: UploadFormat,
    archive_context: _ArchiveContext | None = None,
    page_index_offset: int = 0,
) -> list[Page]:
    """K-2 direct-text finalize branch: extract paragraphs, materialize
    one Page + one Block + N Segments, each Segment with a Revision
    carrying the paragraph text.

    Provenance:
      - SCAN-PO records the source + format + `skip_ocr: true` so any
        future caller can tell at a glance that OCR didn't run.
      - Each Revision uses `change_source=OCR` + `operation_mode=AUTOMATIC`.
        This is a pragmatic call: CAB §5.2 lists 4 canonical
        change_source values (manual / ocr / re_translate /
        style_profile), and direct-text extraction is the only
        existing value that fits "system-extracted text from source"
        — even though canon §2.1 marks these formats "skip-OCR"
        technically. Revisit if canon adds an `import` change_source
        in a future amendment.
      - Page.ocr_status = GO. Direct-text Pages have nothing to OCR-
        review; setting GO immediately at finalize avoids forcing the
        user through an empty review ceremony. Documented as a §2.7
        surface-the-decision call.
    """
    try:
        paragraphs = extract_paragraphs(path=source, fmt=upload_format)
    except EmptyDocument:
        raise
    except TextExtractionError:
        raise

    # One Page per document. When this entry came from inside an
    # archive, `page_index_offset` shifts so direct-text entries
    # continue the archive's page sequence rather than restarting at 1.
    page = Page(
        page_uuid=new_uuid(),
        project_uuid=upload_job.project_uuid,
        page_index=page_index_offset + 1,
        ocr_status=OcrStatus.GO,
    )
    session.add(page)
    await session.flush()

    # One Block — MAIN_TEXT, RTL (matches the OCR-pipeline default).
    block = Block(
        block_uuid=new_uuid(),
        page_uuid=page.page_uuid,
        block_type=BlockClass.MAIN_TEXT.value,
        block_index=0,
        reading_direction=ReadingDirection.RTL,
    )
    session.add(block)
    await session.flush()

    # One Segment + one Revision per paragraph.
    for satz_index, paragraph in enumerate(paragraphs):
        segment = Segment(
            satz_uuid=new_uuid(),
            block_uuid=block.block_uuid,
            satz_index=satz_index,
            lock_flag=LockFlag.NONE,
            text_content=None,  # set by create_revision below.
        )
        session.add(segment)
        await session.flush()
        await create_revision(
            session=session,
            segment=segment,
            after_text=paragraph,
            change_source=ChangeSource.OCR,
            operation_mode=OperationMode.AUTOMATIC,
        )

    # SCAN-PO records the source. `skip_ocr: true` is the marker that
    # downstream pipeline can read to know OCR didn't run for this page.
    scan_payload: dict[str, Any] = {
        "source_file_path": str(source),
        "source_sha256": source_sha256,
        "page_index_in_source": 1,
        "upload_job_uuid": str(upload_job.job_uuid),
        "format": upload_format.value,
        "skip_ocr": True,
        "paragraph_count": len(paragraphs),
    }
    if archive_context is not None:
        scan_payload.update(
            {
                "archive_source_path": archive_context.archive_source_path,
                "archive_sha256": archive_context.archive_sha256,
                "archive_format": archive_context.archive_format,
                "archive_entry_filename": archive_context.archive_entry_filename,
                "archive_entry_index": archive_context.archive_entry_index,
            }
        )
    await create_po(
        session=session,
        po_type=POType.SCAN,
        scope_type=ScopeType.PAGE,
        scope_uuid=page.page_uuid,
        payload=scan_payload,
    )
    return [page]


async def _finalize_archive(
    *,
    session: AsyncSession,
    upload_job: Job,
    source: Path,
    source_sha256: str,
    upload_format: UploadFormat,
) -> list[Page]:
    """K-4 archive finalize branch: extract entries via `archive.extract_and_sort`,
    then dispatch each entry to the per-format helper (`_finalize_binary` for
    images / PDF / DjVu, `_finalize_direct_text` for documents / e-books).

    Each entry's Pages carry archive provenance on their SCAN-POs
    (`archive_source_path`, `archive_format`, `archive_entry_filename`).
    Page indices flow continuously across entries: entry 1 produces
    pages 1..N1, entry 2 produces pages N1+1..N1+N2, etc.

    Nested archives are silently skipped per canon (one-level recursion).
    Unsupported entries are also silent skips. An archive with zero
    supported entries raises `EmptyArchive` (HTTP 422).
    """
    extract_dir = _upload_dir(upload_job) / "extracted"
    entries: list[ArchiveEntry] = extract_and_sort(
        archive_path=source,
        archive_fmt=upload_format,
        dest_dir=extract_dir,
    )

    all_pages: list[Page] = []
    page_index_offset = 0
    for entry_index, entry in enumerate(entries, start=1):
        ctx = _ArchiveContext(
            archive_source_path=str(source),
            archive_sha256=source_sha256,
            archive_format=upload_format.value,
            archive_entry_filename=entry.inner_filename,
            archive_entry_index=entry_index,
        )
        entry_sha256 = _compute_sha256(entry.inner_path)
        if is_direct_text_format(entry.fmt):
            entry_pages = await _finalize_direct_text(
                session=session,
                upload_job=upload_job,
                source=entry.inner_path,
                source_sha256=entry_sha256,
                upload_format=entry.fmt,
                archive_context=ctx,
                page_index_offset=page_index_offset,
            )
        else:
            entry_pages = await _finalize_binary(
                session=session,
                upload_job=upload_job,
                source=entry.inner_path,
                source_sha256=entry_sha256,
                upload_format=entry.fmt,
                archive_context=ctx,
                page_index_offset=page_index_offset,
            )
        all_pages.extend(entry_pages)
        page_index_offset += len(entry_pages)

    return all_pages
