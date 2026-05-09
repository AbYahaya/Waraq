"""§4.15.1 — Qurʾān translation lookup with primary-API → local-fallback semantics.

Per canon (§4.15.1):
  "primary carrier is quranenc.com API. Fallback on API failure is the
  local copy of the translation."

Per §4.15.2:
  "The first external API call (quranenc.com) occurs only in the
  translation phase. During the OCR run only local matching takes
  place; no external call in the OCR phase."

So the public `lookup_translation_aya` here takes a `phase` flag:
  - `phase="ocr"`     → local-fallback only (NEVER hits the API)
  - `phase="translation"` → API primary, local fallback on failure

This honors §4.15.1 + §4.15.2 simultaneously: OCR pipeline can
locally match Qurʾān verses without ever opening a network socket;
the translator stage can pull live translations and gracefully
degrade to the cached weekly-sync copy when quranenc.com is down.

The fallback path returns `TranslationFallbackUsed` as a flag on the
result so callers can log per §4.15.4 ("Fallback to local Quran copy:
log entry in project log") + §4.18 Class B aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.quran.quranenc import (
    JsonFetcher,
    QuranEncError,
    fetch_sura,
)
from waraq.schemas import QuranTranslationVerse


class TranslationSource(StrEnum):
    """Where the lookup result came from."""

    API_PRIMARY = "api_primary"
    LOCAL_FALLBACK = "local_fallback"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class TranslationLookupResult:
    """One translation āya plus the source it came from.

    `text` is None iff `source == NOT_FOUND` — the lookup found no
    matching row in the local fallback either.
    """

    sura_index: int
    aya_index: int
    translation_key: str
    text: str | None
    footnotes: str | None
    source: TranslationSource


async def lookup_translation_aya(
    session: AsyncSession,
    *,
    sura_index: int,
    aya_index: int,
    translation_key: str,
    phase: Literal["ocr", "translation"] = "translation",
    fetcher: JsonFetcher | None = None,
    source_version: str | None = None,
) -> TranslationLookupResult:
    """Look up one āya translation honoring §4.15.1 primary-fallback
    + §4.15.2 phase rules.

    `phase="ocr"` skips the API entirely; `phase="translation"` tries
    the API first and falls back to the local copy on failure. When
    both fail (API down + no local copy), `source == NOT_FOUND` and
    `text is None`.

    `source_version` optionally pins the local-fallback lookup to a
    specific synced version (useful when a deployment wants to lock to
    a specific Rwwad release and ignore newer syncs, e.g., during a
    CR-cycle review of an upstream change). When `None`, the lookup
    returns the first active row for that translation_key — which the
    `(translation_key, source_version)` unique constraint + the
    sync-supersession discipline keeps deterministic.
    """
    if phase == "translation":
        try:
            verses = await fetch_sura(
                translation_key=translation_key,
                sura_index=sura_index,
                fetcher=fetcher,
            )
            for v in verses:
                if v.aya_index == aya_index:
                    return TranslationLookupResult(
                        sura_index=sura_index,
                        aya_index=aya_index,
                        translation_key=translation_key,
                        text=v.translation,
                        footnotes=v.footnotes,
                        source=TranslationSource.API_PRIMARY,
                    )
            # API responded but didn't carry the requested āya —
            # treat as fetch failure and fall through to local.
        except QuranEncError:
            pass

    # Local fallback path (or `phase="ocr"`).
    row = await _lookup_local(
        session=session,
        sura_index=sura_index,
        aya_index=aya_index,
        translation_key=translation_key,
        source_version=source_version,
    )
    if row is not None:
        return TranslationLookupResult(
            sura_index=sura_index,
            aya_index=aya_index,
            translation_key=translation_key,
            text=row.translation_text,
            footnotes=row.footnotes,
            source=TranslationSource.LOCAL_FALLBACK,
        )

    return TranslationLookupResult(
        sura_index=sura_index,
        aya_index=aya_index,
        translation_key=translation_key,
        text=None,
        footnotes=None,
        source=TranslationSource.NOT_FOUND,
    )


async def _lookup_local(
    *,
    session: AsyncSession,
    sura_index: int,
    aya_index: int,
    translation_key: str,
    source_version: str | None = None,
) -> QuranTranslationVerse | None:
    stmt = (
        select(QuranTranslationVerse)
        .where(QuranTranslationVerse.translation_key == translation_key)
        .where(QuranTranslationVerse.sura_index == sura_index)
        .where(QuranTranslationVerse.aya_index == aya_index)
        .where(QuranTranslationVerse.active.is_(True))
    )
    if source_version is not None:
        stmt = stmt.where(QuranTranslationVerse.source_version == source_version)
    result = await session.execute(stmt)
    return result.scalars().first()


__all__ = [
    "TranslationLookupResult",
    "TranslationSource",
    "lookup_translation_aya",
]
