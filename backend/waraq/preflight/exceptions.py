"""T-9.1.1 + T-9.1.2 — Preflight exceptions."""

from __future__ import annotations


class PreflightError(Exception):
    """Base class for preflight errors."""


class SlotNotImplemented(PreflightError):
    """Raised when code attempts to file a finding under an open P/W slot.

    Per Sprint 4 §A HG-S4-3 (kein-stiller-slot-fill): P-01, P-02, P-05,
    P-06, W-04..W-08 are explicitly **offen**. Any attempt to occupy
    these slots is a canon violation per Dokument 2 §6.
    """


class PflichthinweisCannotBeWarning(PreflightError):
    """Raised on any code path that would route a P-04 finding (hoch
    audit / Pflichthinweis) into a W-Slot.

    Per Sprint 4 R-S4-05 / DBB ticket-level risk for T-9.1.2:
    "Pflichthinweis-Klasse (P-04) als W-Warnung behandelt — blockiert
    Export nicht mehr, wenn nötig" must be structurally impossible.
    """
