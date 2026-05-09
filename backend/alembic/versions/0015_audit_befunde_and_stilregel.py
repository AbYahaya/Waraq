"""Sprint 3 — audit_befunde + bestaetigte_stilregeln + extend musterkandidat.state CHECK.

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-07

Three structural changes in one migration (transactional):

1. New `audit_befunde` table per T-8.1.1:
   - Detection-side immutability is enforced at the service layer; the
     CHECK constraints here ensure the enums are sane.
   - Resolution columns are nullable; the CHECK
     `ck_audit_resolution_consistency` makes a half-resolved row
     impossible at the DB level (mirrors `konsistenz_befunde`).

2. New `bestaetigte_stilregeln` table per T-7.3.2:
   - One row per confirmed Stilregel; `musterkandidat_uuid` UNIQUE so a
     Musterkandidat can only be confirmed once.
   - Confirmation Decision Event FK is RESTRICT — the audit trail must
     survive forever.

3. `musterkandidaten.state` CHECK constraint extended to accept
   `bestaetigt` and `verworfen` in addition to `kandidat`. T-7.3.1 only
   needed `kandidat`; T-7.3.2 adds the explicit user-action transitions.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_VERSTOSSKLASSE_VALUES = ("blockierend", "pflichthinweis", "hinweis")
_SCHWEREGRAD_VALUES = ("kritisch", "hoch", "mittel")
_AUFLOESUNG_VALUES = ("offen", "aufgeloest", "quittiert")
_MUSTER_STATE_VALUES_NEW = ("kandidat", "bestaetigt", "verworfen")


def _check_in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    # 1. audit_befunde
    op.create_table(
        "audit_befunde",
        sa.Column("befund_uuid", PG_UUID(as_uuid=True), primary_key=True),
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
        sa.Column(
            "audit_run_job_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("jobs.job_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("regelkennung", sa.String(length=8), nullable=False),
        sa.Column(
            "verstossklasse",
            sa.String(length=16),
            sa.CheckConstraint(
                _check_in("verstossklasse", _VERSTOSSKLASSE_VALUES),
                name="ck_audit_verstossklasse",
            ),
            nullable=False,
        ),
        sa.Column(
            "schweregrad",
            sa.String(length=16),
            sa.CheckConstraint(
                _check_in("schweregrad", _SCHWEREGRAD_VALUES),
                name="ck_audit_schweregrad",
            ),
            nullable=False,
        ),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "detection_context",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "aufloesungsstatus",
            sa.String(length=16),
            sa.CheckConstraint(
                _check_in("aufloesungsstatus", _AUFLOESUNG_VALUES),
                name="ck_audit_aufloesungsstatus",
            ),
            nullable=False,
            server_default="offen",
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
        # Half-resolved rows are forbidden: either fully open or fully
        # resolved/quittiert with both timestamp + decision_event present.
        sa.CheckConstraint(
            "(aufloesungsstatus = 'offen' "
            " AND resolved_at IS NULL "
            " AND resolution_decision_event_uuid IS NULL) "
            "OR (aufloesungsstatus IN ('aufgeloest', 'quittiert') "
            " AND resolved_at IS NOT NULL "
            " AND resolution_decision_event_uuid IS NOT NULL)",
            name="ck_audit_resolution_consistency",
        ),
    )
    op.create_index("ix_audit_befund_segment", "audit_befunde", ["satz_uuid"])
    op.create_index("ix_audit_befund_project", "audit_befunde", ["project_uuid"])
    op.create_index("ix_audit_befund_regelkennung", "audit_befunde", ["regelkennung"])
    op.create_index("ix_audit_befund_status", "audit_befunde", ["aufloesungsstatus"])
    op.create_index("ix_audit_befund_run", "audit_befunde", ["audit_run_job_uuid"])

    # 2. bestaetigte_stilregeln
    op.create_table(
        "bestaetigte_stilregeln",
        sa.Column("stilregel_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "musterkandidat_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("musterkandidaten.musterkandidat_uuid", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "project_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "confirmation_decision_event_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("decision_events.decision_event_uuid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("annotation", sa.String(length=8192), nullable=True),
        sa.Column("pattern_key", sa.String(length=8192), nullable=False),
        sa.Column(
            "source_classes",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
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
        "ix_stilregel_project_pattern",
        "bestaetigte_stilregeln",
        ["project_uuid", "pattern_key"],
    )

    # 3. Extend musterkandidat.state CHECK to allow `bestaetigt` and
    #    `verworfen`. Postgres doesn't support ALTER on CHECKs in place,
    #    so drop the old one and recreate.
    op.drop_constraint(
        "ck_musterkandidat_state",
        "musterkandidaten",
        type_="check",
    )
    op.create_check_constraint(
        "ck_musterkandidat_state",
        "musterkandidaten",
        _check_in("state", _MUSTER_STATE_VALUES_NEW),
    )


def downgrade() -> None:
    # Reverse step 3 — narrow CHECK back to just `kandidat`.
    op.drop_constraint(
        "ck_musterkandidat_state",
        "musterkandidaten",
        type_="check",
    )
    op.create_check_constraint(
        "ck_musterkandidat_state",
        "musterkandidaten",
        _check_in("state", ("kandidat",)),
    )
    op.drop_index("ix_stilregel_project_pattern", table_name="bestaetigte_stilregeln")
    op.drop_table("bestaetigte_stilregeln")
    op.drop_index("ix_audit_befund_run", table_name="audit_befunde")
    op.drop_index("ix_audit_befund_status", table_name="audit_befunde")
    op.drop_index("ix_audit_befund_regelkennung", table_name="audit_befunde")
    op.drop_index("ix_audit_befund_project", table_name="audit_befunde")
    op.drop_index("ix_audit_befund_segment", table_name="audit_befunde")
    op.drop_table("audit_befunde")
