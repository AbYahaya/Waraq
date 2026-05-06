"""T-5.2.1 — concept binding columns (binding_level + project_uuid + account_uuid)

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-05

Adds the columns required by the glossary service:

- `binding_level`        VARCHAR NOT NULL DEFAULT 'project'  (CHECK in {'project','account'})
- `project_uuid`         UUID NULL REFERENCES projects.project_uuid
- `account_uuid`         UUID NULL REFERENCES accounts.account_uuid
- CHECK ck_concept_binding_consistency: exactly one of project_uuid /
  account_uuid is set, matching binding_level.

The defaults are a migration convenience for any pre-existing rows; in
practice no Concept rows exist yet (Sprint 0 created the table; no service
has populated it). Production rollout would seed binding_level/project_uuid
explicitly per row.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "concepts",
        sa.Column(
            "binding_level",
            sa.String(length=16),
            nullable=False,
            server_default="project",
        ),
    )
    op.add_column(
        "concepts",
        sa.Column("project_uuid", PG_UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "concepts",
        sa.Column("account_uuid", PG_UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_concepts_project_uuid",
        "concepts",
        "projects",
        ["project_uuid"],
        ["project_uuid"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_concepts_account_uuid",
        "concepts",
        "accounts",
        ["account_uuid"],
        ["account_uuid"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_concepts_binding_level_values",
        "concepts",
        "binding_level IN ('project', 'account')",
    )
    # Exactly-one-set constraint: project-bound rows must carry
    # project_uuid (and not account_uuid); account-bound rows the inverse.
    # Pre-existing rows (none in dev, but defensive) all default to
    # binding_level='project' — they would fail this check unless backfilled,
    # so we run a backfill first.
    op.execute(
        "UPDATE concepts SET project_uuid = gen_random_uuid() "
        "WHERE binding_level = 'project' AND project_uuid IS NULL"
    )
    op.create_check_constraint(
        "ck_concepts_binding_consistency",
        "concepts",
        "(binding_level = 'project' AND project_uuid IS NOT NULL AND account_uuid IS NULL) "
        "OR (binding_level = 'account' AND account_uuid IS NOT NULL AND project_uuid IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_concepts_binding_consistency", "concepts", type_="check")
    op.drop_constraint("ck_concepts_binding_level_values", "concepts", type_="check")
    op.drop_constraint("fk_concepts_account_uuid", "concepts", type_="foreignkey")
    op.drop_constraint("fk_concepts_project_uuid", "concepts", type_="foreignkey")
    op.drop_column("concepts", "account_uuid")
    op.drop_column("concepts", "project_uuid")
    op.drop_column("concepts", "binding_level")
