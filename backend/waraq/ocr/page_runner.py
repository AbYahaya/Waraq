"""High-level wrapper that lets a UI button trigger OCR for a Page.

Bridges three concerns the lower-level OCR service deliberately doesn't:

1. **Rasterization** — the OCR service takes raw image bytes; this
   helper renders the right page out of the stored source PDF (via
   poppler's `pdftoppm`) and supplies them.
2. **Block + Segment provisioning** — `run_ocr_job` writes its Revision
   into a target Segment. After upload the project has Pages but no
   Block / Segment rows yet; this helper creates one Block + Segment
   per detected layout block and reuses them on subsequent OCR runs.
   In the current default page-wide path, persistence stays at one
   page-wide `DetectedBlock`; the older multi-block persistence path is
   still available behind `OCR_PAGE_WIDE_MODE=0`.
3. **Source PDF lookup** — pulled from the page's SCAN-PO payload, the
   same path the in-browser viewer uses.

Read-side discipline: never re-creates a Block/Segment when one is
already present. Pure write of Revision + OCR-PO via the existing
service path; no Decision Events, no LINEAGE_EVENT-POs.

§3.4 Stage-2 routing
--------------------
In the legacy segmented path, `consensus.run_engines` is called with
the Stage-2 route for the block's class (QURAN → Gemini-only; others
→ both engines parallel). In the current page-wide default path, the
whole page is OCR'd once per active engine; we no longer fan out into
multiple internal per-region OCR calls. The chosen primary text +
per-engine breakdown + agreement label flow through `run_ocr_job` and
land on each block's OCR-PO payload.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
import uuid as _uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.ocr import run_ocr_job, start_ocr_job
from waraq.ocr.consensus import (
    ConsensusResult,
    run_engines,
)
from waraq.ocr.gemini import extract_text as gemini_extract
from waraq.ocr.layout import BoundingBox, DetectedBlock, detect_blocks
from waraq.ocr.layout_opencv import opencv_block_detector
from waraq.ocr.openai_ocr import OpenAiOcrResult
from waraq.ocr.openai_ocr import extract_with_confidence as openai_ocr_extract
from waraq.ocr.preprocessing import preprocess_if_needed
from waraq.ocr.preprocessing_opencv import opencv_preprocessor
from waraq.ocr.routing import OcrEngine
from waraq.ocr.stage3 import Stage3Result, aggregate_stage3
from waraq.ocr.stage3_ai import AiValidator
from waraq.ocr.stage3_ai_production import (
    Stage3AiValidatorUnconfigured,
    make_gemini_ocr_validator,
    make_openai_ocr_validator,
)
from waraq.ocr.stage3_rules import DiacritizerFn, MorphologyAnalyzableFn
from waraq.schemas import Block, Page, ProvenanceObject, Segment
from waraq.schemas.enums import BlockClass, POType, ReadingDirection, ScopeType
from waraq.upload.file_type import UploadFormat, is_direct_text_format, is_image_format

# Per-page render DPI (matches the historical default in `_render_page_png`).
# Treated as the *source DPI* for §3.3 preprocessing decisions until a real
# DPI extraction from the source PDF lands (Phase 4 sub-batch B at the
# earliest — needs LayoutParser-side image metadata).
_RENDER_DPI: int = 200


# Engine extractor type aliases. Production injects `gemini.extract_text`
# and `openai_ocr.extract_with_confidence`; tests inject stubs.
GeminiExtractorFn = Callable[[bytes, str], Awaitable[str]]
OpenAiOcrExtractorFn = Callable[[bytes, str], Awaitable[OpenAiOcrResult]]


# Lazily-built singleton AI validators for the Stage-3 production
# wiring (sub-batch J). Each factory raises `Stage3AiValidatorUnconfigured`
# when the corresponding API key isn't set; we cache the resolution
# (validator OR `None`) so we don't re-attempt construction on every
# page.
_OPENAI_OCR_VALIDATOR_CACHE: AiValidator | None = None
_OPENAI_OCR_VALIDATOR_RESOLVED: bool = False
_GEMINI_OCR_VALIDATOR_CACHE: AiValidator | None = None
_GEMINI_OCR_VALIDATOR_RESOLVED: bool = False
_PAGE_WIDE_OCR_MODE: bool = os.environ.get("OCR_PAGE_WIDE_MODE", "1") != "0"
_PAGE_WIDE_MULTI_ENGINE_MODE: bool = os.environ.get("OCR_PAGE_WIDE_MULTI_ENGINE", "1") != "0"
_PAGE_WIDE_STAGE3_MODE: bool = os.environ.get("OCR_PAGE_WIDE_STAGE3", "1") != "0"


def _resolve_openai_ocr_validator() -> AiValidator | None:
    """Build the production GPT-4o OCR validator on first call; cache
    the result. Returns None when `OPENAI_API_KEY` isn't set — the
    Stage-3 AI track then degrades to the neutral 0.5 stub
    (canon-honest no-signal)."""
    global _OPENAI_OCR_VALIDATOR_CACHE, _OPENAI_OCR_VALIDATOR_RESOLVED
    if _OPENAI_OCR_VALIDATOR_RESOLVED:
        return _OPENAI_OCR_VALIDATOR_CACHE
    try:
        _OPENAI_OCR_VALIDATOR_CACHE = make_openai_ocr_validator()
    except Stage3AiValidatorUnconfigured:
        _OPENAI_OCR_VALIDATOR_CACHE = None
    _OPENAI_OCR_VALIDATOR_RESOLVED = True
    return _OPENAI_OCR_VALIDATOR_CACHE


def _resolve_gemini_ocr_validator() -> AiValidator | None:
    """Build the production Gemini 2.5 Pro OCR validator on first call;
    cache the result."""
    global _GEMINI_OCR_VALIDATOR_CACHE, _GEMINI_OCR_VALIDATOR_RESOLVED
    if _GEMINI_OCR_VALIDATOR_RESOLVED:
        return _GEMINI_OCR_VALIDATOR_CACHE
    try:
        _GEMINI_OCR_VALIDATOR_CACHE = make_gemini_ocr_validator()
    except Stage3AiValidatorUnconfigured:
        _GEMINI_OCR_VALIDATOR_CACHE = None
    _GEMINI_OCR_VALIDATOR_RESOLVED = True
    return _GEMINI_OCR_VALIDATOR_CACHE


async def _run_primary_engine_only(
    *,
    image_bytes: bytes,
    mime_type: str,
    gemini_fn: GeminiExtractorFn,
) -> ConsensusResult:
    """Single-engine fallback path for page-wide OCR.

    The canonical default remains multi-engine OCR plus Stage-3
    validation. This helper is only used when those paths are explicitly
    disabled via env flags for debugging or emergency fallback.
    """
    text = await gemini_fn(image_bytes, mime_type)
    from waraq.ocr.consensus import AGREEMENT_SINGLE_ENGINE, EngineResult

    return ConsensusResult(
        primary_text=text,
        primary_engine_used=OcrEngine.GEMINI,
        engines=(
            EngineResult(
                engine=OcrEngine.GEMINI,
                text=text,
                confidence=None,
            ),
        ),
        agreement=AGREEMENT_SINGLE_ENGINE,
        aggregated_confidence=None,
    )


class PageOcrError(RuntimeError):
    """Raised when the page-level OCR helper cannot complete: missing
    SCAN-PO, missing source file, poppler not installed, or
    rasterization failed. The OCR-service exceptions
    (`GeminiApiError`, `MissingGeminiApiKey`, etc.) bubble up
    untouched."""


@dataclass(frozen=True, kw_only=True, slots=True)
class BlockOcrResult:
    """Per-block result of a multi-block OCR pass. The §3.4 Stage-2
    routing layer produces one of these per detected block on the page."""

    block_uuid: _uuid.UUID
    segment_uuid: _uuid.UUID
    block_class: BlockClass
    text: str
    text_chars: int
    text_changed: bool
    rev_uuid: _uuid.UUID | None
    engines_used: tuple[str, ...]
    engine_agreement: str
    stage3_confidence: float | None = None
    stage3_divergence_penalty_applied: bool = False


@dataclass(frozen=True, kw_only=True, slots=True)
class PageOcrResult:
    """Per-page OCR result. The pre-sub-batch-C surface (text /
    text_chars / text_changed / segment_uuid / block_uuid / rev_uuid)
    refers to the **primary block** — the first MAIN_TEXT block on the
    page when one exists, else the first detected block in reading
    order. `additional_blocks` carries the rest in detection order so
    callers can opt in to multi-block awareness without breaking the
    existing single-block contract."""

    page_uuid: _uuid.UUID
    text: str
    text_chars: int
    text_changed: bool
    segment_uuid: _uuid.UUID
    block_uuid: _uuid.UUID
    rev_uuid: _uuid.UUID | None
    additional_blocks: tuple[BlockOcrResult, ...] = field(default_factory=tuple)


async def _resolve_source_file(*, session: AsyncSession, page: Page) -> tuple[Path, UploadFormat]:
    """Find the SCAN-PO for this page and pull `(source_file_path, format)`
    out of its payload. The format determines how the page is
    rasterized at OCR time (PDF → pdftoppm; image → direct read /
    TIFF-frame extraction).

    Defaults to `UploadFormat.PDF` when the format field is missing
    (legacy SCAN-POs written before Phase 5 K-1). All v1.0 uploads
    persist the format on finalize.
    """
    result = await session.execute(
        select(ProvenanceObject)
        .where(ProvenanceObject.po_type == POType.SCAN.value)
        .where(ProvenanceObject.scope_type == ScopeType.PAGE.value)
        .where(ProvenanceObject.scope_uuid == page.page_uuid)
        .order_by(ProvenanceObject.created_at.desc())
        .limit(1)
    )
    scan_po: ProvenanceObject | None = result.scalar_one_or_none()
    if scan_po is None:
        raise PageOcrError("No SCAN-PO for page (was the upload finalized?)")
    payload: dict[str, Any] = scan_po.payload or {}
    src = payload.get("source_file_path")
    if not isinstance(src, str):
        raise PageOcrError("SCAN-PO payload missing source_file_path")
    path = Path(src)
    if not path.is_file():
        raise PageOcrError(f"Source file not found on disk: {path}")

    fmt_str = payload.get("format")
    if isinstance(fmt_str, str):
        try:
            fmt = UploadFormat(fmt_str)
        except ValueError:
            # Unknown format string on legacy PO — fall through to PDF.
            fmt = UploadFormat.PDF
    else:
        fmt = UploadFormat.PDF
    return path, fmt


def _render_page_png(source_pdf: Path, page_index: int, out_dir: Path, dpi: int = 200) -> Path:
    """Render the given page (1-indexed) of `source_pdf` to PNG.
    Returns the rendered file path. Raises `PageOcrError` if pdftoppm
    is missing or the render fails."""
    if shutil.which("pdftoppm") is None:
        raise PageOcrError(
            "poppler `pdftoppm` not found on PATH; install poppler-utils to enable OCR."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / "page"
    proc = subprocess.run(
        [
            "pdftoppm",
            "-png",
            "-r",
            str(dpi),
            "-f",
            str(page_index),
            "-l",
            str(page_index),
            str(source_pdf),
            str(prefix),
        ],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise PageOcrError(
            f"pdftoppm failed (rc={proc.returncode}): "
            f"{proc.stderr.decode('utf-8', errors='replace')[:300]}"
        )
    candidates = sorted(out_dir.glob("page-*.png"))
    if not candidates:
        raise PageOcrError("pdftoppm produced no PNG output")
    return candidates[0]


def _read_image_page_bytes(source: Path, fmt: UploadFormat, page_index: int) -> bytes:
    """Return the bytes of one logical page from an image upload.

    Non-TIFF images: `page_index` must be 1 (every other image format
    is single-page in v1.0); the file is read and re-encoded to PNG
    via PIL so downstream OCR sees a uniform PNG byte stream.

    TIFF: seeks to frame `page_index - 1` (0-indexed) and re-encodes
    that frame to PNG. Multi-page TIFFs (common in scanned books)
    arrive as one Page row per frame at finalize time.

    HEIC: relies on the `pillow_heif` opener registered by
    `waraq.upload`. If the opener didn't register (package missing),
    PIL raises `UnidentifiedImageError` — caller surfaces as
    `PageOcrError`.

    Re-encoding to PNG matches the existing pdftoppm output contract —
    callers downstream (`preprocess_if_needed`, `consensus.run_engines`,
    OpenAI OCR, Gemini) all expect PNG bytes. This keeps the
    multi-format path invisible to everything below the rasterizer.
    """
    from io import BytesIO

    from PIL import Image

    try:
        img = Image.open(source)
    except Exception as exc:
        raise PageOcrError(f"Could not open image source {source}: {exc!r}") from exc

    try:
        if fmt == UploadFormat.TIFF:
            n_frames = int(getattr(img, "n_frames", 1))
            if page_index < 1 or page_index > n_frames:
                raise PageOcrError(f"TIFF page_index {page_index} out of range (1..{n_frames})")
            img.seek(page_index - 1)
        else:
            if page_index != 1:
                raise PageOcrError(
                    f"Single-image format {fmt.value} expected page_index=1, got {page_index}"
                )

        # Convert palette / mode-1 / RGBA to RGB so PNG encoding is
        # uniform downstream. The OCR engines all accept 3-channel PNG.
        frame: Image.Image = img.convert("RGB") if img.mode not in ("RGB", "L") else img
        buf = BytesIO()
        frame.save(buf, format="PNG")
        return buf.getvalue()
    finally:
        img.close()


def _render_djvu_page_png(source_djvu: Path, page_index: int, out_dir: Path, dpi: int) -> Path:
    """Render the given page (1-indexed) of `source_djvu` to PNG via
    `ddjvu`. Mirrors `_render_page_png` for PDFs. Requires the
    `djvulibre-bin` package (`ddjvu` on PATH); raises `PageOcrError`
    when missing or render fails."""
    if shutil.which("ddjvu") is None:
        raise PageOcrError(
            "ddjvu not found on PATH; install `djvulibre-bin` (apt) to enable DjVu OCR."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / "page.png"
    proc = subprocess.run(
        [
            "ddjvu",
            "-format=ppm",
            f"-page={page_index}",
            f"-scale={dpi}",
            str(source_djvu),
            str(png_path),
        ],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise PageOcrError(
            f"ddjvu failed (rc={proc.returncode}): "
            f"{proc.stderr.decode('utf-8', errors='replace')[:300]}"
        )
    # ddjvu emits PPM by default. Convert via PIL to PNG so the OCR
    # downstream sees a uniform byte stream (matches the pdftoppm path).
    try:
        from PIL import Image

        with Image.open(png_path) as img:
            buf = png_path.with_suffix(".real.png")
            img.save(buf, format="PNG")
            return buf
    except Exception as exc:
        raise PageOcrError(f"PIL could not re-encode ddjvu output: {exc!r}") from exc


def _rasterize_page(source: Path, fmt: UploadFormat, page_index: int, dpi: int) -> bytes:
    """Format-aware rasterizer. Returns PNG bytes for the given page.

    PDF → pdftoppm at `dpi` (the historical OCR render path).
    DjVu → ddjvu (K-3 "special path"; same shape as PDF — pageful raster).
    Image → PIL re-encode (TIFF picks the right frame).
    Direct-text formats (DOCX/ODT/TXT/XML/HTML/EPUB/MOBI/AZW/AZW3) →
    refuse: their Segments were materialized at upload time and OCR
    is meaningless here.

    The return shape (PNG bytes) matches what pdftoppm produces, so
    the pre-Phase-5 OCR pipeline below this point is unchanged.
    """
    if fmt == UploadFormat.PDF:
        with tempfile.TemporaryDirectory(prefix="waraq-ocr-") as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            png_path = _render_page_png(source, page_index, tmpdir, dpi=dpi)
            return png_path.read_bytes()
    if fmt == UploadFormat.DJVU:
        with tempfile.TemporaryDirectory(prefix="waraq-ocr-") as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            png_path = _render_djvu_page_png(source, page_index, tmpdir, dpi)
            return png_path.read_bytes()
    if is_image_format(fmt):
        return _read_image_page_bytes(source, fmt, page_index)
    if is_direct_text_format(fmt):
        raise PageOcrError(
            f"OCR is not applicable to direct-text format {fmt.value!r} — "
            "text was extracted at upload time. Open the page directly."
        )
    raise PageOcrError(f"Unsupported source format for OCR: {fmt.value}")


def _is_sentinel_bbox(bbox: BoundingBox) -> bool:
    """The default detector emits `(0, 0, 0, 0)` because it doesn't
    decode image dimensions. A real adapter returns a non-degenerate
    box. We crop only when the box is non-degenerate."""
    return bbox.x1 <= bbox.x0 or bbox.y1 <= bbox.y0


def _crop_block_bytes(image_bytes: bytes, bbox: BoundingBox) -> bytes:
    """Crop `image_bytes` to `bbox`. Falls back to the original bytes
    when PIL is missing or the crop fails — better to send the whole
    page to OCR than to fail the run."""
    if _is_sentinel_bbox(bbox):
        return image_bytes
    try:
        from PIL import Image
    except ImportError:
        return image_bytes
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            cropped = img.crop((bbox.x0, bbox.y0, bbox.x1, bbox.y1))
            buf = BytesIO()
            cropped.save(buf, format="PNG")
            return buf.getvalue()
    except Exception:
        return image_bytes


async def _ensure_blocks_and_segments(
    *,
    session: AsyncSession,
    page: Page,
    detected_blocks: list[DetectedBlock],
) -> list[tuple[Block, Segment, DetectedBlock]]:
    """Materialize one `(Block, Segment)` row per `DetectedBlock` in
    reading order. Idempotent: a re-run with the same detector returns
    the existing rows in the same order, no new rows created.

    First-detector-wins: if a row already exists at a given
    `block_index`, its layout fields are NOT overwritten. Re-running
    OCR after an explicit reset is the canonical path to update
    layout metadata.

    Concurrency: takes a row-level lock on the Page row so two
    concurrent OCR runs on the same page serialize. DB-side, the
    UNIQUE partial index on `(page_uuid, block_index) WHERE active`
    (migration 0023) is the second line of defense.

    Block/Segment creation order: each detected block becomes one
    `(Block, Segment)` pair with `block_index = i` (detection order)
    and `satz_index = 0` (one segment per block at this stage; sub-
    batch D's three-track consensus may later split segments within
    a block).
    """
    # Row-lock the Page so concurrent OCR runs serialize.
    await session.execute(select(Page).where(Page.page_uuid == page.page_uuid).with_for_update())

    existing_q = await session.execute(
        select(Block)
        .where(Block.page_uuid == page.page_uuid)
        .where(Block.active.is_(True))
        .order_by(Block.block_index.asc())
    )
    existing_blocks: list[Block] = list(existing_q.scalars())
    existing_by_index: dict[int, Block] = {b.block_index: b for b in existing_blocks}

    paired: list[tuple[Block, Segment, DetectedBlock]] = []
    for i, detected in enumerate(detected_blocks):
        block = existing_by_index.get(i)
        if block is None:
            block = Block(
                block_uuid=new_uuid(),
                page_uuid=page.page_uuid,
                block_type=detected.block_class.value,
                block_index=i,
                reading_direction=detected.reading_direction,
                text_density=detected.text_density,
                baseline_y=detected.baseline_y,
            )
            session.add(block)
            await session.flush()

        seg_q = await session.execute(
            select(Segment)
            .where(Segment.block_uuid == block.block_uuid)
            .where(Segment.active.is_(True))
            .order_by(Segment.satz_index.asc())
        )
        segment: Segment | None = seg_q.scalars().first()
        if segment is None:
            segment = Segment(
                satz_uuid=new_uuid(),
                block_uuid=block.block_uuid,
                satz_index=0,
                lock_flag=LockFlag.NONE,
                text_content="",
            )
            session.add(segment)
            await session.flush()
        paired.append((block, segment, detected))
    return paired


async def _ensure_block_and_segment(
    *,
    session: AsyncSession,
    page: Page,
    detected: DetectedBlock | None = None,
) -> tuple[Block, Segment]:
    """Single-block convenience wrapper — preserved for callers that
    used the pre-sub-batch-C single-block API.

    Internally delegates to `_ensure_blocks_and_segments`. When
    `detected` is None, the legacy `main_text` + RTL fallback is used
    so callers without a detector still see the historical behaviour.
    """
    if detected is None:
        # Legacy path: emit a default `main_text` block. Mirrors the
        # pre-sub-batch-B fallback exactly.
        from waraq.schemas.enums import BlockClass as _BlockClass
        from waraq.schemas.enums import ReadingDirection as _ReadingDirection

        detected = DetectedBlock(
            block_class=_BlockClass.MAIN_TEXT,
            reading_direction=_ReadingDirection.RTL,
            bbox=BoundingBox(x0=0, y0=0, x1=0, y1=0),
        )
    paired = await _ensure_blocks_and_segments(
        session=session, page=page, detected_blocks=[detected]
    )
    block, segment, _ = paired[0]
    return block, segment


def _select_primary_index(detected_blocks: list[DetectedBlock]) -> int:
    """Pick the primary block index: first MAIN_TEXT in reading order;
    otherwise index 0 (defensive — `detect_blocks` guarantees the list
    is non-empty)."""
    for i, db in enumerate(detected_blocks):
        if db.block_class == BlockClass.MAIN_TEXT:
            return i
    return 0


def _full_page_detected_block(image_bytes: bytes) -> list[DetectedBlock]:
    """Treat the complete page as one OCR/translation unit.

    This preserves page context and avoids pathological internal block
    splitting on difficult pages. The legacy segmented layout path
    remains available behind `OCR_PAGE_WIDE_MODE=0`.
    """
    width = 0
    height = 0
    try:
        from PIL import Image

        with Image.open(BytesIO(image_bytes)) as img:
            width, height = img.size
    except Exception:
        width = 0
        height = 0

    return [
        DetectedBlock(
            block_class=BlockClass.MAIN_TEXT,
            reading_direction=ReadingDirection.RTL,
            bbox=BoundingBox(x0=0, y0=0, x1=width, y1=height),
            detector_metadata={
                "detector": "page_wide_mode",
                "page_wide_mode": "true",
            },
        )
    ]


async def run_ocr_for_page(
    *,
    session: AsyncSession,
    page: Page,
    gemini_fn: GeminiExtractorFn | None = None,
    openai_ocr_fn: OpenAiOcrExtractorFn | None = None,
    run_stage3: bool = True,
    morphology_fn: MorphologyAnalyzableFn | None = None,
    diacritizer_fn: DiacritizerFn | None = None,
    openai_validator: AiValidator | None = None,
    gemini_validator: AiValidator | None = None,
) -> PageOcrResult:
    """Drive the full per-page OCR sequence end-to-end.

    Renders the page out of its SCAN-PO source PDF, runs the
    Stage-1 layout detector to get one or more `DetectedBlock`s,
    materializes a Block + Segment per detected block, then for
    each block runs Stage-2 routed OCR via `consensus.run_engines`.

    Pure write of Revision + OCR-PO via PROVENANCE-Kern; no Decision
    Events. The page's `ocr_status` is left untouched so the caller
    can drive the review state machine separately.

    Engine callables can be injected for testing; production defaults
    use `gemini.extract_text` + `openai_ocr.extract_with_confidence`.
    """
    source_file, source_fmt = await _resolve_source_file(session=session, page=page)

    def _do_render() -> bytes:
        return _rasterize_page(source_file, source_fmt, page.page_index, _RENDER_DPI)

    image_bytes = await asyncio.to_thread(_do_render)

    # §3.3 — OpenCV INTER_CUBIC upsample + denoise on low-DPI scans
    # (sub-batch H production preprocessor; falls back to identity
    # when cv2 isn't importable).
    image_bytes, was_preprocessed = preprocess_if_needed(
        image_bytes, _RENDER_DPI, preprocessor=opencv_preprocessor
    )

    # Current product direction: OCR the whole page as one unit by
    # default. The older segmented layout path is kept only as an
    # escape hatch while the rest of the stack finishes migrating away
    # from internal OCR fragmentation.
    if _PAGE_WIDE_OCR_MODE:
        detected_blocks = _full_page_detected_block(image_bytes)
    else:
        detected_blocks = detect_blocks(image_bytes, _RENDER_DPI, detector=opencv_block_detector)
    paired = await _ensure_blocks_and_segments(
        session=session, page=page, detected_blocks=detected_blocks
    )
    primary_idx = _select_primary_index(detected_blocks)

    gemini = gemini_fn if gemini_fn is not None else gemini_extract
    openai_ocr = openai_ocr_fn if openai_ocr_fn is not None else openai_ocr_extract

    # Sub-batch J — wire the production OCR-side AI validators as
    # defaults when callers don't inject stubs. Each resolver returns
    # None when the API key isn't set; `aggregate_stage3` then falls
    # through to the neutral 0.5 stub via `run_ai_consensus`'s default.
    if openai_validator is None:
        openai_validator = _resolve_openai_ocr_validator()
    if gemini_validator is None:
        gemini_validator = _resolve_gemini_ocr_validator()

    block_results: list[BlockOcrResult] = []

    run_expensive_pagewide_consensus = (not _PAGE_WIDE_OCR_MODE) or _PAGE_WIDE_MULTI_ENGINE_MODE
    run_stage3_for_page = run_stage3 and ((not _PAGE_WIDE_OCR_MODE) or _PAGE_WIDE_STAGE3_MODE)

    if _PAGE_WIDE_OCR_MODE:
        if run_expensive_pagewide_consensus:
            page_consensus = await run_engines(
                image_bytes=image_bytes,
                mime_type="image/png",
                block_class=BlockClass.MAIN_TEXT,
                gemini_fn=gemini,
                openai_ocr_fn=openai_ocr,
            )
        else:
            page_consensus = await _run_primary_engine_only(
                image_bytes=image_bytes,
                mime_type="image/png",
                gemini_fn=gemini,
            )
        consensus_text = page_consensus.primary_text

        async def _stub_extractor(_image: bytes, _mime: str, _t: str = consensus_text) -> str:
            return _t

        page_stage3: Stage3Result | None = None
        page_confidence_for_po: float | None = page_consensus.aggregated_confidence
        page_stage3_payload: dict[str, Any] | None = None
        if run_stage3_for_page:
            page_stage3 = await aggregate_stage3(
                session=session,
                candidate_text=consensus_text,
                block_class=BlockClass.MAIN_TEXT,
                stage2=page_consensus,
                morphology_fn=morphology_fn,
                diacritizer_fn=diacritizer_fn,
                openai_validator=openai_validator,
                gemini_validator=gemini_validator,
            )
            page_confidence_for_po = page_stage3.confidence
            page_stage3_payload = {
                "confidence": page_stage3.confidence,
                "stage2_score": page_stage3.stage2_score,
                "divergence_penalty_applied": page_stage3.divergence_penalty_applied,
                "rules": {
                    "score": page_stage3.rule_result.score,
                    "morphology_score": page_stage3.rule_result.morphology_score,
                    "morphology_available": page_stage3.rule_result.morphology_available,
                    "diacritization_score": page_stage3.rule_result.diacritization_score,
                    "diacritization_available": page_stage3.rule_result.diacritization_available,
                    "word_count": page_stage3.rule_result.word_count,
                },
                "statistical": {
                    "score": page_stage3.statistical_result.score,
                    "hit_count": page_stage3.statistical_result.hit_count,
                    "scoped_to_kutub_as_sitta": (
                        page_stage3.statistical_result.scoped_to_kutub_as_sitta
                    ),
                    "sample_titles": list(page_stage3.statistical_result.sample_titles),
                },
                "ai": {
                    "score": page_stage3.ai_result.score,
                    "agreement": page_stage3.ai_result.agreement,
                    "verdicts": [
                        {
                            "engine": v.engine,
                            "confidence": v.confidence,
                            "correction_note": v.correction_note,
                            "error_class": v.error_class,
                        }
                        for v in page_stage3.ai_result.verdicts
                    ],
                },
            }

        block, segment, detected = paired[0]
        job = await start_ocr_job(session=session, page=page)
        text = await run_ocr_job(
            session=session,
            ocr_job=job,
            image_bytes=image_bytes,
            mime_type="image/png",
            extractor=_stub_extractor,
            target_segment=segment,
            confidence_score=page_confidence_for_po,
            was_preprocessed=was_preprocessed,
            source_dpi=_RENDER_DPI,
            engine_breakdown=list(page_consensus.engines),
            engine_agreement=page_consensus.agreement,
            stage3_payload=page_stage3_payload,
        )
        job_result = job.result or {}
        rev_uuid_str = job_result.get("rev_uuid")
        primary = BlockOcrResult(
            block_uuid=block.block_uuid,
            segment_uuid=segment.satz_uuid,
            block_class=detected.block_class,
            text=text,
            text_chars=int(job_result.get("text_chars", len(text))),
            text_changed=bool(job_result.get("text_changed", False)),
            rev_uuid=_uuid.UUID(rev_uuid_str) if rev_uuid_str else None,
            engines_used=tuple(r.engine.value for r in page_consensus.engines),
            engine_agreement=page_consensus.agreement,
            stage3_confidence=page_stage3.confidence if page_stage3 is not None else None,
            stage3_divergence_penalty_applied=(
                page_stage3.divergence_penalty_applied if page_stage3 is not None else False
            ),
        )
        return PageOcrResult(
            page_uuid=page.page_uuid,
            text=primary.text,
            text_chars=primary.text_chars,
            text_changed=primary.text_changed,
            segment_uuid=primary.segment_uuid,
            block_uuid=primary.block_uuid,
            rev_uuid=primary.rev_uuid,
            additional_blocks=(),
        )

    for block, segment, detected in paired:
        block_image = _crop_block_bytes(image_bytes, detected.bbox)

        # Page-wide OCR defaults to the primary engine only for speed.
        # The older multi-engine route remains available behind an env
        # flag when deeper OCR diagnostics are worth the extra latency.
        if run_expensive_pagewide_consensus:
            consensus = await run_engines(
                image_bytes=block_image,
                mime_type="image/png",
                block_class=detected.block_class,
                gemini_fn=gemini,
                openai_ocr_fn=openai_ocr,
            )
        else:
            consensus = await _run_primary_engine_only(
                image_bytes=block_image,
                mime_type="image/png",
                gemini_fn=gemini,
            )

        # The pre-extracted text becomes the input to `run_ocr_job`'s
        # canonical Job lifecycle. We pass it through a stub extractor
        # so the existing extract-phase Job state transitions still
        # fire (PENDING → RUNNING → COMPLETED), but no engine call
        # happens twice.
        consensus_text = consensus.primary_text

        async def _stub_extractor(_image: bytes, _mime: str, _t: str = consensus_text) -> str:
            return _t

        # §3.4 Stage-3 — three-track consensus (sub-batch D). When
        # enabled, runs rule-based + statistical + AI tracks over the
        # Stage-2 primary text and aggregates into a final confidence.
        # The Stage-3 confidence overrides the sub-batch C
        # `aggregated_confidence` because it incorporates Stage-2's
        # signal alongside three additional canonical tracks.
        stage3: Stage3Result | None = None
        confidence_for_po: float | None = consensus.aggregated_confidence
        stage3_payload: dict[str, Any] | None = None
        if run_stage3_for_page:
            stage3 = await aggregate_stage3(
                session=session,
                candidate_text=consensus_text,
                block_class=detected.block_class,
                stage2=consensus,
                morphology_fn=morphology_fn,
                diacritizer_fn=diacritizer_fn,
                openai_validator=openai_validator,
                gemini_validator=gemini_validator,
            )
            confidence_for_po = stage3.confidence
            stage3_payload = {
                "confidence": stage3.confidence,
                "stage2_score": stage3.stage2_score,
                "divergence_penalty_applied": stage3.divergence_penalty_applied,
                "rules": {
                    "score": stage3.rule_result.score,
                    "morphology_score": stage3.rule_result.morphology_score,
                    "morphology_available": stage3.rule_result.morphology_available,
                    "diacritization_score": stage3.rule_result.diacritization_score,
                    "diacritization_available": stage3.rule_result.diacritization_available,
                    "word_count": stage3.rule_result.word_count,
                },
                "statistical": {
                    "score": stage3.statistical_result.score,
                    "hit_count": stage3.statistical_result.hit_count,
                    "scoped_to_kutub_as_sitta": stage3.statistical_result.scoped_to_kutub_as_sitta,
                    "sample_titles": list(stage3.statistical_result.sample_titles),
                },
                "ai": {
                    "score": stage3.ai_result.score,
                    "agreement": stage3.ai_result.agreement,
                    "verdicts": [
                        {
                            "engine": v.engine,
                            "confidence": v.confidence,
                            "correction_note": v.correction_note,
                            "error_class": v.error_class,
                        }
                        for v in stage3.ai_result.verdicts
                    ],
                },
            }

        job = await start_ocr_job(session=session, page=page)
        text = await run_ocr_job(
            session=session,
            ocr_job=job,
            image_bytes=block_image,
            mime_type="image/png",
            extractor=_stub_extractor,
            target_segment=segment,
            confidence_score=confidence_for_po,
            was_preprocessed=was_preprocessed,
            source_dpi=_RENDER_DPI,
            engine_breakdown=list(consensus.engines),
            engine_agreement=consensus.agreement,
            stage3_payload=stage3_payload,
        )

        job_result = job.result or {}
        rev_uuid_str = job_result.get("rev_uuid")
        block_results.append(
            BlockOcrResult(
                block_uuid=block.block_uuid,
                segment_uuid=segment.satz_uuid,
                block_class=detected.block_class,
                text=text,
                text_chars=int(job_result.get("text_chars", len(text))),
                text_changed=bool(job_result.get("text_changed", False)),
                rev_uuid=_uuid.UUID(rev_uuid_str) if rev_uuid_str else None,
                engines_used=tuple(r.engine.value for r in consensus.engines),
                engine_agreement=consensus.agreement,
                stage3_confidence=stage3.confidence if stage3 is not None else None,
                stage3_divergence_penalty_applied=(
                    stage3.divergence_penalty_applied if stage3 is not None else False
                ),
            )
        )

    primary = block_results[primary_idx]
    additional = tuple(r for i, r in enumerate(block_results) if i != primary_idx)

    return PageOcrResult(
        page_uuid=page.page_uuid,
        text=primary.text,
        text_chars=primary.text_chars,
        text_changed=primary.text_changed,
        segment_uuid=primary.segment_uuid,
        block_uuid=primary.block_uuid,
        rev_uuid=primary.rev_uuid,
        additional_blocks=additional,
    )


__all__ = [
    "BlockOcrResult",
    "PageOcrError",
    "PageOcrResult",
    "run_ocr_for_page",
]
