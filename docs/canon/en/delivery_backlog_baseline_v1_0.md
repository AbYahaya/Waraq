<!-- Source: Google Drive doc 1_A_sbzOPK1u6iqE0QsG_fAMoPJW7gSDeXbm_F6ftLa0 (DELIVERY BACKLOG BASELINE v1.0) -->

# WARAQ DELIVERY BACKLOG BASELINE v1.0 — Ticketable delivery structure

All terms, module names, object names, and invariant labels follow exclusively the established canon (Document 1, Document 2, Block 3) and the Engineering Execution Baseline v1.0. No new features. No new terminology. No change to canon logic.

## DEFINITION OF DONE (DoD)

Placed up front because every ticket is checked against this DoD. A ticket counts as done when all of the following conditions are met:

| Criterion | Requirement |
|---|---|
| Code | Implemented, reviewed, merged. |
| Tests | All tests required for this ticket green. No merge with red T-H test. |
| Persistence | All affected core objects correctly written to tables. No data loss on restart. |
| Logs | All prescribed log entries (log ID via EVENTING) created. No Revisions-UUID for check operations. |
| Guard behavior | INVARIANT guard active and blocks all relevant violations. Guard not deactivatable. |
| Scope correctness | All POs carry correct `scope_type` + `scope_uuid`. No hard-coded `satz_uuid` mandatory field. |
| Non-goals respected | Not a single non-goal of the ticket has been implemented. |
| Regression tests | All regression tests from the previous milestone remain green. |
| Style-feature test families (CR-3) | For tickets in families F2 (promotion / style-rule development) and F3 (audit / conflict / marker), the style-feature test families substantively defined in CR-2 must be met as acceptance criteria. |

## TICKETABLE BACKLOG UNITS

Ticket-ID schema: `T-{WS}.{AP}.{Seq}` — e.g., T-1.1.1 = Workstream 1, AP 1.1, first ticket.

### WS-1: Foundation

**T-1.1.1 — Implement UUID assignment service.** AP-1.1 | Milestone M-1 | Critical Path: Yes (Step 1). Goal: implement `new_uuid()` as deterministic, collision-free UUID generator. Pure logic layer, no own database table. Module: IDENTITY. Acceptance: ✓ `new_uuid()` produces a new unique UUID each call; ✓ two consecutive calls → different UUIDs; ✗ no own persistence. Dependencies: none. Risk: collisions on parallel calls without cryptographically secure generator.

**T-1.1.2 — UUID immutability and inactivation logic.** AP-1.1 | M-1 | Critical Path: Yes. Goal: `assert_immutable(uuid)` and `mark_inactive(uuid)`. UUID is never deleted, only inactivated. Invariants: H-5. Tests: T-H5-01, T-H5-02. Dependencies: T-1.1.1.

**T-1.2.1 — INVARIANT guard: lock-flag protection (H-1, H-2).** AP-1.2 | M-1 | Critical Path: Yes (Step 2). Goal: guard for H-1/H-2 — every automatic write operation on a segment with active `lock_flag` is blocked. ✗ Guard not deactivatable. Tests: T-H1-01, T-H1-02. Dependencies: T-1.1.1, T-1.1.2.

**T-1.2.2 — INVARIANT guard: H-4, H-5, H-6, H-7.** AP-1.2 | M-1 | Critical Path: Yes. Goal: H-4 (no Revisions-UUID for check operations), H-5 (UUID immutability), H-6 (no silent resolution of terminology/lock-flag conflicts), H-7 (no automatic promote). On H-6 violation attempt: mark conflict as open, do not silently resolve. Tests: T-H2-01, T-H2-02, T-H4-01, T-H4-02, T-H6-01, T-H7-01.

**T-1.3.1 — Core-object schemas: Project, Page, Block, Segment.** AP-1.3 | M-1 | Critical Path: Yes (Step 3). Project with `project_uuid`; Page (`page_uuid`, `project_uuid` FK, `ocr_status`, `completion_mark`, `active`); Block (`block_uuid`, `page_uuid` FK, `block_type`, `sequence`, `active`); Segment (`satz_uuid`, `block_uuid` FK, `lock_flag`, `active`, `current_rev_uuid`, `translation_uuid`). `lock_flag` enum: `none | manual_local | manual_editorial`. Decision-Event schema accepts `scope_type = project`. ✗ No application logic in this ticket. Dependencies: T-1.1.1, T-1.2.1.

**T-1.3.2 — Core-object schemas: Revision, Decision Event, Log entry, EXPORT_EVENT.** AP-1.3 | M-1 | Critical Path: Yes. `change_source` in Revision = enum `manual | ocr | re_translate | style_profile`. `scope_type` in Decision Event = enum `segment | page | block | account | project`. EXPORT_EVENT table created, not yet populated. ✗ No common "Events" schema with type discriminator. Dependencies: T-1.3.1.

**T-1.3.3 — Core-object schemas: Job, Checkpoint, concept ID/glossary entry, provenance table.** AP-1.3 | M-1 | Critical Path: Yes. Provenance table has `scope_type` + `scope_uuid`, **no `satz_uuid` mandatory field**. Checkpoint has `resume_state` JSONB. ✗ No `satz_uuid NOT NULL` in the provenance table. Dependencies: T-1.3.2. Risk: provenance table created with `satz_uuid NOT NULL` — breaks scope model for page-scoped and project-scoped POs.

**T-1.4.1 — REVISION service: create_revision.** AP-1.4 | M-1 | Critical Path: Yes. `create_revision(satz_uuid, before, after, source)`. Revisions-UUID only on actual text change. Invariants: H-4. Tests: T-H4-01.

**T-1.4.2 — REVISION service: create_decision_event.** AP-1.4 | M-1 | Critical Path: Yes. `create_decision_event(scope_type, scope_uuid, decision_type, content)`. Accepts all `scope_type` values. No text-revision field in Decision Event. Tests: T-H4-02.

**T-1.5.1 — EVENTING service: log_event.** AP-1.5 | M-1 | Critical Path: No. Writes exclusively to log-entry table. Log ID is UUID, not autoincrement integer. ✗ No writes to Revision/Decision-Event tables.

**T-1.6.1 — PROVENANCE core: create_po.** AP-1.6 | M-1 | Critical Path: Yes (Step 5). `create_po(po_type, scope_type, scope_uuid, payload)`. PO immutable after creation. Accepts `scope_type = page / project / artefact`. ✗ No `satz_uuid` mandatory field in the PO table. Dependencies: T-1.3.3, T-1.4.2, T-1.5.1.

### WS-2: Job infrastructure

**T-2.1.1 — Job state machine.** AP-2.1 | M-1 | Critical Path: Yes (Step 6). Transitions: `pending → aktiv → deferred → pausiert → teilweise_fehlgeschlagen → abgeschlossen | fehlgeschlagen | bereinigt`. Deferred → auto-retry. Failed → no auto-retry. `job_uuid` preserved on resume. Tests: T-REC-05.

**T-2.1.2 — Checkpoint write and read.** AP-2.1 | M-1 | Critical Path: Yes. Resume from last checkpoint, not from job start. `resume_state` JSONB. Tests: T-REC-01, T-REC-02. Dependencies: T-2.1.1.

### WS-3: Upload pipeline

**T-3.1.1 — Chunked upload: chunk reception, hash check, page materialization.** AP-3.1 | M-2. Upload job created, chunk checkpoints, Page objects for all pages materialized at upload start (each page receives a `page_uuid`). On page replacement: existing `page_uuid`s preserved. `ocr_status = ausstehend` on creation. ✗ UPLOAD writes no POs. Dependencies: T-2.1.2, T-1.3.1.

**T-3.1.2 — Chunked upload: resume and SCAN-PO creation.** AP-3.1 | M-2. Resume from chunk N+1. After completion: PROVENANCE core creates SCAN PO (`scope_type = page`). ✗ UPLOAD writes no POs itself. Tests: T-REC-01.

### WS-4: OCR pipeline

**T-4.1.1 — OCR job: page processing and Block/Segment creation.** AP-4.1 | M-2 | Critical Path: Yes (Step 7). Block- and Satz-UUIDs per page. Checkpoint after each page. ✗ No lock-flag setting. Tests: T-REC-02.

**T-4.1.2 — OCR job: OCR-PO creation and Revisions-UUID on text change.** AP-4.1 | M-2 | Critical Path: Yes. OCR-PO via PROVENANCE core. Revisions-UUID only when OCR text ≠ previous text. Invariants: H-4. Tests: T-H4-01.

**T-4.1.3 — OCR error class profiling (F-01 through F-09).** AP-4.1 | M-2 | Critical Path: Yes. Severity configurable, not hard-coded. `ocr_error_instance` with `resolved = false`. Risk: hard-coded severities prevent calibration.

**T-4.2.1 — Lineage: 1→1 matching and inactivation (1→0).** AP-4.2 | M-2 | Critical Path: No. LINEAGE_EVENT-PO with `automatisch: true`. No Decision-Event-UUID for automatic processes. Invariants: H-5. Tests: T-H5-01, T-H5-02.

**T-4.2.2 — Lineage: split (1→n), merge (n→1), reactivation.** AP-4.2 | M-2 | Critical Path: No. `herkunft_uuid[]` + `ziel_uuid[]`. Reactivation of inactive UUIDs before new creation. Tests: T-H5-01.

**T-4.3.1 — OCR review status: Go/No-Go computation per page.** AP-4.3 | M-2 | Critical Path: Yes (gate for AP-6.1). Transitions: `ausstehend → in_review → go | go_with_warning | no_go`. Aggregation threshold configurable. ✗ No automatic setting of go on no_go.

### WS-5: Protection and decision layer

**T-5.1.1 — LOCK: set and lift lock flag.** AP-5.1 | M-3 | Critical Path: Yes (joint gate). `set_lock(satz_uuid, level)`, `release_lock(satz_uuid)`. Lifting Lock Level 2 requires confirmation-dialog context. MANUAL_*-PO. Invariants: H-1, H-2.

**T-5.1.2 — LOCK: conflict detection and persistent conflict instance.** AP-5.1 | M-3 | Critical Path: Yes. `conflict_instance` (`conflict_uuid`, `satz_uuid` FK, `rule_source`, `conflict_type` enum, `state` enum {`offen | aufgelöst`}, `resolution_type` enum?, `decision_event_uuid?` FK, `detected_at`, `resolved_at?`). state `offen` remains without explicit user action. Three resolution options. ✗ No automatic winner. Invariants: H-6. Tests: T-H2-01, T-H2-02, T-H6-01. Risk: conflict only in-memory — open conflicts lost after server restart.

**T-5.2.1 — GLOSSARY: manage concept IDs and registry entries.** AP-5.2 | M-3 | Critical Path: Yes. Entry change generates Decision-Event-UUID. Tests: T-KE-01.

### WS-6: Release gate

**T-6.1.1 — Release-gate logic.** AP-6.1 | M-3 | Critical Path: Yes (Step 9). Transitions: `nicht_erreichbar → freigabeschranken_prüfung → übersetzungsreif | übersetzbar_mit_warnung | blockiert`. F-06-QR without resolution → blocked. ✗ No automatic translation start. Dependencies: T-4.3.1, T-5.1.2, T-5.2.1.

### WS-7: Translation pipeline

**T-7.1.1 — TRANSLATE: translation job with checkpoint and lock-flag check.** AP-7.1 | M-4 | Critical Path: Yes (Step 10). Checkpoint after each chunk, context buffer in `resume_state`. Segment with active `lock_flag` → skipped. Tests: T-H1-01, T-H1-02, T-REC-03.

**T-7.1.2 — TRANSLATE: TRANSLATION-PO and Revisions-UUID on text change.** AP-7.1 | M-4 | Critical Path: Yes. Resume with diverging result → new Revisions-UUID, no silent overwrite. Tests: T-REC-04.

**T-7.2.1 — RULE_BINDING: glossary binding in translation pipeline.** AP-7.2 | M-4 | Critical Path: No. Conflict with lock flag → `conflict_instance` state `offen`. Invariants: H-2, H-6. Tests: T-H2-01, T-KE-01.

**T-7.3.1 — Promotion pipeline: observation and pattern candidate (Stages 1–2).** AP-7.3 | M-4 | Critical Path: No. Manual correction as local observation. Pattern candidate detected → only offered to user, not applied. Invariants: H-7.

**T-7.3.2 — Promotion pipeline: confirmation as style rule (Stage 3).** AP-7.3 | M-4 | Critical Path: No. Confirmation generates Decision-Event-UUID. ✗ No automatic promote. Tests: T-H7-01.

### WS-8: Audit and consistency

**T-8.1.1 — AUDIT: findings table and audit-run logic.** AP-8.1 | M-5 | Critical Path: No. Findings table: `satz_uuid` FK, `regelkennung`, `verstossklasse`, `schweregrad`, `auflösungsstatus`. ✗ No Revisions-UUID through audit run. ✗ No automatic correction. Tests: T-H4-02.

**T-8.1.2 — AUDIT: rule check A-01 through D-03.** AP-8.1 | M-5. C-01 → Critical → blocking; A-01 → High → mandatory notice; D-01 → Medium → notice (export possible). ✗ No automatic acknowledgment.

**T-8.2.1 — CONSISTENCY: K-01 through K-07 as identity-/reference-based consistency check.** AP-8.2 | M-5 | Critical Path: No. `subject_type` enum: `concept_id` (K-01, K-07), `formel_verzeichnis_id` (K-02), `entity_id` (K-03), `transliterations_muster` (K-04), `source_identity` (K-05), `structural_key` (K-06). Consistency violations → PREFLIGHT (W-02 for consistency warnings; P-03 if simultaneously Critical class §4.6). Tests: T-KA-01, T-KA-02 indirectly. Risk: K-01 on string equality instead of concept ID; K-02–K-06 generalized blanket-style to concept ID.

### WS-9: Preflight and export

**T-9.1.1 — PREFLIGHT: required-question confirmation of the configuration layer, P-03 and P-04, export-run event.** AP-9.1 | M-5 | Critical Path: Yes (Step 11). Required questions occupy no P slot. Export-run event (log ID via EVENTING) always, even on blocked export. ✗ No export without active confirmation of all four required questions.

**T-9.1.2 — PREFLIGHT: occupied W gates and `exportierbar_mit_warnungen`.** AP-9.1 | M-5 | Critical Path: Yes. W-01 (Medium audit), W-02 (K-01–K-07), W-03 (gradual document-style deviations). W-04…W-08 + P-01/P-02/P-05/P-06 open, not substantively occupied. Critical-class consistency violation §4.6 → P-03 (not W-02). Hadith verification status group: H-1 warning-based (`go_with_warning`), H-2 stays blocking. ✗ No mandatory notice run as general warning.

**T-9.2.1 — EXPORT: artifact creation and EXPORT_EVENT.** AP-9.2 | M-5 | Critical Path: Yes (Step 12). EXPORT_EVENT only on success, atomic. Export-run event (log ID) always. `revision_snapshot[]` + `active_decision_event_uuids[]` correctly populated. EXPORT_EVENT immutable after creation. ✗ No EXPORT_EVENT on failure or blocking. Risk: EXPORT_EVENT before artifact completion as progress marker.

### WS-10: Provenance evaluation and history

**T-10.1.1 — PROVENANCE evaluation: get_pos_for_segment and EXPORT_EVENT linkage.** AP-10.1 | M-6 | Critical Path: No. `get_pos_for_segment(satz_uuid)` only segment-scoped POs. `get_export_events_for_segment(satz_uuid)` via `revision_snapshot[]` lookup, not via direct segment FK. ✗ No direct segment FK in EXPORT_EVENT.

**T-10.1.2 — PROVENANCE evaluation: get_page_history and get_project_history.** AP-10.1 | M-6. Page and project history. ✗ No segment-scoped events in page history.

**T-10.2.1 — History scope separation: backend endpoints.** AP-10.2 | M-6. Four scope-separated backend endpoints: segment history, page history, project history, event log. ✗ Log IDs do not appear in segment/page history. ✗ No own logic in the UI.

## DELIVERY ORDER

- **Step 1 (Foundation):** T-1.1.1 → T-1.1.2 → T-1.2.1 → T-1.2.2 → T-1.3.1 → T-1.3.2 → T-1.3.3 → T-1.4.1 → T-1.4.2 ║ T-1.5.1 → T-1.6.1.
- **Step 2 (Job):** T-2.1.1 → T-2.1.2.
- **Step 3 (Upload):** T-3.1.1 → T-3.1.2.
- **Step 4 (OCR):** T-4.1.1 → T-4.1.2 → T-4.1.3; T-4.2.1 (║ after T-4.1.1) → T-4.2.2; T-4.3.1 (after T-4.1.3).
- **Step 5 (Protection — joint gate):** T-5.1.1 ║ T-5.2.1 (║ after T-4.3.1); T-5.1.2 (after T-5.1.1).
- **Step 6 (Release gate):** T-6.1.1 (after T-5.1.2 AND T-5.2.1).
- **Step 7 (Translation):** T-7.1.1 → T-7.1.2; T-7.2.1 (║ after T-7.1.1); T-7.3.1 → T-7.3.2 (║ to T-7.2.1).
- **Step 8 (Audit + Consistency):** T-8.1.1 → T-8.1.2; T-8.2.1 (║ after T-8.1.1 schema).
- **Step 9 (Preflight + Export):** T-9.1.1 → T-9.1.2 → T-9.2.1.
- **Step 10 (Provenance evaluation):** T-10.1.1 → T-10.1.2 → T-10.2.1.

**Hard gate tickets:** T-1.2.2 → Step 2; T-4.3.1 → Step 5; T-5.1.2 + T-5.2.1 → T-6.1.1; T-6.1.1 → Step 7; T-9.1.1 → T-9.2.1.

## MINIMAL FIRST DELIVERY CUT

Tickets: T-1.1.1, T-1.1.2, T-1.2.1, T-1.2.2, T-1.3.1, T-1.3.2, T-1.3.3, T-1.4.1, T-1.4.2, T-1.5.1, T-1.6.1, T-2.1.1, T-2.1.2, T-3.1.1, T-3.1.2, T-4.1.1, T-4.1.2, T-4.1.3.

**End-to-end demonstrably working:** file upload with resume guarantee; OCR run with checkpoint recovery; Block/Satz UUIDs immutable; SCAN-PO and OCR-PO via PROVENANCE core; F-01…F-09 detected and persisted; INVARIANT guard demonstrably blocks all H-1…H-7 violations; Revisions-UUID/Decision-Event-UUID/log-ID correctly separated.

**Deliberately still missing:** WS-5/WS-6/WS-7/WS-8/WS-9/WS-10.

**Core risks in the first cut:** all T-H tests green; T-REC-01 + T-REC-02 green; no `satz_uuid` mandatory field in provenance table.

## A. HARD DELIVERY GATES

These tickets must never be skipped or provisionally bypassed:

| Ticket | Why unavoidable |
|---|---|
| T-1.2.1 + T-1.2.2 (INVARIANT guard) | Without guard every later ticket may inadvertently introduce baseline violations. |
| T-1.3.3 (provenance schema) | `scope_type` + `scope_uuid` must exist before first PROVENANCE write. |
| T-1.6.1 (PROVENANCE core) | All modules from WS-3 onward write POs. |
| T-2.1.2 (checkpoint) | Without checkpoint persistence no recovery guarantee. |
| T-5.1.2 (`conflict_instance` persistent) | Without persistent entries open conflicts are lost on server restart. |
| T-6.1.1 (release gate) | Without release gate translation can start without OCR review. |
| T-9.1.1 (required questions + P-03/P-04) | Without active confirmation and resolution of critical violations export cannot proceed cleanly. |
| T-9.2.1 (EXPORT_EVENT atomic) | EXPORT_EVENT must never be partially written. |

## B. TYPICAL WRONG SHORTCUTS

1. INVARIANT guard as optional middleware.
2. Provenance table with `satz_uuid NOT NULL`.
3. Three identity types in a common Events table.
4. Write EXPORT_EVENT before artifact completion.
5. Trigger release gate automatically when all pages go.
6. Silently resolve conflict on "obviously correct" glossary entry.
7. Upload handler writes SCAN-PO directly.
8. Lineage matching generates Decision-Event-UUIDs.
9. Buffer checkpoints in memory instead of persisting atomically.
10. Check K-01 on string equality instead of concept ID.
11. Hold `conflict_instance` only in memory instead of persisting.

## STYLE-FEATURE BRANCH — BACKLOG LAYER (CR-3)

### 7.1 Structural anchoring of the five style-feature ticket families

- F1 — Object/schema foundation
- F2 — Promotion / style-rule development
- F3 — Audit / conflict / marker
- F4 — Display / provenance / tooltip
- F5 — Configuration / calibration

### 7.2 Delivery placement logic

- F1 fits into the identity/schema sprint area of the DBB and is a prerequisite for all further families.
- F2 and F4 follow F1 and are basically parallelizable.
- F3 follows F1 and the DBB audit layer.
- F5 is late, non-critical-path work.
- T-7.3.1 / T-7.3.2 remain in their existing DBB placement (AP-7.3 / M-4 / Critical Path: No) untouched.

### 7.3 Configuration layer (F5 contents)

- Persistence location of thresholds (open).
- Mutability (role question open).
- Runtime effect of threshold changes.
- Logging as `decision_event` with `decision_source = style_management`.

Values themselves to be marked as Group C with reference to Document 1 §4.14 closing sentence "calibration values are set after gold-corpus tests".

### 7.4 Cross-reference to T-7.3.1 / T-7.3.2

T-7.3.1 / T-7.3.2 stay in their existing DBB form. F2 takes them up without restructuring.

### 7.5 Marked open model question B.3 — granularity of learning source asymmetry §4.13 in F2

Open: whether five source classes (confirmed reference sentences, manual user rules, accepted/corrected/ignored AI suggestions) are implemented as one ticket or five sub-tickets in F2; whether learning source asymmetry is refined exclusively rule-related or additionally example-related/profile-version-related.

— End of version —