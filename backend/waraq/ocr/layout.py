"""§3.4 Stage-1 — layout / block detection harness.

Canon §3.4 Stage 1 mandates LayoutParser (or DocTR) for block
detection: replace the v1.0 single-`main_text`-per-page assumption
with a real layout pass that emits one `DetectedBlock` per region,
each carrying its class (§3.4 Stage-2 routing input), reading
direction, baseline / text-density signals, and bounding box.

This module ships the **harness**:

  - `DetectedBlock` dataclass — the canonical output shape every
    layout adapter returns. Persistence on the `blocks` table reads
    `block_class` + `reading_direction` + optional `text_density` from
    here.
  - `BlockDetector` Protocol — `(image_bytes, source_dpi) -> list[DetectedBlock]`.
    Real adapters (LayoutParser, DocTR) plug in via this signature.
  - `_default_block_detector` — single-`main_text`-block fallback.
    Preserves the v1.0 behaviour exactly so deployments without
    LayoutParser see no functional change.
  - `detect_blocks(...)` — the integration point `run_ocr_for_page`
    calls.

The Real LayoutParser model invocation (~1 GB + detectron2 + torch)
is deliberately a deployment-supplied adapter: the *taxonomy + harness
+ persistence shape* land in code; the *implementation* is pluggable.
Same pattern as the §3.3 preprocessing harness in sub-batch A.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from waraq.schemas.enums import BlockClass, ReadingDirection


@dataclass(frozen=True, kw_only=True, slots=True)
class BoundingBox:
    """Pixel-space bounding box on the page-rendered image. Origin is
    top-left, x increases right, y increases down (PIL/PNG convention).

    All four values are pixel offsets, not normalized fractions —
    detector adapters return image-coordinates and the caller scales
    when needed.
    """

    x0: int
    y0: int
    x1: int
    y1: int


@dataclass(frozen=True, kw_only=True, slots=True)
class DetectedBlock:
    """One layout-detected block per §3.4 Stage 1.

    Fields:
        block_class: Canonical class per `BlockClass`. Stage-2 OCR
            routing reads this to pick the right reading line.
        reading_direction: RTL / LTR / UNKNOWN per the Stage-1
            reading-direction map.
        bbox: Pixel-space bounding box on the page-rendered image.
        text_density: Optional black-pixel density in [0, 1]. Real
            adapters compute it from the rasterized region; the
            default detector leaves it None.
        baseline_y: Optional dominant text baseline y-coordinate in
            pixels. Used by Stage-1 baseline-detection. The default
            detector leaves it None.
        block_index_hint: Optional reading-order index hint. When
            present, callers should use it to order Block rows on the
            page. None means "use detection order".
    """

    block_class: BlockClass
    reading_direction: ReadingDirection
    bbox: BoundingBox
    text_density: float | None = None
    baseline_y: int | None = None
    block_index_hint: int | None = None
    # Free-form provenance crumbs the detector wants to surface (e.g.
    # confidence, model version). Persisted on Block-side audit when
    # populated; not used for control flow here.
    detector_metadata: dict[str, str] = field(default_factory=dict)


BlockDetector = Callable[[bytes, int], list[DetectedBlock]]


def _default_block_detector(image_bytes: bytes, source_dpi: int) -> list[DetectedBlock]:
    """v1.0 fallback: return a single `main_text` block covering the
    whole page with default RTL reading direction.

    Preserves the pre-Phase-4 single-Block-per-page behaviour so
    deployments without LayoutParser see no functional change. The
    bounding box is a sentinel `(0, 0, 0, 0)` because the harness
    does not know image dimensions without decoding the bytes; real
    adapters return real boxes.
    """
    _ = (image_bytes, source_dpi)
    return [
        DetectedBlock(
            block_class=BlockClass.MAIN_TEXT,
            reading_direction=ReadingDirection.RTL,
            bbox=BoundingBox(x0=0, y0=0, x1=0, y1=0),
            detector_metadata={"detector": "default_single_main_text"},
        )
    ]


def detect_blocks(
    image_bytes: bytes,
    source_dpi: int,
    *,
    detector: BlockDetector | None = None,
) -> list[DetectedBlock]:
    """Run the configured layout detector over `image_bytes`.

    Falls back to `_default_block_detector` when no detector is
    configured. Returning an empty list is **not** valid — a page
    that produced zero detected blocks should still get the default
    single-`main_text` block, otherwise downstream OCR has nothing to
    target. Callers that supply a custom detector are responsible for
    matching this contract.
    """
    fn = detector if detector is not None else _default_block_detector
    blocks = fn(image_bytes, source_dpi)
    if not blocks:
        # Conservative fallback so OCR always has at least one target.
        return _default_block_detector(image_bytes, source_dpi)
    return blocks


__all__ = [
    "BlockDetector",
    "BoundingBox",
    "DetectedBlock",
    "detect_blocks",
]
