"""Phase 3 sub-batch F — notifications + per-account preferences.

Revision ID: 0022
Revises: 0021
Create Date: 2026-05-09

Two tables:
- `notifications` (per-account in-app notifications + email-dispatch tracking).
- `account_preferences` (per-account email_enabled / in_app_enabled toggles).

Per Dokument 1 §2.1 / §2.2 / §3.6: in-app + email notification channels.
The §3.6 30-min translation-pipeline failure rule writes here; future
triggers (export complete, Hadith H-2 surfaced, etc.) join the same path.

Per §2.2 user-controllable channels: each account decides whether email
notifications fire, whether in-app fires, or both.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("notification_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "account_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("accounts.account_uuid", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        # Stable kind identifier for filtering / per-kind preferences in
        # future. v1.0 callers use snake_case keys like
        # `translation_api_failure_30min`.
        sa.Column("kind", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        # Read receipts — NULL until the user marks it read.
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        # Email dispatch tracking — NULL when email channel was disabled
        # for this account or when send failed; populated with the
        # successful-send timestamp otherwise.
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "account_preferences",
        sa.Column(
            "account_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("accounts.account_uuid", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "email_notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "in_app_notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        # TimestampMixin columns (inherited on the ORM model).
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("account_preferences")
    op.drop_table("notifications")
