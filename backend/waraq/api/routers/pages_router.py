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
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select

from waraq.api._ownership import owned_page_or_404, owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import PageResponse
from waraq.schemas import Page, ProvenanceObject
from waraq.schemas.enums import POType, ScopeType

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
    page_index_in_source = payload.get("page_index_in_source") or page.page_index
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
        png_bytes = candidates[0].read_bytes()

    import io

    headers = {
        "Cache-Control": "private, max-age=300",
        "X-Waraq-DPI": str(dpi),
    }
    return StreamingResponse(io.BytesIO(png_bytes), media_type="image/png", headers=headers)
