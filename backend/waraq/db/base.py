from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Project-wide SQLAlchemy declarative base. All ORM models inherit from this."""


class TimestampMixin:
    """Common columns for all canonical entity tables.

    `active` implements H-5 inactivation: deletion is forbidden; deactivation flips
    this flag while preserving the UUID. Mutators must go through the IDENTITY
    service (waraq.identity.service.mark_inactive).
    """

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
