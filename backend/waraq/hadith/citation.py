"""§4.16.3 Hadith source-citation format (DE / EN).

Per Dokument 1 §4.16.3:

  - **German:** (Sahih al-Bukhari, Nr. 1; Sahih Muslim, Nr. 1907)
  - **English:** (Sahih al-Bukhari 1; Sahih Muslim 1907)

Both formats wrap the citation in parentheses; entries separated by
"; ". The DE form uses "Nr. <number>" between the work name and the
hadith number; EN omits the literal "Nr." and just appends the number
after a single space.

Work names (e.g., "Sahih al-Bukhari", "Sahih Muslim", "Sunan Abi
Dawud", "Jamiʿ at-Tirmidhi", "Sunan an-Nasaʾi", "Sunan Ibn Majah") are
caller-supplied — the canonical work label is determined by the source
client (sunnah.com, dorar.net, etc.) and not normalized here. Work
labels are written verbatim per §2.4 verbatim discipline for canonical
identifier-like terms.

The EN hadith output canon (§4.16.8) is its own primary translation
path parallel to DE. The DE/EN citation format split below is the only
language-specifically governed piece of the hadith pipeline at the
formatting layer (transliteration is governed by §2.2 separately).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceCitation:
    """One canonical source citation entry.

    Attributes:
        work: Work label as the source client returned it. Verbatim,
            per §2.4 discipline.
        number: Hadith number within the work. Integer per §4.16.3
            examples; callers that have a fractional/letter suffix
            (e.g., "1a") may pass it as a string.
    """

    work: str
    number: int | str


def _format_number(number: int | str) -> str:
    return str(number)


def format_source_citation_de(citations: list[SourceCitation]) -> str:
    """Format a list of SourceCitation as the §4.16.3 German form:
    `(Sahih al-Bukhari, Nr. 1; Sahih Muslim, Nr. 1907)`.

    Empty list → empty string (no parentheses).
    """
    if not citations:
        return ""
    parts = [f"{c.work}, Nr. {_format_number(c.number)}" for c in citations]
    return f"({'; '.join(parts)})"


def format_source_citation_en(citations: list[SourceCitation]) -> str:
    """Format a list of SourceCitation as the §4.16.3 English form:
    `(Sahih al-Bukhari 1; Sahih Muslim 1907)`.

    Empty list → empty string.
    """
    if not citations:
        return ""
    parts = [f"{c.work} {_format_number(c.number)}" for c in citations]
    return f"({'; '.join(parts)})"


__all__ = [
    "SourceCitation",
    "format_source_citation_de",
    "format_source_citation_en",
]
