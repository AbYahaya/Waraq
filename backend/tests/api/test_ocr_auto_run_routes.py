"""HTTP tests for the M5-closeout OCR auto-run endpoints:

- POST /ocr/pages/{page_uuid}/auto-run     (single-page rasterize+OCR)
- POST /ocr/projects/{project_uuid}/auto-run  (bulk over all ausstehend pages)

Tests stub `run_ocr_for_page` in the router module so no Gemini or
poppler is invoked. The router's job (auth, error mapping,
ausstehend-only filter) is what's under test.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import UTC
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

    async def test_refuses_when_page_already_ocrd(
        self,
        auth_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Per the OCR duplicate-Block fix (migration 0023): the
        per-page auto-run endpoint refuses 409 when the page is past
        the `ausstehend` state. Re-running OCR on an already-OCR'd
        page must go through an explicit reset path, not silently
        produce a duplicate Block."""
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

        monkeypatch.setattr(router_mod, "run_ocr_for_page", _stub_result_factory("x"))

        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]

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
                        ocr_status=OcrStatus.IN_REVIEW,
                    )
                )
        finally:
            await engine.dispose()

        r = await auth_client.post(f"/ocr/pages/{page_uuid}/auto-run")
        assert r.status_code == 409, r.text
        body = r.json()
        assert body["detail"]["reason"] == "page_already_ocrd"
        assert body["detail"]["ocr_status"] == "in_review"

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
    async def test_returns_202_with_total_ausstehend_pages(
        self,
        auth_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Sub-batch O — endpoint now returns 202 + Job UUID + the
        snapshot count of ausstehend pages. The BackgroundTask runs
        the actual loop; service-level tests in test_ocr_auto_run.py
        exercise the per-page progress + completion. Here we verify
        the 202 contract and the upfront page snapshot count."""
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

        # Stub run_ocr_for_page so the BackgroundTask doesn't try to
        # actually call Gemini. The task may still run after this test
        # returns; the stub keeps it from blowing up.
        monkeypatch.setattr(router_mod, "run_ocr_for_page", _stub_result_factory("ok"))

        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]

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
        assert r.status_code == 202, r.text
        body = r.json()
        assert body["state"] == "pending"
        # 2 ausstehend pages; the GO page is not in the snapshot total.
        assert body["total_pages"] == 2
        assert "ocr_job_uuid" in body

    async def test_unknown_project_returns_404(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.post(f"/ocr/projects/{_uuid.uuid4()}/auto-run")
        assert r.status_code == 404

    async def test_silence_when_no_pages(
        self,
        auth_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Sub-batch O — empty project still returns 202; total_pages=0
        means the BackgroundTask transitions PENDING → RUNNING →
        COMPLETED almost immediately. Just verify the 202 + zero
        snapshot."""
        _ = monkeypatch  # nothing to patch; no run_ocr_for_page calls
        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        r = await auth_client.post(f"/ocr/projects/{project_uuid}/auto-run")
        assert r.status_code == 202
        body = r.json()
        assert body["total_pages"] == 0
        assert body["state"] == "pending"


@pytest.mark.asyncio
class TestStatusEndpointSelfHeals:
    """Sub-batch O follow-up (2026-05-12) — `GET /ocr/ocr-jobs/{u}`
    self-heals a stale RUNNING row whose worker process died. Without
    this, the UI would poll a zombie row forever (the "Cancelling…
    for 20 hours" failure mode).
    """

    async def test_stale_running_job_is_reaped_on_poll(
        self,
        auth_client: httpx.AsyncClient,
    ) -> None:
        from datetime import datetime, timedelta

        from sqlalchemy import text as sql_text
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.conftest import _test_database_url
        from waraq.identity import new_uuid
        from waraq.ocr.auto_run import (
            OCR_AUTO_RUN_JOB_TYPE,
            STALE_HEARTBEAT_THRESHOLD_SECONDS,
        )
        from waraq.schemas import Job

        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        job_uuid = new_uuid()
        try:
            async with sm() as session, session.begin():
                session.add(
                    Job(
                        job_uuid=job_uuid,
                        job_type=OCR_AUTO_RUN_JOB_TYPE,
                        state="running",
                        project_uuid=_uuid.UUID(project_uuid),
                        payload={
                            "total_pages": 2,
                            "processed_count": 1,
                            "cancel_requested": False,
                        },
                    )
                )
                await session.flush()
                past = datetime.now(UTC) - timedelta(seconds=STALE_HEARTBEAT_THRESHOLD_SECONDS + 60)
                await session.execute(
                    sql_text("UPDATE jobs SET updated_at = :ts WHERE job_uuid = :u"),
                    {"ts": past, "u": job_uuid},
                )
        finally:
            await engine.dispose()

        r = await auth_client.get(f"/ocr/ocr-jobs/{job_uuid}")
        assert r.status_code == 200, r.text
        body = r.json()
        # The poll triggers the self-heal; state should now be 'failed'.
        assert body["state"] == "failed"
        assert body["last_error"]["phase"] == "server_restart_orphan"

    async def test_fresh_running_job_is_not_reaped(
        self,
        auth_client: httpx.AsyncClient,
    ) -> None:
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.conftest import _test_database_url
        from waraq.identity import new_uuid
        from waraq.ocr.auto_run import OCR_AUTO_RUN_JOB_TYPE
        from waraq.schemas import Job

        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        job_uuid = new_uuid()
        try:
            async with sm() as session, session.begin():
                session.add(
                    Job(
                        job_uuid=job_uuid,
                        job_type=OCR_AUTO_RUN_JOB_TYPE,
                        state="running",
                        project_uuid=_uuid.UUID(project_uuid),
                        payload={"total_pages": 2, "processed_count": 1},
                    )
                )
        finally:
            await engine.dispose()

        r = await auth_client.get(f"/ocr/ocr-jobs/{job_uuid}")
        assert r.status_code == 200, r.text
        body = r.json()
        # updated_at is fresh — no reap.
        assert body["state"] == "running"

    async def test_in_flight_endpoint_reaps_fresh_cancel_requested_job(
        self,
        auth_client: httpx.AsyncClient,
    ) -> None:
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.conftest import _test_database_url
        from waraq.identity import new_uuid
        from waraq.ocr.auto_run import OCR_AUTO_RUN_JOB_TYPE
        from waraq.schemas import Job

        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        job_uuid = new_uuid()
        try:
            async with sm() as session, session.begin():
                session.add(
                    Job(
                        job_uuid=job_uuid,
                        job_type=OCR_AUTO_RUN_JOB_TYPE,
                        state="running",
                        project_uuid=_uuid.UUID(project_uuid),
                        payload={
                            "total_pages": 2,
                            "processed_count": 1,
                            "cancel_requested": True,
                        },
                    )
                )
        finally:
            await engine.dispose()

        r = await auth_client.get(f"/ocr/projects/{project_uuid}/ocr-jobs/in-flight")
        assert r.status_code == 200, r.text
        assert r.json() is None


@pytest.mark.asyncio
class TestUniqueActiveIndexes:
    """Migration 0023 — `(page_uuid, block_index)` and `(block_uuid,
    satz_index)` are UNIQUE per-active-row. Defence-in-depth so a
    regressed application path can't silently duplicate either row."""

    async def test_duplicate_active_block_is_blocked_at_db_level(
        self,
        auth_client: httpx.AsyncClient,
    ) -> None:
        from sqlalchemy.exc import IntegrityError
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.conftest import _test_database_url
        from waraq.identity import new_uuid
        from waraq.schemas import Block, Page

        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        page_uuid = new_uuid()
        try:
            # Seed Page + first Block. SQLAlchemy's UoW orders inserts
            # by relationship, not by raw FK column — flush Page first
            # so the Block insert sees a row to FK to.
            async with sm() as session:
                session.add(
                    Page(
                        page_uuid=page_uuid,
                        project_uuid=_uuid.UUID(project_uuid),
                        page_index=1,
                    )
                )
                await session.flush()
                session.add(
                    Block(
                        block_uuid=new_uuid(),
                        page_uuid=page_uuid,
                        block_type="main_text",
                        block_index=0,
                    )
                )
                await session.commit()
            # Second active Block at the same (page_uuid, block_index)
            # — the partial unique index must reject this insert.
            with pytest.raises(IntegrityError):
                async with sm() as session:
                    session.add(
                        Block(
                            block_uuid=new_uuid(),
                            page_uuid=page_uuid,
                            block_type="main_text",
                            block_index=0,
                        )
                    )
                    await session.commit()
        finally:
            await engine.dispose()

    async def test_inactive_duplicate_block_is_allowed(
        self,
        auth_client: httpx.AsyncClient,
    ) -> None:
        """An inactivated row must NOT collide with a new active one —
        the WHERE active=true predicate on the index is essential to
        the inactivate-then-recreate recovery path."""
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.conftest import _test_database_url
        from waraq.identity import new_uuid
        from waraq.schemas import Block, Page

        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        page_uuid = new_uuid()
        try:
            async with sm() as session:
                session.add(
                    Page(
                        page_uuid=page_uuid,
                        project_uuid=_uuid.UUID(project_uuid),
                        page_index=1,
                    )
                )
                await session.flush()
                session.add(
                    Block(
                        block_uuid=new_uuid(),
                        page_uuid=page_uuid,
                        block_type="main_text",
                        block_index=0,
                        active=False,
                    )
                )
                await session.commit()
            async with sm() as session:
                session.add(
                    Block(
                        block_uuid=new_uuid(),
                        page_uuid=page_uuid,
                        block_type="main_text",
                        block_index=0,
                        active=True,
                    )
                )
                await session.commit()
        finally:
            await engine.dispose()


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
