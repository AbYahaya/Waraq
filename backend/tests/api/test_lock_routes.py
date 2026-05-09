"""HTTP tests for /segments/{satz_uuid}/lock."""

from __future__ import annotations

import httpx
import pytest

from tests.api._m4_fixtures import make_page_block_segment


@pytest.mark.asyncio
class TestLockRoutes:
    async def _seed(self, auth_client: httpx.AsyncClient) -> str:
        r = await auth_client.post("/projects", json={"name": "p"})
        f = await make_page_block_segment(r.json()["project_uuid"])
        return str(f.satz_uuid)

    async def test_set_manual_local_lock(self, auth_client: httpx.AsyncClient) -> None:
        satz = await self._seed(auth_client)
        r = await auth_client.post(f"/segments/{satz}/lock", json={"level": "manual_local"})
        assert r.status_code == 201
        assert r.json()["lock_flag"] == "manual_local"

    async def test_release_manual_local_no_confirmation_required(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        satz = await self._seed(auth_client)
        await auth_client.post(f"/segments/{satz}/lock", json={"level": "manual_local"})
        r = await auth_client.request("DELETE", f"/segments/{satz}/lock", json={"note": None})
        assert r.status_code == 200
        assert r.json()["lock_flag"] == "none"

    async def test_set_invalid_level_400(self, auth_client: httpx.AsyncClient) -> None:
        satz = await self._seed(auth_client)
        r = await auth_client.post(f"/segments/{satz}/lock", json={"level": "weird"})
        # Pydantic validation rejects with 422.
        assert r.status_code == 422

    async def test_idempotent_set_409(self, auth_client: httpx.AsyncClient) -> None:
        satz = await self._seed(auth_client)
        r1 = await auth_client.post(f"/segments/{satz}/lock", json={"level": "manual_local"})
        assert r1.status_code == 201
        r2 = await auth_client.post(f"/segments/{satz}/lock", json={"level": "manual_local"})
        assert r2.status_code == 409

    async def test_release_manual_editorial_with_confirmation(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        satz = await self._seed(auth_client)
        r = await auth_client.post(f"/segments/{satz}/lock", json={"level": "manual_editorial"})
        assert r.status_code == 201
        # Release writes a ConfirmationContext from the current account.
        r = await auth_client.request(
            "DELETE",
            f"/segments/{satz}/lock",
            json={"note": "user clicked confirm"},
        )
        assert r.status_code == 200
        assert r.json()["lock_flag"] == "none"
