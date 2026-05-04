"""checkpoints.created_at uses clock_timestamp() (T-2.1.2)

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-04

PostgreSQL `now()` returns transaction-start time. Multiple checkpoints
inside a single transaction would all get the same created_at, making
`read_latest_checkpoint` indeterminate when a Job advances through several
steps in one transaction. `clock_timestamp()` returns wall-clock time per
call, so each row gets a distinct timestamp.

Checkpoint ordering is functional (resume picks the latest), not just
informational, so this matters. Other event tables (revisions,
decision_events, log_entries, provenance_objects) still use now() — the
ordering ambiguity there is acceptable for now and can be revisited if a
real use case surfaces.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "checkpoints",
        "created_at",
        server_default=sa.func.clock_timestamp(),
    )


def downgrade() -> None:
    op.alter_column(
        "checkpoints",
        "created_at",
        server_default=sa.func.now(),
    )
