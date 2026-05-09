"""§4.15.1 — AR-Referenzbestand + Qurʾān translation fallback.

Two tables:

- `ArReferenzVerse` — independent local Arabic reference collection
  per §4.15.1. Local-only by canon ("At no point API-supported; no
  API primary path and no fallback status"). Populated by Tanzil-Hafs
  ingest in v1.0 (concrete source designation canonically still open;
  Tanzil-Hafs picked as a v1.0 implementation choice, not a canon
  amendment).

- `QuranTranslationVerse` — local fallback copies of the quranenc.com
  translations (`german_rwwad` / `english_rwwad`). Per §4.15.1 the
  primary carrier is the quranenc.com API; this table is the
  **fallback on API failure** + the source of weekly-sync refreshes.
  `translation_key` is the upstream identifier; `source_version` is
  the upstream release tag (when none, callers pass an ISO-date stamp).

Both tables follow the same source-name + source-version supersession
pattern: a re-ingest with a fresh `source_version` flips prior rows
to `active=false` (H-5; no deletion). §4.15.3 protection of project
Qurʾān passages against AR/translation collection updates lives
separately at the project-passage-snapshot layer (Phase 2F).

`text_skeleton` on AR rows is the OCR-stage matching key (§4.15.2
local-only: "During the OCR run only local matching takes place; no
external call in the OCR phase") — diacritic-stripped, Tatweel-
stripped, NFC, Alif-variants normalized. §4.15.4 source-citation
insertion uses (sura, aya) direct lookup.
"""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy import Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base, TimestampMixin


class ArReferenzVerse(Base, TimestampMixin):
    """One āya in the Arabic Qurʾān reference collection.

    Attributes:
        verse_uuid: PK.
        source_name: Canonical source label (e.g., "tanzil-hafs-uthmani").
            Recorded so re-ingest from a future source replaces cleanly.
        source_version: Version string from the upstream source. Tanzil
            tags releases (e.g., "tanzil-1.1.0"); recorded for audit.
        sura_index: 1..114 (CHECK constraint in migration).
        aya_index: 1..N within sura (no per-sura upper bound enforced —
            sura-length variation makes that fragile; the upstream
            source is trusted).
        text_vocalized: Full vocalized form (Hafs/Uthmani). Verbatim
            from the upstream source — no normalization at ingest.
        text_skeleton: NFC + Tatweel-stripped + diacritic-stripped form,
            derived once at ingest. Used as the OCR-matching key per
            §4.15.2.
        active: H-5 inactivation. Old rows from a previous source-version
            re-ingest get `active=false`; new rows take their place.
    """

    __tablename__ = "ar_referenz_verses"

    verse_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    source_name: Mapped[str] = mapped_column(String(64), nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    sura_index: Mapped[int] = mapped_column(Integer, nullable=False)
    aya_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text_vocalized: Mapped[str] = mapped_column(String, nullable=False)
    text_skeleton: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "source_name",
            "source_version",
            "sura_index",
            "aya_index",
            name="uq_ar_referenz_verse_source_sura_aya",
        ),
        Index("ix_ar_referenz_verse_skeleton", "text_skeleton"),
        Index(
            "ix_ar_referenz_verse_source_active",
            "source_name",
            "active",
        ),
    )


class QuranTranslationVerse(Base, TimestampMixin):
    """One translation āya — local fallback copy of a quranenc.com
    translation per §4.15.1.

    The API at quranenc.com is the **primary** carrier; this table is
    the canonical fallback on API failure AND the source of the
    weekly-sync refresh. Each refresh writes rows with a fresh
    `source_version` (typically an ISO-date stamp); prior versions go
    `active=false`. §4.15.3 protects already-recognized project
    passages from automatic re-fetch — that protection lives at the
    project-passage-snapshot layer, not here.

    Canonical translation keys (per §4.15.1):
        - `german_rwwad`  (German Rwwad translation)
        - `english_rwwad` (English Rwwad translation)
    """

    __tablename__ = "quran_translation_verses"

    verse_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    translation_key: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    sura_index: Mapped[int] = mapped_column(Integer, nullable=False)
    aya_index: Mapped[int] = mapped_column(Integer, nullable=False)
    translation_text: Mapped[str] = mapped_column(String, nullable=False)
    footnotes: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "translation_key",
            "source_version",
            "sura_index",
            "aya_index",
            name="uq_quran_translation_verse_key_sura_aya",
        ),
        Index(
            "ix_quran_translation_verse_key_active",
            "translation_key",
            "active",
        ),
        Index(
            "ix_quran_translation_verse_lookup",
            "translation_key",
            "sura_index",
            "aya_index",
        ),
    )
