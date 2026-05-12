"""Phase 4 sub-batch G — §3.6 4-situation classifier refinement.

Tests for the new AUTO_CORRECTION + AMBIGUITY situations introduced
on top of sub-batch C's AGREEMENT + SUBSTANTIVE_DEVIATION classifier.
The translator orchestrator path (`make_cross_checked_translator`) is
already covered by the existing `test_cross_check.py`; this file
tests the inner `_classify_situation` directly so we can exercise the
classification taxonomy without spinning up the full async pipeline.
"""

from __future__ import annotations

from waraq.translation.cross_check import (
    CrossCheckSituation,
    _classify_situation,
)


class TestAgreementBranch:
    def test_exact_equal_yields_agreement(self) -> None:
        assert _classify_situation("Hello world", "Hello world") == CrossCheckSituation.AGREEMENT

    def test_whitespace_only_difference_is_still_agreement(self) -> None:
        # The Agreement check normalizes whitespace + casing.
        assert _classify_situation("Hello   world", "hello\nworld") == CrossCheckSituation.AGREEMENT


class TestAutoCorrectionBranch:
    def test_canon_rules_collapse_classifies_auto_correction(self) -> None:
        # `apply_canon_rules` digit-normalizes Arabic digits to Latin.
        # If only one engine missed that pass, re-running both through
        # canon-rules makes them equal — that's deterministic / canon-
        # attributable, not interpretive.
        primary = "Verse 5"
        check = "Verse ٥"  # Arabic-Indic digit 5
        situation = _classify_situation(primary, check)
        assert situation == CrossCheckSituation.AUTO_CORRECTION


class TestAmbiguityBranch:
    def test_german_hedge_marker_classifies_ambiguity(self) -> None:
        # Both texts differ AND one carries a hedge marker.
        primary = "Die Aussage bedeutet möglicherweise X."
        check = "Die Aussage bedeutet Y."
        assert _classify_situation(primary, check) == CrossCheckSituation.AMBIGUITY

    def test_unklar_bracket_classifies_ambiguity(self) -> None:
        primary = "Die Aussage bedeutet [unklar]."
        check = "Die Aussage bedeutet etwas anderes."
        assert _classify_situation(primary, check) == CrossCheckSituation.AMBIGUITY

    def test_arabic_question_mark_classifies_ambiguity(self) -> None:
        # The Arabic question mark `؟` signals reviewer uncertainty.
        primary = "ترجمة محتملة؟"
        check = "ترجمة أخرى"
        assert _classify_situation(primary, check) == CrossCheckSituation.AMBIGUITY


class TestSubstantiveDeviationBranch:
    def test_clean_disagreement_with_no_hedges_is_substantive(self) -> None:
        # Different translations, no hedges, no canon-rules collapse.
        primary = "He went to the mosque."
        check = "He travelled to the temple."
        assert _classify_situation(primary, check) == CrossCheckSituation.SUBSTANTIVE_DEVIATION

    def test_does_not_false_positive_on_wohlgemerkt(self) -> None:
        """The hedge list contains 'wohl ' (with trailing space) so
        legitimate compound words like 'wohlgemerkt' don't trigger the
        ambiguity branch."""
        primary = "Wohlgemerkt war das Ergebnis falsch."
        check = "Beachten Sie: das Ergebnis war richtig."
        assert _classify_situation(primary, check) == CrossCheckSituation.SUBSTANTIVE_DEVIATION
