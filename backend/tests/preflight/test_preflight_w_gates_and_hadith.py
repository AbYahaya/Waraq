"""T-9.1.2 mandatory tests — Sprint 4 §4 W-gates + Hadith + warnings state.

Test ID coverage:
- W-01-Mittel-Warnung-Test
- W-01-Quittiert-Drops-Out-Test
- W-02-Konsistenz-Warnung-Test
- W-03-Graduelle-Formatvorlagen-Test
- Hadith-H2-Blockiert-Test
- Hadith-H1-Warnung-go-with-warning-Test
- Hadith-H0-Kein-Gate-Trigger-Test
- Hadith-Eigene-Gruppe-Kein-P-W-Slot-Test
- Exportierbar-Mit-Warnungen-Per-Gate-Confirmation-Test
- Pflichthinweis-Nicht-Als-W-Klasse-Test
- Konsistenz-Routing-W02-vs-P03-Test
- Konsistenz-Engine-Job-State-Test
- Kein-Stiller-Slot-Fill-P01-P02-P05-P06-Test
- Kein-Stiller-Slot-Fill-W04-W05-W06-W07-W08-Test
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment
from tests.preflight._helpers import (
    seed_audit_job,
    seed_befund,
    seed_hadith,
    seed_konsistenz_befund,
)
from waraq.audit.service import quittiere_befund
from waraq.consistency import KRuleId, register_real_k_rules, run_consistency_check
from waraq.preflight import (
    HADITH_ACTION_TYPES,
    BlockingReason,
    PreflightState,
    accept_warning_gate,
    confirm_pflichtfrage,
    evaluate_preflight,
    go_with_warning_hadith,
    resolve_hadith_h2,
    start_preflight_run,
)
from waraq.preflight.enums import HadithKlasse, HadithStellenTyp, WarningSlot
from waraq.preflight.exceptions import PflichthinweisCannotBeWarning
from waraq.preflight.hadith import derive_hadith_klasse
from waraq.preflight.service import (
    assert_pflichthinweis_not_routed_as_warning,
)
from waraq.schemas import DecisionEvent, Job
from waraq.schemas.enums import DecisionSource, JobState


@pytest.fixture(autouse=True)
def _register_real_k_rules() -> None:
    register_real_k_rules()


async def _confirm_all_four(
    session: AsyncSession,
    *,
    project_uuid,
    preflight_run,
):
    for i in range(1, 5):
        await confirm_pflichtfrage(
            session=session,
            project_uuid=project_uuid,
            preflight_run_uuid=preflight_run.job_uuid,
            frage_index=i,
            frage_key=f"frage_{i}",
            answer={"value": "yes"},
        )


# --- W-01-Mittel-Warnung-Test + W-01-Quittiert-Drops-Out-Test --------


@pytest.mark.asyncio
class TestW01MittelAudit:
    async def test_open_mittel_befund_routes_to_w_01(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        audit_job = await seed_audit_job(db_session, project=project)
        # D-01 is mittel per default severity table.
        befund = await seed_befund(
            db_session,
            project=project,
            segment=seg,
            audit_job=audit_job,
            regelkennung="D-01",
        )
        assert befund.schweregrad == "mittel"
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert WarningSlot.W_01_MITTEL_AUDIT in ev.open_warning_slots

    async def test_quittierter_mittel_drops_out_of_w_01(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        audit_job = await seed_audit_job(db_session, project=project)
        befund = await seed_befund(
            db_session,
            project=project,
            segment=seg,
            audit_job=audit_job,
            regelkennung="D-01",
        )
        # Quittiere it (mittel-severity allows quittierung).
        await quittiere_befund(session=db_session, befund=befund)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert WarningSlot.W_01_MITTEL_AUDIT not in ev.open_warning_slots
        assert ev.w_01_mittel_befund_uuids == []


# --- W-02-Konsistenz-Warnung-Test ------------------------------------


@pytest.mark.asyncio
class TestW02Konsistenz:
    async def test_open_konsistenz_routes_to_w_02_when_not_kritisch(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        kbf = await seed_konsistenz_befund(
            db_session,
            project=project,
            k_rule="K-01",
            subject_type="concept_id",
            subject_key="x",
            verstossklasse="mittel",
        )
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert WarningSlot.W_02_KONSISTENZ in ev.open_warning_slots
        assert kbf.konsistenz_befund_uuid in ev.w_02_konsistenz_befund_uuids


# --- W-03-Graduelle-Formatvorlagen-Test ------------------------------


@pytest.mark.asyncio
class TestW03Formatvorlagen:
    async def test_graduelle_formatvorlagen_routes_to_w_03(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev = await evaluate_preflight(
            session=db_session,
            project_uuid=project.project_uuid,
            preflight_run=run,
            formatvorlagen_graduelle_keys=[
                "heading_3_spacing_drift",
                "footnote_marker_style_drift",
            ],
        )
        assert WarningSlot.W_03_FORMATVORLAGEN_GRADUELL in ev.open_warning_slots
        assert "heading_3_spacing_drift" in ev.w_03_formatvorlagen_finding_keys


# --- Hadith-H2-Blockiert-Test ----------------------------------------


@pytest.mark.asyncio
class TestHadithH2:
    async def test_h2_blocks_via_hadith_group_not_via_p_or_w_slot(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        had = await seed_hadith(
            db_session, project=project, segment=seg, stellen_typ=HadithStellenTyp.N_5
        )
        assert derive_hadith_klasse("N-5") == HadithKlasse.H_2
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert ev.state == PreflightState.BLOCKIERT
        assert BlockingReason.HADITH_H2 in ev.blocking_reasons
        assert had.hadith_status_uuid in ev.hadith_h2_status_uuids
        # Hadith does NOT occupy any P-Slot (must be its own group code).
        assert BlockingReason.P_03_KRITISCH not in ev.blocking_reasons
        assert BlockingReason.P_04_HOCH_PFLICHTHINWEIS not in ev.blocking_reasons


# --- Hadith-H1-Warnung-go-with-warning-Test --------------------------


@pytest.mark.asyncio
class TestHadithH1:
    async def test_h1_supports_go_with_warning_writes_preflight_confirmation_de(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        had = await seed_hadith(
            db_session, project=project, segment=seg, stellen_typ=HadithStellenTyp.N_2
        )
        assert derive_hadith_klasse("N-2") == HadithKlasse.H_1

        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev_before = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert WarningSlot.HADITH_H1 in ev_before.open_warning_slots

        de = await go_with_warning_hadith(session=db_session, status=had)
        assert de.decision_source == DecisionSource.PREFLIGHT_CONFIRMATION.value
        assert de.decision_type == "hadith_go_with_warning"

        await db_session.refresh(had)
        assert had.state == "quittiert"

        ev_after = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert WarningSlot.HADITH_H1 not in ev_after.open_warning_slots


# --- Hadith-H0-Kein-Gate-Trigger-Test --------------------------------


@pytest.mark.asyncio
class TestHadithH0:
    async def test_h0_does_not_contribute_to_gate(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        await seed_hadith(
            db_session, project=project, segment=seg, stellen_typ=HadithStellenTyp.N_1
        )
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert ev.state == PreflightState.EXPORTIERBAR
        assert ev.hadith_h2_status_uuids == []
        assert ev.hadith_h1_status_uuids == []
        assert WarningSlot.HADITH_H1 not in ev.open_warning_slots


# --- Hadith-Eigene-Gruppe-Kein-P-W-Slot-Test (HG-S4-5) ---------------


class TestHadithEigeneGruppe:
    """Code-level: Hadith group is its own benannte Gruppe — its
    blocking reason is the dedicated `HADITH_H2` enum value, NOT a
    P-Slot value. Its warning slot is `HADITH_H1`, NOT a W-04..W-08
    placement."""

    def test_hadith_h2_blocking_reason_is_distinct(self) -> None:
        assert BlockingReason.HADITH_H2.value == "hadith_h2"
        assert BlockingReason.HADITH_H2 not in {
            BlockingReason.P_03_KRITISCH,
            BlockingReason.P_04_HOCH_PFLICHTHINWEIS,
            BlockingReason.KONFIGURATIONSSCHICHT_UNVOLLSTAENDIG,
        }

    def test_hadith_h1_warning_slot_is_distinct_from_w_xx(self) -> None:
        assert WarningSlot.HADITH_H1.value == "hadith_h1"
        for ws in WarningSlot:
            if ws == WarningSlot.HADITH_H1:
                continue
            assert ws.value.startswith("w_")

    def test_seven_canonical_action_types(self) -> None:
        """Per §4.16.5: seven action types, each maps to an existing
        decision_source value (no new sources)."""
        assert len(HADITH_ACTION_TYPES) == 7
        existing_sources = {DecisionSource.TRANSLATION_PIPELINE, DecisionSource.CONFLICT_RESOLUTION}
        for v in HADITH_ACTION_TYPES.values():
            assert v in existing_sources


@pytest.mark.asyncio
class TestHadithH2Resolution:
    async def test_h2_resolution_via_action_type_writes_correct_de(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        had = await seed_hadith(
            db_session, project=project, segment=seg, stellen_typ=HadithStellenTyp.N_5
        )
        de = await resolve_hadith_h2(
            session=db_session,
            status=had,
            action_type="autorenwortlaut_beibehalten",
        )
        # Action type maps to conflict_resolution per §4.16.5.
        assert de.decision_source == DecisionSource.CONFLICT_RESOLUTION.value
        assert de.decision_type == "hadith_autorenwortlaut_beibehalten"
        await db_session.refresh(had)
        assert had.state == "aufgeloest"

    async def test_h2_unknown_action_type_refused(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        had = await seed_hadith(
            db_session, project=project, segment=seg, stellen_typ=HadithStellenTyp.N_5
        )
        with pytest.raises(ValueError, match="not one of the 7 canonical"):
            await resolve_hadith_h2(
                session=db_session,
                status=had,
                action_type="invented_action",
            )


# --- Exportierbar-Mit-Warnungen-Per-Gate-Confirmation-Test -----------


@pytest.mark.asyncio
class TestExportierbarMitWarnungen:
    async def test_state_blockiert_until_each_warning_accepted(
        self, db_session: AsyncSession
    ) -> None:
        """Two open warning slots → must accept both before transitioning."""
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        audit_job = await seed_audit_job(db_session, project=project)
        await seed_befund(
            db_session,
            project=project,
            segment=seg,
            audit_job=audit_job,
            regelkennung="D-01",  # mittel → W-01
        )
        await seed_konsistenz_befund(
            db_session,
            project=project,
            k_rule="K-01",
            subject_type="concept_id",
            subject_key="x",
            verstossklasse="mittel",  # not kritisch → W-02
        )
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)

        ev1 = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        # Two warnings open, none accepted → blockiert.
        assert ev1.state == PreflightState.BLOCKIERT
        assert WarningSlot.W_01_MITTEL_AUDIT in ev1.open_warning_slots
        assert WarningSlot.W_02_KONSISTENZ in ev1.open_warning_slots

        # Accept ONLY W-01.
        await accept_warning_gate(
            session=db_session,
            project_uuid=project.project_uuid,
            preflight_run=run,
            warning_slot=WarningSlot.W_01_MITTEL_AUDIT,
        )
        ev2 = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        # Still blockiert (W-02 unaccepted).
        assert ev2.state == PreflightState.BLOCKIERT

        # Accept W-02.
        await accept_warning_gate(
            session=db_session,
            project_uuid=project.project_uuid,
            preflight_run=run,
            warning_slot=WarningSlot.W_02_KONSISTENZ,
        )
        ev3 = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        assert ev3.state == PreflightState.EXPORTIERBAR_MIT_WARNUNGEN

    async def test_bulk_accept_writes_n_distinct_decision_events(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)

        # Simulate a bulk-accept UX: caller iterates warning slots and
        # writes one DE per slot.
        for slot in (WarningSlot.W_01_MITTEL_AUDIT, WarningSlot.W_02_KONSISTENZ):
            await accept_warning_gate(
                session=db_session,
                project_uuid=project.project_uuid,
                preflight_run=run,
                warning_slot=slot,
            )

        rows = (
            (
                await db_session.execute(
                    select(DecisionEvent)
                    .where(DecisionEvent.related_export_attempt_id == str(run.job_uuid))
                    .where(
                        DecisionEvent.decision_source == DecisionSource.PREFLIGHT_CONFIRMATION.value
                    )
                )
            )
            .scalars()
            .all()
        )
        warning_acceptance_des = [
            r for r in rows if r.decision_type.startswith("preflight_warning_accepted_")
        ]
        assert len(warning_acceptance_des) == 2
        slots_in_des = {de.content.get("warning_slot") for de in warning_acceptance_des}
        assert slots_in_des == {"w_01_mittel_audit", "w_02_konsistenz"}


# --- Pflichthinweis-Nicht-Als-W-Klasse-Test (HG-S4-4) ----------------


class TestPflichthinweisNeverAsWarning:
    """Per Sprint 4 R-S4-05: P-04 must not be routed into W-XX. Two
    structural enforcements:
    1) `WarningSlot` enum has no P-04 entry.
    2) `assert_pflichthinweis_not_routed_as_warning` refuses string
       slot identifiers that look like P-04 routing.
    """

    def test_warning_slot_enum_has_no_p_04(self) -> None:
        for ws in WarningSlot:
            assert "p_04" not in ws.value
            assert "pflichthinweis" not in ws.value

    def test_assert_pflichthinweis_guard_rejects_p_04_strings(self) -> None:
        for slot in ("p_04_anything", "p_04_hoch_pflichthinweis"):
            with pytest.raises(PflichthinweisCannotBeWarning):
                assert_pflichthinweis_not_routed_as_warning(slot)

    def test_blocking_reason_p_04_is_separate_from_warnings(self) -> None:
        # The structural separation enforced by the BlockingReason enum
        # itself: P-04 is in BlockingReason, not WarningSlot.
        assert BlockingReason.P_04_HOCH_PFLICHTHINWEIS.value == "p_04_hoch_pflichthinweis"
        warning_values = {w.value for w in WarningSlot}
        assert BlockingReason.P_04_HOCH_PFLICHTHINWEIS.value not in warning_values


# --- Konsistenz-Routing-W02-vs-P03-Test ------------------------------


@pytest.mark.asyncio
class TestKonsistenzRouting:
    async def test_kritisch_konsistenz_to_p03_else_w02(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        kbf_kritisch = await seed_konsistenz_befund(
            db_session,
            project=project,
            k_rule="K-01",
            subject_type="concept_id",
            subject_key="kritisch_one",
            verstossklasse="kritisch",
        )
        kbf_mittel = await seed_konsistenz_befund(
            db_session,
            project=project,
            k_rule="K-02",
            subject_type="formel_verzeichnis_id",
            subject_key="mittel_one",
            verstossklasse="mittel",
        )
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        await _confirm_all_four(db_session, project_uuid=project.project_uuid, preflight_run=run)
        ev = await evaluate_preflight(
            session=db_session, project_uuid=project.project_uuid, preflight_run=run
        )
        # Kritisch → P-03; mittel → W-02. The routing is computed at
        # evaluation, NOT stored on the row.
        assert kbf_kritisch.konsistenz_befund_uuid in ev.p_03_konsistenz_befund_uuids
        assert kbf_mittel.konsistenz_befund_uuid in ev.w_02_konsistenz_befund_uuids
        # And no row appears in both buckets.
        assert kbf_kritisch.konsistenz_befund_uuid not in ev.w_02_konsistenz_befund_uuids
        assert kbf_mittel.konsistenz_befund_uuid not in ev.p_03_konsistenz_befund_uuids


# --- Konsistenz-Engine-Job-State-Test --------------------------------


@pytest.mark.asyncio
class TestKonsistenzEngineJobState:
    async def test_consistency_run_uses_canonical_job_state_machine(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        job, _findings = await run_consistency_check(
            session=db_session,
            project_uuid=project.project_uuid,
            rule_ids=[KRuleId.K_01],
        )
        assert job.state == JobState.COMPLETED.value
        assert job.job_type == "consistency"
        # Canonical state machine: a fresh job moves PENDING → RUNNING → COMPLETED.
        # Failures must not auto-retry — the engine writes FAILED and re-raises.

    async def test_consistency_failure_writes_failed_state(self, db_session: AsyncSession) -> None:
        from waraq.consistency import register_k_rule

        project = await seed_project(db_session)

        # Ad-hoc rule that raises mid-run.
        async def boom(*, session, project_uuid):
            raise RuntimeError("synthetic")

        register_k_rule(KRuleId.K_01, boom)  # type: ignore[arg-type]

        with pytest.raises(RuntimeError, match="synthetic"):
            await run_consistency_check(
                session=db_session,
                project_uuid=project.project_uuid,
                rule_ids=[KRuleId.K_01],
            )

        rows = (
            (
                await db_session.execute(
                    select(Job)
                    .where(Job.project_uuid == project.project_uuid)
                    .where(Job.job_type == "consistency")
                )
            )
            .scalars()
            .all()
        )
        assert any(j.state == JobState.FAILED.value for j in rows)


# --- Kein-Stiller-Slot-Fill tests (HG-S4-3) --------------------------


class TestKeinStillerSlotFill:
    """Per Sprint 4 §A HG-S4-3: P-01/P-02/P-05/P-06 and W-04..W-08 are
    explicitly **offen**. Code paths that name those slots are canon
    violations per Dokument 2 §6."""

    def test_blocking_reason_enum_lists_only_belegte_p_slots(self) -> None:
        # P-03 + P-04 are belegt; the 4 open slots must NOT be present.
        all_values = {b.value for b in BlockingReason}
        forbidden = {"p_01", "p_02", "p_05", "p_06"}
        for f in forbidden:
            for v in all_values:
                assert f not in v, f"BlockingReason {v!r} mentions forbidden slot {f}"

    def test_warning_slot_enum_lists_only_belegte_w_slots(self) -> None:
        all_values = {w.value for w in WarningSlot}
        forbidden = {"w_04", "w_05", "w_06", "w_07", "w_08"}
        for f in forbidden:
            for v in all_values:
                assert f not in v, f"WarningSlot {v!r} mentions forbidden slot {f}"

    def test_preflight_service_source_does_not_reference_open_slots(self) -> None:
        from waraq.preflight import service as preflight_service

        src = inspect.getsource(preflight_service)
        for forbidden in ("P_01", "P_02", "P_05", "P_06"):
            assert forbidden not in src
        for forbidden in ("W_04", "W_05", "W_06", "W_07", "W_08"):
            assert forbidden not in src
