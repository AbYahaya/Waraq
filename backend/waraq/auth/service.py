"""Sprint -0.5 — Account auth service. Phase 5 sub-batch M adds the
admission gate.

Three operations:
- register_account(email, password, display_name=None) → Account
- authenticate(email, password) → Account
- get_account_by_uuid(account_uuid) → Account  (used by FastAPI dep that
  resolves a JWT into the current account)

Email is normalized to lowercase + stripped before any DB op.

**Phase 5 admission gate (sub-batch M)**: `register_account` sets the
new account's `approval_status` to `APPROVED` for emails in
`ADMIN_EMAILS` env (bootstrap rule — at least one approver must exist)
and `PENDING` for everyone else. `authenticate` refuses non-approved
accounts with `AccountPendingApproval` / `AccountRejected` so the user
sees a specific reason rather than a generic "invalid credentials".

Caller owns the transaction. `register_account` flushes; commit/rollback
is the caller's responsibility.
"""

from __future__ import annotations

import datetime as _dt
import uuid as _uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.admission import is_admin_email
from waraq.auth.exceptions import (
    AccountInactive,
    AccountPendingApproval,
    AccountRejected,
    EmailAlreadyRegistered,
    InvalidCredentials,
)
from waraq.auth.passwords import hash_password, verify_password
from waraq.identity.service import new_uuid
from waraq.schemas import Account
from waraq.schemas.enums import ApprovalStatus


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

    # M admission gate: admin emails auto-approve at registration so
    # the very first admin can immediately act on the pending queue;
    # everyone else starts in `pending` and waits for an admin.
    is_admin = is_admin_email(normalized)
    initial_status = ApprovalStatus.APPROVED if is_admin else ApprovalStatus.PENDING
    approved_at = _dt.datetime.now(_dt.UTC) if is_admin else None

    account = Account(
        account_uuid=new_uuid(),
        email=normalized,
        password_hash=hash_password(password),
        display_name=display_name,
        approval_status=initial_status,
        approved_at=approved_at,
        # Self-approval for admins — there's no other approver at
        # bootstrap time. Subsequent admins are still auto-approved
        # the same way (admin status is env-driven, not DB-driven).
        approved_by_account_uuid=None,
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

    # M admission gate. Surface pending / rejected with explicit
    # error classes so the UI can show a useful message instead of
    # the generic 401.
    if account.approval_status == ApprovalStatus.PENDING:
        raise AccountPendingApproval(account_uuid=account.account_uuid)
    if account.approval_status == ApprovalStatus.REJECTED:
        raise AccountRejected(
            account_uuid=account.account_uuid,
            reason=account.rejection_reason,
        )

    return account


async def get_account_by_uuid(*, session: AsyncSession, account_uuid: _uuid.UUID) -> Account | None:
    """Fetch an Account by its UUID. Returns None if not found.

    The FastAPI auth dependency uses this after JWT verification; it raises
    HTTP 401 in the unknown / inactive cases.
    """
    return (
        await session.execute(select(Account).where(Account.account_uuid == account_uuid))
    ).scalar_one_or_none()
