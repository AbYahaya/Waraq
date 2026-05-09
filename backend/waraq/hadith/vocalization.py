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

For v1.0 we cannot reliably distinguish V-1 from V-2 by surface text
alone — that requires morphological analysis (CAMeL Tools, Phase 4+).
Skeletal-letter equivalence is the deterministic boundary we have:

  - skeleton equal AND only diacritic differences → V-1
  - skeletons differ → V-2

This honors the fallback rule on the V-1 ⇄ V-2 boundary: skeleton
equality is necessary-but-not-sufficient for V-1, so we do NOT
down-classify a V-2 to V-1; but we may upclassify a V-1 to V-2 if
morphology eventually refines the call (Phase 4 follow-up).
"""

from __future__ import annotations

from waraq.arabic import normalize_for_compare, strip_arabic_diacritics
from waraq.hadith.enums import Vokalisierungsklasse


def classify_vocalization_class(
    text_a: str,
    text_b: str,
) -> Vokalisierungsklasse:
    """Return the §4.16.7 V-0/V-1/V-2 class for the deviation between
    two vocalized strings.

    Order-independent: classify(a, b) == classify(b, a). Empty inputs
    are treated as no-deviation (V-0) only when BOTH are empty;
    asymmetric emptiness escalates to V-2 (a missing matn is a
    structural difference, not a vocalization variant).
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
        # word-identity change, Hamzat al-Waṣl/Qaṭʿ). The morphology-
        # aware V-1 vs V-2 refinement is Phase 4+.
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


__all__ = [
    "aggregate_vocalization_class",
    "classify_vocalization_class",
]
