"""Translation paragraph style helpers.

Segment-level paragraph styles are stored as Decision Events rather than a
mutable table. The segment remains the text/provenance anchor; the latest style
decision tells the editor and export path which canonical paragraph style to
apply to that anchor.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.decisions import create_decision_event
from waraq.schemas import DecisionEvent
from waraq.schemas.enums import DecisionSource, ScopeType

DEFAULT_TRANSLATION_STYLE_KEY: Final[str] = "body_de"

TRANSLATION_PARAGRAPH_STYLE_KEYS: Final[set[str]] = {
    "body_de",
    "body_de_no_indent",
    "heading_1",
    "heading_2",
    "heading_3",
    "heading_4",
    "heading_5",
    "heading_6",
    "quran_de",
    "hadith_de",
    "quote_de",
    "source_note",
    "footnote_text",
}


def normalize_translation_style_key(value: str | None) -> str:
    key = str(value or "").strip().lower()
    if key in TRANSLATION_PARAGRAPH_STYLE_KEYS:
        return key
    return DEFAULT_TRANSLATION_STYLE_KEY


async def read_translation_style_map(
    *, session: AsyncSession, segment_uuids: list[_uuid.UUID] | set[_uuid.UUID]
) -> dict[_uuid.UUID, str]:
    if not segment_uuids:
        return {}
    segment_uuid_set = set(segment_uuids)
    result = await session.execute(
        select(DecisionEvent)
        .where(DecisionEvent.scope_type == ScopeType.SEGMENT.value)
        .where(DecisionEvent.scope_uuid.in_(segment_uuid_set))
        .where(DecisionEvent.decision_source == DecisionSource.STYLE_MANAGEMENT.value)
        .where(DecisionEvent.decision_type == "translation_paragraph_style_update")
        .order_by(DecisionEvent.created_at.asc())
    )
    styles: dict[_uuid.UUID, str] = {}
    for decision in result.scalars():
        content = decision.content or {}
        styles[decision.scope_uuid] = normalize_translation_style_key(
            content.get("internal_style_key") if isinstance(content, dict) else None
        )
    return styles


async def write_translation_style_key(
    *,
    session: AsyncSession,
    segment_uuid: _uuid.UUID,
    internal_style_key: str,
    actor_uuid: _uuid.UUID,
) -> DecisionEvent:
    normalized = normalize_translation_style_key(internal_style_key)
    return await create_decision_event(
        session=session,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=segment_uuid,
        decision_type="translation_paragraph_style_update",
        decision_source=DecisionSource.STYLE_MANAGEMENT,
        actor_uuid=actor_uuid,
        content={"internal_style_key": normalized},
    )

