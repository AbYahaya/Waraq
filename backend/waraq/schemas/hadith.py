"""T-9.1.2 — Hadith-Verifikationsstatus schema (Sprint 4 §2 §4.7.5 + §4.16.4).

Per Dokument 1 §4.16.4 — each hadith passage carries a state type
`hadith_stellen_typ` ∈ {N-1..N-10}. The verification class
`hadith_verifikationsklasse` ∈ {H-0, H-1, H-2} is **deterministically
derivable** from the passage type per:

    H-0 (review-internally tolerable, not export-blocking): N-1, N-3, N-9
    H-1 (logging-mandatory, warning-capable):                N-2, N-10
    H-2 (export-blocking until resolution):                  N-4, N-5, N-6,
                                                              N-7, N-8

Per §4.16.6 the H-X is "deterministically derivable, not independently
persisted". We persist only `hadith_stellen_typ`; `hadith_verifikationsklasse`
is computed at read time (see `waraq.preflight.hadith.derive_klasse`).

Resolution of H-2 follows the seven canonical action types per §4.16.5
(none of them adds a new `decision_source`; all map to existing
`translation_pipeline` or `conflict_resolution` values).

H-1 supports `go_with_warning` per §4.9 E-1: the user may proceed with
explicit warning-acknowledgement, which writes a Decision Event with
`decision_source=preflight_confirmation` (per §4.10).

This v1.0 minimal schema records the per-passage state for preflight
gate evaluation. The full §4.16.6 four-level Hadith result-object data
model (single-source + overall-result objects, source_role enum,
vokalisierungsklasse) is parked in Block 3 working drafts and lives
outside Sprint 4 scope.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base, TimestampMixin


class HadithPassageStatus(Base, TimestampMixin):
    """Per-segment hadith verification status (v1.0 minimal model).

    Anchored at the segment level (per §4.16.6 Level 1 — block-uuid +
    sentence-uuid + ocr-rev-uuid full anchor — we use satz_uuid alone for
    v1.0, since OCR-rev anchoring is captured indirectly via the segment's
    current_rev_uuid lineage).

    Lifecycle:
        offen → aufgeloest (via §4.16.5 action types) for H-2.
        offen → quittiert  (via go_with_warning) for H-1.
        H-0 cases do not trigger gate evaluation (per §4.7.5 / §4.16.4).
    """

    __tablename__ = "hadith_passage_status"

    hadith_status_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    satz_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("segments.satz_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    project_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # `N-1` .. `N-10` per §4.16.4. CHECK in migration.
    hadith_stellen_typ: Mapped[str] = mapped_column(String(8), nullable=False)
    # Resolution lifecycle — `offen | aufgeloest | quittiert`. CHECK in migration.
    state: Mapped[str] = mapped_column(
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
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
