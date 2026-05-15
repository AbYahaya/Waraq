<!-- Authored: 2026-05-01. -->
<!-- Status: Authored to replace presumed-lost original v1.0 per option (c). -->
<!-- Anchored to: Baseline Delivery Plan v1.0 §2 (Sprint 0 scope description); Delivery Backlog Baseline v1.0 §11 (Minimaler erster Delivery-Cut, identical 18-ticket inventory); DBB v1.0 ticket definitions T-1.1.1 through T-4.1.3; Engineering Execution Baseline v1.0 (DoD); Core Architecture Baseline v1.0 (H-1…H-7, scope_type, F-01…F-09). -->
<!-- Replaces: any presumed-lost prior "Waraq Sprint-0 / Foundation Delivery Plan v1.0" referenced in Dokument 2 §1 and Baseline Delivery Plan §1. -->
<!-- Structural template: ocr_text_export_v1_3.md §5 Sprint Plan Sprint-OCR v1.3. -->

# Waraq Sprint-0 / Foundation Delivery Plan v1.0

Status: Working basis. No coding release. No silent re-baselining.

## Start condition

Project repository skeleton scaffolded. CI baseline operational. Engineering Execution Baseline v1.0 DoD adopted. Core Architecture Baseline v1.0, Implementation Translation Baseline v1.0, Engineering Execution Baseline v1.0, and Delivery Backlog Baseline v1.0 present in `/docs/canon/`. No prior sprint expected (Sprint 0 is the first operative sprint).

## 1. Scope

| Ticket | Designation |
|---|---|
| T-1.1.1 | UUID issuance service (`new_uuid()`) |
| T-1.1.2 | UUID immutability and inactivation logic (`assert_immutable`, `mark_inactive`) |
| T-1.2.1 | INVARIANT-Guard: lock-flag protection (H-1, H-2) |
| T-1.2.2 | INVARIANT-Guard: revision-UUID, UUID, conflict, promotion protections (H-4, H-5, H-6, H-7) |
| T-1.3.1 | Core-object schemas: Project, Page, Block, Segment |
| T-1.3.2 | Core-object schemas: Revision, Decision Event, Log-Eintrag, EXPORT_EVENT |
| T-1.3.3 | Core-object schemas: Job, Checkpoint, Konzept-ID, Provenance |
| T-1.4.1 | REVISION service: `create_revision` |
| T-1.4.2 | REVISION service: `create_decision_event` |
| T-1.5.1 | EVENTING service: `log_event` |
| T-1.6.1 | PROVENANCE-Kern: `create_po` |
| T-2.1.1 | Job state machine |
| T-2.1.2 | Checkpoint write/read |
| T-3.1.1 | Chunked upload: chunk receipt, hash check, page materialization |
| T-3.1.2 | Chunked upload: resumption and SCAN-PO creation |
| T-4.1.1 | OCR job: page processing and Block/Segment creation |
| T-4.1.2 | OCR job: OCR-PO creation and revision-UUID on text change |
| T-4.1.3 | OCR error-class profiling (F-01 through F-09) |

Deliberately not in this sprint: lineage 1→1/1→0/1→n/n→1 (T-4.2.x — Sprint 1), OCR review status Go/No-Go (T-4.3.1 — Sprint 1), lock-flag management and `conflict_instance` persistence (WS-5 — Sprint 1), glossary service (T-5.2.1 — Sprint 1), release gate (T-6.1.1 — Sprint 2), translation pipeline (WS-7 — Sprint 2/3), audit (WS-8 — Sprint 3), consistency (T-8.2.1 — Sprint 4), preflight (WS-9 — Sprint 4/5), export artefact (T-9.2.1 — Sprint 5), provenance readout (WS-10 — Sprint 6). No UI for any module. No calibration values.

## 2. Sprint target state

**T-1.1.1 — UUID issuance service**
- `new_uuid()` produces a fresh, collision-free UUID on every call.
- Two consecutive calls always produce different UUIDs.
- No own persistence layer.
- No validation of foreign UUIDs.

**T-1.1.2 — UUID immutability and inactivation**
- `assert_immutable(uuid)` raises an error on any attempt to change an issued UUID.
- `mark_inactive(uuid)` sets `active = false`, never deletes.
- No UUID is ever deleted or recycled.
- The `active`-flag convention is consumed by Page, Block, Segment, Job tables; UUID columns are NOT NULL across the schema.

**T-1.2.1 — INVARIANT-Guard: lock-flag protection (H-1, H-2)**
- Automatic write attempt on a Segment with `lock_flag = manual_local` → blocked.
- Automatic write attempt on a Segment with `lock_flag = manual_editorial` → blocked.
- Manual write with explicit confirmation context → permitted.
- Guard is not deactivatable. No middleware switch. No configuration flag. No test override.

**T-1.2.2 — INVARIANT-Guard: H-4, H-5, H-6, H-7**
- Attempt to write a revision-UUID for a check-only operation → blocked (H-4).
- Attempt to mutate an issued UUID → blocked (H-5).
- Terminology application against a locked Segment → conflict reported, never silently resolved (H-6).
- Automatic style-rule derivation without the promotion pipeline → blocked (H-7).
- Guard is not deactivatable.

**T-1.3.1 — Project, Page, Block, Segment schemas**
- Tables created with correct foreign keys.
- `project_uuid` is the primary key of the Project table, NOT NULL.
- `lock_flag` enum on Segment: `none | manual_local | manual_editorial`.
- Decision-Event schema accepts `scope_type = project` with a valid `project_uuid`.
- `Page.ocr_status` enum present (values populated in T-4.1.x).
- No application logic written in this ticket.

**T-1.3.2 — Revision, Decision Event, Log-Eintrag, EXPORT_EVENT schemas**
- Three separate tables for the three identity types — no shared "events" table.
- `change_source` enum on Revision: `manual | ocr | re_translate | style_profile`.
- `scope_type` enum on Decision Event: `segment | page | block | account | project`.
- EXPORT_EVENT table created with `revision_snapshot[]`, `active_decision_event_uuids[]`, `export_config`, `artefact_ref` — table not yet populated this sprint (population in Sprint 5, T-9.2.1).

**T-1.3.3 — Job, Checkpoint, Konzept-ID, Provenance schemas**
- Job schema with all fields per ITB 3.1/3.2/3.5 (state enum, retry_budget, retry_count, parent_job_uuid, started_at, updated_at, terminal_at).
- Checkpoint schema with `resume_state` JSONB.
- Provenance table with `scope_type` + `scope_uuid` and **no** `satz_uuid` NOT NULL constraint.
- Konzept-ID with `display_forms[]`, `translation`, `entry_type`, `binding_level`.

**T-1.4.1 — `create_revision`**
- `create_revision(satz_uuid, before, after, source)` — identical before/after produces no entry, no error.
- Differing after → revision-UUID created.
- `change_source` is a mandatory field.
- No revision-UUID for pure check operations (H-4 enforced).

**T-1.4.2 — `create_decision_event`**
- Decision-event-UUID issued for `scope_type = segment | page | block | account | project`.
- No text-revision field on Decision Event.
- No decision-event-UUID for text revisions (H-4 enforced).

**T-1.5.1 — `log_event`**
- Writes exclusively to the Log-Eintrag table.
- Log-ID is a UUID (no autoincrement integer).
- No writes to Revision or Decision-Event tables.

**T-1.6.1 — PROVENANCE-Kern `create_po`**
- PO created with correct `po_type`, `scope_type`, `scope_uuid`.
- After creation, PO is unchangeable: any update attempt raises an error.
- `scope_type = page` accepted; `scope_type = project` accepted; `scope_type = artefact` accepted.
- No `satz_uuid` mandatory parameter.

**T-2.1.1 — Job state machine**
- All transitions per ITB 3.1/3.2/3.5: `pending → aktiv → deferred → pausiert → teilweise_fehlgeschlagen → abgeschlossen | fehlgeschlagen | bereinigt`.
- `deferred` triggers auto-retry until `retry_budget` is exhausted, then → `fehlgeschlagen`.
- `fehlgeschlagen` does **not** trigger auto-retry.
- `job_uuid` is invariant under resumption.
- No forced restart from job beginning.

**T-2.1.2 — Checkpoint write/read**
- After interruption, resumption picks up at the last checkpoint, not at job start.
- `resume_state` JSONB is correctly serialized and deserialized.
- Multiple checkpoints for the same job: last one is consumed.
- No restart from null.

**T-3.1.1 — Chunked upload: receipt, hash, page materialization**
- Each chunk persisted to Checkpoint after hash confirmation.
- Failed-hash chunk is rejected; the upload job stays in `aktiv`.
- Page objects are materialized **before** chunks are processed, drawn from the document's structural metadata (PDF page count or ordered scan-file list). Each page receives a `page_uuid` via the IDENTITY service. `ocr_status = ausstehend` on creation.
- On re-upload of the same file (page replacement): existing `page_uuid`s are preserved (per the Sprint 1 lineage logic to come — preservation rule is in scope here, lineage matching is not).
- UPLOAD writes no POs in this ticket.

**T-3.1.2 — Resumption and SCAN-PO**
- Resumption begins at chunk N+1, never chunk 1.
- After full upload completion: SCAN-PO created via PROVENANCE-Kern with `po_type = SCAN`, `scope_type = page`, `scope_uuid = page_uuid`, payload = upload metadata.
- UPLOAD does not write POs directly.

**T-4.1.1 — OCR job: per-page processing**
- OCR runs per page; Block-UUIDs and Segment (Satz)-UUIDs created for every page.
- Checkpoint persists after each page.
- No lock-flag setting in this ticket.
- No automatic translation start after OCR completion.

**T-4.1.2 — OCR-PO and revision-UUID on text change**
- OCR-PO created after each pass via PROVENANCE-Kern: `po_type = OCR`, `scope_type = segment`, `scope_uuid = satz_uuid`, payload contains engine, confidence, error-class list.
- Revision-UUID issued only when OCR text differs from prior text on that segment.
- No OCR-PO for pure check passes with no text output.
- No revision-UUID for check-only OCR runs (H-4 enforced).

**T-4.1.3 — OCR error-class profiling F-01 through F-09**
- All nine error classes (F-01 through F-09) detected.
- Severity (`kritisch | hoch | mittel`) correctly assigned.
- `ocr_error_instance` rows created with `resolved = false`.
- Severity assignment reads from a configurable table — never hard-coded.
- No automatic resolution of error classes.

## 3. Ticket sequence

Sprint-internal sequencing per DBB §10 Delivery-Reihenfolge, Schritte 1–4:

```
T-1.1.1 ─→ T-1.1.2 ─→ T-1.2.1 ─→ T-1.2.2
                                    │
                                    v
                                  T-1.3.1 ─→ T-1.3.2 ─→ T-1.3.3
                                                            │
                                                            v
                                                          T-1.4.1 ─→ T-1.4.2
                                                                       │
                                                                       v
                                       T-1.5.1 ║ (parallel to T-1.4.x after T-1.3.2)
                                                                       │
                                                                       v
                                                          T-1.6.1 (after T-1.4.2 ∧ T-1.5.1)
                                                                       │
                                                                       v
                                                          T-2.1.1 ─→ T-2.1.2
                                                                       │
                                                                       v
                                                          T-3.1.1 ─→ T-3.1.2
                                                                       │
                                                                       v
                                                          T-4.1.1 ─→ T-4.1.2 ─→ T-4.1.3
```

Parallel windows: T-1.5.1 may run parallel to T-1.4.x once T-1.3.2 schema is in. No other parallel paths inside Sprint 0.

## 4. Mandatory tests

| Test ID | Ticket | Check content | Setup note |
|---|---|---|---|
| T-H5-01 | T-1.1.1, T-1.1.2, T-4.2.x (regression) | UUID immutability under all mutation attempts | Issue UUID, attempt update → error |
| T-H5-02 | T-1.1.2 | Inactivation does not delete: `active = false` after `mark_inactive`; record still queryable | – |
| T-H1-01 | T-1.2.1 | Automatic write on `lock_flag = manual_local` → blocked | Pre-set lock_flag; attempt automatic update |
| T-H1-02 | T-1.2.1 | Automatic write on `lock_flag = manual_editorial` → blocked | Pre-set lock_flag; attempt automatic update |
| T-H2-01 | T-1.2.2, T-5.1.2 (regression-ready) | Terminology application against a locked Segment → conflict reported, not resolved | Pre-set lock_flag + terminology rule |
| T-H2-02 | T-1.2.2 | No silent resolution path exists from H-2 conflict to applied state | Code-review evidence + integration test |
| T-H4-01 | T-1.2.2, T-1.4.1, T-4.1.2 | No revision-UUID for pure check operations (OCR check pass, audit lookup, etc.) | Run OCR check pass; assert revisions table delta = 0 |
| T-H4-02 | T-1.2.2, T-1.4.2 | No decision-event-UUID for text revisions; the two are strictly separate | Insert text revision; assert decision_event delta = 0 |
| T-H6-01 | T-1.2.2 | Conflict between rule and lock_flag never silently resolved by Guard | Attempt automatic resolution via internal API → error |
| T-H7-01 | T-1.2.2 | Automatic style-rule derivation without promotion-pipeline confirmation → blocked | Attempt automatic promotion → error |
| Schema-Tabellen-Test | T-1.3.1 | All four tables (Project, Page, Block, Segment) created with correct FKs and enums; `project_uuid` NOT NULL | DB introspection |
| Drei-Identitätstypen-Test | T-1.3.2 | Revision, Decision Event, Log-Eintrag are three separate tables — no shared events table with type discriminator | DB introspection |
| Provenance-Schema-Test | T-1.3.3 | Provenance table has `scope_type` + `scope_uuid`; `satz_uuid` NOT NULL constraint absent | DB introspection |
| Trennungs-Test | T-1.5.1 | `log_event` writes only to Log-Eintrag table; no rows appear in Revision or Decision-Event tables | Insert log; assert deltas |
| PO-Smoke-Test | T-1.6.1 | PO created via `create_po` is unchangeable; mutation attempt → error | Create PO; attempt update; assert error |
| PO-Scope-Page-Test | T-1.6.1 | `create_po(scope_type='page', ...)` accepted | – |
| PO-Scope-Project-Test | T-1.6.1 | `create_po(scope_type='project', ...)` accepted | – |
| T-REC-05 | T-2.1.1 | `fehlgeschlagen` state does not trigger auto-retry; `deferred` does | Force failure; assert no retry on fehlgeschlagen |
| T-REC-01 | T-2.1.2, T-3.1.2 | Resumption picks up at last checkpoint, not at job start | Interrupt mid-upload; resume; assert chunk N+1 received |
| T-REC-02 | T-2.1.2, T-4.1.1 | Resumption deserializes `resume_state` correctly across interruptions | Interrupt mid-OCR; resume; assert state continuity |
| Page-Materialisierung-Test | T-3.1.1 | Page objects created with `page_uuid` before any chunk is processed; on re-upload, existing `page_uuid`s preserved | Upload + re-upload; assert UUID stability |
| Hash-Mismatch-Test | T-3.1.1 | Failed hash → chunk rejected, job stays `aktiv` | Submit malformed chunk |
| SCAN-PO-Provenance-Test | T-3.1.2 | SCAN-PO created via PROVENANCE-Kern after upload completion, not directly by UPLOAD; `scope_type = page` | Code-review + integration test |
| OCR-Block-Segment-Anlage-Test | T-4.1.1 | Block-UUIDs and Segment-UUIDs correctly created for every page; checkpoint after each page persists | Upload N-page document; assert N pages × M blocks |
| OCR-PO-Anlage-Test | T-4.1.2 | OCR-PO created after each pass; payload contains engine, confidence, error-class list | – |
| OCR-Pruefung-Keine-Revision-Test | T-4.1.2 | OCR check-only pass produces no revision-UUID | Run pass with text identical to prior; assert revisions delta = 0 |
| F-Klassen-Vollständigkeits-Test | T-4.1.3 | All nine error classes F-01 through F-09 detectable; severity correctly assigned | Synthetic test pages designed to trigger each F-class |
| F-Klassen-Konfigurations-Test | T-4.1.3 | Severity assignment reads from configuration table, not hard-coded | Code review + change severity in config; assert effect |

Invariants in scope this sprint: H-1, H-2, H-4, H-5, H-6, H-7. (H-3 is OCR-export-specific and is exercised in Sprint-OCR per `ocr_text_export_v1_3.md`; not in this sprint.)

New regressions from this sprint onward (these states must never reappear in any later sprint):

- Guard is deactivatable in any environment, including tests.
- Revision, Decision Event, Log-Eintrag merged into a shared events table.
- Provenance table has `satz_uuid` NOT NULL.
- UUID is recycled or deleted instead of inactivated.
- EXPORT_EVENT created before atomic artefact completion (table exists from this sprint; population is later, but the schema must support atomic-only insertion).
- OCR check-only pass writes a revision-UUID.
- F-class severity hard-coded.

## 5. Definition of Done

Code:

- T-1.1.1 through T-4.1.3 implemented, reviewed, and merged.
- Engineering Execution Baseline v1.0 DoD satisfied for every ticket: code, tests, persistence, logs, Guard-behaviour, scope-correctness, non-goals respected, regressions green.
- No open review comment describing a baseline violation.

UUID layer:

- T-H5-01 green.
- T-H5-02 green.

INVARIANT-Guard:

- T-H1-01 green.
- T-H1-02 green.
- T-H2-01 green.
- T-H2-02 green (code review + integration evidence).
- T-H4-01 green.
- T-H4-02 green.
- T-H6-01 green.
- T-H7-01 green.

Schemas:

- Schema-Tabellen-Test green.
- Drei-Identitätstypen-Test green.
- Provenance-Schema-Test green.

Services:

- Trennungs-Test green.
- PO-Smoke-Test green.
- PO-Scope-Page-Test green.
- PO-Scope-Project-Test green.

Job and recovery:

- T-REC-05 green.
- T-REC-01 green.
- T-REC-02 green.

Upload and OCR:

- Page-Materialisierung-Test green.
- Hash-Mismatch-Test green.
- SCAN-PO-Provenance-Test green.
- OCR-Block-Segment-Anlage-Test green.
- OCR-PO-Anlage-Test green.
- OCR-Pruefung-Keine-Revision-Test green.
- F-Klassen-Vollständigkeits-Test green.
- F-Klassen-Konfigurations-Test green.

End-to-end demonstrable at sprint end:

- File upload with resumption guarantee.
- OCR run with checkpoint recovery.
- Block-UUIDs and Segment-UUIDs correctly created and immutable.
- SCAN-PO and OCR-PO correctly created via PROVENANCE-Kern.
- Error classes F-01 through F-09 detected and persisted as `ocr_error_instance`.
- INVARIANT-Guard demonstrably blocks all H-1 through H-7 violations.
- Revisions-UUID, Decision-Event-UUID, and Log-ID kept strictly separate.

## 6. Risks

R-S0-01 — INVARIANT-Guard implemented as an optional middleware layer. Probability: high. Consequence: Guard is deactivated under time pressure or in test environments and forgotten; H-1 through H-7 violations propagate into later sprints undetected. Review obligation: code review confirms Guard has no configuration switch, no environment override, no test override; T-H1-01, T-H1-02, T-H2-01, T-H2-02 must run in every CI environment, not only local.

R-S0-02 — Provenance table created with `satz_uuid` NOT NULL. Probability: medium. Consequence: page-scoped POs (SCAN-PO from T-3.1.2) and project-scoped POs (later sprints) cannot be created. Migration after the fact breaks all already-written POs. Review obligation: Provenance-Schema-Test green; code review confirms the constraint is absent.

R-S0-03 — Three identity types collapsed into a shared "events" table with type discriminator. Probability: medium. Consequence: H-4 enforcement becomes structurally impossible — every check pass "could" be a text revision. Review obligation: Drei-Identitätstypen-Test green; code review confirms three separate tables.

R-S0-04 — UUID recycled or deleted instead of inactivated. Probability: medium. Consequence: revision history breaks; lineage logic in Sprint 1 cannot reactivate inactive UUIDs. Review obligation: T-H5-01, T-H5-02 green; code review confirms `mark_inactive` is the only deactivation pathway.

R-S0-05 — Checkpoint buffered in memory rather than atomically persisted. Probability: medium. Consequence: crash between writes loses progress; T-REC-01 and T-REC-02 cannot pass deterministically. Review obligation: T-REC-01 green under simulated mid-write crash; code review confirms atomic persistence.

R-S0-06 — Page objects created after upload completion rather than at upload start. Probability: medium. Consequence: T-3.1.2 SCAN-PO creation and T-4.1.1 OCR start fail because `page_uuid`s do not yet exist. Review obligation: Page-Materialisierung-Test green; integration test confirms page materialization precedes first chunk processing.

R-S0-07 — UPLOAD writes SCAN-PO directly instead of delegating to PROVENANCE-Kern after job-completion event. Probability: medium. Consequence: SCAN-PO can be created without a successfully completed upload. Review obligation: SCAN-PO-Provenance-Test green; code review confirms PROVENANCE-Kern is the sole writer.

R-S0-08 — OCR check-only pass writes a revision-UUID "for documentation". Probability: high. Consequence: H-4 violation; revisions table polluted with non-text-change entries; downstream regression-test surface contaminated. Review obligation: OCR-Pruefung-Keine-Revision-Test green; T-H4-01 green.

R-S0-09 — F-class severity hard-coded. Probability: high. Consequence: later calibration impossible without code change; Sprint 4 (T-4.3.1 OCR review status, T-8.2.1 consistency engine) inherits inflexibility. Review obligation: F-Klassen-Konfigurations-Test green; code review confirms severity table is configurable.

R-S0-10 — Job state `fehlgeschlagen` receives auto-retry "because deferred works that way". Probability: medium. Consequence: failed jobs auto-retry indefinitely; resource exhaustion; recovery semantics break. Review obligation: T-REC-05 green; code review confirms `fehlgeschlagen` has no retry path.

## 7. Transition to Sprint 1

Sprint 1 (OCR Review + Lock + Glossary) presupposes:

- T-4.1.1 green: Sprint 1's T-4.2.1 lineage matching consumes Block-UUIDs and Segment-UUIDs created here.
- T-4.1.3 green: Sprint 1's T-4.3.1 OCR review status consumes `ocr_error_instance` rows.
- T-1.6.1 green: Sprint 1's T-5.1.1 MANUAL_-PO and T-5.1.2 conflict-instance creation depend on PROVENANCE-Kern.
- T-1.4.2 green: Sprint 1's lock-flag setting and conflict resolution write decision-event-UUIDs via this service.

Sprint 1 may begin only after every Sprint 0 mandatory test in §4 is green.

## A. Hard Gates

HG-S0-1 — T-1.2.2 must be merged before any subsequent Sprint 0 ticket is started. The Guard must be live for every later schema and service write. No Sprint 0 ticket merges until T-H1-01, T-H1-02, T-H2-01, T-H2-02, T-H4-01, T-H4-02, T-H5-01, T-H5-02, T-H6-01, T-H7-01 are all green.

HG-S0-2 — T-1.3.3 (Provenance schema) must be merged before T-1.6.1 (PROVENANCE-Kern). Provenance-Schema-Test green is a precondition for any PO write.

HG-S0-3 — T-1.6.1 PO-Smoke-Test, PO-Scope-Page-Test, and PO-Scope-Project-Test must be green before T-3.1.2 (which is the first ticket in Sprint 0 to actually invoke `create_po`).

HG-S0-4 — T-2.1.2 Checkpoint Test (T-REC-01, T-REC-02) must be green before T-3.1.1 starts. Without checkpoint persistence, upload resumption is untestable.

HG-S0-5 — T-4.1.2 OCR-PO-Anlage-Test and OCR-Pruefung-Keine-Revision-Test must be green before T-4.1.3. Without them, the F-class persistence path through OCR-PO payload cannot be relied upon.

HG-S0-6 — Engineering Execution Baseline v1.0 DoD must be satisfied for every ticket — including the "Stilfeature-Test-Familien (CR-3)" row, which is non-applicable in Sprint 0 (no F2 or F3 tickets present) and therefore vacuously satisfied. Any later sprint that introduces F2/F3 tickets must satisfy that row substantively.

## B. What deliberately does not belong in this sprint

- Lineage logic (1→1, 1→0, 1→n, n→1, reactivation) — T-4.2.1, T-4.2.2 (Sprint 1).
- OCR Review Go/No-Go status per page — T-4.3.1 (Sprint 1).
- Lock-flag setting/release and `conflict_instance` persistence — WS-5 (Sprint 1).
- Glossary lookup, Konzept-ID services — T-5.2.1 (Sprint 1).
- Release gate / Freigabeschranke — T-6.1.1 (Sprint 2).
- Translation pipeline, RULE_BINDING, promotion — WS-7 (Sprints 2–3).
- Audit and consistency — WS-8 (Sprints 3–4).
- Preflight and export — WS-9 (Sprints 4–5).
- Provenance readout, history endpoints — WS-10 (Sprint 6).
- Stilfeature backlog layer — F1 through F5 (deferred per Dokument C v1.1 §3 follow-on work; not bound to this sprint).
- UI for any module. UI is product expansion stage per Baseline Delivery Plan §4.
- Calibration values for F-class severity, aggregation thresholds, OCR confidence — all calibrated post-Gold-Corpus-Tests per Baseline Delivery Plan §4.
- E-5 / Schnittstelle 5 live test package — parked per Block 3 + Dokument 2 §3 Klasse 1.
- Real Shamela Ist-Aufnahme — parked per Block 3 + Dokument 2 §4.3.

*Waraq Sprint-0 / Foundation Delivery Plan v1.0 — End*