"""Phase 2F-A — §4.15.4 source-citation logic tests."""

from __future__ import annotations

from waraq.quran import (
    CitationVerdict,
    format_canonical_citation,
    parse_author_citation,
    verify_author_citation,
)
from waraq.schemas import ProjectQuranPassage


def _passage(*, sura: int, aya_start: int, aya_end: int) -> ProjectQuranPassage:
    """Minimal in-memory passage fixture for formatter/verifier tests
    (no DB session needed — these are pure-function tests)."""
    p = ProjectQuranPassage()
    p.sura_index = sura
    p.aya_index_start = aya_start
    p.aya_index_end = aya_end
    return p


# --- parse_author_citation ------------------------------------------


class TestParseAuthorCitation:
    def test_simple_colon_form(self) -> None:
        assert parse_author_citation("1:1") == (1, 1, 1)

    def test_colon_with_range(self) -> None:
        assert parse_author_citation("1:1-7") == (1, 1, 7)
        assert parse_author_citation("1:1–7") == (1, 1, 7)
        assert parse_author_citation("1:1—7") == (1, 1, 7)

    def test_german_prose_form(self) -> None:
        assert parse_author_citation("Sure 2, Vers 255") == (2, 255, 255)

    def test_english_prose_form(self) -> None:
        assert parse_author_citation("Surah 2, verse 255") == (2, 255, 255)

    def test_inside_parentheses(self) -> None:
        assert parse_author_citation("(1:1)") == (1, 1, 1)
        assert parse_author_citation("[1:1]") == (1, 1, 1)

    def test_arabic_comma_separator(self) -> None:
        assert parse_author_citation("سورة 1، 1") == (1, 1, 1)

    def test_arabic_sura_name_with_arabic_indic_ayah(self) -> None:
        assert parse_author_citation("[النساء: ٤٨]") == (4, 48, 48)
        assert parse_author_citation("[يونس: ٣١]") == (10, 31, 31)
        assert parse_author_citation("[الذاريات: 56]") == (51, 56, 56)

    def test_arabic_sura_name_range(self) -> None:
        assert parse_author_citation("[الفاتحة: ١-٧]") == (1, 1, 7)

    def test_unparseable_returns_none(self) -> None:
        assert parse_author_citation("") is None
        assert parse_author_citation("not a citation") is None

    def test_sura_out_of_range_returns_none(self) -> None:
        assert parse_author_citation("200:1") is None
        assert parse_author_citation("0:1") is None

    def test_aya_zero_returns_none(self) -> None:
        assert parse_author_citation("1:0") is None

    def test_inverted_range_returns_none(self) -> None:
        assert parse_author_citation("1:7-1") is None


# --- format_canonical_citation --------------------------------------


class TestFormatCanonical:
    def test_de_single_aya(self) -> None:
        p = _passage(sura=1, aya_start=1, aya_end=1)
        assert format_canonical_citation(passage=p, lang="de") == "(Sure 1, Vers 1)"

    def test_de_range(self) -> None:
        p = _passage(sura=1, aya_start=1, aya_end=7)
        assert format_canonical_citation(passage=p, lang="de") == "(Sure 1, Verse 1–7)"

    def test_en_single_aya(self) -> None:
        p = _passage(sura=1, aya_start=1, aya_end=1)
        assert format_canonical_citation(passage=p, lang="en") == "(Surah 1, verse 1)"

    def test_en_range(self) -> None:
        p = _passage(sura=2, aya_start=1, aya_end=5)
        assert format_canonical_citation(passage=p, lang="en") == "(Surah 2, verses 1–5)"


# --- verify_author_citation -----------------------------------------


class TestVerifyAuthorCitation:
    def test_correct_citation_adopted(self) -> None:
        p = _passage(sura=1, aya_start=1, aya_end=1)
        result = verify_author_citation(passage=p, author_citation="1:1")
        assert result.verdict == CitationVerdict.ADOPTED
        assert result.parsed_author == (1, 1, 1)
        assert result.canonical_citation == "(Sure 1, Vers 1)"

    def test_incorrect_citation_flagged(self) -> None:
        """§4.15.4: 'Yes: System verifies. Correct → adopt. Incorrect
        → inform user.' We flag with INCORRECT verdict; UI uses the
        canonical_citation field to show what the system thinks the
        right answer is."""
        p = _passage(sura=1, aya_start=1, aya_end=1)
        result = verify_author_citation(passage=p, author_citation="2:5")
        assert result.verdict == CitationVerdict.INCORRECT
        assert result.parsed_author == (2, 5, 5)
        assert result.canonical_citation == "(Sure 1, Vers 1)"

    def test_no_author_citation_when_none(self) -> None:
        """§4.15.4: 'No: Passage remains empty.' We surface
        NO_AUTHOR_CITATION; UI offers the canonical insertion."""
        p = _passage(sura=1, aya_start=1, aya_end=1)
        result = verify_author_citation(passage=p, author_citation=None)
        assert result.verdict == CitationVerdict.NO_AUTHOR_CITATION
        assert result.parsed_author is None
        assert result.canonical_citation == "(Sure 1, Vers 1)"

    def test_no_author_citation_when_empty(self) -> None:
        p = _passage(sura=1, aya_start=1, aya_end=1)
        result = verify_author_citation(passage=p, author_citation="   ")
        assert result.verdict == CitationVerdict.NO_AUTHOR_CITATION

    def test_no_author_citation_when_unparseable(self) -> None:
        """A free-text reference without coordinates is treated as
        'no author citation' — the system can't verify it."""
        p = _passage(sura=1, aya_start=1, aya_end=1)
        result = verify_author_citation(passage=p, author_citation="see the opening sūra")
        assert result.verdict == CitationVerdict.NO_AUTHOR_CITATION

    def test_range_match_adopted(self) -> None:
        p = _passage(sura=1, aya_start=1, aya_end=7)
        result = verify_author_citation(passage=p, author_citation="Sure 1, Vers 1-7")
        assert result.verdict == CitationVerdict.ADOPTED
        assert result.parsed_author == (1, 1, 7)

    def test_partial_range_incorrect(self) -> None:
        p = _passage(sura=1, aya_start=1, aya_end=7)
        result = verify_author_citation(passage=p, author_citation="1:1-3")
        assert result.verdict == CitationVerdict.INCORRECT

    def test_en_lang_verifies_with_en_format(self) -> None:
        p = _passage(sura=1, aya_start=1, aya_end=1)
        result = verify_author_citation(passage=p, author_citation="1:1", lang="en")
        assert result.verdict == CitationVerdict.ADOPTED
        assert result.canonical_citation == "(Surah 1, verse 1)"
