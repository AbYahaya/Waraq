"""Hadith canonical enums per Dokument 1 §4.16.6 + §4.16.7.

Every value here is named in the canon; changes go through a CR
(CLAUDE.md §2.6). Column-level CHECK constraints in the migration
enforce the same value sets in Postgres.
"""

from __future__ import annotations

from enum import StrEnum


class Quellenrolle(StrEnum):
    """Per Dokument 1 §4.16.6 — source role on a Single-source result.

    Mandatory snapshot field — "fixed at the time of the verification
    run; no dynamic back-derivation against the current canon"
    (§4.16.6). The four canonical values:

      - `pflicht`              — mandatory set (P-1/P-2/P-3 per §4.16.1)
      - `erweitert_aktiv`      — active extended set hit (E-1..E-4 if
                                 they ever come back online)
      - `erweitert_sonderrolle`— E-5 special role (§4.16.2)
      - `erweitert_suspendiert`— suspended extended source (E-1, E-2,
                                 E-3, E-4 currently)

    Canonical exclusion: hadithportal.com may NOT be carried in any
    source field; not represented as an enum value either.
    """

    PFLICHT = "pflicht"
    ERWEITERT_AKTIV = "erweitert_aktiv"
    ERWEITERT_SONDERROLLE = "erweitert_sonderrolle"
    ERWEITERT_SUSPENDIERT = "erweitert_suspendiert"


class Vokalisierungsklasse(StrEnum):
    """Per Dokument 1 §4.16.7 — vocalization escalation class.

      - `V-0` (automatically tolerable): orthographic-technical variants
              without sound or meaning change. Automatic adoption,
              no logging obligation at the passage level.
      - `V-1` (logging-mandatory, no escalation): vocalization-density
              differences without meaning change. Documentation in
              passage logging; no decision_event on inaction.
      - `V-2` (escalation-mandatory): meaning, iʿrāb, sarf, isnād-id,
              or matn-lexeme deviation. Active user resolution required
              via §4.16.5 action types (decision_source=conflict_resolution).

    Aggregation rule: with multiple deviations in a passage, the highest
    occurring class applies (V-0 < V-1 < V-2). Fallback rule: with
    ambiguity of the type assignment, the higher class is applied — no
    silent down-classification.
    """

    V_0 = "V-0"
    V_1 = "V-1"
    V_2 = "V-2"


__all__ = ["Quellenrolle", "Vokalisierungsklasse"]
