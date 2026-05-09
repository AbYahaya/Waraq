"""HTTP tests for the M5-closeout OCR auto-run endpoints:

- POST /ocr/pages/{page_uuid}/auto-run     (single-page rasterize+OCR)
- POST /ocr/projects/{project_uuid}/auto-run  (bulk over all ausstehend pages)

Tests stub `run_ocr_for_page` in the router module so no Gemini or
poppler is invoked. The router's job (auth, error mapping,
ausstehend-only filter) is what's under test.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

import httpx
import pytest

from tests.api._m4_fixtures import make_page_block_segment


async def _make_page_for(project_uuid: str) -> _uuid.UUID:
    """Insert one Page (no Block, no Segment) so the auto-run helper
    has to provision them."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from tests.conftest import _test_database_url
    from waraq.identity import new_uuid
    from waraq.schemas import Page

    engine = create_async_engine(_test_database_url(), future=True)
    sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    page_uuid = new_uuid()
    try:
        async with sm() as session, session.begin():
            session.add(
                Page(
                    page_uuid=page_uuid,
                    project_uuid=_uuid.UUID(project_uuid),
                    page_index=1,
                )
            )
            await session.flush()
    finally:
        await engine.dispose()
    return page_uuid


def _stub_result_factory(text: str = "بسم الله") -> Any:
    """Returns an async function with the same signature as
    `run_ocr_for_page` that returns a fixed result."""
    from waraq.ocr.page_runner import PageOcrResult

    async def _stub(*, session: Any, page: Any) -> PageOcrResult:
        from waraq.identity import new_uuid

        return PageOcrResult(
            page_uuid=page.page_uuid,
            text=text,
            text_chars=len(text),
            text_changed=True,
            segment_uuid=new_uuid(),
            block_uuid=new_uuid(),
            rev_uuid=new_uuid(),
        )

    return _stub


@pytest.mark.asyncio
class TestAutoRunPage:
    async def test_happy_path_returns_text_and_segment(
        self,
        auth_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from waraq.api.routers import ocr_router as router_mod

        monkeypatch.setattr(router_mod, "run_ocr_for_page", _stub_result_factory("بسم الله"))
        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        page_uuid = await _make_page_for(project_uuid)

        r = await auth_client.post(f"/ocr/pages/{page_uuid}/auto-run")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["text"] == "بسم الله"
        assert body["text_chars"] == len("بسم الله")
        assert body["page_uuid"] == str(page_uuid)
        assert body["segment_uuid"]
        assert body["rev_uuid"]

    async def test_unknown_page_returns_404(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.post(f"/ocr/pages/{_uuid.uuid4()}/auto-run")
        assert r.status_code == 404

    async def test_other_account_page_returns_404(
        self,
        auth_client: httpx.AsyncClient,
    ) -> None:
        # Insert a page under a project belonging to a different account.
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.conftest import _test_database_url
        from waraq.identity import new_uuid
        from waraq.schemas import Account, Page, Project

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        other_page = new_uuid()
        try:
            async with sm() as session, session.begin():
                acct = Account(
                    account_uuid=new_uuid(),
                    email=f"other-{new_uuid()}@waraq.test",
                    password_hash="x",
                    active=True,
                )
                session.add(acct)
                await session.flush()
                proj = Project(
                    project_uuid=new_uuid(), account_uuid=acct.account_uuid, name="other"
                )
                session.add(proj)
                await session.flush()
                session.add(
                    Page(
                        page_uuid=other_page,
                        project_uuid=proj.project_uuid,
                        page_index=1,
                    )
                )
        finally:
            await engine.dispose()

        r = await auth_client.post(f"/ocr/pages/{other_page}/auto-run")
        assert r.status_code == 404

    async def test_page_ocr_error_maps_to_409(
        self,
        auth_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from waraq.api.routers import ocr_router as router_mod
        from waraq.ocr.page_runner import PageOcrError

        async def _raise(**_kw: Any) -> Any:
            raise PageOcrError("No SCAN-PO for page (was the upload finalized?)")

        monkeypatch.setattr(router_mod, "run_ocr_for_page", _raise)

        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        page_uuid = await _make_page_for(project_uuid)

        r = await auth_client.post(f"/ocr/pages/{page_uuid}/auto-run")
        assert r.status_code == 409
        assert "SCAN-PO" in r.json()["detail"]


@pytest.mark.asyncio
class TestAutoRunProject:
    async def test_runs_only_ausstehend_pages(
        self,
        auth_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.conftest import _test_database_url
        from waraq.api.routers import ocr_router as router_mod
        from waraq.identity import new_uuid
        from waraq.schemas import Page
        from waraq.schemas.enums import OcrStatus

        monkeypatch.setattr(router_mod, "run_ocr_for_page", _stub_result_factory("ok"))

        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]

        # Seed: 2 ausstehend pages + 1 already-GO page.
        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with sm() as session, session.begin():
                for i, status_v in enumerate(
                    [OcrStatus.AUSSTEHEND, OcrStatus.AUSSTEHEND, OcrStatus.GO], start=1
                ):
                    session.add(
                        Page(
                            page_uuid=new_uuid(),
                            project_uuid=_uuid.UUID(project_uuid),
                            page_index=i,
                            ocr_status=status_v,
                        )
                    )
        finally:
            await engine.dispose()

        r = await auth_client.post(f"/ocr/projects/{project_uuid}/auto-run")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["pages_processed"] == 2
        assert body["pages_skipped"] == 1
        assert len(body["skipped_page_uuids"]) == 1

    async def test_unknown_project_returns_404(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.post(f"/ocr/projects/{_uuid.uuid4()}/auto-run")
        assert r.status_code == 404

    async def test_silence_when_no_pages(
        self,
        auth_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Empty project — no pages — no errors, processed=0.
        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        r = await auth_client.post(f"/ocr/projects/{project_uuid}/auto-run")
        assert r.status_code == 200
        body = r.json()
        assert body["pages_processed"] == 0
        assert body["pages_skipped"] == 0


@pytest.mark.asyncio
class TestPageRunnerIdempotence:
    """The provisioning helper inside page_runner must be idempotent —
    a second auto-run on the same page must reuse the existing Block +
    Segment (per H-5 and Sprint 1 / OCR-Re-Run discipline)."""

    async def test_re_run_uses_existing_segment(self, auth_client: httpx.AsyncClient) -> None:
        # Use the real make_page_block_segment helper to pre-seed a
        # Block + Segment, then check `_ensure_block_and_segment` finds
        # them via a direct unit call.
        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        seeded = await make_page_block_segment(project_uuid, text="initial")

        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.conftest import _test_database_url
        from waraq.ocr.page_runner import _ensure_block_and_segment
        from waraq.schemas import Page

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with sm() as session, session.begin():
                page = await session.get(Page, seeded.page_uuid)
                assert page is not None
                block, segment = await _ensure_block_and_segment(session=session, page=page)
                assert block.block_uuid == seeded.block_uuid
                assert segment.satz_uuid == seeded.satz_uuid
        finally:
            await engine.dispose()
