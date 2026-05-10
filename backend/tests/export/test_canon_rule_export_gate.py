"""Phase 3 sub-batch B — §2.2 canon-rule pre-export blocking gate tests."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.export._helpers import (
    reach_exportierbar,
    seed_project_with_account,
    seed_segment_with_revision,
)
from waraq.export import (
    CanonRuleViolationsDetected,
    ExportConfig,
    run_export_job,
)
from waraq.identity import new_uuid
from waraq.preflight import PreflightState
from waraq.schemas import Job, LogEntry, ProvenanceObject
from waraq.schemas.enums import JobState, POType


async def _start_export_with_dirty_segment_text(
    db_session: AsyncSession,
    *,
    project,
    account_uuid,
    dirty_text: str,
):
    """Seed a segment, reach exportierbar, then mutate segment.text_content
    AFTER preflight to simulate a write path that bypassed normalize.

    This is the canonical defense-in-depth scenario for the verifier:
    auto-normalize on translation output + manual-edit save would
    catch the violation upstream — but a tool that wrote raw bytes
    would not. The verifier catches it at the export-job boundary.
    """
    seg = await seed_segment_with_revision(db_session, project=project, text="clean\n---\nclean")
    run, state = await reach_exportierbar(db_session, project=project)
    assert state == PreflightState.EXPORTIERBAR
    # Mutate AFTER preflight + Pflichtfragen — bypasses normalize.
    seg.text_content = dirty_text
    await db_session.flush()
    config = ExportConfig(
        project_uuid=project.project_uuid,
        account_uuid=account_uuid,
        project_title="canon-gate-test",
        current_export_attempt_id=str(new_uuid()),
        preflight_run=run,
    )
    return seg, run, config


@pytest.mark.asyncio
class TestCanonRuleGateRefusesExport:
    async def test_arabic_indic_digits_block_export(self, db_session: AsyncSession) -> None:
        project, account_uuid = await seed_project_with_account(db_session)
        seg, _run, config = await _start_export_with_dirty_segment_text(
            db_session,
            project=project,
            account_uuid=account_uuid,
            dirty_text="Page ٤٢ remix",
        )
        with pytest.raises(CanonRuleViolationsDetected) as exc_info:
            await run_export_job(session=db_session, config=config)
        assert any(v.satz_uuid == seg.satz_uuid for v in exc_info.value.violations)

    async def test_ei2_violations_block_export(self, db_session: AsyncSession) -> None:
        project, account_uuid = await seed_project_with_account(db_session)
        seg, _run, config = await _start_export_with_dirty_segment_text(
            db_session,
            project=project,
            account_uuid=account_uuid,
            dirty_text="Ḳur'an study",
        )
        with pytest.raises(CanonRuleViolationsDetected) as exc_info:
            await run_export_job(session=db_session, config=config)
        assert exc_info.value.violations[0].satz_uuid == seg.satz_uuid


@pytest.mark.asyncio
class TestCanonRuleGateAtomicity:
    async def test_no_export_event_no_artefact_on_violation(self, db_session: AsyncSession) -> None:
        """Verifier failure must leave the system in the same atomicity
        regime as PreflightStateChanged: no EXPORT_EVENT-PO, fail Job,
        export_failed Log-Eintrag."""
        project, account_uuid = await seed_project_with_account(db_session)
        before_po = (
            await db_session.execute(
                select(func.count())
                .select_from(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.EXPORT_EVENT.value)
            )
        ).scalar_one()

        _seg, _run, config = await _start_export_with_dirty_segment_text(
            db_session,
            project=project,
            account_uuid=account_uuid,
            dirty_text="dirty ٤",
        )
        with pytest.raises(CanonRuleViolationsDetected):
            await run_export_job(session=db_session, config=config)

        # No new EXPORT_EVENT.
        after_po = (
            await db_session.execute(
                select(func.count())
                .select_from(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.EXPORT_EVENT.value)
            )
        ).scalar_one()
        assert after_po == before_po

        # Export-side Job exists and is FAILED.
        result = await db_session.execute(
            select(Job)
            .where(Job.project_uuid == project.project_uuid)
            .where(Job.job_type == "export")
        )
        jobs = list(result.scalars())
        assert len(jobs) == 1
        assert jobs[0].state == JobState.FAILED.value
        assert jobs[0].error is not None
        assert jobs[0].error["error_class"] == "CanonRuleViolationsDetected"
        assert jobs[0].error["phase"] == "canon_rule_recheck"

        # export_failed Log-Eintrag with canon_rule_violations reason.
        log_result = await db_session.execute(
            select(LogEntry)
            .where(LogEntry.scope_uuid == project.project_uuid)
            .where(LogEntry.operation_type == "export_failed")
        )
        logs = list(log_result.scalars())
        assert len(logs) == 1
        assert logs[0].result["reason"] == "canon_rule_violations"
        assert logs[0].result["phase"] == "canon_rule_recheck"


@pytest.mark.asyncio
class TestCanonRuleGateCleanProjectPasses:
    async def test_clean_project_export_succeeds(self, db_session: AsyncSession) -> None:
        """Sanity: when no violations exist, the new gate is transparent."""
        from waraq.export import ExportConfig, run_export_job

        project, account_uuid = await seed_project_with_account(db_session)
        await seed_segment_with_revision(
            db_session, project=project, text="clean source\n---\nclean target"
        )
        run, state = await reach_exportierbar(db_session, project=project)
        assert state == PreflightState.EXPORTIERBAR

        config = ExportConfig(
            project_uuid=project.project_uuid,
            account_uuid=account_uuid,
            project_title="clean-test",
            current_export_attempt_id=str(new_uuid()),
            preflight_run=run,
        )
        result = await run_export_job(session=db_session, config=config)
        assert result.export_event_po is not None
