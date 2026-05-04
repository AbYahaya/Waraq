"""T-2.1.2 — Checkpoint write/read service tests.

Three layers:
1. Architectural — service signature and module surface.
2. Integration (rollback fixture) — round-trip writes, ordering, FK behavior.
3. **Restart-survival** — real commit + fresh engine + fresh session
   confirms the checkpoint persisted across what is, from the DB's
   perspective, indistinguishable from a process restart. This is the
   Abkürzung 9 hard rule.
"""

from __future__ import annotations

import asyncio
import inspect

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from waraq.identity import new_uuid
from waraq.jobs import (
    read_checkpoints,
    read_latest_checkpoint,
    write_checkpoint,
)
from waraq.schemas import Checkpoint, Job
from waraq.schemas.enums import JobState

# --- Helpers ---------------------------------------------------------------


async def _seed_job(session: AsyncSession, *, initial_state: JobState = JobState.RUNNING) -> Job:
    job = Job(
        job_uuid=new_uuid(),
        job_type="ocr_baseline",
        state=initial_state.value,
        payload={"book": "test"},
    )
    session.add(job)
    await session.flush()
    return job


# --- Layer 1: signature/module surface ------------------------------------


class TestT_2_1_2_ServiceSurface:
    def test_write_signature_is_keyword_only(self) -> None:
        sig = inspect.signature(write_checkpoint)
        # Reject positional callers — every kwarg here is structural and
        # mis-positional risk (job vs payload swap) is real.
        for name, param in sig.parameters.items():
            assert param.kind == inspect.Parameter.KEYWORD_ONLY, f"{name} must be keyword-only"

    def test_module_has_no_class_or_module_level_storage(self) -> None:
        """A naive 'in-memory checkpoint store' would show up as a
        module-level dict or list. Lock that out: nothing mutable lives at
        module scope in waraq.jobs.checkpoints."""
        from waraq.jobs import checkpoints as cp_module

        for name, value in vars(cp_module).items():
            if name.startswith("_"):
                continue
            # Allow callables (functions/classes) and the imported types.
            # A dict/list/set at module scope would be the smoking gun.
            assert not isinstance(value, (dict, list, set)), (
                f"waraq.jobs.checkpoints exposes mutable module-level state: {name!r}"
            )


# --- Layer 2: integration with rollback fixture ---------------------------


@pytest.mark.asyncio
class TestT_2_1_2_Integration:
    async def test_write_checkpoint_creates_row(self, db_session: AsyncSession) -> None:
        job = await _seed_job(db_session)
        cp = await write_checkpoint(
            session=db_session,
            job=job,
            step="page_47_ocr_done",
            payload={"page_index": 47, "blocks_done": 12},
        )

        loaded = (
            await db_session.execute(
                select(Checkpoint).where(Checkpoint.checkpoint_uuid == cp.checkpoint_uuid)
            )
        ).scalar_one()
        assert loaded.job_uuid == job.job_uuid
        assert loaded.step == "page_47_ocr_done"
        assert loaded.payload == {"page_index": 47, "blocks_done": 12}

    async def test_payload_defaults_to_empty_dict(self, db_session: AsyncSession) -> None:
        job = await _seed_job(db_session)
        cp = await write_checkpoint(session=db_session, job=job, step="started")
        assert cp.payload == {}

    async def test_read_latest_returns_none_when_no_checkpoints(
        self, db_session: AsyncSession
    ) -> None:
        job = await _seed_job(db_session)
        assert await read_latest_checkpoint(session=db_session, job=job) is None

    async def test_read_latest_returns_most_recent(self, db_session: AsyncSession) -> None:
        job = await _seed_job(db_session)

        await write_checkpoint(session=db_session, job=job, step="step_1")
        # Tiny sleep so created_at differs at the timestamp resolution.
        await asyncio.sleep(0.01)
        await write_checkpoint(session=db_session, job=job, step="step_2")
        await asyncio.sleep(0.01)
        latest = await write_checkpoint(session=db_session, job=job, step="step_3")

        loaded = await read_latest_checkpoint(session=db_session, job=job)
        assert loaded is not None
        assert loaded.checkpoint_uuid == latest.checkpoint_uuid
        assert loaded.step == "step_3"

    async def test_read_all_checkpoints_in_order(self, db_session: AsyncSession) -> None:
        job = await _seed_job(db_session)
        steps = ["a", "b", "c", "d"]
        for s in steps:
            await write_checkpoint(session=db_session, job=job, step=s)
            await asyncio.sleep(0.005)

        all_cps = await read_checkpoints(session=db_session, job=job)
        assert [cp.step for cp in all_cps] == steps

    async def test_checkpoints_are_isolated_per_job(self, db_session: AsyncSession) -> None:
        job_a = await _seed_job(db_session)
        job_b = await _seed_job(db_session)

        await write_checkpoint(session=db_session, job=job_a, step="a_only")
        await write_checkpoint(session=db_session, job=job_b, step="b_only_1")
        await write_checkpoint(session=db_session, job=job_b, step="b_only_2")

        a_cps = await read_checkpoints(session=db_session, job=job_a)
        b_cps = await read_checkpoints(session=db_session, job=job_b)
        assert [cp.step for cp in a_cps] == ["a_only"]
        assert [cp.step for cp in b_cps] == ["b_only_1", "b_only_2"]


# --- Layer 3: RESTART-SURVIVAL — Abkürzung 9 hard rule -------------------


@pytest.mark.asyncio
class TestT_2_1_2_AbkurzungNeun_RestartSurvival:
    """The hard rule: writing a checkpoint, then everything tearing down
    (process restart simulation), then reading from a fresh engine — must
    return the same checkpoint.

    This test does NOT use the rollback fixture. It commits to the real DB
    and cleans up its own data afterward."""

    async def test_checkpoint_survives_session_and_engine_teardown(self) -> None:
        from tests.conftest import _test_database_url

        url = _test_database_url()

        # --- Phase 1: write + commit + tear everything down --------------
        engine_a = create_async_engine(url, future=True)
        sessionmaker_a = async_sessionmaker(
            bind=engine_a, class_=AsyncSession, expire_on_commit=False
        )

        job_uuid = new_uuid()
        checkpoint_step = f"restart_survival_test_{new_uuid()}"

        try:
            async with sessionmaker_a() as session, session.begin():
                job = Job(
                    job_uuid=job_uuid,
                    job_type="restart_survival_test",
                    state=JobState.RUNNING.value,
                    payload={},
                )
                session.add(job)
                await session.flush()

                await write_checkpoint(
                    session=session,
                    job=job,
                    step=checkpoint_step,
                    payload={"resume_from": 47},
                )
            # Both job and checkpoint are now committed.
        finally:
            await engine_a.dispose()

        # --- Phase 2: fresh engine + fresh session — read it back -------
        engine_b = create_async_engine(url, future=True)
        sessionmaker_b = async_sessionmaker(
            bind=engine_b, class_=AsyncSession, expire_on_commit=False
        )

        try:
            async with sessionmaker_b() as session:
                # Use the same query the resume code would use.
                stub_job = Job(
                    job_uuid=job_uuid,
                    job_type="restart_survival_test",
                    state=JobState.RUNNING.value,
                    payload={},
                )
                # We do NOT add the stub to the session — read_latest_checkpoint
                # only needs job.job_uuid for its query.
                latest = await read_latest_checkpoint(session=session, job=stub_job)

                assert latest is not None, (
                    "Abkürzung 9 violated: checkpoint did not survive engine "
                    "teardown — service is not atomically persisting"
                )
                assert latest.step == checkpoint_step
                assert latest.payload == {"resume_from": 47}
        finally:
            await engine_b.dispose()

        # --- Phase 3: cleanup so we don't pollute the dev DB -------------
        engine_c = create_async_engine(url, future=True)
        sessionmaker_c = async_sessionmaker(
            bind=engine_c, class_=AsyncSession, expire_on_commit=False
        )
        try:
            async with sessionmaker_c() as session, session.begin():
                await session.execute(delete(Checkpoint).where(Checkpoint.job_uuid == job_uuid))
                await session.execute(delete(Job).where(Job.job_uuid == job_uuid))
        finally:
            await engine_c.dispose()
