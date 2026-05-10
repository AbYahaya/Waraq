"""T-9.1.1 + T-9.1.2 — Preflight exceptions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from waraq.preflight.guard_near import GuardNearResult


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


class GuardNearBlocked(PreflightError):
    """Raised when one or more §4.7.3 guard-near checks block opening
    the preflight dialog.

    Per Dokument 1 §4.7.3: "guard-near; blocking; check before
    preflight dialog. ... if a violation exists, the preflight dialog
    is not opened. Resolution requires technical [restoration of the
    font / removal of the violation]". This exception type signals
    that opening a preflight run was refused for guard-near reasons —
    distinct from any in-dialog Pflichtfrage / gate state.

    The `result` attribute carries the full `GuardNearResult` so
    callers (HTTP layer, UI) can surface the specific blockers.
    """

    def __init__(self, message: str, *, result: GuardNearResult) -> None:
        super().__init__(message)
        self.result = result
