"""§4.19 — Reference and Entity System schema.

Per Dokument 1 §4.19: five canonical categories — scholars/persons,
historical places, units of measurement, Arabic books, dynasties/epochs.
The canon names the categories and the historical Arabic biographical
sources for short bios; the schema shape itself is not canonized — only the
five-value taxonomy is fixed.

Binding follows the same pattern as Concept (§T-5.2.1): `binding_level` =
'project' or 'account', with exactly one of `project_uuid` / `account_uuid`
populated. The CHECK constraint in the migration enforces consistency.

Consumed by K-03 (Sprint 4 / T-8.2.1) which checks named-entity consistency
against `entity_id`. M2 ships the harness; the K-03 rule body is a stub
back-filled later.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base, TimestampMixin


class Entity(Base, TimestampMixin):
    __tablename__ = "entities"

    entity_id: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    # Canonical 5-value taxonomy per §4.19. CHECK constraint in migration.
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    canonical_label: Mapped[str] = mapped_column(String(255), nullable=False)
    # ISO 639-1/3 language tag for the canonical_label (e.g., 'ar', 'de').
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    # Short bio per §4.19 sourcing (سير أعلام النبلاء etc.). Free text.
    # Length cap is generous; longer prose belongs in `metadata_json`.
    short_bio: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    # Category-specific structured fields. For scholars: birth/death years,
    # known names. For places: coordinates, modern equivalent. For units:
    # base unit, conversion factor. Schema is per-category, not enforced
    # here — consumers know their category's payload shape.
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    # Source citations for the bio data (per §4.19 mentions سير أعلام النبلاء,
    # الأعلام للزركلي, etc.). List of {source: "...", ref: "..."} dicts.
    source_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    # Binding scope — same pattern as Concept.
    binding_level: Mapped[str] = mapped_column(String(16), nullable=False, server_default="project")
    project_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=True,
    )
    account_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.account_uuid", ondelete="RESTRICT"),
        nullable=True,
    )
