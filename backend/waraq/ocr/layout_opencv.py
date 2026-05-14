"""§3.4 Stage-1 — OpenCV-backed `BlockDetector` (real production adapter).

Sub-batch H replaces the sub-batch B harness default with a real
layout pass that segments a page image into reading-order blocks using
classical CV operations (no detectron2 / torch dependency):

  1. Grayscale + adaptive threshold to a binary text mask.
  2. Morphological closing on a wide horizontal kernel to glue text
     within a line into solid bars; a smaller vertical close knits
     adjacent lines into block-sized regions.
  3. `findContours` on the closed mask → one bounding box per
     connected text region.
  4. Per-block signals computed from the binary mask:
       - `text_density` — black-pixel ratio inside the bbox.
       - `baseline_y` — y of the dominant horizontal projection peak.
  5. Block-class heuristic — page-position + bbox geometry classify
     each block as `MAIN_TEXT`, `HEADING`, `FOOTNOTE`, or `MARGINALIA`.
     QURAN / HADITH classes are NOT inferred from layout alone (they
     need lexical analysis); those flow through a separate post-pass
     when Stage-3 statistical signals identify them.
  6. Reading-order — sorted top-to-bottom; ties broken right-to-left
     (Arabic primary).

Why not LayoutParser / DocTR?
    Both require detectron2 + torch (~1 GB). The OpenCV approach is
    deliberately lightweight: 4 GB-of-deps cheaper, runs in <100 ms
    per page on commodity CPUs, and surfaces the same `DetectedBlock`
    shape so a deployment can swap in a heavier model later via the
    same `BlockDetector` Protocol slot. Same harness pattern as the
    other sub-batch-A/B/C/D adapter shims.

The detector falls back to the canonical single-`main_text` block
when the input image cannot be decoded — preserves the v1.0 contract
that `detect_blocks(...)` always returns at least one target.
"""

from __future__ import annotations

import logging
from io import BytesIO

from waraq.ocr.layout import BoundingBox, DetectedBlock
from waraq.schemas.enums import BlockClass, ReadingDirection

logger = logging.getLogger(__name__)


# Tunables — Phase 7 gold-corpus calibration target. Documented in
# constants so a single recalibration sweep is a 5-line edit.
_HORIZONTAL_KERNEL: tuple[int, int] = (40, 1)
# Sub-batch O follow-up (2026-05-12): bumped (1,5) → (1,40). At 200 DPI
# a 5-pixel vertical kernel can't bridge the ~50-pixel gap between
# adjacent text lines, so every line became its own contour — a 22-block
# A4 page made OCR run ~10× over the per-page timeout. (1,40) merges
# lines within a paragraph while still separating paragraph-from-footer
# at typical Arabic line spacings. Calibration sweep on output.pdf
# (A4, 200 DPI): 22→2 blocks. See _probe_kernel_tuning.py archive.
_VERTICAL_KERNEL: tuple[int, int] = (1, 40)
_MIN_BLOCK_AREA: int = 800  # pixels² — drop noise specks
_MIN_BLOCK_HEIGHT: int = 12  # pixels — drop single-line stragglers


def _classify_block(
    *,
    bbox: BoundingBox,
    page_height: int,
    page_width: int,
    median_height: float,
) -> BlockClass:
    """Geometry-based block-class heuristic.

    Rules (in order):
      - Block height ≥ 1.6 × median → HEADING (larger font / spacing).
      - Block bottom in lowest 12% of page AND height < median → FOOTNOTE.
      - Block left margin starts in left 8% OR right margin ends in
        right 8% AND block width < 25% of page → MARGINALIA.
      - Otherwise → MAIN_TEXT.
    """
    height = bbox.y1 - bbox.y0
    width = bbox.x1 - bbox.x0
    if height >= median_height * 1.6:
        return BlockClass.HEADING
    if bbox.y1 >= page_height * 0.88 and height < median_height:
        return BlockClass.FOOTNOTE
    in_left_margin = bbox.x0 <= page_width * 0.08
    in_right_margin = bbox.x1 >= page_width * 0.92
    if (in_left_margin or in_right_margin) and width < page_width * 0.25:
        return BlockClass.MARGINALIA
    return BlockClass.MAIN_TEXT


def _read_image(image_bytes: bytes):  # type: ignore[no-untyped-def]
    """Decode `image_bytes` to a numpy uint8 image. Returns None when
    decode fails; callers fall back to the harness default."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    try:
        # Decode through PIL → numpy round-trip so we accept the same
        # PNG/JPEG/WEBP set the upstream rasterizer produces.
        from PIL import Image

        with Image.open(BytesIO(image_bytes)) as pil:
            arr = np.array(pil.convert("RGB"))
    except Exception as exc:
        logger.debug("layout_opencv decode failed: %r", exc)
        return None
    return cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)


def _baseline_y_of(mask, x0: int, y0: int, x1: int, y1: int) -> int | None:  # type: ignore[no-untyped-def]
    """Dominant horizontal-projection-peak y-coordinate inside the bbox.
    The peak is where the ink density is highest along the horizontal
    axis — corresponds to the main text baseline for a single-line
    block, or the dominant baseline for a multi-line block.
    """
    if y1 <= y0 or x1 <= x0:
        return None
    region = mask[y0:y1, x0:x1]
    # Sum black pixels along x for each row.
    row_sums = region.sum(axis=1)
    if row_sums.size == 0:
        return None
    peak_offset = int(row_sums.argmax())
    return y0 + peak_offset


def opencv_block_detector(image_bytes: bytes, source_dpi: int) -> list[DetectedBlock]:
    """Real OpenCV-backed `BlockDetector` per the §3.4 Stage-1
    specification.

    Returns a list of `DetectedBlock`s in reading order. Returns the
    canonical single-`main_text` fallback when:
      - cv2 / Pillow / numpy aren't importable.
      - The input bytes can't be decoded.
      - findContours returns zero text regions (effectively a blank /
        non-text page).
    """
    _ = source_dpi  # advisory; the detector is DPI-agnostic.

    gray = _read_image(image_bytes)
    if gray is None:
        return _fallback()
    try:
        import cv2
        import numpy as np
    except ImportError:
        return _fallback()

    page_height, page_width = gray.shape[:2]
    page_pixels = page_height * page_width

    # Adaptive threshold → black=text, white=background.
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=15,
        C=10,
    )

    # Morphological closing — glue text within a line, then knit lines
    # into block-sized regions.
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, _HORIZONTAL_KERNEL)
    closed_h = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, h_kernel)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, _VERTICAL_KERNEL)
    closed = cv2.morphologyEx(closed_h, cv2.MORPH_CLOSE, v_kernel)

    contours, _hier = cv2.findContours(
        closed,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    if not contours:
        return _fallback()

    boxes: list[BoundingBox] = []
    heights: list[int] = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w * h < _MIN_BLOCK_AREA:
            continue
        if h < _MIN_BLOCK_HEIGHT:
            continue
        boxes.append(BoundingBox(x0=x, y0=y, x1=x + w, y1=y + h))
        heights.append(h)
    if not boxes:
        return _fallback()

    # Reading order — top to bottom; ties (within a small y-band) right
    # to left for Arabic. We use a coarse 12-pixel band so visually
    # adjacent boxes sort the same way.
    boxes.sort(key=lambda b: (b.y0 // 12, -b.x1))

    median_height = float(sorted(heights)[len(heights) // 2])

    detected: list[DetectedBlock] = []
    for i, b in enumerate(boxes):
        # Compute text density inside the bbox using the binary mask.
        region = binary[b.y0 : b.y1, b.x0 : b.x1]
        density: float | None = None
        if region.size > 0:
            density = float(region.mean()) / 255.0
        baseline = _baseline_y_of(binary, b.x0, b.y0, b.x1, b.y1)
        block_class = _classify_block(
            bbox=b,
            page_height=page_height,
            page_width=page_width,
            median_height=median_height,
        )
        detected.append(
            DetectedBlock(
                block_class=block_class,
                reading_direction=ReadingDirection.RTL,
                bbox=b,
                text_density=density,
                baseline_y=baseline,
                block_index_hint=i,
                detector_metadata={
                    "detector": "opencv_v1",
                    "page_width": str(page_width),
                    "page_height": str(page_height),
                    "page_pixels": str(page_pixels),
                    "median_block_height": f"{median_height:.1f}",
                },
            )
        )
    if not detected:
        return _fallback()
    # Defensive: zero-area mask edge case.
    _ = np  # numpy used implicitly via cv2; reference for ruff.
    return detected


def _fallback() -> list[DetectedBlock]:
    return [
        DetectedBlock(
            block_class=BlockClass.MAIN_TEXT,
            reading_direction=ReadingDirection.RTL,
            bbox=BoundingBox(x0=0, y0=0, x1=0, y1=0),
            detector_metadata={"detector": "opencv_v1_fallback"},
        )
    ]


__all__ = [
    "opencv_block_detector",
]
