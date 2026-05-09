"""HTTP integration tests for /pages and /segments routers."""

from __future__ import annotations

import httpx
import pytest

from tests.api._m4_fixtures import make_page_block_segment
from waraq.identity import new_uuid


@pytest.mark.asyncio
class TestPagesAndSegments:
    async def _project(self, auth_client: httpx.AsyncClient) -> str:
        r = await auth_client.post("/projects", json={"name": "p1"})
        assert r.status_code == 201
        return r.json()["project_uuid"]

    async def test_list_pages_empty_project(self, auth_client: httpx.AsyncClient) -> None:
        project_uuid = await self._project(auth_client)
        r = await auth_client.get(f"/projects/{project_uuid}/pages")
        assert r.status_code == 200
        assert r.json() == []

    async def test_list_pages_after_seeding(self, auth_client: httpx.AsyncClient) -> None:
        project_uuid = await self._project(auth_client)
        f = await make_page_block_segment(project_uuid)
        r = await auth_client.get(f"/projects/{project_uuid}/pages")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 1
        assert rows[0]["page_uuid"] == str(f.page_uuid)

    async def test_list_segments_in_page(self, auth_client: httpx.AsyncClient) -> None:
        project_uuid = await self._project(auth_client)
        f = await make_page_block_segment(project_uuid)
        r = await auth_client.get(f"/pages/{f.page_uuid}/segments")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 1
        assert rows[0]["satz_uuid"] == str(f.satz_uuid)
        assert rows[0]["lock_flag"] == "none"

    async def test_get_segment(self, auth_client: httpx.AsyncClient) -> None:
        project_uuid = await self._project(auth_client)
        f = await make_page_block_segment(project_uuid, text="hello")
        r = await auth_client.get(f"/segments/{f.satz_uuid}")
        assert r.status_code == 200
        assert r.json()["text_content"] == "hello"

    async def test_edit_segment_text(self, auth_client: httpx.AsyncClient) -> None:
        project_uuid = await self._project(auth_client)
        f = await make_page_block_segment(project_uuid, text="old")
        r = await auth_client.put(f"/segments/{f.satz_uuid}/text", json={"after_text": "new"})
        assert r.status_code == 200
        body = r.json()
        assert body["text_content"] == "new"
        assert body["current_rev_uuid"] is not None

    async def test_cross_account_returns_404(self, auth_client: httpx.AsyncClient) -> None:
        # Random uuid → 404
        r = await auth_client.get(f"/segments/{new_uuid()}")
        assert r.status_code == 404

    async def test_unauthenticated_calls_blocked(self, http_client: httpx.AsyncClient) -> None:
        r = await http_client.get(f"/pages/{new_uuid()}/segments")
        assert r.status_code == 401


@pytest.mark.asyncio
class TestSourcePdf:
    """Day 3 — `/pages/{page_uuid}/source-pdf` streams the source PDF
    for a page. Used by the in-browser scan viewer.

    Materialization happens via the canonical chunked-upload flow so a
    real SCAN-PO row is written by the upload service (the M4 endpoint
    just looks it up)."""

    async def test_returns_pdf_for_uploaded_page(self, auth_client: httpx.AsyncClient) -> None:
        import io as _io

        from pypdf import PdfWriter

        # Build a tiny 2-page PDF and upload via the canonical flow.
        writer = PdfWriter()
        for _ in range(2):
            writer.add_blank_page(width=612, height=792)
        buf = _io.BytesIO()
        writer.write(buf)
        pdf = buf.getvalue()
        chunks = [pdf[i : i + 256] for i in range(0, len(pdf), 256)]

        r = await auth_client.post("/projects", json={"name": "ScanViewer Test"})
        project_uuid = r.json()["project_uuid"]
        r = await auth_client.post(
            "/uploads",
            json={
                "project_uuid": project_uuid,
                "original_filename": "scans.pdf",
                "total_chunks": len(chunks),
                "total_size_bytes": len(pdf),
            },
        )
        job_uuid = r.json()["job_uuid"]
        for i, c in enumerate(chunks):
            await auth_client.post(
                f"/uploads/{job_uuid}/chunks/{i}",
                files={"chunk": ("c", c, "application/octet-stream")},
            )
        r = await auth_client.post(f"/uploads/{job_uuid}/finalize")
        page_uuids = r.json()["page_uuids"]

        # Stream the PDF for page 1.
        r = await auth_client.get(f"/pages/{page_uuids[0]}/source-pdf")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"] == "application/pdf"
        assert r.headers["content-disposition"].startswith("inline")
        # First-bytes sanity check.
        assert r.content[:5] == b"%PDF-"
        assert len(r.content) == len(pdf)

    async def test_404_for_unknown_page(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.get(f"/pages/{new_uuid()}/source-pdf")
        assert r.status_code == 404

    async def test_404_when_page_has_no_scan_po(self, auth_client: httpx.AsyncClient) -> None:
        # A page seeded directly via _m4_fixtures has no SCAN-PO.
        r = await auth_client.post("/projects", json={"name": "NoScan"})
        f = await make_page_block_segment(r.json()["project_uuid"])
        r = await auth_client.get(f"/pages/{f.page_uuid}/source-pdf")
        assert r.status_code == 404
