"""Phase 4 sub-batch B — §3.4 Stage-1 layout detection harness.

Three orthogonal layers covered:

1. `BlockClass` + `ReadingDirection` enum surface (canonical six +
   three values; wire identifiers stable).
2. `_default_block_detector` + `detect_blocks` harness (single-block
   fallback, custom adapter wiring, empty-result conservative
   fallback).
3. Persistence: `_ensure_block_and_segment` writes the detected
   layout fields onto a fresh Block; idempotent on re-call.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project
from waraq.ocr.layout import (
    BoundingBox,
    DetectedBlock,
    _default_block_detector,
    detect_blocks,
)
from waraq.ocr.page_runner import _ensure_block_and_segment
from waraq.schemas import Block, Page
from waraq.schemas.enums import BlockClass, ReadingDirection


class TestEnumSurface:
    """The canonical 6 BlockClass values + 3 ReadingDirection values
    are wire identifiers — string-stable, renaming is canon-shaped."""

    def test_block_class_canonical_six(self) -> None:
        assert {c.value for c in BlockClass} == {
            "main_text",
            "footnote",
            "heading",
            "quran",
            "hadith",
            "marginalia",
        }

    def test_reading_direction_three_values(self) -> None:
        assert {d.value for d in ReadingDirection} == {"rtl", "ltr", "unknown"}


class TestDefaultDetector:
    """The v1.0 fallback returns one main_text + RTL block.
    Preserves pre-Phase-4 single-Block-per-page behaviour exactly."""

    def test_returns_single_block(self) -> None:
        blocks = _default_block_detector(b"any-bytes", 200)
        assert len(blocks) == 1

    def test_block_is_main_text_rtl(self) -> None:
        block = _default_block_detector(b"", 200)[0]
        assert block.block_class == BlockClass.MAIN_TEXT
        assert block.reading_direction == ReadingDirection.RTL

    def test_metadata_records_detector_identity(self) -> None:
        block = _default_block_detector(b"", 200)[0]
        assert block.detector_metadata.get("detector") == "default_single_main_text"

    def test_density_and_baseline_unset(self) -> None:
        # The default detector doesn't compute these — Real-LayoutParser
        # / DocTR adapters do. Honest None when no signal.
        block = _default_block_detector(b"", 200)[0]
        assert block.text_density is None
        assert block.baseline_y is None


class TestDetectBlocksHarness:
    def test_default_path_uses_default_detector(self) -> None:
        blocks = detect_blocks(b"raw", 200)
        assert len(blocks) == 1
        assert blocks[0].block_class == BlockClass.MAIN_TEXT

    def test_custom_detector_invoked(self) -> None:
        captured: list[tuple[bytes, int]] = []

        def fake(bytes_in: bytes, dpi: int) -> list[DetectedBlock]:
            captured.append((bytes_in, dpi))
            return [
                DetectedBlock(
                    block_class=BlockClass.HEADING,
                    reading_direction=ReadingDirection.RTL,
                    bbox=BoundingBox(x0=0, y0=0, x1=100, y1=50),
                ),
                DetectedBlock(
                    block_class=BlockClass.MAIN_TEXT,
                    reading_direction=ReadingDirection.RTL,
                    bbox=BoundingBox(x0=0, y0=50, x1=100, y1=200),
                ),
            ]

        blocks = detect_blocks(b"abc", 150, detector=fake)
        assert len(blocks) == 2
        assert blocks[0].block_class == BlockClass.HEADING
        assert blocks[1].block_class == BlockClass.MAIN_TEXT
        assert captured == [(b"abc", 150)]

    def test_empty_detector_result_falls_back_to_default(self) -> None:
        """A misbehaving detector that returns [] is recovered to the
        single-`main_text` default — OCR must always have at least one
        target block per page."""

        def empty(_b: bytes, _d: int) -> list[DetectedBlock]:
            return []

        blocks = detect_blocks(b"", 200, detector=empty)
        assert len(blocks) == 1
        assert blocks[0].block_class == BlockClass.MAIN_TEXT


@pytest.mark.asyncio
class TestEnsureBlockAndSegmentLayoutPersistence:
    async def test_writes_detected_layout_fields_on_create(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        page = Page(
            page_uuid=__import__("uuid").uuid4(),
            project_uuid=project.project_uuid,
            page_index=1,
        )
        db_session.add(page)
        await db_session.flush()

        detected = DetectedBlock(
            block_class=BlockClass.HEADING,
            reading_direction=ReadingDirection.LTR,
            bbox=BoundingBox(x0=0, y0=0, x1=10, y1=10),
            text_density=0.42,
            baseline_y=128,
        )
        block, _segment = await _ensure_block_and_segment(
            session=db_session, page=page, detected=detected
        )
        assert block.block_type == "heading"
        assert block.reading_direction == ReadingDirection.LTR
        assert block.text_density == pytest.approx(0.42)
        assert block.baseline_y == 128

    async def test_legacy_no_detected_yields_main_text_default(
        self, db_session: AsyncSession
    ) -> None:
        """Callers that don't supply a DetectedBlock get the historical
        single-main_text + default-RTL behaviour. Preserves pre-sub-batch-B
        callers exactly."""
        project = await seed_project(db_session)
        page = Page(
            page_uuid=__import__("uuid").uuid4(),
            project_uuid=project.project_uuid,
            page_index=2,
        )
        db_session.add(page)
        await db_session.flush()

        block, _segment = await _ensure_block_and_segment(session=db_session, page=page)
        assert block.block_type == "main_text"
        # server_default rtl applies on insert
        result = await db_session.execute(select(Block).where(Block.block_uuid == block.block_uuid))
        refetched = result.scalar_one()
        assert refetched.reading_direction == ReadingDirection.RTL
        assert refetched.text_density is None
        assert refetched.baseline_y is None

    async def test_idempotent_does_not_overwrite_layout_on_reuse(
        self, db_session: AsyncSession
    ) -> None:
        """First detector wins. A second call with a different
        DetectedBlock must NOT silently re-stamp the existing Block —
        re-running OCR after an explicit reset is the canonical path
        for replacing layout metadata."""
        project = await seed_project(db_session)
        page = Page(
            page_uuid=__import__("uuid").uuid4(),
            project_uuid=project.project_uuid,
            page_index=3,
        )
        db_session.add(page)
        await db_session.flush()

        first = DetectedBlock(
            block_class=BlockClass.MAIN_TEXT,
            reading_direction=ReadingDirection.RTL,
            bbox=BoundingBox(x0=0, y0=0, x1=10, y1=10),
            text_density=0.30,
        )
        b1, _ = await _ensure_block_and_segment(session=db_session, page=page, detected=first)
        first_density = b1.text_density

        second = DetectedBlock(
            block_class=BlockClass.HEADING,
            reading_direction=ReadingDirection.LTR,
            bbox=BoundingBox(x0=0, y0=0, x1=10, y1=10),
            text_density=0.99,
        )
        b2, _ = await _ensure_block_and_segment(session=db_session, page=page, detected=second)
        assert b2.block_uuid == b1.block_uuid
        assert b2.block_type == "main_text"
        assert b2.reading_direction == ReadingDirection.RTL
        assert b2.text_density == pytest.approx(first_density)
