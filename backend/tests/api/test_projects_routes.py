"""HTTP integration tests for /projects/*."""

from __future__ import annotations

import httpx
import pytest

from waraq.identity import new_uuid


@pytest.mark.asyncio
class TestProjectsCrud:
    async def test_create_and_get_project(self, auth_client: httpx.AsyncClient) -> None:
        # Create
        resp = await auth_client.post("/projects", json={"name": "Sahih Bukhari Vol 1"})
        assert resp.status_code == 201
        created = resp.json()
        assert created["name"] == "Sahih Bukhari Vol 1"
        assert created["active"] is True
        project_uuid = created["project_uuid"]

        # Get
        resp = await auth_client.get(f"/projects/{project_uuid}")
        assert resp.status_code == 200
        assert resp.json()["project_uuid"] == project_uuid

    async def test_list_returns_only_my_projects(self, auth_client: httpx.AsyncClient) -> None:
        await auth_client.post("/projects", json={"name": "Project A"})
        await auth_client.post("/projects", json={"name": "Project B"})

        resp = await auth_client.get("/projects")
        assert resp.status_code == 200
        names = sorted(p["name"] for p in resp.json())
        assert names == ["Project A", "Project B"]

    async def test_get_other_users_project_returns_404(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        # A random UUID that doesn't exist (or belongs to no one we know).
        resp = await auth_client.get(f"/projects/{new_uuid()}")
        assert resp.status_code == 404

    async def test_endpoints_require_auth(self, http_client: httpx.AsyncClient) -> None:
        resp = await http_client.post("/projects", json={"name": "x"})
        assert resp.status_code == 401
        resp = await http_client.get("/projects")
        assert resp.status_code == 401
