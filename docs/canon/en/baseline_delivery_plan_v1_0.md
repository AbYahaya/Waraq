<!-- Source: Google Drive doc 1F3thl5iPdTdsNUmadQTOXTXqJrYWRnqeCtUwKQoBJwY (Baseline Delivery Plan v1.0) -->
<!-- Pulled: 2026-05-01. Place at /docs/canon/baseline_delivery_plan_v1_0.md -->

# WARAQ BASELINE DELIVERY PLAN

## Version 1.0 — overview

Describes the work state of the Waraq baselines and the corresponding sprint / delivery planning. Structurally elaborated; no coding release, no implementation release.

## 1. ASSOCIATED DOCUMENTS

| Document | Version | Status |
|---|---|---|
| Waraq Core Architecture Baseline | v1.0 | Frozen |
| Waraq Implementation Translation Baseline | v1.0 | Frozen |
| Waraq Engineering Execution Baseline | v1.0 | Frozen |
| Waraq Delivery Backlog Baseline | v1.0 | Frozen |
| Waraq Sprint-0 / Foundation Delivery Plan | v1.0 | Working basis |
| Waraq Sprint-1 / OCR Review + Lock + Glossary Delivery Plan | v1.0 | Working basis |
| Waraq Sprint-2 / Release Gate + Translation Core Delivery Plan | v1.0 | Working basis |
| Waraq Sprint-3 / Audit + Rule-Binding Completion Delivery Plan | v1.0 | Working basis |
| Waraq Sprint-4 / Consistency + Preflight Delivery Plan | v1.0 | Working basis |
| Waraq Sprint-5 / Export Artifact + Provenance Handoff Delivery Plan | v1.0 | Working basis |
| Waraq Sprint-6 / Provenance Readout + History Endpoints Delivery Plan | v1.0 | Working basis |

The baselines are frozen canonical working bases. The sprint plans are led as working basis and do not constitute implementation evidence.

## 2. IMPLEMENTATION LOGIC IN COMPACT OVERVIEW

The delivery is organized into seven operative sprints that build on each other logically. The sprints are structurally elaborated; whether and when they are implemented is not the subject of this version.

**Sprint 0 — Foundation:** UUID service, INVARIANT-Guard, all core-object schemas, REVISION / EVENTING / PROVENANCE core, job infrastructure, upload pipeline, OCR core processing with error-class profiling. First end-to-end runnable foundation.

**Sprint 1 — OCR Review + Lock + Glossary:** lineage service, OCR review status (Go / No-Go per page), lock-flag management with persistent `conflict_instance`, glossary / concept-ID basis.

**Sprint 2 — Release Gate + Translation Core:** release gate as workflow gate before translation start, translation job with checkpoint and lock-flag respect, TRANSLATION-PO and revision UUID on text change. Optional: glossary binding in the translation path (T-7.2.1) and promotion pipeline stages 1–2 (T-7.3.1).

**Sprint 3 — Audit + Rule-Binding Completion:** audit-finding table and full rule check A-01 to D-03. Conditional: glossary binding (T-7.2.1, if not Sprint 2) and promotion pipeline stage 3 (T-7.3.2, if T-7.3.1 present).

**Sprint 4 — Consistency + Preflight:** identity- / reference-based consistency engine K-01 to K-07, each K-rule against the matching identity type. Preflight in the scope of the canon currently substantiated:

- Preflight configuration layer separated from gate-check layer.
- Substantiated gates: P-03 (critical audit violations), P-04 (high-audit obligation indications), W-01 (medium-audit indications), W-02 (consistency warnings K-01–K-07), W-03 (gradual document-style deviations).
- Hadith verification status as an own named group within the gate-check layer (H-2 blocking, H-1 warning-based, no P / W slot occupancy).
- Open and not substantively substantiated: P-01, P-02, P-05, P-06 and W-04 to W-08.
- Guard-near pre-checks (digit standard, RTL, document-style integrity, critical font availability) before the preflight dialog.
- Export-run event (log ID) created for the first time.

**Sprint 5 — Export Artifact + Provenance Handoff:** artefact creation after green preflight, EXPORT_EVENT atomic and unchangeable via PROVENANCE core, `revision_snapshot[]` and `active_decision_event_uuids[]` as work-state-related point-in-time snapshot.

**Sprint 6 — Provenance Readout + History Endpoints:** segment-related provenance queries, EXPORT_EVENT linkage via `revision_snapshot[]` lookup, page and project history, four scope-separated backend history endpoints.

## 3. PLANNING STATE WITH RESPECT TO THE BASELINE

The Waraq Delivery Backlog Baseline v1.0 is structurally fully elaborated. Structurally fully here means: every ticket of the baseline (T-1.1.1 to T-10.2.1) is described with goal, scope, acceptance criteria, dependencies, and critical risks, and entered into the sprint assignment.

This structural completeness does not mean:

- that the tickets are implemented,
- that they are tested or released,
- that a coding release has been issued,
- that the sprint plans have been productively implemented.

Within the structural baseline planning, T-7.3.1 (promotion pipeline stages 1–2) and T-7.3.2 (promotion pipeline stage 3) have a conditional placement between Sprint 2 and Sprint 3. Depending on how these two tickets are addressed in the actual implementation case, they remain either regularly placed in the sprint structure or trail behind as the last open baseline tickets.

All further statements about implementation readiness, test completion, or productive release are not part of this version.

## 4. WHAT IS DELIBERATELY OUTSIDE THE BASELINE

The following topics are not part of the Delivery Backlog Baseline v1.0 and remain deliberately reserved for later phases:

- **Calibration:** OCR confidence thresholds, vocalization thresholds, aggregation-logic thresholds, frequency thresholds of the §4.18 track-2-class-B general logic, confidence threshold for Qurʾān recognition — structurally laid down and intended to be configurable, calibration after gold-corpus tests and real measurement.
- **Live test package interface 5:** the E-5 test-operation questions and the concrete values for rates, backoff, upper limits, resumption, and timeout / retry values per source are kept as a separate full-text work block in Block 3 and parked until real execution.
- **UI build-out:** Why-panel rendering, history presentations, finding-management surface, preflight UI, export dialog. The structural backend foundation is laid down in the baseline; the elaborated UI is a product expansion stage.
- **Additional export targets:** Adobe InDesign / Affinity Publisher export and further export formats.
- **Further languages and source languages:** extension to further source or target languages beyond the currently canonized language pairs.
- **Style-feature follow-on work:** the follow-on tasks named in Dokument C v1.1 §3 (formal integration analysis, CRs for Core Architecture / Engineering Execution / Delivery Backlog Baseline, audit integration, ticket definition, sprint planning, calibration of the open thresholds, coding release) remain expressly open.
- **Real Shamela actual capture (interface 6):** including replay R-1 to R-7 and hadith-related P-2 reconciliation — parked.
- **Productization and scaling:** guest-user timeout calibration, upload chunk sizes, performance optimizations, database indexes, multi-tenancy, and everything that goes beyond the single-user translation platform.

## 5. WORK RULE FOR THE FUTURE

For all further work on the baselines and sprint plans the following rules apply:

1. **No silent changes.** Every substantive change to a canonical document is led as an explicit change request, with indication of the affected document, the affected location, the reason for the change, and a version increment.
2. **No covert further development.** New requirements, new features, or new architecture decisions are not accommodated within existing version numbers but identified as new versions or new documents.
3. **No new baselines without explicit release.** Every new planning level — whether new architecture layer, new backlog version, or new sprint planning — requires an explicit release decision.
4. **Explicit replacement on new material.** If more authentic source material or authentic fragments later emerge, the affected version is replaced in an explicit step by a new cleaned version on the basis of this material, or cleaned again. Silent re-purposing is not permissible.
5. **No code and no implementation release without explicit instruction.** Structural completeness of the planning does not mean implementation release.

*Waraq Baseline Delivery Plan v1.0 — end of version*