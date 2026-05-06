"""T-5.1.2 — `conflict_instance` schema.

CRITICAL — Sprint 1's most load-bearing schema. Per CLAUDE.md §5.6 / DBB
Abkürzung 11: open `conflict_instance` rows MUST survive process restarts.
Holding them in memory is a structural failure: after a restart, locked
Segments would become silently overwritable. This table is the persistent
anchor for H-6 enforcement across restart boundaries.

Lifecycle:

- Detection (T-5.1.2 service `detect_conflict`) writes the row with
  `state = offen`. **No `decision_event_uuid` at this point.**
- Resolution writes (one of three canonical paths) sets `state =
  aufgeloest`, `resolution_type`, `decision_event_uuid` (FK to
  decision_events), and `resolved_at`. The pre-resolution row is **not
  otherwise mutated** — the row becomes its own historical evidence.

`satz_uuid` is a NOT NULL FK — conflict_instance is a legitimate segment-
scoped event table (per Sprint 1 §2). DBB Abkürzung 2 specifically targets
the *Provenance* table; conflict_instance, like revisions, is a domain-
specific segment-scoped event table that legitimately carries `satz_uuid`.

Conflict instance is **not** a PO. HG-S1-6 forbids writing it via
PROVENANCE-Kern. The Decision Event tied to its resolution is the
provenance anchor.
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


class ConflictInstance(Base, TimestampMixin):
    __tablename__ = "conflict_instances"

    conflict_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    satz_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("segments.satz_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    rule_source: Mapped[str] = mapped_column(String(32), nullable=False)
    conflict_type: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="offen", index=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Resolution-side fields. NULL at detection; populated on the offen →
    # aufgeloest transition. The decision_event_uuid FK is the anchor for
    # the user-decision moment (per Sprint 1 §2).
    resolution_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    decision_event_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("decision_events.decision_event_uuid", ondelete="RESTRICT"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
