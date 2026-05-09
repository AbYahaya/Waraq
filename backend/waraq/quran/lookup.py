"""§4.15.1/§4.15.2 — AR-Referenzbestand lookup helpers.

Local-only by design: per §4.15.2 "During the OCR run only local
matching takes place; no external call in the OCR phase." These two
functions are the primary OCR Stage-3 hook (Phase 2F wires them into
the Qurʾān-recognition path).

`find_by_skeleton` returns ALL matches across active source versions.
Callers that need a single canonical hit pick the first match (the
unique key on (source_name, source_version, sura, aya) ensures stable
ordering when there's exactly one active source).

`lookup_aya` is the direct (sura, aya) lookup used by §4.15.4
source-citation insertion.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.arabic import to_skeleton
from waraq.schemas import ArReferenzVerse


async def lookup_aya(
    session: AsyncSession,
    *,
    sura_index: int,
    aya_index: int,
    source_name: str | None = None,
) -> ArReferenzVerse | None:
    """Return the active āya at (sura, aya). When `source_name` is
    given, restrict to that source; otherwise the first active row
    across all sources is returned (deterministic via sura/aya unique
    key, but a deployment with multiple sources should prefer to pin
    one)."""
    stmt = (
        select(ArReferenzVerse)
        .where(ArReferenzVerse.sura_index == sura_index)
        .where(ArReferenzVerse.aya_index == aya_index)
        .where(ArReferenzVerse.active.is_(True))
    )
    if source_name is not None:
        stmt = stmt.where(ArReferenzVerse.source_name == source_name)
    result = await session.execute(stmt)
    return result.scalars().first()


async def find_by_skeleton(
    session: AsyncSession,
    *,
    candidate_text: str,
    source_name: str | None = None,
) -> list[ArReferenzVerse]:
    """Return active āyat whose `text_skeleton` matches the
    candidate's skeleton form (NFC + Tatweel-strip + diacritic-strip).

    Exact skeleton match only — fuzzy/partial matching is the
    consensus engine's job (Phase 2F). Sorted by (sura, aya).
    """
    skeleton = to_skeleton(candidate_text)
    if not skeleton:
        return []
    stmt = (
        select(ArReferenzVerse)
        .where(ArReferenzVerse.text_skeleton == skeleton)
        .where(ArReferenzVerse.active.is_(True))
        .order_by(ArReferenzVerse.sura_index, ArReferenzVerse.aya_index)
    )
    if source_name is not None:
        stmt = stmt.where(ArReferenzVerse.source_name == source_name)
    result = await session.execute(stmt)
    return list(result.scalars())


__all__ = ["find_by_skeleton", "lookup_aya"]
