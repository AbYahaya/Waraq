"""§3.5 Mode A + Mode B Shamela lookup.

Per §3.5:
  - **Mode A — OCR-internal**: system-triggered in OCR Stage 3 as
    plausibility check of recognized text fragments.
  - **Mode B — user-driven**: lexical research and footnote creation
    in the translation phase.

Implementation:
- `find_by_skeleton` is the Mode A primary — exact skeleton-substring
  match against active sections. Returns hits ordered by text_slug.
- `search_by_keyword` is the Mode B primary — substring match against
  the raw `text_arabic` (NOT skeleton). Useful for "find every place
  the lexicons cite this word verbatim", whether vocalized or not.

Both lookups can be scoped to specific `text_slug`s, `text_type`s,
or only Kutub-as-Sitta texts (the latter feeds §4.16.3 P-2 candidate
construction).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.arabic import to_skeleton
from waraq.schemas import ShamelaRegistry, ShamelaSection


@dataclass(frozen=True, slots=True)
class ShamelaHit:
    """One Shamela section returned by lookup."""

    section_uuid: object  # _uuid.UUID; loose-typed to avoid cycle.
    text_slug: str
    title: str
    author: str | None
    is_kutub_as_sitta: bool
    text_type: str
    section_index: int
    section_path: str
    text_arabic: str
    metadata: dict[str, object]


async def find_by_skeleton(
    session: AsyncSession,
    *,
    candidate_text: str,
    text_slugs: Iterable[str] | None = None,
    only_kutub_as_sitta: bool = False,
    limit: int = 50,
) -> list[ShamelaHit]:
    """§3.5 Mode A — find Shamela sections whose skeleton matches the
    candidate's skeleton form.

    The match is **substring** (not exact) so a candidate fragment
    can hit the surrounding section it appears in. Returns hits in
    `(text_slug, section_index)` order, capped at `limit`.

    `only_kutub_as_sitta=True` restricts to the 6 Kutub collections —
    used by §4.16.3 P-2 candidate construction.
    """
    skeleton = to_skeleton(candidate_text)
    if not skeleton:
        return []

    stmt = (
        select(ShamelaSection, ShamelaRegistry)
        .join(
            ShamelaRegistry,
            (ShamelaSection.text_slug == ShamelaRegistry.text_slug)
            & (ShamelaSection.source_version == ShamelaRegistry.source_version),
        )
        .where(ShamelaSection.active.is_(True))
        .where(ShamelaRegistry.active.is_(True))
        .where(ShamelaSection.text_skeleton.like(f"%{skeleton}%"))
        .order_by(ShamelaSection.text_slug, ShamelaSection.section_index)
        .limit(limit)
    )
    if text_slugs is not None:
        slugs = list(text_slugs)
        if not slugs:
            return []
        stmt = stmt.where(ShamelaSection.text_slug.in_(slugs))
    if only_kutub_as_sitta:
        stmt = stmt.where(ShamelaRegistry.is_kutub_as_sitta.is_(True))

    rows = (await session.execute(stmt)).all()
    return [_row_to_hit(section, registry) for section, registry in rows]


async def search_by_keyword(
    session: AsyncSession,
    *,
    keyword: str,
    text_slugs: Iterable[str] | None = None,
    text_types: Iterable[str] | None = None,
    limit: int = 50,
) -> list[ShamelaHit]:
    """§3.5 Mode B — keyword search over the Arabic body.

    Matches the keyword as a substring against EITHER the raw
    `text_arabic` (vocalized form) OR the `text_skeleton` (after
    skeleton-stripping the keyword). This way a bare-letter query
    (e.g., "نوى") finds vocalized stored content (e.g., "نَوَى الشيءَ
    نِيَّةً"), while a vocalized query still hits a verbatim raw match.

    Use `text_types=["lexicon"]` to scope to the dictionaries when
    looking up word definitions.
    """
    from sqlalchemy import or_

    keyword = keyword.strip()
    if not keyword:
        return []
    skeleton_keyword = to_skeleton(keyword)

    raw_clause = ShamelaSection.text_arabic.like(f"%{keyword}%")
    where_clauses = [raw_clause]
    if skeleton_keyword:
        where_clauses.append(ShamelaSection.text_skeleton.like(f"%{skeleton_keyword}%"))
    keyword_clause = or_(*where_clauses) if len(where_clauses) > 1 else raw_clause

    stmt = (
        select(ShamelaSection, ShamelaRegistry)
        .join(
            ShamelaRegistry,
            (ShamelaSection.text_slug == ShamelaRegistry.text_slug)
            & (ShamelaSection.source_version == ShamelaRegistry.source_version),
        )
        .where(ShamelaSection.active.is_(True))
        .where(ShamelaRegistry.active.is_(True))
        .where(keyword_clause)
        .order_by(ShamelaSection.text_slug, ShamelaSection.section_index)
        .limit(limit)
    )
    if text_slugs is not None:
        slugs = list(text_slugs)
        if not slugs:
            return []
        stmt = stmt.where(ShamelaSection.text_slug.in_(slugs))
    if text_types is not None:
        types = list(text_types)
        if not types:
            return []
        stmt = stmt.where(ShamelaRegistry.text_type.in_(types))

    rows = (await session.execute(stmt)).all()
    return [_row_to_hit(section, registry) for section, registry in rows]


def _row_to_hit(section: ShamelaSection, registry: ShamelaRegistry) -> ShamelaHit:
    return ShamelaHit(
        section_uuid=section.section_uuid,
        text_slug=section.text_slug,
        title=registry.title,
        author=registry.author,
        is_kutub_as_sitta=registry.is_kutub_as_sitta,
        text_type=registry.text_type,
        section_index=section.section_index,
        section_path=section.section_path,
        text_arabic=section.text_arabic,
        metadata=dict(section.metadata_json or {}),
    )


__all__ = ["ShamelaHit", "find_by_skeleton", "search_by_keyword"]
