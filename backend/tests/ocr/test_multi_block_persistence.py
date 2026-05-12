"""Phase 4 sub-batch C — multi-block-per-page persistence.

`_ensure_blocks_and_segments` materializes one `(Block, Segment)` row
per `DetectedBlock` returned by the Stage-1 layout detector. The
sub-batch B path only created one Block per page; sub-batch C extends
it to N blocks while preserving:

  - First-detector-wins idempotency (re-runs don't overwrite layout
    fields).
  - Reading-order block_index assignment (`i` for the i-th detected
    block).
  - One `Segment(satz_index=0)` per Block (sub-batch D's three-track
    consensus may later split segments inside a block).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project
from waraq.ocr.layout import BoundingBox, DetectedBlock
from waraq.ocr.page_runner import _ensure_blocks_and_segments
from waraq.schemas import Block, Page, Segment
from waraq.schemas.enums import BlockClass, ReadingDirection


def _detected(
    *,
    block_class: BlockClass,
    direction: ReadingDirection = ReadingDirection.RTL,
    bbox: tuple[int, int, int, int] = (0, 0, 0, 0),
    text_density: float | None = None,
    baseline_y: int | None = None,
) -> DetectedBlock:
    x0, y0, x1, y1 = bbox
    return DetectedBlock(
        block_class=block_class,
        reading_direction=direction,
        bbox=BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1),
        text_density=text_density,
        baseline_y=baseline_y,
    )


async def _seed_page(db_session: AsyncSession, *, page_index: int) -> Page:
    project = await seed_project(db_session)
    page = Page(
        page_uuid=uuid.uuid4(),
        project_uuid=project.project_uuid,
        page_index=page_index,
    )
    db_session.add(page)
    await db_session.flush()
    return page


@pytest.mark.asyncio
class TestMultiBlockCreation:
    async def test_creates_one_row_per_detected_block(self, db_session: AsyncSession) -> None:
        page = await _seed_page(db_session, page_index=1)
        detected = [
            _detected(block_class=BlockClass.HEADING, bbox=(0, 0, 800, 80)),
            _detected(block_class=BlockClass.MAIN_TEXT, bbox=(0, 80, 800, 700)),
            _detected(block_class=BlockClass.FOOTNOTE, bbox=(0, 700, 800, 800)),
        ]
        paired = await _ensure_blocks_and_segments(
            session=db_session, page=page, detected_blocks=detected
        )
        assert len(paired) == 3

        blocks_q = await db_session.execute(
            select(Block).where(Block.page_uuid == page.page_uuid).order_by(Block.block_index.asc())
        )
        blocks = list(blocks_q.scalars())
        assert len(blocks) == 3
        assert [b.block_type for b in blocks] == ["heading", "main_text", "footnote"]
        assert [b.block_index for b in blocks] == [0, 1, 2]

        seg_q = await db_session.execute(
            select(Segment)
            .where(Segment.block_uuid.in_([b.block_uuid for b in blocks]))
            .where(Segment.active.is_(True))
        )
        segments = list(seg_q.scalars())
        assert len(segments) == 3
        assert all(s.satz_index == 0 for s in segments)
        assert all(s.text_content == "" for s in segments)

    async def test_block_index_follows_detection_order(self, db_session: AsyncSession) -> None:
        page = await _seed_page(db_session, page_index=2)
        detected = [
            _detected(block_class=BlockClass.MARGINALIA),
            _detected(block_class=BlockClass.MAIN_TEXT),
            _detected(block_class=BlockClass.QURAN),
        ]
        paired = await _ensure_blocks_and_segments(
            session=db_session, page=page, detected_blocks=detected
        )
        assert [p[0].block_index for p in paired] == [0, 1, 2]
        assert [p[0].block_type for p in paired] == ["marginalia", "main_text", "quran"]

    async def test_writes_layout_fields_on_first_create(self, db_session: AsyncSession) -> None:
        page = await _seed_page(db_session, page_index=3)
        detected = [
            _detected(
                block_class=BlockClass.MAIN_TEXT,
                direction=ReadingDirection.LTR,
                text_density=0.42,
                baseline_y=128,
            )
        ]
        paired = await _ensure_blocks_and_segments(
            session=db_session, page=page, detected_blocks=detected
        )
        block, _, _ = paired[0]
        assert block.reading_direction == ReadingDirection.LTR
        assert block.text_density == pytest.approx(0.42)
        assert block.baseline_y == 128


@pytest.mark.asyncio
class TestMultiBlockIdempotency:
    async def test_rerun_with_same_detector_returns_same_rows(
        self, db_session: AsyncSession
    ) -> None:
        page = await _seed_page(db_session, page_index=10)
        detected = [
            _detected(block_class=BlockClass.HEADING),
            _detected(block_class=BlockClass.MAIN_TEXT),
        ]
        first = await _ensure_blocks_and_segments(
            session=db_session, page=page, detected_blocks=detected
        )
        second = await _ensure_blocks_and_segments(
            session=db_session, page=page, detected_blocks=detected
        )
        assert [p[0].block_uuid for p in first] == [p[0].block_uuid for p in second]
        assert [p[1].satz_uuid for p in first] == [p[1].satz_uuid for p in second]

        blocks_q = await db_session.execute(select(Block).where(Block.page_uuid == page.page_uuid))
        blocks = list(blocks_q.scalars())
        assert len(blocks) == 2  # no duplicate rows

    async def test_first_detector_wins_on_layout_fields(self, db_session: AsyncSession) -> None:
        """Re-running with a different DetectedBlock at the same index
        does NOT overwrite the layout fields. Re-running OCR after an
        explicit reset is the canonical path to update layout
        metadata."""
        page = await _seed_page(db_session, page_index=11)

        first_detected = [
            _detected(
                block_class=BlockClass.MAIN_TEXT,
                direction=ReadingDirection.RTL,
                text_density=0.30,
            )
        ]
        b1, _, _ = (
            await _ensure_blocks_and_segments(
                session=db_session, page=page, detected_blocks=first_detected
            )
        )[0]

        second_detected = [
            _detected(
                block_class=BlockClass.HEADING,
                direction=ReadingDirection.LTR,
                text_density=0.99,
            )
        ]
        b2, _, _ = (
            await _ensure_blocks_and_segments(
                session=db_session, page=page, detected_blocks=second_detected
            )
        )[0]

        assert b2.block_uuid == b1.block_uuid
        assert b2.block_type == "main_text"  # NOT heading
        assert b2.reading_direction == ReadingDirection.RTL
        assert b2.text_density == pytest.approx(0.30)

    async def test_growing_detector_adds_new_blocks_keeps_old(
        self, db_session: AsyncSession
    ) -> None:
        """A second run that detects MORE blocks than the first should
        add the new ones (block_index >= existing max + 1) without
        disturbing the existing ones."""
        page = await _seed_page(db_session, page_index=12)
        first = [_detected(block_class=BlockClass.MAIN_TEXT)]
        await _ensure_blocks_and_segments(session=db_session, page=page, detected_blocks=first)

        # Second run sees two blocks. Detection order means index 0
        # remains the original main_text; index 1 is the new footnote.
        second = [
            _detected(block_class=BlockClass.MAIN_TEXT),
            _detected(block_class=BlockClass.FOOTNOTE),
        ]
        paired = await _ensure_blocks_and_segments(
            session=db_session, page=page, detected_blocks=second
        )
        assert len(paired) == 2
        assert paired[0][0].block_type == "main_text"
        assert paired[1][0].block_type == "footnote"
        assert paired[1][0].block_index == 1
