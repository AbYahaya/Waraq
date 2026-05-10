"""Phase 2F-A — §4.15.3 ProjectQuranPassage snapshot table.

Revision ID: 0020
Revises: 0019
Create Date: 2026-05-09

Per §4.15.3 protection of project Qurʾān passages: this table is the
frozen snapshot mechanism. The CHECK constraint on `state` enumerates
the lifecycle vocabulary (`recognized`, `manually_confirmed`,
`corrected`, `rejected`, `refreshed`) per §4.15.5; the
`aya_index_start ≤ aya_index_end` CHECK enforces multi-āya range
sanity; the sura range CHECK reuses the §4.15.1 1..114 invariant.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_LIFECYCLE_STATES = (
    "recognized",
    "manually_confirmed",
    "corrected",
    "rejected",
    "refreshed",
)


def _check_in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "project_quran_passages",
        sa.Column("passage_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "satz_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("segments.satz_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "sura_index",
            sa.Integer(),
            sa.CheckConstraint(
                "sura_index BETWEEN 1 AND 114",
                name="ck_project_quran_passage_sura_range",
            ),
            nullable=False,
        ),
        sa.Column("aya_index_start", sa.Integer(), nullable=False),
        sa.Column("aya_index_end", sa.Integer(), nullable=False),
        sa.Column("snapshot_text_vocalized", sa.String(), nullable=False),
        sa.Column("snapshot_translation_text", sa.String(), nullable=True),
        sa.Column("ar_source_name", sa.String(length=64), nullable=False),
        sa.Column("ar_source_version", sa.String(length=64), nullable=False),
        sa.Column("translation_key", sa.String(length=64), nullable=True),
        sa.Column("translation_source_version", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "state",
            sa.String(length=32),
            sa.CheckConstraint(
                _check_in("state", _LIFECYCLE_STATES),
                name="ck_project_quran_passage_state",
            ),
            nullable=False,
            server_default="recognized",
        ),
        sa.Column(
            "last_decision_event_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("decision_events.decision_event_uuid", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_state_change_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_check_constraint(
        "ck_project_quran_passage_aya_range_order",
        "project_quran_passages",
        "aya_index_start >= 1 AND aya_index_end >= aya_index_start",
    )
    op.create_check_constraint(
        "ck_project_quran_passage_confidence_range",
        "project_quran_passages",
        "confidence >= 0.0 AND confidence <= 1.0",
    )
    op.create_index(
        "ix_project_quran_passage_project",
        "project_quran_passages",
        ["project_uuid"],
    )
    op.create_index(
        "ix_project_quran_passage_satz",
        "project_quran_passages",
        ["satz_uuid"],
    )
    op.create_index(
        "ix_project_quran_passage_state",
        "project_quran_passages",
        ["state"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_quran_passage_state", table_name="project_quran_passages")
    op.drop_index("ix_project_quran_passage_satz", table_name="project_quran_passages")
    op.drop_index("ix_project_quran_passage_project", table_name="project_quran_passages")
    op.drop_constraint(
        "ck_project_quran_passage_confidence_range",
        "project_quran_passages",
        type_="check",
    )
    op.drop_constraint(
        "ck_project_quran_passage_aya_range_order",
        "project_quran_passages",
        type_="check",
    )
    op.drop_table("project_quran_passages")
