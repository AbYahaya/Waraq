"""Phase 2F-A — §4.15.2 Qurʾān recognition tests.

Uses a distinct AR-source name so tests don't collide with any
production ingest on the same DB.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.quran import ingest_tanzil_quran, recognize_quran_passage
from waraq.quran.tanzil_ingest import TanzilVerse

_TEST_SOURCE_NAME = "phase2f-recognition-test"

# Synthetic 5-āya snippet — distinct text patterns to make multi-āya
# matching unambiguous.
_SEED_VERSES = [
    TanzilVerse(sura_index=2, aya_index=1, text_vocalized="الٓمٓ"),
    TanzilVerse(
        sura_index=2,
        aya_index=2,
        text_vocalized="ذَٰلِكَ ٱلْكِتَٰبُ لَا رَيْبَ فِيهِ هُدًى لِّلْمُتَّقِينَ",
    ),
    TanzilVerse(
        sura_index=2,
        aya_index=3,
        text_vocalized="ٱلَّذِينَ يُؤْمِنُونَ بِٱلْغَيْبِ",
    ),
    TanzilVerse(
        sura_index=3,
        aya_index=1,
        text_vocalized="الٓمٓ",
    ),
    TanzilVerse(
        sura_index=3,
        aya_index=2,
        text_vocalized="ٱللَّهُ لَآ إِلَٰهَ إِلَّا هُوَ ٱلْحَىُّ ٱلْقَيُّومُ",
    ),
]


async def _seed(session: AsyncSession) -> None:
    await ingest_tanzil_quran(
        session=session,
        verses=_SEED_VERSES,
        source_version="recognition-test-v1",
        source_name=_TEST_SOURCE_NAME,
    )


@pytest.mark.asyncio
class TestSingleAyaRecognition:
    async def test_exact_skeleton_matches(self, db_session: AsyncSession) -> None:
        await _seed(db_session)
        # Bare-letter form (no diacritics) of 2:2.
        bare = "ذلك الكتاب لا ريب فيه هدى للمتقين"
        r = await recognize_quran_passage(
            db_session, candidate_text=bare, source_name=_TEST_SOURCE_NAME
        )
        assert r.matched is True
        assert r.confidence == 1.0
        assert r.is_above_threshold
        assert r.sura_index == 2
        assert r.aya_index_start == 2
        assert r.aya_index_end == 2
        assert r.ar_source_name == _TEST_SOURCE_NAME
        assert r.ar_source_version == "recognition-test-v1"

    async def test_no_match_returns_unmatched(self, db_session: AsyncSession) -> None:
        await _seed(db_session)
        r = await recognize_quran_passage(
            db_session,
            candidate_text="نص لا يطابق",
            source_name=_TEST_SOURCE_NAME,
        )
        assert r.matched is False
        assert r.confidence == 0.0
        assert not r.is_above_threshold

    async def test_empty_candidate_returns_unmatched(self, db_session: AsyncSession) -> None:
        await _seed(db_session)
        r = await recognize_quran_passage(
            db_session, candidate_text="", source_name=_TEST_SOURCE_NAME
        )
        assert r.matched is False

    async def test_vocalized_input_normalizes_to_skeleton(self, db_session: AsyncSession) -> None:
        """Fully vocalized OCR output still matches against skeleton-stored rows."""
        await _seed(db_session)
        full = "ذَٰلِكَ ٱلْكِتَٰبُ لَا رَيْبَ فِيهِ هُدًى لِّلْمُتَّقِينَ"
        r = await recognize_quran_passage(
            db_session, candidate_text=full, source_name=_TEST_SOURCE_NAME
        )
        assert r.matched is True
        assert (r.sura_index, r.aya_index_start, r.aya_index_end) == (2, 2, 2)


@pytest.mark.asyncio
class TestMultiAyaRecognition:
    async def test_two_consecutive_ayat_match(self, db_session: AsyncSession) -> None:
        await _seed(db_session)
        # 2:2 + 2:3 concatenated.
        text = "ذلك الكتاب لا ريب فيه هدى للمتقين الذين يؤمنون بالغيب"
        r = await recognize_quran_passage(
            db_session, candidate_text=text, source_name=_TEST_SOURCE_NAME
        )
        assert r.matched is True
        assert r.sura_index == 2
        assert r.aya_index_start == 2
        assert r.aya_index_end == 3

    async def test_disambiguates_same_skeleton_across_suras(self, db_session: AsyncSession) -> None:
        """`الم` skeleton appears as 2:1 AND 3:1. Single-āya match
        returns the first hit; either is acceptable, but the matcher
        must NOT crash or return an inconsistent range.
        """
        await _seed(db_session)
        r = await recognize_quran_passage(
            db_session, candidate_text="الم", source_name=_TEST_SOURCE_NAME
        )
        assert r.matched is True
        assert r.sura_index in (2, 3)
        assert r.aya_index_start == 1
        assert r.aya_index_end == 1

    async def test_partial_text_does_not_falsely_match_full_aya(
        self, db_session: AsyncSession
    ) -> None:
        """A prefix of an āya that doesn't equal a full āya skeleton
        should not match (v1.0 is exact-match only)."""
        await _seed(db_session)
        # A prefix — not a full āya.
        r = await recognize_quran_passage(
            db_session,
            candidate_text="ذلك الكتاب لا",
            source_name=_TEST_SOURCE_NAME,
        )
        assert r.matched is False
