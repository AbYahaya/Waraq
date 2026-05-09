"""§4.16.7 V-0/V-1/V-2 classifier tests."""

from __future__ import annotations

from waraq.hadith import classify_vocalization_class
from waraq.hadith.enums import Vokalisierungsklasse
from waraq.hadith.vocalization import aggregate_vocalization_class

# --- V-0: orthographic-technical, no sound or meaning change ---------


class TestV0_PureRendering:
    def test_identical_strings_are_v0(self) -> None:
        s = "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"
        assert classify_vocalization_class(s, s) == Vokalisierungsklasse.V_0

    def test_both_empty_is_v0(self) -> None:
        assert classify_vocalization_class("", "") == Vokalisierungsklasse.V_0

    def test_tatweel_difference_is_v0(self) -> None:
        without_tatweel = "محمد"
        with_tatweel = "محـمد"  # U+0640 inserted
        assert (
            classify_vocalization_class(without_tatweel, with_tatweel) == Vokalisierungsklasse.V_0
        )

    def test_nfc_normalization_difference_is_v0(self) -> None:
        # NFC vs NFD form of the same vocalized letter
        import unicodedata

        s1 = "بِسْم"
        s2 = unicodedata.normalize("NFD", s1)
        assert classify_vocalization_class(s1, s2) == Vokalisierungsklasse.V_0


# --- V-1: diacritic-only deviation, skeleton equal -------------------


class TestV1_DiacriticOnly:
    def test_vocalized_vs_unvocalized_skeleton_equal(self) -> None:
        # Same skeletal letters; one has full vocalization, the other none.
        # §4.16.7 V-1 example: vocalization-density differences without
        # word-identity change.
        vocalized = "بِسْمِ اللَّهِ"
        bare = "بسم الله"
        assert classify_vocalization_class(vocalized, bare) == Vokalisierungsklasse.V_1

    def test_partial_vocalization_difference(self) -> None:
        a = "كَتَبَ"  # fully vocalized
        b = "كَتب"  # partial vocalization
        assert classify_vocalization_class(a, b) == Vokalisierungsklasse.V_1

    def test_shadda_density_with_skeleton_match(self) -> None:
        # Both write "muḥammad" with the same skeleton; one carries
        # Shadda explicitly, the other omits it. Skeleton matches, so V-1.
        a = "محمّد"  # with Shadda
        b = "محمد"  # without Shadda
        assert classify_vocalization_class(a, b) == Vokalisierungsklasse.V_1


# --- V-2: skeletal letter difference -> meaning/lexeme change --------


class TestV2_SkeletalDeviation:
    def test_different_letters_are_v2(self) -> None:
        # Different skeletal letters => meaning change. Canonical V-2.
        a = "كتب"
        b = "كتاب"  # added Alef => skeleton diverges
        assert classify_vocalization_class(a, b) == Vokalisierungsklasse.V_2

    def test_one_empty_is_v2(self) -> None:
        # Asymmetric emptiness escalates to V-2 — a missing matn is
        # structural, not a vocalization variant.
        assert classify_vocalization_class("بسم", "") == Vokalisierungsklasse.V_2
        assert classify_vocalization_class("", "بسم") == Vokalisierungsklasse.V_2

    def test_completely_different_words(self) -> None:
        a = "صلى"
        b = "كتب"
        assert classify_vocalization_class(a, b) == Vokalisierungsklasse.V_2


# --- Order-independence + commutativity ------------------------------


class TestOrderIndependence:
    def test_v0_symmetric(self) -> None:
        a = "محمد"
        b = "محـمد"
        assert classify_vocalization_class(a, b) == classify_vocalization_class(b, a)

    def test_v1_symmetric(self) -> None:
        a = "بِسْمِ"
        b = "بسم"
        assert classify_vocalization_class(a, b) == classify_vocalization_class(b, a)

    def test_v2_symmetric(self) -> None:
        a = "كتب"
        b = "كتاب"
        assert classify_vocalization_class(a, b) == classify_vocalization_class(b, a)


# --- Aggregation rule (§4.16.7) --------------------------------------


class TestAggregation:
    def test_empty_aggregates_to_v0(self) -> None:
        assert aggregate_vocalization_class([]) == Vokalisierungsklasse.V_0

    def test_highest_class_wins(self) -> None:
        assert (
            aggregate_vocalization_class(
                [Vokalisierungsklasse.V_0, Vokalisierungsklasse.V_2, Vokalisierungsklasse.V_1]
            )
            == Vokalisierungsklasse.V_2
        )

    def test_only_v0_aggregates_to_v0(self) -> None:
        assert (
            aggregate_vocalization_class([Vokalisierungsklasse.V_0, Vokalisierungsklasse.V_0])
            == Vokalisierungsklasse.V_0
        )

    def test_v1_with_v0_aggregates_to_v1(self) -> None:
        assert (
            aggregate_vocalization_class([Vokalisierungsklasse.V_0, Vokalisierungsklasse.V_1])
            == Vokalisierungsklasse.V_1
        )
