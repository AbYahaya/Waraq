"""Phase 4 sub-batch D — V-1/V-2 morphology refinement (§4.16.7).

The skeleton-only classifier from Phase 2A returns V-1 whenever two
strings share a skeleton. With CAMeL morphology available, sub-batch
D can refine V-1 → V-2 when the lexemes differ. The fallback rule
(§4.16.7 "no silent down-classification") forbids the reverse — V-2
verdicts from skeleton mismatch are NEVER reduced by morphology.

Tests use stub `MorphologyLexemeFn` adapters so we don't depend on a
local CAMeL DB install.
"""

from __future__ import annotations

from collections.abc import Callable

from waraq.hadith.enums import Vokalisierungsklasse
from waraq.hadith.vocalization import classify_vocalization_class


def _stub_lexemes(mapping: dict[str, str]) -> Callable[[str], str]:
    """Maps surface forms → lexeme strings for the stub adapter."""

    def _fn(word: str) -> str:
        return mapping.get(word, "")

    return _fn


class TestSkeletonOnlyBehaviorPreserved:
    def test_no_adapter_keeps_v1_when_skeleton_equal(self) -> None:
        # Same skeleton (different vocalization) → V-1 with no adapter.
        result = classify_vocalization_class("بِسْمِ", "بِسْمَ")
        assert result == Vokalisierungsklasse.V_1

    def test_no_adapter_keeps_v2_when_skeleton_differs(self) -> None:
        result = classify_vocalization_class("بسم", "اسم")
        assert result == Vokalisierungsklasse.V_2

    def test_v0_unchanged_when_orthographic_only(self) -> None:
        # Tatweel difference only.
        result = classify_vocalization_class("بسم", "بـسم")
        assert result == Vokalisierungsklasse.V_0


class TestMorphologyRefinement:
    def test_v1_escalates_to_v2_when_lexemes_differ(self) -> None:
        # Same skeleton, but the morphology adapter says lexemes
        # differ (e.g., active vs passive ambiguity that the surface
        # masked). Per §4.16.7 fallback rule: escalate.
        adapter = _stub_lexemes({"بِسْمِ": "lex_active", "بِسْمَ": "lex_passive"})
        result = classify_vocalization_class("بِسْمِ", "بِسْمَ", lexeme_fn=adapter)
        assert result == Vokalisierungsklasse.V_2

    def test_v1_held_when_lexemes_match(self) -> None:
        adapter = _stub_lexemes({"بِسْمِ": "lex_same", "بِسْمَ": "lex_same"})
        result = classify_vocalization_class("بِسْمِ", "بِسْمَ", lexeme_fn=adapter)
        assert result == Vokalisierungsklasse.V_1

    def test_inconclusive_adapter_falls_back_to_skeleton_verdict(self) -> None:
        # Adapter returns "" for at least one word — must not
        # silently change the verdict.
        adapter = _stub_lexemes({"بِسْمِ": "", "بِسْمَ": "lex_x"})
        result = classify_vocalization_class("بِسْمِ", "بِسْمَ", lexeme_fn=adapter)
        assert result == Vokalisierungsklasse.V_1

    def test_word_count_mismatch_falls_back_to_skeleton(self) -> None:
        adapter = _stub_lexemes({"a": "x", "b": "y"})
        # Different number of words — positional alignment fails;
        # adapter is not used to escalate.
        result = classify_vocalization_class("بسم الله", "بسم", lexeme_fn=adapter)
        # Skeletons differ here, so V-2 by the deterministic path.
        assert result == Vokalisierungsklasse.V_2

    def test_morphology_never_downgrades_v2(self) -> None:
        # Skeletons differ → V-2 by the skeleton step. Morphology
        # adapter saying "same lexeme" must NOT down-classify.
        adapter = _stub_lexemes({"بسم": "lex_x", "اسم": "lex_x"})
        result = classify_vocalization_class("بسم", "اسم", lexeme_fn=adapter)
        assert result == Vokalisierungsklasse.V_2

    def test_adapter_exceptions_fall_back_safely(self) -> None:
        def _raises(_word: str) -> str:
            raise RuntimeError("camel exploded")

        # Skeleton matches → would be V-1; adapter raises → fall back
        # to skeleton verdict (V-1), do not crash.
        result = classify_vocalization_class("بِسْمِ", "بِسْمَ", lexeme_fn=_raises)
        assert result == Vokalisierungsklasse.V_1
