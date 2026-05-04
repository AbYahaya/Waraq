"""T-2.1.1 — Job state machine tests.

Three layers:
1. Pure transition-graph tests — no DB. The legal/illegal sets are the
   canonical contract; if the graph changes, these fail first.
2. Integration — round-trip transitions against live Postgres, including
   `result`/`error` payload landing.
3. DB CHECK constraint — Postgres rejects invalid state values too.
"""

from __future__ import annotations

import itertools

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.jobs import (
    TERMINAL_STATES,
    IllegalJobTransition,
    complete_job,
    fail_job,
    is_legal_transition,
    pause_job,
    resume_job,
    start_job,
)
from waraq.schemas import Job
from waraq.schemas.enums import JobState

_LEGAL = frozenset(
    {
        (JobState.PENDING, JobState.RUNNING),
        (JobState.PENDING, JobState.FAILED),
        (JobState.RUNNING, JobState.PAUSED),
        (JobState.RUNNING, JobState.COMPLETED),
        (JobState.RUNNING, JobState.FAILED),
        (JobState.PAUSED, JobState.RUNNING),
        (JobState.PAUSED, JobState.FAILED),
    }
)


# --- Layer 1: pure transition-graph tests --------------------------------


class TestT_2_1_1_TransitionGraph:
    def test_legal_set_matches_canonical_contract(self) -> None:
        for from_state, to_state in _LEGAL:
            assert is_legal_transition(from_state, to_state) is True

    def test_terminal_states_have_no_outgoing_transitions(self) -> None:
        # Once completed or failed, a Job is done. No further transitions.
        for terminal in TERMINAL_STATES:
            for any_state in JobState:
                assert is_legal_transition(terminal, any_state) is False, (
                    f"terminal {terminal.value} should not transition to {any_state.value}"
                )

    def test_no_self_transitions(self) -> None:
        # pending → pending, running → running, etc. all illegal.
        for s in JobState:
            assert is_legal_transition(s, s) is False

    def test_every_non_terminal_state_can_reach_failed(self) -> None:
        # Every non-terminal state must have a path to failure (cancelability).
        for s in JobState:
            if s in TERMINAL_STATES:
                continue
            assert is_legal_transition(s, JobState.FAILED) is True

    def test_only_running_can_complete(self) -> None:
        # COMPLETED reachable only from RUNNING; never from pending or paused.
        for s in JobState:
            if s == JobState.RUNNING:
                continue
            assert is_legal_transition(s, JobState.COMPLETED) is False

    def test_illegal_transitions_are_complement_of_legal(self) -> None:
        # All (from, to) pairs minus the legal set = the illegal set.
        all_pairs = set(itertools.product(JobState, JobState))
        illegal = all_pairs - _LEGAL
        for from_state, to_state in illegal:
            assert is_legal_transition(from_state, to_state) is False


# --- Layer 2: integration --------------------------------------------------


async def _seed_job(session: AsyncSession, *, initial_state: JobState = JobState.PENDING) -> Job:
    job = Job(
        job_uuid=new_uuid(),
        job_type="ocr_baseline",
        state=initial_state.value,
        payload={"book": "test"},
    )
    session.add(job)
    await session.flush()
    return job


@pytest.mark.asyncio
class TestT_2_1_1_Integration:
    async def test_start_job_pending_to_running(self, db_session: AsyncSession) -> None:
        job = await _seed_job(db_session)
        assert job.state == JobState.PENDING.value

        await start_job(session=db_session, job=job)
        assert job.state == JobState.RUNNING.value

    async def test_pause_resume_cycle(self, db_session: AsyncSession) -> None:
        job = await _seed_job(db_session, initial_state=JobState.RUNNING)
        await pause_job(session=db_session, job=job)
        assert job.state == JobState.PAUSED.value
        await resume_job(session=db_session, job=job)
        assert job.state == JobState.RUNNING.value

    async def test_complete_job_stages_result(self, db_session: AsyncSession) -> None:
        job = await _seed_job(db_session, initial_state=JobState.RUNNING)
        result = {"pages_processed": 47, "duration_s": 312.4}

        await complete_job(session=db_session, job=job, result=result)

        assert job.state == JobState.COMPLETED.value
        assert job.result == result
        assert job.error is None

    async def test_fail_job_stages_error(self, db_session: AsyncSession) -> None:
        job = await _seed_job(db_session, initial_state=JobState.RUNNING)
        error = {"class": "F-04", "message": "Gemini quota exceeded"}

        await fail_job(session=db_session, job=job, error=error)

        assert job.state == JobState.FAILED.value
        assert job.error == error

    async def test_fail_from_pending_or_paused(self, db_session: AsyncSession) -> None:
        # pending → failed
        j1 = await _seed_job(db_session, initial_state=JobState.PENDING)
        await fail_job(session=db_session, job=j1, error={"reason": "canceled before start"})
        assert j1.state == JobState.FAILED.value

        # paused → failed
        j2 = await _seed_job(db_session, initial_state=JobState.PAUSED)
        await fail_job(session=db_session, job=j2, error={"reason": "canceled while paused"})
        assert j2.state == JobState.FAILED.value


# --- Layer 2b: illegal transitions raise BEFORE DB write ------------------


@pytest.mark.asyncio
class TestT_2_1_1_IllegalTransitions:
    async def test_cannot_start_running_job(self, db_session: AsyncSession) -> None:
        job = await _seed_job(db_session, initial_state=JobState.RUNNING)
        with pytest.raises(IllegalJobTransition) as exc:
            await start_job(session=db_session, job=job)
        assert exc.value.from_state == JobState.RUNNING.value
        assert exc.value.to_state == JobState.RUNNING.value
        # State unchanged after refusal.
        await db_session.refresh(job)
        assert job.state == JobState.RUNNING.value

    async def test_cannot_complete_pending_job(self, db_session: AsyncSession) -> None:
        job = await _seed_job(db_session, initial_state=JobState.PENDING)
        with pytest.raises(IllegalJobTransition):
            await complete_job(session=db_session, job=job, result={"x": 1})
        await db_session.refresh(job)
        assert job.state == JobState.PENDING.value

    async def test_cannot_resume_running_job(self, db_session: AsyncSession) -> None:
        job = await _seed_job(db_session, initial_state=JobState.RUNNING)
        with pytest.raises(IllegalJobTransition):
            await resume_job(session=db_session, job=job)

    async def test_terminal_completed_job_cannot_transition_anywhere(
        self, db_session: AsyncSession
    ) -> None:
        job = await _seed_job(db_session, initial_state=JobState.COMPLETED)
        for action in (start_job, pause_job, resume_job):
            with pytest.raises(IllegalJobTransition):
                await action(session=db_session, job=job)
        with pytest.raises(IllegalJobTransition):
            await complete_job(session=db_session, job=job)
        with pytest.raises(IllegalJobTransition):
            await fail_job(session=db_session, job=job, error={})

    async def test_terminal_failed_job_cannot_transition_anywhere(
        self, db_session: AsyncSession
    ) -> None:
        job = await _seed_job(db_session, initial_state=JobState.FAILED)
        for action in (start_job, pause_job, resume_job):
            with pytest.raises(IllegalJobTransition):
                await action(session=db_session, job=job)


# --- Layer 3: DB CHECK constraint enforces value set ---------------------


@pytest.mark.asyncio
class TestT_2_1_1_DbCheckConstraint:
    async def test_postgres_rejects_invalid_state_value(self, db_session: AsyncSession) -> None:
        job = Job(
            job_uuid=new_uuid(),
            job_type="x",
            state="garbage_state",
            payload={},
        )
        db_session.add(job)
        with pytest.raises(IntegrityError):
            await db_session.flush()
