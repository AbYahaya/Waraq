"""Shared helpers for M4 router HTTP tests.

The M1 HTTP layer doesn't expose page/segment creation as a CRUD endpoint
(pages are produced by the upload-finalize flow). For unit-testing the
M4 routers we materialize a project + page + block + segment directly via
the DB session bound to the same test DB the API uses.
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.schemas import Block, Page, Segment


@dataclass(frozen=True)
class _M4Fixture:
    project_uuid: _uuid.UUID
    page_uuid: _uuid.UUID
    block_uuid: _uuid.UUID
    satz_uuid: _uuid.UUID


def _test_database_url() -> str:
    from tests.conftest import _test_database_url as parent

    return parent()


async def make_page_block_segment(project_uuid_str: str, *, text: str = "بسم الله") -> _M4Fixture:
    """Insert one page + block + segment under the given project. Commits
    via its own engine so the API session sees them. Returns the UUIDs."""
    engine = create_async_engine(_test_database_url(), future=True)
    sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    project_uuid = _uuid.UUID(project_uuid_str)
    page_uuid = new_uuid()
    block_uuid = new_uuid()
    satz_uuid = new_uuid()
    try:
        async with sm() as session, session.begin():
            session.add(
                Page(
                    page_uuid=page_uuid,
                    project_uuid=project_uuid,
                    page_index=1,
                )
            )
            await session.flush()
            session.add(
                Block(
                    block_uuid=block_uuid,
                    page_uuid=page_uuid,
                    block_type="main_text",
                    block_index=0,
                )
            )
            await session.flush()
            session.add(
                Segment(
                    satz_uuid=satz_uuid,
                    block_uuid=block_uuid,
                    satz_index=0,
                    lock_flag=LockFlag.NONE,
                    text_content=text,
                )
            )
            await session.flush()
    finally:
        await engine.dispose()
    return _M4Fixture(
        project_uuid=project_uuid,
        page_uuid=page_uuid,
        block_uuid=block_uuid,
        satz_uuid=satz_uuid,
    )
