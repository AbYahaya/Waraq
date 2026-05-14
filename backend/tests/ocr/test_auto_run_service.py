"""Sub-batch O — OCR auto-run BackgroundTask body tests.

Service-level tests for `waraq.ocr.auto_run`:
- `start_ocr_auto_run_job` materializes a PENDING Job with the right
  payload + total snapshot.
- `_execute` walks pages, persists progress between pages, handles a
  cooperative cancel flag, transitions to COMPLETED on clean finish.
- `find_in_flight_for_project` returns the in-flight Job for a project.
- `request_cancel` flips the flag (idempotent, no-op on terminal).

The BackgroundTask entrypoint `run_ocr_auto_run_job_in_background` is
not unit-tested directly here — it opens its own session via a
sessionmaker factory; the inner `_execute` body is what we exercise.
"""

from __future__ import annotations

from datetime import UTC
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project
from waraq.identity import new_uuid
from waraq.ocr.auto_run import (
    OCR_AUTO_RUN_JOB_TYPE,
    STALE_HEARTBEAT_THRESHOLD_SECONDS,
    _execute,
    find_in_flight_for_project,
    reap_orphan_jobs,
    request_cancel,
    start_ocr_auto_run_job,
)
from waraq.schemas import Page
from waraq.schemas.enums import JobState, OcrStatus


async def _seed_page(
    session: AsyncSession,
    project_uuid: Any,
    *,
    page_index: int,
    ocr_status: OcrStatus = OcrStatus.AUSSTEHEND,
) -> Page:
    page = Page(
        page_uuid=new_uuid(),
        project_uuid=project_uuid,
        page_index=page_index,
        ocr_status=ocr_status,
    )
    session.add(page)
    await session.flush()
    return page


@pytest.mark.asyncio
class TestStartOcrAutoRunJob:
    async def test_creates_pending_job_with_snapshot_total(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        await _seed_page(db_session, project.project_uuid, page_index=1)
        await _seed_page(db_session, project.project_uuid, page_index=2)
        # One non-ausstehend page — should NOT be in the snapshot total.
        await _seed_page(
            db_session,
            project.project_uuid,
            page_index=3,
            ocr_status=OcrStatus.GO,
        )
        job = await start_ocr_auto_run_job(session=db_session, project=project)
        assert job.job_type == OCR_AUTO_RUN_JOB_TYPE
        assert job.state == JobState.PENDING.value
        assert job.project_uuid == project.project_uuid
        payload = job.payload or {}
        # Only the two ausstehend pages count.
        assert payload["total_pages"] == 2
        assert payload["processed_count"] == 0
        assert payload["cancel_requested"] is False

    async def test_empty_project_returns_total_zero(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        job = await start_ocr_auto_run_job(session=db_session, project=project)
        assert (job.payload or {})["total_pages"] == 0


# ---------------------------------------------------------------------
# _execute — the inner loop the BackgroundTask invokes
# ---------------------------------------------------------------------


async def _stub_ocr_for_page(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Replace `run_ocr_for_page` in the auto_run module with a stub
    that records call args + flips the page to GO so the next pass
    skips it. Returns the list of pages that were passed in (in
    invocation order)."""
    calls: list[Any] = []

    async def _stub(*, session: AsyncSession, page: Page) -> None:
        calls.append(page.page_uuid)
        # Flip the page to GO so a real test can verify the loop
        # advances; the runner will see the GO state on the next
        # refresh and won't re-process.
        page.ocr_status = OcrStatus.GO
        await session.flush()

    import waraq.ocr.auto_run as mod

    monkeypatch.setattr(mod, "run_ocr_for_page", _stub)
    return calls


@pytest.mark.asyncio
class TestExecuteLoop:
    async def test_completes_when_all_pages_succeed(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project = await seed_project(db_session)
        for i in (1, 2, 3):
            await _seed_page(db_session, project.project_uuid, page_index=i)
        calls = await _stub_ocr_for_page(monkeypatch)
        job = await start_ocr_auto_run_job(session=db_session, project=project)
        await _execute(session=db_session, job=job)

        assert job.state == JobState.COMPLETED.value
        assert len(calls) == 3
        assert (job.payload or {})["processed_count"] == 3
        assert (job.result or {})["processed_count"] == 3

    async def test_cancel_flag_aborts_between_pages(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project = await seed_project(db_session)
        for i in (1, 2, 3):
            await _seed_page(db_session, project.project_uuid, page_index=i)
        # Stub that sets cancel after the FIRST page, simulating a
        # concurrent /cancel call.
        first_done = {"flag": False}

        async def _stub(*, session: AsyncSession, page: Page) -> None:
            page.ocr_status = OcrStatus.GO
            await session.flush()
            if not first_done["flag"]:
                first_done["flag"] = True
                # Simulate the cancel endpoint flipping the flag.
                job_payload = job.payload or {}
                job_payload["cancel_requested"] = True
                from sqlalchemy.orm.attributes import flag_modified

                flag_modified(job, "payload")
                await session.flush()

        import waraq.ocr.auto_run as mod

        monkeypatch.setattr(mod, "run_ocr_for_page", _stub)

        job = await start_ocr_auto_run_job(session=db_session, project=project)
        from waraq.ocr.auto_run import OcrAutoRunCancelled

        with pytest.raises(OcrAutoRunCancelled):
            await _execute(session=db_session, job=job)

        assert job.state == JobState.FAILED.value
        assert (job.error or {})["phase"] == "user_cancelled"
        # First page processed; loop bailed before pages 2 & 3.
        assert (job.error or {})["processed_count"] == 1

    async def test_skips_non_ausstehend_pages(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project = await seed_project(db_session)
        await _seed_page(db_session, project.project_uuid, page_index=1)
        # Already-OCR'd page — should be skipped without invoking the stub.
        await _seed_page(
            db_session,
            project.project_uuid,
            page_index=2,
            ocr_status=OcrStatus.GO,
        )
        await _seed_page(db_session, project.project_uuid, page_index=3)
        calls = await _stub_ocr_for_page(monkeypatch)
        job = await start_ocr_auto_run_job(session=db_session, project=project)
        # Snapshot saw 2 ausstehend; the GO page was excluded.
        assert (job.payload or {})["total_pages"] == 2
        await _execute(session=db_session, job=job)
        assert job.state == JobState.COMPLETED.value
        # Only the two ausstehend pages were processed; the GO page was
        # never in the iteration set.
        assert len(calls) == 2


# ---------------------------------------------------------------------
# request_cancel + find_in_flight_for_project
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestRequestCancel:
    async def test_sets_flag_on_pending_job(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        job = await start_ocr_auto_run_job(session=db_session, project=project)
        assert (job.payload or {}).get("cancel_requested") is False
        await request_cancel(session=db_session, job=job)
        assert (job.payload or {})["cancel_requested"] is True

    async def test_idempotent(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        job = await start_ocr_auto_run_job(session=db_session, project=project)
        await request_cancel(session=db_session, job=job)
        await request_cancel(session=db_session, job=job)
        # Still True; no error.
        assert (job.payload or {})["cancel_requested"] is True

    async def test_no_op_on_terminal_job(self, db_session: AsyncSession) -> None:
        from waraq.jobs import complete_job

        project = await seed_project(db_session)
        job = await start_ocr_auto_run_job(session=db_session, project=project)
        # Force completion to make the job terminal.
        from waraq.jobs import start_job

        await start_job(session=db_session, job=job)
        await complete_job(session=db_session, job=job, result={"x": 1})
        # Now request cancel — should be a no-op.
        await request_cancel(session=db_session, job=job)
        # Flag NOT flipped because the job is already terminal.
        assert (job.payload or {}).get("cancel_requested") is False


@pytest.mark.asyncio
class TestFindInFlight:
    async def test_returns_none_when_no_jobs(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        result = await find_in_flight_for_project(
            session=db_session, project_uuid=project.project_uuid
        )
        assert result is None

    async def test_returns_pending_job(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        job = await start_ocr_auto_run_job(session=db_session, project=project)
        result = await find_in_flight_for_project(
            session=db_session, project_uuid=project.project_uuid
        )
        assert result is not None
        assert result.job_uuid == job.job_uuid

    async def test_skips_terminal_jobs(self, db_session: AsyncSession) -> None:
        from waraq.jobs import complete_job, start_job

        project = await seed_project(db_session)
        job = await start_ocr_auto_run_job(session=db_session, project=project)
        await start_job(session=db_session, job=job)
        await complete_job(session=db_session, job=job, result={})
        result = await find_in_flight_for_project(
            session=db_session, project_uuid=project.project_uuid
        )
        assert result is None

    async def test_per_project_scope(self, db_session: AsyncSession) -> None:
        project_a = await seed_project(db_session)
        project_b = await seed_project(db_session)
        await start_ocr_auto_run_job(session=db_session, project=project_a)
        # project_b has no jobs.
        result = await find_in_flight_for_project(
            session=db_session, project_uuid=project_b.project_uuid
        )
        assert result is None


# ---------------------------------------------------------------------
# Sub-batch O follow-up (2026-05-12) — orphan reaper
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestReapOrphanJobs:
    """`reap_orphan_jobs` fails stale RUNNING/PENDING auto-run Jobs.

    "Stale" = `Job.updated_at` older than the threshold. The runner
    commits between pages and `TimestampMixin.onupdate=func.now()`
    refreshes `updated_at` on each commit, so a healthy worker keeps
    its row fresh. A dead worker leaves the row's `updated_at`
    frozen — the reaper fails it so the UI stops polling.
    """

    async def test_reaps_stale_running_job(self, db_session: AsyncSession) -> None:
        from datetime import datetime, timedelta

        from sqlalchemy import text as sql_text

        from waraq.jobs import start_job

        project = await seed_project(db_session)
        job = await start_ocr_auto_run_job(session=db_session, project=project)
        await start_job(session=db_session, job=job)
        await db_session.flush()
        # Backdate updated_at past the threshold so the row looks stale.
        past = datetime.now(UTC) - timedelta(
            seconds=STALE_HEARTBEAT_THRESHOLD_SECONDS + 60
        )
        await db_session.execute(
            sql_text("UPDATE jobs SET updated_at = :ts WHERE job_uuid = :u"),
            {"ts": past, "u": job.job_uuid},
        )
        reaped = await reap_orphan_jobs(session=db_session)
        assert job.job_uuid in reaped
        await db_session.refresh(job)
        assert job.state == JobState.FAILED.value
        assert (job.error or {})["phase"] == "server_restart_orphan"
        assert (job.error or {})["previous_state"] == JobState.RUNNING.value

    async def test_reaps_stale_pending_job(self, db_session: AsyncSession) -> None:
        from datetime import datetime, timedelta

        from sqlalchemy import text as sql_text

        project = await seed_project(db_session)
        job = await start_ocr_auto_run_job(session=db_session, project=project)
        # Still PENDING. Backdate it.
        past = datetime.now(UTC) - timedelta(
            seconds=STALE_HEARTBEAT_THRESHOLD_SECONDS + 60
        )
        await db_session.flush()
        await db_session.execute(
            sql_text("UPDATE jobs SET updated_at = :ts WHERE job_uuid = :u"),
            {"ts": past, "u": job.job_uuid},
        )
        reaped = await reap_orphan_jobs(session=db_session)
        assert job.job_uuid in reaped
        await db_session.refresh(job)
        assert job.state == JobState.FAILED.value
        assert (job.error or {})["previous_state"] == JobState.PENDING.value

    async def test_does_not_reap_fresh_running_job(
        self, db_session: AsyncSession
    ) -> None:
        from waraq.jobs import start_job

        project = await seed_project(db_session)
        job = await start_ocr_auto_run_job(session=db_session, project=project)
        await start_job(session=db_session, job=job)
        await db_session.flush()
        # updated_at is current — not stale.
        reaped = await reap_orphan_jobs(session=db_session)
        assert job.job_uuid not in reaped
        await db_session.refresh(job)
        assert job.state == JobState.RUNNING.value

    async def test_does_not_reap_terminal_jobs(
        self, db_session: AsyncSession
    ) -> None:
        from datetime import datetime, timedelta

        from sqlalchemy import text as sql_text

        from waraq.jobs import complete_job, start_job

        project = await seed_project(db_session)
        job = await start_ocr_auto_run_job(session=db_session, project=project)
        await start_job(session=db_session, job=job)
        await complete_job(session=db_session, job=job, result={})
        await db_session.flush()
        # Even if very old, COMPLETED is untouchable.
        past = datetime.now(UTC) - timedelta(
            seconds=STALE_HEARTBEAT_THRESHOLD_SECONDS + 600
        )
        await db_session.execute(
            sql_text("UPDATE jobs SET updated_at = :ts WHERE job_uuid = :u"),
            {"ts": past, "u": job.job_uuid},
        )
        reaped = await reap_orphan_jobs(session=db_session)
        assert job.job_uuid not in reaped
        await db_session.refresh(job)
        assert job.state == JobState.COMPLETED.value

    async def test_does_not_reap_unseeded_fresh_jobs(
        self, db_session: AsyncSession
    ) -> None:
        """Sanity check: a freshly-seeded job is NOT reaped by a call
        whose threshold matches our heartbeat policy. (We can't assert
        the full reap list is empty — the test suite shares a DB and
        prior tests may leave older `ocr_auto_run` rows around.)"""
        from waraq.jobs import start_job

        project = await seed_project(db_session)
        job = await start_ocr_auto_run_job(session=db_session, project=project)
        await start_job(session=db_session, job=job)
        await db_session.flush()
        reaped = await reap_orphan_jobs(session=db_session)
        assert job.job_uuid not in reaped
