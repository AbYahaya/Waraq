"""Per-account notification preferences (`account_preferences` table).

Lazy-create on first read so existing accounts don't need a backfill
migration — `get_or_create_preferences` returns the row, creating the
default (both channels enabled) on the fly when missing.
"""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.schemas import AccountPreferences


async def get_or_create_preferences(
    *,
    session: AsyncSession,
    account_uuid: _uuid.UUID,
) -> AccountPreferences:
    result = await session.execute(
        select(AccountPreferences).where(AccountPreferences.account_uuid == account_uuid)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row
    row = AccountPreferences(
        account_uuid=account_uuid,
        email_notifications_enabled=True,
        in_app_notifications_enabled=True,
    )
    session.add(row)
    await session.flush()
    return row


async def update_preferences(
    *,
    session: AsyncSession,
    account_uuid: _uuid.UUID,
    email_enabled: bool | None = None,
    in_app_enabled: bool | None = None,
) -> AccountPreferences:
    """Patch one or both toggles. None leaves the field unchanged."""
    row = await get_or_create_preferences(session=session, account_uuid=account_uuid)
    if email_enabled is not None:
        row.email_notifications_enabled = email_enabled
    if in_app_enabled is not None:
        row.in_app_notifications_enabled = in_app_enabled
    await session.flush()
    return row


__all__ = ["get_or_create_preferences", "update_preferences"]
