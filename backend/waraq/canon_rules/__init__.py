"""Mandatory product-logic enforcers per Dokument 1 §2.2.

These are deterministic system mechanisms — not user judgments. The
canon mandates them as direct rules, not audit cases:

- Western digits everywhere (§2.2).
- EI2 transliteration with Q (instead of Ḳ) and J (instead of Dj) (§2.2).
- Religious formulas as Unicode ﷺ ﷻ (§2.2).

Each function is idempotent and pure — calling twice yields the same
result as calling once. Tests live in `tests/canon_rules/`.

The module is the single canonical entry point for these rules; both
the translation pipeline (post-LLM output) and any future manual-edit
write path should call `apply_all`.

Pre-export blocking enforcement (the "guard-near" / "blocking" half of
§2.2 + §4.7.3) is a Phase 3 item — building the auto-normalization
first ensures most violations never reach the export step at all.
"""

from __future__ import annotations

from waraq.canon_rules.digit_guard import (
    has_arabic_indic_digits,
    to_western_digits,
)
from waraq.canon_rules.religious_formulas import normalize_religious_formulas
from waraq.canon_rules.transliteration import enforce_ei2_transliteration


def apply_all(text: str) -> str:
    """Apply every canon rule in canonical order.

    Order matters: religious-formula normalization first (replaces
    multi-character spellings with single Unicode glyphs); then EI2
    transliteration (small character substitutions); then digit
    normalization (Arabic-Indic → Western).

    Idempotent — `apply_all(apply_all(t)) == apply_all(t)`.
    """
    if not text:
        return text
    out = normalize_religious_formulas(text)
    out = enforce_ei2_transliteration(out)
    out = to_western_digits(out)
    return out


__all__ = [
    "apply_all",
    "enforce_ei2_transliteration",
    "has_arabic_indic_digits",
    "normalize_religious_formulas",
    "to_western_digits",
]
