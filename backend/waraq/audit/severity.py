"""Configurable severity / verstossklasse mapping table.

Per Sprint 3 §2: severity weights and verstossklasse mappings are
**configurable, never hard-coded constants** (Audit-Severity-
Konfigurations-Test). This module provides:

- `SeverityTable` — frozen dataclass mapping regelkennung → (severity,
  class). Constructed explicitly per call.
- `default_severity_table()` — the canon-default table reflecting ITB §4:
    A-01 Hoch/Pflichthinweis    A-02 Mittel/Hinweis    A-03 Mittel/Hinweis
    B-01 Hoch/Pflichthinweis    B-02 Hoch/Pflichthinweis
    B-03 Mittel/Hinweis         B-04 Mittel/Hinweis
    C-01 Kritisch/Blockierend   C-02 Hoch/Pflichthinweis
    C-03 Hoch/Pflichthinweis
    D-01 Mittel/Hinweis         D-02 Mittel/Hinweis
    D-03 Kritisch/Blockierend  (escalated per ITB §4.2)

The table is *not* burned into rule check functions — they read the
classification from the table at audit-run time, so an operator can
swap the table without touching rule code.
"""

from __future__ import annotations

from dataclasses import dataclass

from waraq.audit.enums import Schweregrad, Verstossklasse
from waraq.audit.exceptions import UnknownRegelkennung


@dataclass(frozen=True, kw_only=True, slots=True)
class SeverityEntry:
    schweregrad: Schweregrad
    verstossklasse: Verstossklasse


@dataclass(frozen=True, kw_only=True, slots=True)
class SeverityTable:
    entries: dict[str, SeverityEntry]

    def get(self, regelkennung: str) -> SeverityEntry:
        e = self.entries.get(regelkennung)
        if e is None:
            raise UnknownRegelkennung(
                f"regelkennung {regelkennung!r} not present in severity table"
            )
        return e


def default_severity_table() -> SeverityTable:
    """Default table reflecting ITB §4 / Dokument 1 §4.6.

    Per Sprint 3 §B "Calibration values: ... configurable, never pre-set"
    — this default is a non-canonical operational starting point. Tests
    pass an explicit table to verify that swapping the defaults retunes
    the audit-run output (Audit-Severity-Konfigurations-Test).
    """
    hoch_pflicht = SeverityEntry(
        schweregrad=Schweregrad.HOCH, verstossklasse=Verstossklasse.PFLICHTHINWEIS
    )
    mittel_hinweis = SeverityEntry(
        schweregrad=Schweregrad.MITTEL, verstossklasse=Verstossklasse.HINWEIS
    )
    kritisch_block = SeverityEntry(
        schweregrad=Schweregrad.KRITISCH, verstossklasse=Verstossklasse.BLOCKIEREND
    )
    return SeverityTable(
        entries={
            "A-01": hoch_pflicht,
            "A-02": mittel_hinweis,
            "A-03": mittel_hinweis,
            "B-01": hoch_pflicht,
            "B-02": hoch_pflicht,
            "B-03": mittel_hinweis,
            "B-04": mittel_hinweis,
            "C-01": kritisch_block,
            "C-02": hoch_pflicht,
            "C-03": hoch_pflicht,
            "D-01": mittel_hinweis,
            "D-02": mittel_hinweis,
            "D-03": kritisch_block,
        }
    )


def all_regelkennungen() -> tuple[str, ...]:
    """The 13 canonical rule IDs in ITB §4 ordering."""
    return (
        "A-01",
        "A-02",
        "A-03",
        "B-01",
        "B-02",
        "B-03",
        "B-04",
        "C-01",
        "C-02",
        "C-03",
        "D-01",
        "D-02",
        "D-03",
    )
