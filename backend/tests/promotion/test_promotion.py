"""T-7.3.1 — Promotion pipeline Stufen 1-2 tests.

Mandatory tests from Sprint 2 §4:
- Promotion-Stufe1-Beobachtung-Test
- Promotion-Stufe2-Musterkandidat-Test
- Promotion-Kein-Decision-Event-Bei-Beobachtung-Test
- Promotion-Kein-Glossar-Eintrag-Bei-Kandidat-Test
- Promotion-Kandidat-Inert-In-Translation-Test
- Promotion-Schwellenwert-Konfigurations-Test
- T-H7-01 (auto-promotion structurally impossible)
- Promotion-Lernquellen-Source-Class-Recorded-Test
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag, OperationMode
from waraq.promotion import (
    DEFAULT_MUSTERKANDIDAT_THRESHOLD,
    SourceClass,
    aggregate_into_musterkandidaten,
    list_musterkandidaten,
    record_observation,
)
from waraq.release_gate import start_translation
from waraq.revision import create_revision
from waraq.schemas import (
    Block,
    Concept,
    DecisionEvent,
    LogEntry,
    Musterkandidat,
    Page,
    Project,
    ProvenanceObject,
    Segment,
    TranslationObservation,
)
from waraq.schemas.enums import ChangeSource, OcrStatus, POType, ScopeType
from waraq.translation import (
    TranslationContext,
    make_translation_persistence_hook,
    run_translation_job,
    start_translation_job,
)


async def _seed(
    session: AsyncSession, *, segment_text: str = "input-text"
) -> tuple[Project, Segment]:
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)
    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="promotion-test")
    session.add(project)
    await session.flush()
    page = Page(
        page_uuid=new_uuid(),
        project_uuid=project.project_uuid,
        page_index=1,
        ocr_status=OcrStatus.GO,
    )
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
    segment = Segment(
        satz_uuid=new_uuid(),
        block_uuid=block.block_uuid,
        satz_index=1,
        lock_flag=LockFlag.NONE,
        text_content=segment_text,
    )
    session.add(segment)
    await session.flush()
    return project, segment


async def _make_manual_revision_after_engine_revision(
    session: AsyncSession, *, segment: Segment, engine_translation: str, user_correction: str
):
    """Create the canonical revision sequence for a Stufe 1 observation:
    (1) engine produces a translation (RE_TRANSLATE), (2) user corrects
    it (MANUAL). Returns the manual revision."""
    # Engine produces the translation first.
    await create_revision(
        session=session,
        segment=segment,
        after_text=engine_translation,
        change_source=ChangeSource.RE_TRANSLATE,
        operation_mode=OperationMode.AUTOMATIC,
    )
    # User corrects it.
    manual_rev = await create_revision(
        session=session,
        segment=segment,
        after_text=user_correction,
        change_source=ChangeSource.MANUAL,
        operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
    )
    return manual_rev


# --- Promotion-Stufe1-Beobachtung-Test --------------------------


@pytest.mark.asyncio
class TestStufe1Observation:
    async def test_manual_correction_creates_observation(self, db_session: AsyncSession) -> None:
        project, segment = await _seed(db_session, segment_text="alpha beta gamma")
        manual_rev = await _make_manual_revision_after_engine_revision(
            db_session,
            segment=segment,
            engine_translation="DE engine output",
            user_correction="DE user correction",
        )

        obs = await record_observation(
            session=db_session,
            revision=manual_rev,
            segment=segment,
            project_uuid=project.project_uuid,
            prior_translation="DE engine output",
            user_correction="DE user correction",
            terminology_bindings={"k1": "rendering"},
        )

        loaded = (
            await db_session.execute(
                select(TranslationObservation).where(
                    TranslationObservation.observation_uuid == obs.observation_uuid
                )
            )
        ).scalar_one()
        assert loaded.revision_uuid == manual_rev.rev_uuid
        assert loaded.satz_uuid == segment.satz_uuid
        assert loaded.project_uuid == project.project_uuid
        assert loaded.prior_translation == "DE engine output"
        assert loaded.user_correction == "DE user correction"
        assert loaded.terminology_bindings == {"k1": "rendering"}
        # Default source_class.
        assert loaded.source_class == SourceClass.MANUELLE_NUTZERREGELN.value

    async def test_observation_refuses_non_manual_revision(self, db_session: AsyncSession) -> None:
        # An RE_TRANSLATE revision must not produce an observation —
        # observations capture user corrections, not engine output.
        project, segment = await _seed(db_session)
        engine_rev = await create_revision(
            session=db_session,
            segment=segment,
            after_text="engine x",
            change_source=ChangeSource.RE_TRANSLATE,
            operation_mode=OperationMode.AUTOMATIC,
        )
        with pytest.raises(ValueError, match="change_source=manual"):
            await record_observation(
                session=db_session,
                revision=engine_rev,
                segment=segment,
                project_uuid=project.project_uuid,
                prior_translation="x",
                user_correction="y",
            )


# --- Promotion-Kein-Decision-Event-Bei-Beobachtung-Test ----------


@pytest.mark.asyncio
class TestObservationDoesNotCreateDecisionEvent:
    async def test_record_observation_writes_no_decision_event(
        self, db_session: AsyncSession
    ) -> None:
        project, segment = await _seed(db_session)
        manual_rev = await _make_manual_revision_after_engine_revision(
            db_session,
            segment=segment,
            engine_translation="engine",
            user_correction="user",
        )
        before = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        await record_observation(
            session=db_session,
            revision=manual_rev,
            segment=segment,
            project_uuid=project.project_uuid,
            prior_translation="engine",
            user_correction="user",
        )
        after = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        assert after == before


# --- Promotion-Lernquellen-Source-Class-Recorded-Test ------------


@pytest.mark.asyncio
class TestSourceClassRecorded:
    @pytest.mark.parametrize("source_class", list(SourceClass))
    async def test_each_source_class_round_trips(
        self, db_session: AsyncSession, source_class: SourceClass
    ) -> None:
        project, segment = await _seed(db_session)
        manual_rev = await _make_manual_revision_after_engine_revision(
            db_session,
            segment=segment,
            engine_translation="engine",
            user_correction="user",
        )
        obs = await record_observation(
            session=db_session,
            revision=manual_rev,
            segment=segment,
            project_uuid=project.project_uuid,
            prior_translation="engine",
            user_correction="user",
            source_class=source_class,
        )
        assert obs.source_class == source_class.value


# --- Promotion-Stufe2-Musterkandidat-Test -----------------------


@pytest.mark.asyncio
class TestStufe2MusterkandidatRegistration:
    async def test_threshold_observations_register_kandidat_with_log(
        self, db_session: AsyncSession
    ) -> None:
        project, segment = await _seed(db_session, segment_text="recurring source")
        # Inject 3 observations on the same segment with the same
        # source_text so they share a pattern_key.
        for i in range(3):
            manual_rev = await _make_manual_revision_after_engine_revision(
                db_session,
                segment=segment,
                engine_translation=f"engine-v{i}",
                user_correction=f"user-fix-{i}",
            )
            await record_observation(
                session=db_session,
                revision=manual_rev,
                segment=segment,
                project_uuid=project.project_uuid,
                source_text="recurring source",
                prior_translation=f"engine-v{i}",
                user_correction=f"user-fix-{i}",
            )

        before_logs = (
            await db_session.execute(
                select(func.count())
                .select_from(LogEntry)
                .where(LogEntry.operation_type == "musterkandidat_registered")
            )
        ).scalar_one()

        registered = await aggregate_into_musterkandidaten(
            session=db_session, project_uuid=project.project_uuid, threshold=3
        )

        assert len(registered) == 1
        kandidat = registered[0]
        assert kandidat.observation_count == 3
        assert kandidat.state == "kandidat"
        assert len(kandidat.sample_corrections) == 3

        # Log-Eintrag landed.
        after_logs = (
            await db_session.execute(
                select(func.count())
                .select_from(LogEntry)
                .where(LogEntry.operation_type == "musterkandidat_registered")
            )
        ).scalar_one()
        assert after_logs == before_logs + 1

    async def test_below_threshold_observations_register_no_kandidat(
        self, db_session: AsyncSession
    ) -> None:
        project, segment = await _seed(db_session, segment_text="below threshold")
        for i in range(2):
            manual_rev = await _make_manual_revision_after_engine_revision(
                db_session,
                segment=segment,
                engine_translation=f"engine-{i}",
                user_correction=f"user-{i}",
            )
            await record_observation(
                session=db_session,
                revision=manual_rev,
                segment=segment,
                project_uuid=project.project_uuid,
                source_text="below threshold",
                prior_translation=f"engine-{i}",
                user_correction=f"user-{i}",
            )
        registered = await aggregate_into_musterkandidaten(
            session=db_session, project_uuid=project.project_uuid, threshold=3
        )
        assert registered == []


# --- Promotion-Schwellenwert-Konfigurations-Test ----------------


@pytest.mark.asyncio
class TestThresholdIsConfigurable:
    """R-S2-10: same observation set, different threshold → different
    aggregation outcome. Hard-coded threshold would make this impossible."""

    async def test_same_observations_different_thresholds_yield_different_results(
        self, db_session: AsyncSession
    ) -> None:
        project, segment = await _seed(db_session, segment_text="x")
        for i in range(2):
            manual_rev = await _make_manual_revision_after_engine_revision(
                db_session,
                segment=segment,
                engine_translation=f"e{i}",
                user_correction=f"u{i}",
            )
            await record_observation(
                session=db_session,
                revision=manual_rev,
                segment=segment,
                project_uuid=project.project_uuid,
                source_text="threshold-test",
                prior_translation=f"e{i}",
                user_correction=f"u{i}",
            )

        loose = await aggregate_into_musterkandidaten(
            session=db_session, project_uuid=project.project_uuid, threshold=2
        )
        # Clear the kandidat for the strict test.
        from sqlalchemy import delete

        await db_session.execute(delete(Musterkandidat))

        strict = await aggregate_into_musterkandidaten(
            session=db_session, project_uuid=project.project_uuid, threshold=5
        )
        assert len(loose) == 1
        assert strict == []


# --- Promotion-Kein-Glossar-Eintrag-Bei-Kandidat-Test ------------


@pytest.mark.asyncio
class TestKandidatRegistrationDoesNotCreateGlossaryEntry:
    async def test_aggregation_does_not_write_to_concepts_table(
        self, db_session: AsyncSession
    ) -> None:
        project, segment = await _seed(db_session)
        for i in range(3):
            manual_rev = await _make_manual_revision_after_engine_revision(
                db_session,
                segment=segment,
                engine_translation=f"e{i}",
                user_correction="canonical-fix",
            )
            await record_observation(
                session=db_session,
                revision=manual_rev,
                segment=segment,
                project_uuid=project.project_uuid,
                source_text="canonical-source",
                prior_translation=f"e{i}",
                user_correction="canonical-fix",
            )

        before_concepts = (
            await db_session.execute(select(func.count()).select_from(Concept))
        ).scalar_one()
        await aggregate_into_musterkandidaten(
            session=db_session, project_uuid=project.project_uuid, threshold=3
        )
        after_concepts = (
            await db_session.execute(select(func.count()).select_from(Concept))
        ).scalar_one()
        assert after_concepts == before_concepts


# --- T-H7-01: structural impossibility of auto-promotion -------


class TestT_H7_01_NoAutoPromotionPath:
    """R-S2-09 / DBB §A / T-H7-01: the ONLY path from Stufe 2 → Stufe 3
    is the explicit user action `bestaetige_stilregel(musterkandidat_uuid)`.

    Sprint 3 lifts the Sprint-2 protective guard "no Stufe-3 entrypoint
    exists at all" and replaces it with the canonical guard "the Stufe-3
    entrypoints are EXACTLY `bestaetige_stilregel` (confirm) and
    `verwerfe_musterkandidat` (reject) — and nothing automatic". Deeper
    H-7 surface checks live in `tests/promotion/test_promotion_stufe3.py`.
    """

    def test_promotion_module_surface_is_exactly_canonical(self) -> None:
        import inspect as _inspect
        import types

        import waraq.promotion as prom

        functions = {
            name
            for name, obj in vars(prom).items()
            if not name.startswith("_")
            and callable(obj)
            and not isinstance(obj, type)
            and not isinstance(obj, types.ModuleType)
            and _inspect.getmodule(obj) is not None
            and _inspect.getmodule(obj).__name__.startswith("waraq.promotion")  # type: ignore[union-attr]
        }
        # Sprint 2 surface (Stufen 1-2) + Sprint 3 surface (Stufe 3).
        assert functions == {
            "record_observation",
            "aggregate_into_musterkandidaten",
            "list_musterkandidaten",
            "bestaetige_stilregel",
            "verwerfe_musterkandidat",
            "list_bestaetigte_stilregeln",
        }, f"unexpected promotion surface: {functions}"

    def test_no_auto_promotion_function_in_signatures(self) -> None:
        """No `auto_*` / `promote_*` / `auto_confirm_*` signatures in the
        public module — those names would imply non-user-action paths."""
        import waraq.promotion as prom

        forbidden_substrings = ("auto", "promote", "stufe_3")
        for name in vars(prom):
            if name.startswith("_"):
                continue
            assert all(tok not in name.lower() for tok in forbidden_substrings), (
                f"forbidden auto-promotion entrypoint name: {name}"
            )

    def test_musterkandidat_state_machine_extended_by_sprint_3(self) -> None:
        # Sprint 3 extended the CHECK to allow `bestaetigt` and
        # `verworfen`; the canonical default is still `kandidat` so newly
        # registered candidates start there.
        from waraq.schemas import Musterkandidat as _Musterkandidat

        col = _Musterkandidat.__table__.columns["state"]
        default_text = str(col.server_default.arg).strip("'\"")
        assert default_text == "kandidat"


# --- Promotion-Kandidat-Inert-In-Translation-Test ---------------


@pytest.mark.asyncio
class TestKandidatInertInTranslation:
    """Translation passes for new Segments do not consult Musterkandidaten.

    Construction: register a Musterkandidat that "matches" a new segment's
    pattern. Run the translation pipeline. Assert the translator was
    called with the OLD output (engine-default), not the kandidat's
    user-correction sample. This confirms the kandidat is inert."""

    async def test_kandidat_does_not_influence_translation_output(
        self, db_session: AsyncSession
    ) -> None:
        project, segment = await _seed(db_session, segment_text="recurring source")
        # Inject 3 observations + aggregate to register the kandidat.
        for i in range(3):
            manual_rev = await _make_manual_revision_after_engine_revision(
                db_session,
                segment=segment,
                engine_translation=f"e{i}",
                user_correction="canonical-user-fix",
            )
            await record_observation(
                session=db_session,
                revision=manual_rev,
                segment=segment,
                project_uuid=project.project_uuid,
                source_text="recurring source",
                prior_translation=f"e{i}",
                user_correction="canonical-user-fix",
            )
        registered = await aggregate_into_musterkandidaten(
            session=db_session, project_uuid=project.project_uuid, threshold=3
        )
        assert len(registered) == 1
        kandidat = registered[0]
        assert "canonical-user-fix" in kandidat.sample_corrections

        # Now run the translation pipeline on the segment. The translator
        # is the engine — it should NOT see the kandidat's user-fix as
        # input or be told to use it as output.
        await start_translation(session=db_session, project_uuid=project.project_uuid)
        # Reset segment text so translation has fresh input.
        segment.text_content = "recurring source"
        await db_session.flush()

        seen_inputs: list[str] = []

        async def _engine(text: str, ctx: TranslationContext) -> str:
            seen_inputs.append(text)
            # Confirm: terminology_bindings does NOT have the kandidat
            # rendering injected.
            for v in ctx.terminology_bindings.values():
                assert "canonical-user-fix" not in v
            return f"engine-output: {text}"

        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[segment.satz_uuid],
        )
        hook = make_translation_persistence_hook(engine_identifier="stub")
        await run_translation_job(
            session=db_session,
            job=job,
            translator=_engine,
            on_segment_translated=hook,
        )

        # Translator was called with the original input.
        assert "recurring source" in seen_inputs


# --- Cross-table sanity ---------------------------------------


@pytest.mark.asyncio
class TestCrossTableDiscipline:
    async def test_aggregation_writes_no_provenance_object(self, db_session: AsyncSession) -> None:
        project, segment = await _seed(db_session)
        for i in range(3):
            manual_rev = await _make_manual_revision_after_engine_revision(
                db_session,
                segment=segment,
                engine_translation=f"e{i}",
                user_correction=f"u{i}",
            )
            await record_observation(
                session=db_session,
                revision=manual_rev,
                segment=segment,
                project_uuid=project.project_uuid,
                source_text="cross-table-source",
                prior_translation=f"e{i}",
                user_correction=f"u{i}",
            )
        before_pos = (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one()
        await aggregate_into_musterkandidaten(
            session=db_session, project_uuid=project.project_uuid, threshold=3
        )
        after_pos = (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one()
        assert after_pos == before_pos


# --- list_musterkandidaten ------------------------------------


@pytest.mark.asyncio
class TestListMusterkandidaten:
    async def test_list_returns_all_kandidaten_for_project(self, db_session: AsyncSession) -> None:
        project, segment = await _seed(db_session)
        for i in range(3):
            manual_rev = await _make_manual_revision_after_engine_revision(
                db_session,
                segment=segment,
                engine_translation=f"e{i}",
                user_correction=f"u-{i}",
            )
            await record_observation(
                session=db_session,
                revision=manual_rev,
                segment=segment,
                project_uuid=project.project_uuid,
                source_text="list-test-source",
                prior_translation=f"e{i}",
                user_correction=f"u-{i}",
            )
        await aggregate_into_musterkandidaten(
            session=db_session, project_uuid=project.project_uuid, threshold=3
        )

        rows = await list_musterkandidaten(session=db_session, project_uuid=project.project_uuid)
        assert len(rows) == 1


# --- Schema discipline -----------------------------------------


class TestPromotionSchemaDiscipline:
    def test_translation_observations_table_registered(self) -> None:
        from waraq.db.base import Base

        assert "translation_observations" in Base.metadata.tables
        assert "musterkandidaten" in Base.metadata.tables

    def test_observation_does_not_have_satz_uuid_in_allowlisted_form(self) -> None:
        # The Abkürzung 2 allowlist excludes translation_observations —
        # but observations have satz_uuid as an FK because they're per-
        # Segment events. Confirm the column is FK to segments.
        cols = TranslationObservation.__table__.columns
        if "satz_uuid" in cols:
            fks = {fk.target_fullname for fk in cols["satz_uuid"].foreign_keys}
            assert fks == {"segments.satz_uuid"}

    def test_default_threshold_is_an_int(self) -> None:
        # The shipped default is non-canonical; just sanity-check the
        # type. The Schwellenwert-Konfigurations-Test above does the
        # real work.
        assert isinstance(DEFAULT_MUSTERKANDIDAT_THRESHOLD, int)
        assert DEFAULT_MUSTERKANDIDAT_THRESHOLD >= 1


# Silence unused-import warnings at module scope (some imports are
# referenced only inside test bodies).
_ = inspect, ScopeType, POType
