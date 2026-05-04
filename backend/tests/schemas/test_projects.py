"""T-1.3.1 — schema discipline tests for Project, Page, Block, Segment.

Metadata-level only: verify column names, types, nullability, and FK targets
without needing a live database. The migration is exercised separately when
Postgres is up.
"""

from __future__ import annotations

from typing import ClassVar

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from waraq.db.base import Base
from waraq.schemas import Block, Page, Project, Segment


def _col(model: type, name: str):  # type: ignore[no-untyped-def]
    return model.__table__.columns[name]


def _fk_targets(model: type, col: str) -> set[str]:
    return {fk.target_fullname for fk in _col(model, col).foreign_keys}


# --- registration ----------------------------------------------------------


class TestT_1_3_1_TablesRegistered:
    def test_all_four_tables_in_metadata(self) -> None:
        assert {"projects", "pages", "blocks", "segments"} <= set(Base.metadata.tables)


# --- canonical PK column names (CLAUDE.md §2.4 verbatim discipline) --------


class TestT_1_3_1_CanonicalPkNames:
    def test_project_pk_is_project_uuid(self) -> None:
        assert [c.name for c in Project.__table__.primary_key.columns] == ["project_uuid"]

    def test_page_pk_is_page_uuid(self) -> None:
        assert [c.name for c in Page.__table__.primary_key.columns] == ["page_uuid"]

    def test_block_pk_is_block_uuid(self) -> None:
        assert [c.name for c in Block.__table__.primary_key.columns] == ["block_uuid"]

    def test_segment_pk_is_satz_uuid(self) -> None:
        # CLAUDE.md §2.4: canonical column name is `satz_uuid`, never `segment_uuid`.
        assert [c.name for c in Segment.__table__.primary_key.columns] == ["satz_uuid"]


# --- foreign keys ----------------------------------------------------------


class TestT_1_3_1_ForeignKeys:
    def test_page_fks_project(self) -> None:
        assert _fk_targets(Page, "project_uuid") == {"projects.project_uuid"}

    def test_block_fks_page(self) -> None:
        assert _fk_targets(Block, "page_uuid") == {"pages.page_uuid"}

    def test_segment_fks_block(self) -> None:
        assert _fk_targets(Segment, "block_uuid") == {"blocks.block_uuid"}

    def test_project_account_uuid_fks_accounts(self) -> None:
        # FK landed in Sprint -0.5 (migration 0006).
        assert _fk_targets(Project, "account_uuid") == {"accounts.account_uuid"}

    def test_segment_current_rev_uuid_fks_revisions(self) -> None:
        # Wired in T-1.3.2 (revisions table now exists).
        assert _fk_targets(Segment, "current_rev_uuid") == {"revisions.rev_uuid"}


# --- column types and nullability -----------------------------------------


class TestT_1_3_1_CoreColumns:
    def test_project_account_uuid_not_null_uuid(self) -> None:
        col = _col(Project, "account_uuid")
        assert isinstance(col.type, PG_UUID)
        assert col.nullable is False

    def test_project_name_required(self) -> None:
        col = _col(Project, "name")
        assert isinstance(col.type, String)
        assert col.nullable is False

    def test_page_index_integer_required(self) -> None:
        col = _col(Page, "page_index")
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    def test_block_type_string_required(self) -> None:
        col = _col(Block, "block_type")
        assert isinstance(col.type, String)
        assert col.nullable is False

    def test_block_index_integer_required(self) -> None:
        col = _col(Block, "block_index")
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    def test_segment_satz_index_integer_required(self) -> None:
        col = _col(Segment, "satz_index")
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    def test_segment_text_content_nullable(self) -> None:
        col = _col(Segment, "text_content")
        assert isinstance(col.type, Text)
        assert col.nullable is True

    def test_segment_current_rev_uuid_nullable(self) -> None:
        # Per H-4: a fresh Segment has no Revision until first text change.
        col = _col(Segment, "current_rev_uuid")
        assert isinstance(col.type, PG_UUID)
        assert col.nullable is True


# --- lock_flag canonical contract (H-1, H-2 surface) ----------------------


class TestT_1_3_1_LockFlagColumn:
    def test_segment_lock_flag_is_canonical_column_name(self) -> None:
        # CLAUDE.md §2.4: `lock_flag` is verbatim canonical.
        assert "lock_flag" in Segment.__table__.columns

    def test_segment_lock_flag_not_null_with_default_none(self) -> None:
        col = _col(Segment, "lock_flag")
        assert col.nullable is False
        assert col.server_default is not None
        # Default must be the canonical "none" value, never a free-text fallback.
        default_text = str(col.server_default.arg).strip("'\"")
        assert default_text == "none"


# --- TimestampMixin discipline (H-5 active-flag, audit timestamps) --------


class TestT_1_3_1_TimestampMixinAppliedEverywhere:
    """All four entity tables share the inactivation+audit-timestamp surface."""

    def _assert_has_active_and_timestamps(self, model: type) -> None:
        cols = model.__table__.columns
        assert "active" in cols
        assert isinstance(cols["active"].type, Boolean)
        assert cols["active"].nullable is False

        for ts in ("created_at", "updated_at"):
            assert ts in cols
            assert isinstance(cols[ts].type, DateTime)
            assert cols[ts].nullable is False

    def test_project(self) -> None:
        self._assert_has_active_and_timestamps(Project)

    def test_page(self) -> None:
        self._assert_has_active_and_timestamps(Page)

    def test_block(self) -> None:
        self._assert_has_active_and_timestamps(Block)

    def test_segment(self) -> None:
        self._assert_has_active_and_timestamps(Segment)


# --- Abkürzung 2 anticipation: satz_uuid only lives on segments ------------


class TestT_1_3_1_SatzUuidOnlyOnAllowlistedTables:
    """DBB §B Abkürzung 2: `satz_uuid NOT NULL` outside legitimate
    segment-scoped contexts is a structural failure mode. Genuine
    segment-scoped event tables (revisions) carry it as an FK; everything
    else (decision_events, log_entries, provenance, jobs, ...) must use
    scope_type + scope_uuid instead."""

    ALLOWED_TABLES: ClassVar[set[str]] = {"segments", "revisions"}

    def test_satz_uuid_only_on_allowlisted_tables(self) -> None:
        offenders = [
            t.name
            for t in Base.metadata.tables.values()
            if t.name not in self.ALLOWED_TABLES and "satz_uuid" in t.columns
        ]
        assert offenders == [], f"satz_uuid leaked into tables: {offenders}"
