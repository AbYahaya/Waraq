"""Phase 3 sub-batch F — notifications + per-account preferences ORM."""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func, true
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base, TimestampMixin


class Notification(Base):
    """One in-app notification row scoped to an Account.

    Email-channel dispatch is recorded inline (`email_sent_at`) so the
    UI can surface "delivered via in-app + email" vs "in-app only".
    Per-row provenance is intentionally minimal — notifications are
    operational signal, not canon-decision events.
    """

    __tablename__ = "notifications"

    notification_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    account_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.account_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, server_default="info")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    target_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    action_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    page_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pages.page_uuid", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    issue_uuid: Mapped[_uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    issue_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccountPreferences(Base, TimestampMixin):
    """Per-account notification toggles (§2.2 user-controllable channels).

    PK is the account_uuid — at most one row per account. The notification
    service reads this row to decide which channel(s) to fire when
    `notify(...)` runs. Defaults are both-on so newly-registered users
    see notifications immediately.
    """

    __tablename__ = "account_preferences"

    account_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.account_uuid", ondelete="RESTRICT"),
        primary_key=True,
    )
    email_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=true()
    )
    in_app_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=true()
    )
