"""HTTP integration tests for /uploads/*."""

from __future__ import annotations

import io

import httpx
import pytest
from pypdf import PdfWriter

from waraq.identity import new_uuid


def _make_pdf_bytes(num_pages: int) -> bytes:
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _chunk_bytes(data: bytes, n: int) -> list[bytes]:
    return [data[i : i + n] for i in range(0, len(data), n)]


@pytest.mark.asyncio
class TestUploadFlow:
    async def test_full_upload_lifecycle(self, auth_client: httpx.AsyncClient) -> None:
        # 1. Create a project.
        resp = await auth_client.post("/projects", json={"name": "Upload Test"})
        project_uuid = resp.json()["project_uuid"]

        # 2. Start upload.
        pdf = _make_pdf_bytes(3)
        chunks = _chunk_bytes(pdf, 256)
        resp = await auth_client.post(
            "/uploads",
            json={
                "project_uuid": project_uuid,
                "original_filename": "test.pdf",
                "total_chunks": len(chunks),
                "total_size_bytes": len(pdf),
            },
        )
        assert resp.status_code == 201
        job_uuid = resp.json()["job_uuid"]

        # 3. Send chunks.
        for i, c in enumerate(chunks):
            resp = await auth_client.post(
                f"/uploads/{job_uuid}/chunks/{i}",
                files={"chunk": ("chunk", c, "application/octet-stream")},
            )
            assert resp.status_code == 204, resp.text

        # 4. Status.
        resp = await auth_client.get(f"/uploads/{job_uuid}")
        assert resp.status_code == 200
        st = resp.json()
        assert st["received_chunks"] == st["total_chunks"]
        assert st["expected_next_chunk"] is None

        # 5. Finalize.
        resp = await auth_client.post(f"/uploads/{job_uuid}/finalize")
        assert resp.status_code == 200
        body = resp.json()
        assert body["page_count"] == 3
        assert len(body["page_uuids"]) == 3
        assert body["state"] == "completed"
        assert len(body["source_sha256"]) == 64

    async def test_out_of_order_chunk_returns_409(self, auth_client: httpx.AsyncClient) -> None:
        resp = await auth_client.post("/projects", json={"name": "OOO Test"})
        project_uuid = resp.json()["project_uuid"]

        resp = await auth_client.post(
            "/uploads",
            json={
                "project_uuid": project_uuid,
                "original_filename": "x.pdf",
                "total_chunks": 3,
                "total_size_bytes": 30,
            },
        )
        job_uuid = resp.json()["job_uuid"]

        # Send chunk 2 first.
        resp = await auth_client.post(
            f"/uploads/{job_uuid}/chunks/2",
            files={"chunk": ("chunk", b"x" * 10, "application/octet-stream")},
        )
        assert resp.status_code == 409

    async def test_finalize_incomplete_returns_409(self, auth_client: httpx.AsyncClient) -> None:
        resp = await auth_client.post("/projects", json={"name": "Inc Test"})
        project_uuid = resp.json()["project_uuid"]

        pdf = _make_pdf_bytes(1)
        chunks = _chunk_bytes(pdf, 256)
        resp = await auth_client.post(
            "/uploads",
            json={
                "project_uuid": project_uuid,
                "original_filename": "x.pdf",
                "total_chunks": len(chunks),
                "total_size_bytes": len(pdf),
            },
        )
        job_uuid = resp.json()["job_uuid"]

        # Send only the first chunk.
        await auth_client.post(
            f"/uploads/{job_uuid}/chunks/0",
            files={"chunk": ("chunk", chunks[0], "application/octet-stream")},
        )

        resp = await auth_client.post(f"/uploads/{job_uuid}/finalize")
        assert resp.status_code == 409

    async def test_unauthenticated_returns_401(self, http_client: httpx.AsyncClient) -> None:
        resp = await http_client.post(
            "/uploads",
            json={
                "project_uuid": str(new_uuid()),
                "original_filename": "x.pdf",
                "total_chunks": 1,
                "total_size_bytes": 1,
            },
        )
        assert resp.status_code == 401

    async def test_other_users_upload_returns_404(self, auth_client: httpx.AsyncClient) -> None:
        # Random non-existent job_uuid.
        resp = await auth_client.get(f"/uploads/{new_uuid()}")
        assert resp.status_code == 404
