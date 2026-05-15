<!-- Authored: 2026-05-01. -->
<!-- Status: Authored to replace presumed-lost original v1.0 per option (c). Final sprint of the seven-sprint set. -->
<!-- Anchored to: Baseline Delivery Plan v1.0 §2 (Sprint 6 scope description); DBB v1.0 §10 Delivery-Reihenfolge Schritt 10; DBB v1.0 ticket definitions T-10.1.1, T-10.1.2, T-10.2.1; DBB v1.0 §B Abkürzung 8 (Lineage-Matching erzeugt Decision-Event-UUIDs — regression-relevant for history correctness); Engineering Execution Baseline v1.0 (DoD); Core Architecture Baseline v1.0 (scope_type enum, H-5); Dokument 1 §4.11 (Abfrageregel active_decision_event_uuids[]); Dokument 2 §2.3 / §2.4 / §2.10 (Stilfeature account-scoped Decision-Event-Lesepfad as gebundener Resthinweis WS-10). -->
<!-- Replaces: any presumed-lost prior "Waraq Sprint-6 / Provenance Readout + History Endpoints Delivery Plan v1.0" referenced in Dokument 2 §1 and Baseline Delivery Plan §1. -->
<!-- Structural template: ocr_text_export_v1_3.md §5 Sprint Plan Sprint-OCR v1.3. -->

# Waraq Sprint-6 / Provenance Readout + History Endpoints Delivery Plan v1.0

Status: Working basis. No coding release. No silent re-baselining. Final sprint of the seven-sprint set.

## Start condition

Sprints 0–5 fully completed. All Sprint 0–5 mandatory tests green. EXPORT_EVENT rows being produced atomically via PROVENANCE-Kern with correctly populated `revision_snapshot[]` and `active_decision_event_uuids[]` (T-9.2.1). Provenance table contains POs of all canonical types: SCAN, OCR, MANUAL_-, RULE_BINDING, TRANSLATION, LINEAGE_EVENT, EXPORT_EVENT. Decision Events being produced with correct `scope_type` values: `segment`, `page`, `block`, `account`, `project` (per Dokument 2 §2D enum extension). Log-Eintrag rows being produced via EVENTING for all canonical operations.

## 1. Scope

| Ticket | Designation |
|---|---|
| T-10.1.1 | PROVENANCE-Auswertung: `get_pos_for_segment` + `get_export_events_for_segment` via `revision_snapshot[]` lookup |
| T-10.1.2 | PROVENANCE-Auswertung: `get_page_history` (page-scoped Decision Events) + `get_project_history` (project-scoped Decision Events + EXPORT_EVENTs) |
| T-10.2.1 | Historien-Scope-Trennung: four scope-separated backend endpoints |

Deliberately not in this sprint: any further export work (closed in Sprint 5), any UI rendering of histories (the canon explicitly scopes WS-10 to backend endpoints), any new PO writes (the readout layer is read-only by design), Stilfeature backlog families F1–F5 (CR-3) — deferred per Dokument C v1.1 §3 follow-on work, account-scoped Decision-Event-Lesepfad — explicitly held as a gebundener Resthinweis per Dokument 2 §2D, and L-24 Klasse-B-Generallogik concrete Häufungsschwellenwerte. No UI for any module. No calibration values.

## 2. Sprint target state

**T-10.1.1 — Segment-scoped PO query and EXPORT_EVENT linkage**

Two read functions, both pure-read, both against the Provenance table populated across Sprints 0–5.

- `get_pos_for_segment(satz_uuid)` returns all POs where `scope_type = segment` AND `scope_uuid = satz_uuid`. **No other scope_types are returned.** Page-scoped POs (e.g., SCAN-PO from T-3.1.2) and project-scoped POs (e.g., LINEAGE_EVENT with project-scoped variants if any) and artefact-scoped POs (EXPORT_EVENT) are excluded from this query.
- The function is read-only. It writes nothing — no Revision, no Decision Event, no Log-Eintrag. (The Engineering Execution Baseline v1.0 DoD allows logging of user-initiated query operations as part of audit trail, but the readout layer itself per ITB §6 is pure-read; if logging is added, it must use EVENTING and not produce any other side effects.)
- `get_export_events_for_segment(satz_uuid)` returns EXPORT_EVENT rows where the segment's `current_rev_uuid` is contained in the EXPORT_EVENT's `revision_snapshot[]` array. The lookup is **strictly via `revision_snapshot[]`** — no direct segment-FK on the EXPORT_EVENT row exists, and no such FK shortcut may be introduced.
- The lookup follows the segment's lineage history correctly: when a Segment was active under an earlier `current_rev_uuid` that was in some prior export's snapshot, that EXPORT_EVENT is returned. When a Segment was inactivated and reactivated (per Sprint 1 T-4.2.2), EXPORT_EVENTs covering both the pre-inactivation and post-reactivation snapshots are returned in chronological order.
- For each returned EXPORT_EVENT, the result includes a structural marker: `als_werkweite_referenz = true`. This makes explicit that the EXPORT_EVENT is not a segment-eigener Export — it is a project-/work-wide reference in which the Segment participated at the time of export.

**T-10.1.2 — Page-scoped and project-scoped history**

- `get_page_history(page_uuid)` returns Decision Events where `scope_type = page` AND `scope_uuid = page_uuid`. **No segment-scoped Decision Events are included**, even Decision Events about Segments belonging to that Page. The page history is the page-level history only.
- `get_project_history(project_uuid)` returns:
  - Decision Events where `scope_type = project` AND `scope_uuid = project_uuid`.
  - EXPORT_EVENT rows where the EXPORT_EVENT's `project_uuid` matches.
- `get_project_history` does **not** return:
  - segment-scoped Decision Events.
  - page-scoped Decision Events.
  - block-scoped Decision Events.
  - account-scoped Decision Events. (The account-scoped Decision-Event-Lesepfad is a Sprint-6-relevant gap explicitly held as a gebundener Resthinweis per Dokument 2 §2D and addressed in CR-3 follow-on work; this sprint does not introduce it.)
  - Log-Eintrag rows.
  - any PO except EXPORT_EVENT.
- Both functions are pure-read.
- Both functions return results in chronological order (by `created_at`).

**T-10.2.1 — Four scope-separated backend endpoints**

Four endpoints, each strictly scope-trennend. No UI logic in any of them — all scope discipline is enforced backend-side.

- **Segmenthistorie endpoint** — `GET /history/segment/{satz_uuid}` — returns:
  - All segment-scoped Revision-UUIDs for `satz_uuid` (the full revision chain).
  - All segment-scoped Decision-Event-UUIDs for `satz_uuid` (lock changes, conflict resolutions, audit-finding resolutions, manual edits' decision events).
  - All EXPORT_EVENT references where the Segment participated (via `revision_snapshot[]` lookup, marked `als_werkweite_referenz = true`).
  - All segment-scoped POs for `satz_uuid` from `get_pos_for_segment`.
  - **Excludes**: page-scoped Decision Events, block-scoped Decision Events, project-scoped Decision Events, account-scoped Decision Events, Log-Eintrag rows.
- **Seitenhistorie endpoint** — `GET /history/page/{page_uuid}` — returns:
  - All page-scoped Decision-Event-UUIDs for `page_uuid` (OCR-Review-Status resolutions, page-level user actions).
  - **Excludes**: segment-scoped Decision Events of Segments on that Page, segment-scoped Revision-UUIDs, EXPORT_EVENT references, Log-Eintrag rows, all POs.
- **Projekthistorie endpoint** — `GET /history/project/{project_uuid}` — returns:
  - All project-scoped Decision-Event-UUIDs for `project_uuid` (release-gate confirmations, Pflichtfragen-Bestätigungen, exportstart actions, Konsistenzgruppe-verbindlich resolutions, Stilregel-Bestätigungen).
  - All EXPORT_EVENT rows for `project_uuid` (works-direct, not via snapshot lookup — the project owns its EXPORT_EVENTs directly).
  - **Excludes**: segment-scoped Decision Events, page-scoped Decision Events, block-scoped Decision Events, account-scoped Decision Events, Log-Eintrag rows, all POs except EXPORT_EVENT.
- **Ereignis-Log endpoint** — `GET /history/log` (with optional filtering by `scope_uuid`, `operation_type`, time range) — returns:
  - Log-Eintrag rows from the Log-Eintrag table.
  - **Excludes**: everything else. Log-Eintrag rows never appear in Segment-, Page-, or Projekthistorie endpoints.

The four endpoints share a strict invariant: **no two endpoints overlap in their result sets.** A given UUID — Revision-UUID, Decision-Event-UUID, EXPORT_EVENT-UUID, Log-ID — appears in exactly one endpoint's result, never in two. (EXPORT_EVENTs are an explicit dual-presence: they appear in Segmenthistorie as werkweite Referenz and in Projekthistorie as werks-eigene Entität. The structural marker `als_werkweite_referenz` distinguishes the two presentations.)

All four endpoints are pure-read. None writes. None has UI logic — the response shape is structured data; rendering is a separate concern (and explicitly out of scope for v1.0 per Baseline Delivery Plan §4).

## 3. Ticket sequence

Sprint-internal sequencing per DBB §10 Delivery-Reihenfolge, Schritt 10:

```
[Sprint 5 complete; EXPORT_EVENT rows being produced]
                             │
                             v
T-10.1.1 (get_pos_for_segment + get_export_events_for_segment via revision_snapshot[])
                             │
                             v
T-10.1.2 (get_page_history + get_project_history)
                             │
                             v
T-10.2.1 (four scope-separated backend endpoints)
                             │
                             v
[Sprint 6 complete; seven-sprint set complete]
```

Strictly sequential. T-10.2.1 wraps T-10.1.1 and T-10.1.2 into the four endpoints; without both inner functions complete, the endpoint surface is incomplete.

## 4. Mandatory tests

| Test ID | Ticket | Check content | Setup note |
|---|---|---|---|
| Get-Pos-For-Segment-Scope-Filter-Test | T-10.1.1 | `get_pos_for_segment` returns only POs with `scope_type = segment` AND `scope_uuid = satz_uuid` | Synthetic project with segment-, page-, project-, artefact-scoped POs; assert filter |
| Get-Pos-For-Segment-Page-Scoped-Excluded-Test | T-10.1.1 | Page-scoped POs (e.g., SCAN-PO) excluded from segment query | Synthetic project with SCAN-PO on segment's page; assert exclusion |
| Get-Pos-For-Segment-Read-Only-Test | T-10.1.1 | Function writes nothing — no Revision, no Decision Event | Run query; assert all tables unchanged |
| Get-Export-Events-For-Segment-Via-Snapshot-Test | T-10.1.1 | Lookup uses `revision_snapshot[]` exclusively; no segment-FK on EXPORT_EVENT row | Code review + DB introspection of EXPORT_EVENT schema |
| Get-Export-Events-For-Segment-Lineage-Aware-Test | T-10.1.1 | Lookup follows reactivated UUIDs across inactivation cycles | Synthetic case: Segment exported, inactivated, reactivated, exported again; assert both EXPORT_EVENTs returned |
| Get-Export-Events-Werkweite-Referenz-Marker-Test | T-10.1.1 | Each returned EXPORT_EVENT marked `als_werkweite_referenz = true` | Run query; assert marker present |
| Get-Export-Events-No-Direct-FK-Shortcut-Test | T-10.1.1 | EXPORT_EVENT schema has no segment-FK; query implementation does not use any such shortcut | Code review + schema introspection |
| Get-Page-History-Page-Scoped-Only-Test | T-10.1.2 | `get_page_history` returns only page-scoped Decision Events | Synthetic project with segment-, page-, project-scoped DEs on that page; assert page-only |
| Get-Page-History-No-Segment-Events-Test | T-10.1.2 | Decision Events about Segments on the Page are excluded | Synthetic case: lock change on Segment of Page; assert excluded |
| Get-Page-History-Read-Only-Test | T-10.1.2 | Function writes nothing | Run query; assert all tables unchanged |
| Get-Project-History-Project-Scoped-DEs-Test | T-10.1.2 | Returns project-scoped Decision Events | Synthetic project with project-scoped DEs (release-gate, Pflichtfragen, Stilregel-Bestätigungen) |
| Get-Project-History-Includes-Export-Events-Test | T-10.1.2 | Returns EXPORT_EVENTs for the project (direct via `project_uuid`, not via snapshot) | Synthetic project with EXPORT_EVENTs; assert presence |
| Get-Project-History-No-Account-Scoped-Test | T-10.1.2 | Account-scoped Decision Events (Stilprofil-Decisions per `decision_source = style_management`) are excluded — gebundener Resthinweis per Dokument 2 §2D | Synthetic project with account-scoped DEs; assert exclusion |
| Get-Project-History-No-Segment-Events-Test | T-10.1.2 | Segment-scoped, page-scoped, block-scoped Decision Events excluded | Synthetic case |
| Get-Project-History-No-Log-Test | T-10.1.2 | Log-Eintrag rows excluded | Synthetic case |
| Get-Project-History-No-Other-POs-Test | T-10.1.2 | Only EXPORT_EVENT included; other POs excluded | Synthetic case with mixed POs |
| Endpoint-Segmenthistorie-Vollstaendigkeit-Test | T-10.2.1 | Endpoint returns: segment-scoped Revisions, segment-scoped Decision Events, EXPORT_EVENT werkweite Referenzen, segment-scoped POs | Synthetic Segment with full history; assert all four kinds present |
| Endpoint-Segmenthistorie-Excludes-Page-Project-Account-Test | T-10.2.1 | Page-, project-, account-scoped Decision Events excluded | Synthetic case |
| Endpoint-Segmenthistorie-Excludes-Log-Test | T-10.2.1 | Log-Eintrag rows excluded | Synthetic case |
| Endpoint-Seitenhistorie-Page-Scoped-Only-Test | T-10.2.1 | Endpoint returns page-scoped Decision Events only | Synthetic case |
| Endpoint-Seitenhistorie-Excludes-Segment-Events-Test | T-10.2.1 | Segment-scoped Decision Events of Segments on the Page excluded | Synthetic case |
| Endpoint-Seitenhistorie-Excludes-Export-Events-Test | T-10.2.1 | EXPORT_EVENT references excluded from Seitenhistorie | Synthetic case |
| Endpoint-Seitenhistorie-Excludes-Pos-Test | T-10.2.1 | All POs excluded from Seitenhistorie | Synthetic case |
| Endpoint-Projekthistorie-Project-Scoped-DEs-And-Export-Events-Test | T-10.2.1 | Endpoint returns project-scoped Decision Events + EXPORT_EVENTs only | Synthetic case |
| Endpoint-Projekthistorie-Excludes-Account-Scoped-Test | T-10.2.1 | Account-scoped Decision Events excluded — gebundener Resthinweis per Dokument 2 §2D | Synthetic case |
| Endpoint-Projekthistorie-Excludes-Other-Scopes-Test | T-10.2.1 | Segment-, page-, block-scoped Decision Events excluded | Synthetic case |
| Endpoint-Ereignis-Log-Only-Logs-Test | T-10.2.1 | Endpoint returns Log-Eintrag rows only | Synthetic case |
| Endpoint-Ereignis-Log-No-Other-Histories-Test | T-10.2.1 | Log-Eintrag rows do not appear in any other endpoint's results | Cross-endpoint sweep |
| Endpoint-No-Cross-Pollination-Test | T-10.2.1 | Each UUID (Revision-UUID, Decision-Event-UUID, Log-ID) appears in exactly one endpoint's results (with the documented EXPORT_EVENT dual-presence exception) | Cross-endpoint sweep with synthetic comprehensive history |
| Endpoint-Read-Only-Test | T-10.2.1 | All four endpoints write nothing | Run all four; assert all tables unchanged |
| Endpoint-No-UI-Logic-Test | T-10.2.1 | Endpoints return structured data; no rendering, no formatting decisions | Code review of response shape |
| Endpoint-Chronological-Order-Test | T-10.2.1 | All endpoints return results ordered by `created_at` | Run with multi-event synthetic; assert order |
| Lineage-Event-Kein-DE-Regression-Test | T-10.2.1 | Sprint 1 regression: LINEAGE_EVENT-POs do not produce Decision Events; consequently the histories don't show lineage-matching as user decisions | Inject lineage operation; assert Segmenthistorie shows LINEAGE_EVENT-PO but no associated DE |

Invariants in scope this sprint: H-5 indirectly (via the lineage-aware EXPORT_EVENT lookup; UUID immutability is the precondition). No new H-XX exercised. (H-1, H-2, H-4, H-6, H-7 carry forward as Sprint 0–5 regressions; all must remain green.)

New regressions from this sprint onward:

- `get_pos_for_segment` returns POs of scope_types other than `segment`.
- `get_export_events_for_segment` implements via direct segment-FK on EXPORT_EVENT row.
- `get_export_events_for_segment` does not handle reactivated UUIDs (Sprint 1 lineage logic).
- `get_page_history` returns segment-scoped Decision Events.
- `get_project_history` returns account-scoped Decision Events (the gebundener Resthinweis is a future canon decision; introducing it silently here is canon drift).
- `get_project_history` returns Log-Eintrag rows.
- Segmenthistorie endpoint omits EXPORT_EVENT werkweite Referenzen.
- Seitenhistorie endpoint includes segment events.
- Projekthistorie endpoint includes account-scoped events.
- Ereignis-Log endpoint pollutes Segmenthistorie or Seitenhistorie.
- LINEAGE_EVENT-POs surface as Decision Events in any history (Sprint 1 R-S1-01 / DBB Abkürzung 8).

## 5. Definition of Done

Code:

- T-10.1.1, T-10.1.2, T-10.2.1 implemented, reviewed, and merged.
- Engineering Execution Baseline v1.0 DoD satisfied for every ticket.
- Stilfeature-Test-Familien (CR-3) row vacuously satisfied — no F2 or F3 tickets in this sprint.
- All Sprint 0–5 regression tests still green.

T-10.1.1 (segment-scoped readout):

- Get-Pos-For-Segment-Scope-Filter-Test green.
- Get-Pos-For-Segment-Page-Scoped-Excluded-Test green.
- Get-Pos-For-Segment-Read-Only-Test green.
- Get-Export-Events-For-Segment-Via-Snapshot-Test green.
- Get-Export-Events-For-Segment-Lineage-Aware-Test green.
- Get-Export-Events-Werkweite-Referenz-Marker-Test green.
- Get-Export-Events-No-Direct-FK-Shortcut-Test green.

T-10.1.2 (page-scoped and project-scoped readout):

- Get-Page-History-Page-Scoped-Only-Test green.
- Get-Page-History-No-Segment-Events-Test green.
- Get-Page-History-Read-Only-Test green.
- Get-Project-History-Project-Scoped-DEs-Test green.
- Get-Project-History-Includes-Export-Events-Test green.
- Get-Project-History-No-Account-Scoped-Test green.
- Get-Project-History-No-Segment-Events-Test green.
- Get-Project-History-No-Log-Test green.
- Get-Project-History-No-Other-POs-Test green.

T-10.2.1 (four endpoints):

- Endpoint-Segmenthistorie-Vollstaendigkeit-Test green.
- Endpoint-Segmenthistorie-Excludes-Page-Project-Account-Test green.
- Endpoint-Segmenthistorie-Excludes-Log-Test green.
- Endpoint-Seitenhistorie-Page-Scoped-Only-Test green.
- Endpoint-Seitenhistorie-Excludes-Segment-Events-Test green.
- Endpoint-Seitenhistorie-Excludes-Export-Events-Test green.
- Endpoint-Seitenhistorie-Excludes-Pos-Test green.
- Endpoint-Projekthistorie-Project-Scoped-DEs-And-Export-Events-Test green.
- Endpoint-Projekthistorie-Excludes-Account-Scoped-Test green.
- Endpoint-Projekthistorie-Excludes-Other-Scopes-Test green.
- Endpoint-Ereignis-Log-Only-Logs-Test green.
- Endpoint-Ereignis-Log-No-Other-Histories-Test green.
- Endpoint-No-Cross-Pollination-Test green.
- Endpoint-Read-Only-Test green.
- Endpoint-No-UI-Logic-Test green.
- Endpoint-Chronological-Order-Test green.
- Lineage-Event-Kein-DE-Regression-Test green.

End-to-end demonstrable at sprint end:

- For an arbitrary in-scope active Segment, calling `get_pos_for_segment` returns its OCR-PO, MANUAL_-POs, RULE_BINDING-POs, TRANSLATION-POs, and any LINEAGE_EVENT-POs that touched it — and nothing else.
- For the same Segment, calling `get_export_events_for_segment` returns every EXPORT_EVENT whose `revision_snapshot[]` ever contained any of the Segment's revision-UUIDs across its full lineage history (including reactivation cycles).
- For an arbitrary Page, calling `get_page_history` returns the Page's OCR-Review-Status resolutions and page-level user actions — and nothing about the Segments belonging to that Page.
- For an arbitrary Project, calling `get_project_history` returns the Project's release-gate confirmations, Pflichtfragen-Bestätigungen, exportstart actions, Konsistenzgruppe-verbindlich resolutions, Stilregel-Bestätigungen, and EXPORT_EVENTs — and nothing about Segments, Pages, or Account-level decisions.
- The Ereignis-Log endpoint returns Log-Eintrag rows in chronological order; querying any of the other three endpoints returns no Log-Eintrag rows.
- Cross-endpoint inspection of a synthetic comprehensive history confirms: no Revision-UUID, Decision-Event-UUID, or Log-ID appears in two endpoints (excepting the documented EXPORT_EVENT dual-presence with the `als_werkweite_referenz` marker).

## 6. Risks

R-S6-01 — `get_export_events_for_segment` implements via direct segment-FK on EXPORT_EVENT row instead of via `revision_snapshot[]` lookup. **Probability: medium. Severity: structural.** Consequence: the werkweites Scope-Modell of EXPORT_EVENT collapses; EXPORT_EVENT becomes a segment-scoped object instead of an artefact-scoped one; Sprint 5's atomicity discipline is undermined retroactively because the row has FK references that cannot be guaranteed atomic with artefact creation. (DBB ticket-level risk for T-10.1.1.) Review obligation: Get-Export-Events-For-Segment-Via-Snapshot-Test green; Get-Export-Events-No-Direct-FK-Shortcut-Test green; code review of EXPORT_EVENT schema confirms no segment-FK column.

R-S6-02 — `get_export_events_for_segment` does not handle Sprint 1 reactivation logic. Probability: medium. Consequence: a Segment that was inactivated, exported under that lineage chain, then reactivated and exported again, only sees one of the two EXPORT_EVENTs in the history; the user perceives a hole in the history that is actually a query bug. Review obligation: Get-Export-Events-For-Segment-Lineage-Aware-Test green; integration test exercises full inactivation-reactivation-re-export cycle.

R-S6-03 — `get_pos_for_segment` returns POs of scope_types other than segment. Probability: medium. Consequence: page-scoped POs (SCAN-PO) and project-scoped POs leak into the segment-level view; the user sees diagnostics from the wrong scope; downstream consumers (history endpoint) inherit the leak. Review obligation: Get-Pos-For-Segment-Scope-Filter-Test green; Get-Pos-For-Segment-Page-Scoped-Excluded-Test green.

R-S6-04 — `get_page_history` returns segment-scoped Decision Events. Probability: high. Consequence: the page history becomes a denormalized aggregation of all events in scope of the page; the canonical scope_type discipline collapses; downstream Seitenhistorie endpoint inherits the leak. (DBB ticket-level risk for T-10.1.2 — "Seitenhistorie zeigt alle Decision Events aller Segmente der Seite statt nur page-scoped".) Review obligation: Get-Page-History-Page-Scoped-Only-Test green; Get-Page-History-No-Segment-Events-Test green; code review of the query confirms the scope filter.

R-S6-05 — `get_project_history` returns account-scoped Decision Events. Probability: medium. Consequence: Stilprofil-Decisions with `decision_source = style_management` (account-bound per Dokument 1 §5.2) leak into project-scoped history; the gebundener Resthinweis per Dokument 2 §2D is silently pre-empted; later canonization of the account-scoped Lesepfad is constrained by an implementation choice that should have been deferred. Review obligation: Get-Project-History-No-Account-Scoped-Test green; Endpoint-Projekthistorie-Excludes-Account-Scoped-Test green; code review confirms scope_type filter excludes `account`.

R-S6-06 — Log-Eintrag rows leak into Segmenthistorie or Seitenhistorie endpoints. Probability: medium. Consequence: the strict scope_type discipline collapses at the endpoint surface; Log-IDs (which are operational events, not user decisions or text revisions) are presented as decision history; downstream consumers cannot reliably distinguish operational events from content events. (DBB ticket-level risk for T-10.2.1 — "Ereignis-Log-Einträge werden in Seitenhistorie eingeblendet 'für bessere Übersicht' – bricht Scope-Trennung".) Review obligation: Endpoint-Ereignis-Log-No-Other-Histories-Test green; Endpoint-No-Cross-Pollination-Test green.

R-S6-07 — Endpoints duplicate UUIDs across result sets without the documented `als_werkweite_referenz` distinction. Probability: medium. Consequence: a Decision-Event-UUID or Revision-UUID appears in two endpoints without explicit reason; downstream reasoning about uniqueness fails; UI logic (eventual) cannot deduplicate cleanly. Review obligation: Endpoint-No-Cross-Pollination-Test green; the only permitted dual-presence is EXPORT_EVENT in Segmenthistorie (as werkweite Referenz) and Projekthistorie (as werks-eigene Entität), and that case is structurally marked.

R-S6-08 — Endpoints contain UI logic. Probability: medium. Consequence: rendering decisions baked into the backend response shape; later UI work (out of scope for v1.0) becomes coupled to backend changes; API contract becomes brittle. Review obligation: Endpoint-No-UI-Logic-Test green; code review confirms response shape is structured data without rendering hints.

R-S6-09 — LINEAGE_EVENT-POs surface as Decision Events in histories. Probability: medium. Consequence: Sprint 1's R-S1-01 / DBB Abkürzung 8 risk re-emerges at the readout layer; lineage-matching events are presented as user decisions; the canonical separation between automatic system events and user decisions collapses. Review obligation: Lineage-Event-Kein-DE-Regression-Test green; this test is a Sprint-1 regression test promoted to a Sprint-6 mandatory test because the readout layer is where the leak would visibly manifest.

R-S6-10 — Read endpoints write to Log-Eintrag for the read operation itself, polluting the Ereignis-Log with read-trail entries. Probability: low–medium. Consequence: the Ereignis-Log fills with read-trace noise; legitimate operational events become hard to find; storage and query costs balloon. Review obligation: Endpoint-Read-Only-Test green; if read-logging is desired for audit purposes, it must use a separate audit log channel — not the canonical Log-Eintrag table consumed by the Ereignis-Log endpoint.

R-S6-11 — Endpoint chronological ordering broken — events returned in insertion order or random order. Probability: low. Consequence: timeline reconstruction is unreliable; downstream reasoning about cause-and-effect (e.g., "did the conflict resolution happen before or after the audit finding?") fails. Review obligation: Endpoint-Chronological-Order-Test green; code review confirms `ORDER BY created_at`.

## 7. Transition

This is the final sprint of the seven-sprint set. **No Sprint 7 follows.** The system at this point implements:

- All H-1 through H-7 invariants enforced via Guard.
- Full upload, OCR, lineage, OCR-review, lock, glossary, conflict-instance machinery.
- Release gate, translation pipeline with checkpoint and TRANSLATION-PO, RULE_BINDING, promotion Stufen 1–3.
- Audit Befund-Tabelle with A-01–D-03 severity classification.
- Consistency engine K-01–K-07 against passende Identitätstypen.
- Preflight Konfigurationsschicht + Gate-Prüfungsschicht with belegte Slots P-03, P-04, W-01, W-02, W-03, plus Hadith-Verifikationsstatus group.
- Atomic EXPORT_EVENT creation with `revision_snapshot[]` and `active_decision_event_uuids[]` per the positive allowlist.
- Four scope-separated history endpoints reading the full provenance graph.

What remains canonically open after Sprint 6:

- **Stilfeature backlog families F1, F3, F4, F5 (CR-3)** — deferred per Dokument C v1.1 §3 follow-on work. F2 closed in Sprints 2–3.
- **Application of bestätigte Stilregel into translation production** — deferred per DBB §7.5 / Dokument C v1.1 §3.
- **Account-scoped Decision-Event-Lesepfad in WS-10** — gebundener Resthinweis per Dokument 2 §2D; addressed in CR-3 follow-on work.
- **Decision-Event-Mapping decision_source × scope_type** — gebundener Resthinweis per Dokument 2 §2D; requires systematic, source-grounded consolidation before canonization.
- **scope_type-Enum-Erweiterung in CAB §B.1 and Dokument 1 §4.11** — entschieden per Dokument 2 §2D, schluss-audit (Paket 7) anchors the ALT→NEU change.
- **Heading-4/5/6-Abdeckungsgap in Formatvorlagen-Baseline v1.1 §7.2** — gebundener Resthinweis per Dokument 2 §2D; schluss-audit anchors the resolution.
- **L-24 Klasse-B-Generallogik konkrete Häufungsschwellenwerte** — live-measurement-dependent, parked.
- **OCR-Maximum-Modus, Schnittstellen 1–6 final canonization** — Block 3 working drafts; not part of v1.0 baseline.
- **Lernquellen-Asymmetrie partitioning granularity per Dokument 1 §4.13 / DBB §7.5** — explicitly open.
- **English Hadith-Strang K-4 R-3 detail rules** (Quellenangabe-Format, Transliteration, Fussnotenlogik, Verhältnis zum Stilfeature) — Werkbank, not v1.0 baseline.
- **Multi-language export paths beyond AR→DE** — deferred per Baseline Delivery Plan §4.

These are the load-bearing post-v1.0 work fronts. Each is canonically marked as held; none has been silently pre-empted by the seven-sprint set.

**Recommendation**: Before formal canonization of any of the seven sprint plans, review them as a complete set. Cross-sprint invariants (every Sprint-N Hard Gate references Sprint-0 H-test regressions; every Sprint-N risk register inherits a subset of Sprints 0..N-1 regressions; the test-ID space is canonical from DBB §KANONISCHE ZUORDNUNG and verbal where DBB doesn't specify) are easier to spot once everything is on the page than during sprint-by-sprint authoring.

## A. Hard Gates

HG-S6-1 — T-10.1.1 Get-Export-Events-For-Segment-Via-Snapshot-Test must be green before merge. Per DBB ticket-level risk for T-10.1.1, the segment-FK shortcut would retroactively undermine Sprint 5's EXPORT_EVENT atomicity discipline.

HG-S6-2 — T-10.1.1 Get-Export-Events-For-Segment-Lineage-Aware-Test must be green before merge. Sprint 1's reactivation logic is load-bearing for history correctness; queries that ignore reactivation produce silently incomplete history.

HG-S6-3 — T-10.1.2 Get-Page-History-No-Segment-Events-Test must be green before merge. Per DBB ticket-level risk for T-10.1.2, page history collapse to all-events-of-scope is the most-named failure mode.

HG-S6-4 — T-10.2.1 Endpoint-No-Cross-Pollination-Test must be green before merge. The strict scope-trennende invariant is the single canonical structural property of the four-endpoint surface; cross-pollination would collapse the entire scope discipline.

HG-S6-5 — T-10.2.1 Lineage-Event-Kein-DE-Regression-Test must be green before merge. Sprint 1's R-S1-01 risk is most visible here at the readout layer; promoting this to a Sprint 6 hard gate ensures regression coverage at the surface where leakage would manifest.

HG-S6-6 — All Sprint 0–5 H-test regressions remain green: T-H1-01, T-H1-02, T-H2-01, T-H2-02, T-H4-01, T-H4-02, T-H5-01, T-H5-02, T-H6-01, T-H7-01.

HG-S6-7 — Engineering Execution Baseline v1.0 DoD Stilfeature-Test-Familien (CR-3) row vacuously satisfied this sprint (no F2/F3 tickets present).

## B. What deliberately does not belong in this sprint

- Any new PO writes. The readout layer is read-only by design.
- Any UI rendering of histories. The four endpoints return structured data; rendering is a v1.0-out-of-scope concern per Baseline Delivery Plan §4.
- Account-scoped Decision-Event-Lesepfad in WS-10 — explicitly held as gebundener Resthinweis per Dokument 2 §2D. Adding it here would silently consume a future canon decision.
- `style_management`-source Decision Events in any history — deferred per CR-3.
- Decision-Event-Mapping decision_source × scope_type as a centrally-defined table — gebundener Resthinweis per Dokument 2 §2D.
- L-24 Klasse-B-Generallogik concrete Häufungsschwellenwerte — live-measurement-dependent, parked.
- Stilfeature backlog families F1, F3, F4, F5 (CR-3) — deferred per Dokument C v1.1 §3 follow-on work.
- Multi-export-target work (Adobe InDesign, Affinity Publisher) — deferred per Baseline Delivery Plan §4.
- Re-export of an existing EXPORT_EVENT from a stored snapshot — not in DBB v1.0; not in scope.
- Performance-oriented optimizations (caching, query plans, indexes beyond the canonical FKs) — Sprint 6 establishes correctness; performance work is post-v1.0.
- Logging of read-endpoint invocations into the canonical Log-Eintrag table consumed by the Ereignis-Log endpoint. If audit logging of reads is desired, it must use a separate channel.
- E-5 / Schnittstelle 5 live test package — parked.
- Real Shamela Ist-Aufnahme — parked.

*Waraq Sprint-6 / Provenance Readout + History Endpoints Delivery Plan v1.0 — End*