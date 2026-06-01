"""T-7.1.1 — Translation job tests.

Mandatory tests from Sprint 2 §4:
- T-H1-01 / T-H1-02 (translation skips locked Segments)
- T-REC-03 (resumption deserializes context buffer; post-resumption matches)
- Translation-Job-Lock-Live-Read-Test (lock applied mid-job is seen)
- Translation-Job-Skipped-Segments-Reported-Test (job summary lists skips)

Plus DBB §B Abkürzung 5 enforcement: no translation job without an
`uebersetzungsstart` Decision Event.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.release_gate import start_translation
from waraq.schemas import Block, Checkpoint, Job, Page, Project, Segment
from waraq.schemas.enums import JobState, OcrStatus
from waraq.translation import (
    JOB_TYPE,
    TranslationContext,
    TranslationJobUebersetzungsstartMissing,
    resume_translation_job,
    run_translation_job,
    start_translation_job,
)


async def _seed_project_with_segments(
    session: AsyncSession, *, n: int = 3
) -> tuple[Project, list[Segment]]:
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="translation-test")
    session.add(project)
    await session.flush()

    page = Page(
        page_uuid=new_uuid(),
        project_uuid=project.project_uuid,
        page_index=1,
        ocr_status=OcrStatus.GO,
    )
    session.add(page)
    await session.flush()

    block = Block(
        block_uuid=new_uuid(),
        page_uuid=page.page_uuid,
        block_type="main_text",
        block_index=1,
    )
    session.add(block)
    await session.flush()

    segments: list[Segment] = []
    for i in range(n):
        seg = Segment(
            satz_uuid=new_uuid(),
            block_uuid=block.block_uuid,
            satz_index=i + 1,
            lock_flag=LockFlag.NONE,
            text_content=f"input-{i}",
        )
        session.add(seg)
        segments.append(seg)
    await session.flush()
    return project, segments


def _deterministic_translator(prefix: str = "DE:"):
    """Pure function of input text — context is consumed but not used,
    so test outputs are byte-identical for the same input."""

    async def _t(text: str, ctx: TranslationContext) -> str:
        return f"{prefix} {text}"

    return _t


def _context_aware_translator():
    """Translator that mixes input + the size of the upstream window into
    its output. Used for T-REC-03 to verify context buffer serialization
    round-trips: if the deserialized window has the wrong shape, the
    output text changes."""

    async def _t(text: str, ctx: TranslationContext) -> str:
        return f"DE[{len(ctx.upstream_window)}]: {text}"

    return _t


# --- DBB §B Abkürzung 5: no auto-trigger -------------------------------


@pytest.mark.asyncio
class TestNoAutoTriggerWithoutUebersetzungsstart:
    """Sprint 2 §A HG-S2-2 / DBB §B Abkürzung 5: translation cannot be
    started without the user explicitly writing an `uebersetzungsstart`
    Decision Event via release_gate.start_translation."""

    async def test_start_translation_job_refuses_without_de(self, db_session: AsyncSession) -> None:
        project, segments = await _seed_project_with_segments(db_session)
        with pytest.raises(TranslationJobUebersetzungsstartMissing):
            await start_translation_job(
                session=db_session,
                project_uuid=project.project_uuid,
                segment_uuids=[s.satz_uuid for s in segments],
            )

    async def test_start_translation_job_succeeds_after_release_gate_de(
        self, db_session: AsyncSession
    ) -> None:
        project, segments = await _seed_project_with_segments(db_session)
        await start_translation(session=db_session, project_uuid=project.project_uuid)

        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[s.satz_uuid for s in segments],
        )
        assert job.job_type == JOB_TYPE
        assert job.state == JobState.PENDING.value
        assert job.project_uuid == project.project_uuid


# --- Lock skipping (T-H1-01 / T-H1-02) --------------------------------


@pytest.mark.asyncio
class TestTranslationSkipsLockedSegments:
    async def test_manual_local_segment_is_skipped(self, db_session: AsyncSession) -> None:
        project, segments = await _seed_project_with_segments(db_session, n=2)
        segments[0].lock_flag = LockFlag.MANUAL_LOCAL
        await db_session.flush()
        await start_translation(session=db_session, project_uuid=project.project_uuid)

        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[s.satz_uuid for s in segments],
        )
        result = await run_translation_job(
            session=db_session, job=job, translator=_deterministic_translator()
        )

        assert result.chunks[0].skipped is True
        assert result.chunks[0].skip_reason == "lock_flag=manual_local"
        assert result.chunks[1].skipped is False
        assert result.chunks[1].output_text == "DE: input-1"

    async def test_manual_editorial_segment_is_skipped(self, db_session: AsyncSession) -> None:
        project, segments = await _seed_project_with_segments(db_session, n=2)
        segments[1].lock_flag = LockFlag.MANUAL_EDITORIAL
        await db_session.flush()
        await start_translation(session=db_session, project_uuid=project.project_uuid)

        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[s.satz_uuid for s in segments],
        )
        result = await run_translation_job(
            session=db_session, job=job, translator=_deterministic_translator()
        )

        assert result.chunks[1].skipped is True
        assert result.chunks[1].skip_reason == "lock_flag=manual_editorial"


@pytest.mark.asyncio
class TestLockLiveRead:
    """Translation-Job-Lock-Live-Read-Test.

    A lock applied mid-job (after the job started, before the locked
    segment's iteration) MUST be honored. R-S2-04 names this the named
    structural failure mode."""

    async def test_lock_applied_mid_job_is_seen_on_subsequent_iterations(
        self, db_session: AsyncSession
    ) -> None:
        project, segments = await _seed_project_with_segments(db_session, n=3)
        await start_translation(session=db_session, project_uuid=project.project_uuid)

        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[s.satz_uuid for s in segments],
        )

        # Translator that locks segments[2] just before it gets translated,
        # exercising the live-read guarantee.
        seg_to_lock_uuid = segments[2].satz_uuid
        seen_inputs: list[str] = []

        async def _translator(text: str, ctx: TranslationContext) -> str:
            seen_inputs.append(text)
            if text == "input-1":
                # Apply the lock just after seg index 1's output, before
                # iteration 2 reads the segment row.
                target = (
                    await db_session.execute(
                        select(Segment).where(Segment.satz_uuid == seg_to_lock_uuid)
                    )
                ).scalar_one()
                target.lock_flag = LockFlag.MANUAL_LOCAL
                await db_session.flush()
            return f"DE: {text}"

        result = await run_translation_job(session=db_session, job=job, translator=_translator)

        # First two segments translated; third skipped because of the
        # mid-job lock.
        assert result.chunks[0].skipped is False
        assert result.chunks[1].skipped is False
        assert result.chunks[2].skipped is True
        assert result.chunks[2].skip_reason == "lock_flag=manual_local"
        # Translator was NOT called for the locked segment.
        assert "input-2" not in seen_inputs


# --- Skipped-segments summary --------------------------------------


@pytest.mark.asyncio
class TestSkippedSegmentsReported:
    """Translation-Job-Skipped-Segments-Reported-Test."""

    async def test_job_summary_enumerates_skipped_segments(self, db_session: AsyncSession) -> None:
        project, segments = await _seed_project_with_segments(db_session, n=3)
        segments[0].lock_flag = LockFlag.MANUAL_LOCAL
        segments[2].lock_flag = LockFlag.MANUAL_EDITORIAL
        await db_session.flush()
        await start_translation(session=db_session, project_uuid=project.project_uuid)

        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[s.satz_uuid for s in segments],
        )
        result = await run_translation_job(
            session=db_session, job=job, translator=_deterministic_translator()
        )

        assert len(result.skipped) == 2
        skipped_uuids = {s.satz_uuid for s in result.skipped}
        assert segments[0].satz_uuid in skipped_uuids
        assert segments[2].satz_uuid in skipped_uuids
        # Job.result mirrors the summary.
        assert job.result["chunks_total"] == 3
        assert job.result["chunks_translated"] == 1
        assert job.result["chunks_skipped"] == 2
        assert len(job.result["skipped_segments"]) == 2

    async def test_translator_failure_skips_segment_and_continues(
        self, db_session: AsyncSession
    ) -> None:
        project, segments = await _seed_project_with_segments(db_session, n=3)
        await start_translation(session=db_session, project_uuid=project.project_uuid)

        async def flaky_translator(text: str, ctx: TranslationContext) -> str:
            if text == "input-1":
                raise ValueError("missing translation line tag L0012")
            return f"DE: {text}"

        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[s.satz_uuid for s in segments],
        )
        result = await run_translation_job(
            session=db_session, job=job, translator=flaky_translator
        )

        assert job.state == JobState.COMPLETED.value
        assert [chunk.output_text for chunk in result.chunks] == [
            "DE: input-0",
            None,
            "DE: input-2",
        ]
        assert len(result.skipped) == 1
        assert result.skipped[0].satz_uuid == segments[1].satz_uuid
        assert "missing translation line tag L0012" in result.skipped[0].reason
        assert job.result["chunks_total"] == 3
        assert job.result["chunks_translated"] == 2
        assert job.result["chunks_skipped"] == 1
        assert job.result["skipped_segments"][0]["satz_uuid"] == str(segments[1].satz_uuid)


# --- Checkpoint per chunk + resumption (T-REC-03) ------------------


@pytest.mark.asyncio
class TestCheckpointPerChunk:
    async def test_checkpoint_written_after_each_chunk(self, db_session: AsyncSession) -> None:
        project, segments = await _seed_project_with_segments(db_session, n=3)
        await start_translation(session=db_session, project_uuid=project.project_uuid)

        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[s.satz_uuid for s in segments],
        )
        await run_translation_job(
            session=db_session, job=job, translator=_deterministic_translator()
        )

        checkpoints = list(
            (
                await db_session.execute(
                    select(Checkpoint)
                    .where(Checkpoint.job_uuid == job.job_uuid)
                    .order_by(Checkpoint.created_at.asc())
                )
            ).scalars()
        )
        assert len(checkpoints) == 3
        # Last checkpoint records chunk_index = 3 (post-final-iteration).
        assert checkpoints[-1].payload["chunk_index"] == 3


@pytest.mark.asyncio
class TestResumptionRoundTripsContext:
    """T-REC-03: resumption deserializes context buffer; translation
    after resumption matches uninterrupted translation byte-for-byte
    (for a deterministic translator)."""

    async def test_resume_picks_up_from_latest_checkpoint(self, db_session: AsyncSession) -> None:
        project, segments = await _seed_project_with_segments(db_session, n=4)
        await start_translation(session=db_session, project_uuid=project.project_uuid)
        translator = _context_aware_translator()

        # Baseline: run the job uninterrupted and record outputs.
        job_baseline = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[s.satz_uuid for s in segments],
        )
        baseline = await run_translation_job(
            session=db_session, job=job_baseline, translator=translator
        )
        baseline_outputs = [c.output_text for c in baseline.chunks]

        # Now repeat with an interruption: simulate a job that processed
        # chunks 0 and 1, then "crashed". Construct a Job whose latest
        # checkpoint says chunk_index=2 with the matching context, then
        # resume from there.
        await start_translation(session=db_session, project_uuid=project.project_uuid)
        job_resume = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[s.satz_uuid for s in segments],
        )
        # Manually drive job to RUNNING and write the synthetic checkpoint
        # that mirrors the post-chunk-2 state of the baseline run.
        from waraq.jobs import start_job, write_checkpoint

        await start_job(session=db_session, job=job_resume)
        partial_context = TranslationContext()
        for output in baseline_outputs[:2]:
            assert output is not None
            partial_context = partial_context.with_translated(output)
        await write_checkpoint(
            session=db_session,
            job=job_resume,
            step="translation_chunk_2",
            payload={
                "chunk_index": 2,
                "context": partial_context.to_dict(),
                "skipped_so_far": [],
            },
        )

        resumed = await resume_translation_job(
            session=db_session, job=job_resume, translator=translator
        )
        resumed_outputs = [c.output_text for c in resumed.chunks]

        # The resume path only iterates chunks 2 and 3; the chunks list
        # contains only those two entries.
        assert len(resumed.chunks) == 2
        assert resumed_outputs[0] == baseline_outputs[2]
        assert resumed_outputs[1] == baseline_outputs[3]


@pytest.mark.asyncio
class TestResumeWithNoCheckpointBehavesAsFreshRun:
    async def test_resume_without_prior_checkpoint_runs_from_zero(
        self, db_session: AsyncSession
    ) -> None:
        project, segments = await _seed_project_with_segments(db_session, n=2)
        await start_translation(session=db_session, project_uuid=project.project_uuid)

        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[s.satz_uuid for s in segments],
        )
        # Resume without any checkpoints existing — should behave like a
        # fresh run.
        result = await resume_translation_job(
            session=db_session, job=job, translator=_deterministic_translator()
        )
        assert len(result.chunks) == 2
        assert all(not c.skipped for c in result.chunks)


# --- TranslationContext serialization round-trip -------------------


class TestTranslationContextSerialization:
    def test_to_dict_from_dict_round_trip(self) -> None:
        ctx = TranslationContext(
            upstream_window=["a", "b", "c"],
            terminology_bindings={"k1": "rendering-1", "k2": "rendering-2"},
            style_anchors=["short", "anchored"],
        )
        round_trip = TranslationContext.from_dict(ctx.to_dict())
        assert round_trip == ctx

    def test_with_translated_caps_window(self) -> None:
        ctx = TranslationContext(upstream_window=["1", "2", "3"])
        new_ctx = ctx.with_translated("4", window_size=2)
        assert new_ctx.upstream_window == ["3", "4"]


# --- Real-restart-survival (engine.dispose round-trip) -------------


@pytest.mark.asyncio
class TestTranslationJobRestartSurvival:
    """Belt-and-braces: write checkpoints + commit + tear engine down +
    fresh engine + read latest checkpoint → still there. Mirrors the
    Sprint 0 / T-2.1.2 + T-5.1.2 restart-survival pattern."""

    async def test_translation_checkpoint_survives_engine_dispose(self) -> None:
        from tests.conftest import _test_database_url, seed_account_uuid

        url = _test_database_url()
        account_uuid = new_uuid()
        project_uuid = new_uuid()
        page_uuid = new_uuid()
        block_uuid = new_uuid()
        seg_uuids = [new_uuid() for _ in range(2)]
        job_uuid_marker: str

        # Phase A: seed + run with a translator + commit + dispose.
        engine_a = create_async_engine(url, future=True)
        sm_a = async_sessionmaker(bind=engine_a, class_=AsyncSession, expire_on_commit=False)
        try:
            async with sm_a() as session, session.begin():
                await seed_account_uuid(session, account_uuid)
                session.add(
                    Project(
                        project_uuid=project_uuid,
                        account_uuid=account_uuid,
                        name="restart-translation",
                    )
                )
                await session.flush()
                session.add(
                    Page(
                        page_uuid=page_uuid,
                        project_uuid=project_uuid,
                        page_index=1,
                        ocr_status=OcrStatus.GO,
                    )
                )
                await session.flush()
                session.add(
                    Block(
                        block_uuid=block_uuid,
                        page_uuid=page_uuid,
                        block_type="main_text",
                        block_index=1,
                    )
                )
                await session.flush()
                for i, sid in enumerate(seg_uuids):
                    session.add(
                        Segment(
                            satz_uuid=sid,
                            block_uuid=block_uuid,
                            satz_index=i + 1,
                            lock_flag=LockFlag.NONE,
                            text_content=f"restart-{i}",
                        )
                    )
                await session.flush()

                await start_translation(session=session, project_uuid=project_uuid)
                job = await start_translation_job(
                    session=session,
                    project_uuid=project_uuid,
                    segment_uuids=seg_uuids,
                )
                job_uuid_marker = str(job.job_uuid)
                await run_translation_job(
                    session=session, job=job, translator=_deterministic_translator()
                )
        finally:
            await engine_a.dispose()

        # Phase B: brand-new engine + session — checkpoints still there.
        engine_b = create_async_engine(url, future=True)
        sm_b = async_sessionmaker(bind=engine_b, class_=AsyncSession, expire_on_commit=False)
        try:
            async with sm_b() as session:
                rows = list(
                    (
                        await session.execute(
                            select(Checkpoint).where(
                                Checkpoint.job_uuid == _uuid.UUID(job_uuid_marker)
                            )
                        )
                    ).scalars()
                )
                assert len(rows) == len(seg_uuids), (
                    "checkpoint did not survive engine teardown — translation job "
                    "is not atomically persisting per chunk"
                )
        finally:
            await engine_b.dispose()

        # Phase C: cleanup.
        engine_c = create_async_engine(url, future=True)
        sm_c = async_sessionmaker(bind=engine_c, class_=AsyncSession, expire_on_commit=False)
        try:
            async with sm_c() as session, session.begin():
                from waraq.schemas import Account, DecisionEvent, LogEntry

                await session.execute(
                    delete(Checkpoint).where(Checkpoint.job_uuid == _uuid.UUID(job_uuid_marker))
                )
                await session.execute(
                    delete(Job).where(Job.job_uuid == _uuid.UUID(job_uuid_marker))
                )
                await session.execute(delete(Segment).where(Segment.block_uuid == block_uuid))
                await session.execute(delete(Block).where(Block.block_uuid == block_uuid))
                await session.execute(delete(Page).where(Page.page_uuid == page_uuid))
                await session.execute(delete(LogEntry).where(LogEntry.scope_uuid == project_uuid))
                await session.execute(
                    delete(DecisionEvent).where(DecisionEvent.scope_uuid == project_uuid)
                )
                await session.execute(delete(Project).where(Project.project_uuid == project_uuid))
                await session.execute(delete(Account).where(Account.account_uuid == account_uuid))
        finally:
            await engine_c.dispose()


# Need uuid import for the restart test cleanup phase.
import uuid as _uuid  # noqa: E402

# Silence "AsyncIterator imported but unused" — the import is reserved for
# future fixtures that yield a session in a generator. Keeping it documents
# intent without affecting runtime.
_ = AsyncIterator
