"""§4.15.1 — quranenc.com → local fallback weekly sync.

Per canon: "Weekly automatic sync for updates." This module provides
the sync service. The actual scheduling (cron, systemd timer, Celery
beat) is a deployment concern — the canonical mechanism is the
idempotent function below + the CLI driver in `scripts/sync_quranenc.py`.

Behavior:
- For each sura 1..114, fetch via the quranenc.com client.
- Ingest with a fresh `source_version` (default = today's ISO date).
- Prior-version rows of the same `translation_key` flip to
  `active=false` (H-5 inactivation, no deletion).
- Same-version re-run is idempotent (rows update in place).

Failure semantics (§4.15.1 + §4.18 Class B):
- Per-sura fetch failure aborts the sync; partial state is fine —
  the prior version stays active until the next successful run replaces
  it. This honors the §4.15.1 "fallback on API failure" rule: even a
  failed sync leaves the *previous* fallback intact.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.quran.quranenc import (
    TRANSLATION_KEY_TO_LANGUAGE,
    JsonFetcher,
    QuranEncVerse,
    fetch_sura,
)
from waraq.schemas import QuranTranslationVerse


@dataclass(frozen=True, slots=True)
class TranslationSyncResult:
    translation_key: str
    language: str
    source_version: str
    verses_inserted: int
    verses_updated: int
    suras_fetched: int
    superseded_count: int


def _today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


async def sync_translation(
    *,
    session: AsyncSession,
    translation_key: str,
    source_version: str | None = None,
    suras: Iterable[int] | None = None,
    fetcher: JsonFetcher | None = None,
) -> TranslationSyncResult:
    """Pull every sura for `translation_key` from quranenc.com and
    populate the local fallback under a fresh `source_version`.

    Args:
        translation_key: `german_rwwad` or `english_rwwad` per §4.15.1.
        source_version: Tag for this sync. Defaults to today's ISO
            date (UTC). Same-version repeat = idempotent in-place update.
        suras: Iterable of sura indices to fetch. Defaults to 1..114.
            Useful for tests + partial recovery from a failed prior sync.
        fetcher: Optional injected JSON fetcher (tests pass a stub).
    """
    if translation_key not in TRANSLATION_KEY_TO_LANGUAGE:
        raise ValueError(f"unknown translation_key {translation_key!r}")
    language = TRANSLATION_KEY_TO_LANGUAGE[translation_key]
    version = source_version or _today_iso()
    sura_range = list(suras) if suras is not None else list(range(1, 115))

    # Step 1: deactivate prior-version rows of the same translation_key.
    superseded_result = cast(
        CursorResult[Any],
        await session.execute(
            update(QuranTranslationVerse)
            .where(QuranTranslationVerse.translation_key == translation_key)
            .where(QuranTranslationVerse.source_version != version)
            .where(QuranTranslationVerse.active.is_(True))
            .values(active=False)
        ),
    )
    superseded_count = superseded_result.rowcount or 0

    # Step 2: load existing rows for this exact (translation_key, source_version)
    # so the same-version repeat is an in-place update (matches the
    # AR-Referenzbestand ingest semantics from Phase 2D).
    existing_q = await session.execute(
        select(QuranTranslationVerse).where(
            QuranTranslationVerse.translation_key == translation_key,
            QuranTranslationVerse.source_version == version,
        )
    )
    existing_by_key: dict[tuple[int, int], QuranTranslationVerse] = {
        (row.sura_index, row.aya_index): row for row in existing_q.scalars()
    }

    inserted = 0
    updated = 0
    suras_fetched = 0
    for sura_index in sura_range:
        verses = await fetch_sura(
            translation_key=translation_key,
            sura_index=sura_index,
            fetcher=fetcher,
        )
        suras_fetched += 1
        for v in verses:
            ins, upd = _upsert_verse(
                session=session,
                existing_by_key=existing_by_key,
                translation_key=translation_key,
                language=language,
                source_version=version,
                verse=v,
            )
            inserted += ins
            updated += upd

    await session.flush()
    return TranslationSyncResult(
        translation_key=translation_key,
        language=language,
        source_version=version,
        verses_inserted=inserted,
        verses_updated=updated,
        suras_fetched=suras_fetched,
        superseded_count=superseded_count,
    )


def _upsert_verse(
    *,
    session: AsyncSession,
    existing_by_key: dict[tuple[int, int], QuranTranslationVerse],
    translation_key: str,
    language: str,
    source_version: str,
    verse: QuranEncVerse,
) -> tuple[int, int]:
    """Insert or update one verse. Returns (inserted, updated) bumps."""
    key = (verse.sura_index, verse.aya_index)
    if (existing := existing_by_key.get(key)) is not None:
        # Same-version repeat — refresh in place. Track as "updated"
        # iff the text actually changed (callers care about real
        # content drift, not just touch).
        if existing.translation_text != verse.translation or existing.footnotes != verse.footnotes:
            existing.translation_text = verse.translation
            existing.footnotes = verse.footnotes
            existing.active = True
            return (0, 1)
        existing.active = True
        return (0, 0)
    session.add(
        QuranTranslationVerse(
            verse_uuid=_make_uuid(),
            translation_key=translation_key,
            language=language,
            source_version=source_version,
            sura_index=verse.sura_index,
            aya_index=verse.aya_index,
            translation_text=verse.translation,
            footnotes=verse.footnotes,
        )
    )
    return (1, 0)


def _make_uuid() -> _uuid.UUID:
    return new_uuid()


__all__ = ["TranslationSyncResult", "sync_translation"]
