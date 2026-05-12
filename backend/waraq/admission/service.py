"""Phase 5 sub-batch M — admission gate service.

The simplified §2.3 row 8 ("Tier 0/1/2 system + application form + admin
approval"). Per the user's 2026-05-12 scope decision, only the
application + admin-approval slice ships in M. Tier 0/1/2 system stays
deferred until the user explicitly opens that work — row 8 lives at
**partial** in CANON_TRACKER (⚠️) until tiers land.

Five operations:

- `is_admin_email(email)` — does this email match an entry in
  the `ADMIN_EMAILS` env (comma-separated, case-insensitive)? Drives
  the bootstrap rule at registration: admins are auto-approved so
  there's always at least one approver who can act on pending queue
  entries.
- `list_pending_accounts(session)` — accounts with
  `approval_status = pending`, ordered oldest-first (FIFO for fairness).
- `approve_account(session, account, approver)` — flip pending|rejected
  → approved + record `approved_at` + `approved_by_account_uuid`.
- `reject_account(session, account, approver, reason)` — flip pending
  → rejected + record `rejection_reason`. Approved accounts can also
  be rejected (rare but legal — the admin can revoke approval).
- `_AlreadyDecided` raised when no transition would change anything
  (e.g. approving an already-approved account).

Caller owns the transaction. The service flushes; commit is the
caller's responsibility.
"""

from __future__ import annotations

import datetime as _dt
import os
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.schemas import Account
from waraq.schemas.enums import ApprovalStatus


class AlreadyDecided(ValueError):
    """Admin tried to approve/reject an account whose current status
    already matches the requested transition. Defensive — surfacing
    as HTTP 409 in the router so the UI can refresh and re-render."""

    def __init__(self, *, current: ApprovalStatus, requested: ApprovalStatus) -> None:
        super().__init__(
            f"Account is already in status {current.value!r}; "
            f"requested transition to {requested.value!r} is a no-op."
        )
        self.current = current
        self.requested = requested


def is_admin_email(email: str) -> bool:
    """True iff `email` is in the `ADMIN_EMAILS` env (comma-separated,
    case-insensitive). Empty env or missing value → no admins, in
    which case the user-facing experience is that the very first
    account ever registered will stay `pending` forever — surface
    that via the bootstrap warning when the env is empty.

    Mirrors the existing `ADMIN_EMAILS` env var which is already used
    in `backend/.env` (the developer's `ab@gmail.com` entry).
    """
    raw = os.environ.get("ADMIN_EMAILS", "").strip()
    if not raw:
        return False
    canonical = email.strip().lower()
    admins = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return canonical in admins


async def list_pending_accounts(*, session: AsyncSession) -> Sequence[Account]:
    """Return all accounts with `approval_status = pending`, ordered
    by `created_at` ascending (FIFO — first-applied is first-decided).
    Only active accounts are returned (deactivated pending accounts
    are surfaced separately if/when that workflow lands)."""
    result = await session.execute(
        select(Account)
        .where(Account.approval_status == ApprovalStatus.PENDING)
        .where(Account.active.is_(True))
        .order_by(Account.created_at.asc())
    )
    return list(result.scalars())


async def approve_account(
    *,
    session: AsyncSession,
    account: Account,
    approver: Account,
) -> Account:
    """Flip `account` to `approved`. Records `approved_at` + the
    approver's UUID. Idempotent-on-already-approved → `AlreadyDecided`."""
    if account.approval_status == ApprovalStatus.APPROVED:
        raise AlreadyDecided(
            current=account.approval_status,
            requested=ApprovalStatus.APPROVED,
        )
    account.approval_status = ApprovalStatus.APPROVED
    account.approved_at = _dt.datetime.now(_dt.UTC)
    account.approved_by_account_uuid = approver.account_uuid
    # Clear any prior rejection reason — admin overturned the rejection.
    account.rejection_reason = None
    await session.flush()
    return account


async def reject_account(
    *,
    session: AsyncSession,
    account: Account,
    approver: Account,
    reason: str | None,
) -> Account:
    """Flip `account` to `rejected`. Records the rejection reason
    (free-form). `approved_at` is reused to record the decision time
    — the column name predates this flow; "decided_at" would be more
    accurate but renaming is wire-shaped."""
    if account.approval_status == ApprovalStatus.REJECTED:
        raise AlreadyDecided(
            current=account.approval_status,
            requested=ApprovalStatus.REJECTED,
        )
    account.approval_status = ApprovalStatus.REJECTED
    account.approved_at = _dt.datetime.now(_dt.UTC)
    account.approved_by_account_uuid = approver.account_uuid
    account.rejection_reason = (reason or "").strip() or None
    await session.flush()
    return account


__all__ = [
    "AlreadyDecided",
    "approve_account",
    "is_admin_email",
    "list_pending_accounts",
    "reject_account",
]
