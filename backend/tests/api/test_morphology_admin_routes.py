"""HTTP tests for /morphology and /admin endpoints.

Both surfaces are M4 additions. Morphology is gated behind the optional
camel-tools install — these tests run on the absent-package path
(503/availability=false) and the stubbed-analyzer path (mocking the
module-level `_analyzer` binding).

Admin is gated by the `WARAQ_ADMIN_EMAILS` env allowlist; tests
manipulate `Settings.admin_emails` via `db.session.get_settings`'s
`@lru_cache` (clear cache, monkeypatch env, re-evaluate).
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest


@pytest.mark.asyncio
class TestMorphologyAvailability:
    async def test_unauthenticated_blocked(self, http_client: httpx.AsyncClient) -> None:
        r = await http_client.get("/morphology/availability")
        assert r.status_code == 401

    async def test_reports_unavailable_without_camel(
        self, auth_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # camel-tools is not installed in CI/dev. is_available() returns False.
        from waraq.morphology import service as svc

        # Force a fresh import path by clearing any cached analyzer.
        monkeypatch.setattr(svc, "_analyzer", None)
        r = await auth_client.get("/morphology/availability")
        assert r.status_code == 200
        body = r.json()
        assert body["available"] is False
        assert (
            "camel-tools" in (body["reason"] or "").lower()
            or "morphology" in (body["reason"] or "").lower()
        )


@pytest.mark.asyncio
class TestMorphologyAnalyze:
    async def test_503_when_not_installed(
        self, auth_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from waraq.morphology import service as svc

        monkeypatch.setattr(svc, "_analyzer", None)
        r = await auth_client.post("/morphology/analyze", json={"word": "كتاب"})
        assert r.status_code == 503
        body = r.json()
        assert "camel" in (body.get("detail") or "").lower()

    async def test_returns_analyses_with_stubbed_analyzer(
        self, auth_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Stub the module-level analyzer with a fake `analyze` method
        so we don't need camel-tools installed to exercise the happy path."""
        from waraq.morphology import service as svc

        class _FakeAnalyzer:
            def analyze(self, word: str) -> list[dict[str, Any]]:
                return [
                    {
                        "diac": "كِتَاب",
                        "lex": "kitAb",
                        "root": "k.t.b",
                        "pos": "noun",
                        "gloss": "book",
                        "gen": "m",
                        "num": "s",
                        "per": "na",
                        "src": "test",  # extras
                    }
                ]

        monkeypatch.setattr(svc, "_analyzer", _FakeAnalyzer())
        r = await auth_client.post("/morphology/analyze", json={"word": "كتاب"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["word"] == "كتاب"
        assert len(body["analyses"]) == 1
        a = body["analyses"][0]
        assert a["root"] == "k.t.b"
        assert a["gloss"] == "book"
        assert a["pos"] == "noun"

    async def test_empty_word_rejected(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.post("/morphology/analyze", json={"word": ""})
        # Pydantic min_length=1 → 422.
        assert r.status_code == 422


@pytest.mark.asyncio
class TestAdmin:
    async def test_non_admin_forbidden(
        self, auth_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Empty allowlist → caller's email isn't admin.
        from waraq.db import session as db_session_module

        db_session_module.get_settings.cache_clear()
        monkeypatch.setenv("ADMIN_EMAILS", "")
        r = await auth_client.get("/admin/accounts")
        assert r.status_code == 403

    async def test_admin_lists_accounts(
        self, auth_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Look up our test account's email and seed it into the allowlist.
        me = (await auth_client.get("/auth/me")).json()
        email = me["email"]

        from waraq.db import session as db_session_module

        db_session_module.get_settings.cache_clear()
        monkeypatch.setenv("ADMIN_EMAILS", email)

        r = await auth_client.get("/admin/accounts")
        assert r.status_code == 200, r.text
        rows = r.json()
        assert any(row["email"] == email for row in rows)

    async def test_admin_lists_projects(
        self, auth_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Create a project under the current account.
        await auth_client.post("/projects", json={"name": "AdminViewable"})

        me = (await auth_client.get("/auth/me")).json()
        from waraq.db import session as db_session_module

        db_session_module.get_settings.cache_clear()
        monkeypatch.setenv("ADMIN_EMAILS", me["email"])

        r = await auth_client.get("/admin/projects", params={"account_uuid": me["account_uuid"]})
        assert r.status_code == 200, r.text
        rows = r.json()
        assert any(p["name"] == "AdminViewable" for p in rows)
