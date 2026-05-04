"""Upload endpoints — start, append chunk, finalize, status."""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import (
    UploadFinalizeResponse,
    UploadStartRequest,
    UploadStartResponse,
    UploadStatusResponse,
)
from waraq.schemas import Job, Project
from waraq.upload import (
    ChunkOutOfOrder,
    IncompleteUpload,
    UploadNotFound,
    UploadSizeMismatch,
    append_chunk,
    finalize_upload,
    get_upload_status,
    start_upload,
)

router = APIRouter(prefix="/uploads", tags=["uploads"])


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
    job = await start_upload(
        session=session,
        project=project,
        original_filename=req.original_filename,
        total_chunks=req.total_chunks,
        total_size_bytes=req.total_size_bytes,
    )
    return UploadStartResponse(
        job_uuid=job.job_uuid,
        state=job.state,
        expected_next_chunk=0,
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

    assert job.result is not None  # set by finalize_upload on success
    return UploadFinalizeResponse(
        job_uuid=job.job_uuid,
        state=job.state,
        page_count=job.result["page_count"],
        page_uuids=[p.page_uuid for p in pages],
        source_sha256=job.result["source_sha256"],
    )
