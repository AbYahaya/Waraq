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


def has_ei2_violations(text: str) -> bool:
    """True if `text` contains any glyph the EI2-with-Q-and-J rule rewrites.

    Predicate counterpart to `enforce_ei2_transliteration`. Used by the
    Phase 3 sub-batch B pre-export verifier as defense-in-depth: when
    auto-normalize at translation output and on the manual-edit save
    path runs as expected, this returns False everywhere — but if any
    write path bypasses normalization (e.g., a raw DB insert from a
    future tool), the verifier catches the leftover violation before
    export ships.

    The substring checks for `Dj`/`dj`/`DJ` are CASE-SENSITIVE on
    purpose: `enforce_ei2_transliteration` only rewrites those three
    forms (it does NOT touch `dJ` or other mixed-case oddities — those
    are out of scope for EI2). The detector mirrors the rewriter exactly.
    """
    if not text:
        return False
    if _K_DOT_BELOW_CAP in text or _K_DOT_BELOW_LO in text:
        return True
    return "DJ" in text or "Dj" in text or "dj" in text
