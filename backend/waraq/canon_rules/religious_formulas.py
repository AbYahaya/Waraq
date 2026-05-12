"""Religious-formula Unicode normalization per Dokument 1 §2.2.

> "Religious formulas as calligraphy/Unicode: ﷺ, ﷻ."

Two single-codepoint glyphs carry the religious-formula calligraphy:

- U+FDFA  ﷺ  — Arabic ligature *ṣallā Allāhu ʿalayhi wa-sallam* (the
  honorific applied to the Prophet Muḥammad).
- U+FDFB  ﷻ  — Arabic ligature *jalla jalāluhu* (the honorific applied
  to the divine name).

Authors and OCR pipelines often spell these out as multi-character
sequences instead of using the calligraphic glyph. Per §2.2 the canon
mandates the Unicode glyph; this module normalizes common spelled-out
spellings to the single-codepoint form.

Conservative match: we only normalize *unambiguous* spelled-out forms
(exact text matches with optional surrounding whitespace). We do NOT
attempt to match abbreviations like "(s.a.w.)" or English glosses —
those carry semantic ambiguity and need user judgment, which §2.2
explicitly excludes ("direct system mechanism, no user judgment" —
meaning the rule applies WHEN it applies, deterministically).

The display optionality from §4.17 (calligraphy / German translation /
Arabic spelled out) is a per-display setting and is layered ON TOP of
canonical storage; this module governs canonical storage.

Idempotent.
"""

from __future__ import annotations

# Canonical Unicode glyphs.
SALLA_ALLAHU_ALAYHI_WA_SALLAM = "ﷺ"  # ﷺ
JALLA_JALALUHU = "ﷻ"  # ﷻ


# Spelled-out variants we accept as unambiguous synonyms of ﷺ.
# Each matched substring is replaced with the calligraphic glyph.
# Order: longer / more-specific spellings first to avoid partial matches.
_SPELLED_OUT_SAW: tuple[str, ...] = (
    "صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ",  # fully-vocalized
    "صَلَّى اللهُ عَلَيْهِ وَسَلَّمَ",
    "صلى الله عليه وسلم",  # bare consonantal
    "صلى الله عليه و سلم",  # spaced waw
)

# Spelled-out variants for ﷻ.
_SPELLED_OUT_JJ: tuple[str, ...] = (
    "جَلَّ جَلَالُهُ",
    "جَلَّ جَلَالُه",
    "جل جلاله",
)


def normalize_religious_formulas(text: str) -> str:
    """Replace spelled-out religious-formula sequences with their canonical
    Unicode glyphs (ﷺ / ﷻ). Idempotent."""
    if not text:
        return text
    out = text
    for src in _SPELLED_OUT_SAW:
        out = out.replace(src, SALLA_ALLAHU_ALAYHI_WA_SALLAM)
    for src in _SPELLED_OUT_JJ:
        out = out.replace(src, JALLA_JALALUHU)
    return out


def has_religious_formula_violations(text: str) -> bool:
    """Predicate counterpart to `normalize_religious_formulas`.

    Returns True iff `text` contains any unambiguous spelled-out form
    of ﷺ / ﷻ that the normalizer would collapse. Wired into the §2.2
    pre-export verifier as the third canonical-rule kind alongside
    digit + EI2 violations: a write path that bypassed `apply_all`
    (raw DB insert, partial migration, stale fixture) is caught
    before the export artefact ships.

    Idempotent. Pure: no side effects, no I/O.
    """
    if not text:
        return False
    if any(src in text for src in _SPELLED_OUT_SAW):
        return True
    return any(src in text for src in _SPELLED_OUT_JJ)


__all__ = [
    "JALLA_JALALUHU",
    "SALLA_ALLAHU_ALAYHI_WA_SALLAM",
    "has_religious_formula_violations",
    "normalize_religious_formulas",
]
