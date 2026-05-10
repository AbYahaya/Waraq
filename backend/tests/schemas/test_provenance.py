"""T-1.3.3 — Provenance, Job, Checkpoint, Concept schema discipline.

Lead test: DBB §B Abkürzung 2 — provenance_objects must NOT have a satz_uuid
column. Polymorphic addressing via scope_type + scope_uuid only.
"""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from waraq.db.base import Base
from waraq.schemas import Checkpoint, Concept, Job, ProvenanceObject
from waraq.schemas.enums import POType, ScopeType


def _col(model: type, name: str):  # type: ignore[no-untyped-def]
    return model.__table__.columns[name]


def _fk_targets(model: type, col: str) -> set[str]:
    return {fk.target_fullname for fk in _col(model, col).foreign_keys}


# --- Abkürzung 2 — the hard rule -----------------------------------------


class TestT_1_3_3_AbkurzungZwei_ProvenanceHasNoSatzUuid:
    """DBB §B item 2: 'Provenance-Tabelle with `satz_uuid NOT NULL`' is the
    named structural failure mode. The stronger contract: provenance_objects
    must not have a `satz_uuid` column at all — its presence implies the
    wrong addressing model and will tempt future code into satz-only
    assumptions.
    """

    def test_provenance_table_does_not_have_satz_uuid_column(self) -> None:
        cols = ProvenanceObject.__table__.columns
        assert "satz_uuid" not in cols

    def test_provenance_addressing_is_scope_based(self) -> None:
        cols = ProvenanceObject.__table__.columns
        assert "scope_type" in cols
        assert "scope_uuid" in cols
        # And both required — null scope is meaningless for a PO.
        assert cols["scope_type"].nullable is False
        assert cols["scope_uuid"].nullable is False


# --- Provenance shape -----------------------------------------------------


class TestT_1_3_3_ProvenanceShape:
    def test_pk_is_po_uuid(self) -> None:
        assert [c.name for c in ProvenanceObject.__table__.primary_key.columns] == ["po_uuid"]

    def test_po_type_check_constraint_lists_all_seven(self) -> None:
        clause = next(
            c.sqltext.text
            for c in ProvenanceObject.__table__.constraints
            if c.name == "ck_po_type_values"
        )
        for value in (e.value for e in POType):
            assert f"'{value}'" in clause

    def test_po_type_includes_canonical_manual_underscore(self) -> None:
        # CLAUDE.md §2.4 lists `MANUAL_-PO` verbatim — the trailing underscore
        # must survive into the value list.
        assert POType.MANUAL_.value == "manual_"
        clause = next(
            c.sqltext.text
            for c in ProvenanceObject.__table__.constraints
            if c.name == "ck_po_type_values"
        )
        assert "'manual_'" in clause

    def test_scope_type_check_constraint_has_all_five_values(self) -> None:
        clause = next(
            c.sqltext.text
            for c in ProvenanceObject.__table__.constraints
            if c.name == "ck_provenance_scope_type_values"
        )
        for value in (e.value for e in ScopeType):
            assert f"'{value}'" in clause

    def test_payload_jsonb_required(self) -> None:
        col = _col(ProvenanceObject, "payload")
        assert isinstance(col.type, JSONB)
        assert col.nullable is False

    def test_author_uuid_nullable(self) -> None:
        # System-authored POs (LINEAGE_EVENT, automatic SCAN) have no actor.
        col = _col(ProvenanceObject, "author_uuid")
        assert col.nullable is True


class TestT_1_3_3_ProvenanceIsAppendOnly:
    """POs are immutable history. No `active`, no `updated_at`."""

    def test_no_active_column(self) -> None:
        assert "active" not in ProvenanceObject.__table__.columns

    def test_no_updated_at_column(self) -> None:
        assert "updated_at" not in ProvenanceObject.__table__.columns

    def test_has_created_at(self) -> None:
        col = _col(ProvenanceObject, "created_at")
        assert isinstance(col.type, DateTime)
        assert col.nullable is False


# --- Job + Checkpoint -----------------------------------------------------


class TestT_1_3_3_JobShape:
    def test_pk_is_job_uuid(self) -> None:
        assert [c.name for c in Job.__table__.primary_key.columns] == ["job_uuid"]

    def test_job_type_required(self) -> None:
        col = _col(Job, "job_type")
        assert isinstance(col.type, String)
        assert col.nullable is False

    def test_state_has_default_pending(self) -> None:
        col = _col(Job, "state")
        assert col.nullable is False
        assert col.server_default is not None
        assert str(col.server_default.arg).strip("'\"") == "pending"

    def test_state_has_no_check_constraint_yet(self) -> None:
        # State machine values are owned by T-2.1.1. Adding a CHECK here
        # would force a follow-up migration to alter; cleaner to add it
        # together with the state-machine logic.
        names = {c.name for c in Job.__table__.constraints if c.name}
        assert not any("state" in (n or "") for n in names)

    def test_project_uuid_fks_projects_and_is_nullable(self) -> None:
        # Some jobs are account-scoped, not project-scoped.
        assert _fk_targets(Job, "project_uuid") == {"projects.project_uuid"}
        assert _col(Job, "project_uuid").nullable is True

    def test_has_active_and_timestamps(self) -> None:
        cols = Job.__table__.columns
        assert isinstance(cols["active"].type, Boolean)
        assert cols["active"].nullable is False
        assert "created_at" in cols and "updated_at" in cols


class TestT_1_3_3_CheckpointShape:
    """Abkürzung 9: Checkpoint must be atomically persisted, not in-memory.
    Schema check: real table, FK to jobs, JSONB payload."""

    def test_pk_is_checkpoint_uuid(self) -> None:
        assert [c.name for c in Checkpoint.__table__.primary_key.columns] == ["checkpoint_uuid"]

    def test_fk_to_jobs_required(self) -> None:
        assert _fk_targets(Checkpoint, "job_uuid") == {"jobs.job_uuid"}
        assert _col(Checkpoint, "job_uuid").nullable is False

    def test_payload_jsonb_required(self) -> None:
        col = _col(Checkpoint, "payload")
        assert isinstance(col.type, JSONB)
        assert col.nullable is False

    def test_append_only_no_active_no_updated_at(self) -> None:
        cols = Checkpoint.__table__.columns
        assert "active" not in cols
        assert "updated_at" not in cols
        assert "created_at" in cols


# --- Concept --------------------------------------------------------------


class TestT_1_3_3_ConceptShape:
    """CLAUDE.md §2.4: PK column name is `concept_id`, verbatim. Not
    `concept_uuid`, not `id`."""

    def test_pk_column_name_is_concept_id(self) -> None:
        assert [c.name for c in Concept.__table__.primary_key.columns] == ["concept_id"]

    def test_pk_is_uuid_typed(self) -> None:
        col = _col(Concept, "concept_id")
        assert isinstance(col.type, PG_UUID)

    def test_canonical_label_required(self) -> None:
        col = _col(Concept, "canonical_label")
        assert isinstance(col.type, String)
        assert col.nullable is False

    def test_language_required(self) -> None:
        col = _col(Concept, "language")
        assert col.nullable is False

    def test_concept_is_inactivatable_not_deletable(self) -> None:
        # Concepts are identity objects — H-5 inactivation applies.
        cols = Concept.__table__.columns
        assert "active" in cols and isinstance(cols["active"].type, Boolean)
        assert "created_at" in cols and "updated_at" in cols


# --- Re-check Abkürzung 2 across all current tables ----------------------


class TestT_1_3_3_SatzUuidAllowlistStillHolds:
    """satz_uuid only on legitimate segment-scoped event tables.
    provenance_objects, jobs, checkpoints, concepts, ocr_error_instances,
    decision_events, log_entries — none may carry satz_uuid. Sprint 1
    extends the allowlist by `conflict_instances` (T-5.1.2)."""

    ALLOWLIST = frozenset(
        {
            "segments",
            "revisions",
            "conflict_instances",
            "translation_observations",
            "audit_befunde",
            "hadith_passage_status",
            # Phase 2A — §4.16.6 Hadith result tables.
            "hadith_single_source_results",
            "hadith_aggregate_results",
            # Phase 2F-A — §4.15.3 project Quranic passage snapshot.
            "project_quran_passages",
        }
    )

    def test_no_new_table_introduced_satz_uuid(self) -> None:
        offenders = [
            t.name
            for t in Base.metadata.tables.values()
            if t.name not in self.ALLOWLIST and "satz_uuid" in t.columns
        ]
        assert offenders == [], f"satz_uuid leaked into tables: {offenders}"
