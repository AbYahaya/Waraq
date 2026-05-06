"""initial: projects, pages, blocks, segments (T-1.3.1)

Revision ID: 0001
Revises:
Create Date: 2026-05-03

Hand-written; no autogenerate. Establishes the four canonical entity tables
for Sprint 0 T-1.3.1. Identity-types (Revision, Decision Event, Log-Eintrag)
arrive in 0002 / T-1.3.2; Job, Checkpoint, Provenance in 0003 / T-1.3.3.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("project_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("account_uuid", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
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

    op.create_table(
        "pages",
        sa.Column("page_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("page_index", sa.Integer(), nullable=False),
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
    op.create_index("ix_pages_project_uuid", "pages", ["project_uuid"])

    op.create_table(
        "blocks",
        sa.Column("block_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "page_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("pages.page_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("block_type", sa.String(length=32), nullable=False),
        sa.Column("block_index", sa.Integer(), nullable=False),
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
    op.create_index("ix_blocks_page_uuid", "blocks", ["page_uuid"])

    op.create_table(
        "segments",
        sa.Column("satz_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "block_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("blocks.block_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("satz_index", sa.Integer(), nullable=False),
        sa.Column(
            "lock_flag",
            sa.String(length=32),
            sa.CheckConstraint(
                "lock_flag IN ('none', 'manual_local', 'manual_editorial')",
                name="ck_segments_lock_flag",
            ),
            nullable=False,
            server_default="none",
        ),
        # FK to revisions.rev_uuid added in 0002 (T-1.3.2). Column-only here.
        sa.Column("current_rev_uuid", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
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
    op.create_index("ix_segments_block_uuid", "segments", ["block_uuid"])


def downgrade() -> None:
    op.drop_index("ix_segments_block_uuid", table_name="segments")
    op.drop_table("segments")
    op.drop_index("ix_blocks_page_uuid", table_name="blocks")
    op.drop_table("blocks")
    op.drop_index("ix_pages_project_uuid", table_name="pages")
    op.drop_table("pages")
    op.drop_table("projects")
