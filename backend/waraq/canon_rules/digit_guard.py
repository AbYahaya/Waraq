"""Western-digit standard per Dokument 1 §2.2.

> "Western digits everywhere – never Arabic-Indic digits. Violations of
>  the digit standard are handled near the guard layer and are blocking.
>  No audit case, no user judgment – direct system mechanism."

This module supplies the two halves of the rule:

- `to_western_digits` — the deterministic system mechanism that converts
  Arabic-Indic digits (٠-٩, U+0660–U+0669) and Eastern Arabic-Indic
  digits (۰-۹, U+06F0–U+06F9) to Western digits (0-9).
- `has_arabic_indic_digits` — the predicate the guard-near pre-export
  gate uses to refuse opening the preflight dialog when violations
  remain (Phase 3).

Per the canon both digit ranges count as Arabic-Indic and must be
normalized: the U+0660 range is "Arabic" (Mashriq), the U+06F0 range
is "Eastern Arabic-Indic" (Persian/Urdu). Both produce the same Western
digit; the conversion is locale-agnostic.
"""

from __future__ import annotations

# U+0660 through U+0669 — Arabic-Indic digits (Mashriq).
_ARABIC_INDIC_OFFSET = 0x0660
# U+06F0 through U+06F9 — Eastern Arabic-Indic digits (Persian/Urdu).
_EASTERN_ARABIC_INDIC_OFFSET = 0x06F0

_DIGIT_TRANSLATION_TABLE = str.maketrans(
    {chr(_ARABIC_INDIC_OFFSET + i): str(i) for i in range(10)}
    | {chr(_EASTERN_ARABIC_INDIC_OFFSET + i): str(i) for i in range(10)}
)


def to_western_digits(text: str) -> str:
    """Convert every Arabic-Indic / Eastern-Arabic-Indic digit to its
    Western equivalent. Idempotent."""
    if not text:
        return text
    return text.translate(_DIGIT_TRANSLATION_TABLE)


def has_arabic_indic_digits(text: str) -> bool:
    """True if `text` contains any digit from either Arabic-Indic range."""
    if not text:
        return False
    for ch in text:
        cp = ord(ch)
        if 0x0660 <= cp <= 0x0669 or 0x06F0 <= cp <= 0x06F9:
            return True
    return False
