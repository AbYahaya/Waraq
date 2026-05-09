"""T-7.3.1 — Promotion pipeline schema (Stufen 1-2).

Two tables:

- `translation_observations` — Stufe 1 observations: user-corrected
  translation revisions with the bindings/context active at correction
  time. NOT a PO. NOT a Decision Event. (Sprint 2 §2: "stored in a
  service-internal table".)

- `musterkandidaten` — Stufe 2 candidates: recurring observation
  patterns that crossed a configurable threshold. Registration writes a
  Log-Eintrag via EVENTING. Inert with respect to translation production
  (Sprint 2 §2: "translation passes for new Segments do not consult
  Musterkandidaten — only confirmed glossary entries").

Sprint 2 §2 (per DBB §7.5): the granularity at which observations are
partitioned across the five learning-source classes (Lernquellen-
Asymmetrie per Dokument 1 §4.13) is left open. The `source_class` column
records the metadata so a later refinement can partition without
migration. ASCII transliteration of the canonical class names (umlauts
removed) keeps the wire/DB layer ASCII-clean.

H-7 protection (R-S2-09 / T-H7-01): Musterkandidat has only ONE state at
this layer (`kandidat`). There is no transition function from `kandidat`
→ `bestaetigt` here — that path lives exclusively in T-7.3.2 (Sprint 3),
guarded by an explicit user action.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base, TimestampMixin


class TranslationObservation(Base, TimestampMixin):
    __tablename__ = "translation_observations"

    observation_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    # Anchor at the manual Revision that captured the correction.
    revision_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("revisions.rev_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    satz_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("segments.satz_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Project for scope-filtered aggregation.
    project_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_text: Mapped[str] = mapped_column(String(8192), nullable=False)
    prior_translation: Mapped[str] = mapped_column(String(8192), nullable=False)
    user_correction: Mapped[str] = mapped_column(String(8192), nullable=False)
    # Terminology bindings active at correction time. Same shape as
    # TranslationContext.terminology_bindings (concept_id_str → rendering).
    terminology_bindings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    # Per Dokument 1 §4.13: 5 canonical learning-source classes. CHECK in
    # migration. Granularity per DBB §7.5 deliberately left open — recorded,
    # not yet used to partition behaviour.
    source_class: Mapped[str] = mapped_column(String(48), nullable=False)
    # Aggregation key: a normalized form of `source_text` used to group
    # recurring observations into a single Musterkandidat. Simple-string
    # normalization in v1.0; richer pattern extraction is later refinement.
    pattern_key: Mapped[str] = mapped_column(String(8192), nullable=False, index=True)


class Musterkandidat(Base, TimestampMixin):
    __tablename__ = "musterkandidaten"

    musterkandidat_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    project_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    pattern_key: Mapped[str] = mapped_column(String(8192), nullable=False, index=True)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # Sample of the user corrections aggregated into this candidate, useful
    # for the future T-7.3.2 confirmation surface. Bounded length is the
    # service's responsibility.
    sample_corrections: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    # State machine: `kandidat` (initial) → `bestaetigt` | `verworfen`
    # via T-7.3.2 user actions. CHECK constraint extended in migration
    # 0015. H-7: there is NO automatic `kandidat → bestaetigt` path —
    # only `bestaetige_stilregel(uuid)` (and `verwerfe_musterkandidat`
    # for the alternative branch).
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="kandidat", index=True
    )
    first_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BestaetigteStilregel(Base, TimestampMixin):
    """T-7.3.2 — bestätigte Stilregel.

    A user-confirmed style rule. Distinct entity from the Musterkandidat
    that produced it (Promotion-Stufe3-Stilregel-Distinct-Entity-Test).
    The Musterkandidat retains its observation evidence and is marked
    `bestaetigt`.

    Per Sprint 3 §2: confirmed Stilregel does NOT auto-apply to
    translation production this sprint (Promotion-Stufe3-Stilregel-Inert-
    In-Translation-Test). It exists, is queryable, but RULE_BINDING
    (T-7.2.1) does not consult it. The deferred boundary is canonical
    per DBB §7.5 + Dokument C v1.1 §3.

    `source_classes` preserves the Lernquellen-Asymmetrie metadata of
    the underlying observations as a JSONB array of distinct source-class
    values aggregated at confirmation time (Promotion-Stufe3-Source-Class-
    Preserved-Test). Per DBB §7.5 the GRANULARITY of how source-classes
    influence eligibility is open; this column just carries the data so
    a future canon decision can layer filtering without migration.
    """

    __tablename__ = "bestaetigte_stilregeln"

    stilregel_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

    # Anchor at the Musterkandidat that produced this rule. RESTRICT so
    # the kandidat cannot be deleted while a confirmed rule references it.
    musterkandidat_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("musterkandidaten.musterkandidat_uuid", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    project_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # The Decision Event that performed the confirmation. RESTRICT for the
    # same audit-trail reason as conflict resolutions.
    confirmation_decision_event_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("decision_events.decision_event_uuid", ondelete="RESTRICT"),
        nullable=False,
    )
    # User-supplied rule annotation captured at confirmation.
    annotation: Mapped[str | None] = mapped_column(String(8192), nullable=True)
    # Snapshot of the pattern_key at confirmation time (for audit clarity
    # if the underlying Musterkandidat schema later evolves).
    pattern_key: Mapped[str] = mapped_column(String(8192), nullable=False, index=True)
    # Aggregated distinct source-class values from the underlying
    # observations (R-S3-11). JSONB array of strings.
    source_classes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
