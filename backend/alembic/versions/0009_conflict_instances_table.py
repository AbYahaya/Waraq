"""T-5.1.2 — conflict_instances table

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-05

Per CLAUDE.md §5.6 / DBB Abkürzung 11: open `conflict_instance` rows MUST
survive process restarts. This table is the persistent anchor.

Columns:
- conflict_uuid              UUID PK
- satz_uuid                  UUID NOT NULL FK segments.satz_uuid
- rule_source                VARCHAR(32) NOT NULL CHECK in
                             {'glossary','terminology','style_profile'}
- conflict_type              VARCHAR(64) NOT NULL (open vocabulary)
- state                      VARCHAR(16) NOT NULL CHECK in {'offen','aufgeloest'}
                             default 'offen', index
- detected_at                TIMESTAMPTZ NOT NULL default now()
- resolution_type            VARCHAR(32) NULL CHECK in
                             {'lokale_ausnahme','glossar_anpassen','sperrflag_aufheben'}
- decision_event_uuid        UUID NULL FK decision_events.decision_event_uuid
- resolved_at                TIMESTAMPTZ NULL
- context                    JSONB NOT NULL default '{}'::jsonb
- TimestampMixin (active/created_at/updated_at)

Resolution-side fields are NULL at detection and populated atomically on
the offen → aufgeloest transition. CHECK constraint
`ck_conflict_resolution_consistency` enforces that resolution_type +
decision_event_uuid + resolved_at are either all NULL (offen) or all NOT
NULL (aufgeloest), so the row can never end up in a half-resolved state.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_RULE_SOURCE_VALUES = ("glossary", "terminology", "style_profile")
_CONFLICT_STATE_VALUES = ("offen", "aufgeloest")
_RESOLUTION_TYPE_VALUES = (
    "lokale_ausnahme",
    "glossar_anpassen",
    "sperrflag_aufheben",
)


def _check_in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "conflict_instances",
        sa.Column("conflict_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "satz_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("segments.satz_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "rule_source",
            sa.String(length=32),
            sa.CheckConstraint(
                _check_in("rule_source", _RULE_SOURCE_VALUES),
                name="ck_conflict_rule_source",
            ),
            nullable=False,
        ),
        sa.Column("conflict_type", sa.String(length=64), nullable=False),
        sa.Column(
            "state",
            sa.String(length=16),
            sa.CheckConstraint(
                _check_in("state", _CONFLICT_STATE_VALUES), name="ck_conflict_state"
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
        sa.Column(
            "resolution_type",
            sa.String(length=32),
            sa.CheckConstraint(
                f"resolution_type IS NULL OR {_check_in('resolution_type', _RESOLUTION_TYPE_VALUES)}",
                name="ck_conflict_resolution_type",
            ),
            nullable=True,
        ),
        sa.Column(
            "decision_event_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("decision_events.decision_event_uuid", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("context", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
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
        "ix_conflict_instances_satz_state",
        "conflict_instances",
        ["satz_uuid", "state"],
    )
    op.create_index(
        "ix_conflict_instances_state",
        "conflict_instances",
        ["state"],
    )
    op.create_check_constraint(
        "ck_conflict_resolution_consistency",
        "conflict_instances",
        "(state = 'offen' AND resolution_type IS NULL AND decision_event_uuid IS NULL "
        "AND resolved_at IS NULL) "
        "OR (state = 'aufgeloest' AND resolution_type IS NOT NULL "
        "AND decision_event_uuid IS NOT NULL AND resolved_at IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_conflict_resolution_consistency", "conflict_instances", type_="check")
    op.drop_index("ix_conflict_instances_state", table_name="conflict_instances")
    op.drop_index("ix_conflict_instances_satz_state", table_name="conflict_instances")
    op.drop_table("conflict_instances")
