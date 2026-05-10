"""§3.5 + §4.16.1 P-2 — Shamela / OpenITI corpus integration.

Phase 2E exposes:
- `OPENITI_TEXTS` — registry of the v1.0 canonical text set
  (Lisān al-ʿArab + Tāj al-ʿArūs canonical per §3.5; the 6
  Kutub-as-Sitta collections necessary for §4.16.3 consensus to
  exercise the Kutub preference; Muwaṭṭaʾ Mālik + al-Qāmūs al-Muḥīṭ
  as supplementary v1.0 implementation choices).
- `ingest_text` / `parse_section_lines` — section-line ingest service.
- `find_by_skeleton` / `search_by_keyword` — Mode A (OCR plausibility)
  and Mode B (lexical research) lookup.
- `shamela_hits_to_consensus_candidates` — adapts Shamela hits into
  `HadithCandidateHit` for the §4.16.3 consensus engine.
"""

from waraq.shamela.adapter import shamela_hits_to_consensus_candidates
from waraq.shamela.ingest import (
    SectionRow,
    ingest_text,
    parse_section_lines,
    register_text,
)
from waraq.shamela.lookup import (
    ShamelaHit,
    find_by_skeleton,
    search_by_keyword,
)
from waraq.shamela.registry import (
    OPENITI_TEXTS,
    OpenITITextSpec,
    get_text_spec,
)

__all__ = [
    "OPENITI_TEXTS",
    "OpenITITextSpec",
    "SectionRow",
    "ShamelaHit",
    "find_by_skeleton",
    "get_text_spec",
    "ingest_text",
    "parse_section_lines",
    "register_text",
    "search_by_keyword",
    "shamela_hits_to_consensus_candidates",
]
