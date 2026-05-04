"""T-2.1.2 — Checkpoint write/read service.

CLAUDE.md §B Abkürzung 9: "Checkpoint buffered in memory instead of
atomically persisted" is the named structural failure mode. The whole point
of a checkpoint is that it survives a process restart; an in-memory
checkpoint is worse than no checkpoint at all because it provides false
recovery confidence.

This module:
- writes checkpoints into the `checkpoints` table (NOT into any in-memory
  store — by construction, this service has no module-level state)
- reads the latest checkpoint for a Job (the canonical resume entrypoint)
- reads all checkpoints for a Job (for audit / debugging)

Atomicity: caller owns the transaction. The service flushes; commit/rollback
is the caller's responsibility. The atomicity guarantee for "checkpoint +
job state both land or neither does" is satisfied by wrapping the calls in
a single transaction:

    async with session.begin():
        await write_checkpoint(session=session, job=job, step="page_47", payload=...)
        await pause_job(session=session, job=job)

Restart-survival is the test contract: write → close session → open fresh
session → read returns the same row. See `tests/jobs/test_checkpoints.py`.

Checkpoints are append-only history (no `active`, no `updated_at`). To
"replace" a checkpoint, write a new one — the latest-by-created_at read
returns the most recent.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity.service import new_uuid
from waraq.schemas import Checkpoint, Job


async def write_checkpoint(
    *,
    session: AsyncSession,
    job: Job,
    step: str,
    payload: dict[str, Any] | None = None,
) -> Checkpoint:
    """Stage a Checkpoint row for `job` at `step`.

    Args:
        session: Active async session. Caller manages commit/rollback.
        job: The Job this checkpoint belongs to. Must already be persisted.
        step: Free-text label naming the checkpoint within the job lifecycle
            (e.g., "page_47_ocr_done", "translation_chunk_3_complete").
            Vocabulary is owned by the calling job-type service.
        payload: JSONB recoverable state. Defaults to `{}` if omitted; in
            practice every real checkpoint should carry enough state for
            resumption.

    Returns:
        The Checkpoint instance with `checkpoint_uuid` populated.
    """
    checkpoint = Checkpoint(
        checkpoint_uuid=new_uuid(),
        job_uuid=job.job_uuid,
        step=step,
        payload=payload if payload is not None else {},
    )
    session.add(checkpoint)
    await session.flush()
    return checkpoint


async def read_latest_checkpoint(*, session: AsyncSession, job: Job) -> Checkpoint | None:
    """Return the most recent Checkpoint for `job`, or None if none exist.

    "Most recent" is by `created_at DESC` (insertion order). This is the
    canonical entrypoint for resume logic: load the latest checkpoint,
    inspect its `step` and `payload`, and continue from there.
    """
    result = await session.execute(
        select(Checkpoint)
        .where(Checkpoint.job_uuid == job.job_uuid)
        .order_by(desc(Checkpoint.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def read_checkpoints(*, session: AsyncSession, job: Job) -> list[Checkpoint]:
    """Return all Checkpoints for `job`, oldest first.

    Useful for audit, debugging, and lifecycle visualization. Resume logic
    should use `read_latest_checkpoint` instead — replaying intermediate
    checkpoints is a job-type-specific concern and not what this read is for.
    """
    result = await session.execute(
        select(Checkpoint)
        .where(Checkpoint.job_uuid == job.job_uuid)
        .order_by(Checkpoint.created_at)
    )
    return list(result.scalars().all())
