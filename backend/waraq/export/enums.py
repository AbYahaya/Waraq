"""T-9.2.1 — Export-side enums."""

from __future__ import annotations

from enum import StrEnum


class ExportGateMode(StrEnum):
    """The preflight state at the moment the export job started.

    Recorded on EXPORT_EVENT.payload['gate_mode']. Mirrors the canonical
    Sprint 4 PreflightState values that permit export — `exportierbar`
    (no warnings) and `exportierbar_mit_warnungen` (warnings accepted
    per-gate per Sprint 4 R-S4-09).
    """

    EXPORTIERBAR = "exportierbar"
    EXPORTIERBAR_MIT_WARNUNGEN = "exportierbar_mit_warnungen"
