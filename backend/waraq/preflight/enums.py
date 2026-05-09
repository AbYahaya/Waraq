"""T-9.1.1 + T-9.1.2 — Preflight enums and gate-slot codes.

Slot discipline note (HG-S4-3): `BlockingReason` enumerates ONLY the
slots and reasons that are belegt this sprint. P-01/P-02/P-05/P-06 and
W-04..W-08 are deliberately absent — adding them silently is a canon
violation per Dokument 2 §6.
"""

from __future__ import annotations

from enum import StrEnum


class PreflightState(StrEnum):
    """Per Sprint 4 §2 state machine.

    `nicht_gestartet → laeuft → exportierbar | exportierbar_mit_warnungen
    | blockiert`. Re-entry into `laeuft` is permitted by re-running the
    evaluator on a fresh Job (each preflight run is its own Job).
    """

    NICHT_GESTARTET = "nicht_gestartet"
    LAEUFT = "laeuft"
    EXPORTIERBAR = "exportierbar"
    EXPORTIERBAR_MIT_WARNUNGEN = "exportierbar_mit_warnungen"
    BLOCKIERT = "blockiert"


class BlockingReason(StrEnum):
    """Distinct reason codes for `blockiert` state (Sprint 4 §A HG-S4-3).

    Each reason is a separate enum entry — P-03 and P-04 are structurally
    distinct (Sprint 4 R-S4-... and Dokument 2 §2.4: "P-03 ist
    eigenständiges blockierendes Gate, strukturell gleichrangig neben
    P-04"). Konfigurationsschicht failure is its own reason and does not
    occupy a P-Slot.
    """

    P_03_KRITISCH = "p_03_kritisch"
    P_04_HOCH_PFLICHTHINWEIS = "p_04_hoch_pflichthinweis"
    HADITH_H2 = "hadith_h2"
    KONFIGURATIONSSCHICHT_UNVOLLSTAENDIG = "konfigurationsschicht_unvollstaendig"


class WarningSlot(StrEnum):
    """Distinct slot codes for warning gates."""

    W_01_MITTEL_AUDIT = "w_01_mittel_audit"
    W_02_KONSISTENZ = "w_02_konsistenz"
    W_03_FORMATVORLAGEN_GRADUELL = "w_03_formatvorlagen_graduell"
    HADITH_H1 = "hadith_h1"


class HadithStellenTyp(StrEnum):
    """Per Dokument 1 §4.16.4 — N-1..N-10 passage types."""

    N_1 = "N-1"
    N_2 = "N-2"
    N_3 = "N-3"
    N_4 = "N-4"
    N_5 = "N-5"
    N_6 = "N-6"
    N_7 = "N-7"
    N_8 = "N-8"
    N_9 = "N-9"
    N_10 = "N-10"


class HadithKlasse(StrEnum):
    """Per Dokument 1 §4.16.4 — derived verification class."""

    H_0 = "H-0"
    H_1 = "H-1"
    H_2 = "H-2"
