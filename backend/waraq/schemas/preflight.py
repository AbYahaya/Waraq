"""T-9.1.1 — Pflichtfrage configuration schema (Konfigurationsschicht).

Per Sprint 4 §2:

> "Konfigurationsschicht — vier Pflichtfragen. Active confirmation
> required for each of the four canonical export-configuration questions
> (concrete questions defined in product configuration; Pflicht is
> canonical, the four-count is canonical, the questions themselves are
> configurable per Dokument 2 §2.3)."

> "A saved Export-Profil may **pre-fill** Pflichtfragen but never
> **replaces** an active confirmation."

This schema persists the project's saved profile pre-fills. The active
confirmation per export run is recorded as a Decision Event with
`decision_source=preflight_confirmation` (Dokument 1 §4.10) tied to the
preflight job via `related_export_attempt_id`. The Decision Event is the
authoritative active confirmation; the profile row is only the pre-fill.

The four-count is canonical: any project that has any pre-fills must
either have all four or none — enforced at the service layer (not DB —
projects without any preflight runs yet have no rows here).
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base, TimestampMixin


class PflichtfrageProfil(Base, TimestampMixin):
    """One row per (project, frage_index) — saved Export-Profil pre-fill.

    `frage_index` ∈ {1, 2, 3, 4} (CHECK in migration). The row exists if
    the user has saved an Export-Profil pre-fill for this question; absent
    means no pre-fill, user must confirm fresh on every preflight run.

    `prefilled_answer` is the JSONB blob carrying the pre-fill content.
    The structure depends on the question; the row is opaque to the
    Konfigurationsschicht beyond the existence-and-index check.
    """

    __tablename__ = "pflichtfrage_profile"

    profil_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    project_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    frage_index: Mapped[int] = mapped_column(Integer, nullable=False)
    frage_key: Mapped[str] = mapped_column(String(64), nullable=False)
    prefilled_answer: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    __table_args__ = (
        UniqueConstraint("project_uuid", "frage_index", name="uq_pflichtfrage_profil_project_idx"),
    )
