"""Sprint 4 — Identitätstyp scaffolds + Hadith status + Pflichtfrage profile.

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-07

Six new tables in one migration (transactional):

1-4. Identitätstyp scaffold tables for K-02/K-04/K-05/K-06 (Sprint 4 §2,
     option (a) chosen 2026-05-07): formel_verzeichnis_eintraege,
     transliterations_muster_eintraege, quellen_identitaeten,
     strukturelle_schluessel. Each is structurally distinct (no shared
     discriminator — DBB §B Abkürzung 3 generalizes here). Bare
     v1.0 shape; substantive single definitions per EEB §13 deferred.

5.   hadith_passage_status table per Dokument 1 §4.16.4 + Sprint 4 §4.7.5:
     per-segment N-1..N-10 classification + lifecycle. H-X is computed
     at read time from N-X (deterministically derivable per §4.16.6).

6.   pflichtfrage_profile table per Sprint 4 §2 — saved Export-Profil
     pre-fills only. Active confirmation per export run is recorded as
     a Decision Event with decision_source=preflight_confirmation.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_HADITH_STELLEN_TYPEN = (
    "N-1",
    "N-2",
    "N-3",
    "N-4",
    "N-5",
    "N-6",
    "N-7",
    "N-8",
    "N-9",
    "N-10",
)
_HADITH_STATES = ("offen", "aufgeloest", "quittiert")


def _check_in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def _make_identity_type_table(name: str, uq_name: str) -> None:
    """The four Identitätstyp scaffolds share a v1.0 minimal shape but
    intentionally remain distinct tables (no shared discriminator)."""
    op.create_table(
        name,
        sa.Column("identity_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("identity_key", sa.String(length=255), nullable=False),
        sa.Column("source_pattern", sa.String(length=1024), nullable=False),
        sa.Column("expected_rendering", sa.String(length=1024), nullable=False),
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
        sa.UniqueConstraint("project_uuid", "identity_key", name=uq_name),
    )


def upgrade() -> None:
    # 1-4: Identitätstyp scaffold tables.
    _make_identity_type_table(
        "formel_verzeichnis_eintraege", "uq_formel_verzeichnis_project_key"
    )
    _make_identity_type_table(
        "transliterations_muster_eintraege", "uq_transliterations_muster_project_key"
    )
    _make_identity_type_table("quellen_identitaeten", "uq_quellen_identitaet_project_key")
    _make_identity_type_table(
        "strukturelle_schluessel", "uq_struktureller_schluessel_project_key"
    )

    # 5: Hadith passage status.
    op.create_table(
        "hadith_passage_status",
        sa.Column("hadith_status_uuid", PG_UUID(as_uuid=True), primary_key=True),
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
            "hadith_stellen_typ",
            sa.String(length=8),
            sa.CheckConstraint(
                _check_in("hadith_stellen_typ", _HADITH_STELLEN_TYPEN),
                name="ck_hadith_stellen_typ",
            ),
            nullable=False,
        ),
        sa.Column(
            "state",
            sa.String(length=16),
            sa.CheckConstraint(
                _check_in("state", _HADITH_STATES), name="ck_hadith_passage_state"
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
        "ix_hadith_passage_project_state",
        "hadith_passage_status",
        ["project_uuid", "state"],
    )
    op.create_index(
        "ix_hadith_passage_satz",
        "hadith_passage_status",
        ["satz_uuid"],
    )
    op.create_check_constraint(
        "ck_hadith_resolution_consistency",
        "hadith_passage_status",
        "(state = 'offen' AND resolved_at IS NULL "
        "AND resolution_decision_event_uuid IS NULL) "
        "OR (state IN ('aufgeloest', 'quittiert') "
        "AND resolved_at IS NOT NULL "
        "AND resolution_decision_event_uuid IS NOT NULL)",
    )

    # 6: Pflichtfrage profile.
    op.create_table(
        "pflichtfrage_profile",
        sa.Column("profil_uuid", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_uuid",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "frage_index",
            sa.Integer(),
            sa.CheckConstraint("frage_index BETWEEN 1 AND 4", name="ck_pflichtfrage_index_range"),
            nullable=False,
        ),
        sa.Column("frage_key", sa.String(length=64), nullable=False),
        sa.Column(
            "prefilled_answer",
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
        sa.UniqueConstraint("project_uuid", "frage_index", name="uq_pflichtfrage_profil_project_idx"),
    )


def downgrade() -> None:
    op.drop_table("pflichtfrage_profile")
    op.drop_constraint("ck_hadith_resolution_consistency", "hadith_passage_status", type_="check")
    op.drop_index("ix_hadith_passage_satz", table_name="hadith_passage_status")
    op.drop_index("ix_hadith_passage_project_state", table_name="hadith_passage_status")
    op.drop_table("hadith_passage_status")
    op.drop_table("strukturelle_schluessel")
    op.drop_table("quellen_identitaeten")
    op.drop_table("transliterations_muster_eintraege")
    op.drop_table("formel_verzeichnis_eintraege")
