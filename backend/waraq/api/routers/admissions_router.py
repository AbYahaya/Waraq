"""Phase 5 sub-batch M — admin admission gate API.

Three endpoints under `/admin/admissions/*`, all admin-only (via the
existing `CurrentAdmin` dependency that checks the `ADMIN_EMAILS` env
allowlist):

  - `GET  /admin/admissions/pending`       list pending accounts.
  - `POST /admin/admissions/{uuid}/approve` approve a pending or
                                            previously-rejected account.
  - `POST /admin/admissions/{uuid}/reject`  reject (with optional reason).

The simplified §2.3 row 8 — tier system / subscription / inactivity-
deletion / guest user / trash purge (rows 9-13) all stay deferred per
the user's 2026-05-12 scope decision. Approved accounts get full access
to all features.
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from waraq.admission import (
    AlreadyDecided,
    approve_account,
    list_pending_accounts,
    reject_account,
)
from waraq.api.dependencies import CurrentAdmin, DbSession
from waraq.schemas import Account
from waraq.schemas.enums import ApprovalStatus

router = APIRouter(prefix="/admin/admissions", tags=["admin", "admissions"])


# ---------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------


class AdmissionAccountResponse(BaseModel):
    """One pending / decided account as seen in the admin dashboard.
    The password_hash is deliberately NOT exposed."""

    account_uuid: _uuid.UUID
    email: str
    display_name: str | None
    approval_status: str  # ApprovalStatus.value
    approved_at: str | None  # ISO 8601 if set
    approved_by_account_uuid: _uuid.UUID | None
    rejection_reason: str | None
    created_at: str  # ISO 8601 — when the user applied

    @classmethod
    def from_account(cls, account: Account) -> AdmissionAccountResponse:
        return cls(
            account_uuid=account.account_uuid,
            email=account.email,
            display_name=account.display_name,
            approval_status=account.approval_status.value,
            approved_at=(
                account.approved_at.isoformat() if account.approved_at is not None else None
            ),
            approved_by_account_uuid=account.approved_by_account_uuid,
            rejection_reason=account.rejection_reason,
            created_at=account.created_at.isoformat(),
        )


class RejectRequest(BaseModel):
    """Optional rejection reason — free-form text shown to the user
    when they try to log in to a rejected account."""

    reason: str | None = None


class AdmissionListResponse(BaseModel):
    accounts: list[AdmissionAccountResponse]


# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------


@router.get("/pending", response_model=AdmissionListResponse)
async def list_pending(
    session: DbSession,
    admin: CurrentAdmin,
) -> AdmissionListResponse:
    """List all accounts currently in `pending` status (FIFO oldest-first)."""
    _ = admin  # admin role enforced by CurrentAdmin dep
    pending = await list_pending_accounts(session=session)
    return AdmissionListResponse(
        accounts=[AdmissionAccountResponse.from_account(a) for a in pending]
    )


async def _admission_account_or_404(
    session: DbSession, account_uuid: _uuid.UUID
) -> Account:
    """Lookup helper. 404 when the account doesn't exist OR is inactive —
    admin can't act on a deactivated account through this surface."""
    result = await session.execute(
        select(Account)
        .where(Account.account_uuid == account_uuid)
        .where(Account.active.is_(True))
    )
    account: Account | None = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )
    return account


@router.post(
    "/{account_uuid}/approve", response_model=AdmissionAccountResponse
)
async def approve(
    account_uuid: _uuid.UUID,
    session: DbSession,
    admin: CurrentAdmin,
) -> AdmissionAccountResponse:
    """Flip an account from pending or rejected → approved. Idempotent
    on already-approved → HTTP 409."""
    account = await _admission_account_or_404(session, account_uuid)
    try:
        await approve_account(session=session, account=account, approver=admin)
    except AlreadyDecided as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return AdmissionAccountResponse.from_account(account)


@router.post(
    "/{account_uuid}/reject", response_model=AdmissionAccountResponse
)
async def reject(
    account_uuid: _uuid.UUID,
    req: RejectRequest,
    session: DbSession,
    admin: CurrentAdmin,
) -> AdmissionAccountResponse:
    """Flip an account from pending or approved → rejected. The
    rejection reason (optional) is shown to the user on their next
    login attempt."""
    account = await _admission_account_or_404(session, account_uuid)
    try:
        await reject_account(
            session=session,
            account=account,
            approver=admin,
            reason=req.reason,
        )
    except AlreadyDecided as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return AdmissionAccountResponse.from_account(account)


# Silence unused-name lint on the canonical enum import (the router
# references ApprovalStatus values via Account.approval_status.value).
_ = ApprovalStatus
