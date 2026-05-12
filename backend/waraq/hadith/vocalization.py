"""§4.16.7 V-0/V-1/V-2 vocalization classifier.

Pure-text classifier — given two vocalized Arabic strings (e.g., the
matn from two different hadith sources, or a vocalization candidate vs
the chosen reference), returns the §4.16.7 escalation class:

  - V-0: orthographic-technical variants only (Tatweel, Unicode
         normalization, pure rendering variants). Two strings differ
         ONLY in characters that the canon explicitly names as
         "without sound or meaning change".
  - V-1: deviations in vocalization marks that do NOT change meaning
         (vocalization density, Shadda without word-identity change,
         Hamzat al-Waṣl/Qaṭʿ without meaning change).
  - V-2: deviation in non-diacritic skeletal letters — case/mood,
         active/passive/stem, Shadda with word-identity change, Hamza
         with meaning change, matn-lexeme deviation. The skeleton
         differs.

**Fallback rule (§4.16.7):** "with ambiguity of the type assignment,
the higher class is applied; no silent down-classification."

V-1 ↔ V-2 boundary
------------------
Skeletal-letter equivalence is the deterministic boundary the v1.0
shipped with: skeleton equal → V-1; skeleton different → V-2.

Phase 4 sub-batch D adds an **optional morphology refiner** — when a
`MorphologyLexemeFn` adapter is supplied (typically backed by CAMeL
Tools), `classify_vocalization_class` upgrades V-1 candidates whose
lexemes (root/lemma) actually differ to V-2. The fallback rule still
holds: morphology never *down*-classifies a V-2 to V-1, only refines
V-1 → V-2 when morphology says "different lexemes".

When no adapter is supplied (or CAMeL is unavailable), the
deterministic skeleton-only behaviour is preserved exactly — older
callers see no change.
"""

from __future__ import annotations

from collections.abc import Callable

from waraq.arabic import normalize_for_compare, strip_arabic_diacritics
from waraq.hadith.enums import Vokalisierungsklasse

# Adapter: returns the canonical lexeme for a vocalized Arabic word.
# CAMeL Tools' first-analysis `lex` field is the production fit.
# Empty string means "no analysis available" — caller treats as
# inconclusive (does NOT escalate).
MorphologyLexemeFn = Callable[[str], str]


def _default_lexemes_differ(text_a: str, text_b: str) -> bool | None:
    """Return None — no morphology available. Callers respect the
    deterministic skeleton-only verdict."""
    _ = (text_a, text_b)
    return None


def _lexemes_differ(text_a: str, text_b: str, lexeme_fn: MorphologyLexemeFn | None) -> bool | None:
    """Compare lexeme bag-of-words between two texts.

    Returns:
        True  — at least one positionally-aligned word pair has
                differing non-empty lexemes (clear V-2 signal).
        False — every word pair has matching lexemes (V-1 confirmed).
        None  — the adapter is unavailable, returned an empty lexeme
                for any word, or the texts have different word counts
                (positional alignment fails — fall back to the
                deterministic verdict).
    """
    if lexeme_fn is None:
        return None
    a_words = text_a.split()
    b_words = text_b.split()
    if len(a_words) != len(b_words) or not a_words:
        return None
    seen_disagreement = False
    for wa, wb in zip(a_words, b_words, strict=True):
        try:
            la = lexeme_fn(wa)
            lb = lexeme_fn(wb)
        except Exception:
            return None
        if not la or not lb:
            # Inconclusive — adapter could not analyze one side.
            return None
        if la != lb:
            seen_disagreement = True
    return seen_disagreement


def classify_vocalization_class(
    text_a: str,
    text_b: str,
    *,
    lexeme_fn: MorphologyLexemeFn | None = None,
) -> Vokalisierungsklasse:
    """Return the §4.16.7 V-0/V-1/V-2 class for the deviation between
    two vocalized strings.

    Order-independent: classify(a, b) == classify(b, a). Empty inputs
    are treated as no-deviation (V-0) only when BOTH are empty;
    asymmetric emptiness escalates to V-2 (a missing matn is a
    structural difference, not a vocalization variant).

    Args:
        lexeme_fn: Optional morphology adapter. When supplied, V-1
            candidates whose lexemes positionally differ are escalated
            to V-2 per §4.16.7 fallback rule.
    """
    if not text_a and not text_b:
        return Vokalisierungsklasse.V_0
    if not text_a or not text_b:
        return Vokalisierungsklasse.V_2

    norm_a = normalize_for_compare(text_a)
    norm_b = normalize_for_compare(text_b)
    if norm_a == norm_b:
        # Tatweel + NFC differences only — the canonical V-0 case.
        return Vokalisierungsklasse.V_0

    skel_a = strip_arabic_diacritics(norm_a)
    skel_b = strip_arabic_diacritics(norm_b)
    if skel_a == skel_b:
        # Skeletons match — diacritic-only variation. V-1 by the
        # canonical examples (vocalization density, Shadda without
        # word-identity change, Hamzat al-Waṣl/Qaṭʿ).
        # Phase 4 sub-batch D: morphology refiner can escalate V-1 →
        # V-2 when lexemes actually differ (e.g., voiced/passive
        # ambiguity), per §4.16.7 fallback "no silent down-class".
        differ = _lexemes_differ(text_a, text_b, lexeme_fn)
        if differ is True:
            return Vokalisierungsklasse.V_2
        return Vokalisierungsklasse.V_1

    # Skeletal letters diverge — meaning, iʿrāb, or lexeme change.
    # §4.16.7 fallback rule: "with ambiguity, the higher class is
    # applied; no silent down-classification."
    return Vokalisierungsklasse.V_2


def aggregate_vocalization_class(
    classes: list[Vokalisierungsklasse],
) -> Vokalisierungsklasse:
    """Per §4.16.7 aggregation rule: with multiple deviations in one
    passage, the highest occurring class applies (V-0 < V-1 < V-2).
    Empty list → V-0 (no deviation observed).
    """
    if not classes:
        return Vokalisierungsklasse.V_0
    rank = {
        Vokalisierungsklasse.V_0: 0,
        Vokalisierungsklasse.V_1: 1,
        Vokalisierungsklasse.V_2: 2,
    }
    return max(classes, key=lambda c: rank[c])


def camel_lexeme_default() -> MorphologyLexemeFn:
    """Return a CAMeL-Tools-backed `MorphologyLexemeFn` — the
    production adapter for V-1/V-2 refinement.

    Lazily imports `waraq.morphology.service.analyze_word`. Returns
    the first analysis's `lex` field, or `""` when the analyzer has
    no candidates / the engine is unavailable. The classifier treats
    empty lexemes as inconclusive and falls back to the deterministic
    skeleton verdict, so deployments without the morphology DB see
    no change in behaviour."""
    from waraq.morphology.exceptions import MorphologyDataMissing, MorphologyNotInstalled
    from waraq.morphology.service import analyze_word

    def _fn(word: str) -> str:
        try:
            analyses = analyze_word(word)
        except (MorphologyNotInstalled, MorphologyDataMissing):
            return ""
        except Exception:
            return ""
        if not analyses:
            return ""
        return analyses[0].lex

    return _fn


__all__ = [
    "MorphologyLexemeFn",
    "aggregate_vocalization_class",
    "camel_lexeme_default",
    "classify_vocalization_class",
]
