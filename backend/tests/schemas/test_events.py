"""T-1.3.2 — three-identity-type discipline tests.

Locks in DBB Abkürzung 3: Revision, Decision Event, Log-Eintrag live in three
separate tables. A shared `events` table with type discriminator is the named
structural failure mode and must never reappear.
"""

from __future__ import annotations

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from waraq.db.base import Base
from waraq.schemas import DecisionEvent, LogEntry, Revision, Segment
from waraq.schemas.enums import ChangeSource, DecisionSource, ScopeType


def _col(model: type, name: str):  # type: ignore[no-untyped-def]
    return model.__table__.columns[name]


def _fk_targets(model: type, col: str) -> set[str]:
    return {fk.target_fullname for fk in _col(model, col).foreign_keys}


# --- Abkürzung 3: three separate tables, no shared events table ----------


class TestT_1_3_2_ThreeSeparateTables:
    def test_three_tables_registered(self) -> None:
        names = set(Base.metadata.tables)
        assert {"revisions", "decision_events", "log_entries"} <= names

    def test_no_shared_events_table_with_discriminator(self) -> None:
        # Abkürzung 3 names this exact failure mode by name.
        forbidden = {"events", "all_events", "event"}
        assert forbidden.isdisjoint(set(Base.metadata.tables))

    def test_each_has_distinct_canonical_pk(self) -> None:
        assert [c.name for c in Revision.__table__.primary_key.columns] == ["rev_uuid"]
        assert [c.name for c in DecisionEvent.__table__.primary_key.columns] == [
            "decision_event_uuid"
        ]
        assert [c.name for c in LogEntry.__table__.primary_key.columns] == ["log_id"]


# --- Decision Event must NOT carry text-change fields (CAB §5.2) ----------


class TestT_1_3_2_DecisionEventNoTextChange:
    """Per CAB §5.2: 'Decision Event ... never has a text-change field.'

    If before_text or after_text appear on decision_events, the three-types
    separation has collapsed.
    """

    def test_no_before_text(self) -> None:
        assert "before_text" not in DecisionEvent.__table__.columns

    def test_no_after_text(self) -> None:
        assert "after_text" not in DecisionEvent.__table__.columns

    def test_no_change_source(self) -> None:
        # change_source is Revision-only; presence here would mean the table
        # is doing double duty as both kinds of event.
        assert "change_source" not in DecisionEvent.__table__.columns


# --- Revision must NOT carry decision-shaped fields ------------------------


class TestT_1_3_2_RevisionIsTextChangeOnly:
    def test_no_decision_type(self) -> None:
        assert "decision_type" not in Revision.__table__.columns

    def test_no_decision_source(self) -> None:
        assert "decision_source" not in Revision.__table__.columns

    def test_no_scope_type(self) -> None:
        # Revision is satz-scoped by FK, not by scope_type indirection.
        assert "scope_type" not in Revision.__table__.columns


# --- Revision FK + change_source contract ---------------------------------


class TestT_1_3_2_RevisionShape:
    def test_satz_uuid_fk_to_segments(self) -> None:
        assert _fk_targets(Revision, "satz_uuid") == {"segments.satz_uuid"}

    def test_after_text_required(self) -> None:
        col = _col(Revision, "after_text")
        assert isinstance(col.type, Text)
        assert col.nullable is False

    def test_before_text_nullable(self) -> None:
        # First revision of a segment has no before-text.
        col = _col(Revision, "before_text")
        assert isinstance(col.type, Text)
        assert col.nullable is True

    def test_change_source_check_constraint_lists_canonical_values(self) -> None:
        clause = next(
            c.sqltext.text
            for c in Revision.__table__.constraints
            if c.name == "ck_change_source_values"
        )
        for value in (e.value for e in ChangeSource):
            assert f"'{value}'" in clause


# --- Decision Event scope + source contracts ------------------------------


class TestT_1_3_2_DecisionEventShape:
    def test_scope_type_check_constraint_has_all_five_values(self) -> None:
        clause = next(
            c.sqltext.text
            for c in DecisionEvent.__table__.constraints
            if c.name == "ck_scope_type_values"
        )
        for value in (e.value for e in ScopeType):
            assert f"'{value}'" in clause

    def test_decision_source_check_constraint_has_all_ten_values(self) -> None:
        clause = next(
            c.sqltext.text
            for c in DecisionEvent.__table__.constraints
            if c.name == "ck_decision_source_values"
        )
        for value in (e.value for e in DecisionSource):
            assert f"'{value}'" in clause

    def test_content_jsonb_required(self) -> None:
        col = _col(DecisionEvent, "content")
        assert isinstance(col.type, JSONB)
        assert col.nullable is False


# --- Log entry shape ------------------------------------------------------


class TestT_1_3_2_LogEntryShape:
    def test_pk_is_log_id(self) -> None:
        # CAB §5.2 calls this column `log_id`, not `log_uuid`.
        assert "log_id" in LogEntry.__table__.columns

    def test_operation_type_required(self) -> None:
        col = _col(LogEntry, "operation_type")
        assert isinstance(col.type, String)
        assert col.nullable is False

    def test_result_jsonb_required(self) -> None:
        col = _col(LogEntry, "result")
        assert isinstance(col.type, JSONB)
        assert col.nullable is False


# --- All three are append-only history (no `active`, no `updated_at`) -----


class TestT_1_3_2_AppendOnlyHistory:
    """H-5 inactivation does not apply to immutable event history. These tables
    must not carry an `active` flag or an `updated_at` column."""

    def _assert_append_only(self, model: type) -> None:
        cols = model.__table__.columns
        assert "active" not in cols, f"{model.__name__} must not carry an `active` flag"
        assert "updated_at" not in cols, f"{model.__name__} must not carry `updated_at`"
        assert "created_at" in cols
        assert isinstance(cols["created_at"].type, DateTime)

    def test_revision(self) -> None:
        self._assert_append_only(Revision)

    def test_decision_event(self) -> None:
        self._assert_append_only(DecisionEvent)

    def test_log_entry(self) -> None:
        self._assert_append_only(LogEntry)


# --- Segment.current_rev_uuid FK now wired -------------------------------


class TestT_1_3_2_SegmentCurrentRevFkWired:
    def test_segment_current_rev_uuid_now_fks_revisions(self) -> None:
        assert _fk_targets(Segment, "current_rev_uuid") == {"revisions.rev_uuid"}


# --- Abkürzung 2 forecast: satz_uuid stays only on segments + revisions ---


class TestT_1_3_2_SatzUuidStillScoped:
    """Reaffirm Abkürzung 2: only segments (PK) and revisions (segment-scoped
    FK) carry satz_uuid. Provenance must not (T-1.3.3 will re-check)."""

    def test_satz_uuid_only_on_segments_and_revisions(self) -> None:
        offenders = [
            t.name
            for t in Base.metadata.tables.values()
            if t.name not in {"segments", "revisions"} and "satz_uuid" in t.columns
        ]
        assert offenders == [], f"satz_uuid leaked into tables: {offenders}"


# --- Sanity: imports above silence ruff "unused" without runtime cost ----


def test_uuid_type_imports_used() -> None:
    # Sanity-level: confirm event tables actually use Postgres UUID, not
    # generic GUID. Catches accidental dialect drift.
    assert isinstance(_col(Revision, "rev_uuid").type, PG_UUID)
    assert isinstance(_col(DecisionEvent, "decision_event_uuid").type, PG_UUID)
    assert isinstance(_col(LogEntry, "log_id").type, PG_UUID)
