"""Phase 2D — AR-Referenzbestand lookup tests.

Test fixtures use a distinct `_TEST_SOURCE_NAME` so they don't collide
with any production-style ingest sitting in the same database. All
lookup calls scope to that source_name.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.quran import find_by_skeleton, ingest_tanzil_quran, lookup_aya
from waraq.quran.tanzil_ingest import TanzilVerse

_TEST_SOURCE_NAME = "phase2d-test-fixture"

# Two āyāt to keep the fixtures small and the assertions sharp.
_BISMILLAH = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"
_HAMD = "ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ"


async def _seed_two_verses(session: AsyncSession) -> None:
    await ingest_tanzil_quran(
        session=session,
        verses=[
            TanzilVerse(sura_index=1, aya_index=1, text_vocalized=_BISMILLAH),
            TanzilVerse(sura_index=1, aya_index=2, text_vocalized=_HAMD),
        ],
        source_version="test-phase2d-A",
        source_name=_TEST_SOURCE_NAME,
    )


@pytest.mark.asyncio
class TestLookupAya:
    async def test_existing_aya_round_trip(self, db_session: AsyncSession) -> None:
        await _seed_two_verses(db_session)
        row = await lookup_aya(db_session, sura_index=1, aya_index=1, source_name=_TEST_SOURCE_NAME)
        assert row is not None
        assert row.sura_index == 1 and row.aya_index == 1
        assert "بِسْمِ" in row.text_vocalized

    async def test_unknown_aya_returns_none(self, db_session: AsyncSession) -> None:
        await _seed_two_verses(db_session)
        # (1, 99) doesn't exist in the test source.
        assert (
            await lookup_aya(db_session, sura_index=1, aya_index=99, source_name=_TEST_SOURCE_NAME)
            is None
        )
        # (99, 1) doesn't exist in the test source either (real-Quran
        # 99:1 lives under a different source_name and is not visible
        # under this filter).
        assert (
            await lookup_aya(db_session, sura_index=99, aya_index=1, source_name=_TEST_SOURCE_NAME)
            is None
        )

    async def test_inactive_row_excluded(self, db_session: AsyncSession) -> None:
        # Re-ingest under a NEW source_version → original goes inactive.
        await _seed_two_verses(db_session)
        await ingest_tanzil_quran(
            session=db_session,
            verses=[TanzilVerse(sura_index=1, aya_index=1, text_vocalized="REPLACED")],
            source_version="test-phase2d-B",
            source_name=_TEST_SOURCE_NAME,
        )
        row = await lookup_aya(db_session, sura_index=1, aya_index=1, source_name=_TEST_SOURCE_NAME)
        assert row is not None
        assert row.text_vocalized == "REPLACED"

    async def test_source_name_filter(self, db_session: AsyncSession) -> None:
        await _seed_two_verses(db_session)
        await ingest_tanzil_quran(
            session=db_session,
            verses=[TanzilVerse(sura_index=1, aya_index=1, text_vocalized=_BISMILLAH)],
            source_version="alt-1.0",
            source_name="phase2d-test-alt-source",
        )
        # Both sources have (1, 1) active. Filter narrows.
        from_default = await lookup_aya(
            db_session, sura_index=1, aya_index=1, source_name=_TEST_SOURCE_NAME
        )
        from_alt = await lookup_aya(
            db_session, sura_index=1, aya_index=1, source_name="phase2d-test-alt-source"
        )
        assert from_default is not None
        assert from_alt is not None
        assert from_default.source_name != from_alt.source_name


@pytest.mark.asyncio
class TestFindBySkeleton:
    async def test_match_by_full_vocalized_text(self, db_session: AsyncSession) -> None:
        # Searching with the SAME vocalized form returns the row.
        await _seed_two_verses(db_session)
        rows = await find_by_skeleton(
            db_session, candidate_text=_BISMILLAH, source_name=_TEST_SOURCE_NAME
        )
        assert len(rows) == 1
        assert rows[0].sura_index == 1 and rows[0].aya_index == 1

    async def test_match_by_unvocalized_skeleton(self, db_session: AsyncSession) -> None:
        # OCR rarely emits full vocalization; lookup must still match
        # against a bare-letter candidate.
        await _seed_two_verses(db_session)
        bare = "بسم الله الرحمن الرحيم"
        rows = await find_by_skeleton(
            db_session, candidate_text=bare, source_name=_TEST_SOURCE_NAME
        )
        assert len(rows) == 1
        assert rows[0].sura_index == 1 and rows[0].aya_index == 1

    async def test_no_match_returns_empty(self, db_session: AsyncSession) -> None:
        await _seed_two_verses(db_session)
        rows = await find_by_skeleton(
            db_session,
            candidate_text="completely unrelated",
            source_name=_TEST_SOURCE_NAME,
        )
        assert rows == []

    async def test_empty_candidate_returns_empty(self, db_session: AsyncSession) -> None:
        await _seed_two_verses(db_session)
        assert (
            await find_by_skeleton(db_session, candidate_text="", source_name=_TEST_SOURCE_NAME)
            == []
        )
        assert (
            await find_by_skeleton(db_session, candidate_text="   ", source_name=_TEST_SOURCE_NAME)
            == []
        )

    async def test_inactive_rows_not_returned(self, db_session: AsyncSession) -> None:
        await _seed_two_verses(db_session)
        # Different version with completely different text → inactivates old.
        await ingest_tanzil_quran(
            session=db_session,
            verses=[TanzilVerse(sura_index=1, aya_index=1, text_vocalized="فقه إجماع")],
            source_version="test-phase2d-B",
            source_name=_TEST_SOURCE_NAME,
        )
        # The OLD bismillah skeleton is now on an inactive row → no hit.
        rows = await find_by_skeleton(
            db_session, candidate_text=_BISMILLAH, source_name=_TEST_SOURCE_NAME
        )
        assert rows == []
