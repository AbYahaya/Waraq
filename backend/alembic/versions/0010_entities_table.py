"""§4.19 — entities table

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-06

Per Dokument 1 §4.19: 5-value canonical category taxonomy plus binding
scope (project|account, same pattern as Concept).

CHECK constraints:
- ck_entities_category: enum membership for the 5 §4.19 categories
- ck_entities_binding_level_values: 'project' or 'account'
- ck_entities_binding_consistency: exactly one of project_uuid/account_uuid
  set, matching binding_level
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_CATEGORY_VALUES = (
    "scholar_or_person",
    "historical_place",
    "unit_of_measurement",
    "arabic_book",
    "dynasty_or_epoch",
)


def _check_in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "entities",
        sa.Column("entity_id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "category",
            sa.String(length=32),
            sa.CheckConstraint(
                _check_in("category", _CATEGORY_VALUES), name="ck_entities_category"
            ),
            nullable=False,
        ),
        sa.Column("canonical_label", sa.String(length=255), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("short_bio", sa.String(length=4096), nullable=True),
        sa.Column("metadata_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_refs", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "binding_level",
            sa.String(length=16),
            sa.CheckConstraint(
                "binding_level IN ('project', 'account')",
                name="ck_entities_binding_level_values",
            ),
            nullable=False,
            server_default="project",
        ),
        sa.Column(
            "project_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "account_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("accounts.account_uuid", ondelete="RESTRICT"),
            nullable=True,
        ),
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
    op.create_check_constraint(
        "ck_entities_binding_consistency",
        "entities",
        "(binding_level = 'project' AND project_uuid IS NOT NULL AND account_uuid IS NULL) "
        "OR (binding_level = 'account' AND account_uuid IS NOT NULL AND project_uuid IS NULL)",
    )
    op.create_index(
        "ix_entities_category_scope",
        "entities",
        ["category", "project_uuid", "account_uuid"],
    )


def downgrade() -> None:
    op.drop_index("ix_entities_category_scope", table_name="entities")
    op.drop_constraint("ck_entities_binding_consistency", "entities", type_="check")
    op.drop_table("entities")
