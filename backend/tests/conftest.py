from __future__ import annotations

import os
import uuid as _uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
def fresh_segment_id():
    """Convenience: a new segment-uuid for guard tests that need an identifier."""
    from waraq.identity import new_uuid

    return new_uuid()


# Placeholder bcrypt-format hash (60 chars) used by `seed_account_uuid` for
# FK-only test fixtures. Tests that need real authentication call
# register_account through the auth service instead.
_PLACEHOLDER_PASSWORD_HASH = "$2b$12$" + "x" * 53


async def seed_account_uuid(session: AsyncSession, account_uuid: _uuid.UUID) -> None:
    """Seed a placeholder Account row with the given account_uuid.

    Sprint -0.5 added a NOT NULL FK from projects.account_uuid → accounts,
    so any test that creates a Project must first seed the referenced
    Account. This helper centralizes the boilerplate.

    Email is derived from the UUID so it's unique per call. Password hash
    is a placeholder — these accounts are not meant to be authenticated."""
    from waraq.schemas import Account

    session.add(
        Account(
            account_uuid=account_uuid,
            email=f"seed-{account_uuid}@waraq-test.example.com",
            password_hash=_PLACEHOLDER_PASSWORD_HASH,
        )
    )
    await session.flush()


def _test_database_url() -> str:
    """Resolve the URL the integration tests run against.

    Order: explicit env var > backend/.env DATABASE_URL > docker-compose default.
    """
    if url := os.environ.get("WARAQ_TEST_DATABASE_URL"):
        return url
    from waraq.db.session import get_settings

    return get_settings().database_url


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Per-test async session. Operations autobegin a transaction; the fixture
    rolls it back at end-of-test. This works because services in T-1.4.x use
    `session.flush()` (not commit()) and tests never commit explicitly — so
    everything staged inside the test stays in the open transaction and is
    discarded on rollback.

    If a future service or test does need to commit, switch to a connection-
    level outer transaction with `begin_nested()` SAVEPOINTs."""
    engine = create_async_engine(_test_database_url(), future=True)
    sessionmaker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with sessionmaker() as session:
            try:
                yield session
            finally:
                await session.rollback()
    finally:
        await engine.dispose()
