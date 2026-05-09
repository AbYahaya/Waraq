"""T-7.3.1 — translation_observations + musterkandidaten tables

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-06

CHECK constraints:
- ck_observation_source_class: Lernquellen-Asymmetrie 5-class taxonomy
  per Dokument 1 §4.13 (ASCII transliteration; umlauts removed).
- ck_musterkandidat_state: only `kandidat` at this layer (T-7.3.2 in
  Sprint 3 will alter the constraint to add `bestaetigt`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_SOURCE_CLASS_VALUES = (
    "bestaetigte_referenzsaetze",
    "manuelle_nutzerregeln",
    "akzeptierte_ki_vorschlaege",
    "korrigierte_ki_vorschlaege",
    "ignorierte_ki_vorschlaege",
)
_STATE_VALUES = ("kandidat",)


def _check_in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    # translation_observations
    op.create_table(
        "translation_observations",
        sa.Column("observation_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "revision_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("revisions.rev_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "satz_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("segments.satz_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "project_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_text", sa.String(length=8192), nullable=False),
        sa.Column("prior_translation", sa.String(length=8192), nullable=False),
        sa.Column("user_correction", sa.String(length=8192), nullable=False),
        sa.Column(
            "terminology_bindings",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "source_class",
            sa.String(length=48),
            sa.CheckConstraint(
                _check_in("source_class", _SOURCE_CLASS_VALUES),
                name="ck_observation_source_class",
            ),
            nullable=False,
        ),
        sa.Column("pattern_key", sa.String(length=8192), nullable=False),
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
        "ix_observation_project_pattern",
        "translation_observations",
        ["project_uuid", "pattern_key"],
    )

    # musterkandidaten
    op.create_table(
        "musterkandidaten",
        sa.Column("musterkandidat_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("pattern_key", sa.String(length=8192), nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column(
            "sample_corrections",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "state",
            sa.String(length=16),
            sa.CheckConstraint(
                _check_in("state", _STATE_VALUES),
                name="ck_musterkandidat_state",
            ),
            nullable=False,
            server_default="kandidat",
        ),
        sa.Column(
            "first_observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
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
        "ix_musterkandidat_project_pattern",
        "musterkandidaten",
        ["project_uuid", "pattern_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_musterkandidat_project_pattern", table_name="musterkandidaten")
    op.drop_table("musterkandidaten")
    op.drop_index("ix_observation_project_pattern", table_name="translation_observations")
    op.drop_table("translation_observations")
