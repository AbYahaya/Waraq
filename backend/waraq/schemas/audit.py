"""T-8.1.1 — Audit Befund-Tabelle.

Per Sprint 3 §2:

- Befund-Tabelle is its OWN table — NOT an FK extension of Revision or
  Decision Event. The three identity types (Revision / Decision Event /
  Log-Eintrag) plus this table form a fourth, distinct, segment-scoped
  finding store. (R-S3-02 / Audit-Befund-Tabelle-Eigene-Tabelle-Test.)

- Detection fields are immutable post-creation: `regelkennung`,
  `verstossklasse`, `schweregrad`, `detected_at`. Only the resolution
  triple (`aufloesungsstatus`, `resolved_at`, `resolution_decision_event_uuid`)
  may be updated, and only on a transition `offen → aufgelöst | quittiert`.
  Enforced at the service level + Audit-Befund-Immutable-Detection-Test.

- Audit-runs never write to Segment, TRANSLATION-PO, or Revision (H-4 /
  T-H4-02). The Befund row is the only output of an audit-run, plus a
  Log-Eintrag bookending the run.

The verstossklasse / schweregrad split mirrors Dokument 1 §4.6:

    Schweregrad  Verstossklasse   Preflight slot (Sprint 4/5)
    ----------   --------------   ---------------------------
    kritisch     blockierend      P-03  (blocks export)
    hoch         pflichthinweis   P-04  (per-finding resolution required)
    mittel       hinweis          W-01  (warning, non-blocking)

Quittierung is permitted only for `mittel`-severity (Sprint 3 §2 rule).
The service layer enforces this; CHECK constraints just enforce the
enum membership.
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


class Befund(Base, TimestampMixin):
    """One audit finding per (segment, regelkennung) tuple per audit-run.

    Cross-rule audit interactions (a single Segment violating multiple
    rules in one pass) produce multiple rows — one per rule — per
    Sprint 3 §B "the Befund-Tabelle producing one row per (Segment,
    regelkennung) tuple; downstream gate logic decides aggregation."
    """

    __tablename__ = "audit_befunde"

    befund_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

    # Segment scope. Required: a Befund is always anchored at exactly one
    # Segment. Per Abkürzung 2 allowlist this segment-scoped event table
    # is canonically permitted alongside revisions / conflict_instances /
    # translation_observations.
    satz_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("segments.satz_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Project scope for project-wide audit-run queries (severity rollups,
    # per-class counts). Joined-through via segment → block → page →
    # project would also work; this denormalizes for cheap filtering.
    project_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Audit-run that produced this finding. FK to jobs.job_uuid because
    # every audit-run is a Sprint-0 Job (job_type='audit'). The Job's
    # state machine + Log-Eintrag give the run-level audit trail; the
    # Befund row is the per-finding emission.
    audit_run_job_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.job_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Detection fields (IMMUTABLE post-create; service-layer enforced):
    regelkennung: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    verstossklasse: Mapped[str] = mapped_column(String(16), nullable=False)
    schweregrad: Mapped[str] = mapped_column(String(16), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Free-form rule-specific context (e.g., the offending substring,
    # which terminology entry was violated, the source/target excerpt).
    detection_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    # Resolution triple — mutable only on offen → aufgeloest|quittiert.
    aufloesungsstatus: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="offen", index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_decision_event_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("decision_events.decision_event_uuid", ondelete="RESTRICT"),
        nullable=True,
    )
