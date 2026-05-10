"""T-9.1.1 + T-9.1.2 — Preflight evaluator service.

Per Sprint 4 §2:

- The evaluator is a Job (`job_type=preflight`) using the Sprint-0 state
  machine. Each preflight run is a fresh Job with its own UUID; that
  UUID is the `related_export_attempt_id` on the run's Decision Events
  (Pflichtfrage confirmations + W-Slot warning acceptances).
- Every preflight evaluation produces a Log-Eintrag (Exportlauf-
  Ereignis), regardless of outcome. Sprint 4 §A HG-implicit per the
  Exportlauf-Ereignis-Immer-Test.
- Slot discipline: the evaluator enumerates EXACTLY the five belegte
  slots (P-03, P-04, W-01, W-02, W-03) plus the Hadith group. Adding
  P-01/P-02/P-05/P-06/W-04..W-08 silently is a canon violation
  (HG-S4-3).

State machine:

    nicht_gestartet → laeuft → exportierbar
                              | exportierbar_mit_warnungen
                              | blockiert

Transition `blockiert → exportierbar*` is implicit on next evaluation
(re-running the evaluator on a fresh Job). Transition `laeuft →
exportierbar_mit_warnungen` requires per-warning-gate confirmation
(see `accept_warning_gate`).
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.decisions import create_decision_event
from waraq.eventing import log_event
from waraq.identity.service import new_uuid
from waraq.jobs import complete_job, fail_job, start_job
from waraq.preflight.enums import (
    BlockingReason,
    HadithKlasse,
    HadithStellenTyp,
    PreflightState,
    WarningSlot,
)
from waraq.preflight.exceptions import GuardNearBlocked, PflichthinweisCannotBeWarning
from waraq.preflight.guard_near import (
    FontResolver,
    GuardNearResult,
    RtlDetector,
    StyleTemplateDetector,
    run_guard_near_checks,
)
from waraq.preflight.hadith import derive_hadith_klasse
from waraq.preflight.konfiguration import PFLICHTFRAGE_COUNT
from waraq.schemas import (
    Befund,
    DecisionEvent,
    HadithPassageStatus,
    Job,
    KonsistenzBefund,
    OcrErrorInstance,
)
from waraq.schemas.enums import DecisionSource, JobState, ScopeType

JOB_TYPE = "preflight"


# --- result model --------------------------------------------------------


@dataclass(frozen=True, kw_only=True, slots=True)
class PreflightEvaluation:
    """Result of one preflight evaluation pass.

    Per Sprint 4 §A HG-S4-5 the Hadith findings are emitted as their
    own group (`hadith_h2_segment_uuids`, `hadith_h1_segment_uuids`),
    NEVER folded into a P- or W-Slot collection.
    """

    state: PreflightState
    blocking_reasons: list[BlockingReason] = field(default_factory=list)
    open_warning_slots: list[WarningSlot] = field(default_factory=list)

    # Sources (for the resolver UI / audit trail).
    p_03_kritisch_befund_uuids: list[_uuid.UUID] = field(default_factory=list)
    p_03_konsistenz_befund_uuids: list[_uuid.UUID] = field(default_factory=list)
    p_03_ocr_error_instance_uuids: list[_uuid.UUID] = field(default_factory=list)
    p_04_hoch_befund_uuids: list[_uuid.UUID] = field(default_factory=list)

    w_01_mittel_befund_uuids: list[_uuid.UUID] = field(default_factory=list)
    w_02_konsistenz_befund_uuids: list[_uuid.UUID] = field(default_factory=list)
    w_03_formatvorlagen_finding_keys: list[str] = field(default_factory=list)

    hadith_h2_status_uuids: list[_uuid.UUID] = field(default_factory=list)
    hadith_h1_status_uuids: list[_uuid.UUID] = field(default_factory=list)

    konfigurationsschicht_complete: bool = False
    pflichtfrage_active_count: int = 0


# --- the run lifecycle ---------------------------------------------------


async def start_preflight_run(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    rtl_detector: RtlDetector | None = None,
    style_template_detector: StyleTemplateDetector | None = None,
    font_resolver: FontResolver | None = None,
) -> Job:
    """Open a fresh preflight run as a Job (state=PENDING → RUNNING).

    Per §4.7.3, runs the guard-near pre-checks BEFORE creating the
    Job. If any of the four canonical guard-near rules (digit /
    RTL / style template / font) fires, raises `GuardNearBlocked` —
    the preflight dialog is not opened, no Job row created.

    Returns the Job on success. Its UUID is the
    `preflight_run_uuid` / `related_export_attempt_id` callers pass to
    `confirm_pflichtfrage` and `accept_warning_gate` for the rest of
    the run. The detector parameters mirror those on
    `run_guard_near_checks`.
    """
    guard_result = await run_guard_near_checks(
        session=session,
        project_uuid=project_uuid,
        rtl_detector=rtl_detector,
        style_template_detector=style_template_detector,
        font_resolver=font_resolver,
    )
    if not guard_result.passes:
        blockers = ", ".join(b.value for b in guard_result.blockers)
        raise GuardNearBlocked(
            f"Preflight dialog refused to open per §4.7.3 — guard-near "
            f"violations present: {blockers}",
            result=guard_result,
        )

    job = Job(
        job_uuid=new_uuid(),
        job_type=JOB_TYPE,
        state=JobState.PENDING.value,
        project_uuid=project_uuid,
    )
    session.add(job)
    await session.flush()
    await start_job(session=session, job=job)
    return job


async def evaluate_guard_near(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    rtl_detector: RtlDetector | None = None,
    style_template_detector: StyleTemplateDetector | None = None,
    font_resolver: FontResolver | None = None,
) -> GuardNearResult:
    """Run guard-near checks without attempting to open a run.

    The UI uses this to surface blockers preemptively — show the
    "preflight unavailable" panel and the resolution paths before
    the user tries to open the dialog.
    """
    return await run_guard_near_checks(
        session=session,
        project_uuid=project_uuid,
        rtl_detector=rtl_detector,
        style_template_detector=style_template_detector,
        font_resolver=font_resolver,
    )


async def evaluate_preflight(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    preflight_run: Job,
    formatvorlagen_graduelle_keys: Sequence[str] | None = None,
) -> PreflightEvaluation:
    """Run one preflight evaluation against current project state.

    Reads:
    - Befund (T-8.1.2) for P-03 (kritisch), P-04 (hoch), W-01 (mittel).
    - KonsistenzBefund (T-8.2.1) for P-03 (Kritisch-class) / W-02
      (default).
    - HadithPassageStatus for the Hadith group (H-2 → blockiert; H-1 →
      warning).
    - OcrErrorInstance for unresolved kritisch carry-forward (T-4.3.1
      → P-03).
    - DecisionEvents tied to `preflight_run.job_uuid` for the
      Konfigurationsschicht active-confirmation count.

    Writes:
    - The Exportlauf-Ereignis (Log-Eintrag) bookending the evaluation.

    The Sprint 4 §B "Calibration values: ... configurable, never pre-
    set" applies to the W-03 evaluator: callers pass the list of
    graduelle Formatvorlagen-Abweichungen detected by the upstream
    style-template engine; this evaluator just routes them.
    """
    # P-03 — kritische C-class Befund + simultaneous Kritisch Konsistenz
    # + unresolved kritische OCR-Fehlerklassen carry-forward.
    p_03_kritisch_befunde = await _select_open_befunde_by_severity(
        session=session, project_uuid=project_uuid, schweregrad="kritisch"
    )
    p_03_konsistenz_uuids, w_02_konsistenz_uuids = await _route_konsistenz(
        session=session, project_uuid=project_uuid
    )
    p_03_ocr_uuids = await _select_open_kritisch_ocr_errors(
        session=session, project_uuid=project_uuid
    )

    # P-04 — hoch A-/B-class Befund (Pflichthinweis).
    p_04_hoch_befunde = await _select_open_befunde_by_severity(
        session=session, project_uuid=project_uuid, schweregrad="hoch"
    )

    # W-01 — mittel D-class Befund. Quittierte rows are excluded
    # naturally because they are not `aufloesungsstatus=offen`.
    w_01_mittel_befunde = await _select_open_befunde_by_severity(
        session=session, project_uuid=project_uuid, schweregrad="mittel"
    )

    # Hadith group: H-2 blocks, H-1 warns; H-0 is silent.
    hadith_h2, hadith_h1 = await _route_hadith(session=session, project_uuid=project_uuid)

    # Konfigurationsschicht: count active confirmations for THIS run.
    pflichtfrage_active_count = await _count_active_pflichtfragen(
        session=session, project_uuid=project_uuid, preflight_run=preflight_run
    )
    konfig_complete = pflichtfrage_active_count >= PFLICHTFRAGE_COUNT

    # Build the result.
    blocking: list[BlockingReason] = []
    if p_03_kritisch_befunde or p_03_konsistenz_uuids or p_03_ocr_uuids:
        blocking.append(BlockingReason.P_03_KRITISCH)
    if p_04_hoch_befunde:
        blocking.append(BlockingReason.P_04_HOCH_PFLICHTHINWEIS)
    if hadith_h2:
        blocking.append(BlockingReason.HADITH_H2)
    if not konfig_complete:
        blocking.append(BlockingReason.KONFIGURATIONSSCHICHT_UNVOLLSTAENDIG)

    open_warnings: list[WarningSlot] = []
    if w_01_mittel_befunde:
        open_warnings.append(WarningSlot.W_01_MITTEL_AUDIT)
    if w_02_konsistenz_uuids:
        open_warnings.append(WarningSlot.W_02_KONSISTENZ)
    w_03_keys = list(formatvorlagen_graduelle_keys or [])
    if w_03_keys:
        open_warnings.append(WarningSlot.W_03_FORMATVORLAGEN_GRADUELL)
    if hadith_h1:
        open_warnings.append(WarningSlot.HADITH_H1)

    if blocking:
        state = PreflightState.BLOCKIERT
    elif open_warnings:
        # `exportierbar_mit_warnungen` requires per-gate confirmation;
        # without acceptances the state stays `blockiert`-style for
        # warning purposes. We flip to `exportierbar_mit_warnungen`
        # only when each open warning slot has been accepted via
        # `accept_warning_gate`.
        accepted_slots = await _accepted_warning_slots(session=session, preflight_run=preflight_run)
        unaccepted = [w for w in open_warnings if w not in accepted_slots]
        if unaccepted:
            # Treat as blockiert with a synthetic reason (warnings
            # require user attention before export). We keep this
            # distinct from the four BlockingReason codes — callers
            # check `open_warning_slots` to know what's pending.
            state = PreflightState.BLOCKIERT
        else:
            state = PreflightState.EXPORTIERBAR_MIT_WARNUNGEN
    else:
        state = PreflightState.EXPORTIERBAR

    evaluation = PreflightEvaluation(
        state=state,
        blocking_reasons=blocking,
        open_warning_slots=open_warnings,
        p_03_kritisch_befund_uuids=[b.befund_uuid for b in p_03_kritisch_befunde],
        p_03_konsistenz_befund_uuids=p_03_konsistenz_uuids,
        p_03_ocr_error_instance_uuids=p_03_ocr_uuids,
        p_04_hoch_befund_uuids=[b.befund_uuid for b in p_04_hoch_befunde],
        w_01_mittel_befund_uuids=[b.befund_uuid for b in w_01_mittel_befunde],
        w_02_konsistenz_befund_uuids=w_02_konsistenz_uuids,
        w_03_formatvorlagen_finding_keys=w_03_keys,
        hadith_h2_status_uuids=[r.hadith_status_uuid for r in hadith_h2],
        hadith_h1_status_uuids=[r.hadith_status_uuid for r in hadith_h1],
        konfigurationsschicht_complete=konfig_complete,
        pflichtfrage_active_count=pflichtfrage_active_count,
    )

    # Exportlauf-Ereignis — every evaluation, regardless of outcome.
    await log_event(
        session=session,
        operation_type="preflight_evaluation",
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        result={
            "preflight_run_uuid": str(preflight_run.job_uuid),
            "state": evaluation.state.value,
            "blocking_reasons": [r.value for r in evaluation.blocking_reasons],
            "open_warning_slots": [w.value for w in evaluation.open_warning_slots],
            "p_03_count": (
                len(evaluation.p_03_kritisch_befund_uuids)
                + len(evaluation.p_03_konsistenz_befund_uuids)
                + len(evaluation.p_03_ocr_error_instance_uuids)
            ),
            "p_04_count": len(evaluation.p_04_hoch_befund_uuids),
            "w_01_count": len(evaluation.w_01_mittel_befund_uuids),
            "w_02_count": len(evaluation.w_02_konsistenz_befund_uuids),
            "w_03_count": len(evaluation.w_03_formatvorlagen_finding_keys),
            "hadith_h2_count": len(evaluation.hadith_h2_status_uuids),
            "hadith_h1_count": len(evaluation.hadith_h1_status_uuids),
            "konfigurationsschicht_complete": evaluation.konfigurationsschicht_complete,
            "pflichtfrage_active_count": evaluation.pflichtfrage_active_count,
        },
    )

    return evaluation


async def complete_preflight_run(
    *,
    session: AsyncSession,
    preflight_run: Job,
    evaluation: PreflightEvaluation,
) -> None:
    """Close the preflight Job with a result summary."""
    if evaluation.state == PreflightState.BLOCKIERT:
        # The run completed; we do not mark Job FAILED for blockiert —
        # that's a successful evaluation that produced a "blocked"
        # outcome. The Job is COMPLETED with a state field describing
        # the outcome.
        pass
    await complete_job(
        session=session,
        job=preflight_run,
        result={
            "state": evaluation.state.value,
            "blocking_reasons": [r.value for r in evaluation.blocking_reasons],
            "open_warning_slots": [w.value for w in evaluation.open_warning_slots],
        },
    )


async def fail_preflight_run(
    *,
    session: AsyncSession,
    preflight_run: Job,
    error: dict[str, Any],
) -> None:
    await fail_job(session=session, job=preflight_run, error=error)


# --- accept warning gate (per-gate confirmation) -------------------------


async def accept_warning_gate(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    preflight_run: Job,
    warning_slot: WarningSlot,
    actor_uuid: _uuid.UUID | None = None,
    content: dict[str, Any] | None = None,
) -> DecisionEvent:
    """Accept one warning gate for the current preflight run.

    Per Sprint 4 §2: each per-warning confirmation is its own Decision
    Event. A bulk "accept all warnings" UX must produce N distinct
    Decision Events for N warning gates.

    Refuses W-04..W-08 (those slots are open per Dokument 2 §2.5).
    Refuses any attempt to accept P-04 — Pflichthinweis cannot be
    routed into a W-class to allow export (Sprint 4 §A HG-S4-4 /
    R-S4-05).
    """
    # Defensive: WarningSlot is the canonical surface; calling code that
    # tries to reach P-04 via a "warning" path is the failure mode.
    # Refuse early via type system (StrEnum membership is structural).

    de_content: dict[str, Any] = {
        "warning_slot": warning_slot.value,
        "preflight_run_uuid": str(preflight_run.job_uuid),
        "action": "go_with_warning",
    }
    if content:
        de_content.update(content)

    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        decision_type=f"preflight_warning_accepted_{warning_slot.value}",
        decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        actor_uuid=actor_uuid,
        content=de_content,
        related_export_attempt_id=str(preflight_run.job_uuid),
    )
    return de


def assert_pflichthinweis_not_routed_as_warning(slot: str) -> None:
    """Refuse any code path that maps a P-04 finding into a W-Slot.

    Per Sprint 4 §A HG-S4-4 / R-S4-05: P-04 must remain blockierend.
    The structural separation is enforced by the WarningSlot enum
    (no `W_P04_*` value), but call this guard at any seam where a
    string slot identifier crosses module boundaries.
    """
    if slot.startswith("p_04") or slot == "p_04_hoch_pflichthinweis":
        raise PflichthinweisCannotBeWarning(
            f"slot {slot!r} is a Pflichthinweis (P-04). Routing it into "
            "a W-Slot to permit export is forbidden per Sprint 4 R-S4-05 "
            "/ Dokument 2 §2.4."
        )


# --- helpers (selectors) -------------------------------------------------


async def _select_open_befunde_by_severity(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    schweregrad: str,
) -> list[Befund]:
    result = await session.execute(
        select(Befund)
        .where(Befund.project_uuid == project_uuid)
        .where(Befund.schweregrad == schweregrad)
        .where(Befund.aufloesungsstatus == "offen")
    )
    return list(result.scalars())


async def _route_konsistenz(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> tuple[list[_uuid.UUID], list[_uuid.UUID]]:
    """Per Sprint 4 §2: a Konsistenz-Befund routes to W-02 by default;
    if it simultaneously violates a Kritisch-Klasse per §4.6, it routes
    to P-03 instead. Routing is computed at preflight evaluation, NOT
    stored on the Konsistenz-Befund row.

    Returns (p_03_uuids, w_02_uuids).
    """
    result = await session.execute(
        select(KonsistenzBefund)
        .where(KonsistenzBefund.project_uuid == project_uuid)
        .where(KonsistenzBefund.aufloesungsstatus == "offen")
    )
    p_03: list[_uuid.UUID] = []
    w_02: list[_uuid.UUID] = []
    for row in result.scalars():
        if row.verstossklasse == "kritisch":
            p_03.append(row.konsistenz_befund_uuid)
        else:
            w_02.append(row.konsistenz_befund_uuid)
    return p_03, w_02


async def _select_open_kritisch_ocr_errors(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> list[_uuid.UUID]:
    """Carry-forward from T-4.3.1 — unresolved kritisch OCR-Fehlerklassen.

    Reads `ocr_error_instances` joined to pages for project filtering.
    Severity for each F-XX is computed at read time from the configurable
    `SeverityWeights` map (R-S1-04 — never persisted on the row).
    """
    from waraq.ocr.review import make_default_severity_weights
    from waraq.schemas import Page
    from waraq.schemas.enums import OcrSeverity

    weights = make_default_severity_weights()

    result = await session.execute(
        select(OcrErrorInstance)
        .join(Page, Page.page_uuid == OcrErrorInstance.page_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(OcrErrorInstance.state == "offen")
    )
    out: list[_uuid.UUID] = []
    for row in result.scalars():
        # error_code is stored as the F-XX wire form (e.g., "F-01").
        try:
            from waraq.ocr.error_classes import OcrErrorClass

            cls = OcrErrorClass(row.error_code)
        except ValueError:
            continue
        if weights.weights.get(cls) == OcrSeverity.KRITISCH:
            out.append(row.ocr_error_instance_uuid)
    return out


async def _route_hadith(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> tuple[list[HadithPassageStatus], list[HadithPassageStatus]]:
    """Per Sprint 4 §2 + §4.16.4. H-2 → block; H-1 → warn; H-0 → silent.

    Returns (h_2_rows, h_1_rows). Only `state=offen` rows contribute.
    """
    result = await session.execute(
        select(HadithPassageStatus)
        .where(HadithPassageStatus.project_uuid == project_uuid)
        .where(HadithPassageStatus.state == "offen")
    )
    h_2: list[HadithPassageStatus] = []
    h_1: list[HadithPassageStatus] = []
    for row in result.scalars():
        try:
            stellen_typ = HadithStellenTyp(row.hadith_stellen_typ)
        except ValueError:
            continue
        klasse = derive_hadith_klasse(stellen_typ)
        if klasse == HadithKlasse.H_2:
            h_2.append(row)
        elif klasse == HadithKlasse.H_1:
            h_1.append(row)
        # H-0 deliberately silent.
    return h_2, h_1


async def _count_active_pflichtfragen(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    preflight_run: Job,
) -> int:
    """Count distinct frage_indexes confirmed for this run.

    The active-confirmation discipline (Sprint 4 §2) demands an
    `decision_source=preflight_confirmation` Decision Event tagged
    with `related_export_attempt_id=<preflight_run_uuid>` for each of
    the four Pflichtfragen. Saved Export-Profil rows in
    `pflichtfrage_profile` are NOT counted.
    """
    result = await session.execute(
        select(DecisionEvent)
        .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
        .where(DecisionEvent.scope_uuid == project_uuid)
        .where(DecisionEvent.decision_source == DecisionSource.PREFLIGHT_CONFIRMATION.value)
        .where(DecisionEvent.decision_type == "pflichtfrage_bestaetigung")
        .where(DecisionEvent.related_export_attempt_id == str(preflight_run.job_uuid))
    )
    seen_indexes: set[int] = set()
    for de in result.scalars():
        idx = (de.content or {}).get("frage_index")
        if isinstance(idx, int):
            seen_indexes.add(idx)
    return len(seen_indexes)


async def _accepted_warning_slots(
    *,
    session: AsyncSession,
    preflight_run: Job,
) -> set[WarningSlot]:
    """Read which warning slots have been actively accepted for this run."""
    result = await session.execute(
        select(DecisionEvent)
        .where(DecisionEvent.decision_source == DecisionSource.PREFLIGHT_CONFIRMATION.value)
        .where(DecisionEvent.related_export_attempt_id == str(preflight_run.job_uuid))
    )
    accepted: set[WarningSlot] = set()
    for de in result.scalars():
        slot_str = (de.content or {}).get("warning_slot")
        if not isinstance(slot_str, str):
            continue
        try:
            accepted.add(WarningSlot(slot_str))
        except ValueError:
            continue
    return accepted


__all__ = [
    "JOB_TYPE",
    "PreflightEvaluation",
    "accept_warning_gate",
    "assert_pflichthinweis_not_routed_as_warning",
    "complete_preflight_run",
    "evaluate_guard_near",
    "evaluate_preflight",
    "fail_preflight_run",
    "start_preflight_run",
]
