"""Sub-batch O (out-of-phase, 2026-05-12) — OCR auto-run visibility refactor.

Mirrors the translation /run pattern from earlier:

- `start_ocr_auto_run_job(session, project)` creates a PENDING Job with
  `job_type=OCR_AUTO_RUN_JOB_TYPE`, payload pre-loaded with
  `total_pages` / `processed_count=0` / `cancel_requested=False`.
- `run_ocr_auto_run_job_in_background(job_uuid)` is the BackgroundTask
  entrypoint — opens its own DB session (the request session is gone
  by the time it runs), drives the page loop with per-page commits so
  progress + cancel-flag state are visible to other sessions in real
  time, and wraps each per-page OCR call in `asyncio.wait_for` so a
  hung Gemini / Cloud Vision call can't stall the whole run.

The loop checks `payload.cancel_requested` between pages — a separate
HTTP request can set the flag and the next iteration bails with
`OcrAutoRunCancelled`.

Logging is per-page at INFO level so server logs actually show
progress instead of going silent for minutes.
"""

from __future__ import annotations

import asyncio
import logging
import uuid as _uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from waraq.identity import new_uuid
from waraq.jobs import complete_job, fail_job, start_job, write_checkpoint
from waraq.ocr.exceptions import OcrError
from waraq.ocr.page_runner import PageOcrError, run_ocr_for_page
from waraq.schemas import Job, Page, Project
from waraq.schemas.enums import JobState, OcrStatus

logger = logging.getLogger(__name__)

OCR_AUTO_RUN_JOB_TYPE = "ocr_auto_run"

# Hard cap per page so a hung upstream OCR call can't stall the whole
# project loop. Conservative — Gemini + Cloud Vision typically finish in
# 10-30s; 120s leaves room for retries the SDK might do internally.
PER_PAGE_TIMEOUT_SECONDS: float = 120.0


class OcrAutoRunCancelled(Exception):
    """Cooperative cancel — set by the /cancel endpoint via
    `payload.cancel_requested=True`. The runner checks between pages
    and raises this; the BackgroundTask body swallows it after
    `fail_job` records the failure."""


async def start_ocr_auto_run_job(
    *,
    session: AsyncSession,
    project: Project,
) -> Job:
    """Materialize a PENDING Job for the project's auto-run. The
    endpoint hands this to BackgroundTasks; the runner picks it up
    and drives the page loop."""
    # Count `ausstehend` pages now so the UI has a real total to show
    # before the runner even starts. Pages added later in the run
    # would not be picked up — auto-run is a snapshot of "pages that
    # need OCR at the moment the user clicked the button".
    result = await session.execute(
        select(Page)
        .where(Page.project_uuid == project.project_uuid)
        .where(Page.active.is_(True))
        .where(Page.ocr_status == OcrStatus.AUSSTEHEND)
    )
    candidates = list(result.scalars())
    total = len(candidates)

    job = Job(
        job_uuid=new_uuid(),
        job_type=OCR_AUTO_RUN_JOB_TYPE,
        state=JobState.PENDING.value,
        project_uuid=project.project_uuid,
        payload={
            "total_pages": total,
            "processed_count": 0,
            "skipped_count": 0,
            "current_page_index": None,
            "cancel_requested": False,
            "last_error": None,
        },
    )
    session.add(job)
    await session.flush()
    return job


async def run_ocr_auto_run_job_in_background(
    job_uuid: _uuid.UUID,
    sessionmaker_factory: Any,
) -> None:
    """BackgroundTask entrypoint. Mirrors the translation pattern: open
    a fresh session (the request session is closed), look up the Job,
    drive the loop with per-page commits so progress + cancel-flag
    state are visible to other sessions.

    `sessionmaker_factory` is a callable returning a sessionmaker (so
    the caller can inject the real one without import-loops).
    """
    sm = sessionmaker_factory()
    async with sm() as session:
        try:
            job = await session.get(Job, job_uuid)
            if job is None or job.job_type != OCR_AUTO_RUN_JOB_TYPE:
                logger.warning(
                    "ocr_auto_run.background.job_missing",
                    extra={"job_uuid": str(job_uuid)},
                )
                return
            await _execute(session=session, job=job)
            await session.commit()
        except OcrAutoRunCancelled:
            logger.info(
                "ocr_auto_run.background.cancelled",
                extra={"job_uuid": str(job_uuid)},
            )
        except Exception:
            # `_execute` already persisted the failure via fail_job
            # for OCR-shaped errors. Anything that escapes here is an
            # unexpected programmer error — log + swallow.
            logger.exception(
                "ocr_auto_run.background.failed",
                extra={"job_uuid": str(job_uuid)},
            )


async def _execute(*, session: AsyncSession, job: Job) -> None:
    """Inner loop. Runs in the BackgroundTask's session. Each page is
    processed in its own logical transaction (flush + commit) so
    progress + cancel-flag state are visible to other sessions in
    real time.

    Transitions:
      PENDING → RUNNING on first iteration
      RUNNING → COMPLETED on clean finish
      RUNNING → FAILED on per-page error (loop aborts at the failing
                page; processed pages stay persisted)
      RUNNING → FAILED with error.phase=user_cancelled when the cancel
                flag is set between pages
    """
    assert job.project_uuid is not None
    # PENDING → RUNNING.
    if job.state == JobState.PENDING.value:
        await start_job(session=session, job=job)
        await session.commit()

    pages = await _ausstehend_pages(session, job.project_uuid)
    skipped: list[_uuid.UUID] = []
    processed = 0

    for i, page in enumerate(pages, start=1):
        # Cooperative cancel: re-read the job row so a concurrent
        # cancel call's flag write is visible.
        await session.refresh(job)
        payload: dict[str, Any] = job.payload or {}
        if bool(payload.get("cancel_requested")):
            logger.info(
                "ocr_auto_run.cancel.flagged",
                extra={"job_uuid": str(job.job_uuid), "processed": processed},
            )
            await fail_job(
                session=session,
                job=job,
                error={"phase": "user_cancelled", "processed_count": processed},
            )
            await session.commit()
            raise OcrAutoRunCancelled

        # Skip pages already past AUSSTEHEND — race-safe re-check
        # (another process may have OCR'd them).
        await session.refresh(page)
        if page.ocr_status != OcrStatus.AUSSTEHEND:
            skipped.append(page.page_uuid)
            payload["skipped_count"] = len(skipped)
            payload["current_page_index"] = page.page_index
            flag_modified(job, "payload")
            await session.commit()
            continue

        payload["current_page_index"] = page.page_index
        flag_modified(job, "payload")
        await session.commit()

        logger.info(
            "ocr_auto_run.page.start",
            extra={
                "job_uuid": str(job.job_uuid),
                "page_index": page.page_index,
                "page_uuid": str(page.page_uuid),
                "progress": f"{i}/{len(pages)}",
            },
        )

        try:
            await asyncio.wait_for(
                run_ocr_for_page(session=session, page=page),
                timeout=PER_PAGE_TIMEOUT_SECONDS,
            )
            # Persist this page's OCR-PO + revision before the next
            # iteration so progress is durable across crashes.
            await session.commit()
        except TimeoutError:
            logger.exception(
                "ocr_auto_run.page.timeout",
                extra={
                    "job_uuid": str(job.job_uuid),
                    "page_index": page.page_index,
                    "timeout_s": PER_PAGE_TIMEOUT_SECONDS,
                },
            )
            await session.rollback()
            await fail_job(
                session=session,
                job=job,
                error={
                    "phase": "page_timeout",
                    "page_index": page.page_index,
                    "timeout_s": PER_PAGE_TIMEOUT_SECONDS,
                    "processed_count": processed,
                },
            )
            await session.commit()
            return
        except (PageOcrError, OcrError, SQLAlchemyError) as exc:
            logger.exception(
                "ocr_auto_run.page.error",
                extra={
                    "job_uuid": str(job.job_uuid),
                    "page_index": page.page_index,
                },
            )
            await session.rollback()
            await fail_job(
                session=session,
                job=job,
                error={
                    "phase": "page_error",
                    "page_index": page.page_index,
                    "error_class": type(exc).__name__,
                    "message": str(exc)[:300],
                    "processed_count": processed,
                },
            )
            await session.commit()
            return

        processed += 1
        # Re-read job (commit refreshed the row); update progress.
        await session.refresh(job)
        payload = job.payload or {}
        payload["processed_count"] = processed
        payload["skipped_count"] = len(skipped)
        flag_modified(job, "payload")
        await write_checkpoint(
            session=session,
            job=job,
            step=f"page_{page.page_index}_ocrd",
            payload={"page_uuid": str(page.page_uuid), "page_index": page.page_index},
        )
        await session.commit()

        logger.info(
            "ocr_auto_run.page.done",
            extra={
                "job_uuid": str(job.job_uuid),
                "page_index": page.page_index,
                "processed_count": processed,
            },
        )

    # Loop completed cleanly.
    await session.refresh(job)
    await complete_job(
        session=session,
        job=job,
        result={
            "processed_count": processed,
            "skipped_count": len(skipped),
            "skipped_page_uuids": [str(u) for u in skipped],
            "total_pages_at_start": (job.payload or {}).get("total_pages", processed),
        },
    )
    logger.info(
        "ocr_auto_run.done",
        extra={
            "job_uuid": str(job.job_uuid),
            "processed_count": processed,
            "skipped_count": len(skipped),
        },
    )


async def _ausstehend_pages(
    session: AsyncSession, project_uuid: _uuid.UUID
) -> Sequence[Page]:
    result = await session.execute(
        select(Page)
        .where(Page.project_uuid == project_uuid)
        .where(Page.active.is_(True))
        .where(Page.ocr_status == OcrStatus.AUSSTEHEND)
        .order_by(Page.page_index.asc())
    )
    return list(result.scalars())


async def request_cancel(*, session: AsyncSession, job: Job) -> Job:
    """Set the cancel flag on `job.payload`. The runner checks this
    between pages and bails with `OcrAutoRunCancelled`. Idempotent —
    re-cancelling is a no-op. Does NOT transition state directly to
    avoid the race against the runner's own state writes."""
    if job.state not in (JobState.PENDING.value, JobState.RUNNING.value):
        # No-op on terminal jobs.
        return job
    payload: dict[str, Any] = job.payload or {}
    payload["cancel_requested"] = True
    flag_modified(job, "payload")
    await session.flush()
    return job


async def find_in_flight_for_project(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> Job | None:
    """Return the most-recent non-terminal OCR auto-run Job for the
    project, or None. The frontend uses this on mount so a page
    refresh survives an in-flight run (the user keeps seeing the
    progress bar)."""
    result = await session.execute(
        select(Job)
        .where(Job.project_uuid == project_uuid)
        .where(Job.job_type == OCR_AUTO_RUN_JOB_TYPE)
        .where(Job.state.in_([JobState.PENDING.value, JobState.RUNNING.value]))
        .order_by(Job.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


__all__ = [
    "OCR_AUTO_RUN_JOB_TYPE",
    "PER_PAGE_TIMEOUT_SECONDS",
    "OcrAutoRunCancelled",
    "find_in_flight_for_project",
    "request_cancel",
    "run_ocr_auto_run_job_in_background",
    "start_ocr_auto_run_job",
]
