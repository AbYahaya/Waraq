"""Sprint -0.5 — accounts table + FK wire-up

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-04

Creates the `accounts` table and wires the deferred FK constraints from:
- projects.account_uuid → accounts.account_uuid    (NOT NULL — required)
- revisions.author_uuid → accounts.account_uuid    (nullable — system-authored)
- decision_events.actor_uuid → accounts.account_uuid (nullable)
- provenance_objects.author_uuid → accounts.account_uuid (nullable)

If any of these source tables already contain rows whose values don't
correspond to existing accounts, the FK creation will fail. In dev that
typically means running `docker compose down -v && up -d` to wipe state
before applying this migration. In production this would be a backfill
migration — out of scope here since there's no production data yet.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("account_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=60), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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

    # FK wire-ups. ondelete=RESTRICT mirrors the rest of the schema —
    # accounts are deactivated, never deleted (H-5).
    op.create_foreign_key(
        "fk_projects_account_uuid",
        "projects",
        "accounts",
        ["account_uuid"],
        ["account_uuid"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_projects_account_uuid", "projects", ["account_uuid"])

    op.create_foreign_key(
        "fk_revisions_author_uuid",
        "revisions",
        "accounts",
        ["author_uuid"],
        ["account_uuid"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_decision_events_actor_uuid",
        "decision_events",
        "accounts",
        ["actor_uuid"],
        ["account_uuid"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_provenance_objects_author_uuid",
        "provenance_objects",
        "accounts",
        ["author_uuid"],
        ["account_uuid"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_provenance_objects_author_uuid", "provenance_objects", type_="foreignkey"
    )
    op.drop_constraint("fk_decision_events_actor_uuid", "decision_events", type_="foreignkey")
    op.drop_constraint("fk_revisions_author_uuid", "revisions", type_="foreignkey")
    op.drop_index("ix_projects_account_uuid", table_name="projects")
    op.drop_constraint("fk_projects_account_uuid", "projects", type_="foreignkey")
    op.drop_table("accounts")
