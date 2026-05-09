"""T-7.3.2 — Promotion Stufe 3 mandatory tests.

Per Sprint 3 §4:
- T-H7-01 (auto-promotion structurally impossible — already in scope from
  Sprint 2; this sprint deepens the assertion against new entrypoints)
- Promotion-Stufe3-Bestaetigung-Decision-Event-Test
- Promotion-Stufe3-Stilregel-Distinct-Entity-Test
- Promotion-Stufe3-Verwerfung-Test
- Promotion-Stufe3-Stilregel-Inert-In-Translation-Test
- Promotion-Stufe3-Verworfener-Kandidat-Nicht-Wieder-Bestaetigbar-Test
- Promotion-Stufe3-Source-Class-Preserved-Test
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag, OperationMode
from waraq.promotion import (
    KandidatNotInKandidatState,
    SourceClass,
    aggregate_into_musterkandidaten,
    bestaetige_stilregel,
    list_bestaetigte_stilregeln,
    record_observation,
    verwerfe_musterkandidat,
)
from waraq.release_gate import start_translation
from waraq.revision import create_revision
from waraq.schemas import (
    BestaetigteStilregel,
    Block,
    Musterkandidat,
    Page,
    Project,
    Segment,
    TranslationObservation,
)
from waraq.schemas.enums import (
    ChangeSource,
    DecisionSource,
    OcrStatus,
    ScopeType,
)
from waraq.translation import (
    TranslationContext,
    run_translation_job,
    start_translation_job,
)


async def _seed(
    session: AsyncSession, *, segment_text: str = "input-text"
) -> tuple[Project, Segment]:
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)
    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="stufe3-test")
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
        block_index=0,
    )
    session.add(block)
    await session.flush()
    segment = Segment(
        satz_uuid=new_uuid(),
        block_uuid=block.block_uuid,
        satz_index=0,
        lock_flag=LockFlag.NONE,
        text_content=segment_text,
    )
    session.add(segment)
    await session.flush()
    return project, segment


async def _seed_kandidat(
    session: AsyncSession,
    *,
    project: Project,
    segment: Segment,
    threshold: int = 2,
    source_classes: tuple[SourceClass, ...] = (SourceClass.MANUELLE_NUTZERREGELN,),
) -> Musterkandidat:
    """Create N=threshold observations for the same pattern_key, then run
    aggregation. Returns the resulting Musterkandidat."""
    shared_source = "recurring source"
    for i, sc in enumerate(source_classes * threshold):
        rev = await create_revision(
            session=session,
            segment=segment,
            after_text=f"engine-out-{i}",
            change_source=ChangeSource.RE_TRANSLATE,
            operation_mode=OperationMode.AUTOMATIC,
        )
        # Now a manual correction
        manual_rev = await create_revision(
            session=session,
            segment=segment,
            after_text=f"user-correction-{i}",
            change_source=ChangeSource.MANUAL,
            operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
        )
        await record_observation(
            session=session,
            revision=manual_rev,
            segment=segment,
            project_uuid=project.project_uuid,
            prior_translation=rev.after_text,
            user_correction=manual_rev.after_text,
            source_text=shared_source,
            source_class=sc,
        )
        if len(source_classes * threshold) >= threshold and i + 1 >= threshold:
            break
    rows = await aggregate_into_musterkandidaten(
        session=session,
        project_uuid=project.project_uuid,
        threshold=threshold,
    )
    assert len(rows) == 1
    return rows[0]


# --- Bestaetigung Decision Event + distinct entity ----------------


@pytest.mark.asyncio
class TestBestaetigung:
    async def test_bestaetigung_writes_decision_event_and_creates_stilregel(
        self, db_session: AsyncSession
    ) -> None:
        project, seg = await _seed(db_session)
        kand = await _seed_kandidat(db_session, project=project, segment=seg)

        before_stilregel_count = (
            await db_session.execute(select(func.count()).select_from(BestaetigteStilregel))
        ).scalar_one()

        stilregel, de = await bestaetige_stilregel(
            session=db_session,
            musterkandidat_uuid=kand.musterkandidat_uuid,
            actor_uuid=project.account_uuid,
            annotation="confirmed by user review",
        )

        # Decision Event canonical shape.
        assert de.decision_type == "stilregel_bestaetigung"
        assert de.decision_source == DecisionSource.STYLE_MANAGEMENT.value
        assert de.scope_type == ScopeType.PROJECT.value
        assert de.scope_uuid == project.project_uuid

        # Stilregel is a NEW row distinct from the Musterkandidat.
        assert stilregel.musterkandidat_uuid == kand.musterkandidat_uuid
        assert stilregel.stilregel_uuid != kand.musterkandidat_uuid
        assert stilregel.confirmation_decision_event_uuid == de.decision_event_uuid
        assert stilregel.pattern_key == kand.pattern_key

        after_stilregel_count = (
            await db_session.execute(select(func.count()).select_from(BestaetigteStilregel))
        ).scalar_one()
        assert after_stilregel_count == before_stilregel_count + 1

        # Musterkandidat is marked `bestaetigt` and retains its evidence.
        await db_session.refresh(kand)
        assert kand.state == "bestaetigt"
        assert kand.observation_count >= 2  # observation linkage retained
        # Observations themselves are still there.
        obs_count = (
            await db_session.execute(
                select(func.count())
                .select_from(TranslationObservation)
                .where(TranslationObservation.project_uuid == project.project_uuid)
            )
        ).scalar_one()
        assert obs_count >= 2


# --- Verwerfung -----------------------------------------------------


@pytest.mark.asyncio
class TestVerwerfung:
    async def test_verwerfung_writes_decision_event_and_marks_state(
        self, db_session: AsyncSession
    ) -> None:
        project, seg = await _seed(db_session)
        kand = await _seed_kandidat(db_session, project=project, segment=seg)

        before_stilregel_count = (
            await db_session.execute(select(func.count()).select_from(BestaetigteStilregel))
        ).scalar_one()

        rejected, de = await verwerfe_musterkandidat(
            session=db_session,
            musterkandidat_uuid=kand.musterkandidat_uuid,
            actor_uuid=project.account_uuid,
            annotation="not a generalizable pattern",
        )
        assert de.decision_type == "musterkandidat_verworfen"
        assert de.decision_source == DecisionSource.STYLE_MANAGEMENT.value
        assert rejected.state == "verworfen"

        # No Stilregel row was created.
        after_stilregel_count = (
            await db_session.execute(select(func.count()).select_from(BestaetigteStilregel))
        ).scalar_one()
        assert after_stilregel_count == before_stilregel_count


# --- Verworfener Kandidat nicht wieder bestaetigbar ---------------


@pytest.mark.asyncio
class TestVerworfenerNichtWiederBestaetigbar:
    async def test_rejected_then_confirm_refused(self, db_session: AsyncSession) -> None:
        project, seg = await _seed(db_session)
        kand = await _seed_kandidat(db_session, project=project, segment=seg)
        await verwerfe_musterkandidat(
            session=db_session,
            musterkandidat_uuid=kand.musterkandidat_uuid,
        )
        # Subsequent confirm raises.
        with pytest.raises(KandidatNotInKandidatState):
            await bestaetige_stilregel(
                session=db_session,
                musterkandidat_uuid=kand.musterkandidat_uuid,
            )


# --- Stilregel inert in translation production -------------------


@pytest.mark.asyncio
class TestStilregelInertInTranslation:
    async def test_translation_does_not_consult_stilregel(self, db_session: AsyncSession) -> None:
        project, seg = await _seed(db_session, segment_text="recurring source")
        kand = await _seed_kandidat(db_session, project=project, segment=seg)
        stilregel, _de = await bestaetige_stilregel(
            session=db_session,
            musterkandidat_uuid=kand.musterkandidat_uuid,
        )
        # Confirm the stilregel exists.
        listed = await list_bestaetigte_stilregeln(
            session=db_session, project_uuid=project.project_uuid
        )
        assert any(s.stilregel_uuid == stilregel.stilregel_uuid for s in listed)

        # Authorize translation start, then run a translation job. The
        # output is exactly what the translator returns — no stilregel
        # rewriting.
        await start_translation(session=db_session, project_uuid=project.project_uuid)
        # Reset segment text to a fresh source for the translator.
        await create_revision(
            session=db_session,
            segment=seg,
            after_text="recurring source",
            change_source=ChangeSource.OCR,
            operation_mode=OperationMode.AUTOMATIC,
        )
        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[seg.satz_uuid],
        )

        async def _translator(input_text: str, _ctx: TranslationContext) -> str:
            return f"DE-engine: {input_text}"

        result = await run_translation_job(
            session=db_session,
            job=job,
            translator=_translator,
        )
        # Inspect the produced TRANSLATION-PO chunk: output must be
        # exactly what the translator returned, NOT the stilregel's
        # observation user-corrections.
        chunks = result.chunks
        assert len(chunks) == 1
        assert chunks[0].output_text.startswith("DE-engine: ")


# --- Source-class metadata preserved -----------------------------


@pytest.mark.asyncio
class TestSourceClassPreserved:
    async def test_source_classes_propagate_to_stilregel(self, db_session: AsyncSession) -> None:
        project, seg = await _seed(db_session)
        # Build a kandidat backed by observations of TWO distinct
        # source-classes so the propagated set is non-trivial.
        shared_source = "shared phrase"
        for i, sc in enumerate(
            (SourceClass.MANUELLE_NUTZERREGELN, SourceClass.AKZEPTIERTE_KI_VORSCHLAEGE)
        ):
            await create_revision(
                session=db_session,
                segment=seg,
                after_text=f"engine-out-{i}",
                change_source=ChangeSource.RE_TRANSLATE,
                operation_mode=OperationMode.AUTOMATIC,
            )
            manual_rev = await create_revision(
                session=db_session,
                segment=seg,
                after_text=f"user-correction-{i}",
                change_source=ChangeSource.MANUAL,
                operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
            )
            await record_observation(
                session=db_session,
                revision=manual_rev,
                segment=seg,
                project_uuid=project.project_uuid,
                prior_translation=f"engine-out-{i}",
                user_correction=manual_rev.after_text,
                source_text=shared_source,
                source_class=sc,
            )

        rows = await aggregate_into_musterkandidaten(
            session=db_session,
            project_uuid=project.project_uuid,
            threshold=2,
        )
        assert len(rows) == 1
        kand = rows[0]

        stilregel, de = await bestaetige_stilregel(
            session=db_session,
            musterkandidat_uuid=kand.musterkandidat_uuid,
        )
        # Both source-class values must appear on the confirmed Stilregel.
        assert set(stilregel.source_classes) == {
            SourceClass.MANUELLE_NUTZERREGELN.value,
            SourceClass.AKZEPTIERTE_KI_VORSCHLAEGE.value,
        }
        # And on the DE content for audit.
        assert set(de.content["source_classes"]) == set(stilregel.source_classes)


# --- T-H7-01: structurally impossible auto-promotion -----------------


@pytest.mark.asyncio
class TestH7AutomaticPromotionImpossible:
    async def test_promotion_module_only_exposes_user_action_paths(self) -> None:
        """The PROMOTION module's public API must not expose any helper
        that takes a Musterkandidat and transitions it to `bestaetigt`
        WITHOUT the user-action signature. This is the load-bearing
        H-7 surface check (R-S3-08)."""
        from waraq import promotion as promo

        # The two Stufe-3 entrypoints accept `musterkandidat_uuid` and
        # write a Decision Event. Anything else exposed must NOT do that.
        names = list(promo.__all__)
        assert "bestaetige_stilregel" in names
        assert "verwerfe_musterkandidat" in names

        # Source-scan: no other public callable in `waraq.promotion`
        # references `state = "bestaetigt"` directly. Only stilregel.py
        # may. (Belt-and-braces against future drift.)
        for name in names:
            obj = getattr(promo, name)
            if not callable(obj):
                continue
            module_name = getattr(obj, "__module__", "")
            if not module_name.startswith("waraq.promotion"):
                continue
            try:
                src = inspect.getsource(obj)
            except (OSError, TypeError):
                continue
            if module_name == "waraq.promotion.stilregel":
                continue
            assert "bestaetigt" not in src or 'state = "bestaetigt"' not in src, (
                f"{name} ({module_name}) writes the bestaetigt state outside "
                "stilregel.py — H-7 demands the user-action path is the only one."
            )

    async def test_kandidat_only_initial_state_at_creation(self, db_session: AsyncSession) -> None:
        """Newly registered Musterkandidaten must start in `kandidat`,
        not in `bestaetigt`."""
        project, seg = await _seed(db_session)
        kand = await _seed_kandidat(db_session, project=project, segment=seg)
        assert kand.state == "kandidat"
