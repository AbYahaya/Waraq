"""Phase 4 sub-batch H — OpenCV-backed `BlockDetector` production adapter."""

from __future__ import annotations

from io import BytesIO

import pytest

from waraq.ocr.layout import detect_blocks
from waraq.ocr.layout_opencv import opencv_block_detector
from waraq.schemas.enums import BlockClass, ReadingDirection

# Skip the whole module when cv2/PIL aren't importable on this host —
# the harness fallback is already covered by `test_layout_detection.py`.
pytest.importorskip("cv2")
pytest.importorskip("PIL")


def _png_with_blocks(
    *rects: tuple[int, int, int, int], size: tuple[int, int] = (800, 1000)
) -> bytes:
    """Make a synthetic page image with solid black bars at `rects`
    (x0, y0, x1, y1). Black bars proxy for text well enough that the
    OpenCV detector treats each bar as a text region."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    for x0, y0, x1, y1 in rects:
        draw.rectangle((x0, y0, x1, y1), fill="black")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestOpenCVDetector:
    def test_three_separated_blocks_detected(self) -> None:
        # Three distinct horizontal bars with vertical gaps wider than
        # the morphological-close kernel.
        png = _png_with_blocks(
            (60, 50, 740, 90),
            (60, 200, 740, 240),
            (60, 350, 600, 390),
        )
        blocks = opencv_block_detector(png, 200)
        assert len(blocks) == 3
        assert all(b.reading_direction == ReadingDirection.RTL for b in blocks)
        # Reading order: top to bottom.
        ys = [b.bbox.y0 for b in blocks]
        assert ys == sorted(ys)

    def test_density_in_unit_interval(self) -> None:
        png = _png_with_blocks((60, 50, 740, 90))
        blocks = opencv_block_detector(png, 200)
        for b in blocks:
            assert b.text_density is not None
            assert 0.0 <= b.text_density <= 1.0

    def test_baseline_inside_bbox(self) -> None:
        png = _png_with_blocks((60, 100, 740, 140))
        blocks = opencv_block_detector(png, 200)
        b = blocks[0]
        assert b.baseline_y is not None
        assert b.bbox.y0 <= b.baseline_y <= b.bbox.y1

    def test_block_index_hint_monotonic(self) -> None:
        png = _png_with_blocks(
            (60, 50, 740, 90),
            (60, 150, 740, 190),
            (60, 250, 740, 290),
        )
        blocks = opencv_block_detector(png, 200)
        hints = [b.block_index_hint for b in blocks]
        assert hints == [0, 1, 2]

    def test_classifies_tall_block_as_heading(self) -> None:
        # One thick block (heading) + two thin blocks (main text).
        # Sub-batch O follow-up (2026-05-12): bumped vertical-kernel
        # to (1, 40) so adjacent text lines merge into paragraph
        # regions. Test fixture spacing was originally 40 px between
        # main_text blocks — now bumped to 60 px so they stay distinct
        # under the new kernel.
        png = _png_with_blocks(
            (60, 30, 740, 130),  # height 100 — tall
            (60, 200, 740, 230),  # height 30 — normal
            (60, 290, 740, 320),  # height 30 — normal (gap=60 from prev)
        )
        blocks = opencv_block_detector(png, 200)
        # The first block (tall) should be HEADING; the others MAIN_TEXT.
        assert blocks[0].block_class == BlockClass.HEADING
        assert {b.block_class for b in blocks[1:]} == {BlockClass.MAIN_TEXT}

    def test_classifies_bottom_short_block_as_footnote(self) -> None:
        # Page is 1000 tall; a small block in the bottom 12% (y > 880)
        # should be classified FOOTNOTE.
        png = _png_with_blocks(
            (60, 100, 740, 130),  # tall block — main reference
            (60, 920, 740, 945),  # short block in footer band
            size=(800, 1000),
        )
        blocks = opencv_block_detector(png, 200)
        footer = [b for b in blocks if b.bbox.y1 >= 900]
        assert footer
        assert footer[0].block_class == BlockClass.FOOTNOTE

    def test_garbage_bytes_fall_back_to_default(self) -> None:
        blocks = opencv_block_detector(b"not-an-image-at-all", 200)
        # Fallback returns a single MAIN_TEXT sentinel block.
        assert len(blocks) == 1
        assert blocks[0].block_class == BlockClass.MAIN_TEXT
        assert blocks[0].detector_metadata.get("detector") == "opencv_v1_fallback"

    def test_empty_blank_page_falls_back_to_default(self) -> None:
        # Pure white page → no contours → fallback.
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (400, 400), "white").save(buf, format="PNG")
        blocks = opencv_block_detector(buf.getvalue(), 200)
        assert len(blocks) == 1
        assert blocks[0].block_class == BlockClass.MAIN_TEXT


class TestDetectBlocksIntegration:
    """The harness `detect_blocks(...)` wires the OpenCV detector
    correctly when supplied as `detector=` argument."""

    def test_harness_uses_opencv_detector_when_supplied(self) -> None:
        png = _png_with_blocks((60, 50, 740, 90), (60, 200, 740, 240))
        blocks = detect_blocks(png, 200, detector=opencv_block_detector)
        assert len(blocks) == 2

    def test_harness_falls_back_to_default_when_detector_returns_empty(self) -> None:
        # White PNG → opencv_block_detector returns its single-fallback
        # sentinel; detect_blocks should NOT double-fallback (the
        # opencv detector already returns a non-empty list).
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (400, 400), "white").save(buf, format="PNG")
        blocks = detect_blocks(buf.getvalue(), 200, detector=opencv_block_detector)
        assert len(blocks) == 1
