"""Phase 4 sub-batch D — Stage-3 statistical (Shamela Mode-A consumer)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.ocr.stage3_statistical import (
    HIT_SCORE,
    NEUTRAL_SCORE,
    Stage3StatisticalResult,
    statistical_score,
)
from waraq.schemas.enums import BlockClass
from waraq.shamela import ingest_text, parse_section_lines

# Two distinct text fixtures so we can prove kutub-as-sitta scoping
# actually constrains the lookup. The slugs `sahih_bukhari` and
# `lisan_al_arab` already live in the canonical OpenITI registry —
# `ingest_text` looks them up implicitly.
_BUKHARI_FIXTURE = """\
# كتاب بدء الوحي
| إنما الأعمال بالنيات وإنما لكل امرئ ما نوى
"""

_LISAN_FIXTURE = """\
# مادة ن و ى
| نوى الشيءَ نِيَّةً، أي قصده وعزم عليه
"""


async def _seed_corpus(session: AsyncSession) -> None:
    """Seed Bukhari (Kutub-as-Sitta) + Lisān (lexicon) so we can
    prove HADITH routing scopes correctly."""
    await ingest_text(
        session=session,
        text_slug="sahih_bukhari",
        source_version="phase4d-stat",
        sections=list(parse_section_lines(_BUKHARI_FIXTURE)),
    )
    await ingest_text(
        session=session,
        text_slug="lisan_al_arab",
        source_version="phase4d-stat",
        sections=list(parse_section_lines(_LISAN_FIXTURE)),
    )


@pytest.mark.asyncio
class TestStatisticalSignal:
    async def test_empty_text_is_neutral(self, db_session: AsyncSession) -> None:
        result = await statistical_score(
            session=db_session,
            candidate_text="",
            block_class=BlockClass.MAIN_TEXT,
        )
        assert isinstance(result, Stage3StatisticalResult)
        assert result.score == NEUTRAL_SCORE
        assert result.hit_count == 0

    async def test_no_hit_yields_neutral(self, db_session: AsyncSession) -> None:
        await _seed_corpus(db_session)
        result = await statistical_score(
            session=db_session,
            candidate_text="نص عشوائي تماما لن يطابق أي مصدر",
            block_class=BlockClass.MAIN_TEXT,
        )
        assert result.score == NEUTRAL_SCORE
        assert result.hit_count == 0
        assert result.sample_titles == ()

    async def test_hit_in_main_text_lifts_to_hit_score(self, db_session: AsyncSession) -> None:
        await _seed_corpus(db_session)
        result = await statistical_score(
            session=db_session,
            candidate_text="إنما الأعمال بالنيات",
            block_class=BlockClass.MAIN_TEXT,
        )
        assert result.score == HIT_SCORE
        assert result.hit_count >= 1
        # Lookup not scoped to Kutub-as-Sitta for MAIN_TEXT.
        assert result.scoped_to_kutub_as_sitta is False
        # Title comes from the canonical OpenITI registry — Arabic original.
        assert "صحيح البخاري" in result.sample_titles

    async def test_hadith_block_scopes_to_kutub_as_sitta(self, db_session: AsyncSession) -> None:
        """A passage that exists ONLY in Lisān (lexicon, not Kutub) must
        return zero hits when the block class is HADITH — proves the
        scope filter actually fires."""
        await _seed_corpus(db_session)
        result = await statistical_score(
            session=db_session,
            candidate_text="نوى الشيء نية",
            block_class=BlockClass.HADITH,
        )
        assert result.scoped_to_kutub_as_sitta is True
        assert result.hit_count == 0
        assert result.score == NEUTRAL_SCORE

    async def test_hadith_block_finds_kutub_match(self, db_session: AsyncSession) -> None:
        await _seed_corpus(db_session)
        result = await statistical_score(
            session=db_session,
            candidate_text="إنما الأعمال بالنيات",
            block_class=BlockClass.HADITH,
        )
        assert result.scoped_to_kutub_as_sitta is True
        assert result.hit_count >= 1
        assert result.score == HIT_SCORE

    async def test_score_is_in_unit_interval(self, db_session: AsyncSession) -> None:
        await _seed_corpus(db_session)
        result = await statistical_score(
            session=db_session,
            candidate_text="إنما الأعمال بالنيات",
            block_class=BlockClass.MAIN_TEXT,
        )
        assert 0.0 <= result.score <= 1.0
