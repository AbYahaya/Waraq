"""Exceptions for the T-6.1.1 release gate (Freigabeschranke)."""

from __future__ import annotations


class ReleaseGateError(Exception):
    """Base class for release-gate violations."""


class GateNotInWarningState(ReleaseGateError):
    """`confirm_translation_with_warning` was called but the gate is not in
    a warnings-only state (it's either uebersetzungsreif — no warnings to
    confirm — or hard-blocked by kritisch findings, in which case warnings
    confirmation is meaningless).

    Per Sprint 2 §2 / Gate-Test-Mit-Warnung-Erfordert-Bestaetigung-Test:
    confirmation is the user-side handle from blockiert(warnings-only) →
    uebersetzbar_mit_warnung. Calling it from any other state is a no-op
    that should fail loudly rather than silently writing a useless DE."""


class GateNotReady(ReleaseGateError):
    """`start_translation` was called but the gate is neither
    `uebersetzungsreif` nor `uebersetzbar_mit_warnung`. Per Sprint 2 §2 /
    Gate-Test-Kein-Auto-Translation-Start-Test, translation cannot begin
    from `blockiert` (DBB §B Abkürzung 5: auto-trigger when last page
    flips to `go` is the named structural failure mode)."""
