"""§3.6 — Canonical 30-min translation-API-failure rule.

Per Dokument 1 §3.6:

  "On API failure: silent background marking of the affected passage,
   dashboard status indicator, automatic retry, manual retry button
   available to the user. After 30 minutes without recovery, active user
   information via in-app and email is triggered."

This watcher is the runtime hook that fires the §3.6 alert. Run it from
a periodic job (Celery beat / systemd timer / cron — deployment concern;
the canonical mechanism is the watcher contract here).

Inputs:
  - Translation `Job` rows with `state="failed"` whose `created_at` is
    older than 30 minutes — the canonical "no recovery in 30 min"
    predicate. Per the M3 translation pipeline a Job is one
    `translation` invocation; failed Jobs that don't auto-recover are
    the canonical signal.

Output:
  - One `notify(...)` call per (project_uuid, account_uuid) combination
    with at least one un-recovered failure. The notification service
    de-dupes within the 1-hour window so calling this watcher every
    few minutes won't spam.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.notifications.email_resend import EmailSender
from waraq.notifications.service import notify
from waraq.schemas import Job, Project
from waraq.schemas.enums import JobState

# Per §3.6 verbatim — 30 minutes without recovery.
_RECOVERY_DEADLINE = timedelta(minutes=30)

NOTIFICATION_KIND = "translation_api_failure_30min"


async def fire_translation_failure_notifications(
    *,
    session: AsyncSession,
    email_sender: EmailSender | None = None,
    now: datetime | None = None,
) -> list[str]:
    """Run one watcher pass; return the list of notification kinds /
    project titles that fired (empty when none).

    Returns project-title strings (one per fired notification) so
    callers can log what just went out without re-querying.
    """
    cutoff = (now if now is not None else datetime.now(UTC)) - _RECOVERY_DEADLINE

    result = await session.execute(
        select(Job, Project)
        .join(Project, Project.project_uuid == Job.project_uuid)
        .where(Job.job_type == "translation")
        .where(Job.state == JobState.FAILED.value)
        .where(Job.created_at <= cutoff)
    )
    rows = list(result.all())

    # Group by (project_uuid, account_uuid) — one notification per
    # affected project. The notify() de-dupe window absorbs repeated
    # firings across watcher runs.
    seen: set[tuple[str, str]] = set()
    fired: list[str] = []
    for job, project in rows:
        key = (str(project.project_uuid), str(project.account_uuid))
        if key in seen:
            continue
        seen.add(key)

        await notify(
            session=session,
            account_uuid=project.account_uuid,
            kind=NOTIFICATION_KIND,
            title=f"Translation pipeline stalled — {project.name}",
            body=(
                f"At least one translation job for {project.name!r} has been in "
                f"the FAILED state for more than 30 minutes without recovery. "
                f"Open the project to retry or inspect the failure (job "
                f"{job.job_uuid})."
            ),
            email_sender=email_sender,
        )
        fired.append(project.name)
    return fired


def _silence_unused(_x: Iterable[Job]) -> None:
    """Marker for the Iterable import (used as a parameter type elsewhere)."""


__all__ = ["NOTIFICATION_KIND", "fire_translation_failure_notifications"]
