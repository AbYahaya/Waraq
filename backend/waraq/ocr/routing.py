"""§3.4 Stage-2 — block-typed OCR engine routing.

Per the canonical Stage-2 mandate, OCR engine selection is BLOCK-level,
not page-level. Different block classes have different reading-line
characteristics:

  - QURAN: the second OCR engine is still excluded for v1.0
    (vocalization-heavy lines and the small Quranic marks confound
    non-specialized general-purpose OCR). Gemini-only for v1.0.
  - MAIN_TEXT, HEADING, FOOTNOTE, HADITH, MARGINALIA: both engines
    run in parallel; the §3.6-symmetric agreement signal feeds §4.4
    confidence aggregation in `consensus.run_engines`.

The routing table is a static dict keyed by `BlockClass`. The full
three-track Stage-3 consensus refines per-block confidence aggregation;
the routing table itself stays canonical (which engines are eligible per
class is independent from how their outputs combine).
"""

from __future__ import annotations

from enum import StrEnum

from waraq.schemas.enums import BlockClass


class OcrEngine(StrEnum):
    """Canonical OCR engine identifier — wire-stable string. Persisted
    on the OCR-PO `engines[*].engine` payload field; renaming is a
    canon-shaped change."""

    GEMINI = "gemini"
    OPENAI = "openai"


# Stage-2 block-class → engine routing. Each value is the set of
# engines eligible to run for blocks of that class. `frozenset`
# (immutable, hashable) so the table itself is safe to expose.
_ROUTING: dict[BlockClass, frozenset[OcrEngine]] = {
    BlockClass.MAIN_TEXT: frozenset({OcrEngine.GEMINI, OcrEngine.OPENAI}),
    BlockClass.HEADING: frozenset({OcrEngine.GEMINI, OcrEngine.OPENAI}),
    BlockClass.FOOTNOTE: frozenset({OcrEngine.GEMINI, OcrEngine.OPENAI}),
    BlockClass.HADITH: frozenset({OcrEngine.GEMINI, OcrEngine.OPENAI}),
    BlockClass.MARGINALIA: frozenset({OcrEngine.GEMINI, OcrEngine.OPENAI}),
    BlockClass.QURAN: frozenset({OcrEngine.GEMINI}),
}


# Per §3.3, Gemini is the canonical "main reading line". When both
# engines agree, the OCR-PO records both texts but the canonical
# `text` field comes from the primary. Stage-3 consensus (sub-batch
# D) replaces this single-engine pick with a true vote.
_PRIMARY_ENGINE: OcrEngine = OcrEngine.GEMINI


def engines_for(block_class: BlockClass) -> frozenset[OcrEngine]:
    """Return the engine set Stage-2 routes a block of `block_class` to.

    Falls back to MAIN_TEXT routing when the class is not in the table —
    a defensive choice so a future BlockClass added without a routing
    entry runs through the safest superset (both engines) rather than
    silently dropping to one.
    """
    return _ROUTING.get(block_class, _ROUTING[BlockClass.MAIN_TEXT])


def primary_engine() -> OcrEngine:
    """Return the canonical primary engine for §3.3 main-reading-line.
    Used by the consensus driver to pick the OCR-PO `text` field when
    multiple engines ran and agreed."""
    return _PRIMARY_ENGINE


__all__ = [
    "OcrEngine",
    "engines_for",
    "primary_engine",
]
