"""T-1.3.3 + T-5.2.1 — Concept-ID table.

CLAUDE.md §2.4 lists `concept_id` and `binding_level` as canonical verbatim
terms — those are the PK and binding-discriminator column names on this
table. The class is Python-named `Concept` for ergonomic imports.

DBB §B Abkürzung 10: K-01 must look up via `concept_id`, not via string
equality. The Concept table is the stable identity that K-01 binds against;
the consistency-rule service (Sprint 4) reads from here. Glossary lookup
(T-5.2.1) is the *opposite* direction — surface-form text → concept_id —
and is the only legitimate place where string matching against canonical
labels happens.

Per Sprint 1 §2: glossary entries are project-bound or account-bound. The
`binding_level` column drives `scope_type` selection on the Decision Event
written for create/update operations. CHECK constraint enforces exactly one
of project_uuid / account_uuid is set, matching `binding_level`.

Concepts are identity objects — H-5 inactivation applies (no deletion).
"""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy import ForeignKey, String
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
    # Per Sprint 1 §2 / T-5.2.1: 'project' or 'account'. Drives scope_type
    # on the Decision Event written by glossary CRUD. CHECK constraint in
    # the migration enforces value-set correctness.
    binding_level: Mapped[str] = mapped_column(String(16), nullable=False, server_default="project")
    # Exactly one of these is set (CHECK in migration). Project-bound
    # entries fill project_uuid; account-bound entries fill account_uuid.
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
