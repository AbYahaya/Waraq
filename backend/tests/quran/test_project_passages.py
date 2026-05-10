"""Phase 2F-A — §4.15.3 + §4.15.5 project passage tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment
from waraq.quran import (
    PassageNotInExpectedState,
    RecognitionResult,
    confirm_below_threshold,
    correct_sura_aya,
    ingest_tanzil_quran,
    record_recognized_passage,
    refresh_passage_from_collection,
    reject_as_quran,
)
from waraq.quran.tanzil_ingest import TanzilVerse
from waraq.schemas import DecisionEvent, ProjectQuranPassage
from waraq.schemas.enums import DecisionSource

_TEST_SOURCE_NAME = "phase2f-passage-test"
_VERSION_A = "passage-test-A"
_VERSION_B = "passage-test-B"

_VERSES_A = [
    TanzilVerse(
        sura_index=1,
        aya_index=1,
        text_vocalized="بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
    ),
    TanzilVerse(
        sura_index=1,
        aya_index=2,
        text_vocalized="ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ",
    ),
    TanzilVerse(
        sura_index=2,
        aya_index=1,
        text_vocalized="الٓمٓ",
    ),
]


async def _seed_ar(session: AsyncSession, *, version: str = _VERSION_A) -> None:
    await ingest_tanzil_quran(
        session=session,
        verses=_VERSES_A,
        source_version=version,
        source_name=_TEST_SOURCE_NAME,
    )


def _recognition_for(
    *,
    sura: int,
    aya: int,
    text: str,
    confidence: float = 1.0,
) -> RecognitionResult:
    return RecognitionResult(
        matched=True,
        confidence=confidence,
        sura_index=sura,
        aya_index_start=aya,
        aya_index_end=aya,
        ar_source_name=_TEST_SOURCE_NAME,
        ar_source_version=_VERSION_A,
        matched_text_vocalized=text,
    )


# --- record_recognized_passage --------------------------------------


@pytest.mark.asyncio
class TestRecordRecognizedPassage:
    async def test_above_threshold_no_decision_event(self, db_session: AsyncSession) -> None:
        """§4.15.5 canon: 'Automatic acceptance with confidence above
        threshold generates no decision_event.'"""
        await _seed_ar(db_session)
        project = await seed_project(db_session, name="quran-passage-test")
        seg = await seed_segment(db_session, project=project, text="x")

        recognition = _recognition_for(
            sura=1, aya=1, text=_VERSES_A[0].text_vocalized, confidence=1.0
        )
        outcome = await record_recognized_passage(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            recognition=recognition,
            confidence_threshold=0.85,
        )
        assert outcome.decision_event_uuid is None
        assert outcome.passage.state == "recognized"
        assert outcome.passage.confidence == 1.0
        assert outcome.passage.snapshot_text_vocalized == _VERSES_A[0].text_vocalized
        assert outcome.passage.last_state_change_at is None

    async def test_below_threshold_writes_translation_pipeline_de(
        self, db_session: AsyncSession
    ) -> None:
        """§4.15.5 row 1 — manual confirmation = decision_source=translation_pipeline."""
        await _seed_ar(db_session)
        project = await seed_project(db_session, name="quran-low-conf")
        seg = await seed_segment(db_session, project=project, text="x")

        recognition = _recognition_for(
            sura=1, aya=1, text=_VERSES_A[0].text_vocalized, confidence=0.5
        )
        outcome = await record_recognized_passage(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            recognition=recognition,
            confidence_threshold=0.85,
        )
        assert outcome.decision_event_uuid is not None
        assert outcome.passage.state == "manually_confirmed"

        de = (
            await db_session.execute(
                select(DecisionEvent).where(
                    DecisionEvent.decision_event_uuid == outcome.decision_event_uuid
                )
            )
        ).scalar_one()
        assert de.decision_source == DecisionSource.TRANSLATION_PIPELINE.value
        assert de.decision_type == "quran_manual_confirmation_below_threshold"


# --- correct_sura_aya (§4.15.5 row 2 → conflict_resolution) ---------


@pytest.mark.asyncio
class TestCorrectSuraAya:
    async def test_corrects_and_writes_conflict_resolution(self, db_session: AsyncSession) -> None:
        await _seed_ar(db_session)
        project = await seed_project(db_session, name="quran-correct")
        seg = await seed_segment(db_session, project=project, text="x")
        # Initially recognized as 1:1 — but author intended 1:2.
        outcome = await record_recognized_passage(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            recognition=_recognition_for(sura=1, aya=1, text=_VERSES_A[0].text_vocalized),
        )

        de = await correct_sura_aya(
            session=db_session,
            passage=outcome.passage,
            new_sura_index=1,
            new_aya_index_start=2,
            new_aya_index_end=2,
        )
        assert de.decision_source == DecisionSource.CONFLICT_RESOLUTION.value
        assert outcome.passage.sura_index == 1
        assert outcome.passage.aya_index_start == 2
        assert outcome.passage.aya_index_end == 2
        assert outcome.passage.snapshot_text_vocalized == _VERSES_A[1].text_vocalized
        assert outcome.passage.state == "corrected"

    async def test_correction_against_unknown_range_raises(self, db_session: AsyncSession) -> None:
        await _seed_ar(db_session)
        project = await seed_project(db_session, name="quran-correct-bad")
        seg = await seed_segment(db_session, project=project, text="x")
        outcome = await record_recognized_passage(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            recognition=_recognition_for(sura=1, aya=1, text=_VERSES_A[0].text_vocalized),
        )
        # 50:1 is not present in the test AR source.
        with pytest.raises(ValueError, match="not present"):
            await correct_sura_aya(
                session=db_session,
                passage=outcome.passage,
                new_sura_index=50,
                new_aya_index_start=1,
                new_aya_index_end=1,
            )

    async def test_refused_on_rejected_passage(self, db_session: AsyncSession) -> None:
        await _seed_ar(db_session)
        project = await seed_project(db_session, name="quran-correct-rej")
        seg = await seed_segment(db_session, project=project, text="x")
        outcome = await record_recognized_passage(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            recognition=_recognition_for(sura=1, aya=1, text=_VERSES_A[0].text_vocalized),
        )
        await reject_as_quran(session=db_session, passage=outcome.passage)
        with pytest.raises(PassageNotInExpectedState):
            await correct_sura_aya(
                session=db_session,
                passage=outcome.passage,
                new_sura_index=1,
                new_aya_index_start=2,
                new_aya_index_end=2,
            )


# --- reject_as_quran (§4.15.5 row 3 → conflict_resolution) ----------


@pytest.mark.asyncio
class TestRejectAsQuran:
    async def test_rejects_and_writes_conflict_resolution(self, db_session: AsyncSession) -> None:
        await _seed_ar(db_session)
        project = await seed_project(db_session, name="quran-reject")
        seg = await seed_segment(db_session, project=project, text="x")
        outcome = await record_recognized_passage(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            recognition=_recognition_for(sura=1, aya=1, text=_VERSES_A[0].text_vocalized),
        )
        de = await reject_as_quran(
            session=db_session, passage=outcome.passage, note="false positive"
        )
        assert de.decision_source == DecisionSource.CONFLICT_RESOLUTION.value
        assert outcome.passage.state == "rejected"

    async def test_double_reject_raises(self, db_session: AsyncSession) -> None:
        await _seed_ar(db_session)
        project = await seed_project(db_session, name="quran-double-reject")
        seg = await seed_segment(db_session, project=project, text="x")
        outcome = await record_recognized_passage(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            recognition=_recognition_for(sura=1, aya=1, text=_VERSES_A[0].text_vocalized),
        )
        await reject_as_quran(session=db_session, passage=outcome.passage)
        with pytest.raises(PassageNotInExpectedState):
            await reject_as_quran(session=db_session, passage=outcome.passage)


# --- confirm_below_threshold (§4.15.5 row 1 → translation_pipeline) -


@pytest.mark.asyncio
class TestConfirmBelowThreshold:
    async def test_confirms_recognized_state(self, db_session: AsyncSession) -> None:
        await _seed_ar(db_session)
        project = await seed_project(db_session, name="quran-confirm")
        seg = await seed_segment(db_session, project=project, text="x")
        outcome = await record_recognized_passage(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            recognition=_recognition_for(sura=1, aya=1, text=_VERSES_A[0].text_vocalized),
        )
        de = await confirm_below_threshold(session=db_session, passage=outcome.passage)
        assert de.decision_source == DecisionSource.TRANSLATION_PIPELINE.value
        assert outcome.passage.state == "manually_confirmed"

    async def test_refuses_already_confirmed(self, db_session: AsyncSession) -> None:
        await _seed_ar(db_session)
        project = await seed_project(db_session, name="quran-already")
        seg = await seed_segment(db_session, project=project, text="x")
        outcome = await record_recognized_passage(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            recognition=_recognition_for(sura=1, aya=1, text=_VERSES_A[0].text_vocalized),
        )
        await confirm_below_threshold(session=db_session, passage=outcome.passage)
        with pytest.raises(PassageNotInExpectedState):
            await confirm_below_threshold(session=db_session, passage=outcome.passage)


# --- §4.15.3 protection + §4.15.5 row 4 (express refresh) -----------


@pytest.mark.asyncio
class TestProtectionAndRefresh:
    async def test_no_auto_overwrite_on_collection_update(self, db_session: AsyncSession) -> None:
        """§4.15.3: stored project passages remain unchanged on AR
        collection updates. We model this by re-ingesting under a
        different (test) source_version and checking that the
        original passage row is unchanged."""
        await _seed_ar(db_session, version=_VERSION_A)
        project = await seed_project(db_session, name="quran-protect")
        seg = await seed_segment(db_session, project=project, text="x")
        outcome = await record_recognized_passage(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            recognition=_recognition_for(sura=1, aya=1, text=_VERSES_A[0].text_vocalized),
        )
        original_text = outcome.passage.snapshot_text_vocalized
        original_version = outcome.passage.ar_source_version

        # Re-ingest a NEW version with completely different text for
        # 1:1 — old version flips to inactive.
        modified_verses = [
            TanzilVerse(
                sura_index=1,
                aya_index=1,
                text_vocalized="REPLACED in newer collection",
            ),
            *_VERSES_A[1:],
        ]
        await ingest_tanzil_quran(
            session=db_session,
            verses=modified_verses,
            source_version=_VERSION_B,
            source_name=_TEST_SOURCE_NAME,
        )

        # Project passage row is UNTOUCHED — §4.15.3.
        reloaded = (
            await db_session.execute(
                select(ProjectQuranPassage).where(
                    ProjectQuranPassage.passage_uuid == outcome.passage.passage_uuid
                )
            )
        ).scalar_one()
        assert reloaded.snapshot_text_vocalized == original_text
        assert reloaded.ar_source_version == original_version
        assert reloaded.state == "recognized"

    async def test_express_refresh_translation_pipeline(self, db_session: AsyncSession) -> None:
        """§4.15.5 row 4 — express user action to update a stored
        passage following an AR/translation collection update.
        decision_source = translation_pipeline."""
        await _seed_ar(db_session, version=_VERSION_A)
        project = await seed_project(db_session, name="quran-refresh")
        seg = await seed_segment(db_session, project=project, text="x")
        outcome = await record_recognized_passage(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            recognition=_recognition_for(sura=1, aya=1, text=_VERSES_A[0].text_vocalized),
        )

        # New collection version with updated text for 1:1.
        modified_verses = [
            TanzilVerse(
                sura_index=1,
                aya_index=1,
                text_vocalized="بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ — refreshed",
            ),
            *_VERSES_A[1:],
        ]
        await ingest_tanzil_quran(
            session=db_session,
            verses=modified_verses,
            source_version=_VERSION_B,
            source_name=_TEST_SOURCE_NAME,
        )

        # Express user action — refresh.
        de = await refresh_passage_from_collection(
            session=db_session,
            passage=outcome.passage,
            new_ar_source_version=_VERSION_B,
        )
        assert de.decision_source == DecisionSource.TRANSLATION_PIPELINE.value
        assert outcome.passage.state == "refreshed"
        assert outcome.passage.ar_source_version == _VERSION_B
        assert "refreshed" in outcome.passage.snapshot_text_vocalized

    async def test_refresh_refuses_rejected(self, db_session: AsyncSession) -> None:
        await _seed_ar(db_session)
        project = await seed_project(db_session, name="quran-refresh-rej")
        seg = await seed_segment(db_session, project=project, text="x")
        outcome = await record_recognized_passage(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            recognition=_recognition_for(sura=1, aya=1, text=_VERSES_A[0].text_vocalized),
        )
        await reject_as_quran(session=db_session, passage=outcome.passage)
        with pytest.raises(PassageNotInExpectedState):
            await refresh_passage_from_collection(session=db_session, passage=outcome.passage)
