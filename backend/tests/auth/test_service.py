"""Sprint -0.5 — register / authenticate / get_account_by_uuid tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.auth import (
    AccountInactive,
    EmailAlreadyRegistered,
    InvalidCredentials,
    authenticate,
    get_account_by_uuid,
    register_account,
)
from waraq.identity import new_uuid
from waraq.schemas import Account
from waraq.schemas.enums import ApprovalStatus


async def _force_approve(session: AsyncSession, account: Account) -> None:
    """Test helper: bump an account from the M default `pending` to
    `approved` so the legacy auth-service happy-path tests still pass.
    The admission-gate behavior gets its own coverage in `test_admission.py`."""
    account.approval_status = ApprovalStatus.APPROVED
    await session.flush()


@pytest.mark.asyncio
class TestRegisterAccount:
    async def test_creates_account_with_normalized_email(self, db_session: AsyncSession) -> None:
        account = await register_account(
            session=db_session,
            email="  Filu1@GMX.CH  ",
            password="hunter2",
            display_name="Test User",
        )
        assert account.email == "filu1@gmx.ch"
        assert account.display_name == "Test User"
        # Hash is stored, not plaintext.
        assert account.password_hash != "hunter2"
        assert len(account.password_hash) == 60
        assert account.active is True

    async def test_duplicate_email_raises(self, db_session: AsyncSession) -> None:
        await register_account(session=db_session, email="dup@example.com", password="x")
        with pytest.raises(EmailAlreadyRegistered) as exc:
            await register_account(session=db_session, email="DUP@example.com", password="x")
        assert exc.value.email == "dup@example.com"


@pytest.mark.asyncio
class TestAuthenticate:
    async def test_correct_credentials_returns_account(self, db_session: AsyncSession) -> None:
        registered = await register_account(
            session=db_session, email="me@x.com", password="hunter2"
        )
        # Phase 5 M admission gate: register defaults to `pending`;
        # this happy-path test pre-approves the account so login succeeds.
        await _force_approve(db_session, registered)

        loaded = await authenticate(session=db_session, email="me@x.com", password="hunter2")
        assert loaded.account_uuid == registered.account_uuid

    async def test_wrong_password_raises_invalid_credentials(
        self, db_session: AsyncSession
    ) -> None:
        await register_account(session=db_session, email="me@x.com", password="real")
        with pytest.raises(InvalidCredentials):
            await authenticate(session=db_session, email="me@x.com", password="wrong")

    async def test_unknown_email_raises_invalid_credentials(self, db_session: AsyncSession) -> None:
        # Same exception class as wrong-password — no user enumeration.
        with pytest.raises(InvalidCredentials):
            await authenticate(session=db_session, email="ghost@nowhere.invalid", password="x")

    async def test_inactive_account_raises_account_inactive(self, db_session: AsyncSession) -> None:
        account = await register_account(session=db_session, email="off@x.com", password="hunter2")
        await _force_approve(db_session, account)
        # Deactivate via the canonical IDENTITY service.
        from waraq.identity.service import mark_inactive

        mark_inactive(account)
        await db_session.flush()

        with pytest.raises(AccountInactive) as exc:
            await authenticate(session=db_session, email="off@x.com", password="hunter2")
        assert exc.value.account_uuid == account.account_uuid

    async def test_email_lookup_is_case_insensitive(self, db_session: AsyncSession) -> None:
        registered = await register_account(
            session=db_session, email="MixedCase@Example.COM", password="x"
        )
        await _force_approve(db_session, registered)
        loaded = await authenticate(session=db_session, email="mixedcase@example.com", password="x")
        assert loaded.email == "mixedcase@example.com"


@pytest.mark.asyncio
class TestGetAccountByUuid:
    async def test_returns_none_for_unknown_uuid(self, db_session: AsyncSession) -> None:
        loaded = await get_account_by_uuid(session=db_session, account_uuid=new_uuid())
        assert loaded is None

    async def test_returns_account_for_known_uuid(self, db_session: AsyncSession) -> None:
        registered = await register_account(session=db_session, email="me@x.com", password="x")
        loaded = await get_account_by_uuid(session=db_session, account_uuid=registered.account_uuid)
        assert loaded is not None
        assert loaded.account_uuid == registered.account_uuid
