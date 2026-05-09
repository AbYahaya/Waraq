"""EI2 transliteration enforcement per Dokument 1 §2.2.

> "Transliteration standard: EI2 with Q (instead of Ḳ) and J (instead of Dj)."

EI2 (the Encyclopaedia of Islam, 2nd ed. transliteration system) uses
Ḳ and Dj for ق and ج respectively. The Waraq canon mandates two
substitutions on top of standard EI2:

- Ḳ / ḳ  →  Q / q
- Dj / dj  →  J / j

This module supplies the deterministic substitution. It applies only to
those specific glyphs and digraphs; all other EI2 conventions
(macrons, dots, ligatures) pass through untouched.

Idempotent — running twice yields the same output as running once.
"""

from __future__ import annotations

# Single-codepoint substitutions for Ḳ / ḳ.
# U+1E32 LATIN CAPITAL LETTER K WITH LINE BELOW
# U+1E33 LATIN SMALL LETTER K WITH LINE BELOW
_K_DOT_BELOW_CAP = "Ḳ"  # Ḳ
_K_DOT_BELOW_LO = "ḳ"  # ḳ

# The Dj/dj substitution is a digraph — not a single codepoint — so
# we handle it via str.replace rather than translate.


def enforce_ei2_transliteration(text: str) -> str:
    """Replace Ḳ → Q, ḳ → q, Dj → J, dj → j. Idempotent.

    The Dj → J substitution is case-aware: a leading capital remains
    capital. Within an all-uppercase run (`DJINNI`) the substitution
    still preserves casing (`JINNI`). Word-internal ``dj`` lowercase is
    treated as `j`.
    """
    if not text:
        return text

    out = text.replace(_K_DOT_BELOW_CAP, "Q").replace(_K_DOT_BELOW_LO, "q")

    # Replace DJ (uppercase pair) → J, Dj (mixed) → J, dj (lowercase) → j.
    # Order matters: do the casefold-distinguished pairs before any
    # all-uppercase variants, otherwise "Dj" would partially match a
    # general "dj" replacement.
    out = out.replace("DJ", "J").replace("Dj", "J").replace("dj", "j")
    return out
