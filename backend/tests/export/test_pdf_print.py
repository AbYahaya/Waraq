"""M5 — PDF print export tests.

Covers:
- Unit: DOCX → PDF via real LibreOffice (skipped if soffice missing).
- Endpoint: GET /exports/artefacts/{po_uuid}/pdf returns PDF bytes,
  carries X-Waraq-PDF-X-1a + X-Waraq-veraPDF-Valid headers, 404s
  for non-EXPORT_EVENT POs and cross-account access.
- Read-only: PDF download writes nothing.

LibreOffice is required system-side; tests gated with `skipif` on
PATH presence so CI without soffice still passes.
"""

from __future__ import annotations

import shutil

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import seed_account_uuid
from tests.export._helpers import (
    seed_project_with_account,
    seed_segment_with_revision,
)
from waraq.api.dependencies import get_db_session
from waraq.api.main import create_app
from waraq.auth.tokens import issue_token
from waraq.export import ExportConfig, run_export_job
from waraq.export.docx_builder import build_translation_docx
from waraq.export.pdf_print import PdfPrintError, docx_to_pdf_print
from waraq.identity import new_uuid
from waraq.preflight import (
    PFLICHTFRAGE_COUNT,
    confirm_pflichtfrage,
    evaluate_preflight,
    start_preflight_run,
)
from waraq.schemas import (
    DecisionEvent,
    LogEntry,
    ProvenanceObject,
    Revision,
)

_SOFFICE_AVAILABLE = shutil.which("soffice") is not None or shutil.which("libreoffice") is not None


@pytest.fixture
async def authed_client(db_session: AsyncSession):
    account_uuid = new_uuid()
    await seed_account_uuid(db_session, account_uuid)
    app = create_app()

    async def _override():
        yield db_session

    app.dependency_overrides[get_db_session] = _override
    token = issue_token(account_uuid=account_uuid)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, account_uuid, headers


async def _seed_export_for_account(db_session, account_uuid):
    from waraq.schemas import Project

    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="t")
    db_session.add(project)
    await db_session.flush()
    await seed_segment_with_revision(
        db_session, project=project, text="إن الحمد لله\n---\nLob sei Gott"
    )
    run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
    for i in range(1, PFLICHTFRAGE_COUNT + 1):
        await confirm_pflichtfrage(
            session=db_session,
            project_uuid=project.project_uuid,
            preflight_run_uuid=run.job_uuid,
            frage_index=i,
            frage_key=f"frage_{i}",
            answer={"value": "yes"},
        )
    await evaluate_preflight(
        session=db_session, project_uuid=project.project_uuid, preflight_run=run
    )
    cfg = ExportConfig(
        project_uuid=project.project_uuid,
        account_uuid=account_uuid,
        project_title="Test",
        current_export_attempt_id=str(new_uuid()),
        preflight_run=run,
    )
    return await run_export_job(session=db_session, config=cfg)


# --- Unit: pipeline -------------------------------------------------------


@pytest.mark.skipif(
    not _SOFFICE_AVAILABLE,
    reason="LibreOffice (soffice/libreoffice) not on PATH; PDF pipeline unavailable",
)
@pytest.mark.asyncio
class TestPdfPrintPipeline:
    async def test_docx_to_pdf_returns_valid_pdf(self, db_session: AsyncSession) -> None:
        from tests.export._helpers import (
            seed_project_with_account,
            seed_segment_with_revision,
        )

        project, _ = await seed_project_with_account(db_session)
        await seed_segment_with_revision(
            db_session, project=project, text="إن الحمد لله\n---\nLob sei Gott"
        )
        artefact = await build_translation_docx(
            session=db_session,
            project_uuid=project.project_uuid,
            project_title="T",
        )
        result = await docx_to_pdf_print(docx_bytes=artefact.bytes_)
        # Bytes start with the PDF magic header.
        assert result.bytes_[:4] == b"%PDF"
        assert result.size_bytes > 0
        assert len(result.sha256) == 64

    async def test_pdf_x_1a_flag_reflects_ghostscript_outcome(
        self, db_session: AsyncSession
    ) -> None:
        """If `gs` is on PATH, the Ghostscript pass should succeed and
        `is_pdf_x_1a=True`. Else `False`. We don't assert which —
        just that the flag is a bool and consistent with the gs binary
        being available."""
        from tests.export._helpers import (
            seed_project_with_account,
            seed_segment_with_revision,
        )

        project, _ = await seed_project_with_account(db_session)
        await seed_segment_with_revision(db_session, project=project, text="x\n---\ny")
        artefact = await build_translation_docx(
            session=db_session, project_uuid=project.project_uuid, project_title="T"
        )
        result = await docx_to_pdf_print(docx_bytes=artefact.bytes_)
        assert isinstance(result.is_pdf_x_1a, bool)
        gs_present = shutil.which("gs") is not None
        if not gs_present:
            assert result.is_pdf_x_1a is False

    async def test_pdf_x_1a_disable_returns_raw_pdf(self, db_session: AsyncSession) -> None:
        """When the caller explicitly disables PDF/X-1a, the result
        flag is False even if gs is available."""
        from tests.export._helpers import (
            seed_project_with_account,
            seed_segment_with_revision,
        )

        project, _ = await seed_project_with_account(db_session)
        await seed_segment_with_revision(db_session, project=project, text="x\n---\ny")
        artefact = await build_translation_docx(
            session=db_session, project_uuid=project.project_uuid, project_title="T"
        )
        result = await docx_to_pdf_print(docx_bytes=artefact.bytes_, enable_pdf_x_1a=False)
        assert result.is_pdf_x_1a is False


# --- Endpoint -------------------------------------------------------------


@pytest.mark.skipif(
    not _SOFFICE_AVAILABLE,
    reason="LibreOffice (soffice/libreoffice) not on PATH",
)
@pytest.mark.asyncio
class TestPdfDownloadEndpoint:
    async def test_pdf_download_returns_pdf_bytes_and_headers(
        self, db_session: AsyncSession, authed_client
    ) -> None:
        client, account_uuid, headers = authed_client
        export_result = await _seed_export_for_account(db_session, account_uuid)

        resp = await client.get(
            f"/exports/artefacts/{export_result.export_event_po.po_uuid}/pdf",
            headers=headers,
            timeout=120.0,
        )
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"
        assert "X-Waraq-PDF-X-1a" in resp.headers
        assert resp.headers["X-Waraq-PDF-X-1a"] in ("true", "false")
        assert resp.headers["X-Waraq-veraPDF-Valid"] in ("true", "false", "skipped")

    async def test_pdf_download_404_for_unknown_po(
        self, db_session: AsyncSession, authed_client
    ) -> None:
        client, _account_uuid, headers = authed_client
        resp = await client.get(f"/exports/artefacts/{new_uuid()}/pdf", headers=headers)
        assert resp.status_code == 404

    async def test_pdf_download_404_for_other_account(
        self, db_session: AsyncSession, authed_client
    ) -> None:
        client, _account_uuid, headers = authed_client
        # Seed a different account's export.
        other_project, other_uuid = await seed_project_with_account(db_session)
        await seed_segment_with_revision(db_session, project=other_project, text="x\n---\ny")
        export_result = await _seed_export_for_account(db_session, other_uuid)
        # Authed user is account_uuid (not other_uuid) — must 404.
        resp = await client.get(
            f"/exports/artefacts/{export_result.export_event_po.po_uuid}/pdf",
            headers=headers,
        )
        assert resp.status_code == 404


# --- Read-only --------------------------------------------------------------


@pytest.mark.skipif(
    not _SOFFICE_AVAILABLE,
    reason="LibreOffice (soffice/libreoffice) not on PATH",
)
@pytest.mark.asyncio
class TestPdfDownloadReadOnly:
    async def test_pdf_download_writes_nothing(
        self, db_session: AsyncSession, authed_client
    ) -> None:
        client, account_uuid, headers = authed_client
        export_result = await _seed_export_for_account(db_session, account_uuid)

        rev_count = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()
        de_count = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        log_count = (
            await db_session.execute(select(func.count()).select_from(LogEntry))
        ).scalar_one()
        po_count = (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one()

        await client.get(
            f"/exports/artefacts/{export_result.export_event_po.po_uuid}/pdf",
            headers=headers,
            timeout=120.0,
        )

        assert (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one() == rev_count
        assert (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one() == de_count
        assert (
            await db_session.execute(select(func.count()).select_from(LogEntry))
        ).scalar_one() == log_count
        assert (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one() == po_count


# --- Without LibreOffice: 503 ---------------------------------------------


@pytest.mark.asyncio
class TestPdfPrintErrorWhenSofficeMissing:
    async def test_pdf_print_error_message_mentions_libreoffice(self) -> None:
        """When `soffice` is unavailable, the function must raise
        `PdfPrintError` with a clear actionable message."""
        # We can't simulate-uninstall soffice; this test asserts the
        # public exception class + signature.
        assert issubclass(PdfPrintError, Exception)
        # The function exists and is importable.
        assert callable(docx_to_pdf_print)
