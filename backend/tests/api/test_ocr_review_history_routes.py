"""HTTP tests for /pages/.../ocr-review and the history readouts."""

from __future__ import annotations

import httpx
import pytest

from tests.api._m4_fixtures import make_page_block_segment


@pytest.mark.asyncio
class TestOcrReview:
    async def test_enter_and_post_findings_state_machine(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        r = await auth_client.post("/projects", json={"name": "p"})
        f = await make_page_block_segment(r.json()["project_uuid"])

        # Initial state: ausstehend.
        r = await auth_client.get(f"/pages/{f.page_uuid}")
        assert r.status_code == 200
        assert r.json()["ocr_status"] == "ausstehend"

        # Enter review.
        r = await auth_client.post(f"/pages/{f.page_uuid}/ocr-review/enter")
        assert r.status_code == 200
        assert r.json()["ocr_status"] == "in_review"

        # Apply a kritisch finding (F-01) → no_go.
        r = await auth_client.post(
            f"/pages/{f.page_uuid}/ocr-review/findings",
            json={"findings": [{"error_code": "F-01"}]},
        )
        assert r.status_code == 200
        assert r.json()["ocr_status"] == "no_go"

    async def test_findings_without_enter_409(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.post("/projects", json={"name": "p"})
        f = await make_page_block_segment(r.json()["project_uuid"])
        r = await auth_client.post(
            f"/pages/{f.page_uuid}/ocr-review/findings",
            json={"findings": [{"error_code": "F-01"}]},
        )
        assert r.status_code == 409


@pytest.mark.asyncio
class TestHistory:
    async def test_segment_history_empty(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.post("/projects", json={"name": "p"})
        f = await make_page_block_segment(r.json()["project_uuid"])
        r = await auth_client.get(f"/segments/{f.satz_uuid}/history")
        assert r.status_code == 200
        body = r.json()
        assert body["satz_uuid"] == str(f.satz_uuid)
        assert body["revisions"] == []

    async def test_segment_history_after_edit(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.post("/projects", json={"name": "p"})
        f = await make_page_block_segment(r.json()["project_uuid"], text="old")
        await auth_client.put(f"/segments/{f.satz_uuid}/text", json={"after_text": "new"})
        r = await auth_client.get(f"/segments/{f.satz_uuid}/history")
        assert r.status_code == 200
        body = r.json()
        assert len(body["revisions"]) == 1
