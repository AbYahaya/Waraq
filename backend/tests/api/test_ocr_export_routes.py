"""HTTP tests for /projects/.../ocr-export."""

from __future__ import annotations

import httpx
import pytest

from tests.api._m4_fixtures import make_page_block_segment


def _pflichtfragen() -> dict[str, object]:
    return {
        "page_range": [1],
        "block_types_enabled": ["main_text"],
        "markings_enabled": False,
        "mode": "endgueltig",
    }


@pytest.mark.asyncio
class TestOcrExport:
    async def test_gate_empty_project_exportierbar(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        r = await auth_client.post(
            f"/projects/{project_uuid}/ocr-export/gate", json=_pflichtfragen()
        )
        assert r.status_code == 200
        body = r.json()
        # Empty project: no F-codes, no conflicts, complete pflichtfragen → exportierbar.
        assert body["state"] == "exportierbar"
        assert body["blocking_reasons"] == []

    async def test_confirm_writes_de(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        r = await auth_client.post(
            f"/projects/{project_uuid}/ocr-export/confirm",
            json={
                "pflichtfragen": _pflichtfragen(),
                "export_attempt_id": "attempt-1",
            },
        )
        assert r.status_code == 201
        assert "decision_event_uuid" in r.json()

    async def test_run_full_flow(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        # Seed at least one segment so the DOCX has content.
        await make_page_block_segment(project_uuid, text="بسم الله")
        # Confirm Pflichtfragen first.
        r = await auth_client.post(
            f"/projects/{project_uuid}/ocr-export/confirm",
            json={
                "pflichtfragen": _pflichtfragen(),
                "export_attempt_id": "attempt-2",
            },
        )
        assert r.status_code == 201
        # Now run.
        r = await auth_client.post(
            f"/projects/{project_uuid}/ocr-export/run",
            json={
                "pflichtfragen": _pflichtfragen(),
                "export_attempt_id": "attempt-2",
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["job_state"] == "completed"
        assert body["n_pages_exported"] == 1
        assert body["n_segments_exported"] == 1

        # Download the artefact.
        po_uuid = body["ocr_export_event_po_uuid"]
        r = await auth_client.get(f"/ocr-export/artefacts/{po_uuid}")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert len(r.content) > 0
