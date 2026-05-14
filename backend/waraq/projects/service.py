"""Sub-batch P (out-of-phase, 2026-05-13) — project lifecycle service.

`delete_project` is the canonical entrypoint for "user deletes a project
from the UI". Per H-5 (UUIDs are immutable, only `active=false` is
allowed), this is **inactivation**, not a hard delete:

- The Project row stays in the DB forever.
- Child Pages/Blocks/Segments are deliberately NOT cascaded (user
  decision in sub-batch P design). They remain `active=true` in the DB
  but become unreachable because the tightened `_project_visible`
  helper in `waraq.api._ownership` rejects any chain whose top-level
  Project is inactive.
- POs (SCAN-PO, OCR-PO, TRANSLATION-PO, LINEAGE_EVENT-PO,
  EXPORT_EVENT) are append-only audit history (PROVENANCE-Kern is
  the only writer). They keep their UUIDs and remain queryable for
  audit purposes — H-5 is satisfied.

In-flight jobs: per user choice "auto-cancel then delete", any
RUNNING/PENDING `ocr_auto_run` or `translation` Job for the project
has its `payload.cancel_requested` flipped to `true` in the same
transaction as the inactivation. The runners check this flag between
iterations and bail with `error.phase="user_cancelled"`. No wait —
the cancel + inactivation commit atomically; the runner sees both
on its next refresh.

Idempotent: deleting an already-inactive project is a no-op (the
endpoint reaches this through the ownership helper, which returns
404 for inactive projects — so callers don't reach the service path
twice in normal flow; the service still guards defensively).
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from waraq.identity.service import mark_inactive
from waraq.schemas import Job, Project
from waraq.schemas.enums import JobState

logger = logging.getLogger(__name__)

# Job types whose runner reads `payload.cancel_requested` between
# iterations. Sub-batch P sets the flag on any in-flight Job of these
# types when its project is being deleted, so the runner cooperatively
# unwinds.
_CANCELLABLE_JOB_TYPES: tuple[str, ...] = ("ocr_auto_run", "translation")


async def delete_project(*, session: AsyncSession, project: Project) -> Project:
    """Inactivate `project` and cooperatively cancel any in-flight jobs.

    The caller must have already verified ownership (typically via
    `waraq.api._ownership.owned_project_or_404`). This function does
    NOT re-check.

    Idempotent on `active=False` input — returns the project unchanged.
    """
    if not project.active:
        return project

    # Cooperative cancel for in-flight jobs on this project. Same tx as
    # the inactivation, so the runner sees both on its next refresh:
    # cancel_requested=True + project.active=False (deleted).
    result = await session.execute(
        select(Job)
        .where(Job.project_uuid == project.project_uuid)
        .where(Job.job_type.in_(_CANCELLABLE_JOB_TYPES))
        .where(Job.state.in_([JobState.RUNNING.value, JobState.PENDING.value]))
    )
    in_flight: list[Job] = list(result.scalars())
    for job in in_flight:
        payload = job.payload or {}
        payload["cancel_requested"] = True
        job.payload = payload
        flag_modified(job, "payload")

    mark_inactive(project)
    await session.flush()

    if in_flight:
        logger.info(
            "project.delete.cancelled_in_flight_jobs",
            extra={
                "project_uuid": str(project.project_uuid),
                "job_count": len(in_flight),
                "job_uuids": [str(j.job_uuid) for j in in_flight],
            },
        )
    logger.info(
        "project.delete.inactivated",
        extra={
            "project_uuid": str(project.project_uuid),
            "account_uuid": str(project.account_uuid),
        },
    )
    return project


__all__ = ["delete_project"]
