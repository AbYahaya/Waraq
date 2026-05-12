from __future__ import annotations

import uuid as _uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base, TimestampMixin
from waraq.invariant.enums import LockFlag
from waraq.schemas.enums import OcrStatus, ReadingDirection


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    project_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    account_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.account_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class Page(Base, TimestampMixin):
    __tablename__ = "pages"

    page_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    project_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=False,
    )
    page_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # Per T-4.3.1 / Sprint 1 §2: page-level OCR review state machine. Fresh
    # pages enter at `ausstehend`; the LINEAGE/OCR pipeline transitions them
    # through `in_review` to one of the terminal go-states. The `no_go → go`
    # transition is gated on an explicit user-resolution Decision Event.
    ocr_status: Mapped[OcrStatus] = mapped_column(
        SAEnum(
            OcrStatus,
            name="ocr_status",
            native_enum=False,
            length=32,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        server_default=OcrStatus.AUSSTEHEND.value,
    )


class Block(Base, TimestampMixin):
    __tablename__ = "blocks"

    block_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    page_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pages.page_uuid", ondelete="RESTRICT"),
        nullable=False,
    )
    # Canonical value set per Dokument 1 §3.4 (OCR Stage-2 block class).
    # Migration 0024 lands a CHECK constraint allowing the canonical six
    # `BlockClass` values plus the legacy `UE` / `HD` heading synonyms
    # used by the TOC + DOCX-export paths until those callers migrate to
    # `(heading, heading_level=1|2)`.
    block_type: Mapped[str] = mapped_column(String(32), nullable=False)
    block_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # §3.4 Stage-1 reading-direction map. Defaults to RTL (Arabic primary).
    # The `unknown` sentinel captures detector ambiguity so calibration can
    # target it; treat unknown like RTL for layout decisions.
    reading_direction: Mapped[ReadingDirection] = mapped_column(
        SAEnum(
            ReadingDirection,
            name="reading_direction",
            native_enum=False,
            length=16,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        server_default=ReadingDirection.RTL.value,
    )
    # §3.4 Stage-1 text-density signal (black-pixel ratio in [0, 1]) and
    # baseline y-coordinate. Both NULL until a real layout detector
    # (LayoutParser / DocTR) populates them; the v1.0 default detector
    # leaves them None.
    text_density: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_y: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Segment(Base, TimestampMixin):
    """Smallest text unit. Canonical PK column name is `satz_uuid` (CLAUDE.md §2.4)."""

    __tablename__ = "segments"

    satz_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    block_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("blocks.block_uuid", ondelete="RESTRICT"),
        nullable=False,
    )
    satz_index: Mapped[int] = mapped_column(Integer, nullable=False)
    lock_flag: Mapped[LockFlag] = mapped_column(
        SAEnum(
            LockFlag,
            name="lock_flag",
            native_enum=False,
            length=32,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        server_default=LockFlag.NONE.value,
    )
    # Nullable: a freshly created Segment has no revision until first OCR or
    # manual write produces one. FK use_alter=True to break the segments↔revisions
    # circular dependency at table-create time (revisions FKs back to segments).
    current_rev_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "revisions.rev_uuid",
            ondelete="RESTRICT",
            use_alter=True,
            name="fk_segments_current_rev_uuid",
        ),
        nullable=True,
    )
    # Working text cache. Authoritative text history lives in revisions (T-1.3.2);
    # this column is the materialized current value for fast reads.
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
