"""Segment endpoints — list segments of a page, fetch one, manual edit.

Manual edit writes a Revision via the canonical `create_revision` service
(`change_source=manual`, `operation_mode=manual_with_confirmation`). The
INVARIANT-Guard refuses automatic writes to locked segments — manual edits
with confirmation context bypass that guard, which is the canonical H-1/H-2
behaviour.

§2.2 auto-normalize (Phase 3 sub-batch B): manual-edit `after_text` is
passed through `apply_all` before the Revision is staged. This is the
canonical "no user judgment — direct system mechanism" enforcement
applied to the manual-edit write path so the segment text content can
never come to rest with Arabic-Indic digits / Ḳ / ḳ / Dj / dj or
multi-char religious-formula spellings. Idempotent — translation
pipeline already normalizes upstream of `create_revision`, this just
covers the manual-edit branch.
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from waraq.api._ownership import owned_page_or_404, owned_segment_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import (
    SegmentEditRequest,
    SegmentResponse,
    SegmentTranslationEditRequest,
    SegmentTranslationStyleRequest,
)
from waraq.canon_rules import apply_all as apply_canon_rules
from waraq.invariant.enums import OperationMode
from waraq.invariant.exceptions import H1H2Violation
from waraq.revision.service import create_revision
from waraq.schemas import Block, Segment
from waraq.schemas.enums import ChangeSource
from waraq.translation_styles import (
    read_translation_style_map,
    write_translation_style_key,
)

router = APIRouter(tags=["segments"])


@router.get("/pages/{page_uuid}/segments", response_model=list[SegmentResponse])
async def list_segments_in_page(
    page_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> list[SegmentResponse]:
    await owned_page_or_404(session, page_uuid, current.account_uuid)
    result = await session.execute(
        select(Segment, Block.block_type)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .where(Block.page_uuid == page_uuid, Segment.active.is_(True))
        .order_by(Block.block_index.asc(), Segment.satz_index.asc())
    )
    rows = result.all()
    style_map = await read_translation_style_map(
        session=session, segment_uuids=[segment.satz_uuid for segment, _block_type in rows]
    )
    return [
        SegmentResponse.model_validate(segment).model_copy(
            update={
                "block_type": block_type,
                "translation_style_key": style_map.get(segment.satz_uuid),
            }
        )
        for segment, block_type in rows
    ]


@router.get("/segments/{satz_uuid}", response_model=SegmentResponse)
async def get_segment(
    satz_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> SegmentResponse:
    segment = await owned_segment_or_404(session, satz_uuid, current.account_uuid)
    block_type = await session.scalar(
        select(Block.block_type).where(Block.block_uuid == segment.block_uuid)
    )
    style_map = await read_translation_style_map(
        session=session, segment_uuids=[segment.satz_uuid]
    )
    return SegmentResponse.model_validate(segment).model_copy(
        update={
            "block_type": block_type,
            "translation_style_key": style_map.get(segment.satz_uuid),
        }
    )


@router.put("/segments/{satz_uuid}/text", response_model=SegmentResponse)
async def edit_segment_text(
    satz_uuid: _uuid.UUID,
    req: SegmentEditRequest,
    session: DbSession,
    current: CurrentAccount,
) -> SegmentResponse:
    """Manually edit a segment's text. Writes a Revision with
    `change_source=manual`. Authorized for owners of the project."""
    segment = await owned_segment_or_404(session, satz_uuid, current.account_uuid)
    # §2.2 — apply canon rules silently before the Revision is staged.
    normalized = apply_canon_rules(req.after_text)
    try:
        await create_revision(
            session=session,
            segment=segment,
            after_text=normalized,
            change_source=ChangeSource.MANUAL,
            operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
            author_uuid=current.account_uuid,
        )
    except H1H2Violation as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Segment is locked ({exc!s})",
        ) from exc
    block_type = await session.scalar(
        select(Block.block_type).where(Block.block_uuid == segment.block_uuid)
    )
    style_map = await read_translation_style_map(
        session=session, segment_uuids=[segment.satz_uuid]
    )
    return SegmentResponse.model_validate(segment).model_copy(
        update={
            "block_type": block_type,
            "translation_style_key": style_map.get(segment.satz_uuid),
        }
    )


@router.put("/segments/{satz_uuid}/translation-text", response_model=SegmentResponse)
async def edit_segment_translation_text(
    satz_uuid: _uuid.UUID,
    req: SegmentTranslationEditRequest,
    session: DbSession,
    current: CurrentAccount,
) -> SegmentResponse:
    """Manually edit a segment's translation text.

    Writes a Revision with `change_source=re_translate`, allowing the
    target-side text to be corrected independently of the OCR/source
    revision stream.
    """
    segment = await owned_segment_or_404(session, satz_uuid, current.account_uuid)
    try:
        await create_revision(
            session=session,
            segment=segment,
            after_text=req.after_text,
            change_source=ChangeSource.RE_TRANSLATE,
            operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
            author_uuid=current.account_uuid,
        )
    except H1H2Violation as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Segment is locked ({exc!s})",
        ) from exc
    block_type = await session.scalar(
        select(Block.block_type).where(Block.block_uuid == segment.block_uuid)
    )
    style_map = await read_translation_style_map(
        session=session, segment_uuids=[segment.satz_uuid]
    )
    return SegmentResponse.model_validate(segment).model_copy(
        update={
            "block_type": block_type,
            "translation_style_key": style_map.get(segment.satz_uuid),
        }
    )


@router.put("/segments/{satz_uuid}/translation-style", response_model=SegmentResponse)
async def edit_segment_translation_style(
    satz_uuid: _uuid.UUID,
    req: SegmentTranslationStyleRequest,
    session: DbSession,
    current: CurrentAccount,
) -> SegmentResponse:
    """Persist a segment's canonical translation paragraph style key."""
    segment = await owned_segment_or_404(session, satz_uuid, current.account_uuid)
    await write_translation_style_key(
        session=session,
        segment_uuid=satz_uuid,
        internal_style_key=req.internal_style_key,
        actor_uuid=current.account_uuid,
    )
    block_type = await session.scalar(
        select(Block.block_type).where(Block.block_uuid == segment.block_uuid)
    )
    style_map = await read_translation_style_map(
        session=session, segment_uuids=[segment.satz_uuid]
    )
    return SegmentResponse.model_validate(segment).model_copy(
        update={
            "block_type": block_type,
            "translation_style_key": style_map.get(segment.satz_uuid),
        }
    )
