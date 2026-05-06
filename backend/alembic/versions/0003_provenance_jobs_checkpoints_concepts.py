"""provenance, jobs, checkpoints, concepts (T-1.3.3)

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-03

DBB §B Abkürzung 2: provenance_objects must NOT have a satz_uuid column at all.
Addressing is `scope_type` + `scope_uuid`, polymorphic across the five canonical
scope_type values. Test in tests/schemas/test_provenance.py locks this in.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PO_TYPE = (
    "scan",
    "ocr",
    "manual_",
    "rule_binding",
    "translation",
    "lineage_event",
    "export_event",
)
_SCOPE_TYPE = ("segment", "page", "block", "account", "project")


def _check(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    # --- provenance_objects --------------------------------------------------
    op.create_table(
        "provenance_objects",
        sa.Column("po_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "po_type",
            sa.String(length=32),
            sa.CheckConstraint(_check("po_type", _PO_TYPE), name="ck_po_type_values"),
            nullable=False,
        ),
        sa.Column(
            "scope_type",
            sa.String(length=16),
            sa.CheckConstraint(
                _check("scope_type", _SCOPE_TYPE), name="ck_provenance_scope_type_values"
            ),
            nullable=False,
        ),
        sa.Column("scope_uuid", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("author_uuid", PG_UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_provenance_objects_scope",
        "provenance_objects",
        ["scope_type", "scope_uuid"],
    )
    op.create_index(
        "ix_provenance_objects_po_type",
        "provenance_objects",
        ["po_type"],
    )

    # --- jobs ----------------------------------------------------------------
    op.create_table(
        "jobs",
        sa.Column("job_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column(
            "project_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result", JSONB(), nullable=True),
        sa.Column("error", JSONB(), nullable=True),
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
    op.create_index("ix_jobs_project_uuid", "jobs", ["project_uuid"])

    # --- checkpoints ---------------------------------------------------------
    op.create_table(
        "checkpoints",
        sa.Column("checkpoint_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("jobs.job_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("step", sa.String(length=64), nullable=False),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_checkpoints_job_uuid", "checkpoints", ["job_uuid"])

    # --- concepts ------------------------------------------------------------
    op.create_table(
        "concepts",
        sa.Column("concept_id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("canonical_label", sa.String(length=255), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("gloss", sa.String(length=1024), nullable=True),
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


def downgrade() -> None:
    op.drop_table("concepts")
    op.drop_index("ix_checkpoints_job_uuid", table_name="checkpoints")
    op.drop_table("checkpoints")
    op.drop_index("ix_jobs_project_uuid", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_provenance_objects_po_type", table_name="provenance_objects")
    op.drop_index("ix_provenance_objects_scope", table_name="provenance_objects")
    op.drop_table("provenance_objects")
