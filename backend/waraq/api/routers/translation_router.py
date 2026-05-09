"""Translation endpoints — start a translation Job, run it, poll its state.

The `/run` endpoint executes `run_translation_job` synchronously in HTTP
request scope using the OpenAI translator built from environment
variables. No worker / queue. Mirrors the OCR-pipeline pattern (also
synchronous in request scope per current DEPLOY.md note).
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, HTTPException, status

from waraq.api._ownership import owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import JobResponse, TranslationStartRequest
from waraq.schemas import Job, Project
from waraq.schemas.enums import JobState
from waraq.translation import (
    JOB_TYPE,
    TranslationJobUebersetzungsstartMissing,
    make_translation_persistence_hook,
    run_translation_job,
    start_translation_job,
)
from waraq.translation.openai_translator import (
    OpenAITranslatorUnconfigured,
    make_openai_translator,
)

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


@router.post(
    "/translation-jobs/{job_uuid}/run",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
)
async def run_a_translation_job(
    job_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> JobResponse:
    """Execute a PENDING translation Job synchronously in request scope.

    Reads the OpenAI translator from env (`OPENAI_API_KEY`,
    `OPENAI_TRANSLATION_MODEL`). Wires the canonical persistence hook so
    every translated segment writes its Revision + TRANSLATION-PO via
    PROVENANCE-Kern.

    Returns the COMPLETED Job. The caller can `GET /translation-jobs/{u}`
    to inspect `result` for chunk counts.
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
    try:
        translator = make_openai_translator()
    except OpenAITranslatorUnconfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    hook = make_translation_persistence_hook(engine_identifier="openai/gpt-4o-mini")
    await run_translation_job(
        session=session,
        job=job,
        translator=translator,
        on_segment_translated=hook,
    )
    await session.refresh(job)
    return JobResponse.model_validate(job)
