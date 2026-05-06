"""T-4.3.1 — ocr_error_instances table + pages.ocr_status column

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-05

Adds:
- `ocr_error_instances` table with F-XX detection rows. CHECK constraint on
  error_code (F-01..F-09 wire form) and on state (offen | aufgeloest).
  Page-rooted (NOT NULL FK); block-narrowed when applicable; no satz_uuid
  (Abkürzung 2 stays clean).
- `pages.ocr_status` column with state-machine CHECK
  (ausstehend | in_review | go | go_with_warning | no_go) defaulting to
  ausstehend.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_ERROR_CODE_VALUES = (
    "F-01",
    "F-02",
    "F-03",
    "F-04",
    "F-05",
    "F-06",
    "F-07",
    "F-08",
    "F-09",
)
_ERROR_STATE_VALUES = ("offen", "aufgeloest")
_OCR_STATUS_VALUES = ("ausstehend", "in_review", "go", "go_with_warning", "no_go")


def _check_in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "ocr_error_instances",
        sa.Column("ocr_error_instance_uuid", PG_UUID(as_uuid=True), primary_key=True),
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
            nullable=True,
        ),
        sa.Column(
            "error_code",
            sa.String(length=8),
            sa.CheckConstraint(
                _check_in("error_code", _ERROR_CODE_VALUES),
                name="ck_ocr_error_instance_error_code",
            ),
            nullable=False,
        ),
        sa.Column(
            "state",
            sa.String(length=32),
            sa.CheckConstraint(
                _check_in("state", _ERROR_STATE_VALUES),
                name="ck_ocr_error_instance_state",
            ),
            nullable=False,
            server_default="offen",
        ),
        sa.Column("details", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index(
        "ix_ocr_error_instances_page_state",
        "ocr_error_instances",
        ["page_uuid", "state"],
    )

    op.add_column(
        "pages",
        sa.Column(
            "ocr_status",
            sa.String(length=32),
            sa.CheckConstraint(
                _check_in("ocr_status", _OCR_STATUS_VALUES), name="ck_pages_ocr_status"
            ),
            nullable=False,
            server_default="ausstehend",
        ),
    )


def downgrade() -> None:
    op.drop_constraint("ck_pages_ocr_status", "pages", type_="check")
    op.drop_column("pages", "ocr_status")
    op.drop_index("ix_ocr_error_instances_page_state", table_name="ocr_error_instances")
    op.drop_table("ocr_error_instances")
