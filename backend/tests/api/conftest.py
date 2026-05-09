"""HTTP integration test fixtures.

Each `auth_client` fixture creates a fresh Account via the real /auth/register
endpoint, returns an authenticated httpx client, and on teardown deletes
everything that account owns (cascade across the eight tables that point at
account_uuid directly or transitively).

Tests use unique emails (`test-<uuid>@waraq-test.example.com`) so parallel runs
don't collide.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from waraq.api import app
from waraq.identity import new_uuid
from waraq.schemas import (
    Account,
    Block,
    Checkpoint,
    Concept,
    ConflictInstance,
    DecisionEvent,
    Entity,
    Job,
    KonsistenzBefund,
    LogEntry,
    Musterkandidat,
    OcrErrorInstance,
    Page,
    Project,
    ProvenanceObject,
    Revision,
    Segment,
    TranslationObservation,
)


def _test_database_url() -> str:
    from tests.conftest import _test_database_url as parent

    return parent()


async def _cleanup_account(account_uuid: Any) -> None:
    """Delete an account and everything that points at it (transitively).

    FK dependency order (children before parents):
      revisions, log_entries, decision_events,
      provenance_objects, checkpoints,
      segments, blocks, pages, jobs, projects, accounts
    """
    engine = create_async_engine(_test_database_url(), future=True)
    sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with sm() as session, session.begin():
            project_uuids = (
                (
                    await session.execute(
                        select(Project.project_uuid).where(Project.account_uuid == account_uuid)
                    )
                )
                .scalars()
                .all()
            )

            page_uuids: list[Any] = []
            block_uuids: list[Any] = []
            segment_uuids: list[Any] = []
            job_uuids: list[Any] = []
            if project_uuids:
                page_uuids = (
                    (
                        await session.execute(
                            select(Page.page_uuid).where(Page.project_uuid.in_(project_uuids))
                        )
                    )
                    .scalars()
                    .all()
                )
                job_uuids = (
                    (
                        await session.execute(
                            select(Job.job_uuid).where(Job.project_uuid.in_(project_uuids))
                        )
                    )
                    .scalars()
                    .all()
                )
            if page_uuids:
                block_uuids = (
                    (
                        await session.execute(
                            select(Block.block_uuid).where(Block.page_uuid.in_(page_uuids))
                        )
                    )
                    .scalars()
                    .all()
                )
            if block_uuids:
                segment_uuids = (
                    (
                        await session.execute(
                            select(Segment.satz_uuid).where(Segment.block_uuid.in_(block_uuids))
                        )
                    )
                    .scalars()
                    .all()
                )

            scope_uuids: list[Any] = []
            scope_uuids.extend(segment_uuids)
            scope_uuids.extend(page_uuids)
            scope_uuids.extend(block_uuids)
            scope_uuids.extend(project_uuids)
            scope_uuids.append(account_uuid)

            if segment_uuids:
                # Break the segments↔revisions FK cycle by nulling
                # current_rev_uuid before deleting revisions.
                from sqlalchemy import update

                await session.execute(
                    update(Segment)
                    .where(Segment.satz_uuid.in_(segment_uuids))
                    .values(current_rev_uuid=None)
                )
                # Child tables that FK to revisions/segments must die first.
                await session.execute(
                    delete(TranslationObservation).where(
                        TranslationObservation.satz_uuid.in_(segment_uuids)
                    )
                )
                await session.execute(
                    delete(ConflictInstance).where(ConflictInstance.satz_uuid.in_(segment_uuids))
                )
                await session.execute(delete(Revision).where(Revision.satz_uuid.in_(segment_uuids)))
            if page_uuids:
                await session.execute(
                    delete(OcrErrorInstance).where(OcrErrorInstance.page_uuid.in_(page_uuids))
                )
            if project_uuids:
                await session.execute(
                    delete(KonsistenzBefund).where(KonsistenzBefund.project_uuid.in_(project_uuids))
                )
                await session.execute(
                    delete(Musterkandidat).where(Musterkandidat.project_uuid.in_(project_uuids))
                )
                await session.execute(
                    delete(Concept).where(Concept.project_uuid.in_(project_uuids))
                )
                await session.execute(delete(Entity).where(Entity.project_uuid.in_(project_uuids)))
            # Account-bound concepts/entities must also be deleted before the account.
            await session.execute(delete(Concept).where(Concept.account_uuid == account_uuid))
            await session.execute(delete(Entity).where(Entity.account_uuid == account_uuid))
            if scope_uuids:
                await session.execute(
                    delete(DecisionEvent).where(DecisionEvent.scope_uuid.in_(scope_uuids))
                )
                await session.execute(
                    delete(ProvenanceObject).where(ProvenanceObject.scope_uuid.in_(scope_uuids))
                )
                await session.execute(delete(LogEntry).where(LogEntry.scope_uuid.in_(scope_uuids)))
            if job_uuids:
                await session.execute(delete(Checkpoint).where(Checkpoint.job_uuid.in_(job_uuids)))
            if segment_uuids:
                await session.execute(delete(Segment).where(Segment.satz_uuid.in_(segment_uuids)))
            if block_uuids:
                await session.execute(delete(Block).where(Block.block_uuid.in_(block_uuids)))
            if page_uuids:
                await session.execute(delete(Page).where(Page.page_uuid.in_(page_uuids)))
            if project_uuids:
                await session.execute(delete(Job).where(Job.project_uuid.in_(project_uuids)))
                await session.execute(
                    delete(Project).where(Project.project_uuid.in_(project_uuids))
                )
            # Author/actor refs to this account get nulled (FK is nullable
            # for revisions/decision_events/provenance_objects).
            from sqlalchemy import update

            await session.execute(
                update(Revision)
                .where(Revision.author_uuid == account_uuid)
                .values(author_uuid=None)
            )
            await session.execute(
                update(DecisionEvent)
                .where(DecisionEvent.actor_uuid == account_uuid)
                .values(actor_uuid=None)
            )
            await session.execute(
                update(ProvenanceObject)
                .where(ProvenanceObject.author_uuid == account_uuid)
                .values(author_uuid=None)
            )
            await session.execute(delete(Account).where(Account.account_uuid == account_uuid))
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def http_client() -> AsyncIterator[httpx.AsyncClient]:
    """Per-test ASGI client. Clears the lru_cached engine + sessionmaker
    around each test so the cached asyncpg connections aren't reused
    across event loops (which throws 'operation in progress')."""
    from waraq.db import session as db_session_module

    db_session_module._engine.cache_clear()
    db_session_module._sessionmaker.cache_clear()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            yield client
        finally:
            # Tear down the per-test engine.
            try:
                engine = db_session_module._engine()
                await engine.dispose()
            finally:
                db_session_module._engine.cache_clear()
                db_session_module._sessionmaker.cache_clear()


@pytest_asyncio.fixture
async def auth_client(
    http_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> AsyncIterator[httpx.AsyncClient]:
    """Register a fresh account, attach the bearer token, clean up after.

    Also redirects uploads_dir to a per-test tmp_path so HTTP-driven uploads
    don't pollute the dev filesystem."""
    from waraq.db import session as db_session_module

    db_session_module.get_settings.cache_clear()
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))

    email = f"test-{new_uuid()}@waraq-test.example.com"
    password = "test-password-12345"

    resp = await http_client.post(
        "/auth/register",
        json={"email": email, "password": password, "display_name": "Test"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]

    # Look up the account_uuid we just created so cleanup can find it.
    engine = create_async_engine(_test_database_url(), future=True)
    sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with sm() as session:
            account = (
                await session.execute(select(Account).where(Account.email == email))
            ).scalar_one()
            account_uuid = account.account_uuid
    finally:
        await engine.dispose()

    http_client.headers["Authorization"] = f"Bearer {token}"
    try:
        yield http_client
    finally:
        await _cleanup_account(account_uuid)
        db_session_module.get_settings.cache_clear()
