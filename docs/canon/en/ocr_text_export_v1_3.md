<!-- Source: Google Drive doc 1VyvAHtblpwfVlCvvVvPYCBoKzbj_vnmC3n2rUpeT7PI (OCR TEXT EXPORT v1.3) -->

# WARAQ — OCR TEXT EXPORT: CONSOLIDATED FINAL VERSION v1.3

No code. No coding release. Model-side closed final version before implementation decision.

## SECTION 1 — DEFINITIONS AND QUERY RULES

### 1.1 exported_segment_uuids — model-faithful join rule

The mapping of `ocr_revision_snapshot[]` values to Segment UUIDs hangs on the `segments` table, not on the `revisions` table. The `segments` table is the canonical owner of `satz_uuid` and carries `current_rev_uuid` as a derived reference field. The revision is not the owner of segment identity.

Query rule:

```
exported_segment_uuids =
  SELECT satz_uuid FROM segments
  WHERE current_rev_uuid IN ocr_revision_snapshot[]
  AND active = true
```

`ocr_revision_snapshot[]` contains Revisions-UUIDs. The `segments` table links via `current_rev_uuid` to exactly the segment whose current revision state was exported. A segment is included only if it was active at export time (`active = true`).

### 1.2 exported_page_uuids — model-faithful join rule (Variant B)

`export_config.page_range` contains the page range chosen by the user as user input — that is, page numbers, a range specification (e.g., 1–50), or a selection. It is not a pre-resolved set of `page_uuid` values. Resolution to `page_uuid` must occur model-faithfully via the `pages` table.

Page numbers are a display representation for the user. `page_uuid` is the canonical identity bearer in the model. Resolution must not happen implicitly in `export_config` but explicitly via the canonical table.

Query rule:

```
exported_page_uuids =
  SELECT page_uuid FROM pages
  WHERE page_number IN export_config.page_range
  AND project_uuid = current_project_uuid
  AND active = true
```

Notes:

- `page_number`: display field in the `pages` table with the page number visible to the user.
- `export_config.page_range`: normalized set of page numbers from user input (e.g., `{1, 2, …, 50}` from a range specification 1–50).
- `project_uuid`: ensures that the same page number from another project is not erroneously included.
- `active = true`: pages inactivated by page-replacement processes do not belong to the exported range.

- `export_config.page_range`: normalized set of page numbers from the user input (e.g. {1, 2, …, 50} from a range specification 1–50).
- `project_uuid`: ensures that the same page number from a different project is not mistakenly included.
- `active = true`: pages that have been deactivated by page-replacement processes do not belong to the exported range.

`export_config.page_range` stores the user input in the OCR_EXPORT_EVENT as a set of page numbers (not as a set of UUIDs). The UUID resolution is a runtime operation to determine the intermediate set `exported_page_uuids` and is not persisted.

### 1.3 active_decision_event_uuids[] — positive allowlist

Basic principle: the rule is a positive allowlist. Only explicitly permitted `decision_source` values are included. New `decision_source` values therefore do not accidentally land in the snapshot.

Allowlist for OCR_EXPORT_EVENT:

| decision_source | Allowed | Justification |
|---|---|---|
| ocr_review | Yes | OCR error-class resolutions co-determine the exported text state |
| lock_management | Yes | Lock-flag decisions on exported segments are part of the effective text state |
| conflict_resolution | Yes | Conflict resolutions on exported segments determine the effective text state |
| export_confirmation | Yes, restricted | Only the required-question confirmations of the current OCR export, bound to related_export_attempt_id |
| glossary_management | No | Glossary management concerns terminological control in the translation pipeline, not the OCR source-text state |
| translation_pipeline | No | Translation domain, not effective at OCR-export time |
| audit_resolution | No | Concerns translation outputs |
| consistency_resolution | No | Concerns work-wide translation terminology |
| preflight_confirmation | No | Concerns the final publication export, not the OCR export |
| style_management | No | Stilprofil decisions act in the translation phase, not on the OCR source-text state |

Refinement for `export_confirmation`: project-wide decision events from `export_confirmation` must not be included wholesale. Only the required-question confirmations of the current OCR export belong in the snapshot. Older OCR-export confirmations or confirmations from other domains stay out. For this purpose an explicit intermediate set is maintained:

```
current_export_confirmation_uuids =
  SELECT decision_event_uuid FROM decision_events
  WHERE decision_source = 'export_confirmation'
  AND related_export_attempt_id = current_export_attempt_id
  AND is_superseded = false
```

`related_export_attempt_id` is a runtime reference to the current export attempt. It ensures that only the required-question confirmations of this concrete export are included.

### 1.4 Distinction OCR_EXPORT_EVENT vs. EXPORT_EVENT

OCR_EXPORT_EVENT and EXPORT_EVENT are different PO types with different semantics. They must never be silently mixed, never typologically merged, and never aggregated under the same semantic treatment. A common presentation (e.g. in a project history) is permissible only if both types are explicitly separated and identified with their respective `po_type`.

### 1.5 No T-5.2.1 coupling

The OCR export has no glossary runtime relationship. `glossary_management` is excluded from the allowlist. This eliminates any coupling to T-5.2.1. T-5.2.1 is not a starting prerequisite for Sprint-OCR.

## SECTION 2 — CHANGE-REQUEST PASSAGES

### CR-1.1: Core Architecture Baseline v1.0 → v1.1 — new PO type OCR_EXPORT_EVENT

Insertion point: PO-type table, directly after the EXPORT_EVENT entry. Type: addition.

OCR_EXPORT_EVENT fields:

| Field | Type | Required | Meaning |
|---|---|---|---|
| ocr_export_uuid | UUID | Yes | Own UUID via IDENTITY service |
| project_uuid | UUID | Yes | FK to project |
| export_mode | Enum | Yes | `arbeitsstand` or `freigegebener_stand` |
| gate_mode | Enum | Yes | `exportierbar` or `exportierbar_mit_warnungen` — explicit gate state at export time |
| export_config | JSON | Yes | Actively answered required questions (page range as page-number set, block types, markings, export mode) |
| ocr_revision_snapshot[] | Array[UUID] | Yes | Active `current_rev_uuid` values of the exported segments |
| active_decision_event_uuids[] | Array[UUID] | Yes | Per the positive-set rule from §1.3 / §3 |
| export_warnings[] | Array[Object] | Yes | List of active warnings (empty if `gate_mode = exportierbar`) |
| artefact_ref | Ref | Yes | Reference to the DOCX artefact |
| active_stilprofil_version_uuid | UUID | No (nullable) | Active `stilprofil_version` at export time, if applicable |
| created_at | Timestamp | Yes | Time of creation |

On the field `active_stilprofil_version_uuid`: the field is formally established in the schema. For OCR source-text export it is semantically typically irrelevant and as a rule null, since the Stilprofil acts in the translation phase and does not change the OCR raw-text state. The field nevertheless remains part of the unchangeable schema and may not be silently omitted; it ensures uniform structure between EXPORT_EVENT and OCR_EXPORT_EVENT and permits unambiguous later evaluation.

Distinction wording: OCR_EXPORT_EVENT and EXPORT_EVENT are different PO types with different semantics. They must never be silently mixed, never typologically merged, and never aggregated under the same semantic treatment. A common presentation is permissible only if both types are explicitly separated and identified with their respective `po_type`.

Untouched: EXPORT_EVENT definition. All other PO types.

### CR-1.2: Core Architecture Baseline — OCR-export release gate

Insertion point: subsection "release gates" of the Core Architecture Baseline. Type: addition.

Content: the OCR-export release gate (OCR-Export-Gate) is led as an independent release gate alongside the existing publication-export release gate.

- Two gate states: `exportierbar` and `exportierbar_mit_warnungen`.
- Blocking states (gate not exportable): F-06-QR without resolution, F-07 critical, F-08 undecided, critical RTL-encoding problems, `conflict_instance` with unclear text state, inactive segments without lineage resolution.
- `go_with_warning` in `arbeitsstand` mode: double warning (reason + explicit confirmation).
- Four required questions to be actively answered (page range, block types, markings, export mode).
- No profile bypass: a saved profile may pre-fill required questions but never replaces an active confirmation.

### CR-1.3: Core Architecture Baseline — Niemals-Automatisch-Liste

Insertion point: "Niemals-Automatisch-Liste" of the Core Architecture Baseline. Type: addition.

Two new entries:

1. An OCR_EXPORT_EVENT must never be created without a fully successful DOCX artefact.
2. An OCR_EXPORT_EVENT must never be created outside the PROVENANCE core (`create_po()`).

### CR-1.4: Core Architecture Baseline — event classification OCR export

Insertion point: event-classification table. Type: addition.

Four OCR-export event types:

| Call | Gate state | Job started | Log entry | OCR_EXPORT_EVENT |
|---|---|---|---|---|
| check_ocr_export_gate() | any | No | No | No |
| start_ocr_export() | blocked | No | No | No |
| start_ocr_export() | exportierbar | Yes, fails | Yes (FAILED) | No |
| start_ocr_export() | exportierbar | Yes, succeeds | Yes (SUCCESS) | Yes |
| start_ocr_export() | exportierbar_mit_warnungen + confirmation | Yes, succeeds | Yes (SUCCESS) | Yes |

### CR-1.5: Core Architecture Baseline — decision-event object: field decision_source

Insertion point: schema definition of the decision-event object. Type: addition (new mandatory field).

New field:

| Field | Type | Required | Meaning |
|---|---|---|---|
| decision_source | Enum | Yes | Classifies which process domain a decision event originates from |

Complete enum values (non-overlapping):

| Value | Process domain |
|---|---|
| ocr_review | OCR error-class resolution |
| lock_management | Setting/lifting lock flags |
| conflict_resolution | Conflict resolution (terminology vs. lock flag, Qurʾān reference conflicts, Hadith conflicts, other canonized conflict action types) |
| glossary_management | Glossary entry change |
| export_confirmation | Required-question confirmation on OCR source-text export (T-OCR-EX-1). OCR export only; final export explicitly excluded |
| preflight_confirmation | Required-question confirmation on final publication export (P-01, T-9.1.1). Final export only; OCR export explicitly excluded |
| translation_pipeline | Translation and RULE_BINDING phase |
| audit_resolution | Audit-finding resolution |
| consistency_resolution | Consistency-group resolution |
| style_management | Stilprofil decisions (style-rule state changes, user confirmations, rollbacks) |

The separation `export_confirmation` ↔ `preflight_confirmation` is unambiguously secured by the enum table. No final-export decision can accidentally end up in the OCR-export snapshot, and vice versa.

Migration rule for existing decision events: all decision events created before this CR without `decision_source` are classified onto the ten enum values above in a separate migration work state. The final version carries exclusively these ten values; an additional enum value will not be introduced. The concrete classification heuristic and the treatment of unclassifiable legacy entries lie outside this final version and remain reserved for the separate migration work state. The migration is a formal prerequisite for baseline integrity but is not Sprint-OCR scope.

Same addition in: Implementation Translation Baseline v1.0 → v1.1, "core objects" section, decision-event entry.

### CR-1.6: Core Architecture Baseline — decision-event object: field related_export_attempt_id

Insertion point: schema definition of the decision-event object. Type: addition (new optional field).

New field:

| Field | Type | Required | Meaning |
|---|---|---|---|
| related_export_attempt_id | UUID | No (nullable) | Links a decision event with a concrete export attempt. Set only if `decision_source = 'export_confirmation'`. For all other `decision_source` values: null. |

Purpose: prevents required-question confirmations from earlier export attempts from ending up in the `active_decision_event_uuids[]` snapshot of a later export. The binding occurs exclusively via this field — not via time windows or other heuristic filters.

Setting rule: `related_export_attempt_id` is set when an `export_confirmation` decision event is created and is unchangeable thereafter.

Same addition in: Implementation Translation Baseline v1.0 → v1.1.

### CR-2.1: Implementation Translation Baseline v1.0 → v1.1 — core objects

Insertion point: core-object table, directly after EXPORT_EVENT. Type: addition.

Content: OCR_EXPORT_EVENT with full field schema per CR-1.1 (including `gate_mode` and `active_stilprofil_version_uuid`). Decision-event fields `decision_source` and `related_export_attempt_id` per CR-1.5 and CR-1.6. Distinction wording per §1.4.

### CR-2.2: Implementation Translation Baseline — state machines OCR-Export-Gate and Export-Job

Insertion point: state-machines section. Type: addition.

Content: two new state machines.

- OCR-Export-Gate: states `exportierbar`, `exportierbar_mit_warnungen`, `blockiert`. Transitions derived exclusively from inspected OCR states. No manual gate-state settings.
- OCR-Export-Job: states `gestartet`, `erfolgreich`, `fehlgeschlagen`. An OCR_EXPORT_EVENT is created atomically only from `erfolgreich`.

### CR-2.3: Implementation Translation Baseline — event and PO-type entries

Insertion point: event and PO-type registration. Type: addition.

Content: new event types OCR_EXPORT_SUCCESS and OCR_EXPORT_FAILED, registered with associated gate-state and job-state semantics. New PO-type entry OCR_EXPORT_EVENT per CR-1.1.

### CR-3.1: Engineering Execution Baseline — work packages

Insertion point: work-package table. Type: addition.

Content: four new work packages:

- AP-OCR-EX-1: OCR-Export-Gate logic and required-question flow.
- AP-OCR-EX-2: DOCX-artefact creation (RTL per-paragraph, block types, vocalization as present, footnote structure, editorial markings).
- AP-OCR-EX-3: OCR_EXPORT_EVENT creation via PROVENANCE core.
- AP-OCR-EX-4: project-history and lookup extension (`get_ocr_exports_for_segment()`); not part of Sprint-OCR.

### CR-3.2: Engineering Execution Baseline — build order

Insertion point: build-order matrix. Type: addition.

Content: two new build-order stages:

- Stage 2b (M-OCR-Export): T-OCR-EX-1 → T-OCR-EX-2 → T-OCR-EX-3.
- Stage 10b (M-Provenance-OCR): T-OCR-EX-4 (presupposes T-OCR-EX-3 and T-10.2.1).

### CR-4.1: Delivery Backlog Baseline — ticket group

Insertion point: ticket backlog. Type: addition.

Content: new ticket group T-OCR-EX-1 through T-OCR-EX-4 with scope per §5 of this document.

### CR-4.2: Delivery Backlog Baseline — milestones

Insertion point: milestone table. Type: addition.

Content: two new milestones:

- M-OCR-Export: T-OCR-EX-1 through T-OCR-EX-3 green; DOCX artefact reproducibly produced; OCR_EXPORT_EVENT atomically created.
- M-Provenance-OCR: T-OCR-EX-4 green; `get_ocr_exports_for_segment()` functional; project-history view OCR-export-capable.

None of these CRs redefines an existing ticket, an existing milestone, or an existing PO type. All CRs are additions.

## SECTION 3 — COMPLETE CODABLE QUERY RULE

```
-- Step 1: Exported segments (via segments table, model-faithful)
exported_segment_uuids =
  SELECT satz_uuid FROM segments
  WHERE current_rev_uuid IN ocr_revision_snapshot[]
  AND active = true

-- Step 2: Exported pages (via pages table, page number -> UUID resolved)
exported_page_uuids =
  SELECT page_uuid FROM pages
  WHERE page_number IN export_config.page_range
  AND project_uuid = current_project_uuid
  AND active = true

-- Step 3: Required-question confirmations of the current OCR-export attempt
current_export_confirmation_uuids =
  SELECT decision_event_uuid FROM decision_events
  WHERE decision_source = 'export_confirmation'
  AND related_export_attempt_id = current_export_attempt_id
  AND is_superseded = false

-- Step 4: Complete active_decision_event_uuids[]
active_decision_event_uuids[] =

  SELECT decision_event_uuid FROM decision_events
  WHERE is_superseded = false
  AND decision_source IN ('ocr_review', 'lock_management', 'conflict_resolution')
  AND (
    (scope_type = 'segment' AND scope_uuid IN exported_segment_uuids)
    OR (scope_type = 'page'    AND scope_uuid IN exported_page_uuids)
  )

UNION

current_export_confirmation_uuids
```

Guarantees of this rule:

- `export_confirmation` and `preflight_confirmation` are unambiguously separated; no double classification.
- `exported_segment_uuids` model-faithful via the `segments` table; no borrowing from the `revisions` table.
- `exported_page_uuids` model-faithful via the `pages` table, page number → UUID resolved, restricted to the current project.
- Inactive segments and inactive pages excluded.
- Positive allowlist: new `decision_source` values (`style_management`, `translation_pipeline`, `audit_resolution`, `consistency_resolution`, `glossary_management`, `preflight_confirmation`) cannot accidentally land in the snapshot.
- Only required-question confirmations of the current export attempt via `related_export_attempt_id`.

## SECTION 4 — CR OVERVIEW

| CR | Document | Type | Content |
|---|---|---|---|
| CR-1.1 | Core Architecture Baseline | Addition | New PO type OCR_EXPORT_EVENT incl. `gate_mode` and `active_stilprofil_version_uuid`; distinction wording |
| CR-1.2 | Core Architecture Baseline | Addition | OCR-export release gate |
| CR-1.3 | Core Architecture Baseline | Addition | Niemals-Automatisch-Liste: two new entries |
| CR-1.4 | Core Architecture Baseline | Addition | Event classification: four OCR-export event types |
| CR-1.5 | Core Architecture Baseline | Addition | Decision-event object: new mandatory field `decision_source` (enum with 10 values incl. `style_management`) |
| CR-1.6 | Core Architecture Baseline | Addition | Decision-event object: new optional field `related_export_attempt_id` |
| CR-2.1 | Implementation Translation Baseline | Addition | New core object OCR_EXPORT_EVENT; decision-event fields `decision_source` and `related_export_attempt_id` |
| CR-2.2 | Implementation Translation Baseline | Addition | State machines OCR-Export-Gate and Export-Job |
| CR-2.3 | Implementation Translation Baseline | Addition | New event and PO-type entries |
| CR-3.1 | Engineering Execution Baseline | Addition | Work packages AP-OCR-EX-1 through AP-OCR-EX-4 |
| CR-3.2 | Engineering Execution Baseline | Addition | Build-order stages 2b (M-OCR-Export) and 10b (M-Provenance-OCR) |
| CR-4.1 | Delivery Backlog Baseline | Addition | Ticket group T-OCR-EX-1 through T-OCR-EX-4 |
| CR-4.2 | Delivery Backlog Baseline | Addition | Milestones M-OCR-Export and M-Provenance-OCR |

All CRs are additions. No existing ticket, no existing milestone, and no existing PO type is redefined.

## SECTION 5 — SPRINT PLAN SPRINT-OCR v1.3

Start condition: Sprint 1 fully completed (T-4.3.1, T-5.1.1, T-5.1.2, T-4.2.1, T-4.2.2 green; T-1.6.1 green). T-5.2.1 is not a start prerequisite. T-OCR-EX-4 is not part of this sprint. CR-1.5 and CR-1.6 are present as schema migration before T-OCR-EX-1 starts.

### 1. Scope

| Ticket | Designation |
|---|---|
| T-OCR-EX-1 | OCR-export gate (release gate, two modes, four required questions) |
| T-OCR-EX-2 | OCR text-artefact creation DOCX (RTL per paragraph, block types, vocalization as present, markings) |
| T-OCR-EX-3 | OCR_EXPORT_EVENT creation (atomic, via PROVENANCE core, positive-set snapshot, unchangeable) |

Deliberately not in this sprint: T-OCR-EX-4 (after Sprint 6), T-5.2.1 (no coupling), translation pipeline, audit, preflight, EXPORT_EVENT.

### 2. Sprint target state

T-OCR-EX-1 — OCR-Export-Gate:

- `check_ocr_export_gate()` computes the gate state on demand, no log entry.
- `start_ocr_export()` checks the gate as the first action; on a blocked gate, no log entry, no job start.
- Hard blockages: F-06-QR unresolved, F-07 critical, F-08 undecided, critical RTL-encoding problems, `conflict_instance` with unclear text state, inactive segments without lineage resolution.
- `go_with_warning` in `arbeitsstand` mode: double warning (reason + explicit confirmation).
- Four required questions to be actively answered (page range, block types, markings, export mode).
- Decision-event UUID on confirmation with `decision_source = 'export_confirmation'` and `related_export_attempt_id = current_export_attempt_id`.
- Log entry only on an actually started job (gate was green, job started).

T-OCR-EX-2 — DOCX artefact creation:

- Arabic source text from the `current_rev_uuid` text state of all exported segments (locked segments: manually corrected text, never raw OCR text).
- RTL paragraph marking per paragraph (not only document-global).
- Block-type document styles: MT, UE; optional FN, QR, HD, RN.
- Real DOCX footnote structure when FN is activated.
- Vocalization exactly as present — no addition, no suppression.
- Editorial markings (user decision): DOCX comments on locked segments, open conflicts, vocalization uncertainties.
- Export protocol always: page range, mode, block types, vocalization statistics, warning list.
- DOCX opens in Word without warning messages or repair indications.
- No new revision UUID through DOCX creation.

T-OCR-EX-3 — OCR_EXPORT_EVENT creation:

- Atomic after fully successful DOCX via PROVENANCE core (`create_po()`).
- `po_type = OCR_EXPORT_EVENT`, `scope_type = artefact`.
- `ocr_revision_snapshot[]`: all active `current_rev_uuid` values of the exported segments.
- `active_decision_event_uuids[]`: per the positive-set rule (steps 1–4 from §3).
- `gate_mode`: explicitly set (`exportierbar` or `exportierbar_mit_warnungen`).
- `active_stilprofil_version_uuid`: typically null in the OCR-export context; the field is nevertheless carried per schema.
- Unchangeable after creation.
- On failed DOCX: no OCR_EXPORT_EVENT, only log entry (OCR_EXPORT_FAILED).

New objects at sprint end:

| Object | Introduced by | Purpose |
|---|---|---|
| OCR_EXPORT_EVENT | T-OCR-EX-3 | Persistent, unchangeable provenance object |
| decision_source (field) | T-OCR-EX-1 | Classifies the process domain of every decision event |
| related_export_attempt_id (field) | T-OCR-EX-1 | Binds `export_confirmation` decisions to a concrete attempt |
| gate_mode (field in OCR_EXPORT_EVENT) | T-OCR-EX-3 | Explicit gate state, directly readable |
| export_warnings[] | T-OCR-EX-3 | Concrete warnings at export time |

Deliberately not yet present: `get_ocr_exports_for_segment()` (T-OCR-EX-4), project-history extension (T-OCR-EX-4), UI flow.

### 3. Ticket sequence

Start conditions: T-4.3.1 (`ocr_status`), T-5.1.1 (lock flag), T-5.1.2 (`conflict_instance`), T-4.2.1 and T-4.2.2 (lineage), T-1.6.1 (PROVENANCE core) green. T-5.2.1 not required. CR-1.5 and CR-1.6 present as schema migration.

Sequence:

```
T-OCR-EX-1 (gate + decision_source / related_export_attempt_id)
    |
    v
T-OCR-EX-2 (DOCX creation)
    |
    v
T-OCR-EX-3 (OCR_EXPORT_EVENT atomic)
```

Strictly sequential. No parallel window.

### 4. Mandatory tests

| Test ID | Ticket | Check content | Setup note |
|---|---|---|---|
| OCR-Gate-Blockiert-F06-Test | T-OCR-EX-1 | F-06-QR without resolution → gate blocked | F-06-QR without `resolution_type` |
| OCR-Gate-Blockiert-F07-Test | T-OCR-EX-1 | F-07 critical → gate blocked | F-07 with critical classification |
| OCR-Gate-Blockiert-F08-Test | T-OCR-EX-1 | F-08 undecided → gate blocked | F-08 without resolution |
| OCR-Gate-Vorabpruefung-Kein-Log-Test | T-OCR-EX-1 | `check_ocr_export_gate()` → no log entry | Delta check: log table unchanged |
| OCR-Gate-Blockiert-Start-Kein-Log-Test | T-OCR-EX-1 | `start_ocr_export()` on blocked gate → no log entry | Delta check |
| OCR-Gate-Go-With-Warning-Doppelwarnung-Test | T-OCR-EX-1 | `go_with_warning` in `arbeitsstand` → double warning + confirmation | – |
| OCR-Gate-Pflichtfragen-Aktiv-Test | T-OCR-EX-1 | Export without actively answered required questions → blocked | – |
| OCR-Gate-Kein-Profil-Bypass-Test | T-OCR-EX-1 | Saved profile does not replace active confirmation | Profile pre-filled; confirmation missing → blocked |
| OCR-Gate-Decision-Event-Source-Test | T-OCR-EX-1 | Required-question confirmation → decision event with `decision_source = 'export_confirmation'` | Evidence in decision-event table |
| OCR-Gate-Export-Attempt-ID-Test | T-OCR-EX-1 | `related_export_attempt_id` correctly set to `current_export_attempt_id` | Evidence in decision-event table |
| RTL-Absatz-Test | T-OCR-EX-2 | Each paragraph has explicit RTL marking (not only document-global) | DOCX structural check at paragraph level |
| DOCX-Integritaets-Test | T-OCR-EX-2 | DOCX opens in Word without warning messages or repair indications | Word-compatible validation |
| Blocktypen-Filter-Test | T-OCR-EX-2 | Only enabled block types in DOCX; disabled in protocol | QR disabled; QR absent in DOCX; protocol entry present |
| Vokalisation-Wie-Vorliegend-Test | T-OCR-EX-2 | Harakāt in OCR state appear in DOCX; no artificial addition | Segment with Harakāt; segment without Harakāt |
| Gesperrtes-Segment-Manueller-Text-Test | T-OCR-EX-2 | Segment with `manual_local` contains manually corrected text, not raw OCR text | H-1 evidence |
| Fussnotenstruktur-Test | T-OCR-EX-2 | FN blocks as real DOCX footnotes, not as inline text | FN activated; DOCX structure inspected |
| Export-Protokoll-Immer-Test | T-OCR-EX-2 | Protocol always produced; contains vocalization statistics and warning list | – |
| Kein-Rev-UUID-DOCX-Test | T-OCR-EX-2 | DOCX creation produces no new revision UUID | Delta check on revisions table |
| OCR-EXPORT_EVENT-Nur-Bei-Erfolg-Test | T-OCR-EX-3 | OCR_EXPORT_EVENT only on successful DOCX | Delta check |
| OCR-EXPORT_EVENT-Kein-Eintrag-Bei-Fehler-Test | T-OCR-EX-3 | Failed DOCX → no new OCR_EXPORT_EVENT | Simulated artefact failure |
| OCR-EXPORT_EVENT-Atomaritaet-Test | T-OCR-EX-3 | No partial state; all mandatory fields set after creation | – |
| OCR-Snapshot-Vollstaendigkeit-Test | T-OCR-EX-3 | `ocr_revision_snapshot[]` contains all active `current_rev_uuid` values | N segments → N entries |
| OCR-Snapshot-Segments-Join-Test | T-OCR-EX-3 | `exported_segment_uuids` via `segments.current_rev_uuid`, not via revisions table | Code-review evidence |
| OCR-Snapshot-Pages-Join-Test | T-OCR-EX-3 | Query runs via `page_number IN export_config.page_range` with `project_uuid` filter and `active = true`; no direct UUID comparison against `export_config` | Code-review evidence |
| OCR-Decision-Snapshot-Allowlist-Test | T-OCR-EX-3 | `active_decision_event_uuids[]` contains only allowlist sources; no `glossary_management`; no `preflight_confirmation`; no `style_management`; no old `export_confirmation` entry | Known set; array inspected |
| OCR-Decision-Snapshot-Attempt-Bindung-Test | T-OCR-EX-3 | Only `export_confirmation` entries with current `related_export_attempt_id`; older ones excluded | Two entries with different `attempt_id` values; only current in array |
| OCR-Gate-Mode-Test | T-OCR-EX-3 | `gate_mode` correctly set | `go_with_warning` → `gate_mode = exportierbar_mit_warnungen` |
| OCR-EXPORT_EVENT-Via-PROVENANCE-Kern-Test | T-OCR-EX-3 | `create_po()` via PROVENANCE core; no direct table insert | Code-review evidence |
| OCR-EXPORT_EVENT-Unveraenderlichkeit-Test | T-OCR-EX-3 | Update attempt → error | Attempt to change `artefact_ref` → error |
| OCR-EXPORT_EVENT-Scope-Test | T-OCR-EX-3 | `po_type = OCR_EXPORT_EVENT`, `scope_type = artefact` in the provenance table | – |
| Log-Eintrag-Bei-Gestarteten-Job-Test | T-OCR-EX-3 | Log entry (SUCCESS or FAILED) on every actually started job | Failed DOCX: OCR_EXPORT_FAILED log present |

Invariants:

- H-1: locked segments in export with manually corrected text.
- H-3 (analogue): no artefact creation without actively answered required questions.
- H-4: no revision UUID through DOCX creation or OCR_EXPORT_EVENT creation.
- H-5: `ocr_export_uuid` unchangeable after creation.

New regressions from this sprint onward:

- OCR_EXPORT_EVENT created on a blocked or failed export.
- DOCX opens with warning messages in Word.
- RTL only at document level.
- Locked segment exported with raw OCR text.
- Pre-check produces a log entry.
- OCR_EXPORT_EVENT not created via PROVENANCE core.
- `glossary_management`, `preflight_confirmation`, or `style_management` decision in `active_decision_event_uuids[]`.
- Old `export_confirmation` decision from a previous export in `active_decision_event_uuids[]`.
- `decision_source` field unset on a new decision event.
- `exported_page_uuids` contains inactive pages or pages outside the current project.

### 5. Definition of Done

Code:

- T-OCR-EX-1, T-OCR-EX-2, T-OCR-EX-3 implemented, reviewed, and merged.
- CR-1.5 and CR-1.6 (`decision_source`, `related_export_attempt_id`) present as schema migration in the database.
- No open review comment describing a baseline violation.
- Sprint-0 to Sprint-1 regression tests still green.

OCR-Export-Gate:

- OCR-Gate-Blockiert-F06/F07/F08 tests green.
- OCR-Gate-Vorabpruefung-Kein-Log-Test green.
- OCR-Gate-Blockiert-Start-Kein-Log-Test green.
- OCR-Gate-Go-With-Warning-Doppelwarnung-Test green.
- OCR-Gate-Pflichtfragen-Aktiv-Test green.
- OCR-Gate-Kein-Profil-Bypass-Test green.
- OCR-Gate-Decision-Event-Source-Test green.
- OCR-Gate-Export-Attempt-ID-Test green.

DOCX artefact:

- RTL-Absatz-Test green.
- DOCX-Integritaets-Test green.
- Blocktypen-Filter-Test green.
- Vokalisation-Wie-Vorliegend-Test green.
- Gesperrtes-Segment-Manueller-Text-Test green.
- Fussnotenstruktur-Test green.
- Export-Protokoll-Immer-Test green.
- Kein-Rev-UUID-DOCX-Test green.

OCR_EXPORT_EVENT:

- OCR-EXPORT_EVENT-Nur-Bei-Erfolg-Test green.
- OCR-EXPORT_EVENT-Kein-Eintrag-Bei-Fehler-Test green.
- OCR-EXPORT_EVENT-Atomaritaet-Test green.
- OCR-Snapshot-Vollstaendigkeit-Test green.
- OCR-Snapshot-Segments-Join-Test green (code review).
- OCR-Snapshot-Pages-Join-Test green (code review).
- OCR-Decision-Snapshot-Allowlist-Test green.
- OCR-Decision-Snapshot-Attempt-Bindung-Test green.
- OCR-Gate-Mode-Test green.
- OCR-EXPORT_EVENT-Via-PROVENANCE-Kern-Test green (code review).
- OCR-EXPORT_EVENT-Unveraenderlichkeit-Test green.
- OCR-EXPORT_EVENT-Scope-Test green.
- Log-Eintrag-Bei-Gestarteten-Job-Test green.

### 6. Risks

OCR-R01 — RTL only at document level. Probability: high. Consequence: DOCX paragraphs without their own RTL marking; rendering in Word unreliable. Review obligation: RTL-Absatz-Test must inspect paragraph level.

OCR-R02 — Locked segment with raw OCR text. Probability: medium. Consequence: manual corrections lost in export. Review obligation: Gesperrtes-Segment-Manueller-Text-Test green; code review checks the text-state source.

OCR-R03 — OCR_EXPORT_EVENT misunderstood as a progress marker. Probability: high. Consequence: provenance entries for blocked or failed exports. Review obligation: atomicity and error tests green.

OCR-R04 — Pre-check produces log entry. Probability: medium. Consequence: log noise; event classification distorted. Review obligation: Vorabpruefung-Kein-Log-Test and Blockiert-Start-Kein-Log-Test green.

OCR-R05 — Snapshot incomplete. Probability: medium. Consequence: `ocr_revision_snapshot[]` does not fully cover the exported segments. Review obligation: Snapshot-Vollstaendigkeit-Test with known segment count green.

OCR-R06 — DOCX library without per-paragraph RTL. Probability: medium. Consequence: target state technically unattainable. Review obligation: library pre-check before sprint start.

OCR-R07 — `glossary_management` accidentally in snapshot. Probability: medium. Consequence: OCR_EXPORT_EVENT contains semantically false decision events that do not concern the OCR source-text state. Review obligation: OCR-Decision-Snapshot-Allowlist-Test must explicitly verify that no `glossary_management` entry is in the array.

OCR-R08 — Old `export_confirmation` entry in snapshot. Probability: medium. Consequence: required-question confirmations from earlier exports land in the snapshot of the current export. Review obligation: OCR-Decision-Snapshot-Attempt-Bindung-Test green.

OCR-R09 — `decision_source` field unset on all new decision events. Probability: medium. Consequence: `decision_source` is null; allowlist query returns false results or fails. Review obligation: OCR-Gate-Decision-Event-Source-Test green; code review checks all places in the sprint that create decision events.

OCR-R10 — `exported_page_uuids` contains inactive pages or pages outside the current project. Probability: medium. Consequence: page-scoped decision events of inactive or foreign-project pages land in the snapshot. Review obligation: OCR-Snapshot-Pages-Join-Test green; code review confirms `active = true` and `project_uuid` filters.

### 7. Transition to T-OCR-EX-4

T-OCR-EX-4 presupposes T-OCR-EX-3 and T-10.2.1. The `ocr_revision_snapshot[]` filling from T-OCR-EX-3 is the technical basis for the later lookup in T-OCR-EX-4 (`get_ocr_exports_for_segment()`).

### A. Hard Gates

HG-1 — T-OCR-EX-2 not without green T-OCR-EX-1. HG-2 — OCR-EXPORT_EVENT-Atomaritaet-Test and OCR-EXPORT_EVENT-Kein-Eintrag-Bei-Fehler-Test green before T-OCR-EX-3 merge. HG-3 — RTL-Absatz-Test must demonstrate paragraph level (not only document level). HG-4 — OCR-Gate-Vorabpruefung-Kein-Log-Test and OCR-Gate-Blockiert-Start-Kein-Log-Test green before T-OCR-EX-1 merge. HG-5 — OCR-EXPORT_EVENT-Via-PROVENANCE-Kern-Test (code review) green. HG-6 — OCR-Decision-Snapshot-Allowlist-Test and OCR-Decision-Snapshot-Attempt-Bindung-Test green before T-OCR-EX-3 merge. No `glossary_management`, no `preflight_confirmation`, no `style_management`, no old `export_confirmation` entry in the snapshot. HG-7 — CR-1.5 and CR-1.6 present as database schema migration before T-OCR-EX-1 starts. No sprint start without this schema extension.

### B. What deliberately does not belong in this sprint

T-OCR-EX-4, T-5.2.1 coupling, UI flow, calibration, DOCX library decision (to be made before sprint start), translation pipeline, audit, preflight, EXPORT_EVENT.

Migration of existing decision events (`decision_source` field on existing entries): formally required (CR-1.5 migration rule), but not Sprint-OCR scope. Planned as a separate migration step before sprint start.

## OPEN POINTS / NOT RELIABLY RECONSTRUCTABLE REMAINDERS

1. Fully written-out long-form versions of CRs CR-1.2, CR-1.3, CR-2.2, CR-2.3, CR-3.1, CR-3.2, CR-4.1, and CR-4.2 are present in the three predecessor versions only in the form of the CR overview and indirect references. In §2 of this document they are documented in the form that is reliably derivable from the version context and the current Waraq canon (insertion point, type, structural content description). Verbatim original wordings are not available and are not reconstructed.

2. Migration details for existing decision events (heuristic for assigning legacy entries to the ten canonical enum values per CR-1.5, plus treatment of unclassifiable legacy entries) are not written out in any of the three predecessor versions and remain reserved for a separate migration work state.

*Waraq OCR Text Export Consolidated Final Version v1.3 — End*

