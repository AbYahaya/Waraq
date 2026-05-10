"""Phase 3 sub-batch F — notifications + preferences + idle-timeout
support endpoints.

Endpoints:
- GET  /me/notifications                 — list (defaults to all, can filter unread)
- POST /me/notifications/{u}/read        — mark one read
- POST /me/notifications/read-all        — mark all unread read
- GET  /me/notifications/preferences     — current per-channel toggles
- PUT  /me/notifications/preferences     — patch toggles
- GET  /me/active-background-jobs        — count of running/pending jobs (idle-timeout suppression)
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select

from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.notifications import (
    get_or_create_preferences,
    list_notifications,
    mark_all_read,
    mark_read,
    update_preferences,
)
from waraq.schemas import Job, Notification, Project
from waraq.schemas.enums import JobState

router = APIRouter(tags=["notifications"])


class NotificationDto(BaseModel):
    notification_uuid: _uuid.UUID
    kind: str
    title: str
    body: str
    created_at: str
    read_at: str | None
    email_sent_at: str | None


class NotificationListResponse(BaseModel):
    items: list[NotificationDto]
    unread_count: int


@router.get("/me/notifications", response_model=NotificationListResponse)
async def my_notifications(
    session: DbSession,
    current: CurrentAccount,
    only_unread: bool = False,
    limit: int = 50,
) -> NotificationListResponse:
    rows = await list_notifications(
        session=session,
        account_uuid=current.account_uuid,
        only_unread=only_unread,
        limit=limit,
    )
    unread_q = await session.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.account_uuid == current.account_uuid)
        .where(Notification.read_at.is_(None))
    )
    unread = int(unread_q.scalar_one())
    return NotificationListResponse(
        items=[
            NotificationDto(
                notification_uuid=r.notification_uuid,
                kind=r.kind,
                title=r.title,
                body=r.body,
                created_at=r.created_at.isoformat(),
                read_at=r.read_at.isoformat() if r.read_at is not None else None,
                email_sent_at=(
                    r.email_sent_at.isoformat() if r.email_sent_at is not None else None
                ),
            )
            for r in rows
        ],
        unread_count=unread,
    )


@router.post(
    "/me/notifications/{notification_uuid}/read",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def mark_one_read(
    notification_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> None:
    found = await mark_read(
        session=session,
        account_uuid=current.account_uuid,
        notification_uuid=notification_uuid,
    )
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


class MarkAllReadResponse(BaseModel):
    marked: int


@router.post("/me/notifications/read-all", response_model=MarkAllReadResponse)
async def mark_all_read_route(
    session: DbSession,
    current: CurrentAccount,
) -> MarkAllReadResponse:
    n = await mark_all_read(session=session, account_uuid=current.account_uuid)
    return MarkAllReadResponse(marked=n)


class PreferencesDto(BaseModel):
    email_notifications_enabled: bool
    in_app_notifications_enabled: bool


@router.get("/me/notifications/preferences", response_model=PreferencesDto)
async def my_preferences(
    session: DbSession,
    current: CurrentAccount,
) -> PreferencesDto:
    prefs = await get_or_create_preferences(session=session, account_uuid=current.account_uuid)
    return PreferencesDto(
        email_notifications_enabled=prefs.email_notifications_enabled,
        in_app_notifications_enabled=prefs.in_app_notifications_enabled,
    )


class PreferencesPatchRequest(BaseModel):
    email_notifications_enabled: bool | None = None
    in_app_notifications_enabled: bool | None = None


@router.put("/me/notifications/preferences", response_model=PreferencesDto)
async def update_my_preferences(
    req: PreferencesPatchRequest,
    session: DbSession,
    current: CurrentAccount,
) -> PreferencesDto:
    prefs = await update_preferences(
        session=session,
        account_uuid=current.account_uuid,
        email_enabled=req.email_notifications_enabled,
        in_app_enabled=req.in_app_notifications_enabled,
    )
    return PreferencesDto(
        email_notifications_enabled=prefs.email_notifications_enabled,
        in_app_notifications_enabled=prefs.in_app_notifications_enabled,
    )


# --- §2.2 / §7.4 background-aware idle timeout support -----------------


class ActiveBackgroundJobsResponse(BaseModel):
    """Count of jobs that should suppress the 2-hour idle timeout per
    §2.2 / §7.4 ("No timeout during an active background process").

    `running_or_pending` covers both PENDING (just queued) and RUNNING
    jobs across all the user's projects — either qualifies as "active
    background process" for the canonical timeout rule.
    """

    running_or_pending: int


@router.get("/me/active-background-jobs", response_model=ActiveBackgroundJobsResponse)
async def my_active_background_jobs(
    session: DbSession,
    current: CurrentAccount,
) -> ActiveBackgroundJobsResponse:
    result = await session.execute(
        select(func.count())
        .select_from(Job)
        .join(Project, Project.project_uuid == Job.project_uuid)
        .where(Project.account_uuid == current.account_uuid)
        .where(Job.state.in_([JobState.PENDING.value, JobState.RUNNING.value]))
    )
    n = int(result.scalar_one())
    return ActiveBackgroundJobsResponse(running_or_pending=n)
