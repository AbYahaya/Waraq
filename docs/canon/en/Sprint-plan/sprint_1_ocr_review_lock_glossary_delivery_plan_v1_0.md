<!-- Authored: 2026-05-01. -->
<!-- Status: Authored to replace presumed-lost original v1.0 per option (c). -->
<!-- Anchored to: Baseline Delivery Plan v1.0 §2 (Sprint 1 scope description); DBB v1.0 §10 Delivery-Reihenfolge Schritte 4–5; DBB v1.0 ticket definitions T-4.2.1, T-4.2.2, T-4.3.1, T-5.1.1, T-5.1.2, T-5.2.1; DBB v1.0 §A Hard Delivery-Gates; Engineering Execution Baseline v1.0 (DoD); Core Architecture Baseline v1.0 (H-1, H-2, H-5, H-6). -->
<!-- Replaces: any presumed-lost prior "Waraq Sprint-1 / OCR Review + Lock + Glossary Delivery Plan v1.0" referenced in Dokument 2 §1 and Baseline Delivery Plan §1. -->
<!-- Structural template: ocr_text_export_v1_3.md §5 Sprint Plan Sprint-OCR v1.3. -->

# Waraq Sprint-1 / OCR Review + Lock + Glossary Delivery Plan v1.0

Status: Working basis. No coding release. No silent re-baselining.

## Start condition

Sprint 0 fully completed. All Sprint 0 mandatory tests green. INVARIANT-Guard demonstrably blocks all H-1 through H-7 violations. PROVENANCE-Kern operational. Block-UUIDs and Segment-UUIDs are being created and tracked correctly by the OCR pipeline (T-4.1.1). Error classes F-01 through F-09 are detected and persisted as `ocr_error_instance` rows (T-4.1.3). Decision-event service operational and strictly separated from revision and log services.

## 1. Scope

| Ticket | Designation |
|---|---|
| T-4.2.1 | Lineage: 1→1 matching and 1→0 inactivation; LINEAGE_EVENT-PO |
| T-4.2.2 | Lineage: 1→n aspaltung, n→1 zusammenführung, reactivation of inactive UUIDs |
| T-4.3.1 | OCR review status: Go/No-Go computation per page from F-class profile |
| T-5.1.1 | LOCK: set and release lock-flag; MANUAL_-PO; decision-event-UUID on lock change |
| T-5.1.2 | LOCK: Konflikt-Erkennung and persistent `conflict_instance` |
| T-5.2.1 | GLOSSARY: Konzept-ID lookup, entry CRUD, explicit "no entry" return |

Deliberately not in this sprint: release gate (T-6.1.1 — Sprint 2), translation pipeline (WS-7 — Sprints 2/3), RULE_BINDING in translation path (T-7.2.1 — Sprint 2 or 3), promotion pipeline (T-7.3.x — Sprint 2/3), audit (WS-8 — Sprint 3), consistency engine (T-8.2.1 — Sprint 4), preflight (WS-9 — Sprints 4/5), export artefact (T-9.2.1 — Sprint 5), provenance readout (WS-10 — Sprint 6), Stilfeature backlog layer (CR-3, all sprints deferred). No UI for any module. No calibration values for severity aggregation thresholds — must be configurable, not pre-set.

## 2. Sprint target state

**T-4.2.1 — Lineage 1→1 and 1→0**
- On page replacement or re-segmentation, 1→1 matching preserves existing `satz_uuid`s.
- Segments that disappear from the new layout: `active = true → false`. UUID never deleted.
- LINEAGE_EVENT-PO created via PROVENANCE-Kern with `scope_type = segment`, `automatisch: true`. No decision-event-UUID — these are automatic system-matching events, not user decisions.
- Log-Eintrag for every lineage transition via EVENTING.
- No UUID deletion under any code path.

**T-4.2.2 — Lineage 1→n, n→1, reactivation**
- 1→n aspaltung: source `satz_uuid` referenced in LINEAGE_EVENT-PO `herkunft_uuid[]`; new daughter UUIDs in `ziel_uuid[]`. Source UUID → `active = false`.
- n→1 zusammenführung: both source `satz_uuid`s referenced; both → `active = false`. Single new UUID in `ziel_uuid[]`.
- Reactivation: before any new UUID issuance, the LINEAGE service queries inactive UUIDs in scope and reactivates (`active = false → true`) when re-segmentation produces a Segment that plausibly matches a previously inactive one. Plausibility heuristic: text overlap above a configurable threshold AND positional proximity within the same Block; configurable, never hard-coded.
- No decision-event-UUID for any automatic lineage operation.
- Reactivation produces a LINEAGE_EVENT-PO with both old and new UUIDs in `herkunft_uuid[]` / `ziel_uuid[]` so downstream history queries see the continuity.

**T-4.3.1 — OCR review status per page**
- Page-level `ocr_status` derived from the `ocr_error_instance` rows attached to that page and its blocks.
- Page with at least one open `ocr_error_instance` of severity `kritisch` → `ocr_status = no_go`.
- Page with no `kritisch`, but at least one open instance of severity `hoch` or `mittel` → `ocr_status = go_with_warning`.
- Page with all `ocr_error_instance` rows resolved (or none present) → `ocr_status = go`.
- Aggregation logic reads severity weights from a configurable table, not hard-coded constants.
- `ocr_status = go` is never set automatically when prior state was `no_go` — explicit user-resolution action is required, written as a Decision Event with `scope_type = page`.
- State machine: `ausstehend → in_review → go | go_with_warning | no_go`. Re-entry into `in_review` is permitted; transition logged via EVENTING.

**T-5.1.1 — LOCK set and release**
- `set_lock(satz_uuid, level)` writes `lock_flag` from `none` to `manual_local` or `manual_editorial`.
- `release_lock(satz_uuid)` from `manual_local → none` requires no dialog. `manual_editorial → none` requires explicit confirmation context (callers without that context fail).
- Each set or release issues a decision-event-UUID via T-1.4.2 (`scope_type = segment`).
- MANUAL_-PO created via PROVENANCE-Kern after each lock state change.
- No code path performs automatic release of any `lock_flag`.

**T-5.1.2 — Konflikt-Erkennung and persistent `conflict_instance`**
- `detect_conflict(satz_uuid, rule_source)` invoked whenever an automatic rule (terminology, glossary, future style profile) attempts to act on a Segment with `lock_flag ≠ none`, or whenever the rule itself contradicts another active rule on the Segment.
- Every detected conflict creates a `conflict_instance` row with `state = offen`, `conflict_uuid`, `satz_uuid` FK, `rule_source`, `conflict_type` enum (`glossar_vs_sperrflag | terminologie_vs_sperrflag | konzept_vs_konzept | ...`), `detected_at` timestamp.
- `conflict_instance` is persisted to its own table — **not** in memory, not in the Segment table, not as a transient field of the rule application.
- No decision-event-UUID at detection time — that field stays null until resolution.
- Three resolution paths, exposed to the caller as the only valid transitions out of `state = offen`:
  - `lokale_ausnahme` — local exception: the rule does not apply to this Segment; rule itself unchanged.
  - `glossar_anpassen` — glossary entry adjusted via T-5.2.1; new entry version applies to all Segments.
  - `sperrflag_aufheben` — lock flag released via T-5.1.1 (subject to the confirmation rule there).
- On resolution: `state = offen → aufgelöst`, `resolution_type` set, `decision_event_uuid` set (created via T-1.4.2 with `scope_type = segment`), `resolved_at` timestamp set. The pre-resolution `conflict_instance` row is **not** mutated in any other way; the row is now historical evidence.
- `conflict_instance` is **not** a PO — it is not written via PROVENANCE-Kern. The Decision Event tied to its resolution is the provenance anchor.
- Open `conflict_instance` rows are queryable per Segment, per Page, per Project, per `rule_source`. The query path is exposed to the upcoming preflight gates (Sprint 4) and to the future history endpoints (Sprint 6) — but no consumers are wired in this sprint.
- Server restart, session timeout, or process crash never causes a `conflict_instance` row to disappear. The row is persisted at detection.

**T-5.2.1 — GLOSSARY service**
- `lookup(surface_form)` returns either a Konzept-ID or an explicit sentinel value `NO_ENTRY`. Never null. Never silent.
- `get_entry(concept_id)` returns the full Konzept-ID record.
- `create_entry()` and `update_entry()` write decision-event-UUIDs via T-1.4.2 (`scope_type = project` for project-bound entries, `scope_type = account` for account-bound entries — `binding_level` field on the Konzept-ID determines which).
- Glossary entries do not auto-overwrite locked Segments. Any application of a glossary entry against a locked Segment routes through T-5.1.2 conflict detection.
- Glossary entries are never auto-created from external sources, OCR runs, or AI suggestions.
- `lookup()` is the sole entrypoint for surface-form-to-concept resolution. No code path may bypass it via direct table query.

## 3. Ticket sequence

Sprint-internal sequencing per DBB §10 Delivery-Reihenfolge, Schritte 4 (continuation) and 5:

```
T-4.2.1 ─→ T-4.2.2          (parallel to T-4.1.x already complete in Sprint 0)
                  │
                  v
T-4.3.1 (after T-4.1.3 — gate for WS-5 work)
                  │
                  v
T-5.1.1 ║ T-5.2.1 (parallel, both after T-4.3.1)
   │
   v
T-5.1.2 (after T-5.1.1)
                  │
                  v
[Sprint 1 complete; common gate for T-6.1.1 in Sprint 2: T-5.1.2 ∧ T-5.2.1 green]
```

Parallel windows: T-5.1.1 and T-5.2.1 run in parallel after T-4.3.1 is green. T-4.2.1 and T-4.2.2 may overlap with the early phase of T-4.3.1 but T-4.2.2 must complete before T-5.1.2 (since lineage reactivation interacts with conflict-instance carryover across re-segmentation).

## 4. Mandatory tests

| Test ID | Ticket | Check content | Setup note |
|---|---|---|---|
| T-H5-01 | T-4.2.1, T-4.2.2 | UUID immutability holds across all lineage operations | Issue UUID, run lineage transitions, attempt UUID mutation → error |
| T-H5-02 | T-4.2.1 | Inactive UUID remains queryable; not deleted | 1→0 transition, query inactive UUID, assert record present |
| LINEAGE-1zu1-Test | T-4.2.1 | Existing `satz_uuid` preserved on re-segmentation when text content matches | Synthetic re-segmentation case; assert UUID stability |
| LINEAGE-1zu0-Inaktivierungs-Test | T-4.2.1 | Disappearing Segment marked `active = false`, UUID retained | Remove segment from layout; assert active flag |
| LINEAGE-1zun-Aufspaltungs-Test | T-4.2.2 | Source `satz_uuid` referenced in `herkunft_uuid[]`; daughters in `ziel_uuid[]`; source inactivated | Synthetic aspaltung case |
| LINEAGE-nzu1-Zusammenfuehrungs-Test | T-4.2.2 | Both source `satz_uuid`s in `herkunft_uuid[]`; single target in `ziel_uuid[]`; both sources inactivated | Synthetic zusammenführung case |
| LINEAGE-Reaktivierungs-Test | T-4.2.2 | Re-segmentation that produces a Segment matching a previously inactive UUID reactivates that UUID rather than issuing a new one | Inactivate UUID; re-create matching segment; assert reactivation |
| LINEAGE-Kein-Decision-Event-Automatisch-Test | T-4.2.1, T-4.2.2 | Automatic lineage operations create no decision-event-UUID | Run all four lineage types; assert decision_events delta = 0 |
| OCR-Review-Status-Kritisch-No-Go-Test | T-4.3.1 | Page with one open kritisch-class instance → `ocr_status = no_go` | F-01 unresolved; assert no_go |
| OCR-Review-Status-Mittel-Go-With-Warning-Test | T-4.3.1 | Page with no kritisch but open hoch/mittel → `go_with_warning` | F-04 unresolved, no kritisch; assert go_with_warning |
| OCR-Review-Status-Alle-Aufgeloest-Go-Test | T-4.3.1 | All `ocr_error_instance` rows resolved → `go` (only after explicit user resolution event) | Resolve all; user action; assert go + Decision Event |
| OCR-Review-Status-Schwellenwert-Konfigurations-Test | T-4.3.1 | Severity weights read from configurable table, not hard-coded | Change config; rerun aggregation; assert effect |
| OCR-Review-Status-Kein-Auto-Go-Test | T-4.3.1 | `no_go → go` transition requires explicit user Decision Event with `scope_type = page` | Resolve all error instances without user action; assert state stays no_go |
| T-H1-01 | T-5.1.1 | Automatic write on `lock_flag = manual_local` blocked (regression + new path) | Set lock; attempt automatic update via TRANSLATE-side mock |
| T-H1-02 | T-5.1.1 | Automatic write on `lock_flag = manual_editorial` blocked (regression + new path) | Same setup, level 2 |
| LOCK-Set-Decision-Event-Test | T-5.1.1 | `set_lock` issues a decision-event-UUID with `scope_type = segment` | Call `set_lock`; assert decision_events delta = 1 |
| LOCK-Release-Manual-Editorial-Confirmation-Test | T-5.1.1 | `release_lock` from `manual_editorial` without confirmation context → error; with confirmation → permitted | Both call paths |
| LOCK-Manual-PO-Provenance-Test | T-5.1.1 | MANUAL_-PO created via PROVENANCE-Kern after each lock change; not direct insert | Code review + integration test |
| T-H2-01 | T-5.1.2 | Terminology application against locked Segment → `conflict_instance` row created with `state = offen`; not silently resolved | Pre-set lock + terminology rule; trigger application |
| T-H2-02 | T-5.1.2 | No silent resolution path: every transition `offen → aufgelöst` writes a Decision Event | Code review + integration sweep |
| T-H6-01 | T-5.1.2 | Three resolution options exposed; no fourth code path resolves a `conflict_instance` | Attempt resolution via internal API outside the three paths → error |
| Conflict-Instance-Persistenz-Test | T-5.1.2 | `conflict_instance` row exists in the database immediately after detection — not in memory | Detect conflict; query DB without restarting; assert row present |
| Conflict-Instance-Server-Restart-Test | T-5.1.2 | After process restart, all open `conflict_instance` rows from before the restart remain `state = offen` and queryable | Detect conflict, restart process, query → assert preserved |
| Conflict-Instance-Drei-Aufloesungsoptionen-Test | T-5.1.2 | All three resolution paths (`lokale_ausnahme`, `glossar_anpassen`, `sperrflag_aufheben`) implemented and reachable | Three integration cases |
| Conflict-Instance-Decision-Event-Bei-Aufloesung-Test | T-5.1.2 | Decision-event-UUID set only at resolution, not at detection | Detect; assert decision_event_uuid is null. Resolve; assert decision_event_uuid is set |
| Conflict-Instance-Kein-Decision-Event-Bei-Erkennung-Test | T-5.1.2 | At detection time, decision_events table delta = 0 | Detect 5 conflicts; assert decision_events unchanged |
| T-KE-01 | T-5.2.1 | `lookup(surface_form)` returns explicit Konzept-ID or `NO_ENTRY`, never null | Various surface forms including misses |
| Glossar-Lookup-Explicit-No-Entry-Test | T-5.2.1 | Miss returns `NO_ENTRY` sentinel, not null | Lookup unknown surface form |
| Glossar-Eintrag-Aenderung-Decision-Event-Test | T-5.2.1 | `create_entry` and `update_entry` issue decision-event-UUIDs with correct `scope_type` per `binding_level` | Two integration cases (project + account) |
| Glossar-Kein-Auto-Ueberschreiben-Gesperrt-Test | T-5.2.1 | Glossary entry application against locked Segment routes through T-5.1.2, never bypasses lock | Pre-set lock; apply entry; assert `conflict_instance` row created |
| Glossar-Kein-Auto-Erzeugung-Test | T-5.2.1 | Glossary entries cannot be created from external sources; only via explicit `create_entry` call with user context | Code review + sweep of all entrypoints |

Invariants in scope this sprint: H-1, H-2, H-5, H-6. (H-4, H-7 carry forward as Sprint 0 regressions; both must remain green.)

New regressions from this sprint onward (these states must never reappear in any later sprint):

- Lineage operation creates a decision-event-UUID for an automatic match.
- Re-segmentation issues a new `satz_uuid` for content that matches a previously inactive UUID, instead of reactivating.
- `ocr_status = go` is set automatically without an explicit user Decision Event.
- F-class severity aggregation is hard-coded.
- `set_lock` does not issue a decision-event-UUID.
- `release_lock` from `manual_editorial` succeeds without confirmation context.
- `conflict_instance` row exists only in memory.
- `conflict_instance` row is created with a decision-event-UUID at detection time.
- Glossary `lookup` returns null on miss.
- Glossary entry overwrites a locked Segment without routing through `conflict_instance`.

## 5. Definition of Done

Code:

- T-4.2.1, T-4.2.2, T-4.3.1, T-5.1.1, T-5.1.2, T-5.2.1 implemented, reviewed, and merged.
- Engineering Execution Baseline v1.0 DoD satisfied for every ticket. Stilfeature-Test-Familien (CR-3) row vacuously satisfied — no F2 or F3 tickets in this sprint.
- All Sprint 0 regression tests still green.

Lineage:

- T-H5-01 green.
- T-H5-02 green.
- LINEAGE-1zu1-Test green.
- LINEAGE-1zu0-Inaktivierungs-Test green.
- LINEAGE-1zun-Aufspaltungs-Test green.
- LINEAGE-nzu1-Zusammenfuehrungs-Test green.
- LINEAGE-Reaktivierungs-Test green.
- LINEAGE-Kein-Decision-Event-Automatisch-Test green.

OCR review status:

- OCR-Review-Status-Kritisch-No-Go-Test green.
- OCR-Review-Status-Mittel-Go-With-Warning-Test green.
- OCR-Review-Status-Alle-Aufgeloest-Go-Test green.
- OCR-Review-Status-Schwellenwert-Konfigurations-Test green.
- OCR-Review-Status-Kein-Auto-Go-Test green.

Lock:

- T-H1-01 green.
- T-H1-02 green.
- LOCK-Set-Decision-Event-Test green.
- LOCK-Release-Manual-Editorial-Confirmation-Test green.
- LOCK-Manual-PO-Provenance-Test green.

Conflict instance:

- T-H2-01 green.
- T-H2-02 green.
- T-H6-01 green.
- Conflict-Instance-Persistenz-Test green.
- Conflict-Instance-Server-Restart-Test green.
- Conflict-Instance-Drei-Aufloesungsoptionen-Test green.
- Conflict-Instance-Decision-Event-Bei-Aufloesung-Test green.
- Conflict-Instance-Kein-Decision-Event-Bei-Erkennung-Test green.

Glossary:

- T-KE-01 green.
- Glossar-Lookup-Explicit-No-Entry-Test green.
- Glossar-Eintrag-Aenderung-Decision-Event-Test green.
- Glossar-Kein-Auto-Ueberschreiben-Gesperrt-Test green.
- Glossar-Kein-Auto-Erzeugung-Test green.

End-to-end demonstrable at sprint end:

- Re-uploading a document with revised page layout preserves Segment-UUIDs where content survives, inactivates UUIDs where content disappears, and reactivates inactive UUIDs where content reappears — all without issuing decision-event-UUIDs.
- A page with an unresolved F-06 (Qurʾān-related kritisch class) reports `ocr_status = no_go` and stays no_go until a user resolution action.
- Setting a lock on a Segment, then attempting an automatic terminology overwrite from a (mocked) translation-side caller, produces a `conflict_instance` with `state = offen` and no silent resolution.
- Restarting the application process after detecting a conflict preserves the `conflict_instance` row.
- Glossary lookup of an unknown surface form returns `NO_ENTRY`, not null; an attempt to create a glossary entry from outside the explicit user-context entrypoint fails.

## 6. Risks

R-S1-01 — Lineage matching emits decision-event-UUIDs "because matching is important". Probability: high. Consequence: decision-event table flooded with technical events; user decisions become indistinguishable from system matching events; downstream history queries (Sprint 6) return useless noise. Review obligation: LINEAGE-Kein-Decision-Event-Automatisch-Test green; code review confirms no `create_decision_event` call inside the LINEAGE service. (DBB Abkürzung 8 explicitly names this failure mode.)

R-S1-02 — Reactivation logic missing in T-4.2.2. Probability: high. Consequence: every re-segmentation issues new `satz_uuid`s; revision history breaks at re-segmentation boundaries; downstream provenance queries (Sprint 6) cannot connect pre-resegmentation revisions to post-resegmentation Segments. Review obligation: LINEAGE-Reaktivierungs-Test green; code review confirms inactive-UUID lookup precedes any `new_uuid()` call in lineage paths.

R-S1-03 — Inactive Segment treated as "new" on next layout pass. Probability: medium. Consequence: same as R-S1-02 but milder — false reactivation gaps rather than total loss. Review obligation: LINEAGE-1zu0-Inaktivierungs-Test combined with LINEAGE-Reaktivierungs-Test exercises the round-trip.

R-S1-04 — F-class severity aggregation hard-coded. Probability: high. Consequence: Sprint 4 (T-8.2.1 consistency engine, T-9.1.x preflight) inherits an inflexible threshold model; calibration after Gold-Corpus-Tests becomes a code change rather than a config change. Review obligation: OCR-Review-Status-Schwellenwert-Konfigurations-Test green; code review confirms severity weights read from a config table.

R-S1-05 — `set_lock` implemented without decision-event-UUID. Probability: medium. Consequence: lock-flag history is invisible to provenance queries; Sprint 6 history endpoints cannot reconstruct who locked what when. Review obligation: LOCK-Set-Decision-Event-Test green; code review confirms `create_decision_event` is invoked on every lock change.

R-S1-06 — `conflict_instance` held only in memory. **Probability: high. Severity: critical.** Consequence: server restart, session timeout, or worker crash erases all open conflicts; H-6 enforcement collapses across restart boundaries; locked Segments become silently overwritable in subsequent operations. (DBB §A names this as one of the unumgehbar hard gates and DBB Abkürzung 11 names this as a typical false shortcut.) Review obligation: Conflict-Instance-Persistenz-Test green AND Conflict-Instance-Server-Restart-Test green. Both are blocking.

R-S1-07 — `conflict_instance` created with decision-event-UUID at detection time. Probability: medium. Consequence: detection events become indistinguishable from resolution events; the temporal sequence of conflict-then-resolution is lost in the audit trail. Review obligation: Conflict-Instance-Decision-Event-Bei-Aufloesung-Test green; Conflict-Instance-Kein-Decision-Event-Bei-Erkennung-Test green.

R-S1-08 — Glossary `lookup` returns null on miss. Probability: medium. Consequence: callers conflate "no entry" with "lookup failure" or with a permission denial; missing terminology entries go undetected. Review obligation: Glossar-Lookup-Explicit-No-Entry-Test green; T-KE-01 green; code review confirms a `NO_ENTRY` sentinel exists.

R-S1-09 — Glossary entry overwrites locked Segment "because terminology has precedence per architecture". Probability: high. Consequence: H-6 silently violated; manual corrections silently overwritten; lock-flag enforcement compromised. (DBB Abkürzung 6 names this exact failure mode.) Review obligation: Glossar-Kein-Auto-Ueberschreiben-Gesperrt-Test green; T-H2-01 green; code review traces every glossary application path through `detect_conflict`.

R-S1-10 — Glossary entries auto-created from OCR or AI sources "to bootstrap the glossary". Probability: medium. Consequence: unverified terminology enters the canonical glossary; downstream consistency checks (Sprint 4) treat unverified entries as authoritative. Review obligation: Glossar-Kein-Auto-Erzeugung-Test green; code review of all glossary entrypoints.

## 7. Transition to Sprint 2

Sprint 2 (Release Gate + Translation Core) presupposes:

- T-4.3.1 green: Sprint 2's T-6.1.1 release gate consumes per-page `ocr_status` to decide blocking.
- T-5.1.1 green: Sprint 2's T-7.1.1 translation job reads `lock_flag` to skip locked Segments.
- T-5.1.2 green: Sprint 2's T-7.2.1 RULE_BINDING (if scoped to Sprint 2) creates `conflict_instance` rows on glossary-vs-lock collisions.
- T-5.2.1 green: Sprint 2's T-7.2.1 (if scoped to Sprint 2) consumes `lookup` and `get_entry`.

The common gate for Sprint 2's T-6.1.1 is `T-5.1.2 ∧ T-5.2.1` per DBB §A. T-6.1.1 cannot start until both are green.

T-7.2.1 placement decision: per Baseline Delivery Plan §2 and DBB §10, T-7.2.1 is optional in Sprint 2 and conditional in Sprint 3 (placed in Sprint 3 if not in Sprint 2). Recommend placing T-7.2.1 in Sprint 2 alongside T-7.1.1 / T-7.1.2 if Sprint 2 capacity permits — it shortens the path between glossary readiness and rule-binding test surface. Final placement decision is yours.

T-7.3.1 placement decision: same shape as T-7.2.1. Optional in Sprint 2; if placed in Sprint 2, then T-7.3.2 follows in Sprint 3.

Sprint 2 may begin only after every Sprint 1 mandatory test in §4 is green and the gate predicate `T-5.1.2 ∧ T-5.2.1` is satisfied.

## A. Hard Gates

HG-S1-1 — T-4.3.1 must be green before any WS-5 ticket starts. Per DBB §A, T-4.3.1 (OCR-Review-Status) → Gate für Schritt 5. The lock-and-glossary work assumes per-page review state is computable.

HG-S1-2 — T-5.1.2 Conflict-Instance-Persistenz-Test AND Conflict-Instance-Server-Restart-Test must be green before sprint completion. Per DBB §A, T-5.1.2 is unumgehbar — without persistent `conflict_instance`, H-6 enforcement is unreliable. **Neither test may be skipped, mocked, or deferred.**

HG-S1-3 — Common gate for Sprint 2: `T-5.1.2 ∧ T-5.2.1` both green. Per DBB §A, this is the gate to T-6.1.1. Sprint 2 may not start until this predicate holds.

HG-S1-4 — T-1.2.2 H-test family (Sprint 0) regression remains green throughout Sprint 1. Any regression of T-H1-01, T-H1-02, T-H2-01, T-H2-02, T-H4-01, T-H4-02, T-H5-01, T-H5-02, T-H6-01, T-H7-01 blocks Sprint 1 merge.

HG-S1-5 — Engineering Execution Baseline v1.0 DoD must be satisfied for every ticket — including the Stilfeature-Test-Familien (CR-3) row, vacuously satisfied this sprint (no F2/F3 tickets present).

HG-S1-6 — `conflict_instance` is **not** a PO. Per T-5.1.2 acceptance, `conflict_instance` is its own table, not written via PROVENANCE-Kern. The Decision Event tied to its resolution is the provenance anchor. Code review must confirm `create_po` is never called with `po_type = CONFLICT_INSTANCE` or any equivalent.

## B. What deliberately does not belong in this sprint

- Release gate / Freigabeschranke logic — T-6.1.1 (Sprint 2). Sprint 1 produces the inputs (per-page `ocr_status`, lock state, conflict-instance state) that T-6.1.1 will consume; the gate itself is not built here.
- Translation pipeline — WS-7 (Sprints 2–3). No translation job, no TRANSLATION-PO, no chunked translation logic.
- RULE_BINDING in translation path — T-7.2.1 (Sprint 2 or 3). The glossary service is built; its enforcement inside the translation pipeline is not.
- Promotion pipeline — T-7.3.1, T-7.3.2 (Sprint 2/3 conditional).
- Audit — WS-8 (Sprint 3). No Befund-Tabelle in this sprint; the F-class profile from Sprint 0 + the OCR review status from this sprint are not yet routed into audit findings.
- Consistency engine K-01 through K-07 — T-8.2.1 (Sprint 4).
- Preflight gates P-03, P-04, W-01–W-03, Hadith-Verifikationsstatus group — T-9.1.x (Sprint 4/5).
- Export artefact and EXPORT_EVENT — T-9.2.1 (Sprint 5).
- Provenance readout, history endpoints — WS-10 (Sprint 6).
- Stilfeature backlog layer F1–F5 (CR-3) — deferred per Dokument C v1.1 §3 follow-on work.
- UI for any module. The lock-flag set/release, conflict resolution chooser, glossary CRUD, OCR-review-status surfacing are all backend-only this sprint.
- Calibration values: severity aggregation thresholds in T-4.3.1, reactivation plausibility threshold in T-4.2.2 — both must be configurable. Concrete values are post-Gold-Corpus-Tests work per Baseline Delivery Plan §4.
- E-5 / Schnittstelle 5 live test package — parked.
- Real Shamela Ist-Aufnahme — parked.

*Waraq Sprint-1 / OCR Review + Lock + Glossary Delivery Plan v1.0 — End*