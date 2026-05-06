"""T-8.2.1 — Konsistenz-Befund-Tabelle schema.

Per Sprint 4 §2 (working basis, M2 ships the harness; rule bodies back-fill
in M5 alongside T-8.1.x audit infrastructure).

The Konsistenz-Befund table is **distinct** from the Befund-Tabelle of
T-8.1.1 (audit findings). They are not unified — each identity-type
inconsistency has its own subject_type, and the table holds findings
independently of audit severity classification.

Per Sprint 4 §2 acceptance:
- `subject_type` is the identity-type the rule binds to
  (concept_id / formel_verzeichnis_id / entity_id /
  transliterations_muster / source_identity / structural_key /
  concept_id-cross). **No K-rule reads `surface_form` directly for equality
  comparison** — that's the canonical structural failure mode (DBB §B
  Abkürzung 10).
- `vorschlag` carries a system suggestion (never automatically applied).
- Resolution requires a Decision Event with `scope_type=project` and
  `decision_type=konsistenzgruppe_verbindlich`.

ASCII transliteration: the canon writes `auflösungsstatus`; the column /
value form here is `aufloesungsstatus` to keep the wire/DB layer ASCII-safe
(same convention as `OcrErrorState.AUFGELOEST`, `ConflictState.AUFGELOEST`).
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base, TimestampMixin


class KonsistenzBefund(Base, TimestampMixin):
    __tablename__ = "konsistenz_befunde"

    konsistenz_befund_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True
    )
    project_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Which K-rule produced the finding ("K-01" .. "K-07"). CHECK in migration.
    k_rule: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    # The identity-type the rule binds to. CHECK in migration.
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # The identity key — typically a UUID string for K-01/K-03/K-07, a
    # transliteration-pattern key for K-04, etc. The semantics depend on
    # subject_type; column type is plain VARCHAR for cross-rule uniformity.
    subject_key: Mapped[str] = mapped_column(String(255), nullable=False)
    # `kritisch | hoch | mittel`. CHECK in migration.
    verstossklasse: Mapped[str] = mapped_column(String(16), nullable=False)
    # JSONB list of segment-UUID strings affected by the inconsistency.
    # We don't FK each element (would require a child table); the list is
    # advisory data for the resolver UI.
    betroffene_segment_uuids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    # System-generated suggestion describing how to resolve. Never
    # automatically applied (Sprint 4 §2). Shape: `{"action": "...", ...}`.
    vorschlag: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    # offen | aufgeloest | quittiert. CHECK in migration.
    aufloesungsstatus: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="offen", index=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_decision_event_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("decision_events.decision_event_uuid", ondelete="RESTRICT"),
        nullable=True,
    )
