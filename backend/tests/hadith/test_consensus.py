"""Phase 2F-B — §4.16.3 multi-dimensional consensus tests (pure logic, no DB)."""

from __future__ import annotations

import pytest

from waraq.hadith import (
    HadithCandidateHit,
    Quellenrolle,
    Vokalisierungsklasse,
    compute_consensus,
)
from waraq.hadith.consensus import _is_kutub_as_sitta


def _hit(
    *,
    source: str,
    role: Quellenrolle = Quellenrolle.PFLICHT,
    matn: str,
    voc: str | None = None,
    isnad: list[str] | None = None,
    collection: str = "",
    grade: str | None = None,
    author_match: bool = False,
    raw: dict[str, str] | None = None,
) -> HadithCandidateHit:
    return HadithCandidateHit(
        source_name=source,
        quellen_rolle=role,
        matn_arabic=matn,
        matn_vocalized=voc,
        isnad_chain=isnad or [],
        collection_label=collection,
        authenticity_grade=grade,
        matched_author_named_source=author_match,
        raw_payload=raw or {},
    )


# --- Empty input ----------------------------------------------------


class TestPreconditions:
    def test_empty_candidates_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one candidate"):
            compute_consensus([])


# --- Single hit -----------------------------------------------------


class TestSingleHit:
    def test_single_hit_wins_by_default(self) -> None:
        hits = [
            _hit(
                source="sunnah.com",
                matn="إنما الأعمال بالنيات",
                voc="إنَّمَا الأَعْمَالُ بِالنِّيَّاتِ",
                isnad=["عمر بن الخطاب"],
                collection="Sahih al-Bukhari",
                grade="Sahih",
            )
        ]
        r = compute_consensus(hits)
        assert r.reference_matn == "إنما الأعمال بالنيات"
        assert r.reference_matn_source_index == 0
        assert r.reference_vocalization == "إنَّمَا الأَعْمَالُ بِالنِّيَّاتِ"
        assert r.reference_vocalization_source_index == 0
        assert r.kutub_preference_applied is False
        assert r.linear_tie_break_applied is False

    def test_single_hit_no_vocalization(self) -> None:
        hits = [
            _hit(source="sunnah.com", matn="إنما الأعمال بالنيات", grade="Sahih"),
        ]
        r = compute_consensus(hits)
        assert r.reference_vocalization is None
        assert r.reference_vocalization_source_index is None
        assert r.vokalisierungsklasse == Vokalisierungsklasse.V_0
        assert r.vokalisierungs_konflikt is False


# --- Wording proximity dominates -----------------------------------


class TestWordingDominates:
    def test_high_carriage_higher_score_than_isolated(self) -> None:
        # Three sources agree on the matn; one outlier with different text.
        agreed = "إنما الأعمال بالنيات"
        hits = [
            _hit(source="sunnah.com", matn=agreed, collection="Sahih al-Bukhari"),
            _hit(source="dorar.net", matn=agreed, collection="Sahih al-Bukhari"),
            _hit(source="shamela", matn=agreed, collection="Sahih Muslim"),
            _hit(source="E-5", matn="نص مختلف تماما", collection="other"),
        ]
        r = compute_consensus(hits)
        # Top 3 ranking entries should NOT be the outlier.
        outlier = next(s for s in r.ranking if s.hit.source_name == "E-5")
        assert r.ranking[-1].hit_index == outlier.hit_index
        assert r.ranking[0].dimensions.carriage_count >= 2


# --- Kutub-as-Sitta tiebreak ---------------------------------------


class TestKutubAsSittaTiebreak:
    def test_tie_resolved_in_favor_of_kutub(self) -> None:
        """Two hits with equal-strength dimensions; one is Kutub-as-Sitta."""
        agreed = "إنما الأعمال بالنيات"
        hits = [
            # Non-Kutub source, otherwise equivalent.
            _hit(
                source="dorar.net",
                matn=agreed,
                isnad=["عمر بن الخطاب"],
                collection="some other collection",
                grade="Sahih",
            ),
            # Kutub-as-Sitta — Sahih al-Bukhari.
            _hit(
                source="sunnah.com",
                matn=agreed,
                isnad=["عمر بن الخطاب"],
                collection="Sahih al-Bukhari",
                grade="Sahih",
            ),
        ]
        r = compute_consensus(hits)
        # The Kutub-as-Sitta hit (sunnah.com / Bukhari) wins after the
        # tie is resolved.
        assert r.ranking[0].hit.collection_label == "Sahih al-Bukhari"
        assert r.ranking[0].is_kutub_as_sitta is True

    def test_no_tiebreak_when_winner_already_kutub(self) -> None:
        """Winner is already Kutub-as-Sitta on raw score; no tiebreak applied."""
        hits = [
            _hit(
                source="sunnah.com",
                matn="إنما الأعمال بالنيات",
                isnad=["عمر بن الخطاب"],
                collection="Sahih al-Bukhari",
                grade="Sahih",
            ),
            _hit(
                source="dorar.net",
                matn="حديث آخر مختلف",
                collection="other",
            ),
        ]
        r = compute_consensus(hits)
        assert r.kutub_preference_applied is False
        assert r.ranking[0].hit.collection_label == "Sahih al-Bukhari"

    def test_more_wording_faithful_outside_kutub_can_win(self) -> None:
        """§4.16.3 canon: 'A more wording-faithful, robust hit outside
        the Kutub as-Sitta can break precedence.' Modeled by raw
        composite score: when a non-Kutub hit has strictly higher
        composite score, no tie → no Kutub preference applied.
        """
        # Author-named-source bonus pushes the non-Kutub hit above
        # the tie threshold.
        hits = [
            _hit(
                source="sunnah.com",
                matn="إنما الأعمال بالنيات",
                isnad=["عمر بن الخطاب"],
                collection="Sahih al-Bukhari",
                grade="Sahih",
            ),
            _hit(
                source="dorar.net",
                matn="إنما الأعمال بالنيات",
                isnad=["عمر بن الخطاب"],
                collection="other",
                grade="Sahih",
                author_match=True,  # author cited dorar.net
            ),
        ]
        r = compute_consensus(hits)
        # author-match boosts the non-Kutub hit clear of tie threshold.
        assert r.kutub_preference_applied is False


# --- §3.5 Linear tiebreak ------------------------------------------


class TestLinearTiebreak:
    def test_neither_kutub_falls_to_linear(self) -> None:
        """Two non-Kutub-as-Sitta hits with tied composite scores →
        §3.5 linear ranking decides (sunnah.com beats dorar.net)."""
        agreed = "إنما الأعمال بالنيات"
        hits = [
            _hit(source="dorar.net", matn=agreed, collection="other-A"),
            _hit(source="sunnah.com", matn=agreed, collection="other-B"),
        ]
        r = compute_consensus(hits)
        assert r.ranking[0].hit.source_name == "sunnah.com"
        assert r.linear_tie_break_applied is True

    def test_two_kutub_tied_goes_to_linear_within_kutub(self) -> None:
        """Both candidates are Kutub-as-Sitta; tied composite. Linear
        rank breaks within the Kutub set."""
        agreed = "إنما الأعمال بالنيات"
        hits = [
            _hit(source="dorar.net", matn=agreed, collection="Sahih al-Bukhari"),
            _hit(source="sunnah.com", matn=agreed, collection="Sahih Muslim"),
        ]
        r = compute_consensus(hits)
        # sunnah.com beats dorar.net in §3.5 linear rank.
        assert r.ranking[0].hit.source_name == "sunnah.com"


# --- Vocalization picking (§4.16.7) --------------------------------


class TestVocalizationWinner:
    def test_vocalization_winner_can_differ_from_matn_winner(self) -> None:
        """§4.16.7 explicitly allows the vocalization source to differ
        from the matn source."""
        bare = "إنما الأعمال بالنيات"
        hits = [
            # Matn-winner candidate: Kutub-as-Sitta but no vocalization.
            _hit(
                source="sunnah.com",
                matn=bare,
                voc=None,  # no vocalization
                collection="Sahih al-Bukhari",
                grade="Sahih",
            ),
            # Vocalized-only candidate: lower matn score but rich voc.
            _hit(
                source="dorar.net",
                matn=bare,
                voc="إِنَّمَا الأَعْمَالُ بِالنِّيَّاتِ",
                collection="other",
            ),
        ]
        r = compute_consensus(hits)
        # Vocalization comes from dorar.net's hit even though sunnah
        # likely wins on matn.
        assert r.reference_vocalization == "إِنَّمَا الأَعْمَالُ بِالنِّيَّاتِ"

    def test_vokalisierungs_konflikt_binary(self) -> None:
        """§4.16.7 — `vokalisierungs_konflikt` is strictly binary."""
        # Two vocalized hits with V-1 difference (skeleton same,
        # vocalization differs in diacritic density).
        hits = [
            _hit(
                source="sunnah.com",
                matn="بسم الله",
                voc="بِسْمِ اللَّهِ",
                collection="Sahih al-Bukhari",
            ),
            _hit(
                source="dorar.net",
                matn="بسم الله",
                voc="بسم الله",  # bare-letter, same skeleton
                collection="other",
            ),
        ]
        r = compute_consensus(hits)
        # Conflict is binary; either True or False.
        assert isinstance(r.vokalisierungs_konflikt, bool)
        # Skeleton match (regular alif on both sides) but vocalization
        # density differs → V-1 → conflict True.
        assert r.vokalisierungs_konflikt is True
        assert r.vokalisierungsklasse == Vokalisierungsklasse.V_1


# --- Consensus summary shape ---------------------------------------


class TestConsensusSummary:
    def test_summary_carries_per_dimension_breakdown(self) -> None:
        hits = [
            _hit(
                source="sunnah.com",
                matn="إنما الأعمال بالنيات",
                isnad=["عمر"],
                collection="Sahih al-Bukhari",
                grade="Sahih",
            ),
            _hit(
                source="dorar.net",
                matn="إنما الأعمال بالنيات",
                collection="other",
            ),
        ]
        r = compute_consensus(hits)
        s = r.consensus_summary
        assert "winner" in s
        assert "tiebreak" in s
        assert "ranking" in s
        assert s["candidate_count"] == 2
        # Winner block carries per-dimension values.
        winner_dims = s["winner"]["dimensions"]
        for key in (
            "wording_proximity",
            "carriage_count",
            "author_named_match",
            "isnad_collection_quality",
            "vocalization_consistency",
            "authenticity_score",
        ):
            assert key in winner_dims


# --- Kutub-as-Sitta detection helper -------------------------------


class TestKutubDetection:
    def test_canonical_names_recognized(self) -> None:
        for label in (
            "Sahih al-Bukhari",
            "sahih al-bukhari",
            "Sahih Muslim",
            "Sunan Abi Dawud",
            "Jami at-Tirmidhi",
            "Sunan an-Nasai",
            "Sunan Ibn Majah",
        ):
            assert _is_kutub_as_sitta(label) is True, f"failed for {label!r}"

    def test_non_kutub_rejected(self) -> None:
        for label in ("", "musnad ahmad", "muwatta malik", "sunan ad-darimi"):
            assert _is_kutub_as_sitta(label) is False, f"unexpectedly kutub: {label!r}"

    def test_extra_whitespace_handled(self) -> None:
        assert _is_kutub_as_sitta("  Sahih   al-Bukhari  ") is True
