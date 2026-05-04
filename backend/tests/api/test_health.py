"""HTTP smoke tests for /health and /health/db."""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.asyncio
class TestHealth:
    async def test_health_returns_ok(self, http_client: httpx.AsyncClient) -> None:
        resp = await http_client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_health_db_connects(self, http_client: httpx.AsyncClient) -> None:
        resp = await http_client.get("/health/db")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["db"] == "ok"
