"""T-8.2.1 — Identitätstyp scaffold tables for K-02/K-04/K-05/K-06.

Per Sprint 4 §2 (option (a) chosen 2026-05-07):

The Sprint 4 plan binds K-02..K-06 to identity-types whose substantive single
definitions are listed as **open** in EEB v1.0 §13. To satisfy the Sprint 4 §A
HG-S4-1 K-Identitaetstyp-Trennung-Test (each K-rule reads ONLY its passende
Identitätstyp), the four missing tables are scaffolded here with a v1.0
minimal shape:

    (identity_uuid PK,
     project_uuid FK,
     identity_key       — canonical key (e.g., "basmala", "ʿabd_Allāh")
     source_pattern     — source-side pattern to scan Segments for
     expected_rendering — canonical target-language rendering
     active             — H-5 inactivation, no deletion)

The four tables stay structurally distinct (no shared discriminator —
DBB §B Abkürzung 3 generalizes to "shared tables with type discriminator"
being a smell for separation-of-concerns work). Calibration values
(severity weights, detection thresholds) per Sprint 4 §B remain
configurable, never pre-set.

Subject-type binding (per migration 0011's `ck_konsistenz_befund_subject_type`):
    K-02 → formel_verzeichnis_id   → FormelVerzeichnisEintrag
    K-04 → transliterations_muster → TransliterationsMusterEintrag
    K-05 → source_identity         → QuellenIdentitaet
    K-06 → structural_key          → StrukturellerSchluessel
"""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base, TimestampMixin


class FormelVerzeichnisEintrag(Base, TimestampMixin):
    """K-02 Identitätstyp — religious formulas + standard index entries.

    Examples: Basmala, Salutation upon the Prophet, Tarḍiyah, common Hadith
    citation index entries. Each entry binds one source pattern to a
    canonical target rendering for the project.
    """

    __tablename__ = "formel_verzeichnis_eintraege"

    identity_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    project_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    identity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_pattern: Mapped[str] = mapped_column(String(1024), nullable=False)
    expected_rendering: Mapped[str] = mapped_column(String(1024), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __table_args__ = (
        UniqueConstraint("project_uuid", "identity_key", name="uq_formel_verzeichnis_project_key"),
    )


class TransliterationsMusterEintrag(Base, TimestampMixin):
    """K-04 Identitätstyp — transliteration scheme entries.

    Each entry binds one source-side Arabic string to a canonical
    transliteration form for the project's transliteration scheme. The
    rule flags Segments where the source string appears but the target
    uses a different transliteration than the canonical one.
    """

    __tablename__ = "transliterations_muster_eintraege"

    identity_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    project_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    identity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_pattern: Mapped[str] = mapped_column(String(1024), nullable=False)
    expected_rendering: Mapped[str] = mapped_column(String(1024), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __table_args__ = (
        UniqueConstraint(
            "project_uuid", "identity_key", name="uq_transliterations_muster_project_key"
        ),
    )


class QuellenIdentitaet(Base, TimestampMixin):
    """K-05 Identitätstyp — source-citation identity records.

    Each entry binds one canonical source identifier (e.g., "Bukhari, ṣaḥīḥ,
    K. al-īmān, bāb 1") to its canonical citation rendering. The rule
    flags Segments where the source identifier appears but the citation
    is rendered divergently across the project.
    """

    __tablename__ = "quellen_identitaeten"

    identity_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    project_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    identity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_pattern: Mapped[str] = mapped_column(String(1024), nullable=False)
    expected_rendering: Mapped[str] = mapped_column(String(1024), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __table_args__ = (
        UniqueConstraint("project_uuid", "identity_key", name="uq_quellen_identitaet_project_key"),
    )


class StrukturellerSchluessel(Base, TimestampMixin):
    """K-06 Identitätstyp — recurring structural patterns.

    Examples: section heading conventions, footnote markers, chapter
    delimiters. Each entry binds a structural source pattern to its
    canonical target rendering. The rule flags Segments using the
    pattern with divergent target structure.
    """

    __tablename__ = "strukturelle_schluessel"

    identity_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    project_uuid: Mapped[_uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.project_uuid", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    identity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_pattern: Mapped[str] = mapped_column(String(1024), nullable=False)
    expected_rendering: Mapped[str] = mapped_column(String(1024), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __table_args__ = (
        UniqueConstraint(
            "project_uuid", "identity_key", name="uq_struktureller_schluessel_project_key"
        ),
    )
