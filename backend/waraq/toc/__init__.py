"""§2.1 Phase 4 TOC handling — auto-detection + AR/DE compare + fallback.

Per Dokument 1 §2.1:

  "Phase 4 – TOC confirmation: Arabic/German comparison view, adjust
  chapter headings. No TOC detected → page-by-page split. Manual TOC
  definition is not part of this version. Separate CR if desired later."

v1.0 scope (this module):

  - `detect_toc(session, project_uuid) -> TocResult` scans the project
    for heading-typed blocks (`block_type in {UE, HD}` per OCR-export
    block-type taxonomy — UE = Heading 1, HD = Heading 2). Returns
    one `TocEntry` per heading segment carrying the AR source +
    DE translation pair so the UI can render them side-by-side.

  - When NO heading blocks are detected, the result.fallback_kind is
    "page_by_page" and entries are synthesized one-per-active-page
    (canonical fallback per §2.1 "No TOC detected → page-by-page
    split").

  - `edit_toc_entry_heading(...)` updates the underlying segment's
    text via `create_revision` (`change_source=manual`) so the edit
    is provenance-tracked. AR + DE updates are separate Revision
    writes targeting the same segment row (combined-text format
    `source\\n---\\ntarget`); the helper preserves the unedited side.

Manual TOC definition (per-user override of the detected structure)
is **explicitly out of v1.0** per §2.1 — would need a CR.
"""

from waraq.toc.service import (
    HEADING_BLOCK_TYPES,
    TocEntry,
    TocFallbackKind,
    TocResult,
    detect_toc,
    edit_toc_entry_heading,
)

__all__ = [
    "HEADING_BLOCK_TYPES",
    "TocEntry",
    "TocFallbackKind",
    "TocResult",
    "detect_toc",
    "edit_toc_entry_heading",
]
