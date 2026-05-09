"""T-8.1.2 — Audit rule classification + resolution path tests.

Per Sprint 3 §4:
- Audit-A-Klasse-Hoch-Pflichthinweis-Test
- Audit-B-Klasse-Hoch-Pflichthinweis-Test
- Audit-C-Klasse-Kritisch-Blockierend-Test
- Audit-D-Klasse-Mittel-Hinweis-Test
- Audit-Severity-Konfigurations-Test
- Audit-Aufloesung-Decision-Event-Test
- Audit-Quittierung-Nur-Mittel-Test
- Audit-Kein-Auto-Quittierung-Test
- Audit-Findings-Stoppen-Translation-Flow-Nicht-Test
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment, st
from waraq.audit import (
    BefundAlreadyResolved,
    BefundNotResolvable,
    RuleFinding,
    SeverityEntry,
    SeverityTable,
    quittiere_befund,
    record_befund,
    resolve_befund,
    run_audit_for_project,
)
from waraq.audit.enums import AufloesungsStatus, Schweregrad, Verstossklasse
from waraq.audit.rules import (
    rule_a_01,
    rule_b_01,
    rule_c_01,
    rule_d_01,
)
from waraq.audit.severity import default_severity_table
from waraq.identity import new_uuid
from waraq.invariant.enums import OperationMode
from waraq.release_gate import start_translation
from waraq.revision import create_revision
from waraq.schemas import Befund, Job
from waraq.schemas.enums import (
    ChangeSource,
    DecisionSource,
    JobState,
    ScopeType,
)
from waraq.translation import TranslationContext, run_translation_job, start_translation_job

# --- Severity classification per class -------------------------------


@pytest.mark.asyncio
class TestSeverityClassification:
    async def test_a01_hoch_pflichthinweis(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await seed_segment(db_session, project=project, text=st("إنّ الحمد لله", "Lob sei Gott."))
        result = await run_audit_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            rules=[rule_a_01],
        )
        rows = (
            (await db_session.execute(select(Befund).where(Befund.regelkennung == "A-01")))
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].schweregrad == Schweregrad.HOCH.value
        assert rows[0].verstossklasse == Verstossklasse.PFLICHTHINWEIS.value
        assert result.by_severity[Schweregrad.HOCH.value] == 1

    async def test_b01_hoch_pflichthinweis(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        # idafa with pronoun suffix in source, no genitive in target.
        await seed_segment(
            db_session,
            project=project,
            text=st("كتابُهُ مفتوح", "Buch ist offen."),
        )
        await run_audit_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            rules=[rule_b_01],
        )
        rows = (
            (await db_session.execute(select(Befund).where(Befund.regelkennung == "B-01")))
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].schweregrad == Schweregrad.HOCH.value
        assert rows[0].verstossklasse == Verstossklasse.PFLICHTHINWEIS.value

    async def test_c01_kritisch_blockierend(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await seed_segment(
            db_session,
            project=project,
            text=st("source", "[TERM-VIOLATION] target"),
        )
        await run_audit_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            rules=[rule_c_01],
        )
        rows = (
            (await db_session.execute(select(Befund).where(Befund.regelkennung == "C-01")))
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].schweregrad == Schweregrad.KRITISCH.value
        assert rows[0].verstossklasse == Verstossklasse.BLOCKIEREND.value

    async def test_d01_mittel_hinweis(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await seed_segment(
            db_session,
            project=project,
            text=st("source", "Some [METAPHER] line."),
        )
        await run_audit_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            rules=[rule_d_01],
        )
        rows = (
            (await db_session.execute(select(Befund).where(Befund.regelkennung == "D-01")))
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].schweregrad == Schweregrad.MITTEL.value
        assert rows[0].verstossklasse == Verstossklasse.HINWEIS.value


# --- Audit-Severity-Konfigurations-Test ------------------------------


@pytest.mark.asyncio
class TestSeverityConfigurable:
    async def test_swap_severity_table_changes_classification(
        self, db_session: AsyncSession
    ) -> None:
        """Same finding, different SeverityTable → different classification.

        Demonstrates R-S3-04: severity is read from a configurable table,
        not hard-coded in rule bodies.
        """
        project = await seed_project(db_session)
        await seed_segment(db_session, project=project, text=st("إنّ الحمد لله", "Lob sei Gott."))

        # Default table classifies A-01 as Hoch / Pflichthinweis.
        await run_audit_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            rules=[rule_a_01],
            severity_table=default_severity_table(),
        )
        default_rows = (
            (await db_session.execute(select(Befund).where(Befund.regelkennung == "A-01")))
            .scalars()
            .all()
        )
        assert all(r.schweregrad == Schweregrad.HOCH.value for r in default_rows)

        # Swap to a "every rule is mittel/hinweis" table; rerun.
        flat_table = SeverityTable(
            entries={
                "A-01": SeverityEntry(
                    schweregrad=Schweregrad.MITTEL,
                    verstossklasse=Verstossklasse.HINWEIS,
                ),
            }
        )
        await run_audit_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            rules=[rule_a_01],
            severity_table=flat_table,
        )
        all_rows = (
            (await db_session.execute(select(Befund).where(Befund.regelkennung == "A-01")))
            .scalars()
            .all()
        )
        # The second run produced new rows classified at the lower severity.
        new_rows = [r for r in all_rows if r.schweregrad == Schweregrad.MITTEL.value]
        assert len(new_rows) >= 1
        assert all(r.verstossklasse == Verstossklasse.HINWEIS.value for r in new_rows)


# --- Audit-Aufloesung-Decision-Event-Test ----------------------------


@pytest.mark.asyncio
class TestResolveCreatesDecisionEvent:
    async def test_resolve_writes_decision_event_with_canonical_source(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(
            db_session, project=project, text=st("إنّ الحمد لله", "Lob sei Gott.")
        )
        await run_audit_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            rules=[rule_a_01],
        )
        befund = (
            await db_session.execute(
                select(Befund).where(Befund.satz_uuid == seg.satz_uuid).limit(1)
            )
        ).scalar_one()
        de = await resolve_befund(
            session=db_session,
            befund=befund,
            # Use the project's owning account so the FK is satisfied.
            actor_uuid=project.account_uuid,
            annotation="manual fix below",
        )
        assert de.decision_type == "audit_befund_aufgeloest"
        assert de.decision_source == DecisionSource.AUDIT_RESOLUTION.value
        assert de.scope_type == ScopeType.SEGMENT.value
        # Befund row stamped.
        await db_session.refresh(befund)
        assert befund.aufloesungsstatus == AufloesungsStatus.AUFGELOEST.value
        assert befund.resolution_decision_event_uuid == de.decision_event_uuid
        assert befund.resolved_at is not None


# --- Audit-Quittierung-Nur-Mittel-Test + Audit-Kein-Auto-Quittierung-


@pytest.mark.asyncio
class TestQuittierungOnlyMittel:
    async def _seed_befund(
        self,
        db_session: AsyncSession,
        *,
        regelkennung: str,
        target_text: str,
    ) -> Befund:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text=st("إنّ الحمد لله", target_text))
        job = Job(job_uuid=new_uuid(), job_type="audit", state=JobState.PENDING.value)
        db_session.add(job)
        await db_session.flush()
        return await record_befund(
            session=db_session,
            finding=RuleFinding(
                regelkennung=regelkennung,
                satz_uuid=seg.satz_uuid,
                detection_context={},
            ),
            project_uuid=project.project_uuid,
            audit_run_job_uuid=job.job_uuid,
            severity_table=default_severity_table(),
        )

    async def test_quittiere_kritisch_refused(self, db_session: AsyncSession) -> None:
        # C-01 → Kritisch.
        b = await self._seed_befund(
            db_session,
            regelkennung="C-01",
            target_text="Lob sei Gott.",
        )
        with pytest.raises(BefundNotResolvable):
            await quittiere_befund(session=db_session, befund=b)

    async def test_quittiere_hoch_refused(self, db_session: AsyncSession) -> None:
        # A-01 → Hoch.
        b = await self._seed_befund(
            db_session,
            regelkennung="A-01",
            target_text="Lob sei Gott.",
        )
        with pytest.raises(BefundNotResolvable):
            await quittiere_befund(session=db_session, befund=b)

    async def test_quittiere_mittel_permitted_writes_de(self, db_session: AsyncSession) -> None:
        # D-01 → Mittel.
        b = await self._seed_befund(
            db_session,
            regelkennung="D-01",
            target_text="Lob sei Gott.",
        )
        de = await quittiere_befund(
            session=db_session,
            befund=b,
            annotation="acknowledged without change",
        )
        assert de.decision_type == "audit_befund_quittiert"
        assert de.decision_source == DecisionSource.AUDIT_RESOLUTION.value

    async def test_no_auto_quittierung_module_surface(self) -> None:
        """Audit-Kein-Auto-Quittierung-Test: only `quittiere_befund` is the
        public path. No "auto" entry in the public module API."""
        from waraq import audit as audit_module

        for name in audit_module.__all__:
            assert "auto" not in name.lower(), (
                f"AUDIT module exports {name!r} which contains 'auto'; "
                "Audit-Kein-Auto-Quittierung-Test forbids any auto path."
            )

    async def test_double_resolve_refused(self, db_session: AsyncSession) -> None:
        b = await self._seed_befund(db_session, regelkennung="D-01", target_text="x")
        await quittiere_befund(session=db_session, befund=b)
        # Second call must refuse.
        with pytest.raises(BefundAlreadyResolved):
            await resolve_befund(session=db_session, befund=b)


# --- Audit-Findings-Stoppen-Translation-Flow-Nicht-Test --------------


@pytest.mark.asyncio
class TestFindingsDoNotStopTranslation:
    async def test_translation_runs_to_completion_with_pending_findings(
        self, db_session: AsyncSession
    ) -> None:
        """Pre-existing findings must not break a translation job."""
        project = await seed_project(db_session)
        seg = await seed_segment(
            db_session, project=project, text=st("إنّ الحمد لله", "Lob sei Gott.")
        )
        # Generate a finding before the translation runs.
        await run_audit_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            rules=[rule_a_01],
        )
        befund_count = (await db_session.execute(select(Befund))).scalars().all()
        assert len(befund_count) >= 1

        # Now run a translation job — must complete normally.
        await start_translation(
            session=db_session,
            project_uuid=project.project_uuid,
        )
        # Reset segment text to a clean source for translation.
        await create_revision(
            session=db_session,
            segment=seg,
            after_text="بسم الله",
            change_source=ChangeSource.OCR,
            operation_mode=OperationMode.AUTOMATIC,
        )
        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[seg.satz_uuid],
        )

        async def _translator(input_text: str, _ctx: TranslationContext) -> str:
            return f"DE: {input_text}"

        result = await run_translation_job(
            session=db_session,
            job=job,
            translator=_translator,
        )
        # Job completed normally despite outstanding Befund rows.
        assert result.job.state == JobState.COMPLETED.value
