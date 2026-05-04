"""T-1.3.3 — Concept-ID table.

CLAUDE.md §2.4 lists `concept_id` as a canonical verbatim term — that is the
PK column name on this table. The class is Python-named `Concept` for
ergonomic imports.

DBB §B Abkürzung 10: K-01 must look up via `concept_id`, not via string
equality. The Concept table is the stable identity that K-01 binds against;
the consistency-rule service (Sprint 4) reads from here.

Concepts are identity objects — H-5 inactivation applies (no deletion).
"""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base, TimestampMixin


class Concept(Base, TimestampMixin):
    __tablename__ = "concepts"

    concept_id: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    canonical_label: Mapped[str] = mapped_column(String(255), nullable=False)
    # ISO 639-1/3 language tag for the canonical_label (e.g., 'ar', 'de').
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    gloss: Mapped[str | None] = mapped_column(String(1024), nullable=True)
