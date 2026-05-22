"""M5 closeout + Phase 3 sub-batch A — Preflight HTTP endpoints.

Wraps `waraq.preflight` so the M4 UI can drive the four canonical
Pflichtfragen + final evaluation entirely through HTTP.

Flow expected by the UI:
0. GET  /preflight/pflichtfragen/definitions                   — canonical 4 questions
1. GET  /projects/{uuid}/preflight/guard-near                  — §4.7.3 pre-checks
2. POST /projects/{uuid}/preflight/runs                        — open run (refused on guard-near block)
3. POST /projects/{uuid}/preflight/runs/{run_uuid}/pflichtfragen
   (×4, one per frage_index 1..4)
4. POST /projects/{uuid}/preflight/runs/{run_uuid}/pdf-format  — §4.7.2 Digital | Print
5. POST /projects/{uuid}/preflight/runs/{run_uuid}/evaluate    — final state

The router is read-only with respect to project state; all writes
happen through the service layer (Decision Events, Log-Einträge,
Job state transitions per the canonical service implementation).
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from waraq.api._ownership import owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.notifications.events import (
    notify_project_event,
    project_audit_url,
    project_workspace_url,
)
from waraq.preflight import (
    PFLICHTFRAGE_COUNT,
    PFLICHTFRAGEN,
    GuardNearBlocked,
    GuardNearViolation,
    PdfFormatChoice,
    PreflightError,
    WarningSlot,
    accept_warning_gate,
    confirm_pdf_format_choice,
    confirm_pflichtfrage,
    evaluate_guard_near,
    evaluate_preflight,
    read_pdf_format_choice,
    start_preflight_run,
)
from waraq.preflight.service import JOB_TYPE as PREFLIGHT_JOB_TYPE
from waraq.schemas import Job

router = APIRouter(tags=["preflight"])


TESTER_BLOCKING_GUARD_NEAR: set[GuardNearViolation] = {
    GuardNearViolation.CRITICAL_RTL,
    GuardNearViolation.STYLE_TEMPLATE_INTEGRITY,
}


class PreflightRunResponse(BaseModel):
    run_uuid: _uuid.UUID
    state: str


class PflichtfrageConfirmRequest(BaseModel):
    frage_index: int = Field(ge=1, le=PFLICHTFRAGE_COUNT)
    frage_key: str = Field(min_length=1, max_length=128)
    answer: dict[str, Any] = Field(default_factory=dict)


class PflichtfrageConfirmResponse(BaseModel):
    decision_event_uuid: _uuid.UUID
    frage_index: int


class PreflightEvaluateResponse(BaseModel):
    run_uuid: _uuid.UUID
    state: str
    blocking_reasons: list[str]
    open_warning_slots: list[str]
    konfigurationsschicht_complete: bool
    pflichtfrage_active_count: int
    p_03_kritisch_befund_uuids: list[_uuid.UUID]
    p_04_hoch_befund_uuids: list[_uuid.UUID]
    w_01_mittel_befund_uuids: list[_uuid.UUID]
    w_02_konsistenz_befund_uuids: list[_uuid.UUID]
    w_03_formatvorlagen_finding_keys: list[str]
    hadith_h2_status_uuids: list[_uuid.UUID]
    hadith_h1_status_uuids: list[_uuid.UUID]


class WarningAcceptRequest(BaseModel):
    warning_slot: WarningSlot


class WarningAcceptResponse(BaseModel):
    decision_event_uuid: _uuid.UUID
    warning_slot: WarningSlot


async def _resolve_run_or_404(
    *, session: DbSession, project_uuid: _uuid.UUID, run_uuid: _uuid.UUID
) -> Job:
    job: Job | None = await session.get(Job, run_uuid)
    if job is None or job.job_type != PREFLIGHT_JOB_TYPE or job.project_uuid != project_uuid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preflight run not found")
    return job


# --- §4.7.2 Pflichtfragen definitions endpoint -------------------------------


class PflichtfrageDefinitionDto(BaseModel):
    frage_index: int
    frage_key: str
    prompt_de: str
    prompt_en: str
    answer_schema: dict[str, Any]


class PflichtfragenDefinitionsResponse(BaseModel):
    pflichtfragen: list[PflichtfrageDefinitionDto]


@router.get(
    "/preflight/pflichtfragen/definitions",
    response_model=PflichtfragenDefinitionsResponse,
)
async def list_pflichtfrage_definitions() -> PflichtfragenDefinitionsResponse:
    """Return the canonical 4 §4.7.2 Pflichtfragen with JSON-schema answers.

    UI clients consume this to render the dialog without hardcoding
    keys / prompts. Public (no auth) — definitions are not project-scoped.
    """
    return PflichtfragenDefinitionsResponse(
        pflichtfragen=[
            PflichtfrageDefinitionDto(
                frage_index=spec.frage_index,
                frage_key=spec.frage_key,
                prompt_de=spec.prompt_de,
                prompt_en=spec.prompt_en,
                answer_schema=spec.schema.model_json_schema(),
            )
            for spec in PFLICHTFRAGEN
        ]
    )


# --- §4.7.3 Guard-near pre-check preview --------------------------------------


class GuardNearResponse(BaseModel):
    passes: bool
    blockers: list[str]
    advisories: list[str] = Field(default_factory=list)
    evidence: dict[str, list[str]]


@router.get(
    "/projects/{project_uuid}/preflight/guard-near",
    response_model=GuardNearResponse,
)
async def get_guard_near_state(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> GuardNearResponse:
    """Run the §4.7.3 guard-near pre-checks without opening a run.

    The UI uses this to show the "preflight unavailable" panel + the
    canonical resolution paths before the user attempts to open the
    preflight dialog. Same logic as the gate that runs inside
    `start_preflight_run`.
    """
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    result = await evaluate_guard_near(
        session=session,
        project_uuid=project_uuid,
        blocking_guard_near_violations=TESTER_BLOCKING_GUARD_NEAR,
    )
    return GuardNearResponse(
        passes=result.passes,
        blockers=[b.value for b in result.blockers],
        advisories=[a.value for a in result.advisories],
        evidence=result.evidence,
    )


@router.post(
    "/projects/{project_uuid}/preflight/runs",
    response_model=PreflightRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def open_preflight_run(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> PreflightRunResponse:
    project = await owned_project_or_404(session, project_uuid, current.account_uuid)
    try:
        job = await start_preflight_run(
            session=session,
            project_uuid=project_uuid,
            blocking_guard_near_violations=TESTER_BLOCKING_GUARD_NEAR,
        )
    except GuardNearBlocked as exc:
        # Per §4.7.3 — preflight dialog refused; surface the blockers
        # so the UI can render the resolution panel directly. 409 is
        # the canonical "request can't proceed in current state" code.
        guard_result = exc.result
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "reason": "guard_near_blocked",
                "blockers": [b.value for b in guard_result.blockers],
                "advisories": [a.value for a in guard_result.advisories],
                "evidence": guard_result.evidence,
            },
        ) from exc
    await notify_project_event(
        session=session,
        project=project,
        kind="preflight_started",
        severity="info",
        title=f"Preflight started — {project.name}",
        body="Export readiness checks have started.",
        target_url=project_workspace_url(project.project_uuid),
        action_label="Open project",
    )
    return PreflightRunResponse(run_uuid=job.job_uuid, state=job.state)


@router.post(
    "/projects/{project_uuid}/preflight/runs/{run_uuid}/pflichtfragen",
    response_model=PflichtfrageConfirmResponse,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_one_pflichtfrage(
    project_uuid: _uuid.UUID,
    run_uuid: _uuid.UUID,
    req: PflichtfrageConfirmRequest,
    session: DbSession,
    current: CurrentAccount,
) -> PflichtfrageConfirmResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    await _resolve_run_or_404(session=session, project_uuid=project_uuid, run_uuid=run_uuid)
    try:
        de = await confirm_pflichtfrage(
            session=session,
            project_uuid=project_uuid,
            preflight_run_uuid=run_uuid,
            frage_index=req.frage_index,
            frage_key=req.frage_key,
            answer=req.answer,
            actor_uuid=current.account_uuid,
        )
    except PreflightError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PflichtfrageConfirmResponse(
        decision_event_uuid=de.decision_event_uuid, frage_index=req.frage_index
    )


# --- §4.7.2 PDF format choice (Configuration Layer, separate from the 4 Pflichtfragen) ---


class PdfFormatChoiceRequest(BaseModel):
    choice: PdfFormatChoice


class PdfFormatChoiceResponse(BaseModel):
    decision_event_uuid: _uuid.UUID
    choice: PdfFormatChoice


class PdfFormatChoiceReadResponse(BaseModel):
    choice: PdfFormatChoice | None


@router.post(
    "/projects/{project_uuid}/preflight/runs/{run_uuid}/pdf-format",
    response_model=PdfFormatChoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_pdf_format(
    project_uuid: _uuid.UUID,
    run_uuid: _uuid.UUID,
    req: PdfFormatChoiceRequest,
    session: DbSession,
    current: CurrentAccount,
) -> PdfFormatChoiceResponse:
    """Active confirmation of the §4.7.2 PDF format choice for the run."""
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    await _resolve_run_or_404(session=session, project_uuid=project_uuid, run_uuid=run_uuid)
    de = await confirm_pdf_format_choice(
        session=session,
        project_uuid=project_uuid,
        preflight_run_uuid=run_uuid,
        choice=req.choice,
        actor_uuid=current.account_uuid,
    )
    return PdfFormatChoiceResponse(decision_event_uuid=de.decision_event_uuid, choice=req.choice)


@router.get(
    "/projects/{project_uuid}/preflight/runs/{run_uuid}/pdf-format",
    response_model=PdfFormatChoiceReadResponse,
)
async def get_pdf_format(
    project_uuid: _uuid.UUID,
    run_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> PdfFormatChoiceReadResponse:
    """Read the latest active PDF format choice for the run, or None."""
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    await _resolve_run_or_404(session=session, project_uuid=project_uuid, run_uuid=run_uuid)
    choice = await read_pdf_format_choice(
        session=session, project_uuid=project_uuid, preflight_run_uuid=run_uuid
    )
    return PdfFormatChoiceReadResponse(choice=choice)


@router.post(
    "/projects/{project_uuid}/preflight/runs/{run_uuid}/warnings",
    response_model=WarningAcceptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def accept_preflight_warning(
    project_uuid: _uuid.UUID,
    run_uuid: _uuid.UUID,
    req: WarningAcceptRequest,
    session: DbSession,
    current: CurrentAccount,
) -> WarningAcceptResponse:
    """Accept one warning slot for this readiness run and allow re-evaluation."""
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    job = await _resolve_run_or_404(session=session, project_uuid=project_uuid, run_uuid=run_uuid)
    try:
        de = await accept_warning_gate(
            session=session,
            project_uuid=project_uuid,
            preflight_run=job,
            warning_slot=req.warning_slot,
            actor_uuid=current.account_uuid,
        )
    except PreflightError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WarningAcceptResponse(
        decision_event_uuid=de.decision_event_uuid,
        warning_slot=req.warning_slot,
    )


@router.post(
    "/projects/{project_uuid}/preflight/runs/{run_uuid}/evaluate",
    response_model=PreflightEvaluateResponse,
)
async def evaluate_preflight_run(
    project_uuid: _uuid.UUID,
    run_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> PreflightEvaluateResponse:
    project = await owned_project_or_404(session, project_uuid, current.account_uuid)
    job = await _resolve_run_or_404(session=session, project_uuid=project_uuid, run_uuid=run_uuid)
    evaluation = await evaluate_preflight(
        session=session, project_uuid=project_uuid, preflight_run=job
    )
    blocker_count = len(evaluation.blocking_reasons)
    warning_count = len(evaluation.open_warning_slots)
    severity = "success" if blocker_count == 0 and warning_count == 0 else "action_required"
    await notify_project_event(
        session=session,
        project=project,
        kind="preflight_evaluated",
        severity=severity,
        title=f"Preflight {evaluation.state.value} — {project.name}",
        body=(
            f"{blocker_count} blocker(s), {warning_count} warning slot(s). "
            "Open Audit if anything needs resolution."
        ),
        target_url=project_audit_url(project.project_uuid) if blocker_count else project_workspace_url(project.project_uuid),
        action_label="Open Audit" if blocker_count else "Open project",
    )
    return PreflightEvaluateResponse(
        run_uuid=run_uuid,
        state=evaluation.state.value,
        blocking_reasons=[r.value for r in evaluation.blocking_reasons],
        open_warning_slots=[s.value for s in evaluation.open_warning_slots],
        konfigurationsschicht_complete=evaluation.konfigurationsschicht_complete,
        pflichtfrage_active_count=evaluation.pflichtfrage_active_count,
        p_03_kritisch_befund_uuids=list(evaluation.p_03_kritisch_befund_uuids),
        p_04_hoch_befund_uuids=list(evaluation.p_04_hoch_befund_uuids),
        w_01_mittel_befund_uuids=list(evaluation.w_01_mittel_befund_uuids),
        w_02_konsistenz_befund_uuids=list(evaluation.w_02_konsistenz_befund_uuids),
        w_03_formatvorlagen_finding_keys=list(evaluation.w_03_formatvorlagen_finding_keys),
        hadith_h2_status_uuids=list(evaluation.hadith_h2_status_uuids),
        hadith_h1_status_uuids=list(evaluation.hadith_h1_status_uuids),
    )
