"""T-8.2.1 — konsistenz_befunde table (M2 closeout: harness ships, K-rule
bodies are stubbed and back-fill alongside T-8.1.x in M5)

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-06

CHECK constraints:
- ck_konsistenz_befund_k_rule: K-01 .. K-07
- ck_konsistenz_befund_subject_type: 7-value subject-type taxonomy
- ck_konsistenz_befund_verstossklasse: kritisch | hoch | mittel
- ck_konsistenz_befund_aufloesungsstatus: offen | aufgeloest | quittiert
- ck_konsistenz_resolution_consistency: half-resolved rows impossible
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_K_RULE_VALUES = ("K-01", "K-02", "K-03", "K-04", "K-05", "K-06", "K-07")
# Per Sprint 4 §2: each K-rule binds to its OWN subject_type. K-01 and K-07
# share `concept_id` semantically; K-04 binds to a transliteration-pattern
# key (not an FK); K-05 binds to a source-identity record key.
_SUBJECT_TYPE_VALUES = (
    "concept_id",
    "formel_verzeichnis_id",
    "entity_id",
    "transliterations_muster",
    "source_identity",
    "structural_key",
)
_VERSTOSSKLASSE_VALUES = ("kritisch", "hoch", "mittel")
_STATUS_VALUES = ("offen", "aufgeloest", "quittiert")


def _check_in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "konsistenz_befunde",
        sa.Column("konsistenz_befund_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "k_rule",
            sa.String(length=8),
            sa.CheckConstraint(
                _check_in("k_rule", _K_RULE_VALUES), name="ck_konsistenz_befund_k_rule"
            ),
            nullable=False,
        ),
        sa.Column(
            "subject_type",
            sa.String(length=32),
            sa.CheckConstraint(
                _check_in("subject_type", _SUBJECT_TYPE_VALUES),
                name="ck_konsistenz_befund_subject_type",
            ),
            nullable=False,
        ),
        sa.Column("subject_key", sa.String(length=255), nullable=False),
        sa.Column(
            "verstossklasse",
            sa.String(length=16),
            sa.CheckConstraint(
                _check_in("verstossklasse", _VERSTOSSKLASSE_VALUES),
                name="ck_konsistenz_befund_verstossklasse",
            ),
            nullable=False,
        ),
        sa.Column(
            "betroffene_segment_uuids",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("vorschlag", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "aufloesungsstatus",
            sa.String(length=16),
            sa.CheckConstraint(
                _check_in("aufloesungsstatus", _STATUS_VALUES),
                name="ck_konsistenz_befund_aufloesungsstatus",
            ),
            nullable=False,
            server_default="offen",
        ),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resolution_decision_event_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("decision_events.decision_event_uuid", ondelete="RESTRICT"),
            nullable=True,
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
        "ix_konsistenz_befund_project_status",
        "konsistenz_befunde",
        ["project_uuid", "aufloesungsstatus"],
    )
    op.create_check_constraint(
        "ck_konsistenz_resolution_consistency",
        "konsistenz_befunde",
        "(aufloesungsstatus = 'offen' AND resolved_at IS NULL "
        "AND resolution_decision_event_uuid IS NULL) "
        "OR (aufloesungsstatus IN ('aufgeloest', 'quittiert') "
        "AND resolved_at IS NOT NULL "
        "AND resolution_decision_event_uuid IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_konsistenz_resolution_consistency", "konsistenz_befunde", type_="check")
    op.drop_index("ix_konsistenz_befund_project_status", table_name="konsistenz_befunde")
    op.drop_table("konsistenz_befunde")
