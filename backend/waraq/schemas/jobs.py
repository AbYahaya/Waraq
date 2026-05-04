"""T-1.3.3 — Job + Checkpoint schemas.

CLAUDE.md §B Abkürzung 9: Checkpoint must be atomically persisted, not buffered
in memory. The atomicity guarantee is at the service layer (T-2.1.2); the
schema's role is to make persistence the obvious option (a real table, not a
serialized blob next to the job state).

Job state values are deliberately not check-constrained here — the canonical
state machine and its allowed values are owned by T-2.1.1. The column is a
plain String(32); the constraint lands in the migration that introduces the
state machine.
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


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    job_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # State machine values are owned by T-2.1.1 — no CHECK here yet.
    state: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    project_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class Checkpoint(Base):
    """Persistent recovery point for a Job. Append-only — no `active`, no
    `updated_at`. Atomic-write semantics enforced by the T-2.1.2 service."""

    __tablename__ = "checkpoints"

    checkpoint_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    job_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.job_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    # clock_timestamp() instead of now() so multiple checkpoints in the SAME
    # transaction get distinct created_at values. now() returns transaction-
    # start time, which would make read_latest_checkpoint indeterminate when
    # a job advances through multiple steps inside one transaction. The
    # ordering is functional here (resume), not informational, so this matters.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.clock_timestamp()
    )
