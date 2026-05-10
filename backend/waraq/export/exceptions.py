"""T-9.2.1 — Export-side exceptions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from waraq.canon_rules import CanonRuleViolation


class ExportError(Exception):
    """Base class for export-pipeline errors."""


class ExportNotInExportableState(ExportError):
    """Raised when `export_starten` is called against a project whose
    preflight state is `blockiert` (or `nicht_gestartet`).

    Per Sprint 5 §2 / Export-Starten-Nur-Aus-Exportierbar-Test: the
    user action is rejected at the entry check. NO Job is created,
    NO Log-Eintrag is written, NO EXPORT_EVENT is written.
    """


class PreflightStateChanged(ExportError):
    """Raised inside `run_export_job` when the preflight state at job
    start differs from the state at the moment of `export_starten`.

    Per Sprint 5 §2: the export job re-checks state at job start. If
    the state has degraded between user action and job execution (e.g.,
    a new audit finding appeared), the job fails with reason
    `preflight_state_changed`. NO artefact is produced, NO EXPORT_EVENT
    is written; the Log-Eintrag records the failure.
    """


class CanonRuleViolationsDetected(ExportError):
    """Raised inside `run_export_job` when the §2.2 pre-export verifier
    finds residual canon-rule violations on active project segments.

    Per Phase 3 sub-batch B / Dokument 1 §2.2: digit + EI2 normalization
    is the canonical primary mechanism (auto-normalize on translation
    output + manual-edit save). This exception is the defense-in-depth
    twin: when any write path bypassed normalization, the verifier
    catches the leftover violation at the export-job boundary, fails
    the Job, and writes an `export_failed` Log-Eintrag — same shape as
    `PreflightStateChanged`. NO artefact is produced, NO EXPORT_EVENT
    is written.

    The `violations` attribute carries the structured findings for the
    UI's resolution panel (which segments / which rule-kind).
    """

    def __init__(self, message: str, *, violations: list[CanonRuleViolation]) -> None:
        super().__init__(message)
        self.violations = violations
