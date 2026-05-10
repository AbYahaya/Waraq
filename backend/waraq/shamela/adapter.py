"""Phase 2E — Shamela → §4.16.3 consensus engine adapter.

Per §4.16.1 P-2: Shamela is a **mandatory** Hadith verification
source. When the consensus engine in `waraq.hadith.consensus` runs,
Shamela hits become `HadithCandidateHit` candidates alongside
sunnah.com (P-1) and dorar.net (P-3) hits.

This adapter converts `ShamelaHit` rows from the Kutub-as-Sitta
collections into consensus candidates. Hits from non-Kutub texts
(lexicons, supplementary works) are NOT wired in here — those are
informational lookups, not Hadith verification carriers.

`quellen_rolle` is set to `pflicht` per §4.16.1 (Shamela is in the
mandatory tier). Source name is the canonical `"shamela"` so
`LINEAR_SOURCE_RANK` (quranenc=1 > sunnah=2 > shamela=3 > dorar=4)
applies cleanly. `collection_label` is set to the registry `title`
so the consensus engine's Kutub-as-Sitta detection
(`KUTUB_AS_SITTA_LABELS`) matches.
"""

from __future__ import annotations

from waraq.hadith.consensus import HadithCandidateHit
from waraq.hadith.enums import Quellenrolle
from waraq.shamela.lookup import ShamelaHit


def shamela_hits_to_consensus_candidates(
    hits: list[ShamelaHit],
) -> list[HadithCandidateHit]:
    """Adapt Kutub-as-Sitta Shamela hits to `HadithCandidateHit` rows.

    Non-Kutub hits are filtered out — those don't belong in the
    Hadith consensus pipeline (they're for Mode-B lexical lookup
    only). Hadith-collection hits outside the Kutub-as-Sitta set
    (e.g., Muwaṭṭaʾ Mālik) ARE included as `quellen_rolle=pflicht`
    candidates, since they're still legitimate Hadith primary
    sources — they just don't get the Kutub-as-Sitta tiebreak
    preference (the consensus engine reads `is_kutub_as_sitta` from
    `collection_label`, so non-Kutub Hadith collections drop out of
    the tiebreak naturally).
    """
    candidates: list[HadithCandidateHit] = []
    for hit in hits:
        if hit.text_type != "hadith":
            continue
        candidates.append(
            HadithCandidateHit(
                source_name="shamela",
                quellen_rolle=Quellenrolle.PFLICHT,
                matn_arabic=hit.text_arabic,
                matn_vocalized=None,
                isnad_chain=[],
                collection_label=_collection_label_for_kutub(hit),
                hadith_number=_extract_hadith_number(hit),
                authenticity_grade=None,
                raw_payload={
                    "text_slug": hit.text_slug,
                    "section_index": hit.section_index,
                    "section_path": hit.section_path,
                    "section_uuid": str(hit.section_uuid),
                    **dict(hit.metadata),
                },
            )
        )
    return candidates


def _collection_label_for_kutub(hit: ShamelaHit) -> str:
    """Return the canonical English-transliteration collection label
    that the §4.16.3 `KUTUB_AS_SITTA_LABELS` set recognizes.

    Maps the Shamela `text_slug` to its canonical `Sahih al-Bukhari` /
    `Sahih Muslim` / etc. label. Non-Kutub hadith works keep their
    title as the label (transliterated when available).
    """
    slug_to_label = {
        "sahih_bukhari": "Sahih al-Bukhari",
        "sahih_muslim": "Sahih Muslim",
        "sunan_abi_dawud": "Sunan Abi Dawud",
        "jami_at_tirmidhi": "Jami at-Tirmidhi",
        "sunan_an_nasai": "Sunan an-Nasa'i",
        "sunan_ibn_majah": "Sunan Ibn Majah",
    }
    return slug_to_label.get(hit.text_slug, hit.title)


def _extract_hadith_number(hit: ShamelaHit) -> str | None:
    """Pull a hadith number from the section metadata when present.

    OpenITI ingest may carry a `hadith_number` key in the metadata
    JSONB; if absent, fall back to the `section_path` for
    informational citation. Returns the number as a string so callers
    that want either int or string-with-suffix get verbatim.
    """
    raw = hit.metadata.get("hadith_number")
    if isinstance(raw, (int, str)) and str(raw):
        return str(raw)
    if hit.section_path:
        return hit.section_path
    return None


__all__ = ["shamela_hits_to_consensus_candidates"]
