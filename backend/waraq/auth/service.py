"""Sprint -0.5 — Account auth service.

Three operations:
- register_account(email, password, display_name=None) → Account
- authenticate(email, password) → Account
- get_account_by_uuid(account_uuid) → Account  (used by FastAPI dep that
  resolves a JWT into the current account)

Email is normalized to lowercase + stripped before any DB op.

Caller owns the transaction. `register_account` flushes; commit/rollback
is the caller's responsibility.
"""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.auth.exceptions import (
    AccountInactive,
    EmailAlreadyRegistered,
    InvalidCredentials,
)
from waraq.auth.passwords import hash_password, verify_password
from waraq.identity.service import new_uuid
from waraq.schemas import Account


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def register_account(
    *,
    session: AsyncSession,
    email: str,
    password: str,
    display_name: str | None = None,
) -> Account:
    """Create a new Account. Raises EmailAlreadyRegistered if the email
    is already taken (case-insensitive)."""
    normalized = _normalize_email(email)

    existing = (
        await session.execute(select(Account).where(Account.email == normalized))
    ).scalar_one_or_none()
    if existing is not None:
        raise EmailAlreadyRegistered(email=normalized)

    account = Account(
        account_uuid=new_uuid(),
        email=normalized,
        password_hash=hash_password(password),
        display_name=display_name,
    )
    session.add(account)
    await session.flush()
    return account


async def authenticate(
    *,
    session: AsyncSession,
    email: str,
    password: str,
) -> Account:
    """Look up the account by email and verify the password.

    Raises:
        InvalidCredentials: email unknown OR password wrong. Same class for
            both — don't leak existence-vs-password-wrong to the caller.
        AccountInactive: account exists, credentials valid, but `active=False`.
    """
    normalized = _normalize_email(email)
    account = (
        await session.execute(select(Account).where(Account.email == normalized))
    ).scalar_one_or_none()

    # Defense against timing oracles: do a dummy verify even when the account
    # doesn't exist, so the response time doesn't reveal account existence.
    if account is None:
        verify_password(password, "$2b$12$" + "x" * 53)
        raise InvalidCredentials("Email or password is incorrect")

    if not verify_password(password, account.password_hash):
        raise InvalidCredentials("Email or password is incorrect")

    if not account.active:
        raise AccountInactive(account_uuid=account.account_uuid)

    return account


async def get_account_by_uuid(*, session: AsyncSession, account_uuid: _uuid.UUID) -> Account | None:
    """Fetch an Account by its UUID. Returns None if not found.

    The FastAPI auth dependency uses this after JWT verification; it raises
    HTTP 401 in the unknown / inactive cases.
    """
    return (
        await session.execute(select(Account).where(Account.account_uuid == account_uuid))
    ).scalar_one_or_none()
