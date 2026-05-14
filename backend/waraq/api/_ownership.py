"""Shared ownership guards for the HTTP layer.

Each `_owned_*` walks from the requested resource up the FK chain to its
project, and asserts that project belongs to the current account. Returns
the resource on success; raises 404 on miss or cross-account access.

The 404-on-cross-account behaviour is deliberate: a 403 would leak that
the resource exists but isn't yours. We return 404 in both cases.
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.schemas import Block, Page, Project, Segment


def _project_visible(project: Project | None, account_uuid: _uuid.UUID) -> bool:
    """A project is visible to the caller iff it exists, is still active,
    and belongs to the calling account.

    Sub-batch P (2026-05-13) tightened the `active` check across every
    ownership chain so a deleted project (and its children) returns 404
    everywhere — not just on the project list endpoint."""
    return project is not None and project.active and project.account_uuid == account_uuid


async def owned_project_or_404(
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    account_uuid: _uuid.UUID,
) -> Project:
    project: Project | None = await session.get(Project, project_uuid)
    if not _project_visible(project, account_uuid):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    assert project is not None  # narrowed by _project_visible
    return project


async def owned_page_or_404(
    session: AsyncSession,
    page_uuid: _uuid.UUID,
    account_uuid: _uuid.UUID,
) -> Page:
    page: Page | None = await session.get(Page, page_uuid)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    project: Project | None = await session.get(Project, page.project_uuid)
    if not _project_visible(project, account_uuid):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return page


async def owned_block_or_404(
    session: AsyncSession,
    block_uuid: _uuid.UUID,
    account_uuid: _uuid.UUID,
) -> Block:
    block: Block | None = await session.get(Block, block_uuid)
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
    page: Page | None = await session.get(Page, block.page_uuid)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
    project: Project | None = await session.get(Project, page.project_uuid)
    if not _project_visible(project, account_uuid):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
    return block


async def owned_segment_or_404(
    session: AsyncSession,
    satz_uuid: _uuid.UUID,
    account_uuid: _uuid.UUID,
) -> Segment:
    segment: Segment | None = await session.get(Segment, satz_uuid)
    if segment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    block: Block | None = await session.get(Block, segment.block_uuid)
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    page: Page | None = await session.get(Page, block.page_uuid)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    project: Project | None = await session.get(Project, page.project_uuid)
    if not _project_visible(project, account_uuid):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    return segment
