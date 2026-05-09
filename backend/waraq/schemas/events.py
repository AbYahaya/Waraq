"""T-1.3.2 — three identity types in three separate tables.

CAB §5.2 / DBB Abkürzung 3: Revision, Decision Event, Log-Eintrag are three
distinct tables with three distinct purposes. A shared `events` table with a
type discriminator is the named structural failure mode.

- Revision           — text change. Has rev_uuid, FK to satz_uuid, before/after
                       text, change_source.
- Decision Event     — user decision. Has decision_event_uuid, scope_type +
                       scope_uuid, decision_type, decision_source, content
                       JSONB. **Never** has a text-change field.
- Log-Eintrag        — operational/system event. Has log_id, operation_type,
                       result JSONB. Lineage matching writes here (CLAUDE.md
                       §5.5), never to decision_events.

These are append-only history records. They do not carry an `active` flag —
H-5 inactivation does not apply to immutable event history. They carry only
`created_at` (set once at insert).
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base
from waraq.schemas.enums import ChangeSource, DecisionSource, ScopeType


def _enum_check(column: str, enum_cls: type[StrEnum]) -> CheckConstraint:
    values = ", ".join(f"'{e.value}'" for e in enum_cls)
    return CheckConstraint(f"{column} IN ({values})", name=f"ck_{column}_values")


class Revision(Base):
    __tablename__ = "revisions"

    rev_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    satz_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("segments.satz_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    before_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_text: Mapped[str] = mapped_column(Text, nullable=False)
    change_source: Mapped[ChangeSource] = mapped_column(String(32), nullable=False)
    # Nullable: OCR-driven revisions are system-authored (no human actor).
    author_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.account_uuid", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (_enum_check("change_source", ChangeSource),)


class DecisionEvent(Base):
    """A user decision. Carries scope_type + scope_uuid; **never** carries a
    before_text / after_text field — those belong on Revision."""

    __tablename__ = "decision_events"

    decision_event_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    scope_type: Mapped[ScopeType] = mapped_column(String(16), nullable=False)
    scope_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    decision_type: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_source: Mapped[DecisionSource] = mapped_column(String(32), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    actor_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.account_uuid", ondelete="RESTRICT"),
        nullable=True,
    )
    # Per OCR Endfassung v1.3 CR-1.6: binds `export_confirmation`-source
    # Decision Events to a concrete export attempt. NULL for non-export
    # decisions. The OCR-Export-Job (Sprint-OCR T-OCR-EX-1) sets this on
    # Pflichtfragen-Bestätigung; the OCR_EXPORT_EVENT positive-set rule
    # uses it to filter old confirmations out of `active_decision_event_uuids[]`.
    related_export_attempt_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        _enum_check("scope_type", ScopeType),
        _enum_check("decision_source", DecisionSource),
    )


class LogEntry(Base):
    """Operational/system event. Lineage matching writes here (CLAUDE.md §5.5).

    Canonical PK column name is `log_id` per CAB §5.2.
    """

    __tablename__ = "log_entries"

    log_id: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    operation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    # Optional context for filtered reads (lineage events tagged by segment, etc.).
    scope_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    scope_uuid: Mapped[_uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
