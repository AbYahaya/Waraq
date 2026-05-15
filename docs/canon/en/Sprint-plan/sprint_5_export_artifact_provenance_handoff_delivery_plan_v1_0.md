<!-- Authored: 2026-05-01. -->
<!-- Status: Authored to replace presumed-lost original v1.0 per option (c). -->
<!-- Anchored to: Baseline Delivery Plan v1.0 §2 (Sprint 5 scope description); DBB v1.0 §10 Delivery-Reihenfolge Schritt 9 (continuation); DBB v1.0 ticket definition T-9.2.1; DBB v1.0 §A Hard Delivery-Gates (T-9.2.1 EXPORT_EVENT-Atomarität as unverhandelbar); DBB v1.0 §B Abkürzung 4 (EXPORT_EVENT vor Artefakt-Abschluss); Engineering Execution Baseline v1.0 (DoD); Implementation Translation Baseline v1.0; Core Architecture Baseline v1.0; OCR Text Export Endfassung v1.3 §3 (the canonical query rule for active_decision_event_uuids[] — structurally analogous for EXPORT_EVENT). -->
<!-- Replaces: any presumed-lost prior "Waraq Sprint-5 / Export Artifact + Provenance Handoff Delivery Plan v1.0" referenced in Dokument 2 §1 and Baseline Delivery Plan §1. -->
<!-- Structural template: ocr_text_export_v1_3.md §5 Sprint Plan Sprint-OCR v1.3. -->

# Waraq Sprint-5 / Export Artifact + Provenance Handoff Delivery Plan v1.0

Status: Working basis. No coding release. No silent re-baselining.

## Start condition

Sprints 0–4 fully completed. All Sprint 0–4 mandatory tests green. Preflight machinery operational and reaches `exportierbar` or `exportierbar_mit_warnungen` on clean projects (T-9.1.1, T-9.1.2). Exportlauf-Ereignis log family established (T-9.1.1). PROVENANCE-Kern operational with `scope_type = artefact` accepted (T-1.6.1). EXPORT_EVENT table schema in place from Sprint 0 (T-1.3.2) but not yet populated. `revision_snapshot[]` and `active_decision_event_uuids[]` array fields ready to receive content. All consistency findings classifiable into W-02 or P-03 (T-8.2.1). Konsistenzgruppe-verbindlich Decision Events being produced on consistency resolution.

## 1. Scope

| Ticket | Designation |
|---|---|
| T-9.2.1 | EXPORT: Artefakterzeugung and EXPORT_EVENT atomic creation via PROVENANCE-Kern |

Single-ticket sprint by design. The atomicity discipline is load-bearing per DBB §A and DBB Abkürzung 4. Concentrating it in its own sprint isolates the structural risk from competing implementation pressure.

Deliberately not in this sprint: provenance readout (T-10.1.x — Sprint 6), history endpoints (T-10.2.1 — Sprint 6), Stilfeature backlog families (CR-3) — deferred per Dokument C v1.1 §3 follow-on work. No UI for any module. No calibration values. No additional export targets (Adobe InDesign / Affinity Publisher Export per Baseline Delivery Plan §4 are explicitly out of scope, both for this sprint and for v1.0 baseline overall).

## 2. Sprint target state

**T-9.2.1 — Artefakterzeugung and EXPORT_EVENT**

The export operation produces two outputs and one log signal:

1. The export artefact (the actual deliverable file, format determined by `export_config.export_type`).
2. The EXPORT_EVENT row, written to the Provenance table via `create_po` from PROVENANCE-Kern.
3. A Log-Eintrag (Exportlauf-Ereignis, log family established in Sprint 4 T-9.1.1).

The Log-Eintrag is produced for **every** export attempt — successful, failed, or blocked. The artefact and the EXPORT_EVENT are produced **only** when the artefact creation step has completed fully and successfully. The atomicity rule binds the EXPORT_EVENT to the completed artefact: there is no scenario in which an EXPORT_EVENT exists without its artefact, and no scenario in which the artefact exists without its EXPORT_EVENT.

### State machine and triggering

- Job type `export` consumes Sprint 0 T-2.1.1 state machine: `pending → aktiv → abgeschlossen | fehlgeschlagen`.
- Trigger: an explicit user action `export_starten` issued from preflight state `exportierbar` or `exportierbar_mit_warnungen`. The action creates a Decision Event with `scope_type = project`, `decision_type = exportstart`. (This Decision Event is **not** the same as the per-warning confirmations from T-9.1.2; those precede `export_starten` and exist whether or not the user proceeds to export.)
- Preflight state must be `exportierbar` or `exportierbar_mit_warnungen` at the moment of `export_starten`. The export job re-checks the state at job start. If the state has changed since the user's action (e.g., a new audit finding appeared), the job fails with reason `preflight_state_changed`, no artefact is produced, no EXPORT_EVENT is written, only the Log-Eintrag is recorded.
- No code path bypasses the preflight check. The export job cannot be invoked for a project in `blockiert` state.

### Artefact creation

- The artefact is produced from the project's translation state at the moment of job start (the `current_rev_uuid` of every active Segment in scope of the export, per `export_config.scope`).
- Artefact creation is a multi-step pipeline. Each step is checkpointed using Sprint 0 T-2.1.2 checkpoint machinery. On mid-job interruption, resumption picks up at the last checkpoint.
- Artefact creation does **not** modify Segment text, does not write Revision rows, does not write TRANSLATION-PO rows, does not write decision-event rows for content. Per Sprint 0 H-4 and Sprint 3 H-4 regression: the export pipeline is a pure-read operation with respect to project content.
- Artefact creation reads Formatvorlagen-Baseline v1.1 §7.2 (the canonical Formatvorlagen-Baseline) for layout. RTL handling per §7.2's per-run rule. Footnotes per `eachSect`. TOC per `\o "1-4"`.
- Artefact creation respects the user-confirmed Pflichtfragen-Bestätigungen recorded in T-9.1.1 (page range, scope mode, block types, export type) — these are read from the relevant project-scoped Decision Events with `decision_source = preflight_confirmation` and matching `related_export_attempt_id`.
- The artefact, on Word-compatible validation, opens without warning messages or repair indications.
- No new revision-UUID is issued during artefact creation. Code review is mandatory evidence here, per OCR Text Export Endfassung v1.3 H-4 analog.

### EXPORT_EVENT atomic creation

The EXPORT_EVENT is written **only** after the artefact is fully and successfully created. The two are atomic: either both exist, or neither does.

- Implementation: artefact creation runs to completion in a temporary location. Final commit is a single transactional step that (a) moves the artefact to its persistent location, (b) writes the EXPORT_EVENT via `create_po`, (c) marks the export job `abgeschlossen`. If any of (a), (b), (c) fails, the job → `fehlgeschlagen`, the temporary artefact is discarded, no EXPORT_EVENT exists, and the Log-Eintrag records the failure.
- `create_po` is called with `po_type = EXPORT_EVENT`, `scope_type = artefact`. The Provenance table accepts this scope_type per Sprint 0 T-1.6.1.
- The EXPORT_EVENT payload includes:
  - `export_uuid` (own UUID, issued via IDENTITY)
  - `project_uuid` (FK)
  - `export_type` (from `export_config.export_type`)
  - `export_config` JSONB (the active Pflichtfragen-Bestätigungen at job start, including page range as a page-number set, block types, scope mode, export type per OCR Text Export Endfassung v1.3 analog)
  - `revision_snapshot[]` UUID[] — every active `current_rev_uuid` of every Segment in the export's scope at the moment of job start
  - `active_decision_event_uuids[]` UUID[] — per the positive-allowlist rule below
  - `gate_mode` enum — explicit value `exportierbar` or `exportierbar_mit_warnungen`, set from preflight state at job start
  - `export_warnings[]` — concrete warning entries if `gate_mode = exportierbar_mit_warnungen`, empty array otherwise
  - `artefact_ref` — reference to the persisted artefact
  - `created_at` Timestamp
- After creation, the EXPORT_EVENT is unchangeable. Mutation attempts → error per Sprint 0 T-1.6.1 PO-Smoke-Test regression.

### `revision_snapshot[]` filling rule

Per OCR Text Export Endfassung v1.3 §3 step 1 analog:

```
exported_segment_uuids =
  SELECT satz_uuid FROM segments
  WHERE active = true
  AND in_scope_of(export_config.scope)

revision_snapshot[] =
  SELECT current_rev_uuid FROM segments
  WHERE satz_uuid IN exported_segment_uuids
  AND current_rev_uuid IS NOT NULL
```

- Reads from the `segments` table, not from the `revisions` table. The `current_rev_uuid` field on each in-scope active Segment is the source.
- Inactive Segments are excluded.
- Segments outside `export_config.scope` are excluded.
- The query is run once at job start; the snapshot is the result. The snapshot is not re-evaluated during artefact creation.

### `active_decision_event_uuids[]` filling rule (positive allowlist)

Per OCR Text Export Endfassung v1.3 §1.3 / §3 analog. The allowlist for `EXPORT_EVENT` (translation-export, distinct from `OCR_EXPORT_EVENT`) is:

| decision_source | Allowed | Justification |
|---|---|---|
| ocr_review | Yes | OCR error-class resolutions co-determine the exported text state |
| lock_management | Yes | Lock-flag decisions on exported Segments are part of the effective text state |
| conflict_resolution | Yes | Conflict resolutions on exported Segments determine the effective text state |
| translation_pipeline | Yes | Translation-pipeline Decision Events (incl. accepted Qurʾān-Stelle bestätigungen per §4.15 / Q4-5.1) determine the effective translation state |
| audit_resolution | Yes | A-class, B-class, D-class audit-finding resolutions on exported Segments determine the effective state |
| consistency_resolution | Yes | K-01–K-07 consistency-group resolutions determine work-wide terminology |
| preflight_confirmation | Yes, restricted | Only the four Pflichtfragen-Bestätigungen of the current export, bound to `related_export_attempt_id`. Plus per-warning go_with_warning confirmations from T-9.1.2 of the current export attempt. |
| glossary_management | Yes | Glossary entry decisions affect terminology binding state |
| export_confirmation | No | This `decision_source` is for OCR-export per §4.10; it does not apply to translation EXPORT_EVENT |
| style_management | No | Stilprofil-Versionierung-Decisions (per Dokument B v1.2 / Dokument C v1.1) are deferred from CR-3. When the F-family is built, this row is revisited. For now, no inclusion. |

The four Pflichtfragen-Bestätigungen and per-warning confirmations are bound to the current export attempt via `related_export_attempt_id` per OCR Text Export Endfassung v1.3 CR-1.6 analog. A `current_export_attempt_id` is generated at job start and used to filter `preflight_confirmation` events:

```
current_preflight_confirmation_uuids =
  SELECT decision_event_uuid FROM decision_events
  WHERE decision_source = 'preflight_confirmation'
  AND related_export_attempt_id = current_export_attempt_id
  AND is_superseded = false
```

The full filling query:

```
active_decision_event_uuids[] =

  SELECT decision_event_uuid FROM decision_events
  WHERE is_superseded = false
  AND decision_source IN (
    'ocr_review',
    'lock_management',
    'conflict_resolution',
    'translation_pipeline',
    'audit_resolution',
    'consistency_resolution',
    'glossary_management'
  )
  AND (
    (scope_type = 'segment' AND scope_uuid IN exported_segment_uuids)
    OR (scope_type = 'page'    AND scope_uuid IN exported_page_uuids)
    OR (scope_type = 'block'   AND scope_uuid IN exported_block_uuids)
    OR (scope_type = 'project' AND scope_uuid = current_project_uuid)
    OR (scope_type = 'account' AND scope_uuid = current_account_uuid)
  )

UNION

  current_preflight_confirmation_uuids
```

The five scope_type branches in the inner OR cover the canonical scope_type enum per Core Architecture Baseline §B.1 (extended per Dokument 2 §2D scope_type enum extension).

### Niemals-Automatisch-Liste additions

Per OCR Text Export Endfassung v1.3 CR-1.3 analog, two operational invariants for translation-export:

1. An EXPORT_EVENT must never be created without a fully successful artefact.
2. An EXPORT_EVENT must never be created outside the PROVENANCE core (`create_po`).

These are not new core-architecture invariants (they don't earn an H-XX number) but are operational invariants for the export pipeline. They are tested explicitly.

### Failure modes and event classification

Per OCR Text Export Endfassung v1.3 CR-1.4 analog:

| Call | Gate state | Job started | Log entry | EXPORT_EVENT |
|---|---|---|---|---|
| `check_preflight_state()` | any | No | No | No |
| `export_starten()` | blockiert | No | No | No |
| `export_starten()` | exportierbar | Yes, fails | Yes (FAILED) | No |
| `export_starten()` | exportierbar | Yes, succeeds | Yes (SUCCESS) | Yes |
| `export_starten()` | exportierbar_mit_warnungen + per-warning confirmations | Yes, succeeds | Yes (SUCCESS) | Yes |

The `check_preflight_state()` call from Sprint 4 T-9.1.x produces no Log-Eintrag and no EXPORT_EVENT; it is a pure-read pre-check. The Log-Eintrag and EXPORT_EVENT are tied to actual export attempts.

## 3. Ticket sequence

Single-ticket sprint:

```
[Sprint 4 complete; preflight reaches exportierbar | exportierbar_mit_warnungen on clean projects]
                             │
                             v
T-9.2.1 (artefact creation + EXPORT_EVENT atomic)
                             │
                             v
[Sprint 5 complete]
```

No internal parallelism within T-9.2.1. The artefact-creation pipeline is multi-step, but the steps are sequential per the canonical OCR-Export §5 analog.

## 4. Mandatory tests

| Test ID | Ticket | Check content | Setup note |
|---|---|---|---|
| EXPORT-EVENT-Nur-Bei-Erfolg-Test | T-9.2.1 | EXPORT_EVENT created only on a fully successful artefact creation | Run successful export; assert EXPORT_EVENT row + artefact present |
| EXPORT-EVENT-Kein-Eintrag-Bei-Fehler-Test | T-9.2.1 | Failed artefact creation → no EXPORT_EVENT, only Log-Eintrag | Force artefact creation failure; assert no EXPORT_EVENT row, log entry FAILED present |
| EXPORT-EVENT-Atomaritaet-Test | T-9.2.1 | No partial state: all mandatory fields set after creation; mid-commit failure produces no row at all | Force failure during commit step (a)/(b)/(c); assert no partial row, no orphaned artefact |
| EXPORT-EVENT-Via-PROVENANCE-Kern-Test | T-9.2.1 | EXPORT_EVENT written via `create_po`; no direct table insert from inside the export service | Code review |
| EXPORT-EVENT-Unveraenderlichkeit-Test | T-9.2.1 | EXPORT_EVENT mutation attempt after creation → error | Create EXPORT_EVENT; attempt update of `artefact_ref` → error |
| EXPORT-EVENT-Scope-Test | T-9.2.1 | `po_type = EXPORT_EVENT`, `scope_type = artefact` correctly set in the Provenance row | DB introspection |
| Revision-Snapshot-Vollstaendigkeit-Test | T-9.2.1 | `revision_snapshot[]` contains every active `current_rev_uuid` of every in-scope Segment at job start | Synthetic project with N in-scope active Segments; assert N entries |
| Revision-Snapshot-Inaktive-Excluded-Test | T-9.2.1 | Inactive Segments excluded from `revision_snapshot[]` | Mark Segments inactive; rerun export; assert exclusion |
| Revision-Snapshot-Outside-Scope-Excluded-Test | T-9.2.1 | Segments outside `export_config.scope` excluded | Synthetic project with mixed scope; assert filtering |
| Revision-Snapshot-Segments-Join-Test | T-9.2.1 | Snapshot read from `segments.current_rev_uuid`, not from `revisions` table | Code review |
| Active-Decision-Event-Uuids-Allowlist-Test | T-9.2.1 | `active_decision_event_uuids[]` contains only allowlist sources; no `export_confirmation`, no `style_management` | Inject Decision Events of all 10 source types; assert filtering |
| Active-Decision-Event-Uuids-Preflight-Confirmation-Attempt-Bindung-Test | T-9.2.1 | Only `preflight_confirmation` events with current `related_export_attempt_id` are included; older attempts excluded | Two attempt sequences; assert second snapshot contains only second attempt's confirmations |
| Active-Decision-Event-Uuids-Scope-Coverage-Test | T-9.2.1 | All five scope_type branches (segment, page, block, project, account) correctly filtered | Synthetic Decision Events at each scope; assert inclusion logic |
| Active-Decision-Event-Uuids-Is-Superseded-Filter-Test | T-9.2.1 | Superseded Decision Events excluded | Inject superseded events; assert exclusion |
| Gate-Mode-Set-Correctly-Test | T-9.2.1 | `gate_mode` field set to `exportierbar` or `exportierbar_mit_warnungen` per preflight state at job start | Two cases |
| Export-Warnings-Filled-When-With-Warnings-Test | T-9.2.1 | `export_warnings[]` contains concrete warning entries when `gate_mode = exportierbar_mit_warnungen`; empty array when `gate_mode = exportierbar` | Two cases |
| Pflichtfragen-Read-From-Decision-Events-Test | T-9.2.1 | `export_config` populated from project-scoped `preflight_confirmation` Decision Events of the current attempt — never from a saved Export-Profil directly | Pre-fill profile but require active confirmation per Sprint 4; assert export_config matches confirmation events, not profile |
| Preflight-Recheck-At-Job-Start-Test | T-9.2.1 | Preflight state re-checked at job start; if state changed since user's `export_starten` action, job fails with `preflight_state_changed` | Simulate state change between user action and job execution |
| Artefakt-Modifies-Nothing-Test | T-9.2.1 | Artefact creation does not modify Segment text, Revision, TRANSLATION-PO, or content decision-event rows | Run export; assert tables unchanged except Provenance (EXPORT_EVENT) and Log-Eintrag |
| Kein-Rev-UUID-Bei-Artefakterzeugung-Test | T-9.2.1 | No new revision-UUID issued during artefact creation; H-4 regression | Run export; assert revisions table delta = 0 |
| Word-Kompatibel-Oeffnungs-Test | T-9.2.1 | Generated artefact opens in Word without warning messages or repair indications | Word-compatible validation |
| RTL-Per-Run-Test | T-9.2.1 | Arabic runs carry `<w:rtl/>` per run per Formatvorlagen-Baseline v1.1 §7.2 | DOCX structural inspection |
| Formatvorlagen-Baseline-Adherence-Test | T-9.2.1 | Layout follows Formatvorlagen-Baseline v1.1 §7.2: page setup, header/footer, marginal lines, footnotes (eachSect), TOC (\o "1-4") | DOCX structural inspection |
| Log-Eintrag-Bei-Jedem-Versuch-Test | T-9.2.1 | Every export attempt produces a Log-Eintrag — successful, failed, or blocked | Three integration cases |
| Log-Eintrag-Vorabpruefung-Kein-Test | T-9.2.1 | `check_preflight_state()` calls produce no Log-Eintrag (only `export_starten()` calls do) | Five preflight checks; assert no log entries |
| Atomare-Commit-Step-Test | T-9.2.1 | Failure in commit step (a), (b), or (c) produces no EXPORT_EVENT, no orphaned artefact, no partial Provenance row | Force failure at each of three commit steps |
| Niemals-Automatisch-Test-1 | T-9.2.1 | EXPORT_EVENT cannot be created without successful artefact (operational invariant 1) | Code review + integration: attempt to call `create_po` for EXPORT_EVENT before artefact completion → error |
| Niemals-Automatisch-Test-2 | T-9.2.1 | EXPORT_EVENT cannot be created outside PROVENANCE core (operational invariant 2) | Code review |
| Export-Starten-Decision-Event-Test | T-9.2.1 | `export_starten` user action creates a Decision Event with `decision_type = exportstart` distinct from per-warning confirmations | Trigger user action; assert decision event |
| Export-Starten-Nur-Aus-Exportierbar-Test | T-9.2.1 | `export_starten` from `blockiert` state → error, no job created | Project in blockiert; attempt action → error |

Invariants in scope this sprint: H-4 (no revision-UUID for export operations), H-5 (UUID immutability for EXPORT_EVENT). Operational invariants: Niemals-Automatisch list entries 1 and 2 above. (H-1, H-2, H-6, H-7 carry forward as Sprint 0–4 regressions; all must remain green.)

New regressions from this sprint onward:

- EXPORT_EVENT created without successful artefact.
- EXPORT_EVENT created via direct table insert.
- EXPORT_EVENT mutated after creation.
- `revision_snapshot[]` reads from revisions table instead of `segments.current_rev_uuid`.
- `revision_snapshot[]` includes inactive Segments.
- `active_decision_event_uuids[]` includes `export_confirmation` (this `decision_source` is OCR-export-specific per §4.10; including it in translation EXPORT_EVENT is a category error).
- `active_decision_event_uuids[]` includes `style_management` (deferred per CR-3).
- `active_decision_event_uuids[]` includes `preflight_confirmation` from a previous export attempt.
- `gate_mode` not set or set to a value other than `exportierbar` / `exportierbar_mit_warnungen`.
- `export_config` populated directly from saved profile, bypassing active Pflichtfragen-Bestätigungen.
- Preflight state not re-checked at job start.
- Artefact creation modifies Segment text, Revision, TRANSLATION-PO, or content decision-events.
- Revision-UUID issued during artefact creation.
- Generated artefact opens with Word warnings or repair indications.
- Log-Eintrag missing from a failed or blocked export attempt.
- `check_preflight_state()` produces a Log-Eintrag.

## 5. Definition of Done

Code:

- T-9.2.1 implemented, reviewed, and merged.
- Engineering Execution Baseline v1.0 DoD satisfied for the ticket.
- Stilfeature-Test-Familien (CR-3) row vacuously satisfied — no F2 or F3 tickets in this sprint.
- All Sprint 0–4 regression tests still green.

Atomicity and provenance discipline:

- EXPORT-EVENT-Nur-Bei-Erfolg-Test green.
- EXPORT-EVENT-Kein-Eintrag-Bei-Fehler-Test green.
- EXPORT-EVENT-Atomaritaet-Test green.
- EXPORT-EVENT-Via-PROVENANCE-Kern-Test green.
- EXPORT-EVENT-Unveraenderlichkeit-Test green.
- EXPORT-EVENT-Scope-Test green.
- Atomare-Commit-Step-Test green.
- Niemals-Automatisch-Test-1 green.
- Niemals-Automatisch-Test-2 green.

Snapshot correctness:

- Revision-Snapshot-Vollstaendigkeit-Test green.
- Revision-Snapshot-Inaktive-Excluded-Test green.
- Revision-Snapshot-Outside-Scope-Excluded-Test green.
- Revision-Snapshot-Segments-Join-Test green.

Decision-event allowlist correctness:

- Active-Decision-Event-Uuids-Allowlist-Test green.
- Active-Decision-Event-Uuids-Preflight-Confirmation-Attempt-Bindung-Test green.
- Active-Decision-Event-Uuids-Scope-Coverage-Test green.
- Active-Decision-Event-Uuids-Is-Superseded-Filter-Test green.

Gate-mode and warnings:

- Gate-Mode-Set-Correctly-Test green.
- Export-Warnings-Filled-When-With-Warnings-Test green.

Pflichtfragen and preflight integration:

- Pflichtfragen-Read-From-Decision-Events-Test green.
- Preflight-Recheck-At-Job-Start-Test green.

Read-only export pipeline:

- Artefakt-Modifies-Nothing-Test green.
- Kein-Rev-UUID-Bei-Artefakterzeugung-Test green.

Artefact format compliance:

- Word-Kompatibel-Oeffnungs-Test green.
- RTL-Per-Run-Test green.
- Formatvorlagen-Baseline-Adherence-Test green.

Logging:

- Log-Eintrag-Bei-Jedem-Versuch-Test green.
- Log-Eintrag-Vorabpruefung-Kein-Test green.

User-action discipline:

- Export-Starten-Decision-Event-Test green.
- Export-Starten-Nur-Aus-Exportierbar-Test green.

End-to-end demonstrable at sprint end:

- A clean project in `exportierbar` state, on user `export_starten`, produces a complete artefact, an atomically-created EXPORT_EVENT row with correct `revision_snapshot[]` and `active_decision_event_uuids[]`, and a SUCCESS Log-Eintrag.
- A project in `exportierbar_mit_warnungen` with three confirmed warnings, on user `export_starten`, produces an artefact, an EXPORT_EVENT with `gate_mode = exportierbar_mit_warnungen`, `export_warnings[]` containing the three warning entries, and a SUCCESS Log-Eintrag.
- A simulated artefact-creation failure produces no EXPORT_EVENT, no orphaned artefact in the persistent location, only a FAILED Log-Eintrag.
- A simulated commit-step failure (in step (a), (b), or (c)) produces no EXPORT_EVENT, no artefact in the persistent location, no partial Provenance row.
- An `export_starten` attempt on a project in `blockiert` state fails immediately, produces no Log-Eintrag (since the attempt is rejected at the entry check), no job, no EXPORT_EVENT.
- A previously-exported project's EXPORT_EVENT row remains unchangeable — any update attempt fails.

## 6. Risks

R-S5-01 — EXPORT_EVENT created before artefact completion as a "progress marker". **Probability: high. Severity: structural.** Consequence: EXPORT_EVENTs exist for artefacts that were never produced or that failed mid-creation; downstream provenance queries (Sprint 6) return references to non-existent files; the "atomic" property collapses silently. (DBB §A names T-9.2.1 EXPORT_EVENT-Atomarität as unverhandelbar; DBB Abkürzung 4 names this exact failure mode.) Review obligation: EXPORT-EVENT-Nur-Bei-Erfolg-Test green; EXPORT-EVENT-Atomaritaet-Test green; Atomare-Commit-Step-Test green; code review confirms `create_po` for EXPORT_EVENT is reachable only from the post-artefact commit transaction.

R-S5-02 — EXPORT_EVENT written via direct table insert from the export service. Probability: medium. Consequence: PO immutability and atomic-creation guarantees from PROVENANCE-Kern bypassed; partial rows possible after mid-write crash; Niemals-Automatisch operational invariant 2 violated. Review obligation: EXPORT-EVENT-Via-PROVENANCE-Kern-Test green; Niemals-Automatisch-Test-2 green; code review of every EXPORT_EVENT write path.

R-S5-03 — `revision_snapshot[]` read from the `revisions` table instead of from `segments.current_rev_uuid`. Probability: medium. Consequence: snapshot includes superseded revisions; the snapshot represents the revision history rather than the in-scope effective state. Review obligation: Revision-Snapshot-Segments-Join-Test green (code review); Revision-Snapshot-Vollstaendigkeit-Test green.

R-S5-04 — `active_decision_event_uuids[]` includes `export_confirmation` decision_source. Probability: medium. Consequence: category error — `export_confirmation` per §4.10 is OCR-export-specific; including it in translation EXPORT_EVENT mixes the two snapshot semantics that OCR Text Export Endfassung v1.3 §1.4 explicitly forbids ("OCR_EXPORT_EVENT and EXPORT_EVENT are different PO types with different semantics... must never be silently mixed"). Review obligation: Active-Decision-Event-Uuids-Allowlist-Test green; code review of allowlist enforcement.

R-S5-05 — `active_decision_event_uuids[]` includes `style_management` despite CR-3 deferral. Probability: medium. Consequence: Stilprofil-Versionierung-Decisions per Dokument B v1.2 / Dokument C v1.1 are silently included in export provenance before the F-family is built; later canonization of the inclusion is pre-empted. Review obligation: Active-Decision-Event-Uuids-Allowlist-Test green; code review confirms `style_management` is in the No row of the allowlist.

R-S5-06 — Old `preflight_confirmation` from a previous export attempt included. Probability: medium. Consequence: stale Pflichtfragen-Bestätigungen pollute the current snapshot; the per-attempt binding via `related_export_attempt_id` collapses. Review obligation: Active-Decision-Event-Uuids-Preflight-Confirmation-Attempt-Bindung-Test green.

R-S5-07 — `export_config` populated directly from saved Export-Profil, bypassing active Pflichtfragen-Bestätigungen. Probability: medium. Consequence: Sprint 4's R-S4-04 risk re-emerges in the export pipeline despite Sprint 4's discipline; the Konfigurationsschicht's purpose silently violated at the artefact-creation step. Review obligation: Pflichtfragen-Read-From-Decision-Events-Test green; code review traces `export_config` source to current-attempt `preflight_confirmation` events.

R-S5-08 — Preflight state not re-checked at job start. Probability: medium. Consequence: a project that became `blockiert` between user action and job execution proceeds to artefact creation; export produces an artefact for a state that no longer satisfies preflight. Review obligation: Preflight-Recheck-At-Job-Start-Test green.

R-S5-09 — Artefact creation modifies Segment text, Revision, or TRANSLATION-PO. Probability: low. Consequence: H-4 silently violated; export becomes side-effect-producing; subsequent reads see export-modified state. Review obligation: Artefakt-Modifies-Nothing-Test green; Kein-Rev-UUID-Bei-Artefakterzeugung-Test green.

R-S5-10 — Generated artefact opens with Word warnings or repair indications. Probability: medium. Consequence: end-user experience degrades; format compliance with Formatvorlagen-Baseline v1.1 §7.2 broken; downstream consumers (publishers, editors) reject the file. (Analog to OCR Text Export Endfassung v1.3 OCR-R01.) Review obligation: Word-Kompatibel-Oeffnungs-Test green; RTL-Per-Run-Test green; Formatvorlagen-Baseline-Adherence-Test green.

R-S5-11 — Log-Eintrag missing from failed or blocked export attempts. Probability: low. Consequence: Sprint 4 Exportlauf-Ereignis discipline collapses for the actual export step; failure mode visibility lost. Review obligation: Log-Eintrag-Bei-Jedem-Versuch-Test green; assert log entry on FAILED, on success, on `preflight_state_changed`.

R-S5-12 — `check_preflight_state()` produces a Log-Eintrag. Probability: low. Consequence: log noise pollutes the Exportlauf-Ereignis family; pre-checks and actual attempts become indistinguishable in downstream analysis. Review obligation: Log-Eintrag-Vorabpruefung-Kein-Test green.

## 7. Transition to Sprint 6

Sprint 6 (Provenance Readout + History Endpoints) presupposes:

- T-9.2.1 green: Sprint 6's T-10.1.1 `get_export_events_for_segment(satz_uuid)` finds EXPORT_EVENTs via `revision_snapshot[]` lookup. Without populated EXPORT_EVENT rows, the lookup has nothing to find.
- `revision_snapshot[]` correctly populated: Sprint 6's lookup logic depends on the snapshot being a faithful set of in-scope active `current_rev_uuid` values at export time.
- `active_decision_event_uuids[]` correctly populated: Sprint 6's history endpoints (T-10.2.1 segment, page, project) must be able to attribute Decision Events to specific export contexts.

Sprint 6 may begin only after every Sprint 5 mandatory test in §4 is green.

## A. Hard Gates

HG-S5-1 — EXPORT-EVENT-Atomaritaet-Test must be green before merge. Per DBB §A, "EXPORT_EVENT-Atomarität... unverhandelbar". Atomic creation is the load-bearing discipline of this sprint.

HG-S5-2 — EXPORT-EVENT-Nur-Bei-Erfolg-Test AND EXPORT-EVENT-Kein-Eintrag-Bei-Fehler-Test must both be green before merge. Per DBB Abkürzung 4, the early-EXPORT_EVENT failure mode is one of the most-named risks.

HG-S5-3 — Niemals-Automatisch-Test-1 AND Niemals-Automatisch-Test-2 must both be green before merge. The two operational invariants are explicitly canonical (analog to OCR Text Export Endfassung v1.3 CR-1.3).

HG-S5-4 — Active-Decision-Event-Uuids-Allowlist-Test must be green before merge. The allowlist's structural correctness is the only protection against `export_confirmation` / `style_management` pollution; getting it wrong silently corrupts every EXPORT_EVENT going forward.

HG-S5-5 — Word-Kompatibel-Oeffnungs-Test must be green before merge. The artefact's Word-compatibility is the user-facing guarantee; failures here are immediately visible to end users.

HG-S5-6 — All Sprint 0–4 H-test regressions remain green: T-H1-01, T-H1-02, T-H2-01, T-H2-02, T-H4-01, T-H4-02, T-H5-01, T-H5-02, T-H6-01, T-H7-01.

HG-S5-7 — Engineering Execution Baseline v1.0 DoD Stilfeature-Test-Familien (CR-3) row vacuously satisfied this sprint (no F2/F3 tickets present).

HG-S5-8 — Preflight-Recheck-At-Job-Start-Test must be green before merge. Without this re-check, the export pipeline can produce artefacts for projects that became `blockiert` between user action and job execution — a structural failure that's hard to detect downstream.

## B. What deliberately does not belong in this sprint

- Provenance readout, history endpoints — WS-10 (Sprint 6). Sprint 5 produces EXPORT_EVENT rows; Sprint 6 reads them.
- Stilfeature backlog families F1, F3, F4, F5 (CR-3) — deferred per Dokument C v1.1 §3 follow-on work.
- `style_management` decision_source inclusion in `active_decision_event_uuids[]` — explicitly excluded per CR-3 deferral. Revisited when the F-family is built.
- Adobe InDesign / Affinity Publisher Export — deferred per Baseline Delivery Plan §4.
- Multi-language export beyond AR→DE — Schnittstelle 3's K-4 R-3 (English Hadith strang) and §4.15 EN Qurʾān-Übersetzung are canonical but not exercised at export this sprint. Both remain inert here.
- L-24 Klasse-B-Generallogik concrete Häufungsschwellenwerte per Dokument 1 §4.18 — structural mechanism canonical; concrete values are live-measurement-dependent and parked.
- UI for any module. Export-Starten dialog, progress indicator, post-export artefact preview — all backend-only this sprint.
- Calibration values: artefact-creation timeout, retry budget for export jobs, Word-compatibility validation thresholds — all configurable, never pre-set.
- Re-export of an existing EXPORT_EVENT (i.e., regenerating an artefact from a stored snapshot) — not in scope; would require a separate ticket and is not in DBB v1.0.
- E-5 / Schnittstelle 5 live test package — parked.
- Real Shamela Ist-Aufnahme — parked.

*Waraq Sprint-5 / Export Artifact + Provenance Handoff Delivery Plan v1.0 — End*