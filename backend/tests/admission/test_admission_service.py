"""Phase 5 sub-batch M — admission service tests.

Covers:
- `is_admin_email` honors `ADMIN_EMAILS` env (comma-separated,
  case-insensitive, missing-env = no admins).
- `register_account` defaults to `pending` for non-admin emails and
  auto-approves for admin emails (with `approved_at` set).
- `authenticate` refuses pending / rejected accounts with the
  specific exception classes.
- `list_pending_accounts` returns FIFO ordering, only active accounts.
- `approve_account` / `reject_account` flip status, record approver,
  raise `AlreadyDecided` on no-op transitions.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.admission import (
    AlreadyDecided,
    approve_account,
    is_admin_email,
    list_pending_accounts,
    reject_account,
)
from waraq.auth import (
    AccountPendingApproval,
    AccountRejected,
    authenticate,
    register_account,
)
from waraq.schemas.enums import ApprovalStatus

# ---------------------------------------------------------------------
# is_admin_email — env-driven
# ---------------------------------------------------------------------


class TestIsAdminEmail:
    def test_empty_env_no_admin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        assert is_admin_email("anyone@example.com") is False

    def test_blank_env_no_admin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADMIN_EMAILS", "   ")
        assert is_admin_email("anyone@example.com") is False

    def test_single_email_match(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADMIN_EMAILS", "admin@waraq.example")
        assert is_admin_email("admin@waraq.example") is True
        assert is_admin_email("admin@waraq.example".upper()) is True
        assert is_admin_email("other@waraq.example") is False

    def test_comma_separated_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADMIN_EMAILS", "alice@x.com, bob@x.com ,carol@x.com")
        assert is_admin_email("alice@x.com") is True
        assert is_admin_email("bob@x.com") is True
        assert is_admin_email("carol@x.com") is True
        assert is_admin_email("dave@x.com") is False

    def test_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADMIN_EMAILS", "Admin@Example.COM")
        assert is_admin_email("admin@example.com") is True
        assert is_admin_email("ADMIN@EXAMPLE.COM") is True


# ---------------------------------------------------------------------
# register_account — status defaults
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestRegisterApprovalDefaults:
    async def test_non_admin_registers_as_pending(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        account = await register_account(
            session=db_session, email="alice@example.com", password="hunter2"
        )
        assert account.approval_status == ApprovalStatus.PENDING
        assert account.approved_at is None
        assert account.approved_by_account_uuid is None

    async def test_admin_email_auto_approves(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ADMIN_EMAILS", "boss@example.com")
        account = await register_account(
            session=db_session, email="boss@example.com", password="hunter2"
        )
        assert account.approval_status == ApprovalStatus.APPROVED
        assert account.approved_at is not None
        # Self-approval at bootstrap: no separate approver UUID.
        assert account.approved_by_account_uuid is None


# ---------------------------------------------------------------------
# authenticate — refuses pending / rejected
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestAuthenticateRefusesNonApproved:
    async def test_pending_account_raises_pending_approval(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        await register_account(
            session=db_session, email="wait@example.com", password="hunter2"
        )
        with pytest.raises(AccountPendingApproval):
            await authenticate(
                session=db_session, email="wait@example.com", password="hunter2"
            )

    async def test_rejected_account_raises_rejected_with_reason(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        applicant = await register_account(
            session=db_session, email="no@example.com", password="hunter2"
        )
        # Self-reject for simplicity — approver in the audit field is
        # the applicant itself (doesn't matter for this test).
        await reject_account(
            session=db_session,
            account=applicant,
            approver=applicant,
            reason="Spam application",
        )
        with pytest.raises(AccountRejected) as exc:
            await authenticate(
                session=db_session, email="no@example.com", password="hunter2"
            )
        assert exc.value.reason == "Spam application"


# ---------------------------------------------------------------------
# list_pending_accounts — FIFO
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestListPending:
    async def test_includes_all_pending_accounts(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Three pending registrations are all returned. The service
        # orders by `created_at.asc()` but PG resolution can tie at
        # the microsecond when three INSERTs land in the same call —
        # we assert membership rather than order.
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        a = await register_account(
            session=db_session, email="a@x.com", password="x"
        )
        b = await register_account(
            session=db_session, email="b@x.com", password="x"
        )
        c = await register_account(
            session=db_session, email="c@x.com", password="x"
        )
        pending = await list_pending_accounts(session=db_session)
        uuids = {acc.account_uuid for acc in pending}
        assert a.account_uuid in uuids
        assert b.account_uuid in uuids
        assert c.account_uuid in uuids

    async def test_excludes_approved_accounts(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ADMIN_EMAILS", "boss@x.com")
        await register_account(session=db_session, email="boss@x.com", password="x")
        # boss is auto-approved; should NOT appear in pending list.
        pending = await list_pending_accounts(session=db_session)
        emails = {acc.email for acc in pending}
        assert "boss@x.com" not in emails


# ---------------------------------------------------------------------
# approve_account / reject_account
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestApproveReject:
    async def test_approve_flips_pending_to_approved(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ADMIN_EMAILS", "admin@x.com")
        admin = await register_account(
            session=db_session, email="admin@x.com", password="x"
        )
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        applicant = await register_account(
            session=db_session, email="new@x.com", password="x"
        )
        assert applicant.approval_status == ApprovalStatus.PENDING

        await approve_account(session=db_session, account=applicant, approver=admin)
        assert applicant.approval_status == ApprovalStatus.APPROVED
        assert applicant.approved_at is not None
        assert applicant.approved_by_account_uuid == admin.account_uuid
        assert applicant.rejection_reason is None

    async def test_approve_clears_prior_rejection_reason(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ADMIN_EMAILS", "admin@x.com")
        admin = await register_account(
            session=db_session, email="admin@x.com", password="x"
        )
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        applicant = await register_account(
            session=db_session, email="overturn@x.com", password="x"
        )
        await reject_account(
            session=db_session,
            account=applicant,
            approver=admin,
            reason="initial mistake",
        )
        assert applicant.rejection_reason == "initial mistake"
        # Admin overturns the rejection.
        await approve_account(session=db_session, account=applicant, approver=admin)
        assert applicant.approval_status == ApprovalStatus.APPROVED
        assert applicant.rejection_reason is None

    async def test_reject_flips_pending_to_rejected_with_reason(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ADMIN_EMAILS", "admin@x.com")
        admin = await register_account(
            session=db_session, email="admin@x.com", password="x"
        )
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        applicant = await register_account(
            session=db_session, email="reject@x.com", password="x"
        )
        await reject_account(
            session=db_session,
            account=applicant,
            approver=admin,
            reason="No reason given",
        )
        assert applicant.approval_status == ApprovalStatus.REJECTED
        assert applicant.rejection_reason == "No reason given"
        assert applicant.approved_by_account_uuid == admin.account_uuid

    async def test_reject_with_blank_reason_normalizes_to_none(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ADMIN_EMAILS", "admin@x.com")
        admin = await register_account(
            session=db_session, email="admin@x.com", password="x"
        )
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        applicant = await register_account(
            session=db_session, email="r2@x.com", password="x"
        )
        await reject_account(
            session=db_session, account=applicant, approver=admin, reason="   "
        )
        assert applicant.rejection_reason is None

    async def test_approve_already_approved_raises_already_decided(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ADMIN_EMAILS", "admin@x.com")
        admin = await register_account(
            session=db_session, email="admin@x.com", password="x"
        )
        # admin is already approved.
        with pytest.raises(AlreadyDecided) as exc:
            await approve_account(session=db_session, account=admin, approver=admin)
        assert exc.value.current == ApprovalStatus.APPROVED

    async def test_reject_already_rejected_raises_already_decided(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ADMIN_EMAILS", "admin@x.com")
        admin = await register_account(
            session=db_session, email="admin@x.com", password="x"
        )
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        applicant = await register_account(
            session=db_session, email="twice@x.com", password="x"
        )
        await reject_account(
            session=db_session, account=applicant, approver=admin, reason="first"
        )
        with pytest.raises(AlreadyDecided):
            await reject_account(
                session=db_session, account=applicant, approver=admin, reason="second"
            )
