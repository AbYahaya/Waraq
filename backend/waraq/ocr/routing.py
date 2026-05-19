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
three-track Stage-3 consensus (rule-based + AI + statistical) lands in
sub-batch D and refines the per-block confidence aggregation; the
routing table itself stays canonical (which engines are eligible per
class is independent from how their outputs combine).

kraken (project-flag gated)
---------------------------
Per §3.3 canon row "kraken + eScriptorium for manuscripts/calligraphy
(gate behind project-flag)", a third engine — kraken — is available
for projects whose source material is handwritten / calligraphic.
`engines_for(block_class, *, use_kraken=True)` adds `OcrEngine.KRAKEN`
to the eligible set for every non-QURAN class. QURAN is excluded
because Qurʾān script is canonically printed (and kraken's
manuscript-oriented models degrade rather than help on the Mushaf).

The "project-flag" is currently materialized as the `use_kraken`
function-call boundary parameter; no DB column is added in this
sub-batch (CLAUDE.md §2.3 — canon names the gate but not its schema,
so we do not invent one). When a future canon-amendment specifies
schema (e.g. `Project.ocr_use_kraken`), the column plumbs into this
kwarg without changing the routing-table semantics.
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
    KRAKEN = "kraken"


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


def engines_for(
    block_class: BlockClass, *, use_kraken: bool = False
) -> frozenset[OcrEngine]:
    """Return the engine set Stage-2 routes a block of `block_class` to.

    Falls back to MAIN_TEXT routing when the class is not in the table —
    a defensive choice so a future BlockClass added without a routing
    entry runs through the safest superset (both engines) rather than
    silently dropping to one.

    When `use_kraken` is True, `OcrEngine.KRAKEN` is added to the
    eligible set for every block class except QURAN. The flag stands
    in for the §3.3 "project-flag" canon line — callers pass it from
    project context (or, in v1.0, from the diagnostics-endpoint test
    surface). QURAN routing stays Gemini-only regardless: Qurʾān
    script is printed-only canonically, and kraken's manuscript
    orientation would degrade rather than help.
    """
    base = _ROUTING.get(block_class, _ROUTING[BlockClass.MAIN_TEXT])
    if use_kraken and block_class != BlockClass.QURAN:
        return base | {OcrEngine.KRAKEN}
    return base


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
