"""§4.4 — OCR confidence taxonomy.

Three canonical classes per Dokument 1 §4.4:

  - **Accepted**  : confidence ≥ 0.85 — proceed without intervention
  - **Deficient** : 0.60 ≤ confidence < 0.85 — flag for review
  - **Critical**  : confidence < 0.60 — block / require manual confirmation

This module ships the **taxonomy + classifier + persistence shape**
only. The actual confidence *signal* in v1.0 single-engine OCR
(Gemini-only) is **None** — Gemini does not return a per-page
confidence in any usable form, and the canonical confidence signal
is meant to come from §3.4 Stage-3 multi-engine consensus (Phase 4
sub-batches C+D). Until then `confidence_score` on OCR-POs is None
and `confidence_class` is None; the structural shape is in place so
sub-batch D can populate without a schema change.

Threshold rationale: the 0.85 / 0.60 split is canon. Boundary
behavior: `score == 0.85` lands in ACCEPTED, `score == 0.60` lands
in DEFICIENT. (Strict `<` on the upper bound of each lower class.)
"""

from __future__ import annotations

from enum import StrEnum

# Per §4.4 — canonical thresholds, unveränderlich.
ACCEPTED_MIN: float = 0.85
DEFICIENT_MIN: float = 0.60


class OcrConfidenceClass(StrEnum):
    """The three canonical confidence classes per §4.4.

    Wire identifiers (lowercase, snake-case) are stable — they appear
    on OCR-PO payloads and any UI / export artefact that surfaces the
    class. Renaming a value is a canon-amendment-shaped change.
    """

    ACCEPTED = "accepted"
    DEFICIENT = "deficient"
    CRITICAL = "critical"


def classify_confidence(score: float) -> OcrConfidenceClass:
    """Map a confidence score in [0.0, 1.0] to a canonical class.

    Inputs outside [0, 1] are clamped before classification — a
    misbehaving consensus signal must not produce an undefined class.
    """
    if score < 0.0:
        score = 0.0
    elif score > 1.0:
        score = 1.0
    if score >= ACCEPTED_MIN:
        return OcrConfidenceClass.ACCEPTED
    if score >= DEFICIENT_MIN:
        return OcrConfidenceClass.DEFICIENT
    return OcrConfidenceClass.CRITICAL


__all__ = [
    "ACCEPTED_MIN",
    "DEFICIENT_MIN",
    "OcrConfidenceClass",
    "classify_confidence",
]
