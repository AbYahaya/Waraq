"""Phase 2A — §4.16.6 four-level Hadith data model (Single-source + Aggregate).

Revision ID: 0017
Revises: 0016
Create Date: 2026-05-09

Two new tables landing the §4.16.6 Level 2 + Level 3 result objects:

1. hadith_aggregate_results — Level 3 overall result per (passage,
   verification run). Carries reference matn + reference vocalization
   (which may come from different Single-source rows per §4.16.7),
   plus derived vokalisierungsklasse + binary vokalisierungs_konflikt,
   plus the multi-dimensional consensus_summary JSONB.

   Immutable per §4.16.6 / §4.9 E-10. New verification round writes a
   new aggregate (fresh aggregate_uuid); old one stays with
   is_aktiv=false and superseded_by_uuid pointing forward.

2. hadith_single_source_results — Level 2 per-source-per-run readings.
   Multiple rows per source per run permitted (hit variants). Source
   role is snapshot-at-run per §4.16.6 — frozen against current canon.

Level 1 anchor lives on the FK columns (satz_uuid + block_uuid +
ocr_rev_uuid). Level 4 user-decision overlay lives entirely on
existing decision_events rows pointing at the aggregate; no new table.

CHECK constraints:
- vokalisierungsklasse in {V-0, V-1, V-2}
- quellen_rolle in {pflicht, erweitert_aktiv, erweitert_sonderrolle,
                    erweitert_suspendiert}

hadithportal.com is canonically excluded as a source per §4.16.1; the
constraint is enforced by the consensus-engine ingest path (Phase 2F),
not at the column level.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_VOKALISIERUNGSKLASSEN = ("V-0", "V-1", "V-2")
_QUELLEN_ROLLEN = (
    "pflicht",
    "erweitert_aktiv",
    "erweitert_sonderrolle",
    "erweitert_suspendiert",
)


def _check_in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "hadith_aggregate_results",
        sa.Column("aggregate_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "satz_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("segments.satz_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "block_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("blocks.block_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "ocr_rev_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("revisions.rev_uuid", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "project_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("run_uuid", sa.String(length=64), nullable=False),
        sa.Column("reference_matn", sa.String(), nullable=True),
        sa.Column("reference_matn_source_uuid", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("reference_vocalization", sa.String(), nullable=True),
        sa.Column(
            "reference_vocalization_source_uuid", PG_UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "vokalisierungsklasse",
            sa.String(length=8),
            sa.CheckConstraint(
                _check_in("vokalisierungsklasse", _VOKALISIERUNGSKLASSEN),
                name="ck_hadith_aggregate_vokalisierungsklasse",
            ),
            nullable=False,
        ),
        sa.Column("vokalisierungs_konflikt", sa.Boolean(), nullable=False),
        sa.Column(
            "consensus_summary",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_aktiv", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "superseded_by_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("hadith_aggregate_results.aggregate_uuid", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "detected_at",
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
        "ix_hadith_aggregate_satz",
        "hadith_aggregate_results",
        ["satz_uuid"],
    )
    op.create_index(
        "ix_hadith_aggregate_block",
        "hadith_aggregate_results",
        ["block_uuid"],
    )
    op.create_index(
        "ix_hadith_aggregate_project",
        "hadith_aggregate_results",
        ["project_uuid"],
    )
    op.create_index(
        "ix_hadith_aggregate_run",
        "hadith_aggregate_results",
        ["run_uuid"],
    )
    op.create_index(
        "ix_hadith_aggregate_is_aktiv",
        "hadith_aggregate_results",
        ["is_aktiv"],
    )

    op.create_table(
        "hadith_single_source_results",
        sa.Column("single_source_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "aggregate_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey(
                "hadith_aggregate_results.aggregate_uuid", ondelete="RESTRICT"
            ),
            nullable=False,
        ),
        sa.Column("source_name", sa.String(length=64), nullable=False),
        sa.Column(
            "quellen_rolle",
            sa.String(length=32),
            sa.CheckConstraint(
                _check_in("quellen_rolle", _QUELLEN_ROLLEN),
                name="ck_hadith_single_source_quellen_rolle",
            ),
            nullable=False,
        ),
        sa.Column("matn_text", sa.String(), nullable=True),
        sa.Column("matn_vocalized", sa.String(), nullable=True),
        sa.Column(
            "raw_payload",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "website_uebersetzung",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "detected_at",
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
        "ix_hadith_single_source_aggregate",
        "hadith_single_source_results",
        ["aggregate_uuid"],
    )
    op.create_index(
        "ix_hadith_single_source_source_name",
        "hadith_single_source_results",
        ["source_name"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_hadith_single_source_source_name", table_name="hadith_single_source_results"
    )
    op.drop_index(
        "ix_hadith_single_source_aggregate", table_name="hadith_single_source_results"
    )
    op.drop_table("hadith_single_source_results")
    op.drop_index("ix_hadith_aggregate_is_aktiv", table_name="hadith_aggregate_results")
    op.drop_index("ix_hadith_aggregate_run", table_name="hadith_aggregate_results")
    op.drop_index("ix_hadith_aggregate_project", table_name="hadith_aggregate_results")
    op.drop_index("ix_hadith_aggregate_block", table_name="hadith_aggregate_results")
    op.drop_index("ix_hadith_aggregate_satz", table_name="hadith_aggregate_results")
    op.drop_table("hadith_aggregate_results")
