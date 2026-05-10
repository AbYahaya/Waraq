"""Translation endpoints — start a translation Job, run it, poll its state.

The `/run` endpoint validates the Job, then launches the translation
loop via `BackgroundTasks` so the HTTP request returns immediately with
a RUNNING job. The browser polls `GET /translation-jobs/{u}` for
progress (`payload.chunks_translated` / `payload.chunks_total`) and a
companion `/cancel` endpoint flips a cooperative-cancel flag the loop
checks between chunks.
"""

from __future__ import annotations

import logging
import uuid as _uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from waraq.api._ownership import owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import JobResponse, TranslationStartRequest
from waraq.db.session import _sessionmaker
from waraq.schemas import Job, Project
from waraq.schemas.enums import JobState
from waraq.translation import (
    JOB_TYPE,
    TranslationJobUebersetzungsstartMissing,
    make_translation_persistence_hook,
    run_translation_job,
    start_translation_job,
)
from waraq.translation.cross_check import make_cross_checked_translator
from waraq.translation.exceptions import TranslationJobCancelled
from waraq.translation.gemini_translator import (
    GeminiTranslatorUnconfigured,
    make_gemini_translator,
)
from waraq.translation.openai_translator import (
    OpenAITranslatorUnconfigured,
    make_openai_translator,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["translation"])


@router.post(
    "/projects/{project_uuid}/translation-jobs",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_a_translation_job(
    project_uuid: _uuid.UUID,
    req: TranslationStartRequest,
    session: DbSession,
    current: CurrentAccount,
) -> JobResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    try:
        job = await start_translation_job(
            session=session,
            project_uuid=project_uuid,
            segment_uuids=list(req.segment_uuids),
        )
    except TranslationJobUebersetzungsstartMissing as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return JobResponse.model_validate(job)


@router.get("/translation-jobs/{job_uuid}", response_model=JobResponse)
async def get_translation_job(
    job_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> JobResponse:
    job: Job | None = await session.get(Job, job_uuid)
    if job is None or job.job_type != JOB_TYPE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Translation job not found"
        )
    if job.project_uuid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Translation job not found"
        )
    project: Project | None = await session.get(Project, job.project_uuid)
    if project is None or project.account_uuid != current.account_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Translation job not found"
        )
    return JobResponse.model_validate(job)


def _build_translator_and_label() -> tuple[object, str]:
    """Build the canonical Primary + Check translator pair from env.

    Returns `(translator, engine_label)`. Raises HTTPException(503) if
    `OPENAI_API_KEY` is unset (Primary is mandatory). Falls back to
    Primary-only when GEMINI is unset — canon-compliant per §3.6 "no
    silent role swap": Check absence is recorded as cross_check=None on
    each TRANSLATION-PO, never as a Primary substitution.
    """
    try:
        primary = make_openai_translator()
    except OpenAITranslatorUnconfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    engine_label_primary = "openai/gpt-4o"
    try:
        check = make_gemini_translator()
        translator: object = make_cross_checked_translator(
            primary=primary,
            check=check,
            primary_engine_label=engine_label_primary,
            check_engine_label="google/gemini-2.5-pro",
        )
        return translator, f"{engine_label_primary}+google/gemini-2.5-pro"
    except GeminiTranslatorUnconfigured:
        return primary, engine_label_primary


async def _run_translation_in_background(job_uuid: _uuid.UUID) -> None:
    """BackgroundTask body. Opens its OWN DB session (the request session
    is closed by the time we run) and drives the translation loop with
    `commit_per_chunk=True` so progress + cancel-flag state stay visible
    to other sessions in real time.
    """
    translator, engine_label = _build_translator_and_label()
    hook = make_translation_persistence_hook(engine_identifier=engine_label)
    async with _sessionmaker()() as session:
        try:
            job = await session.get(Job, job_uuid)
            if job is None or job.job_type != JOB_TYPE:
                logger.warning(
                    "translation.background.job_missing", extra={"job_uuid": str(job_uuid)}
                )
                return
            await run_translation_job(
                session=session,
                job=job,
                translator=translator,  # type: ignore[arg-type]
                on_segment_translated=hook,
                commit_per_chunk=True,
            )
            await session.commit()
        except TranslationJobCancelled:
            # Already persisted as failed with phase=user_cancelled by
            # _execute. Swallow here — it's the user's own action, not
            # an unexpected error.
            logger.info("translation.background.cancelled", extra={"job_uuid": str(job_uuid)})
        except Exception:
            # _execute already wrote the failure. Log + swallow so the
            # BackgroundTasks runner doesn't surface to uvicorn as an
            # unhandled exception.
            logger.exception("translation.background.failed", extra={"job_uuid": str(job_uuid)})


@router.post(
    "/translation-jobs/{job_uuid}/run",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_a_translation_job(
    job_uuid: _uuid.UUID,
    background_tasks: BackgroundTasks,
    session: DbSession,
    current: CurrentAccount,
) -> JobResponse:
    """Launch a PENDING translation Job asynchronously.

    Validates ownership + state, builds the translator pair eagerly (so
    a misconfigured key surfaces as a synchronous 503), then schedules
    the loop in a BackgroundTask and returns the Job immediately. The
    UI polls `GET /translation-jobs/{u}` for `payload.chunks_translated`
    / `payload.chunks_total` and uses `/cancel` for cooperative abort.
    """
    job: Job | None = await session.get(Job, job_uuid)
    if job is None or job.job_type != JOB_TYPE or job.project_uuid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Translation job not found"
        )
    project: Project | None = await session.get(Project, job.project_uuid)
    if project is None or project.account_uuid != current.account_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Translation job not found"
        )
    if job.state != JobState.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Translation job is in state {job.state!r}; only PENDING jobs can be run.",
        )

    # Build translators eagerly so misconfiguration is a synchronous
    # 503 rather than a silent BackgroundTask failure the user only
    # learns about by polling.
    _build_translator_and_label()

    background_tasks.add_task(_run_translation_in_background, job_uuid)
    # Return the Job as-is (still PENDING from the caller's view; the
    # background task will transition it to RUNNING within a few ms of
    # the response landing). The frontend's poll loop will pick up the
    # RUNNING transition + progress on its first tick.
    return JobResponse.model_validate(job)


@router.post(
    "/translation-jobs/{job_uuid}/cancel",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
)
async def cancel_a_translation_job(
    job_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> JobResponse:
    """Request cooperative cancel of a translation Job.

    Sets `payload.cancel_requested = true`. The `_execute` loop checks
    this between chunks and aborts with `error.phase=user_cancelled`.
    Cancel is a no-op on terminal Jobs (already completed/failed); it
    returns the current Job state in that case.
    """
    job: Job | None = await session.get(Job, job_uuid)
    if job is None or job.job_type != JOB_TYPE or job.project_uuid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Translation job not found"
        )
    project: Project | None = await session.get(Project, job.project_uuid)
    if project is None or project.account_uuid != current.account_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Translation job not found"
        )
    if job.state in (JobState.COMPLETED.value, JobState.FAILED.value):
        return JobResponse.model_validate(job)
    job.payload = {**(job.payload or {}), "cancel_requested": True}
    await session.flush()
    return JobResponse.model_validate(job)
