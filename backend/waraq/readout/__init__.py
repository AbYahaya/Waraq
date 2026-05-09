"""T-10.1.1 + T-10.1.2 + T-10.2.1 — Provenance readout (Sprint 6).

Per Sprint 6 §2: the canonical scope-trennende read layer over the
provenance graph populated across Sprints 0–5. Read-only by design —
the module writes NOTHING (no Revision, no Decision Event, no
Log-Eintrag, no PO).

Distinct from `waraq.history` (the M2-closeout aggregate layer used by
the M4 UI sidebar) — `waraq.history` deliberately denormalizes (page →
all segments under page; project → all pages). `waraq.readout` is the
canonical Sprint-6 surface with strict scope discipline:

- `get_pos_for_segment` → POs with `scope_type=segment` AND
  `scope_uuid=satz_uuid` only. No page-scoped, no project-scoped, no
  artefact-scoped.
- `get_export_events_for_segment` → lineage-aware lookup via
  `revision_snapshot[]` (NEVER via a segment-FK shortcut on the
  EXPORT_EVENT row — the canonical structural failure mode named in
  Sprint 6 R-S6-01). Walks all Revision rows for the segment, including
  reactivation cycles (R-S6-02).
- `get_segment_readout` → segment-scoped Revisions + segment-scoped DEs
  + segment-scoped POs + EXPORT_EVENT werkweite Referenzen (marked
  `als_werkweite_referenz=True`).
- `get_page_readout` → ONLY page-scoped DEs (R-S6-04: page history must
  not collapse to all-events-of-scope).
- `get_project_readout` → ONLY project-scoped DEs + EXPORT_EVENT-POs
  (R-S6-05: account-scoped DEs explicitly excluded per Dokument 2 §2D
  gebundener Resthinweis).
- `get_log_entries` → Log-Eintrag rows with optional filter (R-S6-06:
  Log-Eintrag rows never appear in segment / page / project readouts).

All readouts return chronologically ordered results (by `created_at`).
"""

from waraq.readout.service import (
    LogEntryFilter,
    PageReadout,
    ProjectReadout,
    SegmentExportEventRef,
    SegmentReadout,
    get_export_events_for_segment,
    get_log_entries,
    get_page_readout,
    get_pos_for_segment,
    get_project_readout,
    get_segment_readout,
)

__all__ = [
    "LogEntryFilter",
    "PageReadout",
    "ProjectReadout",
    "SegmentExportEventRef",
    "SegmentReadout",
    "get_export_events_for_segment",
    "get_log_entries",
    "get_page_readout",
    "get_pos_for_segment",
    "get_project_readout",
    "get_segment_readout",
]
