"""T-2.1.1 — Job state machine service.

Single mutation point for `Job.state`. The transition graph is the canonical
contract; only legal transitions succeed. Illegal transitions raise
`IllegalJobTransition` BEFORE any DB write.

Per CLAUDE.md §B Abkürzung 9, Checkpoint must be atomically persisted
(T-2.1.2). The Job and its checkpoint progress through state transitions
together; this service is the boundary that enforces "no silent state
mutation" alongside the Guard discipline.

Atomicity: caller owns the transaction. The service flushes; commit/rollback
is the caller's responsibility.

Design choice: per-action functions (`start_job`, `pause_job`, ...) over a
single generic `transition_job(to_state)`. Per-action names make call sites
self-documenting and let each function take exactly the kwargs that its
transition cares about (e.g., `complete_job` takes `result`, `fail_job` takes
`error`).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.schemas import Job
from waraq.schemas.enums import JobState


class IllegalJobTransition(Exception):
    """Raised when a caller attempts a transition not in the canonical graph."""

    def __init__(self, *, job_uuid: object, from_state: str, to_state: str) -> None:
        super().__init__(f"Illegal Job transition for {job_uuid}: {from_state!r} → {to_state!r}")
        self.job_uuid = job_uuid
        self.from_state = from_state
        self.to_state = to_state


_LEGAL_TRANSITIONS: frozenset[tuple[JobState, JobState]] = frozenset(
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


TERMINAL_STATES: frozenset[JobState] = frozenset({JobState.COMPLETED, JobState.FAILED})


def is_legal_transition(from_state: JobState, to_state: JobState) -> bool:
    """Pure check: would `(from_state, to_state)` be a legal transition?

    Useful for UI / dry-run checks where you want to query the graph without
    side effects."""
    return (from_state, to_state) in _LEGAL_TRANSITIONS


async def _transition(
    session: AsyncSession,
    job: Job,
    to_state: JobState,
    *,
    result: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> Job:
    """Internal: validate and apply a state transition.

    Raises IllegalJobTransition if the transition is not in the canonical
    graph. Validation runs BEFORE any DB mutation — failed transitions leave
    the Job row untouched."""
    from_state = JobState(job.state)
    if (from_state, to_state) not in _LEGAL_TRANSITIONS:
        raise IllegalJobTransition(
            job_uuid=job.job_uuid, from_state=from_state.value, to_state=to_state.value
        )
    job.state = to_state.value
    if result is not None:
        job.result = result
    if error is not None:
        job.error = error
    await session.flush()
    return job


async def start_job(*, session: AsyncSession, job: Job) -> Job:
    """pending → running."""
    return await _transition(session, job, JobState.RUNNING)


async def pause_job(*, session: AsyncSession, job: Job) -> Job:
    """running → paused."""
    return await _transition(session, job, JobState.PAUSED)


async def resume_job(*, session: AsyncSession, job: Job) -> Job:
    """paused → running."""
    return await _transition(session, job, JobState.RUNNING)


async def complete_job(
    *, session: AsyncSession, job: Job, result: dict[str, Any] | None = None
) -> Job:
    """running → completed. `result` is staged into `Job.result` if provided."""
    return await _transition(session, job, JobState.COMPLETED, result=result)


async def fail_job(*, session: AsyncSession, job: Job, error: dict[str, Any] | None = None) -> Job:
    """{pending | running | paused} → failed. `error` is staged into `Job.error`."""
    return await _transition(session, job, JobState.FAILED, error=error)
