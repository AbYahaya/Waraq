"""Shared seed helpers for audit tests."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.schemas import Block, Page, Project, Segment
from waraq.schemas.enums import OcrStatus


async def seed_project(session: AsyncSession, *, name: str = "audit-test") -> Project:
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)
    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name=name)
    session.add(project)
    await session.flush()
    return project


async def seed_segment(
    session: AsyncSession,
    *,
    project: Project,
    text: str,
    page_index: int = 1,
    block_index: int = 0,
    satz_index: int = 0,
) -> Segment:
    page = Page(
        page_uuid=new_uuid(),
        project_uuid=project.project_uuid,
        page_index=page_index,
        ocr_status=OcrStatus.GO,
    )
    session.add(page)
    await session.flush()
    block = Block(
        block_uuid=new_uuid(),
        page_uuid=page.page_uuid,
        block_type="main_text",
        block_index=block_index,
    )
    session.add(block)
    await session.flush()
    seg = Segment(
        satz_uuid=new_uuid(),
        block_uuid=block.block_uuid,
        satz_index=satz_index,
        lock_flag=LockFlag.NONE,
        text_content=text,
    )
    session.add(seg)
    await session.flush()
    return seg


def st(source: str, target: str) -> str:
    """Encode source + target into a single text_content per the v1.0
    rule-body convention (`source\\n---\\ntarget`). See audit/rules.py
    `_source_target` for the read side."""
    return f"{source}\n---\n{target}"
