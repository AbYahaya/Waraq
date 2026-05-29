"""Persisted OCR attention issue and retry candidate lifecycle."""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base, TimestampMixin


class OcrAttentionIssue(Base, TimestampMixin):
    __tablename__ = "ocr_attention_issues"
    __table_args__ = (
        UniqueConstraint(
            "project_uuid",
            "satz_uuid",
            "issue_type",
            "source_po_uuid",
            name="uq_ocr_attention_issue_source",
        ),
    )

    issue_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    project_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    page_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pages.page_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    block_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("blocks.block_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    satz_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("segments.satz_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_po_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("provenance_objects.po_uuid", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, server_default="open")
    severity: Mapped[str] = mapped_column(String(32), nullable=False, server_default="warning")
    group_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")


class OcrRetryCandidate(Base, TimestampMixin):
    __tablename__ = "ocr_retry_candidates"

    candidate_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    issue_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ocr_attention_issues.issue_uuid", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    page_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pages.page_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    segment_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("segments.satz_uuid", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    engine: Mapped[str] = mapped_column(String(32), nullable=False)
    dpi: Mapped[int] = mapped_column(Integer, nullable=False)
    crop: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    current_text_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="candidate")
    decision_event_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("decision_events.decision_event_uuid", ondelete="SET NULL"),
        nullable=True,
    )
