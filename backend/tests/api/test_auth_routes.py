"""HTTP integration tests for /auth/*."""

from __future__ import annotations

import os

import httpx
import pytest

from waraq.identity import new_uuid


@pytest.mark.asyncio
class TestRegisterAndLogin:
    async def test_register_returns_token(
        self, http_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Phase 5 M: admin emails auto-approve and get a token; non-admin
        # emails get pending status with no token. Add this email to
        # ADMIN_EMAILS so the happy path under test (token-on-register)
        # still works.
        email = f"reg-{new_uuid()}@waraq-test.example.com"
        existing = os.environ.get("ADMIN_EMAILS", "")
        monkeypatch.setenv("ADMIN_EMAILS", f"{existing},{email}".lstrip(","))
        from waraq.db.session import get_settings

        get_settings.cache_clear()
        resp = await http_client.post(
            "/auth/register",
            json={"email": email, "password": "supersecret"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["approval_status"] == "approved"
        assert body["token_type"] == "bearer"
        assert body["access_token"]

        # Cleanup so we don't leak.
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from tests.api.conftest import _cleanup_account
        from waraq.schemas import Account

        engine = create_async_engine(
            __import__("tests.conftest", fromlist=["_test_database_url"])._test_database_url(),
            future=True,
        )
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with sm() as s:
                acc = (await s.execute(select(Account).where(Account.email == email))).scalar_one()
                uuid = acc.account_uuid
        finally:
            await engine.dispose()
        await _cleanup_account(uuid)

    async def test_register_duplicate_email_returns_409(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        # auth_client is already registered; pull its email from /auth/me.
        resp = await auth_client.get("/auth/me")
        email_from_me = resp.json()["email"]

        resp = await auth_client.post(
            "/auth/register",
            json={"email": email_from_me, "password": "anything-else"},
        )
        assert resp.status_code == 409

    async def test_login_with_correct_credentials(
        self, http_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = f"login-{new_uuid()}@waraq-test.example.com"
        password = "myPassword123"

        # Phase 5 M: pre-approve this account by adding it to ADMIN_EMAILS
        # so the login happy path under test still works.
        existing = os.environ.get("ADMIN_EMAILS", "")
        monkeypatch.setenv("ADMIN_EMAILS", f"{existing},{email}".lstrip(","))
        from waraq.db.session import get_settings

        get_settings.cache_clear()

        # Register
        await http_client.post("/auth/register", json={"email": email, "password": password})

        # Login
        resp = await http_client.post("/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200
        assert resp.json()["access_token"]

        # Cleanup
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from tests.api.conftest import _cleanup_account
        from tests.conftest import _test_database_url
        from waraq.schemas import Account

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with sm() as s:
                acc = (await s.execute(select(Account).where(Account.email == email))).scalar_one()
                uuid = acc.account_uuid
        finally:
            await engine.dispose()
        await _cleanup_account(uuid)

    async def test_login_with_wrong_password_returns_401(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        email_resp = await auth_client.get("/auth/me")
        email = email_resp.json()["email"]

        resp = await auth_client.post("/auth/login", json={"email": email, "password": "wrong"})
        assert resp.status_code == 401

    async def test_login_with_unknown_email_returns_401(
        self, http_client: httpx.AsyncClient
    ) -> None:
        # Use a syntactically-valid email that just doesn't exist.
        resp = await http_client.post(
            "/auth/login",
            json={
                "email": f"ghost-{new_uuid()}@waraq-test.example.com",
                "password": "x",
            },
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestAuthMe:
    async def test_me_returns_account_for_valid_token(self, auth_client: httpx.AsyncClient) -> None:
        resp = await auth_client.get("/auth/me")
        assert resp.status_code == 200
        body = resp.json()
        assert "@waraq-test.example.com" in body["email"]
        assert body["active"] is True

    async def test_me_without_token_returns_401(self, http_client: httpx.AsyncClient) -> None:
        resp = await http_client.get("/auth/me")
        assert resp.status_code == 401

    async def test_me_with_garbage_token_returns_401(self, http_client: httpx.AsyncClient) -> None:
        resp = await http_client.get("/auth/me", headers={"Authorization": "Bearer not.a.real.jwt"})
        assert resp.status_code == 401

    async def test_me_with_non_bearer_scheme_returns_401(
        self, http_client: httpx.AsyncClient
    ) -> None:
        resp = await http_client.get("/auth/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert resp.status_code == 401
