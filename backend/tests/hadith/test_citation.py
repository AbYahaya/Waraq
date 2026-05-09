"""§4.16.3 source-citation format DE/EN tests."""

from __future__ import annotations

from waraq.hadith import (
    SourceCitation,
    format_source_citation_de,
    format_source_citation_en,
)

# Canonical examples from Dokument 1 §4.16.3:
#   German:  (Sahih al-Bukhari, Nr. 1; Sahih Muslim, Nr. 1907)
#   English: (Sahih al-Bukhari 1; Sahih Muslim 1907)


class TestGermanFormat:
    def test_canonical_example_two_works(self) -> None:
        cits = [
            SourceCitation(work="Sahih al-Bukhari", number=1),
            SourceCitation(work="Sahih Muslim", number=1907),
        ]
        assert (
            format_source_citation_de(cits) == "(Sahih al-Bukhari, Nr. 1; Sahih Muslim, Nr. 1907)"
        )

    def test_single_work(self) -> None:
        cits = [SourceCitation(work="Sahih al-Bukhari", number=42)]
        assert format_source_citation_de(cits) == "(Sahih al-Bukhari, Nr. 42)"

    def test_empty_list_returns_empty_string(self) -> None:
        assert format_source_citation_de([]) == ""

    def test_string_number_passthrough(self) -> None:
        # Some sources carry letter suffixes; pass-through verbatim.
        cits = [SourceCitation(work="Sunan Abi Dawud", number="1a")]
        assert format_source_citation_de(cits) == "(Sunan Abi Dawud, Nr. 1a)"


class TestEnglishFormat:
    def test_canonical_example_two_works(self) -> None:
        cits = [
            SourceCitation(work="Sahih al-Bukhari", number=1),
            SourceCitation(work="Sahih Muslim", number=1907),
        ]
        assert format_source_citation_en(cits) == "(Sahih al-Bukhari 1; Sahih Muslim 1907)"

    def test_single_work(self) -> None:
        cits = [SourceCitation(work="Sahih al-Bukhari", number=42)]
        assert format_source_citation_en(cits) == "(Sahih al-Bukhari 42)"

    def test_empty_list_returns_empty_string(self) -> None:
        assert format_source_citation_en([]) == ""

    def test_no_literal_nr_in_english(self) -> None:
        # The DE form uses ", Nr. <n>"; the EN form uses " <n>".
        # Regression on accidental DE-style EN output.
        cits = [SourceCitation(work="Sahih al-Bukhari", number=1)]
        assert "Nr." not in format_source_citation_en(cits)


class TestVerbatim:
    def test_work_name_not_normalized(self) -> None:
        # §2.4 verbatim discipline — the formatter does not normalize
        # work names; sources control the exact label.
        cits = [SourceCitation(work="Sahih al-Bukhari (Egyptian)", number=1)]
        assert format_source_citation_de(cits) == "(Sahih al-Bukhari (Egyptian), Nr. 1)"

    def test_three_works_separator(self) -> None:
        cits = [
            SourceCitation(work="Sahih al-Bukhari", number=1),
            SourceCitation(work="Sahih Muslim", number=1907),
            SourceCitation(work="Sunan Abi Dawud", number=4607),
        ]
        de = format_source_citation_de(cits)
        en = format_source_citation_en(cits)
        # Two semicolons → three entries.
        assert de.count(";") == 2
        assert en.count(";") == 2
