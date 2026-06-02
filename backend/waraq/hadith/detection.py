"""Hadith-like text detection helpers.

These heuristics are intentionally broad. They do not prove a passage is a
verified hadith; they decide whether the safer path is to route the passage
through hadith verification/review instead of treating it as ordinary prose.
"""

from __future__ import annotations


def looks_like_hadith(text: str) -> bool:
    lowered = text.strip()
    if not lowered:
        return False
    markers = (
        "قال رسول",
        "رسول الله ﷺ قال",
        "رسول الله صلى الله عليه وسلم قال",
        "صلى الله عليه وسلم",
        "ﷺ قال",
        "روى",
        "رواه",
        "حدثنا",
        "وفي رواية",
        "بروايات",
        "حديثاً",
        "حديثا",
        "حَدِيثاً",
        "حَدِيث",
        "عن أبي",
        "عن عائشة",
        "عن ابن",
        "أبو هريرة",
        "أبي هريرة",
        "أبو سعيد",
        "أبي سعيد",
        "ابن مسعود",
        "ابن عمر",
        "ابن عباس",
        "معاذ بن جبل",
        "أبي الدرداء",
    )
    return any(marker in lowered for marker in markers)


__all__ = ["looks_like_hadith"]
