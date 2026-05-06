"""Canonical enums for the CONFLICT-Erkennung service (T-5.1.2).

All values are wire/DB strings. CHECK constraints in migration 0009
enforce the value sets server-side.
"""

from __future__ import annotations

from enum import StrEnum


class RuleSource(StrEnum):
    """Per Sprint 1 §2 — what kind of automatic rule attempted to act."""

    GLOSSARY = "glossary"
    TERMINOLOGY = "terminology"
    # Forward-canonical: future Stilfeature pipeline will trigger conflicts
    # when it tries to overwrite locked Segments. The enum slot is reserved
    # so detection wiring is forward-compatible.
    STYLE_PROFILE = "style_profile"


class ConflictType(StrEnum):
    """Per Sprint 1 §2 — taxonomy of conflict shapes.

    Open vocabulary: the canon's "..." indicates more types may emerge in
    later sprints. The migration's `conflict_type` column is plain
    VARCHAR(64) without a CHECK so new types can be added without
    schema migration; this enum is the codebase's curated reference set.
    """

    GLOSSAR_VS_SPERRFLAG = "glossar_vs_sperrflag"
    TERMINOLOGIE_VS_SPERRFLAG = "terminologie_vs_sperrflag"
    KONZEPT_VS_KONZEPT = "konzept_vs_konzept"


class ConflictState(StrEnum):
    """Per Sprint 1 §2 — `offen → aufgeloest`. ASCII transliteration of
    "aufgelöst" used in the wire/DB form."""

    OFFEN = "offen"
    AUFGELOEST = "aufgeloest"


class ResolutionType(StrEnum):
    """Per Sprint 1 §2 — the three canonical resolution paths.

    HG-S1 enforces that no fourth path exists. The conflict service's
    public surface exposes exactly three resolution functions, one per
    enum value.
    """

    LOKALE_AUSNAHME = "lokale_ausnahme"
    GLOSSAR_ANPASSEN = "glossar_anpassen"
    SPERRFLAG_AUFHEBEN = "sperrflag_aufheben"
