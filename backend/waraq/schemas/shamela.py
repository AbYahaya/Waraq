"""§3.5 + §4.16.1 P-2 — Shamela / OpenITI corpus schemas.

Per Dokument 1 §3.5:
  "مكتبة الشاملة (Shamela) – complete database including Lisān al-ʿArab
  and Tāj al-ʿArūs. Lisān al-ʿArab (20+ volumes) and Tāj al-ʿArūs (40
  volumes) are treated within Shamela as independently queryable units"

  "Shamela is used in two functionally separated modes:
    - Mode A – OCR-internal: system-triggered in OCR Stage 3 (semantic
      reconstruction) as plausibility check of recognized text fragments.
    - Mode B – user-driven: lexical research and footnote creation in
      the translation phase.
  The data source is the same in both modes; trigger, purpose, and
  result processing differ."

Per §4.16.1 P-2: Shamela is a mandatory hadith verification source.

Per WORKLOG decision 2026-05-08: OpenITI is the v1.0 implementation
source for Shamela ingestion (CC BY 4.0; stable GitHub-hosted URIs;
machine-readable `.mARkdown`).

Two tables:
- `ShamelaRegistry` — text-level metadata (one row per text in the
  v1.0 set: 2 lexicons + 6 Kutub-as-Sitta collections + 2 supplementary).
- `ShamelaSection` — content rows (one row per section / paragraph /
  hadith). Skeleton-indexed for Mode A plausibility lookup.

The `text_type` and `is_kutub_as_sitta` columns let the consensus
engine wire Shamela hits into §4.16.3 with the correct `quellen_rolle`
+ Kutub preference, AND distinguish lexicon Mode-B lookups from
hadith P-2 verification.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base, TimestampMixin


class ShamelaRegistry(Base, TimestampMixin):
    """Text-level metadata. One row per (text_slug, source_version).

    Re-ingest of a fresher OpenITI release writes a new
    `(text_slug, source_version)` row. The prior version's row +
    sections flip to `active=false` (H-5 inactivation, no deletion).
    """

    __tablename__ = "shamela_registry"

    text_slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_version: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    # `lexicon | hadith | fiqh | tafsir | other` — informational, drives
    # the lookup specialization (Mode A plausibility / Mode B lexical /
    # Hadith verification candidate construction).
    text_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # True only for the 6 Kutub-as-Sitta collections per §4.16.3.
    # The consensus engine reads this to apply the Kutub tiebreak.
    is_kutub_as_sitta: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )


class ShamelaSection(Base, TimestampMixin):
    """One section / paragraph / hadith of a Shamela text.

    For lexicon entries (`text_type=lexicon`): one row per lemma /
    headword. `section_path` carries the lemma. For hadith collections:
    one row per hadith. `section_path` carries the kitāb / bāb hierarchy
    plus the hadith number; `metadata_json.hadith_number` carries the
    canonical number for sunnah.com-compatible citation.

    `text_skeleton` is the OCR-stage matching key (Mode A — §3.5 OCR
    Stage 3 plausibility check). NFC + Tatweel + diacritic-stripped +
    Alif-variants normalized + non-initial alif stripped (same
    `to_skeleton` pipeline as AR-Referenzbestand for consistency).
    """

    __tablename__ = "shamela_sections"

    section_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    text_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    section_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_path: Mapped[str] = mapped_column(String(1024), nullable=False, server_default="")
    text_arabic: Mapped[str] = mapped_column(String, nullable=False)
    text_skeleton: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["text_slug", "source_version"],
            ["shamela_registry.text_slug", "shamela_registry.source_version"],
            ondelete="RESTRICT",
            name="fk_shamela_section_registry",
        ),
        UniqueConstraint(
            "text_slug",
            "source_version",
            "section_index",
            name="uq_shamela_section_text_version_index",
        ),
        Index("ix_shamela_section_skeleton", "text_skeleton"),
        Index("ix_shamela_section_text_active", "text_slug", "active"),
    )
