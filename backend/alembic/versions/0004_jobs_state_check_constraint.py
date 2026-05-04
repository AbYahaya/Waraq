"""jobs.state CHECK constraint (T-2.1.1)

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-04

Lands the CHECK constraint that 0003 deferred — the canonical Job state
machine values are now owned by T-2.1.1, so they can be enforced at the DB
level too.

Canonical states: pending | running | paused | completed | failed.
Transition graph enforced by waraq.jobs.service (the value set is enforced
here in Postgres).
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_JOB_STATES = ("pending", "running", "paused", "completed", "failed")


def upgrade() -> None:
    quoted = ", ".join(f"'{s}'" for s in _JOB_STATES)
    op.create_check_constraint(
        "ck_jobs_state_values",
        "jobs",
        f"state IN ({quoted})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_jobs_state_values", "jobs", type_="check")
