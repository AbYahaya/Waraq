"""High-level wrapper that lets a UI button trigger OCR for a Page.

Bridges three concerns the lower-level OCR service deliberately doesn't:

1. **Rasterization** — the OCR service takes raw image bytes; this
   helper renders the right page out of the stored source PDF (via
   poppler's `pdftoppm`) and supplies them.
2. **Block + Segment provisioning** — `run_ocr_job` writes its Revision
   into a target Segment. After upload the project has Pages but no
   Block / Segment rows yet; this helper creates a default `main_text`
   block + one Segment if absent. Subsequent OCR runs reuse them so
   re-runs don't duplicate identity rows.
3. **Source PDF lookup** — pulled from the page's SCAN-PO payload, the
   same path the in-browser viewer uses.

Read-side discipline: never re-creates a Block/Segment when one is
already present. Pure write of Revision + OCR-PO via the existing
service path; no Decision Events, no LINEAGE_EVENT-POs.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
import uuid as _uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.ocr import run_ocr_job, start_ocr_job
from waraq.schemas import Block, Page, ProvenanceObject, Segment
from waraq.schemas.enums import POType, ScopeType


class PageOcrError(RuntimeError):
    """Raised when the page-level OCR helper cannot complete: missing
    SCAN-PO, missing source file, poppler not installed, or
    rasterization failed. The OCR-service exceptions
    (`GeminiApiError`, `MissingGeminiApiKey`, etc.) bubble up
    untouched."""


@dataclass(frozen=True, kw_only=True, slots=True)
class PageOcrResult:
    page_uuid: _uuid.UUID
    text: str
    text_chars: int
    text_changed: bool
    segment_uuid: _uuid.UUID
    block_uuid: _uuid.UUID
    rev_uuid: _uuid.UUID | None


async def _resolve_source_pdf(*, session: AsyncSession, page: Page) -> Path:
    """Find the SCAN-PO for this page and pull the source PDF path
    out of its payload."""
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
    return path


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


async def _ensure_block_and_segment(*, session: AsyncSession, page: Page) -> tuple[Block, Segment]:
    """If the page has no Block/Segment yet, create a default
    `main_text` block + one empty Segment. Idempotent under serialized
    calls AND concurrent calls in separate transactions.

    Concurrency contract: takes a row-level lock on the Page row via
    `SELECT ... FOR UPDATE`. Two concurrent OCR runs on the same page
    serialize through the lock — the first to acquire it wins the
    creation race; the second blocks, then sees the committed row
    when it acquires the lock and reuses it. The DB-level UNIQUE
    partial indexes on `(page_uuid, block_index) WHERE active` and
    `(block_uuid, satz_index) WHERE active` are the second line of
    defense (migration 0023).

    The `.active.is_(True)` filters scope the idempotency to live
    rows: an inactivated duplicate from before migration 0023 must
    not match here.
    """
    # Row-lock the Page row so concurrent OCR runs serialize.
    await session.execute(select(Page).where(Page.page_uuid == page.page_uuid).with_for_update())

    block_q = await session.execute(
        select(Block)
        .where(Block.page_uuid == page.page_uuid)
        .where(Block.active.is_(True))
        .order_by(Block.block_index.asc())
    )
    block: Block | None = block_q.scalars().first()
    if block is None:
        block = Block(
            block_uuid=new_uuid(),
            page_uuid=page.page_uuid,
            block_type="main_text",
            block_index=0,
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
    return block, segment


async def run_ocr_for_page(*, session: AsyncSession, page: Page) -> PageOcrResult:
    """Drive the full per-page OCR sequence end-to-end.

    Renders the page out of its SCAN-PO source PDF, provisions a
    default Block + Segment if absent, then calls the canonical
    `start_ocr_job` + `run_ocr_job` path. Pure write of Revision +
    OCR-PO via PROVENANCE-Kern; no Decision Events. The page's
    `ocr_status` is left untouched so the caller can drive the
    review state machine separately.
    """
    source_pdf = await _resolve_source_pdf(session=session, page=page)

    # Rasterize in a per-call tempdir; cleaned up regardless of outcome.
    def _do_render() -> bytes:
        with tempfile.TemporaryDirectory(prefix="waraq-ocr-") as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            png_path = _render_page_png(source_pdf, page.page_index, tmpdir)
            return png_path.read_bytes()

    image_bytes = await asyncio.to_thread(_do_render)

    block, segment = await _ensure_block_and_segment(session=session, page=page)

    job = await start_ocr_job(session=session, page=page)
    text = await run_ocr_job(
        session=session,
        ocr_job=job,
        image_bytes=image_bytes,
        mime_type="image/png",
        target_segment=segment,
    )

    job_result = job.result or {}
    rev_uuid_str = job_result.get("rev_uuid")
    return PageOcrResult(
        page_uuid=page.page_uuid,
        text=text,
        text_chars=int(job_result.get("text_chars", len(text))),
        text_changed=bool(job_result.get("text_changed", False)),
        segment_uuid=segment.satz_uuid,
        block_uuid=block.block_uuid,
        rev_uuid=_uuid.UUID(rev_uuid_str) if rev_uuid_str else None,
    )


__all__ = [
    "PageOcrError",
    "PageOcrResult",
    "run_ocr_for_page",
]
