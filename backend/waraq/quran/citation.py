"""§4.15.4 — Qurʾān source citation logic.

Per Dokument 1 §4.15.4:

  Order in the text: Arabic → German translation → source citation.

  Source citation logic:
    1. System recognizes Quranic verse.
    2. Did the author provide a source citation?
       - Yes: System verifies. Correct → adopt. Incorrect → inform user.
       - No: Passage remains empty.
    3. In both cases: User is given the option to insert canonical
       source citation.

This module provides the **verification** half of step 2: given a
recognized passage and an author-supplied citation, decide whether
the citation matches what the system recognized. The "User is given
the option to insert canonical source citation" step is a UI hook —
this module supplies `format_canonical_citation` so the UI can show
what would be inserted.

Citation format (canonical Qurʾān citation per §4.15):
  - DE: `(Sure 1, Vers 1)`            — single āya
        `(Sure 1, Vers 1–7)`          — multi-āya range
  - EN: `(Surah 1, verse 1)`          — single āya
        `(Surah 1, verses 1–7)`       — multi-āya range

The DE/EN forms differ from §4.16.3 Hadith citation format (which uses
`(Sahih al-Bukhari, Nr. 1)`) — Qurʾān citation references coordinate
positions in the Qurʾān, Hadith citation references collection +
hadith number. v1.0 Qurʾān-citation format below mirrors the §4.16.3
shape (parentheses, semicolons for multi-source) so the editor's
citation block format reads consistently across both.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from waraq.arabic import to_skeleton
from waraq.schemas import ProjectQuranPassage


class CitationVerdict(StrEnum):
    """§4.15.4 step 2 verdicts."""

    NO_AUTHOR_CITATION = "no_author_citation"
    ADOPTED = "adopted"
    INCORRECT = "incorrect"


@dataclass(frozen=True, slots=True)
class CitationVerificationResult:
    verdict: CitationVerdict
    canonical_citation: str
    author_citation: str | None
    parsed_author: tuple[int, int, int] | None  # (sura, aya_start, aya_end) or None


# Range-detection regex: find any "<digits><dash><digits>" anywhere
# in the input. Used to disambiguate (sura, aya, aya2-as-range) from
# (sura, aya, aya2-as-trailing-annotation).
_RANGE_DETECT_RE = re.compile(r"\d+\s*[-–—]\s*\d+")
_NUMBER_RE = re.compile(r"\d+")
_ARABIC_SURA_NAMES: tuple[str, ...] = (
    "الفاتحة",
    "البقرة",
    "آل عمران",
    "النساء",
    "المائدة",
    "الأنعام",
    "الأعراف",
    "الأنفال",
    "التوبة",
    "يونس",
    "هود",
    "يوسف",
    "الرعد",
    "إبراهيم",
    "الحجر",
    "النحل",
    "الإسراء",
    "الكهف",
    "مريم",
    "طه",
    "الأنبياء",
    "الحج",
    "المؤمنون",
    "النور",
    "الفرقان",
    "الشعراء",
    "النمل",
    "القصص",
    "العنكبوت",
    "الروم",
    "لقمان",
    "السجدة",
    "الأحزاب",
    "سبأ",
    "فاطر",
    "يس",
    "الصافات",
    "ص",
    "الزمر",
    "غافر",
    "فصلت",
    "الشورى",
    "الزخرف",
    "الدخان",
    "الجاثية",
    "الأحقاف",
    "محمد",
    "الفتح",
    "الحجرات",
    "ق",
    "الذاريات",
    "الطور",
    "النجم",
    "القمر",
    "الرحمن",
    "الواقعة",
    "الحديد",
    "المجادلة",
    "الحشر",
    "الممتحنة",
    "الصف",
    "الجمعة",
    "المنافقون",
    "التغابن",
    "الطلاق",
    "التحريم",
    "الملك",
    "القلم",
    "الحاقة",
    "المعارج",
    "نوح",
    "الجن",
    "المزمل",
    "المدثر",
    "القيامة",
    "الإنسان",
    "المرسلات",
    "النبأ",
    "النازعات",
    "عبس",
    "التكوير",
    "الانفطار",
    "المطففين",
    "الانشقاق",
    "البروج",
    "الطارق",
    "الأعلى",
    "الغاشية",
    "الفجر",
    "البلد",
    "الشمس",
    "الليل",
    "الضحى",
    "الشرح",
    "التين",
    "العلق",
    "القدر",
    "البينة",
    "الزلزلة",
    "العاديات",
    "القارعة",
    "التكاثر",
    "العصر",
    "الهمزة",
    "الفيل",
    "قريش",
    "الماعون",
    "الكوثر",
    "الكافرون",
    "النصر",
    "المسد",
    "الإخلاص",
    "الفلق",
    "الناس",
)
_SURA_NAME_TO_INDEX: dict[str, int] = {}
for index, name in enumerate(_ARABIC_SURA_NAMES, start=1):
    skeleton = to_skeleton(name).replace(" ", "")
    _SURA_NAME_TO_INDEX[skeleton] = index
    if skeleton.startswith("ال"):
        _SURA_NAME_TO_INDEX[skeleton[1:]] = index


def parse_author_citation(citation: str) -> tuple[int, int, int] | None:
    """Parse `(sura, aya_start, aya_end)` from a free-form citation.

    The matcher is heuristic and prose-tolerant: it pulls all
    integers from the input and reads the first as sura, the second
    as aya. If a third integer is present AND the input contains a
    dash-separated range pattern (`<n>-<n>`), the third integer is
    treated as `aya_end`; otherwise `aya_end == aya_start`.

    Accepted shapes (non-exhaustive):
        "1:1", "1:1-7", "1:1–7"
        "Sure 1, Vers 1", "Sure 2, Vers 255", "Sure 1, Vers 1-7"
        "Surah 1, verse 1", "Surah 2, verses 1-7"
        "(1:1)", "[1:1]"
        "سورة 1، 1"

    Returns `None` when:
      - no integers found OR fewer than two
      - sura out of canonical range 1..114
      - aya_start < 1
      - aya_end < aya_start (inverted range)
    """
    if not citation:
        return None
    numbers = [int(m.group()) for m in _NUMBER_RE.finditer(citation)]
    by_name = _parse_arabic_sura_name_citation(citation, numbers)
    if by_name is not None:
        return by_name
    if len(numbers) < 2:
        return None
    sura = numbers[0]
    aya1 = numbers[1]
    aya2 = aya1
    if len(numbers) >= 3 and _RANGE_DETECT_RE.search(citation):
        aya2 = numbers[2]
    if not 1 <= sura <= 114:
        return None
    if aya1 < 1 or aya2 < aya1:
        return None
    return (sura, aya1, aya2)


def _parse_arabic_sura_name_citation(
    citation: str,
    numbers: list[int],
) -> tuple[int, int, int] | None:
    if len(numbers) < 1:
        return None
    citation_skeleton = to_skeleton(citation).replace(" ", "")
    matched_sura: int | None = None
    for name_skeleton, sura_index in sorted(
        _SURA_NAME_TO_INDEX.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if name_skeleton and name_skeleton in citation_skeleton:
            matched_sura = sura_index
            break
    if matched_sura is None:
        return None
    aya1 = numbers[0]
    aya2 = aya1
    if len(numbers) >= 2 and _RANGE_DETECT_RE.search(citation):
        aya2 = numbers[1]
    if aya1 < 1 or aya2 < aya1:
        return None
    return (matched_sura, aya1, aya2)


def format_canonical_citation(
    *,
    passage: ProjectQuranPassage,
    lang: str = "de",
) -> str:
    """Produce the canonical Qurʾān citation string for a passage.

    `lang="de"` → "(Sure S, Vers A)" / "(Sure S, Verse A–B)"
    `lang="en"` → "(Surah S, verse A)" / "(Surah S, verses A–B)"
    """
    sura = passage.sura_index
    a1 = passage.aya_index_start
    a2 = passage.aya_index_end
    is_range = a1 != a2
    if lang.startswith("en"):
        if is_range:
            return f"(Surah {sura}, verses {a1}–{a2})"
        return f"(Surah {sura}, verse {a1})"
    if is_range:
        return f"(Sure {sura}, Verse {a1}–{a2})"
    return f"(Sure {sura}, Vers {a1})"


def verify_author_citation(
    *,
    passage: ProjectQuranPassage,
    author_citation: str | None,
    lang: str = "de",
) -> CitationVerificationResult:
    """§4.15.4 step 2 — verify the author's citation against the
    recognized passage.

    - `author_citation = None` (or empty/no parseable pattern):
      verdict = `NO_AUTHOR_CITATION`. Per canon: "Passage remains empty."
    - Citation parses to `(sura, aya_start, aya_end)` matching the
      recognized passage exactly: verdict = `ADOPTED`.
    - Citation parses but disagrees with the recognized coords:
      verdict = `INCORRECT`. Per canon: "inform user."

    `canonical_citation` is always set so the UI can offer the
    "insert canonical source citation" action regardless of verdict.
    """
    canonical = format_canonical_citation(passage=passage, lang=lang)
    if not author_citation or not author_citation.strip():
        return CitationVerificationResult(
            verdict=CitationVerdict.NO_AUTHOR_CITATION,
            canonical_citation=canonical,
            author_citation=author_citation,
            parsed_author=None,
        )
    parsed = parse_author_citation(author_citation)
    if parsed is None:
        # Not parseable as a sura:aya reference — treated as
        # "no author citation" per canon ("Did the author provide a
        # source citation?"). Free-text references that don't carry
        # coordinates are not citations the system can verify.
        return CitationVerificationResult(
            verdict=CitationVerdict.NO_AUTHOR_CITATION,
            canonical_citation=canonical,
            author_citation=author_citation,
            parsed_author=None,
        )
    expected = (passage.sura_index, passage.aya_index_start, passage.aya_index_end)
    verdict = CitationVerdict.ADOPTED if parsed == expected else CitationVerdict.INCORRECT
    return CitationVerificationResult(
        verdict=verdict,
        canonical_citation=canonical,
        author_citation=author_citation,
        parsed_author=parsed,
    )


__all__ = [
    "CitationVerdict",
    "CitationVerificationResult",
    "format_canonical_citation",
    "parse_author_citation",
    "verify_author_citation",
]
