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
import os
import uuid as _uuid
from collections.abc import Sequence
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from waraq.identity import new_uuid
from waraq.jobs import complete_job, fail_job, start_job, write_checkpoint
from waraq.notifications.events import (
    notify_project_event,
    project_audit_url,
    project_workspace_url,
)
from waraq.ocr.exceptions import OcrError
from waraq.ocr.page_runner import PageOcrError, run_ocr_for_page
from waraq.schemas import Job, Page, Project
from waraq.schemas.enums import JobState, OcrStatus

logger = logging.getLogger(__name__)

OCR_AUTO_RUN_JOB_TYPE = "ocr_auto_run"
_LIVE_PAGE_TASKS: dict[_uuid.UUID, asyncio.Task[Any]] = {}

# Hard cap per page so a hung upstream OCR call can't stall the whole
# project loop. The earlier 240s assumption no longer holds reliably
# once layout detection + multi-block OCR + Stage-3 validation all run
# on larger real pages, so this is now configurable and defaults to a
# more forgiving 600s.
#
# This does NOT fix the deeper "page OCR still segments internally"
# architecture, but it removes the immediate false-timeout failure mode
# while that restructuring is in progress.
PER_PAGE_TIMEOUT_SECONDS: float = float(os.environ.get("OCR_PER_PAGE_TIMEOUT_SECONDS", "600"))

# Heartbeat staleness threshold for orphan reaping (sub-batch O follow-up,
# 2026-05-12). FastAPI BackgroundTasks die when the uvicorn worker dies
# (--reload restart, crash, OOM), leaving the Job row stuck in RUNNING
# with no worker to drive it. The runner commits between pages — those
# commits bump `Job.updated_at` via TimestampMixin's `onupdate=func.now()`,
# so `updated_at` is a free heartbeat.
#
# Threshold = 2.5 × PER_PAGE_TIMEOUT_SECONDS gives a healthy worker plenty
# of headroom (even a worst-case 120s page leaves 180s of slack) without
# letting a dead worker's row sit stuck for long.
STALE_HEARTBEAT_THRESHOLD_SECONDS: int = int(PER_PAGE_TIMEOUT_SECONDS * 2.5)
_CANCEL_POLL_INTERVAL_SECONDS: float = 1.0


class OcrAutoRunCancelled(Exception):
    """Cooperative cancel — set by the /cancel endpoint via
    `payload.cancel_requested=True`. The runner checks between pages
    and raises this; the BackgroundTask body swallows it after
    `fail_job` records the failure."""


async def _run_page_with_cancel_monitor(
    *,
    session: AsyncSession,
    job: Job,
    page: Page,
) -> None:
    """Run one page OCR while polling the cancel flag.

    This lets project-wide OCR cancel promptly even when a single page is
    taking a long time. The underlying provider call may still continue
    briefly in its own thread/network stack, but the job itself will stop
    waiting on it and terminate visibly on the server/UI side.
    """
    task = asyncio.create_task(run_ocr_for_page(session=session, page=page))
    _LIVE_PAGE_TASKS[job.job_uuid] = task
    try:
        while True:
            done, _pending = await asyncio.wait(
                {task},
                timeout=_CANCEL_POLL_INTERVAL_SECONDS,
            )
            if task in done:
                await task
                return

            await session.refresh(job)
            payload: dict[str, Any] = job.payload or {}
            if bool(payload.get("cancel_requested")):
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
                raise OcrAutoRunCancelled
    finally:
        _LIVE_PAGE_TASKS.pop(job.job_uuid, None)
        if not task.done():
            task.cancel()


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
    project: Project | None = await session.get(Project, job.project_uuid)
    if project is None:
        logger.warning("ocr_auto_run.project_missing", extra={"job_uuid": str(job.job_uuid)})
        return
    # PENDING → RUNNING.
    if job.state == JobState.PENDING.value:
        await start_job(session=session, job=job)
        await notify_project_event(
            session=session,
            project=project,
            kind="ocr_auto_run_started",
            severity="info",
            title=f"OCR started — {project.name}",
            body=f"Auto OCR started for {(job.payload or {}).get('total_pages', 0)} page(s).",
            target_url=project_workspace_url(project.project_uuid),
            action_label="Open project",
        )
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
        page_index = page.page_index

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
                _run_page_with_cancel_monitor(
                    session=session,
                    job=job,
                    page=page,
                ),
                timeout=PER_PAGE_TIMEOUT_SECONDS,
            )
            # Persist this page's OCR-PO + revision before the next
            # iteration so progress is durable across crashes.
            await session.commit()
        except OcrAutoRunCancelled:
            logger.info(
                "ocr_auto_run.page.cancelled",
                extra={
                    "job_uuid": str(job.job_uuid),
                    "page_index": page.page_index,
                    "processed_count": processed,
                },
            )
            await session.rollback()
            await session.refresh(job)
            await fail_job(
                session=session,
                job=job,
                error={
                    "phase": "user_cancelled",
                    "page_index": page_index,
                    "processed_count": processed,
                },
            )
            await notify_project_event(
                session=session,
                project=project,
                kind="ocr_auto_run_cancelled",
                severity="warning",
                title=f"OCR cancelled — {project.name}",
                body=f"Auto OCR was cancelled after {processed} processed page(s).",
                target_url=project_workspace_url(project.project_uuid),
                action_label="Open project",
            )
            await session.commit()
            raise
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
            await session.refresh(job)
            await fail_job(
                session=session,
                job=job,
                error={
                    "phase": "page_timeout",
                    "page_index": page_index,
                    "timeout_s": PER_PAGE_TIMEOUT_SECONDS,
                    "processed_count": processed,
                },
            )
            await notify_project_event(
                session=session,
                project=project,
                kind="ocr_auto_run_failed",
                severity="error",
                title=f"OCR stopped on page {page_index} — {project.name}",
                body=(
                    f"Page {page_index} exceeded the {PER_PAGE_TIMEOUT_SECONDS:.0f}s timeout. "
                    "Open Audit or DPI recovery to inspect the page."
                ),
                target_url=project_audit_url(project.project_uuid),
                action_label="Open Audit",
                page_uuid=page.page_uuid,
            )
            await session.commit()
            return
        except (PageOcrError, OcrError, SQLAlchemyError, Exception) as exc:
            logger.exception(
                "ocr_auto_run.page.error",
                extra={
                    "job_uuid": str(job.job_uuid),
                    "page_index": page.page_index,
                },
            )
            await session.rollback()
            await session.refresh(job)
            await fail_job(
                session=session,
                job=job,
                error={
                    "phase": "page_error",
                    "page_index": page_index,
                    "error_class": type(exc).__name__,
                    "message": str(exc)[:300],
                    "processed_count": processed,
                },
            )
            await notify_project_event(
                session=session,
                project=project,
                kind="ocr_auto_run_failed",
                severity="error",
                title=f"OCR stopped on page {page_index} — {project.name}",
                body=f"{type(exc).__name__}: {str(exc)[:220]}",
                target_url=project_audit_url(project.project_uuid),
                action_label="Open Audit",
                page_uuid=page.page_uuid,
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
    await notify_project_event(
        session=session,
        project=project,
        kind="ocr_auto_run_completed",
        severity="success",
        title=f"OCR completed — {project.name}",
        body=f"Processed {processed} page(s); skipped {len(skipped)} page(s).",
        target_url=project_audit_url(project.project_uuid),
        action_label="Review Audit",
    )
    logger.info(
        "ocr_auto_run.done",
        extra={
            "job_uuid": str(job.job_uuid),
            "processed_count": processed,
            "skipped_count": len(skipped),
        },
    )


async def _ausstehend_pages(session: AsyncSession, project_uuid: _uuid.UUID) -> Sequence[Page]:
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
    live_task = _LIVE_PAGE_TASKS.get(job.job_uuid)
    if live_task is not None and not live_task.done():
        live_task.cancel()
    await session.flush()
    return job


async def reap_orphan_jobs(
    *,
    session: AsyncSession,
    threshold_seconds: int = STALE_HEARTBEAT_THRESHOLD_SECONDS,
) -> list[_uuid.UUID]:
    """Mark stale RUNNING/PENDING ocr_auto_run Jobs as FAILED.

    Stale = `Job.updated_at` older than `threshold_seconds`. The runner
    commits between pages, and TimestampMixin's `onupdate=func.now()`
    refreshes `updated_at` on every commit, so a healthy worker keeps
    its row fresh well within the threshold. A row that hasn't been
    touched in that window had its worker process die — orphaned.

    Used by:
      - The app's lifespan startup hook (sweep all stale jobs once on
        boot, so a previous-server crash doesn't leave the UI staring
        at a zombie progress bar after restart).
      - The status-poll endpoint (self-heal stale rows inline so the
        frontend doesn't have to wait for next boot to unstick).

    Returns the list of reaped job_uuids. Safe to call concurrently
    (each row is locked individually via fail_job's UPDATE).
    """
    threshold = datetime.now(UTC) - timedelta(seconds=threshold_seconds)
    result = await session.execute(
        select(Job)
        .where(Job.job_type == OCR_AUTO_RUN_JOB_TYPE)
        .where(Job.state.in_([JobState.RUNNING.value, JobState.PENDING.value]))
    )
    candidates = list(result.scalars())
    reaped: list[_uuid.UUID] = []
    for job in candidates:
        await session.refresh(job, ["updated_at", "state"])
        payload: dict[str, Any] = job.payload or {}
        cancel_requested = bool(payload.get("cancel_requested"))
        stale = job.updated_at < threshold
        if not cancel_requested and not stale:
            continue
        previous_state = job.state
        phase = "cancel_requested_orphan" if cancel_requested else "server_restart_orphan"
        await fail_job(
            session=session,
            job=job,
            error={
                "phase": phase,
                "previous_state": previous_state,
                "reaped_at": datetime.now(UTC).isoformat(),
                "threshold_seconds": threshold_seconds,
                "note": (
                    "Job marked FAILED during orphan reap so the UI stops polling."
                    if cancel_requested
                    else "No heartbeat for >threshold — worker process died. "
                    "Job marked FAILED so the UI stops polling."
                ),
            },
        )
        reaped.append(job.job_uuid)
    return reaped


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
    "STALE_HEARTBEAT_THRESHOLD_SECONDS",
    "OcrAutoRunCancelled",
    "find_in_flight_for_project",
    "reap_orphan_jobs",
    "request_cancel",
    "run_ocr_auto_run_job_in_background",
    "start_ocr_auto_run_job",
]
