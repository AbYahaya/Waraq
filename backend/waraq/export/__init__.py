"""T-9.2.1 — Export module (translation export artefact + EXPORT_EVENT).

Per Sprint 5 §2 + DBB §A (EXPORT_EVENT-Atomarität unverhandelbar) +
DBB §B Abkürzung 4 (no EXPORT_EVENT before artefact completion):

The export module produces three outputs per attempt:
- The DOCX artefact, persisted to the artefact store on full success.
- The EXPORT_EVENT row, written via PROVENANCE-Kern `create_po` ONLY
  after the artefact is fully and successfully created.
- A Log-Eintrag (Exportlauf-Ereignis log family from Sprint 4) on
  every attempt — successful, failed, or blocked.

The atomicity rule binds EXPORT_EVENT to artefact: either both exist,
or neither does. Implementation: the post-build commit is a single
in-session sequence of (a) move artefact to persistent location,
(b) `create_po` for EXPORT_EVENT, (c) mark Job COMPLETED. If any step
raises, the caller's transaction rolls back; no EXPORT_EVENT, no
orphaned artefact.

EXPORT_EVENT addressing: per the 2026-05-04 + 2026-05-06 decisions,
`scope_type='project'` + `scope_uuid=project_uuid` with artefact
identity (filename, format, sha256, size_bytes) in `payload`.
ScopeType remains the canonical 5-value enum (CLAUDE.md §5.8).
"""

from waraq.export.artefact_storage import (
    ArtefactStore,
    ArtefactStoreCommitFailed,
    InMemoryArtefactStore,
)
from waraq.export.enums import ExportGateMode
from waraq.export.exceptions import (
    CanonRuleViolationsDetected,
    ExportError,
    ExportNotInExportableState,
    PreflightStateChanged,
)
from waraq.export.service import (
    ExportConfig,
    ExportResult,
    export_starten,
    run_export_job,
)
from waraq.export.snapshot import (
    ALLOWLISTED_DECISION_SOURCES,
    collect_active_decision_event_uuids,
    collect_revision_snapshot,
)

__all__ = [
    "ALLOWLISTED_DECISION_SOURCES",
    "ArtefactStore",
    "ArtefactStoreCommitFailed",
    "CanonRuleViolationsDetected",
    "ExportConfig",
    "ExportError",
    "ExportGateMode",
    "ExportNotInExportableState",
    "ExportResult",
    "InMemoryArtefactStore",
    "PreflightStateChanged",
    "collect_active_decision_event_uuids",
    "collect_revision_snapshot",
    "export_starten",
    "run_export_job",
]
