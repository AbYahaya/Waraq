"""T-9.1.1 mandatory tests — Sprint 4 §4 Konfigurationsschicht + P-gates.

Test ID coverage:
- Pflichtfrage-Active-Confirmation-Required-Test
- Pflichtfrage-Decision-Event-preflight-confirmation-Test
- Pflichtfrage-Profile-Prefills-But-Not-Replaces-Test
- P-03-Kritisch-Audit-Blockierung-Test
- P-03-Kritisch-OCR-Fehlerklasse-Carry-Forward-Test
- P-03-Kritisch-Konsistenz-Test
- P-04-Hoch-Pflichthinweis-Blockierung-Test
- P-03-P-04-Strukturell-Distinct-Test
- Exportlauf-Ereignis-Immer-Test
- Pflichtfrage-Konfigurationsschicht-Kein-P-Slot-Test
- Preflight-State-Machine-Blockiert-Exportierbar-Test
- Preflight-Kein-Auto-Aufloesung-Test
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment
from tests.preflight._helpers import (
    canonical_pflichtfrage_payload,
    seed_audit_job,
    seed_befund,
    seed_hadith,
    seed_konsistenz_befund,
    seed_ocr_error,
)
from waraq.preflight import (
    PFLICHTFRAGE_COUNT,
    BlockingReason,
    PreflightState,
    confirm_pflichtfrage,
    evaluate_preflight,
    save_export_profile_prefill,
    start_preflight_run,
)
from waraq.preflight.enums import HadithStellenTyp, WarningSlot
from waraq.schemas import DecisionEvent, LogEntry
from waraq.schemas.enums import DecisionSource, ScopeType


async def _confirm_all_four(
    session: AsyncSession,
    *,
    project_uuid,
    preflight_run,
):
    for i in range(1, PFLICHTFRAGE_COUNT + 1):
        key, ans = canonical_pflichtfrage_payload(i)
        await confirm_pflichtfrage(
            session=session,
            project_uuid=project_uuid,
            preflight_run_uuid=preflight_run.job_uuid,
            frage_index=i,
            frage_key=key,
            answer=ans,
        )


# --- Pflichtfrage-Active-Confirmation-Required-Test ------------------


@pytest.mark.asyncio
class TestPflichtfrageActiveConfirmationRequired:
    async def test_export_blocked_when_no_pflichtfragen_confirmed(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert ev.state == PreflightState.BLOCKIERT
        assert BlockingReason.KONFIGURATIONSSCHICHT_UNVOLLSTAENDIG in ev.blocking_reasons
        assert ev.konfigurationsschicht_complete is False
        assert ev.pflichtfrage_active_count == 0

    async def test_partial_confirmations_still_block(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        # Only confirm 2 out of 4.
        for i in (1, 2):
            key, ans = canonical_pflichtfrage_payload(i)
            await confirm_pflichtfrage(
                session=db_session,
                project_uuid=project.project_uuid,
                preflight_run_uuid=run.job_uuid,
                frage_index=i,
                frage_key=key,
                answer=ans,
            )
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert ev.state == PreflightState.BLOCKIERT
        assert BlockingReason.KONFIGURATIONSSCHICHT_UNVOLLSTAENDIG in ev.blocking_reasons

    async def test_full_confirmations_unblock_konfiguration(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert ev.konfigurationsschicht_complete is True
        assert ev.pflichtfrage_active_count == 4
        assert BlockingReason.KONFIGURATIONSSCHICHT_UNVOLLSTAENDIG not in ev.blocking_reasons
        # No findings either → exportierbar.
        assert ev.state == PreflightState.EXPORTIERBAR


# --- Pflichtfrage-Decision-Event-preflight-confirmation-Test ---------


@pytest.mark.asyncio
class TestPflichtfrageDecisionEventShape:
    async def test_each_confirmation_writes_correct_decision_event(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        rows = (
            (
                await db_session.execute(
                    select(DecisionEvent)
                    .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
                    .where(DecisionEvent.scope_uuid == project.project_uuid)
                    .where(DecisionEvent.decision_type == "pflichtfrage_bestaetigung")
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 4
        for de in rows:
            assert de.decision_source == DecisionSource.PREFLIGHT_CONFIRMATION.value
            assert de.related_export_attempt_id == str(run.job_uuid)


# --- Pflichtfrage-Profile-Prefills-But-Not-Replaces-Test -------------


@pytest.mark.asyncio
class TestProfilePrefillsButNotReplaces:
    async def test_profile_prefill_alone_does_not_satisfy_konfig(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        # Save a full set of profile pre-fills.
        for i in range(1, PFLICHTFRAGE_COUNT + 1):
            key, ans = canonical_pflichtfrage_payload(i)
            await save_export_profile_prefill(
                session=db_session,
                project_uuid=project.project_uuid,
                frage_index=i,
                frage_key=key,
                prefilled_answer=ans,
            )
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        # Pre-fills MUST NOT replace active confirmation.
        assert ev.state == PreflightState.BLOCKIERT
        assert BlockingReason.KONFIGURATIONSSCHICHT_UNVOLLSTAENDIG in ev.blocking_reasons
        assert ev.pflichtfrage_active_count == 0

    async def test_profile_plus_active_confirmation_unblocks(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        for i in range(1, PFLICHTFRAGE_COUNT + 1):
            key, ans = canonical_pflichtfrage_payload(i)
            await save_export_profile_prefill(
                session=db_session,
                project_uuid=project.project_uuid,
                frage_index=i,
                frage_key=key,
                prefilled_answer=ans,
            )
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert ev.konfigurationsschicht_complete is True
        assert ev.state == PreflightState.EXPORTIERBAR


# --- P-03-Kritisch-Audit-Blockierung-Test ----------------------------


@pytest.mark.asyncio
class TestP03KritischAudit:
    async def test_open_kritisch_audit_blocks_at_p_03(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        audit_job = await seed_audit_job(db_session, project=project)
        # C-01 / D-03 are kritisch per default severity table.
        befund = await seed_befund(
            db_session,
            project=project,
            segment=seg,
            audit_job=audit_job,
            regelkennung="C-01",
        )
        assert befund.schweregrad == "kritisch"

        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert ev.state == PreflightState.BLOCKIERT
        assert BlockingReason.P_03_KRITISCH in ev.blocking_reasons
        assert befund.befund_uuid in ev.p_03_kritisch_befund_uuids


# --- P-03-Kritisch-OCR-Fehlerklasse-Carry-Forward-Test ----------------


@pytest.mark.asyncio
class TestP03OcrCarryForward:
    async def test_unresolved_kritisch_ocr_error_blocks_at_p_03(
        self, db_session: AsyncSession
    ) -> None:
        from waraq.schemas import Block

        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        block = await db_session.get(Block, seg.block_uuid)
        # F-01 (api_authentication) is kritisch per default SeverityWeights.
        ocr_err = await seed_ocr_error(
            db_session,
            page_uuid=block.page_uuid,
            error_code="F-01",
        )

        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert ev.state == PreflightState.BLOCKIERT
        assert BlockingReason.P_03_KRITISCH in ev.blocking_reasons
        assert ocr_err.ocr_error_instance_uuid in ev.p_03_ocr_error_instance_uuids


# --- P-03-Kritisch-Konsistenz-Test -----------------------------------


@pytest.mark.asyncio
class TestP03Konsistenz:
    async def test_kritisch_konsistenz_routes_to_p_03(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        kbf = await seed_konsistenz_befund(
            db_session,
            project=project,
            k_rule="K-01",
            subject_type="concept_id",
            subject_key="x",
            verstossklasse="kritisch",
        )
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert BlockingReason.P_03_KRITISCH in ev.blocking_reasons
        assert kbf.konsistenz_befund_uuid in ev.p_03_konsistenz_befund_uuids
        # And it does NOT show up under W-02.
        assert kbf.konsistenz_befund_uuid not in ev.w_02_konsistenz_befund_uuids


# --- P-04-Hoch-Pflichthinweis-Blockierung-Test -----------------------


@pytest.mark.asyncio
class TestP04HochPflichthinweis:
    async def test_open_hoch_audit_blocks_at_p_04(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        audit_job = await seed_audit_job(db_session, project=project)
        # A-01 is hoch per default severity table.
        befund = await seed_befund(
            db_session,
            project=project,
            segment=seg,
            audit_job=audit_job,
            regelkennung="A-01",
        )
        assert befund.schweregrad == "hoch"
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert ev.state == PreflightState.BLOCKIERT
        assert BlockingReason.P_04_HOCH_PFLICHTHINWEIS in ev.blocking_reasons


# --- P-03-P-04-Strukturell-Distinct-Test -----------------------------


@pytest.mark.asyncio
class TestP03P04StructurallyDistinct:
    async def test_both_findings_yield_two_distinct_blocking_reasons(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        audit_job = await seed_audit_job(db_session, project=project)
        await seed_befund(
            db_session,
            project=project,
            segment=seg,
            audit_job=audit_job,
            regelkennung="C-01",
        )
        seg2 = await seed_segment(db_session, project=project, text="y", page_index=2, satz_index=1)
        await seed_befund(
            db_session,
            project=project,
            segment=seg2,
            audit_job=audit_job,
            regelkennung="A-01",
        )
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert BlockingReason.P_03_KRITISCH in ev.blocking_reasons
        assert BlockingReason.P_04_HOCH_PFLICHTHINWEIS in ev.blocking_reasons
        # Distinct enum members → distinct reason codes.
        assert BlockingReason.P_03_KRITISCH.value != BlockingReason.P_04_HOCH_PFLICHTHINWEIS.value


# --- Exportlauf-Ereignis-Immer-Test ----------------------------------


@pytest.mark.asyncio
class TestExportlaufEreignisAlways:
    async def test_every_evaluation_writes_log_entry(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        # Three evaluations under three outcomes: blocked (no confirms),
        # blocked (partial confirms), exportierbar (full confirms).
        await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        key1, ans1 = canonical_pflichtfrage_payload(1)
        await confirm_pflichtfrage(
            session=db_session,
            project_uuid=project.project_uuid,
            preflight_run_uuid=run.job_uuid,
            frage_index=1,
            frage_key=key1,
            answer=ans1,
        )
        await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        for i in (2, 3, 4):
            key, ans = canonical_pflichtfrage_payload(i)
            await confirm_pflichtfrage(
                session=db_session,
                project_uuid=project.project_uuid,
                preflight_run_uuid=run.job_uuid,
                frage_index=i,
                frage_key=key,
                answer=ans,
            )
        await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )

        rows = (
            (
                await db_session.execute(
                    select(LogEntry)
                    .where(LogEntry.operation_type == "preflight_evaluation")
                    .where(LogEntry.scope_uuid == project.project_uuid)
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 3


# --- Pflichtfrage-Konfigurationsschicht-Kein-P-Slot-Test -------------


@pytest.mark.asyncio
class TestKonfigurationsschichtKeinPSlot:
    async def test_konfig_failure_does_not_occupy_p_slot(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        # Konfigurationsschicht failure produces its own reason, NOT P-XX.
        assert BlockingReason.KONFIGURATIONSSCHICHT_UNVOLLSTAENDIG in ev.blocking_reasons
        # Without P-XX findings, those slots are empty.
        assert ev.p_03_kritisch_befund_uuids == []
        assert ev.p_04_hoch_befund_uuids == []
        # And the BlockingReason enum has the konfig reason as a SEPARATE
        # value from P-03 / P-04.
        konfig = BlockingReason.KONFIGURATIONSSCHICHT_UNVOLLSTAENDIG
        assert konfig != BlockingReason.P_03_KRITISCH
        assert konfig != BlockingReason.P_04_HOCH_PFLICHTHINWEIS


# --- Preflight-State-Machine-Blockiert-Exportierbar-Test -------------


@pytest.mark.asyncio
class TestPreflightStateMachine:
    async def test_state_transitions_per_spec(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)

        # 1) blockiert (no confirms)
        ev1 = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert ev1.state == PreflightState.BLOCKIERT

        # 2) confirms only → exportierbar (no findings)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev2 = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert ev2.state == PreflightState.EXPORTIERBAR

        # 3) Add a hoch finding → blockiert (P-04)
        seg = await seed_segment(db_session, project=project, text="x")
        audit_job = await seed_audit_job(db_session, project=project)
        await seed_befund(
            db_session,
            project=project,
            segment=seg,
            audit_job=audit_job,
            regelkennung="A-01",
        )
        ev3 = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert ev3.state == PreflightState.BLOCKIERT
        assert BlockingReason.P_04_HOCH_PFLICHTHINWEIS in ev3.blocking_reasons


# --- Preflight-Kein-Auto-Aufloesung-Test -----------------------------


@pytest.mark.asyncio
class TestPreflightNoAutoResolution:
    async def test_evaluator_does_not_auto_resolve_anything(self, db_session: AsyncSession) -> None:
        """The preflight evaluator reads state. It must not write
        Decision Events for Pflichtfragen, must not change Befund
        aufloesungsstatus, must not mutate Segments, must not flip
        Hadith state."""
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        audit_job = await seed_audit_job(db_session, project=project)
        befund = await seed_befund(
            db_session,
            project=project,
            segment=seg,
            audit_job=audit_job,
            regelkennung="A-01",
        )
        kbf = await seed_konsistenz_befund(
            db_session,
            project=project,
            k_rule="K-01",
            subject_type="concept_id",
            subject_key="x",
        )
        had = await seed_hadith(
            db_session, project=project, segment=seg, stellen_typ=HadithStellenTyp.N_5
        )

        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        await db_session.refresh(befund)
        await db_session.refresh(kbf)
        await db_session.refresh(had)
        assert befund.aufloesungsstatus == "offen"
        assert kbf.aufloesungsstatus == "offen"
        assert had.state == "offen"

        # No Pflichtfrage Decision Events should have been written by the evaluator.
        rows = (
            (
                await db_session.execute(
                    select(DecisionEvent)
                    .where(DecisionEvent.decision_type == "pflichtfrage_bestaetigung")
                    .where(DecisionEvent.related_export_attempt_id == str(run.job_uuid))
                )
            )
            .scalars()
            .all()
        )
        assert rows == []


# --- WarningSlot enum (HG-S4-3 Slot-Discipline) ----------------------


def test_warning_slot_enum_only_lists_belegte_slots() -> None:
    """Sprint 4 §A HG-S4-3: W-04..W-08 are explicitly offen. The
    WarningSlot enum must enumerate only the belegt slots."""
    values = {w.value for w in WarningSlot}
    # The enum must contain exactly the four belegt warning surfaces.
    assert values == {
        "w_01_mittel_audit",
        "w_02_konsistenz",
        "w_03_formatvorlagen_graduell",
        "hadith_h1",
    }
    forbidden_substrings = ("w_04", "w_05", "w_06", "w_07", "w_08")
    for v in values:
        for forbidden in forbidden_substrings:
            assert forbidden not in v
