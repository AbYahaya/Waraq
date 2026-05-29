"""Add persisted OCR attention issue lifecycle.

Revision ID: 0028
Revises: 0027
Create Date: 2026-05-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ocr_attention_issues",
        sa.Column("issue_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "page_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("pages.page_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "block_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("blocks.block_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "satz_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("segments.satz_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source_po_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("provenance_objects.po_uuid", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("issue_type", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="warning"),
        sa.Column("group_key", sa.String(length=160), nullable=False),
        sa.Column("details", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "project_uuid",
            "satz_uuid",
            "issue_type",
            "source_po_uuid",
            name="uq_ocr_attention_issue_source",
        ),
    )
    op.create_index("ix_ocr_attention_issues_project_uuid", "ocr_attention_issues", ["project_uuid"])
    op.create_index("ix_ocr_attention_issues_page_uuid", "ocr_attention_issues", ["page_uuid"])
    op.create_index("ix_ocr_attention_issues_block_uuid", "ocr_attention_issues", ["block_uuid"])
    op.create_index("ix_ocr_attention_issues_satz_uuid", "ocr_attention_issues", ["satz_uuid"])
    op.create_index("ix_ocr_attention_issues_source_po_uuid", "ocr_attention_issues", ["source_po_uuid"])
    op.create_index("ix_ocr_attention_issues_group_key", "ocr_attention_issues", ["group_key"])

    op.create_table(
        "ocr_retry_candidates",
        sa.Column("candidate_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "issue_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("ocr_attention_issues.issue_uuid", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "project_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "page_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("pages.page_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "segment_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("segments.satz_uuid", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("engine", sa.String(length=32), nullable=False),
        sa.Column("dpi", sa.Integer(), nullable=False),
        sa.Column("crop", JSONB(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("current_text_snapshot", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="candidate"),
        sa.Column(
            "decision_event_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("decision_events.decision_event_uuid", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ocr_retry_candidates_issue_uuid", "ocr_retry_candidates", ["issue_uuid"])
    op.create_index("ix_ocr_retry_candidates_project_uuid", "ocr_retry_candidates", ["project_uuid"])
    op.create_index("ix_ocr_retry_candidates_page_uuid", "ocr_retry_candidates", ["page_uuid"])
    op.create_index("ix_ocr_retry_candidates_segment_uuid", "ocr_retry_candidates", ["segment_uuid"])


def downgrade() -> None:
    op.drop_index("ix_ocr_retry_candidates_segment_uuid", table_name="ocr_retry_candidates")
    op.drop_index("ix_ocr_retry_candidates_page_uuid", table_name="ocr_retry_candidates")
    op.drop_index("ix_ocr_retry_candidates_project_uuid", table_name="ocr_retry_candidates")
    op.drop_index("ix_ocr_retry_candidates_issue_uuid", table_name="ocr_retry_candidates")
    op.drop_table("ocr_retry_candidates")
    op.drop_index("ix_ocr_attention_issues_group_key", table_name="ocr_attention_issues")
    op.drop_index("ix_ocr_attention_issues_source_po_uuid", table_name="ocr_attention_issues")
    op.drop_index("ix_ocr_attention_issues_satz_uuid", table_name="ocr_attention_issues")
    op.drop_index("ix_ocr_attention_issues_block_uuid", table_name="ocr_attention_issues")
    op.drop_index("ix_ocr_attention_issues_page_uuid", table_name="ocr_attention_issues")
    op.drop_index("ix_ocr_attention_issues_project_uuid", table_name="ocr_attention_issues")
    op.drop_table("ocr_attention_issues")
