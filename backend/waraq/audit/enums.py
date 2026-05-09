"""Audit canonical enums — Sprint 3 §2 / Dokument 1 §4.6.

Three orthogonal axes:

- `Schweregrad`  — severity (kritisch | hoch | mittel)
- `Verstossklasse` — gate-class (blockierend | pflichthinweis | hinweis)
- `AufloesungsStatus` — resolution-state (offen | aufgeloest | quittiert)

Per Sprint 3 §2 the mapping `(Schweregrad → Verstossklasse → preflight
slot)` is configurable, never hard-coded as a one-to-one. The default
table lives in `severity.py` and reflects ITB §4.

Verbatim per CLAUDE.md §2.4: `verstossklasse`, `schweregrad`,
`aufloesungsstatus` are canonical column names — preserve identically
in code. The umlauted form `auflösungsstatus` from Dokument 1 transliterates
to the ASCII column name in the DB layer (matches the convention used by
`konsistenz_befunde`).
"""

from __future__ import annotations

from enum import StrEnum


class Schweregrad(StrEnum):
    KRITISCH = "kritisch"
    HOCH = "hoch"
    MITTEL = "mittel"


class Verstossklasse(StrEnum):
    BLOCKIEREND = "blockierend"
    PFLICHTHINWEIS = "pflichthinweis"
    HINWEIS = "hinweis"


class AufloesungsStatus(StrEnum):
    OFFEN = "offen"
    AUFGELOEST = "aufgeloest"
    QUITTIERT = "quittiert"
