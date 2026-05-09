"""T-9.2.1 — Export-side exceptions."""

from __future__ import annotations


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
