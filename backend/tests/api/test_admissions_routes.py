"""Phase 5 sub-batch M — HTTP-layer admission tests.

Covers:
- Register response shape: `approval_status` + `access_token` per email type.
- Login error mapping for pending / rejected.
- /admin/admissions/pending requires admin role.
- /admin/admissions/{uuid}/approve and /reject flows + 409 on no-op.
- /auth/me surfaces approval_status + is_admin.
"""

from __future__ import annotations

import contextlib
import os

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.api.conftest import _cleanup_account
from tests.conftest import _test_database_url
from waraq.identity import new_uuid
from waraq.schemas import Account


def _admin_env(monkeypatch: pytest.MonkeyPatch, email: str) -> None:
    """Add `email` to ADMIN_EMAILS env so register auto-approves it."""
    existing = os.environ.get("ADMIN_EMAILS", "")
    monkeypatch.setenv("ADMIN_EMAILS", f"{existing},{email}".lstrip(","))
    from waraq.db.session import get_settings

    get_settings.cache_clear()


async def _delete_account_by_email(email: str) -> None:
    engine = create_async_engine(_test_database_url(), future=True)
    sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with sm() as s:
            acc = (
                await s.execute(select(Account).where(Account.email == email))
            ).scalar_one_or_none()
            if acc is not None:
                uuid = acc.account_uuid
    finally:
        await engine.dispose()
    with contextlib.suppress(NameError):
        await _cleanup_account(uuid)  # type: ignore[possibly-undefined]


# ---------------------------------------------------------------------
# Register response shape
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestRegisterResponse:
    async def test_non_admin_register_returns_pending_without_token(
        self, http_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        email = f"pending-{new_uuid()}@waraq-test.example.com"
        resp = await http_client.post(
            "/auth/register",
            json={"email": email, "password": "supersecret"},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["approval_status"] == "pending"
        assert body["access_token"] is None

        await _delete_account_by_email(email)

    async def test_admin_email_register_returns_approved_with_token(
        self, http_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = f"admin-{new_uuid()}@waraq-test.example.com"
        _admin_env(monkeypatch, email)
        resp = await http_client.post(
            "/auth/register",
            json={"email": email, "password": "supersecret"},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["approval_status"] == "approved"
        assert body["access_token"]

        await _delete_account_by_email(email)


# ---------------------------------------------------------------------
# Login refusals for pending / rejected
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestLoginGate:
    async def test_pending_account_login_returns_403_with_approval_message(
        self, http_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ADMIN_EMAILS", raising=False)
        email = f"pending-login-{new_uuid()}@waraq-test.example.com"
        await http_client.post(
            "/auth/register", json={"email": email, "password": "long-enough-password"}
        )
        resp = await http_client.post(
            "/auth/login", json={"email": email, "password": "long-enough-password"}
        )
        assert resp.status_code == 403
        assert "approval" in resp.json()["detail"].lower()

        await _delete_account_by_email(email)


# ---------------------------------------------------------------------
# Admin admissions endpoints
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestAdminAdmissionsEndpoints:
    async def test_pending_endpoint_requires_admin(self, auth_client: httpx.AsyncClient) -> None:
        # The auth_client fixture's email is an admin (added to
        # ADMIN_EMAILS at fixture time), so this should succeed.
        # First check that the endpoint exists + returns a list shape.
        resp = await auth_client.get("/admin/admissions/pending")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "accounts" in body
        assert isinstance(body["accounts"], list)

    async def test_non_admin_gets_403_on_pending_endpoint(
        self,
        http_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Create a non-admin account, log in, hit the endpoint with their token.
        admin_email = f"adm-{new_uuid()}@waraq-test.example.com"
        _admin_env(monkeypatch, admin_email)
        non_admin_email = f"reg-{new_uuid()}@waraq-test.example.com"

        await http_client.post(
            "/auth/register",
            json={"email": admin_email, "password": "long-enough-password"},
        )
        await http_client.post(
            "/auth/register",
            json={"email": non_admin_email, "password": "long-enough-password"},
        )
        # Approve the non-admin via the admin route so they can log in.
        admin_login = await http_client.post(
            "/auth/login",
            json={"email": admin_email, "password": "long-enough-password"},
        )
        admin_token = admin_login.json()["access_token"]
        # Find the non-admin's uuid.
        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with sm() as s:
                applicant = (
                    await s.execute(select(Account).where(Account.email == non_admin_email))
                ).scalar_one()
        finally:
            await engine.dispose()
        # Approve.
        approve_resp = await http_client.post(
            f"/admin/admissions/{applicant.account_uuid}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert approve_resp.status_code == 200, approve_resp.text

        # Now log in as the non-admin and try to hit the admissions endpoint.
        login = await http_client.post(
            "/auth/login",
            json={"email": non_admin_email, "password": "long-enough-password"},
        )
        token = login.json()["access_token"]
        resp = await http_client.get(
            "/admin/admissions/pending",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

        await _delete_account_by_email(non_admin_email)
        await _delete_account_by_email(admin_email)

    async def test_approve_pending_account_flips_status(
        self,
        http_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        admin_email = f"adm-{new_uuid()}@waraq-test.example.com"
        _admin_env(monkeypatch, admin_email)
        pending_email = f"applicant-{new_uuid()}@waraq-test.example.com"

        await http_client.post(
            "/auth/register",
            json={"email": admin_email, "password": "long-enough-password"},
        )
        await http_client.post(
            "/auth/register",
            json={"email": pending_email, "password": "long-enough-password"},
        )

        admin_login = await http_client.post(
            "/auth/login",
            json={"email": admin_email, "password": "long-enough-password"},
        )
        admin_token = admin_login.json()["access_token"]

        # Find applicant uuid.
        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with sm() as s:
                applicant = (
                    await s.execute(select(Account).where(Account.email == pending_email))
                ).scalar_one()
        finally:
            await engine.dispose()

        # Approve.
        approve_resp = await http_client.post(
            f"/admin/admissions/{applicant.account_uuid}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert approve_resp.status_code == 200, approve_resp.text
        assert approve_resp.json()["approval_status"] == "approved"

        # Login now succeeds.
        login = await http_client.post(
            "/auth/login",
            json={"email": pending_email, "password": "long-enough-password"},
        )
        assert login.status_code == 200
        assert login.json()["access_token"]

        await _delete_account_by_email(pending_email)
        await _delete_account_by_email(admin_email)

    async def test_reject_pending_account_blocks_login(
        self,
        http_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        admin_email = f"adm-{new_uuid()}@waraq-test.example.com"
        _admin_env(monkeypatch, admin_email)
        applicant_email = f"applicant-{new_uuid()}@waraq-test.example.com"

        await http_client.post(
            "/auth/register",
            json={"email": admin_email, "password": "long-enough-password"},
        )
        await http_client.post(
            "/auth/register",
            json={"email": applicant_email, "password": "long-enough-password"},
        )

        admin_login = await http_client.post(
            "/auth/login",
            json={"email": admin_email, "password": "long-enough-password"},
        )
        admin_token = admin_login.json()["access_token"]

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with sm() as s:
                applicant = (
                    await s.execute(select(Account).where(Account.email == applicant_email))
                ).scalar_one()
        finally:
            await engine.dispose()

        # Reject with a reason.
        reject_resp = await http_client.post(
            f"/admin/admissions/{applicant.account_uuid}/reject",
            json={"reason": "Test rejection"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["approval_status"] == "rejected"
        assert reject_resp.json()["rejection_reason"] == "Test rejection"

        # Login is now refused with a specific message that includes the reason.
        login = await http_client.post(
            "/auth/login",
            json={"email": applicant_email, "password": "long-enough-password"},
        )
        assert login.status_code == 403
        assert "Test rejection" in login.json()["detail"]

        await _delete_account_by_email(applicant_email)
        await _delete_account_by_email(admin_email)

    async def test_approve_already_approved_returns_409(
        self,
        auth_client: httpx.AsyncClient,
    ) -> None:
        # auth_client's account is admin (and approved). Try to
        # approve it again — should 409.
        me = await auth_client.get("/auth/me")
        account_uuid = me.json()["account_uuid"]
        resp = await auth_client.post(f"/admin/admissions/{account_uuid}/approve")
        assert resp.status_code == 409


# ---------------------------------------------------------------------
# /auth/me extension
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestAuthMeApprovalFields:
    async def test_me_surfaces_approval_status_and_is_admin(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        resp = await auth_client.get("/auth/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["approval_status"] == "approved"
        # auth_client's email is in ADMIN_EMAILS by fixture design.
        assert body["is_admin"] is True
