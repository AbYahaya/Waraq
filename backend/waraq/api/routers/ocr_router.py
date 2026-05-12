"""OCR endpoints.

Three families:

1. **Per-segment** (M1) — `POST /ocr/pages/{u}/start` + `POST /ocr/jobs/{u}/run/{s}`.
   Synchronous; multipart upload of page bytes.

2. **Per-page auto-run** (M3) — `POST /ocr/pages/{u}/auto-run`. Renders the
   page from the SCAN-PO, runs OCR, persists revision + OCR-PO. Synchronous
   in HTTP scope — single page is short enough to wait on (10–30 s).

3. **Per-project auto-run** (sub-batch O, 2026-05-12) — `POST
   /ocr/projects/{u}/auto-run` is now **detached**: returns 202 + the
   tracking Job's UUID immediately and the loop runs in a BackgroundTask.
   Companion endpoints `GET /ocr/ocr-jobs/{u}` (status polling) and
   `POST /ocr/ocr-jobs/{u}/cancel` (cooperative abort) replace the old
   "synchronous in HTTP scope" pattern that froze the UI for minutes
   and died on page refresh. `GET /ocr/projects/{u}/ocr-jobs/in-flight`
   lets the frontend resume the progress UI after a page refresh.
"""

from __future__ import annotations

import logging
import uuid as _uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.api._ownership import owned_page_or_404, owned_project_or_404
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
from waraq.ocr.auto_run import (
    OCR_AUTO_RUN_JOB_TYPE,
    find_in_flight_for_project,
    request_cancel,
    run_ocr_auto_run_job_in_background,
    start_ocr_auto_run_job,
)
from waraq.ocr.page_runner import PageOcrError, run_ocr_for_page
from waraq.schemas import Job, Page, Project, Segment
from waraq.schemas.enums import OcrStatus

logger = logging.getLogger(__name__)

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


# --- Auto-run helpers (UI-facing) ----------------------------------------
#
# `start` + `run` above expect the caller to already have a Segment and to
# provide PNG bytes. The endpoints below let a UI button drive the full
# rasterize + segment-provision + extract sequence in one call.


class PageOcrAutoResponse(BaseModel):
    page_uuid: _uuid.UUID
    text: str
    text_chars: int
    text_changed: bool
    segment_uuid: _uuid.UUID
    rev_uuid: _uuid.UUID | None


class ProjectOcrAutoResponse(BaseModel):
    """Pre-O response shape — preserved for the legacy synchronous
    callers (kept as deprecated; new callers use `OcrAutoRunStartResponse`).
    """

    project_uuid: _uuid.UUID
    pages_processed: int
    pages_skipped: int
    skipped_page_uuids: list[_uuid.UUID]


# Sub-batch O response shapes.


class OcrAutoRunStartResponse(BaseModel):
    """Returned 202 ACCEPTED when the project auto-run is queued. The
    frontend polls `GET /ocr/ocr-jobs/{job_uuid}` for progress."""

    ocr_job_uuid: _uuid.UUID
    project_uuid: _uuid.UUID
    state: str
    total_pages: int


class OcrJobStatusResponse(BaseModel):
    """Progress + state of an OCR auto-run Job. The poll target for
    the frontend progress UI."""

    ocr_job_uuid: _uuid.UUID
    project_uuid: _uuid.UUID
    state: str  # JobState.value
    total_pages: int
    processed_count: int
    skipped_count: int
    current_page_index: int | None
    cancel_requested: bool
    last_error: dict[str, Any] | None
    result: dict[str, Any] | None
    created_at: str  # ISO-8601


@router.post(
    "/pages/{page_uuid}/auto-run",
    response_model=PageOcrAutoResponse,
    status_code=status.HTTP_200_OK,
)
async def auto_run_page(
    page_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> PageOcrAutoResponse:
    """Render the page from the stored source PDF, provision a default
    main_text Block + Segment if absent, then run Gemini OCR. Page
    `ocr_status` is left untouched — the review state machine is driven
    separately via `/pages/{u}/ocr-review/...`.
    """
    page = await owned_page_or_404(session, page_uuid, current.account_uuid)
    # §H-5 / data-integrity gate: only `ausstehend` pages may be OCR'd.
    # The project-wide auto-run already enforces this; the per-page
    # endpoint enforces it here so a second click while the first run
    # is still in flight (or after it has produced rows) cannot
    # silently create a duplicate Block. Re-running OCR on an already
    # OCR'd page is a deliberate user action that goes through an
    # explicit reset path (not yet wired — this is the canonical
    # refusal until that lands).
    if page.ocr_status != OcrStatus.AUSSTEHEND:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "reason": "page_already_ocrd",
                "ocr_status": page.ocr_status.value,
            },
        )
    # Sub-batch O — add visibility + bounded wait. Per-page is still
    # synchronous in HTTP scope (single page is short enough to wait
    # on), but the request is now logged and timeout-bounded so the
    # caller can't hang on a stuck Gemini/Cloud Vision call forever.
    import asyncio

    from waraq.ocr.auto_run import PER_PAGE_TIMEOUT_SECONDS

    logger.info(
        "ocr.page.start",
        extra={"page_uuid": str(page_uuid), "page_index": page.page_index},
    )
    try:
        result = await asyncio.wait_for(
            run_ocr_for_page(session=session, page=page),
            timeout=PER_PAGE_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        logger.exception(
            "ocr.page.timeout",
            extra={
                "page_uuid": str(page_uuid),
                "timeout_s": PER_PAGE_TIMEOUT_SECONDS,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"OCR exceeded {PER_PAGE_TIMEOUT_SECONDS:.0f}s per-page timeout",
        ) from exc
    except PageOcrError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except H1H2Violation as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Segment is locked ({exc!s})"
        ) from exc
    except MissingGeminiApiKey as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR provider not configured (missing API key)",
        ) from exc
    except (GeminiApiError, OcrError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"OCR error: {exc!s}"
        ) from exc
    logger.info(
        "ocr.page.done",
        extra={
            "page_uuid": str(page_uuid),
            "page_index": page.page_index,
            "text_chars": result.text_chars,
        },
    )
    return PageOcrAutoResponse(
        page_uuid=result.page_uuid,
        text=result.text,
        text_chars=result.text_chars,
        text_changed=result.text_changed,
        segment_uuid=result.segment_uuid,
        rev_uuid=result.rev_uuid,
    )


def _job_to_status(job: Job) -> OcrJobStatusResponse:
    payload: dict[str, Any] = job.payload or {}
    assert job.project_uuid is not None
    return OcrJobStatusResponse(
        ocr_job_uuid=job.job_uuid,
        project_uuid=job.project_uuid,
        state=job.state,
        total_pages=int(payload.get("total_pages", 0)),
        processed_count=int(payload.get("processed_count", 0)),
        skipped_count=int(payload.get("skipped_count", 0)),
        current_page_index=(
            int(payload["current_page_index"])
            if isinstance(payload.get("current_page_index"), int)
            else None
        ),
        cancel_requested=bool(payload.get("cancel_requested", False)),
        last_error=(job.error if isinstance(job.error, dict) else None),
        result=(job.result if isinstance(job.result, dict) else None),
        created_at=job.created_at.isoformat(),
    )


@router.post(
    "/projects/{project_uuid}/auto-run",
    response_model=OcrAutoRunStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def auto_run_project(
    project_uuid: _uuid.UUID,
    background_tasks: BackgroundTasks,
    session: DbSession,
    current: CurrentAccount,
) -> OcrAutoRunStartResponse:
    """Sub-batch O — kick off project-wide OCR auto-run **detached**.

    Creates a PENDING Job, queues the runner via BackgroundTasks, and
    returns 202 + the Job's UUID immediately. The frontend polls
    `GET /ocr/ocr-jobs/{job_uuid}` for progress and uses
    `POST /ocr/ocr-jobs/{job_uuid}/cancel` for cooperative abort.

    Pages already past `ausstehend` are skipped by the runner. The
    per-page OCR call is bounded by `PER_PAGE_TIMEOUT_SECONDS` so a
    hung upstream can't stall the whole run; on timeout the job
    fails with `error.phase = page_timeout`.
    """
    project = await owned_project_or_404(session, project_uuid, current.account_uuid)
    job = await start_ocr_auto_run_job(session=session, project=project)
    await session.commit()  # ensure the Job is visible to the BackgroundTask's session

    from waraq.db.session import _sessionmaker

    background_tasks.add_task(
        run_ocr_auto_run_job_in_background, job.job_uuid, _sessionmaker
    )
    logger.info(
        "ocr_auto_run.queued",
        extra={
            "ocr_job_uuid": str(job.job_uuid),
            "project_uuid": str(project.project_uuid),
            "total_pages": (job.payload or {}).get("total_pages", 0),
        },
    )
    return OcrAutoRunStartResponse(
        ocr_job_uuid=job.job_uuid,
        project_uuid=project.project_uuid,
        state=job.state,
        total_pages=int((job.payload or {}).get("total_pages", 0)),
    )


@router.get(
    "/ocr-jobs/{job_uuid}",
    response_model=OcrJobStatusResponse,
)
async def get_ocr_job_status(
    job_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> OcrJobStatusResponse:
    """Progress + state poll target for the frontend OCR auto-run UI."""
    job: Job | None = await session.get(Job, job_uuid)
    if (
        job is None
        or job.job_type != OCR_AUTO_RUN_JOB_TYPE
        or job.project_uuid is None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OCR job not found"
        )
    project: Project | None = await session.get(Project, job.project_uuid)
    if project is None or project.account_uuid != current.account_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OCR job not found"
        )
    return _job_to_status(job)


@router.post(
    "/ocr-jobs/{job_uuid}/cancel",
    response_model=OcrJobStatusResponse,
)
async def cancel_ocr_job(
    job_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> OcrJobStatusResponse:
    """Request cooperative cancel of an OCR auto-run Job.

    Sets `payload.cancel_requested = true`. The runner checks the flag
    between pages and aborts with `error.phase = user_cancelled`.
    Idempotent — calling cancel on a terminal job is a no-op.
    """
    job: Job | None = await session.get(Job, job_uuid)
    if (
        job is None
        or job.job_type != OCR_AUTO_RUN_JOB_TYPE
        or job.project_uuid is None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OCR job not found"
        )
    project: Project | None = await session.get(Project, job.project_uuid)
    if project is None or project.account_uuid != current.account_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OCR job not found"
        )
    job = await request_cancel(session=session, job=job)
    await session.commit()
    return _job_to_status(job)


@router.get(
    "/projects/{project_uuid}/ocr-jobs/in-flight",
    response_model=OcrJobStatusResponse | None,
)
async def get_in_flight_ocr_job(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> OcrJobStatusResponse | None:
    """Resume helper: the frontend calls this on workspace mount so a
    page refresh can pick up an in-flight progress bar. Returns the
    most-recent non-terminal OCR auto-run Job for the project, or
    null if none."""
    project = await owned_project_or_404(session, project_uuid, current.account_uuid)
    job = await find_in_flight_for_project(
        session=session, project_uuid=project.project_uuid
    )
    if job is None:
        return None
    return _job_to_status(job)

