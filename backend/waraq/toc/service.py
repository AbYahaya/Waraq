"""TOC detection + edit service — see module docstring for canonical scope."""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.invariant.enums import OperationMode
from waraq.revision.service import create_revision
from waraq.schemas import Block, Page, Revision, Segment
from waraq.schemas.enums import ChangeSource
from waraq.text_state import (
    join_source_target_text,
    resolve_segment_text_state,
)

# Per `waraq.ocr_export.docx_builder._BLOCK_TYPE_STYLE`:
#   UE → Heading 1, HD → Heading 2.
# These two are the v1.0 TOC-relevant block types. The other block
# types (main_text / MT / FN / QR / RN) are not chapter-marker
# candidates.
HEADING_BLOCK_TYPES: Final[dict[str, int]] = {
    "UE": 1,
    "HD": 2,
}


class TocFallbackKind(StrEnum):
    """Why the TocResult uses fallback entries instead of detected ones."""

    NONE = "none"  # Headings detected — entries are real.
    PAGE_BY_PAGE = "page_by_page"  # No headings; canonical §2.1 fallback.


@dataclass(frozen=True, slots=True)
class TocEntry:
    """One row in the TOC.

    `level` is 1 (UE) or 2 (HD) for detected entries; 1 for fallback
    page-by-page entries.

    `satz_uuid` and `block_uuid` are None when the entry is a fallback
    (no segment exists to attach the heading to). When the entry IS a
    real heading segment, both are populated and the resolver UI uses
    them to dispatch heading edits to the right `create_revision`
    target.

    `ar_text` / `de_text` are the AR-source + DE-translation halves of
    the segment's `text_content` (split on the `\\n---\\n` separator).
    Either may be empty when the segment hasn't been translated yet.
    """

    page_index: int
    page_uuid: _uuid.UUID
    level: int
    ar_text: str
    de_text: str
    satz_uuid: _uuid.UUID | None = None
    block_uuid: _uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class TocResult:
    """Project-wide TOC + fallback marker."""

    entries: list[TocEntry]
    fallback_kind: TocFallbackKind
    detected_heading_count: int = 0
    page_count: int = 0


async def detect_toc(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> TocResult:
    """Build the project TOC by scanning heading-typed blocks.

    No-headings → canonical §2.1 fallback (one entry per active page).
    """
    result = await session.execute(
        select(Page, Block, Segment)
        .join(Block, Block.page_uuid == Page.page_uuid)
        .join(Segment, Segment.block_uuid == Block.block_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(Page.active.is_(True))
        .where(Segment.active.is_(True))
        .where(Block.block_type.in_(list(HEADING_BLOCK_TYPES.keys())))
        .order_by(Page.page_index.asc(), Block.block_index.asc(), Segment.satz_index.asc())
    )
    rows = list(result.all())

    page_count_q = await session.execute(
        select(Page)
        .where(Page.project_uuid == project_uuid)
        .where(Page.active.is_(True))
        .order_by(Page.page_index.asc())
    )
    pages: list[Page] = list(page_count_q.scalars())

    if rows:
        entries: list[TocEntry] = []
        for page, block, segment in rows:
            text_state = await resolve_segment_text_state(session=session, segment=segment)
            entries.append(
                TocEntry(
                    page_index=page.page_index,
                    page_uuid=page.page_uuid,
                    level=HEADING_BLOCK_TYPES[block.block_type],
                    ar_text=text_state.source_text,
                    de_text=text_state.target_text,
                    satz_uuid=segment.satz_uuid,
                    block_uuid=block.block_uuid,
                )
            )
        return TocResult(
            entries=entries,
            fallback_kind=TocFallbackKind.NONE,
            detected_heading_count=len(entries),
            page_count=len(pages),
        )

    # Canonical §2.1 fallback: one entry per active page.
    fallback_entries = [
        TocEntry(
            page_index=p.page_index,
            page_uuid=p.page_uuid,
            level=1,
            ar_text=f"صفحة {p.page_index}",
            de_text=f"Seite {p.page_index}",
            satz_uuid=None,
            block_uuid=None,
        )
        for p in pages
    ]
    return TocResult(
        entries=fallback_entries,
        fallback_kind=TocFallbackKind.PAGE_BY_PAGE,
        detected_heading_count=0,
        page_count=len(pages),
    )


async def edit_toc_entry_heading(
    *,
    session: AsyncSession,
    satz_uuid: _uuid.UUID,
    new_ar_text: str | None = None,
    new_de_text: str | None = None,
    actor_uuid: _uuid.UUID | None = None,
) -> Revision:
    """Edit the AR and/or DE half of a TOC heading segment.

    Writes a single Revision via `create_revision`; the unedited side
    is preserved verbatim. Refuses calls that touch a fallback page-
    by-page entry — that signature requires `satz_uuid` and the
    fallback entries don't have one.

    Raises:
        LookupError: when `satz_uuid` doesn't resolve.
        ValueError: when neither `new_ar_text` nor `new_de_text` is given.
    """
    if new_ar_text is None and new_de_text is None:
        raise ValueError("at least one of new_ar_text / new_de_text must be supplied")

    segment: Segment | None = await session.get(Segment, satz_uuid)
    if segment is None:
        raise LookupError(f"segment {satz_uuid!r} not found")

    text_state = await resolve_segment_text_state(session=session, segment=segment)
    current_ar, current_de = text_state.source_text, text_state.target_text
    final_ar = new_ar_text if new_ar_text is not None else current_ar
    final_de = new_de_text if new_de_text is not None else current_de
    final_text = join_source_target_text(final_ar, final_de)

    revision = await create_revision(
        session=session,
        segment=segment,
        after_text=final_text,
        change_source=ChangeSource.MANUAL,
        operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
        author_uuid=actor_uuid,
    )
    return revision


# Silence unused-warning for re-exported items.
_ = field

__all__ = [
    "HEADING_BLOCK_TYPES",
    "TocEntry",
    "TocFallbackKind",
    "TocResult",
    "detect_toc",
    "edit_toc_entry_heading",
]
