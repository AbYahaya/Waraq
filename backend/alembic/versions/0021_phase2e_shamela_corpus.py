"""Phase 2E — Shamela / OpenITI corpus tables.

Revision ID: 0021
Revises: 0020
Create Date: 2026-05-09

Two tables:
- `shamela_registry` (PK: text_slug + source_version) — text-level metadata.
- `shamela_sections` (PK: section_uuid; composite FK to registry).

The CHECK on `shamela_registry.text_type` enumerates the canonical
type vocabulary (`lexicon`, `hadith`, `fiqh`, `tafsir`, `other`).
v1.0 ingest writes only `lexicon` and `hadith` rows; the wider set is
present so future supplementary texts (Tafsir, Fiqh) drop in without
a migration.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TEXT_TYPES = ("lexicon", "hadith", "fiqh", "tafsir", "other")


def _check_in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "shamela_registry",
        sa.Column("text_slug", sa.String(length=64), primary_key=True),
        sa.Column("source_version", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("source_uri", sa.String(length=1024), nullable=False),
        sa.Column(
            "text_type",
            sa.String(length=32),
            sa.CheckConstraint(
                _check_in("text_type", _TEXT_TYPES),
                name="ck_shamela_registry_text_type",
            ),
            nullable=False,
        ),
        sa.Column(
            "is_kutub_as_sitta",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "metadata_json",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
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
    op.create_index(
        "ix_shamela_registry_kutub",
        "shamela_registry",
        ["is_kutub_as_sitta", "active"],
    )

    op.create_table(
        "shamela_sections",
        sa.Column("section_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("text_slug", sa.String(length=64), nullable=False),
        sa.Column("source_version", sa.String(length=64), nullable=False),
        sa.Column("section_index", sa.Integer(), nullable=False),
        sa.Column(
            "section_path",
            sa.String(length=1024),
            nullable=False,
            server_default="",
        ),
        sa.Column("text_arabic", sa.String(), nullable=False),
        sa.Column("text_skeleton", sa.String(), nullable=False),
        sa.Column(
            "metadata_json",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
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
        sa.ForeignKeyConstraint(
            ["text_slug", "source_version"],
            ["shamela_registry.text_slug", "shamela_registry.source_version"],
            name="fk_shamela_section_registry",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "text_slug",
            "source_version",
            "section_index",
            name="uq_shamela_section_text_version_index",
        ),
    )
    op.create_index(
        "ix_shamela_section_skeleton",
        "shamela_sections",
        ["text_skeleton"],
    )
    op.create_index(
        "ix_shamela_section_text_active",
        "shamela_sections",
        ["text_slug", "active"],
    )


def downgrade() -> None:
    op.drop_index("ix_shamela_section_text_active", table_name="shamela_sections")
    op.drop_index("ix_shamela_section_skeleton", table_name="shamela_sections")
    op.drop_table("shamela_sections")
    op.drop_index("ix_shamela_registry_kutub", table_name="shamela_registry")
    op.drop_table("shamela_registry")
