"""Upload endpoints — start, append chunk, finalize, status."""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import (
    DuplicateMatchResponse,
    UploadFinalizeResponse,
    UploadPrecheckResponse,
    UploadStartRequest,
    UploadStartResponse,
    UploadStatusResponse,
)
from waraq.notifications.events import notify_project_event, project_workspace_url
from waraq.schemas import Job, Project
from waraq.upload import (
    ArchiveCorrupted,
    ChunkOutOfOrder,
    DjvuToolsMissing,
    EmptyArchive,
    EmptyDocument,
    IncompleteUpload,
    TextExtractionError,
    UnrarToolsMissing,
    UnsupportedFormat,
    UploadNotFound,
    UploadSizeMismatch,
    UploadTooLarge,
    append_chunk,
    finalize_upload,
    get_upload_status,
    start_upload,
)
from waraq.upload.duplicate import (
    DuplicateMatch,
    find_sha256_matches,
    precheck_for_project,
)

router = APIRouter(prefix="/uploads", tags=["uploads"])


def _match_to_response(m: DuplicateMatch) -> DuplicateMatchResponse:
    return DuplicateMatchResponse(
        page_uuid=m.page_uuid,
        page_index=m.page_index,
        upload_job_uuid=m.upload_job_uuid,
        original_filename=m.original_filename,
        source_sha256=m.source_sha256,
        match_kind=m.match_kind,
    )


async def _project_or_404(
    session: AsyncSession, project_uuid: _uuid.UUID, account_uuid: _uuid.UUID
) -> Project:
    project: Project | None = await session.get(Project, project_uuid)
    if project is None or project.account_uuid != account_uuid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


async def _upload_job_or_404(
    session: AsyncSession, job_uuid: _uuid.UUID, account_uuid: _uuid.UUID
) -> Job:
    job: Job | None = await session.get(Job, job_uuid)
    if job is None or job.job_type != "upload":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    # Authorization: only the owning account can touch the upload.
    project: Project | None = await session.get(Project, job.project_uuid)
    if project is None or project.account_uuid != account_uuid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return job


@router.post(
    "",
    response_model=UploadStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start(
    req: UploadStartRequest,
    session: DbSession,
    current: CurrentAccount,
) -> UploadStartResponse:
    project = await _project_or_404(session, req.project_uuid, current.account_uuid)
    try:
        job = await start_upload(
            session=session,
            project=project,
            original_filename=req.original_filename,
            total_chunks=req.total_chunks,
            total_size_bytes=req.total_size_bytes,
        )
    except UploadTooLarge as exc:
        # K-5 row 5: declared total exceeds 2 GB. Reject up front
        # so 2 GB+ of bytes don't transit before finalize.
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    return UploadStartResponse(
        job_uuid=job.job_uuid,
        state=job.state,
        expected_next_chunk=0,
    )


@router.get(
    "/precheck",
    response_model=UploadPrecheckResponse,
)
async def precheck(
    project_uuid: _uuid.UUID,
    filename: str,
    session: DbSession,
    current: CurrentAccount,
) -> UploadPrecheckResponse:
    """K-5 rows 6+7. Called by the frontend when the user picks a file,
    BEFORE any bytes upload. Returns filename matches (canon row 6 part 1)
    + `project_has_existing_pages` flag (canon row 7 1-book-at-a-time
    warning). Both warnings only; frontend shows modals; user confirms
    to proceed."""
    await _project_or_404(session, project_uuid, current.account_uuid)
    result = await precheck_for_project(
        session=session, project_uuid=project_uuid, filename=filename
    )
    return UploadPrecheckResponse(
        filename_matches=[_match_to_response(m) for m in result.filename_matches],
        project_has_existing_pages=result.project_has_existing_pages,
    )


@router.post("/{job_uuid}/chunks/{chunk_index}", status_code=status.HTTP_204_NO_CONTENT)
async def append(
    job_uuid: _uuid.UUID,
    chunk_index: int,
    session: DbSession,
    current: CurrentAccount,
    chunk: UploadFile = File(...),
) -> None:
    job = await _upload_job_or_404(session, job_uuid, current.account_uuid)
    chunk_data = await chunk.read()
    try:
        await append_chunk(
            session=session,
            upload_job=job,
            chunk_index=chunk_index,
            chunk_data=chunk_data,
        )
    except ChunkOutOfOrder as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Expected chunk {exc.expected}, received chunk {exc.received}",
        ) from exc
    except UploadTooLarge as exc:
        # K-5 row 5 defensive cap. Cumulative bytes-on-disk exceeded
        # 2 GB despite the declared total. Client lied or chunk-stream
        # was tampered with.
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc


@router.get("/{job_uuid}", response_model=UploadStatusResponse)
async def status_endpoint(
    job_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> UploadStatusResponse:
    # Auth + presence check first.
    await _upload_job_or_404(session, job_uuid, current.account_uuid)
    try:
        s = await get_upload_status(session=session, job_uuid=job_uuid)
    except UploadNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        ) from exc
    return UploadStatusResponse(
        job_uuid=s.job_uuid,
        state=s.state.value,
        received_chunks=s.received_chunks,
        total_chunks=s.total_chunks,
        expected_next_chunk=s.expected_next_chunk,
    )


@router.post("/{job_uuid}/finalize", response_model=UploadFinalizeResponse)
async def finalize(
    job_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> UploadFinalizeResponse:
    job = await _upload_job_or_404(session, job_uuid, current.account_uuid)
    try:
        pages = await finalize_upload(session=session, upload_job=job)
    except IncompleteUpload as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Upload incomplete: {exc.received}/{exc.total} chunks received",
        ) from exc
    except UploadSizeMismatch as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Size mismatch: declared {exc.declared}, got {exc.actual}",
        ) from exc
    except UnsupportedFormat as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except EmptyDocument as exc:
        # Direct-text upload parsed cleanly but had no non-whitespace
        # paragraphs. Better than silently materializing a 0-Segment Page.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except TextExtractionError as exc:
        # Direct-text parser failed (malformed XML/HTML, etc.). 422 to
        # signal "we understood the format but couldn't parse it".
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except DjvuToolsMissing as exc:
        # K-3 DjVu upload but the host is missing `djvulibre-bin`.
        # 503 (service unavailable) signals "we accept this format but
        # the server can't process it right now" — distinct from the
        # 415 "we don't accept this format at all" surface.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except UnrarToolsMissing as exc:
        # K-4 RAR/CBR upload but the host is missing `unrar`. Same 503
        # semantic as DjVu's djvulibre-bin gap.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except EmptyArchive as exc:
        # K-4 archive parsed cleanly but contains no supported entries.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ArchiveCorrupted as exc:
        # K-4 archive can't be opened/read — bad CRC, truncated, etc.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    assert job.result is not None  # set by finalize_upload on success

    # K-5 row 6 SHA-256 dedupe: look up any prior pages in this
    # project with the same content hash. Exclude pages from THIS
    # upload (otherwise the just-finalized upload always "duplicates
    # itself" since archive recursion can produce multiple pages with
    # the same SHA-256). Upload jobs always have `project_uuid` set
    # (validated at start_upload), but mypy sees `Job.project_uuid` as
    # `UUID | None` — assert defensively.
    source_sha256: str = job.result["source_sha256"]
    assert job.project_uuid is not None
    project = await _project_or_404(session, job.project_uuid, current.account_uuid)
    sha256_matches = await find_sha256_matches(
        session=session,
        project_uuid=job.project_uuid,
        sha256=source_sha256,
        exclude_job_uuid=job.job_uuid,
    )
    await notify_project_event(
        session=session,
        project=project,
        kind="upload_finalized",
        severity="success",
        title=f"Upload processed — {project.name}",
        body=f"{job.result['page_count']} page(s) are ready for OCR review.",
        target_url=project_workspace_url(project.project_uuid, pages[0].page_uuid if pages else None),
        action_label="Open project",
    )
    return UploadFinalizeResponse(
        job_uuid=job.job_uuid,
        state=job.state,
        page_count=job.result["page_count"],
        page_uuids=[p.page_uuid for p in pages],
        source_sha256=source_sha256,
        duplicate_sha256_matches=[_match_to_response(m) for m in sha256_matches],
    )
