"""Shared Arabic-text utilities.

Used by:
- `waraq.hadith.vocalization` for V-0/V-1/V-2 classification (skeleton
  equality is the V-1 ↔ V-2 boundary).
- `waraq.quran` for AR-Referenzbestand local matching (skeleton form
  is the OCR-stage matching key per §4.15.2 "local-only in OCR phase").

The Unicode ranges below cover Arabic combining marks per Unicode 15.0:

  U+0640         — Tatweel (kashida) — pure rendering, never meaning.
  U+064B..U+065F — Arabic diacritics (Fathatan, Dammatan, Kasratan,
                   Fatha, Damma, Kasra, Shadda, Sukun, Quranic marks).
  U+0670         — Arabic letter superscript Alef.
  U+06D6..U+06DC — Arabic small high marks (Quranic notation).
  U+06DF..U+06E4 — Arabic small low marks.
  U+06E7..U+06E8 — Arabic small high marks.
  U+06EA..U+06ED — Arabic empty centre / rounded zero / mini.
"""

from __future__ import annotations

import unicodedata

TATWEEL = "ـ"  # U+0640 — Arabic Tatweel (kashida).

_DIACRITIC_RANGES: tuple[tuple[int, int], ...] = (
    (0x064B, 0x065F),
    (0x0670, 0x0670),
    (0x06D6, 0x06DC),
    (0x06DF, 0x06E4),
    (0x06E7, 0x06E8),
    (0x06EA, 0x06ED),
)

# Alif / similar-letter variants that the AR-Referenzbestand skeleton
# matcher (§4.15.2 OCR-stage local matching) collapses to the bare
# letter. Used by `to_skeleton` only — `normalize_for_compare` (V-0
# detector) does NOT collapse these because §4.16.7 V-1 explicitly
# names "Hamzat al-Waṣl/Qaṭʿ without meaning change" as V-1, not V-0.
_OCR_LETTER_NORMALIZATION = str.maketrans(
    {
        "ٱ": "ا",  # Alif Waṣl  → Alif
        "أ": "ا",  # Alif Hamza-above → Alif
        "إ": "ا",  # Alif Hamza-below → Alif
        "آ": "ا",  # Alif Madda → Alif
    }
)


def strip_arabic_diacritics(text: str) -> str:
    """Remove Arabic combining marks + Tatweel; leave skeletal letters.

    Idempotent: applying twice is the same as once.
    """
    out: list[str] = []
    for ch in text:
        cp = ord(ch)
        if ch == TATWEEL:
            continue
        if any(start <= cp <= end for start, end in _DIACRITIC_RANGES):
            continue
        out.append(ch)
    return "".join(out)


def to_skeleton(text: str) -> str:
    """NFC-normalize, strip Tatweel, strip all diacritics, normalize
    Alif variants — yields the skeletal-letter form used as the lookup
    key for AR-Referenzbestand matching (§4.15.2 OCR-stage local
    matching). Whitespace runs collapsed to single spaces.

    Alif normalization is deliberately scoped to this function only —
    `normalize_for_compare` (V-0 detector) does NOT apply it, so the
    Hadith §4.16.7 V-0/V-1 boundary stays canon-faithful."""
    nfc = unicodedata.normalize("NFC", text)
    stripped = strip_arabic_diacritics(nfc)
    normalized = stripped.translate(_OCR_LETTER_NORMALIZATION)
    return " ".join(normalized.split())


def normalize_for_compare(text: str) -> str:
    """NFC + Tatweel-strip — keeps diacritics. Used by V-0 detection
    (orthographic-only deviation per §4.16.7)."""
    return unicodedata.normalize("NFC", text).replace(TATWEEL, "")


__all__ = [
    "TATWEEL",
    "normalize_for_compare",
    "strip_arabic_diacritics",
    "to_skeleton",
]
