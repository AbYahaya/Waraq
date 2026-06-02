"""Lightweight sunnah.com citation extraction.

The sunnah.com API path needs a canonical collection slug plus hadith
number. This module recognizes common inline citations so production
verification can exercise P-1 when the source text already provides
enough address information.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SunnahLookup:
    collection: str
    hadith_number: int
    matched_text: str


_COLLECTION_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("bukhari", ("bukhari", "al-bukhari", "al bukhari", "البخاري")),
    ("muslim", ("muslim", "مسلم")),
    ("abudawud", ("abu dawud", "abi dawud", "abī dāwūd", "أبو داود", "ابي داود")),
    ("tirmidhi", ("tirmidhi", "at-tirmidhi", "al-tirmidhi", "الترمذي")),
    ("nasai", ("nasai", "nasa'i", "an-nasa'i", "النسائي")),
    ("ibnmajah", ("ibn majah", "ibn mājah", "ابن ماجه")),
    ("malik", ("muwatta", "muwatta malik", "موطأ", "مالك")),
    ("ahmad", ("ahmad", "musnad ahmad", "أحمد")),
)

_NUMBER_PREFIX = r"(?:no\.?|nr\.?|number|hadith|حديث|ح\.?)?\s*"
_NUMBER_RE = r"(?P<number>[0-9٠-٩]+)"


def extract_sunnah_lookup(text: str) -> SunnahLookup | None:
    """Return the first recognizable sunnah.com direct lookup.

    Recognized forms include examples such as:
    - Sahih al-Bukhari 1
    - Bukhari, no. 1
    - صحيح البخاري حديث 1
    """
    normalized = _normalize_digits(text)
    for collection, aliases in _COLLECTION_ALIASES:
        for alias in aliases:
            pattern = re.compile(
                rf"(?:sahih|sunan|jami|musnad|muwatta|صحيح|سنن|جامع|مسند)?\s*"
                rf"{re.escape(alias)}\s*[,،:؛-]?\s*{_NUMBER_PREFIX}{_NUMBER_RE}",
                re.IGNORECASE,
            )
            match = pattern.search(normalized)
            if match is None:
                continue
            try:
                number = int(match.group("number"))
            except ValueError:
                continue
            if number > 0:
                return SunnahLookup(
                    collection=collection,
                    hadith_number=number,
                    matched_text=match.group(0).strip(),
                )
    return None


def _normalize_digits(text: str) -> str:
    return text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))


__all__ = ["SunnahLookup", "extract_sunnah_lookup"]
