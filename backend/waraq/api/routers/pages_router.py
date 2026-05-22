"""Page endpoints — list pages of a project, fetch a single page, and
stream the source PDF behind a page for the in-browser viewer.

Two listing/fetching shapes:
- /projects/{project_uuid}/pages              — list pages of a project
- /pages/{page_uuid}                          — fetch a single page (page
  UUIDs are globally unique; ownership verified server-side)
- /pages/{page_uuid}/source-pdf               — stream the source PDF
  the page belongs to. The browser's native PDF viewer renders it; the
  frontend appends `#page=N` to jump to the right page.
- /pages/{page_uuid}/render-png?dpi=N         — render the page at the
  requested DPI as PNG (Phase 3 sub-batch D — DPI compare view).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import uuid as _uuid
from io import BytesIO
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from waraq.api._ownership import owned_page_or_404, owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import PageResponse
from waraq.notifications.events import notify_project_event, page_dpi_url
from waraq.schemas import Block, Page, Project, ProvenanceObject, Segment
from waraq.schemas.enums import POType, ScopeType
from waraq.text_state import resolve_segment_source_text

router = APIRouter(tags=["pages"])


def _dedupe_pages_by_index(pages: list[Page]) -> list[Page]:
    """Return one active logical page per page number.

    Older OCR/upload paths can leave more than one active Page row with
    the same `page_index`. The workspace is page-number based, so exposing
    those duplicate rows makes the sidebar and export ranges look doubled.
    The caller orders newest rows first within each page_index.
    """
    seen: set[int] = set()
    logical_pages: list[Page] = []
    for page in pages:
        if page.page_index in seen:
            continue
        seen.add(page.page_index)
        logical_pages.append(page)
    return logical_pages


@router.get("/projects/{project_uuid}/pages", response_model=list[PageResponse])
async def list_pages(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> list[PageResponse]:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    result = await session.execute(
        select(Page)
        .where(Page.project_uuid == project_uuid, Page.active.is_(True))
        .order_by(Page.page_index.asc(), Page.created_at.desc())
    )
    pages = _dedupe_pages_by_index(list(result.scalars()))
    return [PageResponse.model_validate(p) for p in pages]


@router.get("/pages/{page_uuid}", response_model=PageResponse)
async def get_page(
    page_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> PageResponse:
    page = await owned_page_or_404(session, page_uuid, current.account_uuid)
    return PageResponse.model_validate(page)


@router.get("/pages/{page_uuid}/source-pdf")
async def get_page_source_pdf(
    page_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> FileResponse:
    """Stream the source PDF that contains this page.

    Looks up the page's SCAN-PO to read `source_file_path` from its
    payload, then streams the file. Same source PDF is reused for every
    page that landed in the same upload, so the frontend uses
    `#page={page_index_in_source}` to jump to the right one.
    """
    page = await owned_page_or_404(session, page_uuid, current.account_uuid)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No SCAN-PO for page (was the upload finalized?)",
        )
    payload: dict[str, Any] = scan_po.payload or {}
    source_path_str = payload.get("source_file_path")
    if not isinstance(source_path_str, str):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SCAN-PO payload missing source_file_path",
        )
    source_path = Path(source_path_str)
    if not source_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source file not found on disk",
        )
    return FileResponse(
        path=source_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="page-{page.page_index}.pdf"'},
    )


# Phase 3 sub-batch D — DPI comparison view per §2.1.
# `pdftoppm` (poppler-utils) is the same render path the OCR pipeline
# uses, so the rendered PNG matches what the OCR sees at that DPI.
DPI_MIN = 50
DPI_MAX = 600


class NormalizedCropBox(BaseModel):
    """Crop rectangle in normalized image coordinates."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def _inside_image(self) -> NormalizedCropBox:
        if self.x + self.width > 1.000001 or self.y + self.height > 1.000001:
            raise ValueError("crop rectangle must stay inside the image")
        return self


class OcrRetryCandidateRequest(BaseModel):
    dpi: int = Field(default=300, ge=DPI_MIN, le=DPI_MAX)
    scope: Literal["region", "full_page"]
    crop: NormalizedCropBox | None = None
    engine: Literal["openai", "gemini"] = "openai"

    @model_validator(mode="after")
    def _region_requires_crop(self) -> OcrRetryCandidateRequest:
        if self.scope == "region" and self.crop is None:
            raise ValueError("region retry requires a crop rectangle")
        return self


class OcrRetryCandidateResponse(BaseModel):
    candidate_uuid: _uuid.UUID
    page_uuid: _uuid.UUID
    segment_uuid: _uuid.UUID | None
    scope: Literal["region", "full_page"]
    engine: Literal["openai", "gemini"]
    dpi: int
    crop: NormalizedCropBox | None
    text: str
    text_chars: int
    current_text: str | None
    changed: bool
    warning: str | None = None


async def _latest_scan_po_for_page(session: DbSession, page: Page) -> ProvenanceObject:
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No SCAN-PO for page (was the upload finalized?)",
        )
    return scan_po


def _scan_source_path(scan_po: ProvenanceObject) -> Path:
    payload: dict[str, Any] = scan_po.payload or {}
    source_path_str = payload.get("source_file_path")
    if not isinstance(source_path_str, str):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SCAN-PO payload missing source_file_path",
        )
    source_path = Path(source_path_str)
    if not source_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source file not found on disk",
        )
    return source_path


def _page_index_in_source(scan_po: ProvenanceObject, page: Page) -> int:
    payload: dict[str, Any] = scan_po.payload or {}
    page_index_in_source = payload.get("page_index_in_source") or page.page_index
    return int(page_index_in_source)


def _render_png_bytes(source_path: Path, page_index_in_source: int, dpi: int) -> bytes:
    if shutil.which("pdftoppm") is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="poppler-utils (`pdftoppm`) is required for PNG rendering",
        )

    with tempfile.TemporaryDirectory(prefix="waraq-render-") as tmpdir:
        out_dir = Path(tmpdir)
        prefix = out_dir / "page"
        proc = subprocess.run(
            [
                "pdftoppm",
                "-png",
                "-r",
                str(dpi),
                "-f",
                str(page_index_in_source),
                "-l",
                str(page_index_in_source),
                str(source_path),
                str(prefix),
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        if proc.returncode != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"pdftoppm failed: {proc.stderr.decode('utf-8', errors='replace')[:300]}",
            )
        candidates = sorted(out_dir.glob("page-*.png"))
        if not candidates:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="pdftoppm produced no PNG output",
            )
        return candidates[0].read_bytes()


async def _render_page_png_bytes(session: DbSession, page: Page, dpi: int) -> bytes:
    scan_po = await _latest_scan_po_for_page(session, page)
    return _render_png_bytes(
        source_path=_scan_source_path(scan_po),
        page_index_in_source=_page_index_in_source(scan_po, page),
        dpi=dpi,
    )


def _crop_png_bytes(image_bytes: bytes, crop: NormalizedCropBox) -> bytes:
    from PIL import Image

    with Image.open(BytesIO(image_bytes)) as img:
        width, height = img.size
        left = max(0, min(width - 1, round(crop.x * width)))
        top = max(0, min(height - 1, round(crop.y * height)))
        right = max(left + 1, min(width, round((crop.x + crop.width) * width)))
        bottom = max(top + 1, min(height, round((crop.y + crop.height) * height)))
        region = img.crop((left, top, right, bottom))
        out = BytesIO()
        region.save(out, format="PNG")
        return out.getvalue()


async def _first_active_segment_for_page(session: DbSession, page_uuid: _uuid.UUID) -> Segment | None:
    result = await session.execute(
        select(Segment)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .where(Block.page_uuid == page_uuid, Segment.active.is_(True))
        .order_by(Block.block_index.asc(), Segment.satz_index.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _extract_retry_candidate_text(
    image_bytes: bytes,
    engine: Literal["openai", "gemini"],
) -> str:
    try:
        if engine == "gemini":
            from waraq.ocr.gemini import extract_text
        else:
            from waraq.ocr.openai_ocr import extract_text

        return await extract_text(image_bytes, "image/png")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{engine} OCR retry failed: {exc}",
        ) from exc


@router.get("/pages/{page_uuid}/render-png")
async def render_page_png_at_dpi(
    page_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
    dpi: int = Query(default=200, ge=DPI_MIN, le=DPI_MAX),
) -> StreamingResponse:
    """Render the page as PNG at the requested DPI.

    Phase 3 sub-batch D — backs the DPI comparison view. The frontend
    requests two DPIs (low + high) and renders them side-by-side so
    the user can see what the OCR engine sees at low vs high
    fidelity.

    503 if `pdftoppm` (poppler-utils) is not installed on the host.
    """
    page = await owned_page_or_404(session, page_uuid, current.account_uuid)
    png_bytes = await _render_page_png_bytes(session, page, dpi)

    import io

    headers = {
        "Cache-Control": "private, max-age=300",
        "X-Waraq-DPI": str(dpi),
    }
    return StreamingResponse(io.BytesIO(png_bytes), media_type="image/png", headers=headers)


@router.post("/pages/{page_uuid}/ocr-retry-candidate", response_model=OcrRetryCandidateResponse)
async def create_ocr_retry_candidate(
    page_uuid: _uuid.UUID,
    req: OcrRetryCandidateRequest,
    session: DbSession,
    current: CurrentAccount,
) -> OcrRetryCandidateResponse:
    """Run OCR again for a page/crop and return an unsaved candidate.

    This endpoint is intentionally non-destructive: it never replaces the
    current page OCR. The workspace must explicitly accept the returned
    candidate through the existing manual edit endpoint.
    """
    page = await owned_page_or_404(session, page_uuid, current.account_uuid)
    png_bytes = await _render_page_png_bytes(session, page, req.dpi)
    image_for_ocr = _crop_png_bytes(png_bytes, req.crop) if req.crop is not None else png_bytes
    candidate_text = await _extract_retry_candidate_text(image_for_ocr, req.engine)

    segment = await _first_active_segment_for_page(session, page_uuid)
    current_text = (
        await resolve_segment_source_text(session=session, segment=segment)
        if segment is not None
        else None
    )
    warning = None
    if segment is None:
        warning = "No active OCR segment exists yet, so this candidate cannot be accepted directly."
    project: Project | None = await session.get(Project, page.project_uuid)
    if project is not None:
        await notify_project_event(
            session=session,
            project=project,
            kind="ocr_retry_candidate_created",
            severity="info",
            title=f"OCR retry candidate created — page {page.page_index}",
            body=(
                f"{req.engine} generated a {req.scope.replace('_', ' ')} candidate "
                f"at {req.dpi} DPI. It is not saved until accepted."
            ),
            target_url=page_dpi_url(project.project_uuid, page.page_uuid),
            action_label="Open DPI recovery",
            page_uuid=page.page_uuid,
        )

    return OcrRetryCandidateResponse(
        candidate_uuid=_uuid.uuid4(),
        page_uuid=page_uuid,
        segment_uuid=segment.satz_uuid if segment is not None else None,
        scope=req.scope,
        engine=req.engine,
        dpi=req.dpi,
        crop=req.crop,
        text=candidate_text,
        text_chars=len(candidate_text),
        current_text=current_text,
        changed=(current_text or "").strip() != candidate_text.strip(),
        warning=warning,
    )
