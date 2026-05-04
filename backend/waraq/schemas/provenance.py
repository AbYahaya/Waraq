"""T-1.3.3 — Provenance Object table.

CAB §5.3 / CLAUDE.md §5.3: a single Provenance table holds all seven canonical
PO types (scan, ocr, manual_, rule_binding, translation, lineage_event,
export_event). PROVENANCE-Kern is the only writer to this table (T-1.6.1
service); the schema does not enforce that — service-layer responsibility.

DBB §B Abkürzung 2 — structural failure modes:

    Provenance-Tabelle with `satz_uuid NOT NULL`.

A `satz_uuid` column on Provenance — NULL or NOT NULL — is wrong by
construction. It would block page-scoped POs (SCAN), project-scoped POs
(EXPORT_EVENT), and account-scoped POs. The canonical addressing pattern is
`scope_type` + `scope_uuid` (polymorphic). A test in
tests/schemas/test_provenance.py locks this in.

POs are append-only history records. They do not carry an `active` flag or
`updated_at` (same rationale as event tables: H-5 inactivation does not apply
to immutable provenance history; soft-delete of provenance would be worse
than the rule it tries to honor).
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base
from waraq.schemas.enums import POType, ScopeType


class ProvenanceObject(Base):
    """Sole table for all seven canonical PO types."""

    __tablename__ = "provenance_objects"

    po_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    po_type: Mapped[POType] = mapped_column(String(32), nullable=False)
    scope_type: Mapped[ScopeType] = mapped_column(String(16), nullable=False)
    scope_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    # System-authored POs (LINEAGE_EVENT, automatic SCAN finalization) carry no actor.
    author_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.account_uuid", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "po_type IN (" + ", ".join(f"'{e.value}'" for e in POType) + ")",
            name="ck_po_type_values",
        ),
        CheckConstraint(
            "scope_type IN (" + ", ".join(f"'{e.value}'" for e in ScopeType) + ")",
            name="ck_provenance_scope_type_values",
        ),
    )
