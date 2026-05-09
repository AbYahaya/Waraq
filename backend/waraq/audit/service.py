"""T-8.1.1 — AUDIT service: record/resolve/quittiere + audit-run.

Per Sprint 3 §2 + §A Hard Gates:

- Befund detection writes nothing to Revision, Segment, or
  TRANSLATION-PO (Audit-Kein-Auto-Korrektur-Test, T-H4-02).
- Audit-run uses the Sprint-0 Job state machine (job_type='audit'); the
  Job records start, end, finding count by severity in `result`.
- Each audit-run produces a Log-Eintrag via EVENTING with the same
  per-severity count summary (Audit-Run-Log-Eintrag-Test).
- Befund detection fields are immutable post-creation. Only resolution
  fields may be updated, and only on offen → aufgelöst | quittiert.
- Quittierung is permitted only for `mittel`-severity (Audit-Quittierung-
  Nur-Mittel-Test). `kritisch` and `hoch` must use the resolution path.
- Resolution / quittierung both require a Decision Event with
  `decision_source = audit_resolution`. No auto-quittierung surface
  exists (Audit-Kein-Auto-Quittierung-Test).
- Audit findings do NOT stop the translation flow. Detection is
  passive; the gate (Sprint 4/5) is the consumer (Audit-Findings-
  Stoppen-Translation-Flow-Nicht-Test).

The check functions live in `rules.py`; this service orchestrates the
run + persists the findings.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.audit.enums import AufloesungsStatus, Schweregrad
from waraq.audit.exceptions import (
    BefundAlreadyResolved,
    BefundDetectionImmutable,
    BefundNotResolvable,
)
from waraq.audit.severity import SeverityTable, default_severity_table
from waraq.decisions import create_decision_event
from waraq.eventing import log_event
from waraq.identity.service import new_uuid
from waraq.jobs import complete_job, fail_job, start_job
from waraq.schemas import Befund, Block, DecisionEvent, Job, Page, Segment
from waraq.schemas.enums import DecisionSource, JobState, ScopeType

JOB_TYPE = "audit"


# --- finding shape (rule check return value) -------------------------


@dataclass(frozen=True, kw_only=True, slots=True)
class RuleFinding:
    """Single hit produced by a rule check function. Severity /
    verstossklasse are NOT carried here — they're looked up at persist
    time from the configurable SeverityTable."""

    regelkennung: str
    satz_uuid: _uuid.UUID
    detection_context: dict[str, Any]


# Type alias for rule check signature. Pure-by-design: takes a Segment
# (and the audit run's project context), returns a list of findings. No
# DB writes, no exceptions for "no finding".
RuleCheck = Callable[[Segment], list[RuleFinding]]


# --- record_befund ---------------------------------------------------


async def record_befund(
    *,
    session: AsyncSession,
    finding: RuleFinding,
    project_uuid: _uuid.UUID,
    audit_run_job_uuid: _uuid.UUID,
    severity_table: SeverityTable,
) -> Befund:
    """Persist one finding as an `audit_befunde` row.

    Reads severity / verstossklasse from `severity_table`; refuses if the
    regelkennung isn't registered. Does NOT write a Decision Event.
    Findings on detection do not produce DEs — DEs land at resolution
    time only (T-H4-02 / Audit-Aufloesung-Decision-Event-Test).
    """
    entry = severity_table.get(finding.regelkennung)
    befund = Befund(
        befund_uuid=new_uuid(),
        satz_uuid=finding.satz_uuid,
        project_uuid=project_uuid,
        audit_run_job_uuid=audit_run_job_uuid,
        regelkennung=finding.regelkennung,
        verstossklasse=entry.verstossklasse.value,
        schweregrad=entry.schweregrad.value,
        detection_context=dict(finding.detection_context),
        aufloesungsstatus=AufloesungsStatus.OFFEN.value,
    )
    session.add(befund)
    await session.flush()
    return befund


# --- resolve / quittiere -------------------------------------------


_DETECTION_FIELDS = ("regelkennung", "verstossklasse", "schweregrad", "detected_at")


def _ensure_offen(befund: Befund) -> None:
    if befund.aufloesungsstatus != AufloesungsStatus.OFFEN.value:
        raise BefundAlreadyResolved(
            f"Befund {befund.befund_uuid} is already {befund.aufloesungsstatus}; "
            "resolution is a one-shot transition."
        )


def _refuse_detection_mutation(befund: Befund, **proposed: Any) -> None:
    """Service-layer guard that rejects updates to immutable detection
    fields. (Audit-Befund-Immutable-Detection-Test.)"""
    for field in _DETECTION_FIELDS:
        if field in proposed:
            raise BefundDetectionImmutable(
                f"detection field {field!r} is immutable on a created Befund"
            )


async def resolve_befund(
    *,
    session: AsyncSession,
    befund: Befund,
    actor_uuid: _uuid.UUID | None = None,
    annotation: str | None = None,
    extra_content: dict[str, Any] | None = None,
) -> DecisionEvent:
    """Transition `offen → aufgeloest`.

    Writes a Decision Event with `scope_type=segment`, `decision_source=
    audit_resolution`, `decision_type=audit_befund_aufgeloest`, then
    stamps the Befund's resolution triple. Permitted for ALL severities
    (kritisch / hoch / mittel).
    """
    _ensure_offen(befund)
    content: dict[str, Any] = {
        "befund_uuid": str(befund.befund_uuid),
        "regelkennung": befund.regelkennung,
        "verstossklasse": befund.verstossklasse,
        "schweregrad": befund.schweregrad,
        "annotation": annotation,
    }
    if extra_content:
        content.update(extra_content)
    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=befund.satz_uuid,
        decision_type="audit_befund_aufgeloest",
        decision_source=DecisionSource.AUDIT_RESOLUTION,
        actor_uuid=actor_uuid,
        content=content,
    )
    befund.aufloesungsstatus = AufloesungsStatus.AUFGELOEST.value
    befund.resolved_at = datetime.now(UTC)
    befund.resolution_decision_event_uuid = de.decision_event_uuid
    await session.flush()
    return de


async def quittiere_befund(
    *,
    session: AsyncSession,
    befund: Befund,
    actor_uuid: _uuid.UUID | None = None,
    annotation: str | None = None,
    extra_content: dict[str, Any] | None = None,
) -> DecisionEvent:
    """Transition `offen → quittiert` (acknowledged without change).

    Permitted ONLY for `mittel`-severity findings. Refuses on `kritisch`
    or `hoch` (Audit-Quittierung-Nur-Mittel-Test). Writes a Decision
    Event with `decision_type=audit_befund_quittiert`,
    `decision_source=audit_resolution`.
    """
    _ensure_offen(befund)
    if befund.schweregrad != Schweregrad.MITTEL.value:
        raise BefundNotResolvable(
            f"Quittierung is permitted only for schweregrad=mittel; "
            f"this Befund has schweregrad={befund.schweregrad}. Use "
            "resolve_befund instead."
        )
    content: dict[str, Any] = {
        "befund_uuid": str(befund.befund_uuid),
        "regelkennung": befund.regelkennung,
        "verstossklasse": befund.verstossklasse,
        "schweregrad": befund.schweregrad,
        "annotation": annotation,
    }
    if extra_content:
        content.update(extra_content)
    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=befund.satz_uuid,
        decision_type="audit_befund_quittiert",
        decision_source=DecisionSource.AUDIT_RESOLUTION,
        actor_uuid=actor_uuid,
        content=content,
    )
    befund.aufloesungsstatus = AufloesungsStatus.QUITTIERT.value
    befund.resolved_at = datetime.now(UTC)
    befund.resolution_decision_event_uuid = de.decision_event_uuid
    await session.flush()
    return de


# --- audit-run -------------------------------------------------------


async def _segments_in_project(session: AsyncSession, *, project_uuid: _uuid.UUID) -> list[Segment]:
    """All active Segments under the project, ordered by page/block/satz
    index. Used by the audit-run iterator."""
    result = await session.execute(
        select(Segment)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(Segment.active.is_(True))
        .order_by(Page.page_index.asc(), Block.block_index.asc(), Segment.satz_index.asc())
    )
    return list(result.scalars())


@dataclass(frozen=True, kw_only=True, slots=True)
class AuditRunResult:
    job: Job
    befund_count: int
    by_severity: dict[str, int]


async def run_audit_for_project(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    rules: Iterable[RuleCheck],
    severity_table: SeverityTable | None = None,
) -> AuditRunResult:
    """Execute one audit-run over a project's segments.

    Steps:
      1. Create a Job (job_type='audit') in PENDING.
      2. Transition to RUNNING via start_job.
      3. For each segment, invoke each rule check; for each finding,
         persist a Befund.
      4. Bookend the run with a Log-Eintrag carrying the run summary
         (Audit-Run-Log-Eintrag-Test).
      5. Complete the Job with the same summary on result.

    Raises only if `start_job` / DB operations fail. Rule check functions
    must not raise — if a rule body fails, the run is marked
    fehlgeschlagen via fail_job and re-raised. The Sprint-0 state machine
    handles deferred / fehlgeschlagen retry semantics
    (Audit-Job-State-Machine-Test).
    """
    table = severity_table if severity_table is not None else default_severity_table()
    rules_list = list(rules)

    job = Job(
        job_uuid=new_uuid(),
        job_type=JOB_TYPE,
        state=JobState.PENDING.value,
        project_uuid=project_uuid,
        payload={
            "regelkennungen": sorted({_unique_regelkennung(r) for r in rules_list}),
        },
    )
    session.add(job)
    await session.flush()
    await start_job(session=session, job=job)

    by_severity: dict[str, int] = {
        Schweregrad.KRITISCH.value: 0,
        Schweregrad.HOCH.value: 0,
        Schweregrad.MITTEL.value: 0,
    }
    befund_count = 0

    try:
        segments = await _segments_in_project(session, project_uuid=project_uuid)
        for segment in segments:
            for rule in rules_list:
                findings = rule(segment)
                for finding in findings:
                    befund = await record_befund(
                        session=session,
                        finding=finding,
                        project_uuid=project_uuid,
                        audit_run_job_uuid=job.job_uuid,
                        severity_table=table,
                    )
                    by_severity[befund.schweregrad] = by_severity.get(befund.schweregrad, 0) + 1
                    befund_count += 1
    except Exception as exc:
        await fail_job(
            session=session,
            job=job,
            error={
                "phase": "rule_evaluation",
                "error_class": type(exc).__name__,
                "repr": repr(exc),
            },
        )
        await log_event(
            session=session,
            operation_type="audit_run_failed",
            scope_type=ScopeType.PROJECT,
            scope_uuid=project_uuid,
            result={
                "job_uuid": str(job.job_uuid),
                "befund_count_so_far": befund_count,
                "by_severity_so_far": dict(by_severity),
            },
        )
        raise

    summary = {
        "befund_count": befund_count,
        "by_severity": dict(by_severity),
    }
    await complete_job(session=session, job=job, result=summary)
    await log_event(
        session=session,
        operation_type="audit_run_completed",
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        result={"job_uuid": str(job.job_uuid), **summary},
    )
    return AuditRunResult(job=job, befund_count=befund_count, by_severity=dict(by_severity))


def _unique_regelkennung(rule: RuleCheck) -> str:
    """Helper used by the run summary to enumerate which rules ran. Each
    rule function exposes its regelkennung via a `regelkennung` attr —
    set by the `register_rule` decorator in rules.py."""
    rk = getattr(rule, "regelkennung", None)
    if isinstance(rk, str):
        return rk
    return rule.__name__


# Re-export the immutable-detection guard for tests / external callers
# that perform direct ORM updates and want to enforce the rule.
def assert_detection_immutable(befund: Befund, **proposed: Any) -> None:
    _refuse_detection_mutation(befund, **proposed)
