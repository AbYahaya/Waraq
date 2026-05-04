"""three identity types: revisions, decision_events, log_entries (T-1.3.2)

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-03

CAB §5.2 / DBB Abkürzung 3 — three identity types in three separate tables.
Also lands the deferred FK from 0001: segments.current_rev_uuid → revisions.rev_uuid.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Canonical value sets — keep here verbatim so the migration is self-describing.
_CHANGE_SOURCE = ("manual", "ocr", "re_translate", "style_profile")
_SCOPE_TYPE = ("segment", "page", "block", "account", "project")
_DECISION_SOURCE = (
    "ocr_review",
    "lock_management",
    "conflict_resolution",
    "translation_pipeline",
    "audit_resolution",
    "consistency_resolution",
    "glossary_management",
    "preflight_confirmation",
    "export_confirmation",
    "style_management",
)


def _check(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    # --- revisions -----------------------------------------------------------
    op.create_table(
        "revisions",
        sa.Column("rev_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "satz_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("segments.satz_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("before_text", sa.Text(), nullable=True),
        sa.Column("after_text", sa.Text(), nullable=False),
        sa.Column(
            "change_source",
            sa.String(length=32),
            sa.CheckConstraint(_check("change_source", _CHANGE_SOURCE), name="ck_change_source_values"),
            nullable=False,
        ),
        sa.Column("author_uuid", PG_UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_revisions_satz_uuid", "revisions", ["satz_uuid"])

    # --- decision_events -----------------------------------------------------
    op.create_table(
        "decision_events",
        sa.Column("decision_event_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "scope_type",
            sa.String(length=16),
            sa.CheckConstraint(_check("scope_type", _SCOPE_TYPE), name="ck_scope_type_values"),
            nullable=False,
        ),
        sa.Column("scope_uuid", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("decision_type", sa.String(length=64), nullable=False),
        sa.Column(
            "decision_source",
            sa.String(length=32),
            sa.CheckConstraint(
                _check("decision_source", _DECISION_SOURCE), name="ck_decision_source_values"
            ),
            nullable=False,
        ),
        sa.Column("content", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("actor_uuid", PG_UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_decision_events_scope", "decision_events", ["scope_type", "scope_uuid"]
    )

    # --- log_entries ---------------------------------------------------------
    op.create_table(
        "log_entries",
        sa.Column("log_id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("operation_type", sa.String(length=64), nullable=False),
        sa.Column("result", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("scope_type", sa.String(length=16), nullable=True),
        sa.Column("scope_uuid", PG_UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- finalize segments.current_rev_uuid FK (deferred from 0001) ---------
    op.create_foreign_key(
        "fk_segments_current_rev_uuid",
        "segments",
        "revisions",
        ["current_rev_uuid"],
        ["rev_uuid"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_segments_current_rev_uuid", "segments", type_="foreignkey")
    op.drop_table("log_entries")
    op.drop_index("ix_decision_events_scope", table_name="decision_events")
    op.drop_table("decision_events")
    op.drop_index("ix_revisions_satz_uuid", table_name="revisions")
    op.drop_table("revisions")
