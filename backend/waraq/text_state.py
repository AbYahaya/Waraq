"""Shared source/target text-state resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.schemas import Revision, Segment
from waraq.schemas.enums import ChangeSource

SEPARATOR = "\n---\n"


@dataclass(frozen=True, slots=True)
class SegmentTextState:
    source_text: str
    target_text: str


def split_source_target_text(text: str | None) -> tuple[str, str]:
    if not text:
        return "", ""
    if SEPARATOR in text:
        source, target = text.split(SEPARATOR, 1)
        return source, target
    return text, ""


def join_source_target_text(source_text: str, target_text: str) -> str:
    return f"{source_text}{SEPARATOR}{target_text}"


async def resolve_segment_text_state(
    *,
    session: AsyncSession,
    segment: Segment,
    at_or_before: datetime | None = None,
) -> SegmentTextState:
    stmt = (
        select(Revision.change_source, Revision.after_text)
        .where(Revision.satz_uuid == segment.satz_uuid)
        .order_by(Revision.created_at.asc())
    )
    if at_or_before is not None:
        stmt = stmt.where(Revision.created_at <= at_or_before)

    rows = (await session.execute(stmt)).all()

    latest_source_text: str | None = None
    latest_target_text: str | None = None
    for change_source, after_text in rows:
        if change_source == ChangeSource.RE_TRANSLATE.value:
            latest_target_text = after_text
        else:
            latest_source_text = after_text

    current_source, current_target = split_source_target_text(segment.text_content)

    if latest_source_text is not None:
        source_text, embedded_target = split_source_target_text(latest_source_text)
    else:
        source_text = current_source
        embedded_target = current_target

    if latest_target_text is not None:
        _, target_text = split_source_target_text(latest_target_text)
        if not target_text:
            target_text = latest_target_text
    else:
        target_text = embedded_target or current_target

    return SegmentTextState(source_text=source_text, target_text=target_text)


async def resolve_segment_source_text(
    *,
    session: AsyncSession,
    segment: Segment,
    at_or_before: datetime | None = None,
) -> str:
    return (
        await resolve_segment_text_state(
            session=session,
            segment=segment,
            at_or_before=at_or_before,
        )
    ).source_text


async def resolve_segment_target_text(
    *,
    session: AsyncSession,
    segment: Segment,
    at_or_before: datetime | None = None,
) -> str:
    return (
        await resolve_segment_text_state(
            session=session,
            segment=segment,
            at_or_before=at_or_before,
        )
    ).target_text
