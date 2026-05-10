"""Notification dispatch service — see module docstring for canonical scope.

Honors `account_preferences` for per-channel gating and de-duplicates
within a 1-hour window so a periodic watcher (the §3.6 30-min rule
runs every few minutes) doesn't spam the user with the same alert.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity.service import new_uuid
from waraq.notifications.email_resend import EmailSender, make_default_email_sender
from waraq.notifications.preferences import get_or_create_preferences
from waraq.schemas import Account, Notification

# Per-(account, kind) dedupe window. Re-firing the same kind within
# this window with identical title+body is a no-op. Width is a v1.0
# implementation choice; the periodic-watcher pattern (§3.6 30-min rule
# polled every 5 min) means this prevents 6× spam per hour.
_DEDUPE_WINDOW = timedelta(hours=1)


async def notify(
    *,
    session: AsyncSession,
    account_uuid: _uuid.UUID,
    kind: str,
    title: str,
    body: str,
    email_sender: EmailSender | None = None,
) -> Notification | None:
    """Dispatch a notification to one account across enabled channels.

    Returns the new `Notification` row when one was written, or None
    when dedup suppressed it. Email send is best-effort: a failure
    leaves `email_sent_at` NULL on the row but the in-app row IS
    written (so the user still sees the alert when they open the
    panel).

    When the account has `in_app_notifications_enabled=False` the
    in-app row is NOT written; the function returns None even if the
    email channel fired (operator visibility is via the Resend
    dashboard in that case).
    """
    prefs = await get_or_create_preferences(session=session, account_uuid=account_uuid)

    # Dedupe lookup.
    cutoff = datetime.now(UTC) - _DEDUPE_WINDOW
    dedupe_q = await session.execute(
        select(Notification)
        .where(Notification.account_uuid == account_uuid)
        .where(Notification.kind == kind)
        .where(Notification.title == title)
        .where(Notification.body == body)
        .where(Notification.created_at >= cutoff)
        .limit(1)
    )
    if dedupe_q.scalar_one_or_none() is not None:
        return None

    if not prefs.in_app_notifications_enabled:
        # Account opted out of in-app — still try email if that channel
        # is enabled (matches §2.2 "user-controllable channels").
        if prefs.email_notifications_enabled:
            account = await session.get(Account, account_uuid)
            if account is not None:
                sender = email_sender if email_sender is not None else make_default_email_sender()
                await sender.send(to_email=account.email, subject=title, body_text=body)
        return None

    notification = Notification(
        notification_uuid=new_uuid(),
        account_uuid=account_uuid,
        kind=kind,
        title=title,
        body=body,
    )
    session.add(notification)
    await session.flush()

    # Email channel — best-effort.
    if prefs.email_notifications_enabled:
        account = await session.get(Account, account_uuid)
        if account is not None:
            sender = email_sender if email_sender is not None else make_default_email_sender()
            sent = await sender.send(to_email=account.email, subject=title, body_text=body)
            if sent:
                notification.email_sent_at = datetime.now(UTC)
                await session.flush()

    return notification


async def list_notifications(
    *,
    session: AsyncSession,
    account_uuid: _uuid.UUID,
    only_unread: bool = False,
    limit: int = 50,
) -> Sequence[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.account_uuid == account_uuid)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if only_unread:
        stmt = stmt.where(Notification.read_at.is_(None))
    result = await session.execute(stmt)
    return list(result.scalars())


async def mark_read(
    *,
    session: AsyncSession,
    account_uuid: _uuid.UUID,
    notification_uuid: _uuid.UUID,
) -> bool:
    """Mark one notification read. Returns True if the row was found
    + still belonged to the account; False otherwise (the caller can
    decide whether to surface a 404)."""
    result = await session.execute(
        select(Notification)
        .where(Notification.notification_uuid == notification_uuid)
        .where(Notification.account_uuid == account_uuid)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return False
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
        await session.flush()
    return True


async def mark_all_read(
    *,
    session: AsyncSession,
    account_uuid: _uuid.UUID,
) -> int:
    """Mark every unread notification for the account as read.
    Returns the number of rows touched."""
    now = datetime.now(UTC)
    result = cast(
        CursorResult[Any],
        await session.execute(
            update(Notification)
            .where(Notification.account_uuid == account_uuid)
            .where(Notification.read_at.is_(None))
            .values(read_at=now)
        ),
    )
    await session.flush()
    return int(result.rowcount or 0)


__all__ = ["list_notifications", "mark_all_read", "mark_read", "notify"]
