"""Tanzil-Hafs ingest into the AR-Referenzbestand.

Per WORKLOG decision 2026-05-09: Tanzil-Hafs (Uthmani vocalized text)
is the v1.0 implementation source for §4.15.1 — not a canon amendment;
the canonical wording remains "concrete source designation still open".

Tanzil distributes the text under CC BY 3.0. The pipe-delimited format:

    1|1|بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ
    1|2|ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ
    ...

Lines starting with '#' are comments; blank lines are skipped. The
parser is strict on the 3-field layout (sura | aya | text) so a
malformed upstream file raises rather than silently skipping content.

Re-ingest semantics: a fresh ingest of the **same** `(source_name,
source_version)` triple is idempotent — pre-existing rows for that
triple are upserted (text replaced if changed). A re-ingest of a
**new** `source_version` flips all rows of the prior version to
`active=false` and inserts the new version as active. This honors §4.9
E-10 immutability without forcing every project to update — §4.15.3
project-passage protection is applied separately at recognition time.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.arabic import to_skeleton
from waraq.identity import new_uuid
from waraq.schemas import ArReferenzVerse

DEFAULT_TANZIL_HAFS_SOURCE_NAME = "tanzil-hafs-uthmani"


class TanzilParseError(ValueError):
    """Malformed Tanzil pipe-delimited input."""


@dataclass(frozen=True, slots=True)
class TanzilVerse:
    """One parsed line from the Tanzil pipe-delimited text."""

    sura_index: int
    aya_index: int
    text_vocalized: str


@dataclass(frozen=True, slots=True)
class TanzilIngestResult:
    inserted_count: int
    superseded_count: int
    source_name: str
    source_version: str


def parse_tanzil_pipe_text(content: str) -> Iterator[TanzilVerse]:
    """Parse the Tanzil `sura|aya|text` pipe-delimited format.

    - Lines starting with '#' are comments; skipped.
    - Blank lines are skipped.
    - Other lines must split into exactly 3 fields.
    - sura_index must parse as int in 1..114; aya_index must parse as
      int >= 1.

    Raises TanzilParseError on the first malformed line.
    """
    for lineno, raw in enumerate(content.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) != 3:
            raise TanzilParseError(
                f"line {lineno}: expected 3 fields separated by '|', got {len(parts)}"
            )
        sura_str, aya_str, text = parts
        try:
            sura_index = int(sura_str)
            aya_index = int(aya_str)
        except ValueError as exc:
            raise TanzilParseError(
                f"line {lineno}: sura/aya must be integers ({sura_str!r}, {aya_str!r})"
            ) from exc
        if not 1 <= sura_index <= 114:
            raise TanzilParseError(
                f"line {lineno}: sura_index {sura_index} out of canonical range 1..114"
            )
        if aya_index < 1:
            raise TanzilParseError(f"line {lineno}: aya_index {aya_index} must be >= 1")
        if not text:
            raise TanzilParseError(
                f"line {lineno}: empty text field for ({sura_index}, {aya_index})"
            )
        yield TanzilVerse(
            sura_index=sura_index,
            aya_index=aya_index,
            text_vocalized=text,
        )


async def ingest_tanzil_quran(
    *,
    session: AsyncSession,
    verses: Iterable[TanzilVerse],
    source_version: str,
    source_name: str = DEFAULT_TANZIL_HAFS_SOURCE_NAME,
) -> TanzilIngestResult:
    """Ingest a Tanzil verse stream into AR-Referenzbestand.

    Behavior:
      - For (source_name, source_version) already present: rows are
        updated in place when text differs; missing rows are inserted.
      - For prior source_versions of the same source_name: those rows
        are flipped to active=false (H-5 inactivation, no deletion).
      - text_skeleton is derived from text_vocalized via
        `waraq.arabic.to_skeleton` at ingest time.

    Returns an `TanzilIngestResult` with counts.
    """
    # Step 1: deactivate prior-version rows of the same source_name.
    # `session.execute(update(...))` returns a CursorResult under the
    # hood, but its async-typed return is the broader `Result[Any]`.
    # Cast to access `rowcount` cleanly.
    superseded_result = cast(
        CursorResult[Any],
        await session.execute(
            update(ArReferenzVerse)
            .where(ArReferenzVerse.source_name == source_name)
            .where(ArReferenzVerse.source_version != source_version)
            .where(ArReferenzVerse.active.is_(True))
            .values(active=False)
        ),
    )
    superseded_count = superseded_result.rowcount or 0

    # Step 2: load existing rows for this exact (source_name, source_version)
    # so we can do a small in-process upsert without a Postgres UPSERT
    # round-trip per row (the table is bounded — 6236 āyāt for Tanzil-Hafs).
    existing_q = await session.execute(
        select(ArReferenzVerse).where(
            ArReferenzVerse.source_name == source_name,
            ArReferenzVerse.source_version == source_version,
        )
    )
    existing_by_key: dict[tuple[int, int], ArReferenzVerse] = {
        (row.sura_index, row.aya_index): row for row in existing_q.scalars()
    }

    inserted_count = 0
    seen_keys: set[tuple[int, int]] = set()
    for v in verses:
        key = (v.sura_index, v.aya_index)
        if key in seen_keys:
            raise TanzilParseError(f"duplicate (sura={v.sura_index}, aya={v.aya_index}) in input")
        seen_keys.add(key)
        skeleton = to_skeleton(v.text_vocalized)
        if (existing := existing_by_key.get(key)) is not None:
            # Update-in-place: same identity, possibly refreshed text.
            existing.text_vocalized = v.text_vocalized
            existing.text_skeleton = skeleton
            existing.active = True
        else:
            session.add(
                ArReferenzVerse(
                    verse_uuid=_make_uuid(),
                    source_name=source_name,
                    source_version=source_version,
                    sura_index=v.sura_index,
                    aya_index=v.aya_index,
                    text_vocalized=v.text_vocalized,
                    text_skeleton=skeleton,
                )
            )
            inserted_count += 1

    await session.flush()
    return TanzilIngestResult(
        inserted_count=inserted_count,
        superseded_count=superseded_count,
        source_name=source_name,
        source_version=source_version,
    )


def _make_uuid() -> _uuid.UUID:
    return new_uuid()


__all__ = [
    "DEFAULT_TANZIL_HAFS_SOURCE_NAME",
    "TanzilIngestResult",
    "TanzilParseError",
    "TanzilVerse",
    "ingest_tanzil_quran",
    "parse_tanzil_pipe_text",
]
