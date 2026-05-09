"""Phase 2D — Tanzil-Hafs ingest tests.

Test fixtures use a distinct `_TEST_SOURCE_NAME` so they don't collide
with any production-style ingest sitting in the same database. Every
SELECT in these tests filters by that source_name.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.quran import (
    TanzilParseError,
    ingest_tanzil_quran,
    parse_tanzil_pipe_text,
)
from waraq.quran.tanzil_ingest import TanzilVerse
from waraq.schemas import ArReferenzVerse

# Distinct from `DEFAULT_TANZIL_HAFS_SOURCE_NAME` so production ingest
# rows don't pollute these tests.
_TEST_SOURCE_NAME = "phase2d-test-fixture"


def _select_test_rows():
    return select(ArReferenzVerse).where(ArReferenzVerse.source_name == _TEST_SOURCE_NAME)


# A small but real subset of the Hafs Uthmani text for ingest tests —
# Surat al-Fatiha (sura 1, all 7 āyat). Public domain, CC BY 3.0 source.
_FATIHA_TANZIL = """\
1|1|بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ
1|2|ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ
1|3|ٱلرَّحْمَٰنِ ٱلرَّحِيمِ
1|4|مَٰلِكِ يَوْمِ ٱلدِّينِ
1|5|إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ
1|6|ٱهْدِنَا ٱلصِّرَٰطَ ٱلْمُسْتَقِيمَ
1|7|صِرَٰطَ ٱلَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ ٱلْمَغْضُوبِ عَلَيْهِمْ وَلَا ٱلضَّآلِّينَ
"""


# --- Parser tests ----------------------------------------------------


class TestParser:
    def test_parses_canonical_format(self) -> None:
        verses = list(parse_tanzil_pipe_text(_FATIHA_TANZIL))
        assert len(verses) == 7
        assert verses[0].sura_index == 1
        assert verses[0].aya_index == 1
        assert "بِسْمِ" in verses[0].text_vocalized

    def test_skips_comments_and_blank_lines(self) -> None:
        text = "# Tanzil release v1.1\n\n1|1|بِسْمِ ٱللَّهِ\n# trailing comment\n"
        verses = list(parse_tanzil_pipe_text(text))
        assert len(verses) == 1

    def test_rejects_non_three_field_line(self) -> None:
        with pytest.raises(TanzilParseError, match="3 fields"):
            list(parse_tanzil_pipe_text("1|1\n"))

    def test_rejects_non_integer_sura(self) -> None:
        with pytest.raises(TanzilParseError, match="must be integers"):
            list(parse_tanzil_pipe_text("X|1|text\n"))

    def test_rejects_sura_out_of_range(self) -> None:
        with pytest.raises(TanzilParseError, match="canonical range"):
            list(parse_tanzil_pipe_text("115|1|text\n"))
        with pytest.raises(TanzilParseError, match="canonical range"):
            list(parse_tanzil_pipe_text("0|1|text\n"))

    def test_rejects_aya_below_one(self) -> None:
        with pytest.raises(TanzilParseError, match=">= 1"):
            list(parse_tanzil_pipe_text("1|0|text\n"))

    def test_rejects_empty_text_field(self) -> None:
        with pytest.raises(TanzilParseError, match="empty text field"):
            list(parse_tanzil_pipe_text("1|1|\n"))


# --- Ingest tests ----------------------------------------------------


@pytest.mark.asyncio
class TestIngest:
    async def test_initial_ingest_inserts_all(self, db_session: AsyncSession) -> None:
        verses = list(parse_tanzil_pipe_text(_FATIHA_TANZIL))
        result = await ingest_tanzil_quran(
            session=db_session,
            verses=verses,
            source_version="test-phase2d-A",
            source_name=_TEST_SOURCE_NAME,
        )
        assert result.inserted_count == 7
        assert result.superseded_count == 0
        assert result.source_name == _TEST_SOURCE_NAME

        rows = list((await db_session.execute(_select_test_rows())).scalars())
        assert len(rows) == 7
        # Skeleton derived: vocalized form's diacritics stripped.
        first = next(r for r in rows if r.aya_index == 1)
        assert "ِ" not in first.text_skeleton  # no Kasra
        assert "ْ" not in first.text_skeleton  # no Sukun

    async def test_re_ingest_same_version_is_idempotent(self, db_session: AsyncSession) -> None:
        verses = list(parse_tanzil_pipe_text(_FATIHA_TANZIL))
        first = await ingest_tanzil_quran(
            session=db_session,
            verses=verses,
            source_version="test-phase2d-A",
            source_name=_TEST_SOURCE_NAME,
        )
        assert first.inserted_count == 7

        # Run again with the SAME version — no new inserts, no supersession.
        second = await ingest_tanzil_quran(
            session=db_session,
            verses=verses,
            source_version="test-phase2d-A",
            source_name=_TEST_SOURCE_NAME,
        )
        assert second.inserted_count == 0
        assert second.superseded_count == 0

        rows = list((await db_session.execute(_select_test_rows())).scalars())
        assert len(rows) == 7
        assert all(r.active for r in rows)

    async def test_new_version_supersedes_old(self, db_session: AsyncSession) -> None:
        verses = list(parse_tanzil_pipe_text(_FATIHA_TANZIL))
        await ingest_tanzil_quran(
            session=db_session,
            verses=verses,
            source_version="test-phase2d-A",
            source_name=_TEST_SOURCE_NAME,
        )

        # Different version — old rows go inactive, new rows take their place.
        result = await ingest_tanzil_quran(
            session=db_session,
            verses=verses,
            source_version="test-phase2d-B",
            source_name=_TEST_SOURCE_NAME,
        )
        assert result.inserted_count == 7
        assert result.superseded_count == 7

        # Now: 14 rows total — 7 active (new version), 7 inactive (old).
        rows = list((await db_session.execute(_select_test_rows())).scalars())
        assert len(rows) == 14
        active = [r for r in rows if r.active]
        inactive = [r for r in rows if not r.active]
        assert len(active) == 7
        assert len(inactive) == 7
        assert all(r.source_version == "test-phase2d-B" for r in active)
        assert all(r.source_version == "test-phase2d-A" for r in inactive)

    async def test_partial_re_ingest_updates_text_in_place(self, db_session: AsyncSession) -> None:
        verses_v1 = list(parse_tanzil_pipe_text(_FATIHA_TANZIL))
        await ingest_tanzil_quran(
            session=db_session,
            verses=verses_v1,
            source_version="test-phase2d-A",
            source_name=_TEST_SOURCE_NAME,
        )

        # Same version, but one verse text changed (simulating an
        # upstream typo correction without a version bump).
        modified = [
            TanzilVerse(
                sura_index=v.sura_index,
                aya_index=v.aya_index,
                text_vocalized=v.text_vocalized + "X" if v.aya_index == 3 else v.text_vocalized,
            )
            for v in verses_v1
        ]
        result = await ingest_tanzil_quran(
            session=db_session,
            verses=modified,
            source_version="test-phase2d-A",
            source_name=_TEST_SOURCE_NAME,
        )
        assert result.inserted_count == 0
        assert result.superseded_count == 0

        # Verse 1:3 has the updated text — scoped to test source.
        row = (
            await db_session.execute(
                _select_test_rows()
                .where(ArReferenzVerse.sura_index == 1)
                .where(ArReferenzVerse.aya_index == 3)
            )
        ).scalar_one()
        assert row.text_vocalized.endswith("X")

    async def test_duplicate_in_input_is_rejected(self, db_session: AsyncSession) -> None:
        dup = [
            TanzilVerse(sura_index=1, aya_index=1, text_vocalized="first"),
            TanzilVerse(sura_index=1, aya_index=1, text_vocalized="second"),
        ]
        with pytest.raises(TanzilParseError, match="duplicate"):
            await ingest_tanzil_quran(
                session=db_session,
                verses=dup,
                source_version="test-phase2d-A",
                source_name=_TEST_SOURCE_NAME,
            )


@pytest.mark.asyncio
class TestSchemaConstraints:
    async def test_sura_out_of_range_rejected_by_check(self, db_session: AsyncSession) -> None:
        from waraq.identity import new_uuid

        bogus = ArReferenzVerse(
            verse_uuid=new_uuid(),
            source_name=_TEST_SOURCE_NAME,
            source_version="test-phase2d-A",
            sura_index=200,  # invalid
            aya_index=1,
            text_vocalized="x",
            text_skeleton="x",
        )
        db_session.add(bogus)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_aya_zero_rejected_by_check(self, db_session: AsyncSession) -> None:
        from waraq.identity import new_uuid

        bogus = ArReferenzVerse(
            verse_uuid=new_uuid(),
            source_name=_TEST_SOURCE_NAME,
            source_version="test-phase2d-A",
            sura_index=1,
            aya_index=0,  # invalid
            text_vocalized="x",
            text_skeleton="x",
        )
        db_session.add(bogus)
        with pytest.raises(IntegrityError):
            await db_session.flush()
