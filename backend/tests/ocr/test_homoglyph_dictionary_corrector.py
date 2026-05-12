"""Phase 4 sub-batch H — `make_dictionary_homoglyph_corrector` factory."""

from __future__ import annotations

from waraq.ocr.homoglyph import (
    HomoglyphSuggestion,
    find_homoglyph_candidates,
    make_camel_homoglyph_corrector,
    make_dictionary_homoglyph_corrector,
)


def _oracle_with(known: set[str]):
    """Build a deterministic analyzability oracle for tests."""

    def _is_known(word: str) -> bool:
        return word in known

    return _is_known


class TestDictionaryCorrector:
    def test_known_word_emits_no_suggestions(self) -> None:
        # Word recognized → no swap candidates surfaced.
        corrector = make_dictionary_homoglyph_corrector(_oracle_with({"بسم"}))
        suggestions = corrector("بسم الله")
        # "الله" might not be in the oracle, but no swap of either word
        # produces another known form.
        # The dictionary corrector should NOT surface anything for "بسم"
        # since it IS known.
        positions_for_basm = [s for s in suggestions if 0 <= s.position <= 2]
        assert positions_for_basm == []

    def test_unknown_word_swap_to_known_yields_suggestion(self) -> None:
        # OCR'd "بسم" but the oracle only recognizes "تسم" (synthetic).
        # The canonical homoglyph pair (ب, ت) lets the corrector
        # propose ب→ت at position 0 yielding "تسم" → suggestion.
        corrector = make_dictionary_homoglyph_corrector(_oracle_with({"تسم"}))
        suggestions = corrector("بسم")
        assert len(suggestions) >= 1
        match = next((s for s in suggestions if s.position == 0 and s.replacement == "ت"), None)
        assert match is not None
        assert match.original == "ب"
        assert match.replacement == "ت"
        assert match.confidence > 0.5
        assert "تسم" in match.rationale

    def test_below_min_skeleton_len_skipped(self) -> None:
        # "اب" is 2 chars — under the 3-char default → skipped.
        corrector = make_dictionary_homoglyph_corrector(
            _oracle_with(set()),
            min_word_skeleton_len=3,
        )
        assert corrector("اب") == []

    def test_oracle_exception_does_not_kill_pass(self) -> None:
        def _raises(_word: str) -> bool:
            raise RuntimeError("oracle exploded")

        corrector = make_dictionary_homoglyph_corrector(_raises)
        # Defensive: oracle errors degrade to no suggestions, not crash.
        assert corrector("نص عربي") == []

    def test_no_arabic_words_yields_no_suggestions(self) -> None:
        corrector = make_dictionary_homoglyph_corrector(_oracle_with(set()))
        assert corrector("Just English text") == []

    def test_suggestion_shape(self) -> None:
        corrector = make_dictionary_homoglyph_corrector(_oracle_with({"تسم"}))
        suggestions = corrector("بسم")
        assert all(isinstance(s, HomoglyphSuggestion) for s in suggestions)


class TestCamelCorrectorGracefulDegradation:
    """When CAMeL DB is missing the production CAMeL-backed corrector
    must degrade to no-op (zero suggestions) — never raise."""

    def test_camel_corrector_no_db_returns_no_suggestions(self) -> None:
        # The CAMeL DB is not installed in CI. The factory returns a
        # corrector whose `_is_known` returns True for every word →
        # no swap surfaces (no "unknown" word to flag).
        corrector = make_camel_homoglyph_corrector()
        # Real Arabic input — should not crash, should not flag
        # anything (no DB → every word looks "known").
        suggestions = corrector("هذا اختبار للنص العربي")
        assert suggestions == []


class TestFindHomoglyphCandidatesIntegration:
    def test_factory_returned_corrector_works_through_harness(self) -> None:
        # The find_homoglyph_candidates harness should accept the
        # factory-built corrector and stable-sort its output.
        corrector = make_dictionary_homoglyph_corrector(_oracle_with({"ذسم"}))
        suggestions = find_homoglyph_candidates("رسم", corrector=corrector)
        positions = [s.position for s in suggestions]
        assert positions == sorted(positions)
