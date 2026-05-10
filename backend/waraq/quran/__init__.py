"""§4.15 — AR-Referenzbestand and Qurʾān handling.

Phase 2D — AR-Referenzbestand:
- Schema (`schemas.quran.ArReferenzVerse`).
- Tanzil-Hafs ingest (`tanzil_ingest`).
- Local skeleton + (sura, aya) lookup (`lookup`).

Phase 2B — translation carrier (quranenc.com + local fallback):
- API client (`quranenc`).
- Weekly sync (`translation_sync`).
- Phase-aware lookup (`translation_lookup`) with API-primary + local-
  fallback semantics per §4.15.1 / §4.15.2.

Phase 2F will add: §4.15.2 Qurʾān recognition pipeline + §4.15.3
project-passage protection + §4.15.4 source-citation insertion logic.
"""

from waraq.quran.citation import (
    CitationVerdict,
    CitationVerificationResult,
    format_canonical_citation,
    parse_author_citation,
    verify_author_citation,
)
from waraq.quran.lookup import find_by_skeleton, lookup_aya
from waraq.quran.project_passages import (
    PassageNotInExpectedState,
    ProjectPassageError,
    RecordedPassage,
    confirm_below_threshold,
    correct_sura_aya,
    record_recognized_passage,
    refresh_passage_from_collection,
    reject_as_quran,
)
from waraq.quran.quranenc import (
    DEFAULT_BASE_URL,
    ENGLISH_RWWAD_KEY,
    GERMAN_RWWAD_KEY,
    QuranEncError,
    QuranEncVerse,
    fetch_sura,
)
from waraq.quran.recognition import (
    RecognitionResult,
    recognize_quran_passage,
)
from waraq.quran.tanzil_ingest import (
    DEFAULT_TANZIL_HAFS_SOURCE_NAME,
    TanzilParseError,
    ingest_tanzil_quran,
    parse_tanzil_pipe_text,
)
from waraq.quran.translation_lookup import (
    TranslationLookupResult,
    TranslationSource,
    lookup_translation_aya,
)
from waraq.quran.translation_sync import TranslationSyncResult, sync_translation

__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_TANZIL_HAFS_SOURCE_NAME",
    "ENGLISH_RWWAD_KEY",
    "GERMAN_RWWAD_KEY",
    "CitationVerdict",
    "CitationVerificationResult",
    "PassageNotInExpectedState",
    "ProjectPassageError",
    "QuranEncError",
    "QuranEncVerse",
    "RecognitionResult",
    "RecordedPassage",
    "TanzilParseError",
    "TranslationLookupResult",
    "TranslationSource",
    "TranslationSyncResult",
    "confirm_below_threshold",
    "correct_sura_aya",
    "fetch_sura",
    "find_by_skeleton",
    "format_canonical_citation",
    "ingest_tanzil_quran",
    "lookup_aya",
    "lookup_translation_aya",
    "parse_author_citation",
    "parse_tanzil_pipe_text",
    "recognize_quran_passage",
    "record_recognized_passage",
    "refresh_passage_from_collection",
    "reject_as_quran",
    "sync_translation",
    "verify_author_citation",
]
