"""Phase 4 sub-batch D — Stage-3 rule-based grammar validators.

The CAMeL morphology DB and Mishkal can be slow / unavailable in CI,
so the production adapters are pluggable. These tests inject
deterministic stubs and assert the score-shaping logic in isolation.
"""

from __future__ import annotations

from waraq.ocr.stage3_rules import (
    NEUTRAL_SCORE,
    Stage3RuleResult,
    rule_based_score,
)


def _stub_morphology(words_to_accept: set[str]):
    def _fn(word: str) -> bool:
        return word in words_to_accept

    return _fn


def _identity_diacritizer(text: str) -> str:
    """Mishkal default-stub: returns input unchanged → 0 added
    diacritics → score 0.0."""
    return text


def _full_vocalizer(text: str) -> str:
    """Stubs Mishkal as if it returned a fully vocalized result.
    Adds a fatha after every Arabic letter so the density score → 1.0."""
    out: list[str] = []
    for c in text:
        out.append(c)
        if "؀" <= c <= "ۿ" and not "ً" <= c <= "ٟ":
            out.append("َ")  # fatha
    return "".join(out)


class TestEmptyAndNonArabic:
    def test_empty_text_is_all_neutral(self) -> None:
        result = rule_based_score(
            "",
            morphology_fn=_stub_morphology(set()),
            diacritizer_fn=_identity_diacritizer,
        )
        assert isinstance(result, Stage3RuleResult)
        assert result.morphology_available is False
        assert result.morphology_score == NEUTRAL_SCORE
        assert result.word_count == 0

    def test_non_arabic_text_skips_morphology(self) -> None:
        result = rule_based_score(
            "Hello world 123",
            morphology_fn=_stub_morphology({"بسم"}),
            diacritizer_fn=_identity_diacritizer,
        )
        assert result.word_count == 0
        # No Arabic letters → diacritization score is neutral, not 0.0.
        assert result.diacritization_score == NEUTRAL_SCORE


class TestMorphologyTrack:
    def test_all_analyzable_yields_one(self) -> None:
        result = rule_based_score(
            "بسم الله الرحمن",
            morphology_fn=_stub_morphology({"بسم", "الله", "الرحمن"}),
            diacritizer_fn=_identity_diacritizer,
        )
        assert result.morphology_available is True
        assert result.morphology_score == 1.0
        assert result.word_count == 3

    def test_partial_analyzable_is_fractional(self) -> None:
        result = rule_based_score(
            "بسم الله الرحمن",
            morphology_fn=_stub_morphology({"بسم", "الله"}),  # 2 of 3
            diacritizer_fn=_identity_diacritizer,
        )
        assert abs(result.morphology_score - (2 / 3)) < 1e-9

    def test_engine_raise_flips_to_unavailable_neutral(self) -> None:
        def _raises(_word: str) -> bool:
            raise RuntimeError("camel db missing")

        result = rule_based_score(
            "بسم",
            morphology_fn=_raises,
            diacritizer_fn=_identity_diacritizer,
        )
        assert result.morphology_available is False
        assert result.morphology_score == NEUTRAL_SCORE


class TestDiacritizationTrack:
    def test_identity_diacritizer_yields_zero_added(self) -> None:
        result = rule_based_score(
            "بسم الله",
            morphology_fn=_stub_morphology(set()),
            diacritizer_fn=_identity_diacritizer,
        )
        assert result.diacritization_available is True
        assert result.diacritization_score == 0.0

    def test_full_vocalizer_yields_one(self) -> None:
        result = rule_based_score(
            "بسم الله",
            morphology_fn=_stub_morphology(set()),
            diacritizer_fn=_full_vocalizer,
        )
        assert result.diacritization_available is True
        # One fatha per bare letter — density = 1.0.
        assert result.diacritization_score == 1.0

    def test_diacritizer_raise_flips_to_unavailable_neutral(self) -> None:
        def _raises(_text: str) -> str:
            raise RuntimeError("mishkal failed")

        result = rule_based_score(
            "بسم",
            morphology_fn=_stub_morphology(set()),
            diacritizer_fn=_raises,
        )
        assert result.diacritization_available is False
        assert result.diacritization_score == NEUTRAL_SCORE


class TestAggregateScore:
    def test_both_available_uses_weighted_average(self) -> None:
        result = rule_based_score(
            "بسم الله",
            morphology_fn=_stub_morphology({"بسم", "الله"}),  # → 1.0
            diacritizer_fn=_full_vocalizer,  # → 1.0
            morphology_weight=0.6,
            diacritization_weight=0.4,
        )
        assert result.score == 1.0

    def test_only_morph_available_uses_morph_score(self) -> None:
        def _diac_raises(_t: str) -> str:
            raise RuntimeError("nope")

        result = rule_based_score(
            "بسم الله",
            morphology_fn=_stub_morphology({"بسم", "الله"}),
            diacritizer_fn=_diac_raises,
        )
        assert result.morphology_available is True
        assert result.diacritization_available is False
        # When only one signal is real, that signal carries full weight.
        assert result.score == result.morphology_score == 1.0

    def test_only_diac_available_uses_diac_score(self) -> None:
        def _morph_raises(_w: str) -> bool:
            raise RuntimeError("camel down")

        result = rule_based_score(
            "بسم الله",
            morphology_fn=_morph_raises,
            diacritizer_fn=_full_vocalizer,
        )
        assert result.morphology_available is False
        assert result.diacritization_available is True
        assert result.score == result.diacritization_score == 1.0

    def test_neither_available_is_neutral(self) -> None:
        def _morph_raises(_w: str) -> bool:
            raise RuntimeError("x")

        def _diac_raises(_t: str) -> str:
            raise RuntimeError("y")

        result = rule_based_score(
            "بسم",
            morphology_fn=_morph_raises,
            diacritizer_fn=_diac_raises,
        )
        assert result.score == NEUTRAL_SCORE
