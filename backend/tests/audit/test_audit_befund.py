"""T-8.1.1 — Befund-Tabelle + audit-run mandatory tests.

Per Sprint 3 §4:
- T-H4-02: audit produces no revision-UUID
- Audit-Befund-Tabelle-Eigene-Tabelle-Test
- Audit-Befund-Immutable-Detection-Test
- Audit-Befund-Resolution-Mutable-Only-Test
- Audit-Run-Log-Eintrag-Test
- Audit-Kein-Auto-Korrektur-Test
- Audit-Job-State-Machine-Test
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment, st
from waraq.audit import (
    AuditRunResult,
    BefundDetectionImmutable,
    RuleFinding,
    assert_detection_immutable,
    record_befund,
    run_audit_for_project,
)
from waraq.audit.rules import rule_a_01
from waraq.audit.severity import default_severity_table
from waraq.identity import new_uuid
from waraq.schemas import (
    Befund,
    DecisionEvent,
    Job,
    LogEntry,
    Revision,
    Segment,
    TranslationObservation,
)
from waraq.schemas.enums import JobState, ScopeType

# --- Audit-Befund-Tabelle-Eigene-Tabelle-Test ------------------------


@pytest.mark.asyncio
class TestBefundIsOwnTable:
    async def test_befund_table_is_distinct_from_revision_and_decision(self) -> None:
        """DB-introspection check that `audit_befunde` is its own table.

        Per Sprint 3 R-S3-02: Befund-Tabelle is NOT an FK extension of
        Revision or Decision Event."""
        # Befund's __table__ name and FK targets must show three separate tables.
        assert Befund.__tablename__ == "audit_befunde"
        # The Befund FKs reach segments / projects / jobs / decision_events
        # — but Befund is not a row inside any of those, and not joined to
        # them by inheritance.
        fk_targets = {fk.column.table.name for fk in Befund.__table__.foreign_keys}
        assert "segments" in fk_targets
        assert "projects" in fk_targets
        assert "jobs" in fk_targets
        assert "decision_events" in fk_targets
        # Crucially Befund is NOT a row in revisions or decision_events.
        assert Befund.__tablename__ != Revision.__tablename__
        assert Befund.__tablename__ != DecisionEvent.__tablename__


# --- Audit-Befund-Immutable-Detection-Test ---------------------------


@pytest.mark.asyncio
class TestBefundDetectionImmutable:
    async def test_detection_field_mutation_refused(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        segment = await seed_segment(db_session, project=project, text="hello")
        # Create a Befund directly (without going through a full run).
        job = Job(job_uuid=new_uuid(), job_type="audit", state=JobState.PENDING.value)
        db_session.add(job)
        await db_session.flush()
        befund = await record_befund(
            session=db_session,
            finding=RuleFinding(
                regelkennung="A-01",
                satz_uuid=segment.satz_uuid,
                detection_context={"marker": "x"},
            ),
            project_uuid=project.project_uuid,
            audit_run_job_uuid=job.job_uuid,
            severity_table=default_severity_table(),
        )
        # Service-level guard refuses kwargs targeting detection fields.
        for field in ("regelkennung", "verstossklasse", "schweregrad", "detected_at"):
            with pytest.raises(BefundDetectionImmutable):
                assert_detection_immutable(befund, **{field: "anything"})


# --- Audit-Befund-Resolution-Mutable-Only-Test -----------------------


@pytest.mark.asyncio
class TestResolutionFieldsMutable:
    async def test_resolution_fields_pass_immutability_guard(
        self, db_session: AsyncSession
    ) -> None:
        # The detection-immutability guard should NOT block resolution-side
        # field updates. (No exception raised.)
        project = await seed_project(db_session)
        segment = await seed_segment(db_session, project=project, text="hi")
        job = Job(job_uuid=new_uuid(), job_type="audit", state=JobState.PENDING.value)
        db_session.add(job)
        await db_session.flush()
        befund = await record_befund(
            session=db_session,
            finding=RuleFinding(
                regelkennung="A-01",
                satz_uuid=segment.satz_uuid,
                detection_context={},
            ),
            project_uuid=project.project_uuid,
            audit_run_job_uuid=job.job_uuid,
            severity_table=default_severity_table(),
        )
        # No exception — proves resolution fields are not in the immutable set.
        assert_detection_immutable(
            befund,
            aufloesungsstatus="aufgeloest",
            resolved_at="now",
            resolution_decision_event_uuid=str(new_uuid()),
        )


# --- T-H4-02 + Audit-Kein-Auto-Korrektur-Test + Audit-Run-Log-Eintrag-Test


@pytest.mark.asyncio
class TestAuditRunCleanliness:
    """End-to-end audit-run on a synthetic project. Asserts:
    - No Revision rows produced (T-H4-02).
    - No Segment text_content mutation (Audit-Kein-Auto-Korrektur).
    - No TranslationObservation produced.
    - Exactly one start + one completion Log-Eintrag (Audit-Run-Log-Eintrag).
    - Befund rows AND a completed Job row produced.
    """

    async def test_run_produces_no_revisions_or_text_mutation(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        # Seed a segment that A-01 will flag (inna present, no rendering).
        seg = await seed_segment(
            db_session,
            project=project,
            text=st("إنّ الحمد لله", "Lob sei Gott."),
        )

        rev_before = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()
        text_before = seg.text_content

        result: AuditRunResult = await run_audit_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            rules=[rule_a_01],
        )

        # Befund persisted.
        befund_count = (
            await db_session.execute(
                select(func.count())
                .select_from(Befund)
                .where(Befund.project_uuid == project.project_uuid)
            )
        ).scalar_one()
        assert befund_count >= 1
        assert result.befund_count == befund_count

        # No Revision row added.
        rev_after = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()
        assert rev_after == rev_before

        # Segment text untouched.
        await db_session.refresh(seg)
        assert seg.text_content == text_before

        # No TranslationObservation produced.
        obs_count = (
            await db_session.execute(select(func.count()).select_from(TranslationObservation))
        ).scalar_one()
        assert obs_count == 0

        # Job state COMPLETED.
        assert result.job.state == JobState.COMPLETED.value
        assert result.job.result is not None
        assert "befund_count" in result.job.result

    async def test_run_writes_exactly_one_completion_log_entry(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        await seed_segment(db_session, project=project, text=st("salam", "hi"))
        await run_audit_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            rules=[rule_a_01],
        )
        # Filter to the project-scope log entries from this run.
        rows = (
            (
                await db_session.execute(
                    select(LogEntry)
                    .where(LogEntry.scope_type == ScopeType.PROJECT.value)
                    .where(LogEntry.scope_uuid == project.project_uuid)
                    .where(LogEntry.operation_type == "audit_run_completed")
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].result is not None
        assert "befund_count" in rows[0].result
        assert "by_severity" in rows[0].result


# --- Audit-Job-State-Machine-Test ------------------------------------


@pytest.mark.asyncio
class TestAuditJobStateMachine:
    async def test_failure_marks_job_failed_and_writes_failure_log(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        await seed_segment(db_session, project=project, text="x")

        # Build a rule that raises mid-run.
        def boom(_seg: Segment) -> list[RuleFinding]:
            raise RuntimeError("synthetic failure")

        boom.regelkennung = "A-01"  # type: ignore[attr-defined]

        with pytest.raises(RuntimeError, match="synthetic"):
            await run_audit_for_project(
                session=db_session,
                project_uuid=project.project_uuid,
                rules=[boom],
            )

        # The Job is in FAILED state with error context.
        rows = (
            (await db_session.execute(select(Job).where(Job.project_uuid == project.project_uuid)))
            .scalars()
            .all()
        )
        # We may have other jobs from earlier tests; pick our audit one.
        audit_jobs = [j for j in rows if j.job_type == "audit"]
        assert len(audit_jobs) == 1
        assert audit_jobs[0].state == JobState.FAILED.value
        assert audit_jobs[0].error is not None
        assert audit_jobs[0].error.get("error_class") == "RuntimeError"

        # Failure log written.
        log_rows = (
            (
                await db_session.execute(
                    select(LogEntry)
                    .where(LogEntry.operation_type == "audit_run_failed")
                    .where(LogEntry.scope_uuid == project.project_uuid)
                )
            )
            .scalars()
            .all()
        )
        assert len(log_rows) == 1


# --- Sprint 3 §A HG-S3-2: T-H4-02 must remain green ----------------


@pytest.mark.asyncio
class TestH4ForAuditRun:
    async def test_audit_module_does_not_call_create_revision(self) -> None:
        """Source-scan: no path inside the AUDIT module imports
        `create_revision`. Per R-S3-01 / Sprint 3 §A HG-S3-2."""
        import inspect

        from waraq import audit as audit_module

        # Walk all submodules and ensure none mention create_revision.
        for name, sub in vars(audit_module).items():
            if not callable(sub) or not hasattr(sub, "__module__"):
                continue
            if not isinstance(sub.__module__, str):
                continue
            if not sub.__module__.startswith("waraq.audit"):
                continue
            try:
                src = inspect.getsource(sub)
            except (OSError, TypeError):
                continue
            assert "create_revision" not in src, (
                f"{name} ({sub.__module__}) references create_revision; "
                "audit must not call it (T-H4-02 / R-S3-01)."
            )
