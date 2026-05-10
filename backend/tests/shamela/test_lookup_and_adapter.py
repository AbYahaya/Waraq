"""Phase 2E — lookup (Mode A + Mode B) + consensus-engine adapter tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.hadith.consensus import compute_consensus
from waraq.hadith.enums import Quellenrolle
from waraq.shamela import (
    SectionRow,
    find_by_skeleton,
    ingest_text,
    search_by_keyword,
    shamela_hits_to_consensus_candidates,
)

_TEST_VERSION = "phase2e-lookup-test"

_BUKHARI_SECTIONS = [
    SectionRow(
        section_index=1,
        section_path="كتاب بدء الوحي > باب 1",
        text_arabic="إنما الأعمال بالنيات وإنما لكل امرئ ما نوى",
        metadata={"hadith_number": 1},
    ),
    SectionRow(
        section_index=2,
        section_path="كتاب الإيمان > باب 1",
        text_arabic="الإسلام أن تشهد أن لا إله إلا الله",
        metadata={"hadith_number": 8},
    ),
]
_LISAN_SECTIONS = [
    SectionRow(
        section_index=1,
        section_path="نوى",
        text_arabic="نَوَى الشيءَ نِيَّةً ونَوَاةً قَصَدَه",
        metadata={"lemma": "نوى"},
    ),
]


async def _seed(session: AsyncSession) -> None:
    await ingest_text(
        session=session,
        text_slug="sahih_bukhari",
        source_version=_TEST_VERSION,
        sections=_BUKHARI_SECTIONS,
    )
    await ingest_text(
        session=session,
        text_slug="lisan_al_arab",
        source_version=_TEST_VERSION,
        sections=_LISAN_SECTIONS,
    )


# --- find_by_skeleton (§3.5 Mode A) ---------------------------------


@pytest.mark.asyncio
class TestFindBySkeleton:
    async def test_skeleton_substring_match_against_bukhari(self, db_session: AsyncSession) -> None:
        await _seed(db_session)
        # Bare-letter form of the matn (different from stored vocalized form).
        bare = "إنما الأعمال بالنيات"
        hits = await find_by_skeleton(db_session, candidate_text=bare)
        slugs = {h.text_slug for h in hits}
        assert "sahih_bukhari" in slugs

    async def test_only_kutub_as_sitta_filter(self, db_session: AsyncSession) -> None:
        await _seed(db_session)
        hits = await find_by_skeleton(
            db_session,
            candidate_text="إنما الأعمال",
            only_kutub_as_sitta=True,
        )
        # All hits are from Kutub-as-Sitta.
        assert all(h.is_kutub_as_sitta for h in hits)
        # Lisān al-ʿArab (lexicon, not Kutub) excluded.
        assert all(h.text_slug != "lisan_al_arab" for h in hits)

    async def test_text_slugs_filter(self, db_session: AsyncSession) -> None:
        await _seed(db_session)
        hits = await find_by_skeleton(
            db_session,
            candidate_text="نوى",
            text_slugs=["lisan_al_arab"],
        )
        # Only lisān_al_arab hits returned.
        assert all(h.text_slug == "lisan_al_arab" for h in hits)

    async def test_empty_candidate_returns_empty(self, db_session: AsyncSession) -> None:
        await _seed(db_session)
        assert await find_by_skeleton(db_session, candidate_text="") == []
        assert await find_by_skeleton(db_session, candidate_text="   ") == []


# --- search_by_keyword (§3.5 Mode B) --------------------------------


@pytest.mark.asyncio
class TestSearchByKeyword:
    async def test_lexicon_lookup_for_word(self, db_session: AsyncSession) -> None:
        await _seed(db_session)
        # Look up "نوى" in lexicons only.
        hits = await search_by_keyword(db_session, keyword="نوى", text_types=["lexicon"])
        assert len(hits) >= 1
        assert all(h.text_type == "lexicon" for h in hits)

    async def test_keyword_match_includes_vocalized_form(self, db_session: AsyncSession) -> None:
        """Mode B searches the raw `text_arabic` (vocalized form, not
        skeleton). A vocalized keyword match works."""
        await _seed(db_session)
        hits = await search_by_keyword(db_session, keyword="نَوَى")
        assert any(h.text_slug == "lisan_al_arab" for h in hits)


# --- adapter (Shamela → consensus engine) ---------------------------


@pytest.mark.asyncio
class TestConsensusAdapter:
    async def test_shamela_kutub_hits_become_pflicht_candidates(
        self, db_session: AsyncSession
    ) -> None:
        await _seed(db_session)
        hits = await find_by_skeleton(
            db_session,
            candidate_text="إنما الأعمال",
            only_kutub_as_sitta=True,
        )
        candidates = shamela_hits_to_consensus_candidates(hits)
        assert len(candidates) >= 1
        assert all(c.source_name == "shamela" for c in candidates)
        assert all(c.quellen_rolle == Quellenrolle.PFLICHT for c in candidates)
        # Collection label maps to the canonical Kutub-as-Sitta name.
        assert all(c.collection_label == "Sahih al-Bukhari" for c in candidates)

    async def test_lexicon_hits_filtered_out(self, db_session: AsyncSession) -> None:
        """Mode-B lexicon hits don't belong in the §4.16.3 consensus
        pipeline — they're informational lookups, not Hadith verification
        carriers."""
        await _seed(db_session)
        hits = await search_by_keyword(db_session, keyword="نوى")
        candidates = shamela_hits_to_consensus_candidates(hits)
        # No lexicon hits forwarded.
        assert all(c.source_name == "shamela" for c in candidates)
        # If lexicon hits were included they'd have collection_label
        # = "لسان العرب"; verify none did.
        assert all(c.collection_label != "لسان العرب" for c in candidates)

    async def test_end_to_end_shamela_into_consensus(self, db_session: AsyncSession) -> None:
        """Full pipe: Shamela P-2 hit + a sunnah.com P-1 hit → consensus
        engine returns a winner. Validates the §4.16.3 Kutub preference
        resolves correctly when both are Kutub-as-Sitta."""
        from waraq.hadith.consensus import HadithCandidateHit

        await _seed(db_session)
        shamela_hits = await find_by_skeleton(
            db_session,
            candidate_text="إنما الأعمال",
            only_kutub_as_sitta=True,
        )
        shamela_candidates = shamela_hits_to_consensus_candidates(shamela_hits)

        # Add a non-Kutub sunnah.com candidate alongside.
        candidates = [
            *shamela_candidates,
            HadithCandidateHit(
                source_name="dorar.net",
                quellen_rolle=Quellenrolle.PFLICHT,
                matn_arabic="إنما الأعمال بالنيات",
                collection_label="other",
            ),
        ]
        result = compute_consensus(candidates)
        # Shamela's Bukhari hit is Kutub-as-Sitta — should win.
        assert result.ranking[0].is_kutub_as_sitta is True
        assert result.ranking[0].hit.collection_label == "Sahih al-Bukhari"
