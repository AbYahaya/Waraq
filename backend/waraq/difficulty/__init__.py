"""§2.1 Phase 3 — Difficulty report (per-page + project-aggregate).

Scope (per Dokument 1 §2.1):

  "Phase 3 – OCR review: difficulty report, guided review, DPI
  comparison view."

Canon names the feature without pinning internals — concrete weights
are calibration territory (§3.5 "Concrete rates ... remain open").
v1.0 ships a structurally sensible weighted-sum aggregation with
documented per-dimension contributions; the real weights live in
`DEFAULT_DIFFICULTY_WEIGHTS` and are tuneable per-call.

Inputs (each a count of unresolved / open / problematic items
scoped to the relevant unit):

  - kritisch / hoch / mittel audit Befunde
  - kritisch / non-kritisch Konsistenz Befunde
  - Hadith H-2 (blocking) / H-1 (warning) status rows
  - OCR-error instances grouped by canonical severity class
  - manual_local + manual_editorial locked segment counts

Output: a `DifficultyReport` carrying the breakdown + a composite
score. Per-page rollup queries pages-scoped data only; project-
aggregate sums across pages plus project-scope-only data
(KonsistenzBefund, HadithPassageStatus do project-scope and segment-
scope; the report covers both correctly).
"""

from waraq.difficulty.service import (
    DEFAULT_DIFFICULTY_WEIGHTS,
    DifficultyBreakdown,
    DifficultyReport,
    DifficultyWeights,
    compute_page_difficulty,
    compute_project_difficulty,
)

__all__ = [
    "DEFAULT_DIFFICULTY_WEIGHTS",
    "DifficultyBreakdown",
    "DifficultyReport",
    "DifficultyWeights",
    "compute_page_difficulty",
    "compute_project_difficulty",
]
