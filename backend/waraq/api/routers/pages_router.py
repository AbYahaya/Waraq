"""Page endpoints — list pages of a project, fetch a single page, and
stream the source PDF behind a page for the in-browser viewer.

Two listing/fetching shapes:
- /projects/{project_uuid}/pages              — list pages of a project
- /pages/{page_uuid}                          — fetch a single page (page
  UUIDs are globally unique; ownership verified server-side)
- /pages/{page_uuid}/source-pdf               — stream the source PDF
  the page belongs to. The browser's native PDF viewer renders it; the
  frontend appends `#page=N` to jump to the right page.
"""

from __future__ import annotations

import uuid as _uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from waraq.api._ownership import owned_page_or_404, owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import PageResponse
from waraq.schemas import Page, ProvenanceObject
from waraq.schemas.enums import POType, ScopeType

router = APIRouter(tags=["pages"])


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
        .order_by(Page.page_index.asc())
    )
    return [PageResponse.model_validate(p) for p in result.scalars()]


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
