"""Phase 2 — Hadith verification result objects and helpers.

Per Dokument 1 §4.16, Hadith verification spans:

- §4.16.1 two-tier source structure (P-1/P-2/P-3 + E-1..E-5)
- §4.16.3 multi-dimensional consensus + Kutub-as-Sitta weighting
- §4.16.6 four-level data model (Level 1 anchor / Level 2 Single-source /
  Level 3 Aggregate / Level 4 user-decision overlay via decision_event_uuid)
- §4.16.7 V-0/V-1/V-2 vocalization escalation
- §4.16.3 source-citation format (DE / EN)

This module provides the value-layer pieces that don't depend on external
APIs: the Quellenrolle/Vokalisierungsklasse enums, the V-0/V-1/V-2
classifier (pure text comparison), and the canonical DE/EN citation
formatter. The external clients (sunnah.com, dorar.net, Shamela) live in
sibling modules and are wired to these pieces by Phase 2C/E/F.
"""

from waraq.hadith.citation import (
    SourceCitation,
    format_source_citation_de,
    format_source_citation_en,
)
from waraq.hadith.dorar import (
    DorarHadith,
    search_via_api,
    search_via_scraping_fallback,
)
from waraq.hadith.enums import Quellenrolle, Vokalisierungsklasse
from waraq.hadith.sunnah import (
    DEFAULT_SUNNAH_BASE_URL,
    SunnahApiKeyMissing,
    SunnahHadith,
    fetch_hadith,
)
from waraq.hadith.vocalization import classify_vocalization_class

__all__ = [
    "DEFAULT_SUNNAH_BASE_URL",
    "DorarHadith",
    "Quellenrolle",
    "SourceCitation",
    "SunnahApiKeyMissing",
    "SunnahHadith",
    "Vokalisierungsklasse",
    "classify_vocalization_class",
    "fetch_hadith",
    "format_source_citation_de",
    "format_source_citation_en",
    "search_via_api",
    "search_via_scraping_fallback",
]
