"""T-8.2.1 — Consistency engine tests (M2-closeout shape).

The harness is real: registry, K-rule Protocol, Job lifecycle,
Konsistenz-Befund persistence, Decision-Event resolution + quittierung.

The K-rule **bodies** are stubs that return no findings; they back-fill
in M5. These tests exercise the harness end-to-end by registering ad-hoc
test rules that emit synthetic findings, plus verifying the stub
registration is itself a no-op.
"""

from __future__ import annotations

import inspect
import uuid as _uuid
from collections.abc import Iterable

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.consistency import (
    AufloesungsStatus,
    KConsistencyFinding,
    KonsistenzAlreadyClosed,
    KRuleId,
    SubjectType,
    Verstossklasse,
    quittiere_konsistenz_befund,
    register_k_rule,
    register_stub_k_rules,
    resolve_konsistenz_befund,
    run_consistency_check,
)
from waraq.consistency.engine import K_RULE_SUBJECT_TYPE
from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.schemas import (
    Block,
    DecisionEvent,
    Job,
    KonsistenzBefund,
    Page,
    Project,
    Segment,
)
from waraq.schemas.enums import DecisionSource, JobState, ScopeType


async def _seed_project_with_segments(
    session: AsyncSession, *, n_segments: int = 2
) -> tuple[Project, list[Segment]]:
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="consistency-test")
    session.add(project)
    await session.flush()

    page = Page(page_uuid=new_uuid(), project_uuid=project.project_uuid, page_index=1)
    session.add(page)
    await session.flush()

    block = Block(
        block_uuid=new_uuid(),
        page_uuid=page.page_uuid,
        block_type="main_text",
        block_index=1,
    )
    session.add(block)
    await session.flush()

    segments: list[Segment] = []
    for i in range(n_segments):
        seg = Segment(
            satz_uuid=new_uuid(),
            block_uuid=block.block_uuid,
            satz_index=i + 1,
            lock_flag=LockFlag.NONE,
            text_content=f"text-{i}",
        )
        session.add(seg)
        segments.append(seg)
    await session.flush()
    return project, segments


# --- Layer 1: K-rule taxonomy / subject_type discipline ------------------


class TestKRuleTaxonomy:
    """Sprint 4 §2 / DBB Abkürzung 10: each K-rule binds to its OWN
    subject_type. K-01 and K-07 share `concept_id` (cross-rule). No K-rule
    binds to surface_form."""

    def test_seven_canonical_k_rules(self) -> None:
        assert {r.value for r in KRuleId} == {
            "K-01",
            "K-02",
            "K-03",
            "K-04",
            "K-05",
            "K-06",
            "K-07",
        }

    def test_all_k_rules_have_subject_type(self) -> None:
        for rule in KRuleId:
            assert rule in K_RULE_SUBJECT_TYPE

    def test_k_rule_subject_type_table_matches_sprint4_spec(self) -> None:
        # Sprint 4 §2: K-01 / K-07 → concept_id; K-02 → formel_verzeichnis_id;
        # K-03 → entity_id; K-04 → transliterations_muster;
        # K-05 → source_identity; K-06 → structural_key.
        assert K_RULE_SUBJECT_TYPE[KRuleId.K_01] == SubjectType.CONCEPT_ID
        assert K_RULE_SUBJECT_TYPE[KRuleId.K_02] == SubjectType.FORMEL_VERZEICHNIS_ID
        assert K_RULE_SUBJECT_TYPE[KRuleId.K_03] == SubjectType.ENTITY_ID
        assert K_RULE_SUBJECT_TYPE[KRuleId.K_04] == SubjectType.TRANSLITERATIONS_MUSTER
        assert K_RULE_SUBJECT_TYPE[KRuleId.K_05] == SubjectType.SOURCE_IDENTITY
        assert K_RULE_SUBJECT_TYPE[KRuleId.K_06] == SubjectType.STRUCTURAL_KEY
        assert K_RULE_SUBJECT_TYPE[KRuleId.K_07] == SubjectType.CONCEPT_ID

    def test_no_subject_type_uses_surface_form(self) -> None:
        # DBB §B Abkürzung 10: K-rules must not be reduced to string equality.
        forbidden = {"surface_form", "text_content", "raw_string", "label_string"}
        for st in SubjectType:
            assert st.value not in forbidden


# --- Layer 1: stub registration is a no-op -------------------------------


@pytest.mark.asyncio
class TestStubKRules:
    """`register_stub_k_rules` registers no-op bodies for all 7 rules.
    Running the engine after stub-only registration produces zero findings."""

    async def test_running_with_only_stubs_produces_no_findings(
        self, db_session: AsyncSession
    ) -> None:
        register_stub_k_rules()
        project, _ = await _seed_project_with_segments(db_session)

        before = (
            await db_session.execute(select(func.count()).select_from(KonsistenzBefund))
        ).scalar_one()

        job, findings = await run_consistency_check(
            session=db_session, project_uuid=project.project_uuid
        )

        after = (
            await db_session.execute(select(func.count()).select_from(KonsistenzBefund))
        ).scalar_one()

        assert findings == []
        assert after == before
        assert job.state == JobState.COMPLETED.value
        assert job.result["findings_count"] == 0
        # All 7 rules ran (the rule_ids list defaults to every K-rule).
        assert set(job.payload["k_rule_ids"]) == {r.value for r in KRuleId}


# --- Layer 2: harness end-to-end with synthetic test rules ---------------


@pytest.mark.asyncio
class TestEngineEndToEndWithSyntheticRule:
    """Register a real (non-stub) K-rule body and assert the harness
    persists findings, transitions Job state, and writes Log-Einträge."""

    async def test_synthetic_rule_findings_are_persisted_with_subject_type(
        self, db_session: AsyncSession
    ) -> None:
        project, segments = await _seed_project_with_segments(db_session, n_segments=3)
        concept_id_uuid = new_uuid()

        async def _synthetic_k01_rule(
            *, session: AsyncSession, project_uuid: _uuid.UUID
        ) -> Iterable[KConsistencyFinding]:
            # Emit one mittel-class K-01 finding spanning all three Segments.
            return [
                KConsistencyFinding(
                    k_rule=KRuleId.K_01,
                    subject_key=str(concept_id_uuid),
                    verstossklasse=Verstossklasse.MITTEL,
                    betroffene_segment_uuids=[s.satz_uuid for s in segments],
                    vorschlag={
                        "action": "use_canonical_rendering",
                        "concept_id": str(concept_id_uuid),
                        "preferred_rendering": "Hadith-Kritiker",
                    },
                )
            ]

        register_stub_k_rules()
        register_k_rule(KRuleId.K_01, _synthetic_k01_rule)
        try:
            job, findings = await run_consistency_check(
                session=db_session, project_uuid=project.project_uuid
            )
        finally:
            register_stub_k_rules()  # restore the stubs for other tests

        assert job.state == JobState.COMPLETED.value
        assert len(findings) == 1
        finding = findings[0]
        assert finding.k_rule == KRuleId.K_01.value
        assert finding.subject_type == SubjectType.CONCEPT_ID.value
        assert finding.subject_key == str(concept_id_uuid)
        assert finding.verstossklasse == Verstossklasse.MITTEL.value
        assert finding.aufloesungsstatus == AufloesungsStatus.OFFEN.value
        assert finding.resolution_decision_event_uuid is None
        assert finding.resolved_at is None
        assert len(finding.betroffene_segment_uuids) == 3
        assert finding.vorschlag["preferred_rendering"] == "Hadith-Kritiker"
        # Job carries the rule id list and the count.
        assert job.result["findings_count"] == 1

    async def test_engine_refuses_finding_tagged_with_wrong_k_rule(
        self, db_session: AsyncSession
    ) -> None:
        # If a rule emits a finding tagged under a different KRuleId, the
        # engine must refuse — this catches accidental cross-binding bugs
        # (Sprint 4 §2 ticket-level risk).
        project, _ = await _seed_project_with_segments(db_session)

        async def _misbehaved_rule(
            *, session: AsyncSession, project_uuid: _uuid.UUID
        ) -> Iterable[KConsistencyFinding]:
            return [
                KConsistencyFinding(
                    k_rule=KRuleId.K_02,  # registered as K-01, but tags K-02
                    subject_key="x",
                    verstossklasse=Verstossklasse.MITTEL,
                )
            ]

        register_stub_k_rules()
        register_k_rule(KRuleId.K_01, _misbehaved_rule)
        try:
            with pytest.raises(ValueError, match="tagged with a different rule"):
                await run_consistency_check(session=db_session, project_uuid=project.project_uuid)
        finally:
            register_stub_k_rules()


# --- Layer 2: resolution paths --------------------------------------------


@pytest.mark.asyncio
class TestResolutionPaths:
    async def test_resolve_writes_decision_event_and_transitions_to_aufgeloest(
        self, db_session: AsyncSession
    ) -> None:
        project, _ = await _seed_project_with_segments(db_session)
        finding = KonsistenzBefund(
            konsistenz_befund_uuid=new_uuid(),
            project_uuid=project.project_uuid,
            k_rule=KRuleId.K_01.value,
            subject_type=SubjectType.CONCEPT_ID.value,
            subject_key=str(new_uuid()),
            verstossklasse=Verstossklasse.HOCH.value,
            betroffene_segment_uuids=[],
            vorschlag={"preferred_rendering": "X"},
        )
        db_session.add(finding)
        await db_session.flush()

        de = await resolve_konsistenz_befund(
            session=db_session,
            finding=finding,
            chosen_rendering={"preferred_rendering": "X"},
        )

        assert finding.aufloesungsstatus == AufloesungsStatus.AUFGELOEST.value
        assert finding.resolved_at is not None
        assert finding.resolution_decision_event_uuid == de.decision_event_uuid
        # DE shape per Sprint 4 §2:
        assert str(de.scope_type) == ScopeType.PROJECT.value
        assert de.scope_uuid == project.project_uuid
        assert de.decision_type == "konsistenzgruppe_verbindlich"
        assert str(de.decision_source) == DecisionSource.CONSISTENCY_RESOLUTION.value

    async def test_quittieren_only_for_mittel_class(self, db_session: AsyncSession) -> None:
        project, _ = await _seed_project_with_segments(db_session)

        # mittel-class finding → quittierung permitted.
        mittel = KonsistenzBefund(
            konsistenz_befund_uuid=new_uuid(),
            project_uuid=project.project_uuid,
            k_rule=KRuleId.K_04.value,
            subject_type=SubjectType.TRANSLITERATIONS_MUSTER.value,
            subject_key="pattern-A",
            verstossklasse=Verstossklasse.MITTEL.value,
            betroffene_segment_uuids=[],
            vorschlag={},
        )
        db_session.add(mittel)
        await db_session.flush()

        de = await quittiere_konsistenz_befund(session=db_session, finding=mittel)
        assert mittel.aufloesungsstatus == AufloesungsStatus.QUITTIERT.value
        assert mittel.resolution_decision_event_uuid == de.decision_event_uuid
        assert de.decision_type == "konsistenzbefund_quittiert"

        # hoch-class finding → quittierung refused.
        hoch = KonsistenzBefund(
            konsistenz_befund_uuid=new_uuid(),
            project_uuid=project.project_uuid,
            k_rule=KRuleId.K_05.value,
            subject_type=SubjectType.SOURCE_IDENTITY.value,
            subject_key="source-X",
            verstossklasse=Verstossklasse.HOCH.value,
            betroffene_segment_uuids=[],
            vorschlag={},
        )
        db_session.add(hoch)
        await db_session.flush()

        with pytest.raises(ValueError, match="only `mittel`-class findings"):
            await quittiere_konsistenz_befund(session=db_session, finding=hoch)

    async def test_second_resolution_raises(self, db_session: AsyncSession) -> None:
        project, _ = await _seed_project_with_segments(db_session)
        finding = KonsistenzBefund(
            konsistenz_befund_uuid=new_uuid(),
            project_uuid=project.project_uuid,
            k_rule=KRuleId.K_01.value,
            subject_type=SubjectType.CONCEPT_ID.value,
            subject_key="x",
            verstossklasse=Verstossklasse.MITTEL.value,
            betroffene_segment_uuids=[],
            vorschlag={},
        )
        db_session.add(finding)
        await db_session.flush()

        await resolve_konsistenz_befund(
            session=db_session, finding=finding, chosen_rendering={"x": 1}
        )

        with pytest.raises(KonsistenzAlreadyClosed):
            await resolve_konsistenz_befund(
                session=db_session, finding=finding, chosen_rendering={"x": 2}
            )
        with pytest.raises(KonsistenzAlreadyClosed):
            await quittiere_konsistenz_befund(session=db_session, finding=finding)


# --- Layer 3: signature discipline ---------------------------------------


class TestSignatureDiscipline:
    """The resolver functions must not accept caller-supplied
    decision_event_uuid — same shape as conflict resolvers."""

    def test_resolution_signatures_block_decision_event_uuid_kwarg(self) -> None:
        for fn in (resolve_konsistenz_befund, quittiere_konsistenz_befund):
            params = set(inspect.signature(fn).parameters)
            assert "decision_event_uuid" not in params

    def test_run_consistency_check_signature(self) -> None:
        params = set(inspect.signature(run_consistency_check).parameters)
        assert {"session", "project_uuid"} <= params


# --- Layer 4: schema discipline ------------------------------------------


class TestKonsistenzBefundSchemaDiscipline:
    def test_table_registered(self) -> None:
        from waraq.db.base import Base

        assert "konsistenz_befunde" in Base.metadata.tables

    def test_resolution_decision_event_uuid_fk_is_nullable(self) -> None:
        col = KonsistenzBefund.__table__.columns["resolution_decision_event_uuid"]
        assert col.nullable is True
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert fk_targets == {"decision_events.decision_event_uuid"}

    def test_no_satz_uuid_on_konsistenz_befunde(self) -> None:
        # Konsistenz-Befund is project-scoped (group of segments via JSONB
        # list, not a single satz_uuid FK). Abkürzung 2 stays clean.
        assert "satz_uuid" not in KonsistenzBefund.__table__.columns


# --- Layer 5: cross-module discipline ------------------------------------


@pytest.mark.asyncio
class TestCrossTableDiscipline:
    async def test_detection_writes_no_decision_event(self, db_session: AsyncSession) -> None:
        # Sprint 4 §2: detection produces NO Decision Event. Resolution
        # does. Same shape as conflict_instance.
        project, _ = await _seed_project_with_segments(db_session)
        register_stub_k_rules()

        before = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        # Force a synthetic finding so the path is exercised even with stubs.

        async def _emits_one(
            *, session: AsyncSession, project_uuid: _uuid.UUID
        ) -> Iterable[KConsistencyFinding]:
            return [
                KConsistencyFinding(
                    k_rule=KRuleId.K_03,
                    subject_key=str(new_uuid()),
                    verstossklasse=Verstossklasse.MITTEL,
                )
            ]

        register_k_rule(KRuleId.K_03, _emits_one)
        try:
            await run_consistency_check(session=db_session, project_uuid=project.project_uuid)
        finally:
            register_stub_k_rules()

        after = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        assert after == before

    async def test_run_creates_log_eintraege_at_start_and_end(
        self, db_session: AsyncSession
    ) -> None:
        # Sprint 4 §2: "Log-Eintrag for every run" — start + end at minimum.
        from waraq.schemas import LogEntry

        register_stub_k_rules()
        project, _ = await _seed_project_with_segments(db_session)

        before = (await db_session.execute(select(func.count()).select_from(LogEntry))).scalar_one()
        await run_consistency_check(session=db_session, project_uuid=project.project_uuid)
        after = (await db_session.execute(select(func.count()).select_from(LogEntry))).scalar_one()
        assert after >= before + 2  # start + completed (jobs may also log)

    async def test_consistency_run_creates_consistency_job(self, db_session: AsyncSession) -> None:
        register_stub_k_rules()
        project, _ = await _seed_project_with_segments(db_session)

        job, _ = await run_consistency_check(session=db_session, project_uuid=project.project_uuid)

        loaded = (
            await db_session.execute(select(Job).where(Job.job_uuid == job.job_uuid))
        ).scalar_one()
        assert loaded.job_type == "consistency"
        assert loaded.state == JobState.COMPLETED.value
        assert loaded.project_uuid == project.project_uuid
