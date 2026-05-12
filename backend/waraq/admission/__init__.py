"""Phase 5 sub-batch M — admission gate (simplified §2.3 row 8).

Public surface:
- `is_admin_email(email)` — does this email match an entry in
  `ADMIN_EMAILS` env? Used at registration to auto-approve admins
  (bootstrap rule).
- `list_pending_accounts(session)` — admin dashboard data source.
- `approve_account(session, account, approver)` — flip status to
  `approved` + record audit.
- `reject_account(session, account, approver, reason)` — flip to
  `rejected` + audit.
- `AlreadyDecided` — raised when admin tries to approve/reject an
  account that's not pending.
"""

from __future__ import annotations

from waraq.admission.service import (
    AlreadyDecided,
    approve_account,
    is_admin_email,
    list_pending_accounts,
    reject_account,
)

__all__ = [
    "AlreadyDecided",
    "approve_account",
    "is_admin_email",
    "list_pending_accounts",
    "reject_account",
]
