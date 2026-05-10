"""§4.16.1 — Extended source set (E-1..E-5).

Per Dokument 1 §4.16.1:
  Extended set (automatically activated when the mandatory set yields
  no robust hit; can also be triggered manually by the user at any time):
    - E-1: islamweb.net – documented, factually suspended.
    - E-2: جَامِعُ السُّنَّةِ النَّبَوِيَّة – Alifta-/Harf variant; suspended.
    - E-3: المكتبة الوقفية – suspended; only kept as manual reference.
    - E-4: جَامِعُ الكُتُبِ التِّسْعَة – suspended.
    - E-5: مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة – not suspended;
            kept in special role (see §4.16.2).

Per §4.16.2 E-5 special role:
  No API full-text search path. Technical connection via the official
  API and the official bulk downloads. Official Live API is the
  primary runtime path; official bulk downloads are secondary
  auxiliary. No offline index as normal path. No frontend scraping
  as normal model.

This module provides the **structural representation** of E-1..E-5:
- `EXTENDED_SOURCE_SPECS` enumerates all five with their canonical
  state (suspended / active-special-role).
- `Quellenrolle` mapping makes Extended hits land in the §4.16.6
  Single-source rows with the correct `quellen_rolle` snapshot
  (`erweitert_aktiv` / `erweitert_sonderrolle` / `erweitert_suspendiert`).

E-1..E-4 are **factually suspended** per canon — they do NOT have
runtime client implementations in v1.0. Calling their fetch path
returns an empty hit list. E-5 has a stub fetcher in this module
that can be wired to the real official-API integration when that
work is taken up; v1.0 returns empty hits with a documented stub.

The two-tier orchestrator (`waraq.hadith.orchestrator`) reads from
this module to know which extended sources to invoke when escalation
fires.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum

from waraq.hadith.consensus import HadithCandidateHit
from waraq.hadith.enums import Quellenrolle


class ExtendedSourceState(StrEnum):
    """Per §4.16.1 + §4.16.2 — runtime state of an extended source."""

    SUSPENDED = "suspended"
    ACTIVE_SPECIAL_ROLE = "active_special_role"


@dataclass(frozen=True, slots=True)
class ExtendedSourceSpec:
    """Static metadata for one Extended source (E-1..E-5)."""

    source_id: str  # "e_1_islamweb", "e_5_mawsuat_ahadith", ...
    canonical_label: str
    arabic_label: str
    state: ExtendedSourceState
    quellen_rolle: Quellenrolle
    notes: str


EXTENDED_SOURCE_SPECS: list[ExtendedSourceSpec] = [
    ExtendedSourceSpec(
        source_id="e_1_islamweb",
        canonical_label="islamweb.net",
        arabic_label="إسلام ويب",
        state=ExtendedSourceState.SUSPENDED,
        quellen_rolle=Quellenrolle.ERWEITERT_SUSPENDIERT,
        notes="§4.16.1 E-1 — documented, factually suspended. No v1.0 client.",
    ),
    ExtendedSourceSpec(
        source_id="e_2_jami_sunnah",
        canonical_label="Jami al-Sunnah al-Nabawiyyah",
        arabic_label="جامع السنة النبوية",
        state=ExtendedSourceState.SUSPENDED,
        quellen_rolle=Quellenrolle.ERWEITERT_SUSPENDIERT,
        notes="§4.16.1 E-2 — Alifta-/Harf variant, suspended.",
    ),
    ExtendedSourceSpec(
        source_id="e_3_maktabat_waqfia",
        canonical_label="al-Maktaba al-Waqfia",
        arabic_label="المكتبة الوقفية",
        state=ExtendedSourceState.SUSPENDED,
        quellen_rolle=Quellenrolle.ERWEITERT_SUSPENDIERT,
        notes="§4.16.1 E-3 — kept only as possible manual reference; suspended.",
    ),
    ExtendedSourceSpec(
        source_id="e_4_jami_kutub_tisa",
        canonical_label="Jami al-Kutub al-Tisʿa",
        arabic_label="جامع الكتب التسعة",
        state=ExtendedSourceState.SUSPENDED,
        quellen_rolle=Quellenrolle.ERWEITERT_SUSPENDIERT,
        notes="§4.16.1 E-4 — suspended.",
    ),
    ExtendedSourceSpec(
        source_id="e_5_mawsuat_ahadith",
        canonical_label="Mawsuat al-Ahadith al-Nabawiyyah",
        arabic_label="موسوعة الأحاديث النبوية",
        state=ExtendedSourceState.ACTIVE_SPECIAL_ROLE,
        quellen_rolle=Quellenrolle.ERWEITERT_SONDERROLLE,
        notes="§4.16.2 E-5 — German/multilingual reference source. Active in special role: official API as primary runtime path; bulk downloads as secondary auxiliary; no offline-index normal path; no frontend scraping as normal model. v1.0 ships a stub — concrete Official-API integration is post-v1.0 work.",
    ),
]


_BY_ID: dict[str, ExtendedSourceSpec] = {s.source_id: s for s in EXTENDED_SOURCE_SPECS}


def get_extended_source(source_id: str) -> ExtendedSourceSpec:
    if source_id not in _BY_ID:
        raise KeyError(f"unknown extended source {source_id!r}; canonical IDs: {sorted(_BY_ID)}")
    return _BY_ID[source_id]


def is_active(source_id: str) -> bool:
    """True only for sources whose canonical state is not SUSPENDED."""
    return get_extended_source(source_id).state != ExtendedSourceState.SUSPENDED


# Type alias for an Extended source fetcher: takes a query string,
# returns a list of HadithCandidateHit. Used by the orchestrator when
# escalation triggers. Suspended sources receive a no-op fetcher; E-5
# receives the v1.0 stub below until the real Official-API client
# lands.
ExtendedFetcher = Callable[[str], Awaitable[list[HadithCandidateHit]]]


async def _suspended_no_hits(_query: str) -> list[HadithCandidateHit]:
    """No-op fetcher for E-1..E-4 (suspended per canon §4.16.1)."""
    return []


async def _e5_stub_no_hits(_query: str) -> list[HadithCandidateHit]:
    """v1.0 stub for E-5. Returns empty until the §4.16.2 Official Live
    API integration is built. Documented as canonical no-op so the
    two-tier orchestrator can call this without crashing — escalation
    simply produces no extended hits today."""
    return []


def default_extended_fetchers() -> dict[str, ExtendedFetcher]:
    """Return the v1.0 default mapping `source_id → fetcher`. All
    suspended sources get the no-hits no-op; E-5 gets the stub."""
    return {
        "e_1_islamweb": _suspended_no_hits,
        "e_2_jami_sunnah": _suspended_no_hits,
        "e_3_maktabat_waqfia": _suspended_no_hits,
        "e_4_jami_kutub_tisa": _suspended_no_hits,
        "e_5_mawsuat_ahadith": _e5_stub_no_hits,
    }


__all__ = [
    "EXTENDED_SOURCE_SPECS",
    "ExtendedFetcher",
    "ExtendedSourceSpec",
    "ExtendedSourceState",
    "default_extended_fetchers",
    "get_extended_source",
    "is_active",
]
