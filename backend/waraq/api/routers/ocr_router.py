"""OCR endpoints — start an OCR job for a Page, run it for a Segment.

Two endpoints are exposed:

POST /ocr/pages/{page_uuid}/start
    Create a PENDING OCR Job for the given Page.

POST /ocr/jobs/{job_uuid}/run/{satz_uuid}
    Multipart upload of the page image bytes; runs the OCR job against the
    target Segment, writes Revision (on text change) + OCR-PO. Returns the
    extracted text.

The HTTP layer doesn't (yet) handle PDF→image rasterization — clients
provide page images directly. That's a deliberate scope choice for M1
closeout; rasterization belongs in the OCR pipeline expansion in M3.
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import OcrRunResponse, OcrStartResponse
from waraq.invariant.exceptions import H1H2Violation
from waraq.ocr import (
    GeminiApiError,
    MissingGeminiApiKey,
    OcrError,
    run_ocr_job,
    start_ocr_job,
)
from waraq.schemas import Job, Page, Project, Segment

router = APIRouter(prefix="/ocr", tags=["ocr"])


async def _owned_page_or_404(
    session: AsyncSession, page_uuid: _uuid.UUID, account_uuid: _uuid.UUID
) -> Page:
    page: Page | None = await session.get(Page, page_uuid)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    project = await session.get(Project, page.project_uuid)
    if project is None or project.account_uuid != account_uuid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return page


async def _owned_segment_or_404(
    session: AsyncSession, satz_uuid: _uuid.UUID, account_uuid: _uuid.UUID
) -> Segment:
    segment: Segment | None = await session.get(Segment, satz_uuid)
    if segment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    # Walk segment → block → page → project to verify account ownership.
    from waraq.schemas import Block

    block: Block | None = await session.get(Block, segment.block_uuid)
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    page: Page | None = await session.get(Page, block.page_uuid)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    project: Project | None = await session.get(Project, page.project_uuid)
    if project is None or project.account_uuid != account_uuid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    return segment


async def _owned_ocr_job_or_404(
    session: AsyncSession, job_uuid: _uuid.UUID, account_uuid: _uuid.UUID
) -> Job:
    job: Job | None = await session.get(Job, job_uuid)
    if job is None or job.job_type != "ocr_baseline":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OCR job not found")
    project: Project | None = await session.get(Project, job.project_uuid)
    if project is None or project.account_uuid != account_uuid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OCR job not found")
    return job


@router.post(
    "/pages/{page_uuid}/start",
    response_model=OcrStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start(
    page_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> OcrStartResponse:
    page = await _owned_page_or_404(session, page_uuid, current.account_uuid)
    job = await start_ocr_job(session=session, page=page)
    return OcrStartResponse(job_uuid=job.job_uuid, state=job.state)


@router.post("/jobs/{job_uuid}/run/{satz_uuid}", response_model=OcrRunResponse)
async def run(
    job_uuid: _uuid.UUID,
    satz_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
    image: UploadFile = File(...),
    mime_type: str = Form(default="image/png"),
) -> OcrRunResponse:
    job = await _owned_ocr_job_or_404(session, job_uuid, current.account_uuid)
    segment = await _owned_segment_or_404(session, satz_uuid, current.account_uuid)
    image_bytes = await image.read()

    try:
        text = await run_ocr_job(
            session=session,
            ocr_job=job,
            image_bytes=image_bytes,
            mime_type=mime_type,
            target_segment=segment,
        )
    except H1H2Violation as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Segment is locked ({exc!s})",
        ) from exc
    except MissingGeminiApiKey as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR provider not configured (missing API key)",
        ) from exc
    except GeminiApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OCR provider error: {exc!s}",
        ) from exc
    except OcrError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OCR error: {exc!s}",
        ) from exc

    assert job.result is not None
    rev_uuid_str = job.result.get("rev_uuid")
    return OcrRunResponse(
        job_uuid=job.job_uuid,
        state=job.state,
        text=text,
        text_chars=job.result["text_chars"],
        text_changed=job.result["text_changed"],
        rev_uuid=_uuid.UUID(rev_uuid_str) if rev_uuid_str else None,
    )
