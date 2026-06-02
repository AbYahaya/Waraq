"""Phase 4 sub-batch G — §4.17 "no glossary hit" auto-detection.

Pure-text tests for `ChunkContextResolver._resolve_untracked_term_candidates`
behaviour. The DB-backed `for_project` builder is exercised separately
in test_chunk_context.py.
"""

from __future__ import annotations

from waraq.translation.chunk_context import (
    ChunkContextResolver,
    UntrackedTermCandidate,
)


def _resolver_with_no_data() -> ChunkContextResolver:
    return ChunkContextResolver(glossary=[], entities=[])


class TestUntrackedDetection:
    def test_arabic_only_words_become_candidates(self) -> None:
        brief = _resolver_with_no_data().resolve("ذكر العلماء كتاب الفقه والتوحيد")
        forms = [c.surface_form for c in brief.untracked_term_candidates]
        # Conservative §4.17 fallback keeps obvious technical terms while
        # filtering ordinary prose words.
        assert len(forms) >= 2
        assert "العلماء" not in forms
        assert "كتاب" not in forms
        assert all(c.surface_form.isprintable() for c in brief.untracked_term_candidates)

    def test_stopword_filter_excludes_common_words(self) -> None:
        # "في" is a preposition + len-2; "هذا" is a stopword. Neither
        # should surface.
        brief = _resolver_with_no_data().resolve("في هذا الفصل")
        forms = {c.surface_form for c in brief.untracked_term_candidates}
        assert "في" not in forms
        assert "هذا" not in forms
        assert "الفصل" not in forms

    def test_divine_names_and_common_religious_prose_are_not_candidates(self) -> None:
        brief = _resolver_with_no_data().resolve(
            "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ وأسأل الله الكريم رب العرش العظيم"
        )
        assert brief.untracked_term_candidates == []

    def test_quran_spans_are_not_scanned_for_ai_source_candidates(self) -> None:
        brief = _resolver_with_no_data().resolve(
            "قال تعالى: ﴿وما خلقت الجن والإنس إلا ليعبدون﴾ ثم ذكر التوحيد"
        )
        forms = [c.surface_form for c in brief.untracked_term_candidates]
        assert forms == ["التوحيد"]

    def test_obvious_technical_terms_still_surface(self) -> None:
        brief = _resolver_with_no_data().resolve("العبادة لا تسمى عبادة إلا مع التوحيد")
        forms = {c.surface_form for c in brief.untracked_term_candidates}
        assert {"العبادة", "التوحيد"}.issubset(forms)

    def test_empty_text_yields_no_candidates(self) -> None:
        brief = _resolver_with_no_data().resolve("")
        assert brief.untracked_term_candidates == []

    def test_non_arabic_text_yields_no_candidates(self) -> None:
        brief = _resolver_with_no_data().resolve("Just English text 123")
        assert brief.untracked_term_candidates == []

    def test_each_skeleton_returned_once(self) -> None:
        # `الكتاب` and `كتاب` share the alif-collapsed skeleton; only
        # one survives. (The test surfaces whichever appears first.)
        brief = _resolver_with_no_data().resolve("الكتاب كتاب الكتاب")
        skeletons = {c.skeleton for c in brief.untracked_term_candidates}
        # Only the unique skeleton is preserved.
        assert len(skeletons) == len(brief.untracked_term_candidates)


class TestCoverageInteractionWithGlossary:
    def test_glossary_hit_skeleton_is_not_re_surfaced(self) -> None:
        """When a glossary entry matches a word, that word's skeleton
        must NOT also appear in `untracked_term_candidates` — the
        glossary hit already covers it (and supplies a canonical
        rendering)."""
        # Build a resolver with a stub Concept-like object the resolver
        # treats as a glossary entry. Easier approach: use the
        # `_resolver_with_glossary` factory that goes through the same
        # filter logic via the constructor.
        from waraq.identity import new_uuid
        from waraq.schemas import Concept

        concept = Concept(
            concept_id=new_uuid(),
            canonical_label="الإجماع",
            language="ar",
            gloss="Konsens",
            binding_level="project",
        )
        resolver = ChunkContextResolver(glossary=[concept], entities=[])
        brief = resolver.resolve("ذكر الإجماع كتاب فقهي")

        # Glossary hit registered.
        assert len(brief.glossary_hits) == 1
        assert brief.glossary_hits[0].surface_form == "الإجماع"

        # The matched skeleton must not appear among the untracked
        # candidates.
        from waraq.arabic import to_skeleton

        glossary_skel = to_skeleton("الإجماع")
        untracked_skels = {c.skeleton for c in brief.untracked_term_candidates}
        assert glossary_skel not in untracked_skels


class TestCandidateShape:
    def test_candidate_carries_surface_and_skeleton(self) -> None:
        brief = _resolver_with_no_data().resolve("الفقه كتاب")
        for c in brief.untracked_term_candidates:
            assert isinstance(c, UntrackedTermCandidate)
            assert c.surface_form
            assert c.skeleton
            # Skeleton is diacritic-stripped & generally shorter / ==
            # length to surface.
            assert len(c.skeleton) <= len(c.surface_form)
