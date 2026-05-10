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
    """NFC + Tatweel + diacritic-strip + Alif-variant + long-ā-collapse
    yielding the skeletal-letter lookup key for AR-Referenzbestand
    matching (§4.15.2 OCR-stage local matching). Whitespace collapsed.

    Hafs Uthmani / modern bare-letter alignment: Hafs uses a dagger
    alef (U+0670) where modern text uses an explicit alif (U+0627),
    AND inconsistently between the two: `ذلك` is defective in both,
    while `الكتاب` is plene in modern bare but defective (dagger-
    alef) in Hafs (`ٱلْكِتَٰبُ`). To align both consistently we:

      1. Strip the dagger alef (along with all other diacritics).
      2. Strip every non-word-initial U+0627 (explicit alif).

    This drops the long-ā marker uniformly. Both `ذلك` (modern) and
    `ذَٰلِكَ` (Hafs) collapse to `ذلك`; both `الكتاب` (modern) and
    `ٱلْكِتَٰبُ` (Hafs) collapse to `الكتب`. The leading "ال" definite
    article preserves its initial alif because step 2 keeps word-
    initial alifs.

    Trade-off: this collapses some distinct words to the same
    skeleton (e.g., `كاتب` "writer" and `كتب` "he wrote"). For v1.0
    Qurʾān recognition that's acceptable — `find_by_skeleton` returns
    a list, the consensus engine handles disambiguation, and the
    morphology-aware refinement is Phase 4 (CAMeL Tools).

    Alif/long-ā collapse is deliberately scoped to this function —
    `normalize_for_compare` (V-0 detector) does NOT apply it, so the
    Hadith §4.16.7 V-0/V-1 boundary stays canon-faithful."""
    nfc = unicodedata.normalize("NFC", text)
    stripped = strip_arabic_diacritics(nfc)
    normalized = stripped.translate(_OCR_LETTER_NORMALIZATION)
    out_words: list[str] = []
    for word in normalized.split():
        if not word:
            continue
        # Keep the first character; strip any U+0627 elsewhere.
        out_words.append(word[0] + word[1:].replace("ا", ""))
    return " ".join(out_words)


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
