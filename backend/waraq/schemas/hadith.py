"""Hadith schemas — §4.16.4 passage status + §4.16.6 four-level result objects.

**§4.16.4** — each hadith passage carries a state type
`hadith_stellen_typ` ∈ {N-1..N-10}. The verification class
`hadith_verifikationsklasse` ∈ {H-0, H-1, H-2} is **deterministically
derivable** from the passage type per:

    H-0 (review-internally tolerable, not export-blocking): N-1, N-3, N-9
    H-1 (logging-mandatory, warning-capable):                N-2, N-10
    H-2 (export-blocking until resolution):                  N-4, N-5, N-6,
                                                              N-7, N-8

Per §4.16.6 the H-X is "deterministically derivable, not independently
persisted". We persist only `hadith_stellen_typ`; `hadith_verifikationsklasse`
is computed at read time (see `waraq.preflight.hadith.derive_hadith_klasse`).

Resolution of H-2 follows the seven canonical action types per §4.16.5
(none of them adds a new `decision_source`; all map to existing
`translation_pipeline` or `conflict_resolution` values).

H-1 supports `go_with_warning` per §4.9 E-1: the user may proceed with
explicit warning-acknowledgement, which writes a Decision Event with
`decision_source=preflight_confirmation` (per §4.10).

**§4.16.6 four-level data model** (Phase 2 — landed 2026-05-09):

- **Level 1 — Passage anchor** via Block-UUID + Sentence-UUID + OCR
  Revision-UUID. Lives on the FKs of HadithSingleSourceResult and
  HadithAggregateResult (`satz_uuid` + `block_uuid` + `ocr_rev_uuid`).
- **Level 2 — Single-source reading** per source per verification run;
  multiple objects per source per run permitted (hit variants).
  → `HadithSingleSourceResult`.
- **Level 3 — Aggregated overall result** per verification run,
  references Level 2 objects, determines reference matn and reference
  vocalization. → `HadithAggregateResult`.
- **Level 4 — User decision overlay** exclusively via existing
  `decision_event_uuid` per §4.10 + §4.11; **no own table, no own
  superseding logic**. The overlay grows by appending new Decision
  Events that point at the aggregate.

**Immutability** per §4.9 E-10: Single-source objects and the overall
result are immutable after creation w.r.t. provenance and references.
A new verification round generates a new aggregate with its own UUID;
the old one is preserved as provenance (`is_aktiv = false`).

**Source enum exclusion**: hadithportal.com may not appear in the
source field of any Single-source result (canonical exclusion per
§4.16.1).
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
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


class HadithAggregateResult(Base, TimestampMixin):
    """§4.16.6 Level 3 — Aggregated overall result per verification run.

    One row per (passage, verification run). References Level 2
    Single-source objects via FK from `HadithSingleSourceResult`; this
    row carries the *chosen* reference matn + reference vocalization
    (which may come from different sources per §4.16.7) and the
    derived classification.

    **Immutability** (§4.16.6 / §4.9 E-10): once written, this row is
    not mutated. A new verification round writes a new aggregate
    (fresh `aggregate_uuid`); the old one is preserved by flipping
    `is_aktiv = false` AND optionally pointing `superseded_by_uuid`
    at the new row. `decision_event_uuids` (Level 4 overlay) grow
    only by appending new Decision Events — not modeled here.
    """

    __tablename__ = "hadith_aggregate_results"

    aggregate_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    # Level 1 anchor — passage identity.
    satz_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("segments.satz_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    block_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("blocks.block_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ocr_rev_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("revisions.rev_uuid", ondelete="RESTRICT"),
        nullable=True,
    )
    project_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Verification run identifier — multiple aggregates per passage
    # across runs (one per run). String not UUID so callers can use a
    # stable hash if they wish; canonical clients pass a UUID-string.
    run_uuid: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Chosen reference fields per §4.16.7 (matn and vocalization may
    # come from DIFFERENT Single-source rows). NULL if no aggregable hit.
    reference_matn: Mapped[str | None] = mapped_column(String, nullable=True)
    reference_matn_source_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    reference_vocalization: Mapped[str | None] = mapped_column(String, nullable=True)
    reference_vocalization_source_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    # Derived state per §4.16.6 (deterministically derivable from the
    # Level 2 + Level 3 + Level 4 graph, not independently persisted —
    # but cached here at-creation for cheap reads). The
    # `vokalisierungs_konflikt` is strictly binary per §4.16.7.
    vokalisierungsklasse: Mapped[str] = mapped_column(String(8), nullable=False)
    vokalisierungs_konflikt: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Multi-dimensional consensus summary (§4.16.3): Wording proximity,
    # carriage by multiple sources, proximity to author-named source,
    # isnād / collection reference, vocalization consistency,
    # authenticity signals. JSONB so the consensus engine evolves
    # without schema churn (Phase 2F).
    consensus_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    # Provenance: H-5 inactivation. New verification round flips this
    # to false and points superseded_by_uuid at the fresh aggregate.
    is_aktiv: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true", index=True
    )
    superseded_by_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("hadith_aggregate_results.aggregate_uuid", ondelete="RESTRICT"),
        nullable=True,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class HadithSingleSourceResult(Base, TimestampMixin):
    """§4.16.6 Level 2 — Single-source reading per source per verification run.

    One row per (source, verification run, hit variant). The same
    source may produce multiple rows for the same run when the source
    delivers multiple hit candidates ("hit variants permitted" per
    §4.16.6).

    Source role is **fixed at the time of the verification run** per
    §4.16.6 — it does not back-derive against the current canon. The
    canonical Quellenrolle enum lives in `waraq.hadith.enums`.

    `website_uebersetzung` carries language-tagged translations the
    source delivers per §4.16.8: list of `{"lang": "<iso>", "text":
    "<translation>"}` dicts. These are comparison/provenance only —
    they have no effect on matn consensus or reference vocalization.
    """

    __tablename__ = "hadith_single_source_results"

    single_source_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    aggregate_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("hadith_aggregate_results.aggregate_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Canonical source identifier — caller provides (e.g.,
    # "sunnah.com", "Shamela", "dorar.net", "E-5"). hadithportal.com
    # explicitly excluded by canon per §4.16.1; not enforced at the
    # column level (the consensus engine refuses to ingest it instead).
    source_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Source role — canonical Quellenrolle enum. Snapshot at run-time.
    quellen_rolle: Mapped[str] = mapped_column(String(32), nullable=False)
    # Single-source matn (raw + extracted vocalization). Both come from
    # this source on this run. Either / both may be NULL if the source
    # only returned a metadata stub.
    matn_text: Mapped[str | None] = mapped_column(String, nullable=True)
    matn_vocalized: Mapped[str | None] = mapped_column(String, nullable=True)
    # Source-side metadata (kitab/bab/hadith number/authenticity grade/
    # isnād chain — source-specific schema). JSONB.
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    # §4.16.8 language-neutral comparison material — list of
    # {lang, text} dicts. NEVER influences matn consensus; comparison
    # only.
    website_uebersetzung: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
