"""T-8.2.1 — Consistency engine harness.

Per Sprint 4 §2 (M2-closeout shape, full bodies in M5):

- 7 K-rules: K-01 .. K-07. Each binds to its OWN `subject_type`. **No rule
  reduces to plain string equality of surface forms** (DBB §B Abkürzung 10).
- Engine reads only the rules' passende Identitätstyp records. The
  per-rule check function is a `KRule` Protocol implementation registered
  via `register_k_rule`.
- Inconsistency detection produces a `Konsistenz-Befund` row with
  `aufloesungsstatus=offen`. The `vorschlag` is a system suggestion, never
  applied automatically.
- The engine runs as a Job (`job_type=consistency`) using the canonical
  Sprint-0 state machine. EVENTING records every run.

**M2-closeout limitation**: K-rule bodies are stubs (`waraq.consistency.stubs`)
that return empty finding lists. The harness — registry, finding-row write,
Job lifecycle, resolution-with-DE — is real. Real rule bodies land in M5
once T-8.1.x audit infrastructure is available; the public surface here
will not change at that point.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.eventing import log_event
from waraq.identity.service import new_uuid
from waraq.jobs import complete_job, fail_job, start_job
from waraq.schemas import Job, KonsistenzBefund
from waraq.schemas.enums import JobState, ScopeType


class KRuleId(StrEnum):
    """Per Sprint 4 §2 — 7 canonical K-rules."""

    K_01 = "K-01"  # terminological consistency (concept_id)
    K_02 = "K-02"  # formula and index consistency (formel_verzeichnis_id)
    K_03 = "K-03"  # entity consistency (entity_id)
    K_04 = "K-04"  # transliteration consistency (transliterations_muster)
    K_05 = "K-05"  # source-citation consistency (source_identity)
    K_06 = "K-06"  # structural pattern consistency (structural_key)
    K_07 = "K-07"  # cross-rule terminological consistency (concept_id)


class SubjectType(StrEnum):
    """Per Sprint 4 §2 — the identity-type each K-rule binds to."""

    CONCEPT_ID = "concept_id"
    FORMEL_VERZEICHNIS_ID = "formel_verzeichnis_id"
    ENTITY_ID = "entity_id"
    TRANSLITERATIONS_MUSTER = "transliterations_muster"
    SOURCE_IDENTITY = "source_identity"
    STRUCTURAL_KEY = "structural_key"


# Static binding of K-rules to subject_type. K-01 and K-07 both bind to
# concept_id (per Sprint 4 §2: K-07 = cross-rule terminology, same
# Identitätstyp as K-01 but different scope).
K_RULE_SUBJECT_TYPE: dict[KRuleId, SubjectType] = {
    KRuleId.K_01: SubjectType.CONCEPT_ID,
    KRuleId.K_02: SubjectType.FORMEL_VERZEICHNIS_ID,
    KRuleId.K_03: SubjectType.ENTITY_ID,
    KRuleId.K_04: SubjectType.TRANSLITERATIONS_MUSTER,
    KRuleId.K_05: SubjectType.SOURCE_IDENTITY,
    KRuleId.K_06: SubjectType.STRUCTURAL_KEY,
    KRuleId.K_07: SubjectType.CONCEPT_ID,
}


class Verstossklasse(StrEnum):
    """Per Dokument 1 §4.6 — severity classes used by both audit and
    consistency findings. Routing into preflight (W-02 vs P-03) happens at
    preflight evaluation, not stored on this row."""

    KRITISCH = "kritisch"
    HOCH = "hoch"
    MITTEL = "mittel"


@dataclass(frozen=True, kw_only=True, slots=True)
class KConsistencyFinding:
    """An in-memory finding produced by a K-rule before persistence.

    The engine converts each finding into a `KonsistenzBefund` row.
    `subject_type` is fixed by the K-rule (see `K_RULE_SUBJECT_TYPE`); the
    rule fills `subject_key` (the actual identity it found inconsistent),
    severity, affected segments, and the system suggestion.
    """

    k_rule: KRuleId
    subject_key: str
    verstossklasse: Verstossklasse
    betroffene_segment_uuids: list[_uuid.UUID] = field(default_factory=list)
    vorschlag: dict[str, Any] = field(default_factory=dict)


class KRule(Protocol):
    """A K-rule check function.

    Receives a session + project_uuid and returns the findings it produced.
    Implementations are pure-by-construction with respect to the table
    schema: they MUST NOT write KonsistenzBefund rows themselves; the
    engine handles persistence.
    """

    async def __call__(
        self,
        *,
        session: AsyncSession,
        project_uuid: _uuid.UUID,
    ) -> Iterable[KConsistencyFinding]: ...


# --- registry -------------------------------------------------------------

_REGISTRY: dict[KRuleId, KRule] = {}


def register_k_rule(rule_id: KRuleId, rule: KRule) -> None:
    """Register (or replace) the check function for a K-rule.

    Stub registration happens at import time via
    `consistency.stubs.register_stub_k_rules()`; back-fill in M5 replaces
    each entry with a real body.
    """
    _REGISTRY[rule_id] = rule


def _get_registered_rule(rule_id: KRuleId) -> KRule:
    if rule_id not in _REGISTRY:
        raise KeyError(
            f"K-rule {rule_id.value} is not registered. Call "
            "register_stub_k_rules() at startup, or register a real body "
            "via register_k_rule()."
        )
    return _REGISTRY[rule_id]


# --- engine ---------------------------------------------------------------


JOB_TYPE = "consistency"


async def run_consistency_check(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    rule_ids: Iterable[KRuleId] | None = None,
) -> tuple[Job, list[KonsistenzBefund]]:
    """Run the registered K-rules against a project.

    Wraps the run in a Job (`job_type=consistency`, Sprint-0 state
    machine). Persists every finding as a `Konsistenz-Befund` row with
    `aufloesungsstatus=offen`. Logs start + end via EVENTING.

    Args:
        session: Active async session. Caller manages commit/rollback.
        project_uuid: Project to scope the run to.
        rule_ids: Optional subset of K-rules to run. Defaults to all 7.

    Returns:
        `(job, findings)`. Job is COMPLETED on success. Findings is the
        flat list of newly persisted Konsistenz-Befund rows (all
        `aufloesungsstatus=offen`).
    """
    rules = list(rule_ids) if rule_ids is not None else list(KRuleId)

    job = Job(
        job_uuid=new_uuid(),
        job_type=JOB_TYPE,
        state=JobState.PENDING.value,
        project_uuid=project_uuid,
        payload={"k_rule_ids": [r.value for r in rules]},
    )
    session.add(job)
    await session.flush()
    await start_job(session=session, job=job)

    await log_event(
        session=session,
        operation_type="consistency_run_started",
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        result={"job_uuid": str(job.job_uuid), "k_rule_ids": [r.value for r in rules]},
    )

    findings_persisted: list[KonsistenzBefund] = []
    try:
        for rule_id in rules:
            rule = _get_registered_rule(rule_id)
            findings = list(
                await _materialize_iterable(rule(session=session, project_uuid=project_uuid))
            )
            for f in findings:
                if f.k_rule != rule_id:
                    raise ValueError(
                        f"K-rule {rule_id.value} returned a finding tagged "
                        f"with a different rule ({f.k_rule.value}). Rules "
                        "must only emit findings under their own k_rule id."
                    )
                row = KonsistenzBefund(
                    konsistenz_befund_uuid=new_uuid(),
                    project_uuid=project_uuid,
                    k_rule=f.k_rule.value,
                    subject_type=K_RULE_SUBJECT_TYPE[f.k_rule].value,
                    subject_key=f.subject_key,
                    verstossklasse=f.verstossklasse.value,
                    betroffene_segment_uuids=[str(u) for u in f.betroffene_segment_uuids],
                    vorschlag=f.vorschlag,
                )
                session.add(row)
                findings_persisted.append(row)
        await session.flush()
    except Exception as exc:
        await fail_job(
            session=session,
            job=job,
            error={
                "error_class": type(exc).__name__,
                "repr": repr(exc),
                "phase": "consistency_run",
            },
        )
        raise

    await complete_job(
        session=session,
        job=job,
        result={
            "findings_count": len(findings_persisted),
            "k_rule_ids": [r.value for r in rules],
        },
    )
    await log_event(
        session=session,
        operation_type="consistency_run_completed",
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        result={
            "job_uuid": str(job.job_uuid),
            "findings_count": len(findings_persisted),
        },
    )
    return job, findings_persisted


async def _materialize_iterable(
    awaitable_or_iter: Awaitable[Iterable[KConsistencyFinding]] | Iterable[KConsistencyFinding],
) -> Iterable[KConsistencyFinding]:
    """Some K-rule signatures will be `async def` returning an iterable.
    Awaiting one already gives the iterable. Defensive helper kept for
    readability of the engine loop."""
    if hasattr(awaitable_or_iter, "__await__"):
        # mypy: this branch is the awaitable case.
        return await awaitable_or_iter  # type: ignore[no-any-return,misc]
    return awaitable_or_iter


# Compatibility export — some callers expect the registry function alone.
def _registered_rule_ids() -> list[KRuleId]:
    return list(_REGISTRY.keys())


__all__ = [
    "JOB_TYPE",
    "K_RULE_SUBJECT_TYPE",
    "KConsistencyFinding",
    "KRule",
    "KRuleId",
    "SubjectType",
    "Verstossklasse",
    "register_k_rule",
    "run_consistency_check",
]


# Cast to silence unused import warnings in __init__.py re-export.
_: Callable[..., Any] = run_consistency_check
