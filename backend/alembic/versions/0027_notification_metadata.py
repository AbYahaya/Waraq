"""Add actionable notification metadata.

Revision ID: 0027
Revises: 0026
Create Date: 2026-05-22

Notifications started as plain text rows. This adds nullable routing
metadata so the UI can render severity, project/page links, action
labels, and issue references without breaking existing notifications.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="info"),
    )
    op.add_column("notifications", sa.Column("target_url", sa.String(length=512), nullable=True))
    op.add_column("notifications", sa.Column("action_label", sa.String(length=64), nullable=True))
    op.add_column(
        "notifications",
        sa.Column(
            "project_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("projects.project_uuid", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "notifications",
        sa.Column(
            "page_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("pages.page_uuid", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("notifications", sa.Column("issue_uuid", PG_UUID(as_uuid=True), nullable=True))
    op.add_column("notifications", sa.Column("issue_kind", sa.String(length=64), nullable=True))
    op.create_index("ix_notifications_project_uuid", "notifications", ["project_uuid"])
    op.create_index("ix_notifications_page_uuid", "notifications", ["page_uuid"])


def downgrade() -> None:
    op.drop_index("ix_notifications_page_uuid", table_name="notifications")
    op.drop_index("ix_notifications_project_uuid", table_name="notifications")
    op.drop_column("notifications", "issue_kind")
    op.drop_column("notifications", "issue_uuid")
    op.drop_column("notifications", "page_uuid")
    op.drop_column("notifications", "project_uuid")
    op.drop_column("notifications", "action_label")
    op.drop_column("notifications", "target_url")
    op.drop_column("notifications", "severity")
