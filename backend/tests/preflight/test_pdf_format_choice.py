"""Phase 3 sub-batch A — §4.7.2 PDF format choice tests.

PDF Digital (RGB) vs Print (PDF/X-1a) is a Configuration-Layer choice
separate from the four canonical Pflichtfragen.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project
from waraq.preflight import (
    PdfFormatChoice,
    confirm_pdf_format_choice,
    read_pdf_format_choice,
    start_preflight_run,
)
from waraq.schemas import DecisionEvent
from waraq.schemas.enums import DecisionSource, ScopeType


@pytest.mark.asyncio
class TestConfirmPdfFormatChoice:
    async def test_confirm_writes_decision_event(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)

        de = await confirm_pdf_format_choice(
            session=db_session,
            project_uuid=project.project_uuid,
            preflight_run_uuid=run.job_uuid,
            choice=PdfFormatChoice.DIGITAL_RGB,
        )
        assert de.decision_type == "pdf_format_choice"
        assert de.decision_source == DecisionSource.PREFLIGHT_CONFIRMATION.value
        assert de.scope_type == ScopeType.PROJECT.value
        assert de.related_export_attempt_id == str(run.job_uuid)
        assert de.content["choice"] == PdfFormatChoice.DIGITAL_RGB.value

    async def test_both_canonical_values_supported(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        for choice in (PdfFormatChoice.DIGITAL_RGB, PdfFormatChoice.PRINT_PDF_X_1A):
            de = await confirm_pdf_format_choice(
                session=db_session,
                project_uuid=project.project_uuid,
                preflight_run_uuid=run.job_uuid,
                choice=choice,
            )
            assert de.content["choice"] == choice.value


@pytest.mark.asyncio
class TestReadPdfFormatChoice:
    async def test_unset_returns_none(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        choice = await read_pdf_format_choice(
            session=db_session,
            project_uuid=project.project_uuid,
            preflight_run_uuid=run.job_uuid,
        )
        assert choice is None

    async def test_returns_latest_choice(self, db_session: AsyncSession) -> None:
        """User is allowed to change their mind — latest DE wins."""
        from datetime import UTC, datetime, timedelta

        project = await seed_project(db_session)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)

        de_first = await confirm_pdf_format_choice(
            session=db_session,
            project_uuid=project.project_uuid,
            preflight_run_uuid=run.job_uuid,
            choice=PdfFormatChoice.DIGITAL_RGB,
        )
        de_second = await confirm_pdf_format_choice(
            session=db_session,
            project_uuid=project.project_uuid,
            preflight_run_uuid=run.job_uuid,
            choice=PdfFormatChoice.PRINT_PDF_X_1A,
        )
        # Postgres `now()` is transaction-frozen; in production each
        # confirm runs in its own transaction so timestamps differ
        # naturally. Inside the test fixture transaction we have to
        # nudge them by hand.
        de_first.created_at = datetime.now(UTC)
        de_second.created_at = datetime.now(UTC) + timedelta(seconds=1)
        await db_session.flush()

        choice = await read_pdf_format_choice(
            session=db_session,
            project_uuid=project.project_uuid,
            preflight_run_uuid=run.job_uuid,
        )
        assert choice == PdfFormatChoice.PRINT_PDF_X_1A

        # Both Decision Events still on file (no supersession at the row level).
        rows = (
            (
                await db_session.execute(
                    select(DecisionEvent)
                    .where(DecisionEvent.scope_uuid == project.project_uuid)
                    .where(DecisionEvent.decision_type == "pdf_format_choice")
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 2

    async def test_run_isolation(self, db_session: AsyncSession) -> None:
        """A choice on run A must not leak into run B's read."""
        project = await seed_project(db_session)
        run_a = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        run_b = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)

        await confirm_pdf_format_choice(
            session=db_session,
            project_uuid=project.project_uuid,
            preflight_run_uuid=run_a.job_uuid,
            choice=PdfFormatChoice.PRINT_PDF_X_1A,
        )
        # Run B has no choice yet.
        b_choice = await read_pdf_format_choice(
            session=db_session,
            project_uuid=project.project_uuid,
            preflight_run_uuid=run_b.job_uuid,
        )
        assert b_choice is None
        a_choice = await read_pdf_format_choice(
            session=db_session,
            project_uuid=project.project_uuid,
            preflight_run_uuid=run_a.job_uuid,
        )
        assert a_choice == PdfFormatChoice.PRINT_PDF_X_1A
