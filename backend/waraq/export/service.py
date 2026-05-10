"""T-9.2.1 — Export service: `export_starten` + `run_export_job`.

Per Sprint 5 §2:

- `export_starten` is the user action. Refused if preflight is not
  `exportierbar` / `exportierbar_mit_warnungen`. Writes a Decision
  Event with `decision_type='exportstart'` and
  `scope_type='project'`. Returns the `current_export_attempt_id`.

- `run_export_job` performs the export pipeline. State machine maps
  to canonical Sprint-0 JobState values (per WORKLOG decision the
  English vocabulary is kept; Sprint 5 §2's German `aktiv |
  abgeschlossen | fehlgeschlagen` maps to `running | completed |
  failed`).

- Atomic commit per DBB Abkürzung 4: artefact built in memory →
  preflight re-checked at job start → on success, the three-step
  commit (a) `ArtefactStore.commit` move-to-persistent, (b)
  `create_po` for EXPORT_EVENT via PROVENANCE-Kern, (c)
  `complete_job`. Any failure rolls back the caller's transaction —
  no EXPORT_EVENT, no orphaned artefact, only a FAILED Log-Eintrag.

- Exportlauf-Ereignis Log-Eintrag is written on every attempt that
  reached the Job stage (success / fail / preflight_state_changed).
  `export_starten` refusal at the entry check produces NO Log-Eintrag
  (per Log-Eintrag-Vorabpruefung-Kein-Test).
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.canon_rules import verify_canon_rules_for_export
from waraq.decisions import create_decision_event
from waraq.eventing import log_event
from waraq.export.artefact_storage import (
    ArtefactStore,
    ArtefactStoreCommitFailed,
    InMemoryArtefactStore,
)
from waraq.export.docx_builder import build_translation_docx
from waraq.export.enums import ExportGateMode
from waraq.export.exceptions import (
    CanonRuleViolationsDetected,
    ExportNotInExportableState,
    PreflightStateChanged,
)
from waraq.export.snapshot import (
    collect_active_decision_event_uuids,
    collect_revision_snapshot,
)
from waraq.identity.service import new_uuid
from waraq.jobs import complete_job, fail_job, start_job
from waraq.preflight import PreflightState, evaluate_preflight, start_preflight_run
from waraq.preflight.service import JOB_TYPE as PREFLIGHT_JOB_TYPE
from waraq.provenance import create_po
from waraq.schemas import DecisionEvent, Job, ProvenanceObject
from waraq.schemas.enums import DecisionSource, JobState, POType, ScopeType

JOB_TYPE = "export"


_EXPORTABLE_STATES = {
    PreflightState.EXPORTIERBAR,
    PreflightState.EXPORTIERBAR_MIT_WARNUNGEN,
}


# --- public dataclasses -------------------------------------------------


@dataclass(frozen=True, kw_only=True, slots=True)
class ExportConfig:
    """Per-attempt export configuration.

    `current_export_attempt_id` binds Pflichtfragen-Bestätigungen and
    per-warning go_with_warning confirmations from Sprint 4 to this
    specific attempt (R-S5-06: stale prior-attempt confirmations must
    not pollute the current snapshot).

    `segment_uuids` constrains the scope (None = full project). Per
    Sprint 5 §2 / Revision-Snapshot-Outside-Scope-Excluded-Test the
    snapshot must respect this scope.
    """

    project_uuid: _uuid.UUID
    account_uuid: _uuid.UUID
    project_title: str
    current_export_attempt_id: str
    preflight_run: Job
    export_type: str = "docx"
    segment_uuids: list[_uuid.UUID] | None = None
    actor_uuid: _uuid.UUID | None = None
    export_warnings: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True, slots=True)
class ExportResult:
    job: Job
    export_event_po: ProvenanceObject
    artefact_uuid: _uuid.UUID
    artefact_sha256: str
    artefact_size_bytes: int
    artefact_ref: str
    revision_snapshot: list[_uuid.UUID]
    active_decision_event_uuids: list[_uuid.UUID]
    gate_mode: ExportGateMode


# --- export_starten -----------------------------------------------------


async def export_starten(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    preflight_state: PreflightState,
    actor_uuid: _uuid.UUID | None = None,
    annotation: str | None = None,
) -> tuple[DecisionEvent, str]:
    """User-action entry point. Per Export-Starten-Decision-Event-Test +
    Export-Starten-Nur-Aus-Exportierbar-Test:

    - Refuses any preflight state outside
      {`exportierbar`, `exportierbar_mit_warnungen`}.
    - Writes a Decision Event with
      `decision_type='exportstart'`,
      `scope_type='project'`.
    - Returns `(decision_event, export_attempt_id)`. The
      `export_attempt_id` ties downstream `run_export_job` to this
      user action (used as `related_export_attempt_id` on per-warning
      Decision Events filtered by `collect_active_decision_event_uuids`).
    - Refusal at this gate produces NO Log-Eintrag and NO Job (per
      Log-Eintrag-Vorabpruefung-Kein-Test).
    """
    if preflight_state not in _EXPORTABLE_STATES:
        raise ExportNotInExportableState(
            f"export_starten refused: preflight state is "
            f"{preflight_state.value!r}; must be `exportierbar` or "
            "`exportierbar_mit_warnungen`."
        )

    export_attempt_id = str(new_uuid())
    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        decision_type="exportstart",
        decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        actor_uuid=actor_uuid,
        content={
            "preflight_state_at_action": preflight_state.value,
            "export_attempt_id": export_attempt_id,
            "annotation": annotation,
        },
        related_export_attempt_id=export_attempt_id,
    )
    return de, export_attempt_id


# --- run_export_job -----------------------------------------------------


async def run_export_job(
    *,
    session: AsyncSession,
    config: ExportConfig,
    artefact_store: ArtefactStore | None = None,
) -> ExportResult:
    """Execute one export attempt end-to-end.

    Steps:
    1. Start `Job` with `job_type='export'` (PENDING → RUNNING).
    2. Re-check preflight state at job start. State degradation since
       `export_starten` → `PreflightStateChanged` raised, Job →
       FAILED, Log-Eintrag (`export_failed`) written, no artefact.
    3. Build the DOCX in memory (read-only, no Revision/Segment
       mutation).
    4. Atomic commit:
       (a) `artefact_store.commit(artefact_uuid, bytes_)` — move to
           persistent location.
       (b) `create_po(po_type=EXPORT_EVENT, scope_type=project,
           scope_uuid=project_uuid, payload={...})`.
       (c) `complete_job(job)`.
       Any failure raises and the caller's transaction rolls back —
       no EXPORT_EVENT, no orphaned artefact.
    5. Log `export_success` Eintrag.
    """
    store = artefact_store or InMemoryArtefactStore()

    # --- Step 1: Job start ---
    job = Job(
        job_uuid=new_uuid(),
        job_type=JOB_TYPE,
        state=JobState.PENDING.value,
        project_uuid=config.project_uuid,
        payload={
            "export_attempt_id": config.current_export_attempt_id,
            "export_type": config.export_type,
            "segment_uuids": (
                [str(u) for u in config.segment_uuids] if config.segment_uuids is not None else None
            ),
        },
    )
    session.add(job)
    await session.flush()
    await start_job(session=session, job=job)

    # --- Step 2: re-check preflight at job start ---
    # The preflight job from Sprint 4 holds the gate state for THIS
    # attempt's per-warning acceptances. Re-evaluate against current
    # project state — if any new finding has appeared the preflight
    # may have degraded to `blockiert`.
    preflight_now = await evaluate_preflight(
        session=session,
        project_uuid=config.project_uuid,
        preflight_run=config.preflight_run,
    )
    if preflight_now.state not in _EXPORTABLE_STATES:
        await fail_job(
            session=session,
            job=job,
            error={
                "error_class": "PreflightStateChanged",
                "phase": "preflight_recheck",
                "current_state": preflight_now.state.value,
                "blocking_reasons": [r.value for r in preflight_now.blocking_reasons],
                "reason": "preflight_state_changed",
            },
        )
        await log_event(
            session=session,
            operation_type="export_failed",
            scope_type=ScopeType.PROJECT,
            scope_uuid=config.project_uuid,
            result={
                "job_uuid": str(job.job_uuid),
                "export_attempt_id": config.current_export_attempt_id,
                "phase": "preflight_recheck",
                "reason": "preflight_state_changed",
                "current_state": preflight_now.state.value,
            },
        )
        raise PreflightStateChanged(
            f"preflight state at job start is {preflight_now.state.value!r}; "
            "must be `exportierbar` or `exportierbar_mit_warnungen`."
        )

    # --- Step 2b: §2.2 canon-rule pre-export verifier (Phase 3 sub-batch B) ---
    # Defense-in-depth: when any write path bypassed `apply_all` the
    # auto-normalize, residual digit / EI2 violations are caught here.
    # Same shape as the PreflightStateChanged path above — fail Job,
    # write Log-Eintrag, raise; no artefact, no EXPORT_EVENT.
    canon_violations = await verify_canon_rules_for_export(
        session=session,
        project_uuid=config.project_uuid,
    )
    if canon_violations:
        await fail_job(
            session=session,
            job=job,
            error={
                "error_class": "CanonRuleViolationsDetected",
                "phase": "canon_rule_recheck",
                "reason": "canon_rule_violations",
                "violations": [
                    {"satz_uuid": str(v.satz_uuid), "kind": v.kind.value} for v in canon_violations
                ],
            },
        )
        await log_event(
            session=session,
            operation_type="export_failed",
            scope_type=ScopeType.PROJECT,
            scope_uuid=config.project_uuid,
            result={
                "job_uuid": str(job.job_uuid),
                "export_attempt_id": config.current_export_attempt_id,
                "phase": "canon_rule_recheck",
                "reason": "canon_rule_violations",
                "violation_count": len(canon_violations),
            },
        )
        raise CanonRuleViolationsDetected(
            f"§2.2 canon-rule violations detected on {len(canon_violations)} segment "
            f"row(s) at export-job start; re-translate or manually fix the affected "
            "segments before retrying export.",
            violations=canon_violations,
        )

    gate_mode = (
        ExportGateMode.EXPORTIERBAR_MIT_WARNUNGEN
        if preflight_now.state == PreflightState.EXPORTIERBAR_MIT_WARNUNGEN
        else ExportGateMode.EXPORTIERBAR
    )
    export_warnings = (
        list(config.export_warnings)
        if (gate_mode == ExportGateMode.EXPORTIERBAR_MIT_WARNUNGEN)
        else []
    )

    # --- Step 3: build artefact (read-only) ---
    try:
        artefact = await build_translation_docx(
            session=session,
            project_uuid=config.project_uuid,
            project_title=config.project_title,
            segment_uuids=config.segment_uuids,
        )
    except Exception as exc:
        await fail_job(
            session=session,
            job=job,
            error={
                "error_class": type(exc).__name__,
                "phase": "artefact_build",
                "repr": repr(exc),
            },
        )
        await log_event(
            session=session,
            operation_type="export_failed",
            scope_type=ScopeType.PROJECT,
            scope_uuid=config.project_uuid,
            result={
                "job_uuid": str(job.job_uuid),
                "export_attempt_id": config.current_export_attempt_id,
                "phase": "artefact_build",
            },
        )
        raise

    # --- Step 4: atomic commit ---
    # Build the snapshots first; they read project state, no writes.
    (
        revision_snapshot,
        snapshot_seg_uuids,
        page_uuids,
        block_uuids,
    ) = await collect_revision_snapshot(
        session=session,
        project_uuid=config.project_uuid,
        segment_uuids=config.segment_uuids,
    )
    active_de_uuids = await collect_active_decision_event_uuids(
        session=session,
        project_uuid=config.project_uuid,
        account_uuid=config.account_uuid,
        segment_uuids=snapshot_seg_uuids,
        page_uuids=page_uuids,
        block_uuids=block_uuids,
        current_export_attempt_id=config.current_export_attempt_id,
    )

    # Read the Pflichtfragen-Bestätigungen of the current attempt to
    # populate `export_config`. Per Pflichtfragen-Read-From-Decision-
    # Events-Test: read DEs, never read the Export-Profil table.
    pflichtfragen_des = list(
        (
            await session.execute(
                _build_current_pflichtfragen_query(
                    project_uuid=config.project_uuid,
                    export_attempt_id=config.current_export_attempt_id,
                )
            )
        ).scalars()
    )
    export_config_payload: dict[str, Any] = {
        "export_type": config.export_type,
        "scope_segment_uuids": (
            [str(u) for u in config.segment_uuids] if config.segment_uuids is not None else None
        ),
        "pflichtfragen": [
            {
                "decision_event_uuid": str(de.decision_event_uuid),
                "frage_index": (de.content or {}).get("frage_index"),
                "frage_key": (de.content or {}).get("frage_key"),
                "answer": (de.content or {}).get("answer"),
            }
            for de in pflichtfragen_des
        ],
    }

    # (a) Move artefact to persistent location.
    try:
        artefact_ref = store.commit(artefact_uuid=artefact.artefact_uuid, bytes_=artefact.bytes_)
    except ArtefactStoreCommitFailed as exc:
        await fail_job(
            session=session,
            job=job,
            error={
                "error_class": type(exc).__name__,
                "phase": "atomic_commit_a_move",
                "repr": repr(exc),
            },
        )
        await log_event(
            session=session,
            operation_type="export_failed",
            scope_type=ScopeType.PROJECT,
            scope_uuid=config.project_uuid,
            result={
                "job_uuid": str(job.job_uuid),
                "export_attempt_id": config.current_export_attempt_id,
                "phase": "atomic_commit_a_move",
            },
        )
        raise

    # (b) Write EXPORT_EVENT via PROVENANCE-Kern.
    payload: dict[str, Any] = {
        "export_uuid": str(new_uuid()),
        "project_uuid": str(config.project_uuid),
        "project_title": config.project_title,
        "export_type": config.export_type,
        "export_config": export_config_payload,
        "revision_snapshot": [str(u) for u in revision_snapshot],
        "active_decision_event_uuids": [str(u) for u in active_de_uuids],
        "gate_mode": gate_mode.value,
        "export_warnings": export_warnings,
        "artefact_ref": artefact_ref,
        "artefact_uuid": str(artefact.artefact_uuid),
        "filename": f"export_{config.current_export_attempt_id}.docx",
        "format": "docx",
        "sha256": artefact.sha256,
        "size_bytes": artefact.size_bytes,
        "n_pages_exported": artefact.n_pages_exported,
        "n_segments_exported": artefact.n_segments_exported,
        "block_types_present": list(artefact.block_types_present),
        "export_attempt_id": config.current_export_attempt_id,
    }
    po = await create_po(
        session=session,
        po_type=POType.EXPORT_EVENT,
        scope_type=ScopeType.PROJECT,
        scope_uuid=config.project_uuid,
        payload=payload,
        author_uuid=config.actor_uuid,
    )

    # (c) Mark Job COMPLETED.
    await complete_job(
        session=session,
        job=job,
        result={
            "export_attempt_id": config.current_export_attempt_id,
            "export_event_po_uuid": str(po.po_uuid),
            "artefact_sha256": artefact.sha256,
            "size_bytes": artefact.size_bytes,
            "gate_mode": gate_mode.value,
            "n_segments_exported": artefact.n_segments_exported,
        },
    )
    await log_event(
        session=session,
        operation_type="export_success",
        scope_type=ScopeType.PROJECT,
        scope_uuid=config.project_uuid,
        result={
            "job_uuid": str(job.job_uuid),
            "export_attempt_id": config.current_export_attempt_id,
            "export_event_po_uuid": str(po.po_uuid),
            "gate_mode": gate_mode.value,
        },
    )

    return ExportResult(
        job=job,
        export_event_po=po,
        artefact_uuid=artefact.artefact_uuid,
        artefact_sha256=artefact.sha256,
        artefact_size_bytes=artefact.size_bytes,
        artefact_ref=artefact_ref,
        revision_snapshot=revision_snapshot,
        active_decision_event_uuids=active_de_uuids,
        gate_mode=gate_mode,
    )


# --- helpers ------------------------------------------------------------


def _build_current_pflichtfragen_query(*, project_uuid: _uuid.UUID, export_attempt_id: str) -> Any:
    """Return the SELECT for `pflichtfrage_bestaetigung` DEs of THIS
    attempt — per Pflichtfragen-Read-From-Decision-Events-Test."""
    from sqlalchemy import select

    return (
        select(DecisionEvent)
        .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
        .where(DecisionEvent.scope_uuid == project_uuid)
        .where(DecisionEvent.decision_type == "pflichtfrage_bestaetigung")
        .where(DecisionEvent.decision_source == DecisionSource.PREFLIGHT_CONFIRMATION.value)
        .where(DecisionEvent.related_export_attempt_id == export_attempt_id)
    )


# Silence unused-import warnings for symbols re-exported via __init__.
_ = (PREFLIGHT_JOB_TYPE, start_preflight_run)


__all__ = [
    "JOB_TYPE",
    "ExportConfig",
    "ExportResult",
    "export_starten",
    "run_export_job",
]
