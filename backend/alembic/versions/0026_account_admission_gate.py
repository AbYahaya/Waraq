"""Phase 5 sub-batch M — admission gate columns on `accounts`.

Revision ID: 0026
Revises: 0025
Create Date: 2026-05-12

Adds four columns to `accounts` for the simplified admin-approval gate
(canon §2.3 row 8 partial; tier system + subscription deferred per user
scope decision 2026-05-12):

  - `approval_status` (text-encoded enum: pending/approved/rejected)
    NOT NULL DEFAULT 'pending'. Existing rows back-fill to 'approved'
    so the migration doesn't lock out the dev account or test fixtures.
  - `approved_at` (timestamptz) nullable.
  - `approved_by_account_uuid` (uuid, FK accounts) nullable.
  - `rejection_reason` (text) nullable.

A CHECK constraint enforces the value set at the DB level. CHECK
constraint name `ck_accounts_approval_status` follows the existing
convention (see migration 0024 `ck_blocks_block_type`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CANONICAL_STATUSES = ("pending", "approved", "rejected")


def upgrade() -> None:
    # Step 1: add the column nullable so we can back-fill existing rows
    # before flipping to NOT NULL.
    op.add_column(
        "accounts",
        sa.Column(
            "approval_status",
            sa.String(length=16),
            nullable=True,
        ),
    )
    # Step 2: back-fill all existing accounts to 'approved' so the
    # admission gate doesn't retroactively lock out pre-M accounts
    # (developer / test fixtures / any prior dev-shell registration).
    op.execute("UPDATE accounts SET approval_status = 'approved' WHERE approval_status IS NULL")
    # Step 3: flip to NOT NULL + server-default 'pending' for new rows.
    op.alter_column(
        "accounts",
        "approval_status",
        nullable=False,
        server_default=sa.text("'pending'"),
    )
    # Step 4: CHECK constraint matching the ApprovalStatus enum values.
    op.create_check_constraint(
        "ck_accounts_approval_status",
        "accounts",
        f"approval_status IN ({', '.join(repr(s) for s in _CANONICAL_STATUSES)})",
    )

    op.add_column(
        "accounts",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "accounts",
        sa.Column(
            "approved_by_account_uuid",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.account_uuid", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.add_column(
        "accounts",
        sa.Column("rejection_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("accounts", "rejection_reason")
    op.drop_column("accounts", "approved_by_account_uuid")
    op.drop_column("accounts", "approved_at")
    op.drop_constraint("ck_accounts_approval_status", "accounts", type_="check")
    op.drop_column("accounts", "approval_status")
