"""Phase 2D — AR-Referenzbestand (Qurʾān reference collection).

Revision ID: 0018
Revises: 0017
Create Date: 2026-05-09

Per §4.15.1: independent local collection, target-language-independent,
no API path. Source picked for v1.0: Tanzil-Hafs (Uthmani vocalized
text, CC BY 3.0). Source-name-tagged so a future re-ingest from a
different canonical source overwrites cleanly without touching project
data (per §4.15.3 protection).

Schema:
- (sura_index, aya_index) keyed; sura_index CHECKed to 1..114; aya_index
  CHECKed to >= 1.
- text_skeleton index for OCR Stage-3 matching (§4.15.2 local-only).
- (source_name, source_version) index + active index for re-ingest /
  fallback selection.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ar_referenz_verses",
        sa.Column("verse_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("source_name", sa.String(length=64), nullable=False),
        sa.Column("source_version", sa.String(length=64), nullable=False),
        sa.Column(
            "sura_index",
            sa.Integer(),
            sa.CheckConstraint(
                "sura_index BETWEEN 1 AND 114",
                name="ck_ar_referenz_verse_sura_range",
            ),
            nullable=False,
        ),
        sa.Column(
            "aya_index",
            sa.Integer(),
            sa.CheckConstraint(
                "aya_index >= 1",
                name="ck_ar_referenz_verse_aya_min",
            ),
            nullable=False,
        ),
        sa.Column("text_vocalized", sa.String(), nullable=False),
        sa.Column("text_skeleton", sa.String(), nullable=False),
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
        sa.UniqueConstraint(
            "source_name",
            "source_version",
            "sura_index",
            "aya_index",
            name="uq_ar_referenz_verse_source_sura_aya",
        ),
    )
    op.create_index(
        "ix_ar_referenz_verse_skeleton",
        "ar_referenz_verses",
        ["text_skeleton"],
    )
    op.create_index(
        "ix_ar_referenz_verse_source_active",
        "ar_referenz_verses",
        ["source_name", "active"],
    )


def downgrade() -> None:
    op.drop_index("ix_ar_referenz_verse_source_active", table_name="ar_referenz_verses")
    op.drop_index("ix_ar_referenz_verse_skeleton", table_name="ar_referenz_verses")
    op.drop_table("ar_referenz_verses")
