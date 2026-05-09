"""HTTP tests for /projects/.../release-gate and /translation-jobs."""

from __future__ import annotations

import httpx
import pytest

from tests.api._m4_fixtures import make_page_block_segment


@pytest.mark.asyncio
class TestReleaseGate:
    async def test_evaluate_empty_project_uebersetzungsreif(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        # Empty project: no pages → no no_go, no F-06-QR, no conflicts → ready.
        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        r = await auth_client.get(f"/projects/{project_uuid}/release-gate")
        assert r.status_code == 200
        body = r.json()
        assert body["state"] == "uebersetzungsreif"
        assert body["blocking_reasons"] == []

    async def test_start_translation_writes_de(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        r = await auth_client.post(
            f"/projects/{project_uuid}/release-gate/start-translation",
            json={"note": "go"},
        )
        assert r.status_code == 201
        assert "decision_event_uuid" in r.json()


@pytest.mark.asyncio
class TestTranslation:
    async def test_start_refused_without_uebersetzungsstart(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        f = await make_page_block_segment(project_uuid)
        r = await auth_client.post(
            f"/projects/{project_uuid}/translation-jobs",
            json={"segment_uuids": [str(f.satz_uuid)]},
        )
        # Without prior uebersetzungsstart DE → 409.
        assert r.status_code == 409

    async def test_start_after_uebersetzungsstart(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        f = await make_page_block_segment(project_uuid)
        # Write the DE
        await auth_client.post(f"/projects/{project_uuid}/release-gate/start-translation", json={})
        r = await auth_client.post(
            f"/projects/{project_uuid}/translation-jobs",
            json={"segment_uuids": [str(f.satz_uuid)]},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["job_type"] == "translation"
        assert body["state"] == "pending"
