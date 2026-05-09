"""Sprint-OCR — POType += OCR_EXPORT_EVENT + DecisionEvent.related_export_attempt_id

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-06

Per OCR Endfassung v1.3:
- CR-1.1: new POType OCR_EXPORT_EVENT (Sprint-OCR §1.4 distinction).
- CR-1.5 / CR-1.6: DecisionEvent gains `related_export_attempt_id`
  (VARCHAR(64) NULL) to bind `export_confirmation` decisions to a
  specific export attempt.

Drop and recreate the existing `ck_po_type_values` constraint to include
'ocr_export_event'.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PO_TYPE_VALUES = (
    "scan",
    "ocr",
    "manual_",
    "rule_binding",
    "translation",
    "lineage_event",
    "export_event",
    "ocr_export_event",
)


def _check_in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    op.drop_constraint("ck_po_type_values", "provenance_objects", type_="check")
    op.create_check_constraint(
        "ck_po_type_values",
        "provenance_objects",
        _check_in("po_type", _PO_TYPE_VALUES),
    )
    op.add_column(
        "decision_events",
        sa.Column("related_export_attempt_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_decision_events_related_export_attempt_id",
        "decision_events",
        ["related_export_attempt_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_decision_events_related_export_attempt_id", table_name="decision_events")
    op.drop_column("decision_events", "related_export_attempt_id")
    op.drop_constraint("ck_po_type_values", "provenance_objects", type_="check")
    op.create_check_constraint(
        "ck_po_type_values",
        "provenance_objects",
        _check_in("po_type", _PO_TYPE_VALUES[:-1]),  # drop OCR_EXPORT_EVENT
    )
