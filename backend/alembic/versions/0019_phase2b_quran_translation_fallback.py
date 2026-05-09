"""Phase 2B — Qurʾān translation local fallback (§4.15.1).

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-09

Per §4.15.1 the primary carrier of German/English Qurʾān translations
is the quranenc.com API; the local copy is the **fallback on API
failure** and the source of weekly-sync refreshes. Schema mirrors the
shape of `ar_referenz_verses` (source_name → translation_key + language;
otherwise identical). Sura range CHECK 1..114; āya CHECK ≥ 1.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quran_translation_verses",
        sa.Column("verse_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("translation_key", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("source_version", sa.String(length=64), nullable=False),
        sa.Column(
            "sura_index",
            sa.Integer(),
            sa.CheckConstraint(
                "sura_index BETWEEN 1 AND 114",
                name="ck_quran_translation_verse_sura_range",
            ),
            nullable=False,
        ),
        sa.Column(
            "aya_index",
            sa.Integer(),
            sa.CheckConstraint(
                "aya_index >= 1",
                name="ck_quran_translation_verse_aya_min",
            ),
            nullable=False,
        ),
        sa.Column("translation_text", sa.String(), nullable=False),
        sa.Column("footnotes", sa.String(), nullable=True),
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
            "translation_key",
            "source_version",
            "sura_index",
            "aya_index",
            name="uq_quran_translation_verse_key_sura_aya",
        ),
    )
    op.create_index(
        "ix_quran_translation_verse_key_active",
        "quran_translation_verses",
        ["translation_key", "active"],
    )
    op.create_index(
        "ix_quran_translation_verse_lookup",
        "quran_translation_verses",
        ["translation_key", "sura_index", "aya_index"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_quran_translation_verse_lookup", table_name="quran_translation_verses"
    )
    op.drop_index(
        "ix_quran_translation_verse_key_active",
        table_name="quran_translation_verses",
    )
    op.drop_table("quran_translation_verses")
