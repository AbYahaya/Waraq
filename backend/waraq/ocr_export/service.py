"""T-OCR-EX-1 + T-OCR-EX-2 + T-OCR-EX-3 orchestration.

`run_ocr_export` ties the three pieces together:

1. (T-OCR-EX-1) Re-check the gate. Block → raise OcrExportBlocked, NO
   log entry, NO job. (OCR-Gate-Blockiert-Start-Kein-Log-Test.)
2. (T-OCR-EX-1) Verify the Pflichtfragen-Bestätigung Decision Event
   exists for `export_attempt_id`. Missing → raise
   `OcrExportPflichtfragenMissing`.
3. Start an OCR-export Job (job_type=`ocr_export`, Sprint-0 state machine).
   Log Eintrag fires here — Sprint-OCR §2 / Log-Eintrag-Bei-Gestarteten-
   Job-Test.
4. (T-OCR-EX-2) Build the DOCX artefact. On failure → fail the Job, write
   an `OCR_EXPORT_FAILED` log entry, no OCR_EXPORT_EVENT (OCR-EXPORT_EVENT-
   Kein-Eintrag-Bei-Fehler-Test).
5. (T-OCR-EX-3) Atomic OCR_EXPORT_EVENT write via PROVENANCE-Kern, with
   `ocr_revision_snapshot[]` (the segment current_rev_uuid values),
   `active_decision_event_uuids[]` (positive-set: only allowlisted
   decision_sources + only the current attempt's `export_confirmation`),
   `gate_mode`, `active_stilprofil_version_uuid` (null in OCR context),
   `export_warnings[]`.
6. Complete the Job, write `OCR_EXPORT_SUCCESS` log entry.

Per Sprint-OCR §2: OCR_EXPORT_EVENT is `scope_type='project'` +
`scope_uuid=project_uuid` per the EXPORT_EVENT addressing convention
adopted 2026-05-04 (artefact identity in payload). Consistent with the
prior resolution; the Sprint-OCR spec's "scope_type=artefact" wording is
adapted to the canonical 5-value ScopeType.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.eventing import log_event
from waraq.identity.service import new_uuid
from waraq.jobs import complete_job, fail_job, start_job
from waraq.ocr_export.docx_builder import DocxArtefact, build_ocr_docx
from waraq.ocr_export.exceptions import (
    DocxArtefactFailed,
    OcrExportBlocked,
    OcrExportPflichtfragenMissing,
)
from waraq.ocr_export.gate import (
    OcrExportConfig,
    OcrExportGateState,
    check_ocr_export_gate,
)
from waraq.provenance import create_po
from waraq.schemas import DecisionEvent, Job, ProvenanceObject
from waraq.schemas.enums import (
    DecisionSource,
    JobState,
    POType,
    ScopeType,
)

JOB_TYPE = "ocr_export"


# Allowlist of decision_source values that can appear in
# `active_decision_event_uuids[]` per OCR Endfassung §3 positive-set
# rule. Per OCR-Decision-Snapshot-Allowlist-Test:
# - NO `glossary_management`
# - NO `preflight_confirmation`
# - NO `style_management`
# - `export_confirmation` ONLY for the current attempt
_ACTIVE_DE_SOURCE_ALLOWLIST: frozenset[str] = frozenset(
    {
        DecisionSource.OCR_REVIEW.value,
        DecisionSource.LOCK_MANAGEMENT.value,
        DecisionSource.CONFLICT_RESOLUTION.value,
        DecisionSource.AUDIT_RESOLUTION.value,
        DecisionSource.CONSISTENCY_RESOLUTION.value,
        DecisionSource.EXPORT_CONFIRMATION.value,
    }
)


async def _has_pflichtfragen_de(
    *, session: AsyncSession, project_uuid: _uuid.UUID, attempt_id: str
) -> DecisionEvent | None:
    """Look up the Pflichtfragen-Bestätigung DE for this attempt. If
    missing, the export must not start (Sprint-OCR §A H-3 analogue)."""
    result = await session.execute(
        select(DecisionEvent)
        .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
        .where(DecisionEvent.scope_uuid == project_uuid)
        .where(DecisionEvent.decision_type == "ocr_export_pflichtfragen_bestaetigt")
        .where(DecisionEvent.related_export_attempt_id == attempt_id)
    )
    return result.scalar_one_or_none()


async def _collect_segment_revision_snapshot(
    *, session: AsyncSession, segment_uuids: list[_uuid.UUID]
) -> list[str]:
    """Per OCR-Snapshot-Vollstaendigkeit-Test +
    OCR-Snapshot-Segments-Join-Test: snapshot is built from
    `segments.current_rev_uuid`, not from the revisions table directly.
    N segments → N entries (one per segment, even if current_rev_uuid
    is null)."""
    from waraq.schemas import Segment

    result = await session.execute(
        select(Segment.current_rev_uuid).where(Segment.satz_uuid.in_(segment_uuids))
    )
    return [str(rev) if rev is not None else "" for (rev,) in result]


async def _collect_active_decision_event_uuids(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    current_attempt_id: str,
) -> list[str]:
    """Positive-set rule per OCR Endfassung §3 +
    OCR-Decision-Snapshot-Allowlist-Test +
    OCR-Decision-Snapshot-Attempt-Bindung-Test:

    - Only DE with `decision_source ∈ allowlist`
    - For `decision_source=export_confirmation`: only DEs whose
      `related_export_attempt_id == current_attempt_id` (older attempts'
      confirmations are excluded)
    """
    result = await session.execute(
        select(
            DecisionEvent.decision_event_uuid,
            DecisionEvent.decision_source,
            DecisionEvent.related_export_attempt_id,
        )
        .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
        .where(DecisionEvent.scope_uuid == project_uuid)
    )
    out: list[str] = []
    for de_uuid, source, related_attempt in result:
        source_value = str(source)
        if source_value not in _ACTIVE_DE_SOURCE_ALLOWLIST:
            continue
        if (
            source_value == DecisionSource.EXPORT_CONFIRMATION.value
            and related_attempt != current_attempt_id
        ):
            continue
        out.append(str(de_uuid))
    return out


async def run_ocr_export(
    *,
    session: AsyncSession,
    config: OcrExportConfig,
) -> tuple[Job, DocxArtefact, ProvenanceObject]:
    """Execute one OCR-export attempt end-to-end.

    Returns `(job, artefact, ocr_export_event_po)` on success.
    Raises `OcrExportBlocked` / `OcrExportPflichtfragenMissing` on
    pre-job failures (NO log entry written). Raises `DocxArtefactFailed`
    on artefact failure AFTER writing OCR_EXPORT_FAILED log + failing
    the job (NO OCR_EXPORT_EVENT written).
    """
    project_uuid = config.project_uuid
    attempt_id = config.export_attempt_id

    # Pre-job: gate check. Block → no log entry, no job.
    gate = await check_ocr_export_gate(session=session, config=config)
    if gate.state == OcrExportGateState.BLOCKIERT:
        raise OcrExportBlocked(f"OCR export gate is blockiert; reasons: {gate.blocking_reasons}")

    # Pre-job: Pflichtfragen DE must exist for this attempt.
    pflicht_de = await _has_pflichtfragen_de(
        session=session, project_uuid=project_uuid, attempt_id=attempt_id
    )
    if pflicht_de is None:
        raise OcrExportPflichtfragenMissing(
            f"no ocr_export_pflichtfragen_bestaetigt Decision Event found for "
            f"project {project_uuid} + attempt {attempt_id}"
        )

    # --- Job start ---
    job = Job(
        job_uuid=new_uuid(),
        job_type=JOB_TYPE,
        state=JobState.PENDING.value,
        project_uuid=project_uuid,
        payload={
            "export_attempt_id": attempt_id,
            "page_range": list(config.pflichtfragen.page_range),
            "mode": config.pflichtfragen.mode.value,
            "block_types_enabled": list(config.pflichtfragen.block_types_enabled),
        },
    )
    session.add(job)
    await session.flush()
    await start_job(session=session, job=job)

    # --- T-OCR-EX-2: build DOCX ---
    try:
        artefact = await build_ocr_docx(
            session=session,
            project_uuid=project_uuid,
            page_range=config.pflichtfragen.page_range,
            block_types_enabled=config.pflichtfragen.block_types_enabled,
            markings_enabled=config.pflichtfragen.markings_enabled,
            mode=config.pflichtfragen.mode.value,
            warnings=gate.warnings,
        )
    except DocxArtefactFailed as exc:
        await fail_job(
            session=session,
            job=job,
            error={
                "error_class": type(exc).__name__,
                "repr": repr(exc),
                "phase": "docx_build",
            },
        )
        await log_event(
            session=session,
            operation_type="ocr_export_failed",
            scope_type=ScopeType.PROJECT,
            scope_uuid=project_uuid,
            result={
                "job_uuid": str(job.job_uuid),
                "export_attempt_id": attempt_id,
                "phase": "docx_build",
            },
        )
        raise

    # --- T-OCR-EX-3: atomic OCR_EXPORT_EVENT ---
    snapshot = await _collect_segment_revision_snapshot(
        session=session, segment_uuids=artefact.exported_segment_uuids
    )
    active_de_uuids = await _collect_active_decision_event_uuids(
        session=session, project_uuid=project_uuid, current_attempt_id=attempt_id
    )

    payload: dict[str, Any] = {
        "filename": f"ocr_export_{attempt_id}.docx",
        "format": "docx",
        "sha256": artefact.sha256,
        "size_bytes": artefact.size_bytes,
        "artefact_uuid": str(artefact.artefact_uuid),
        "page_range": list(config.pflichtfragen.page_range),
        "mode": config.pflichtfragen.mode.value,
        "block_types_enabled": list(config.pflichtfragen.block_types_enabled),
        "markings_enabled": config.pflichtfragen.markings_enabled,
        "ocr_revision_snapshot": snapshot,
        "active_decision_event_uuids": active_de_uuids,
        "gate_mode": (
            "exportierbar_mit_warnungen"
            if gate.state == OcrExportGateState.EXPORTIERBAR_MIT_WARNUNGEN
            else "exportierbar"
        ),
        "active_stilprofil_version_uuid": None,
        "export_warnings": list(gate.warnings),
        "export_attempt_id": attempt_id,
        "exported_segment_uuids": [str(u) for u in artefact.exported_segment_uuids],
        "exported_page_uuids": [str(u) for u in artefact.exported_page_uuids],
        "n_segments_exported": artefact.n_segments_exported,
        "n_pages_exported": artefact.n_pages_exported,
        "n_locked_segments_exported": artefact.n_locked_segments_exported,
        "block_types_present": list(artefact.block_types_present),
    }

    po = await create_po(
        session=session,
        po_type=POType.OCR_EXPORT_EVENT,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        payload=payload,
        author_uuid=config.actor_uuid,
    )

    await complete_job(
        session=session,
        job=job,
        result={
            "export_attempt_id": attempt_id,
            "artefact_sha256": artefact.sha256,
            "size_bytes": artefact.size_bytes,
            "ocr_export_event_po_uuid": str(po.po_uuid),
            "n_segments_exported": artefact.n_segments_exported,
        },
    )
    await log_event(
        session=session,
        operation_type="ocr_export_success",
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        result={
            "job_uuid": str(job.job_uuid),
            "export_attempt_id": attempt_id,
            "ocr_export_event_po_uuid": str(po.po_uuid),
        },
    )
    return job, artefact, po


# Helper for downstream code: count OCR_EXPORT_EVENT POs for a project.
async def count_ocr_export_events_for_project(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(ProvenanceObject)
        .where(ProvenanceObject.po_type == POType.OCR_EXPORT_EVENT.value)
        .where(ProvenanceObject.scope_uuid == project_uuid)
    )
    return result.scalar_one()
