<!-- Authored: 2026-05-01. -->
<!-- Status: Authored to replace presumed-lost original v1.0 per option (c). -->
<!-- Anchored to: Baseline Delivery Plan v1.0 §2 (Sprint 2 scope description, including optional T-7.2.1 and T-7.3.1); DBB v1.0 §10 Delivery-Reihenfolge Schritte 6–7; DBB v1.0 ticket definitions T-6.1.1, T-7.1.1, T-7.1.2, T-7.2.1, T-7.3.1; DBB v1.0 §A Hard Delivery-Gates; DBB v1.0 §7 Stilfeature-Strang Backlog-Schicht (CR-3); Engineering Execution Baseline v1.0 (DoD); Core Architecture Baseline v1.0 (H-1, H-2, H-6, H-7); Dokument 1 §4.13 (Lernquellen-Asymmetrie). -->
<!-- Replaces: any presumed-lost prior "Waraq Sprint-2 / Release Gate + Translation Core Delivery Plan v1.0" referenced in Dokument 2 §1 and Baseline Delivery Plan §1. -->
<!-- Scoping decision: T-7.2.1 (RULE_BINDING) and T-7.3.1 (Promotion Stufen 1–2) placed in this sprint per user direction "place in Sprint 2 if capacity permits". T-7.3.2 (Promotion Stufe 3) thereby follows in Sprint 3. -->
<!-- Structural template: ocr_text_export_v1_3.md §5 Sprint Plan Sprint-OCR v1.3. -->

# Waraq Sprint-2 / Release Gate + Translation Core Delivery Plan v1.0

Status: Working basis. No coding release. No silent re-baselining.

## Start condition

Sprint 0 and Sprint 1 fully completed. All Sprint 0 and Sprint 1 mandatory tests green. Common gate predicate `T-5.1.2 ∧ T-5.2.1` satisfied per DBB §A. Per-page `ocr_status` is being correctly computed (T-4.3.1). Persistent `conflict_instance` table operational with all three resolution paths exposed (T-5.1.2). Glossary service with explicit `NO_ENTRY` sentinel operational (T-5.2.1). Lock-flag set/release with mandatory decision-event-UUIDs operational (T-5.1.1). Lineage matching for all four types (1→1, 1→0, 1→n, n→1) plus reactivation operational (T-4.2.1, T-4.2.2).

## 1. Scope

| Ticket | Designation |
|---|---|
| T-6.1.1 | Freigabeschranke / release gate: five release conditions checked; no automatic translation start |
| T-7.1.1 | TRANSLATE: translation job with Checkpoint, context buffer in `resume_state`, lock-flag check |
| T-7.1.2 | TRANSLATE: TRANSLATION-PO and revision-UUID on text change |
| T-7.2.1 | RULE_BINDING: glossary binding inside translation pipeline; conflict-instance route |
| T-7.3.1 | Promotion pipeline: observation (Stufe 1) and pattern candidate (Stufe 2) |

**Conditional placement.** T-7.2.1 and T-7.3.1 are placed in this sprint per the project decision recorded in this file's header. Per Baseline Delivery Plan §2 and DBB §10, both are optional in Sprint 2 and conditional in Sprint 3. With T-7.2.1 placed here, Sprint 3 does not need to repeat it. With T-7.3.1 placed here, T-7.3.2 (Stufe 3) follows in Sprint 3. If sprint capacity proves inadequate during execution, T-7.3.1 is the first ticket to defer (it is non-critical-path per DBB and the only F2-family ticket in this sprint, so deferring it isolates the F2-substantive obligation cleanly to Sprint 3).

Deliberately not in this sprint: promotion Stufe 3 / T-7.3.2 (Sprint 3, follows T-7.3.1 from this sprint), audit Befund-Tabelle and A-01–D-03 regelprüfung (T-8.1.1, T-8.1.2 — Sprint 3), consistency engine K-01–K-07 (T-8.2.1 — Sprint 4), preflight gates (T-9.1.x — Sprint 4/5), export artefact and EXPORT_EVENT (T-9.2.1 — Sprint 5), provenance readout (WS-10 — Sprint 6). Stilfeature backlog families F1, F3, F4, F5 (CR-3) — deferred per Dokument C v1.1 §3 follow-on work; F2 (Promotion) is partially exercised here through T-7.3.1 only, leaving the Lernquellen-Asymmetrie granularity per DBB §7.5 explicitly open. No UI for any module. No calibration values: confidence thresholds, promotion thresholds, severity weights all configurable, never pre-set.

## 2. Sprint target state

**T-6.1.1 — Release gate**
- All five release conditions per ITB D.2 checked on every gate evaluation:
  1. No page has `ocr_status = no_go` with unresolved kritisch-class `ocr_error_instance` rows.
  2. F-06-QR error class (Qurʾān-recognition class) has no unresolved instance anywhere in the project.
  3. All open `conflict_instance` rows for the project are resolved or accepted.
  4. Glossary integrity check passes (no orphaned references, no entries pointing to inactive Konzept-IDs).
  5. Project metadata required for translation start is complete.
- Gate result: `übersetzungsreif | übersetzbar_mit_warnung | blockiert`.
- `übersetzbar_mit_warnung` requires an explicit user confirmation event recorded as a Decision Event with `scope_type = project` and `decision_type = freigabe_mit_warnung`.
- `übersetzungsreif` is a state, not an action: it does not by itself start translation. Translation is started only by an explicit user action that creates its own Decision Event (`scope_type = project`, `decision_type = uebersetzungsstart`).
- Gate evaluation reads live state on every invocation. No cached gate result.
- State machine: `nicht_erreichbar → freigabeschranken_prüfung → übersetzungsreif | übersetzbar_mit_warnung | blockiert`.
- Log-Eintrag for every gate evaluation, regardless of outcome.

**T-7.1.1 — Translation job**
- Job type `translation` with checkpoint after every chunk.
- `resume_state` JSONB carries: chunk index, current Segment, full upstream context buffer (the running translation context that conditions per-Segment translation), accumulated terminology bindings, accumulated style anchors. Serialization is deterministic and round-trips through deserialization without information loss.
- Before every Segment write, `lock_flag` is read live (not from a cached batch fetch). Segments with `lock_flag ∈ {manual_local, manual_editorial}` are skipped — translation never overwrites locked Segments.
- Skipped Segments are recorded in the job's chunk metadata so the user-facing job summary at the end can report which Segments were intentionally bypassed.
- Resumption picks up at the last persisted checkpoint with the context buffer fully reconstructed. Translation produced after resumption uses the same context as if no interruption had occurred.
- Job state machine consumes Sprint 0 T-2.1.1 transitions: `pending → aktiv → deferred | pausiert → abgeschlossen | fehlgeschlagen`.
- No TRANSLATION-PO in this ticket — that is T-7.1.2's responsibility.

**T-7.1.2 — TRANSLATION-PO and revision-UUID**
- After every Segment translation, TRANSLATION-PO created via PROVENANCE-Kern with `po_type = TRANSLATION`, `scope_type = segment`, `scope_uuid = satz_uuid`, payload containing the engine identifier, the Segment input, the Segment output, the active terminology bindings consumed, the active style anchors consumed.
- Revision-UUID issued only when Segment output text differs from the prior `current_rev_uuid` text. Identical output produces no revision-UUID.
- On resumption with output that differs from the prior result for the same Segment: new revision-UUID issued. The prior revision is not overwritten — it remains in the revision history.
- No revision-UUID for translation-pipeline check operations (e.g., a dry-run pass that does not produce an emitted Segment translation). H-4 enforced.
- TRANSLATION-PO is written via PROVENANCE-Kern only — no direct table insert from inside the translation service.

**T-7.2.1 — RULE_BINDING in translation pipeline**
- Inside the translation pipeline, every Segment translation pass invokes the GLOSSARY service (`lookup`, `get_entry`) to resolve terminology. Resolved entries are applied to the Segment output before TRANSLATION-PO is written.
- When a glossary entry is applied to a Segment with `lock_flag ∈ {manual_local, manual_editorial}`: the conflict-instance pathway from T-5.1.2 is invoked. The translation does **not** silently apply the glossary entry to the locked Segment; the conflict-instance row is created with `state = offen` and the translation pipeline records the Segment as awaiting conflict resolution.
- When a glossary entry is applied to an unlocked Segment cleanly: RULE_BINDING-PO created via PROVENANCE-Kern with `po_type = RULE_BINDING`, `scope_type = segment`, `scope_uuid = satz_uuid`, payload containing the Konzept-ID, the surface form bound, the application context.
- When a Segment was previously a `conflict_instance` resolved via `lokale_ausnahme`: the RULE_BINDING-PO carries `ausnahme_flag = true` and `decision_event_uuid` referencing the original resolution.
- Glossary entries against locked Segments never silently win. H-2 and H-6 both enforced through this pathway.
- The translation pipeline does not bypass the GLOSSARY service via direct database queries. `lookup` is the sole entrypoint.

**T-7.3.1 — Promotion pipeline Stufen 1–2**
- Stufe 1 (Beobachtung): when a user manually corrects a translated Segment (a manual edit that produces a new revision via T-1.4.1 with `change_source = manual`), the correction is recorded as a local observation. The observation is attached to the manual revision and stored in a service-internal table (not a PO, not a Decision Event). Each observation captures the source segment, the prior translation, the user-corrected translation, the active terminology bindings at the time of correction.
- Stufe 2 (Musterkandidat): the system passively aggregates observations. When a recurring pattern crosses a configurable threshold of observation count (per source phrase, per terminology binding, per syntactic structure — granularity per DBB §7.5 deliberately left open as later refinement work), the pattern is registered as a Musterkandidat. Registration writes a Log-Eintrag via EVENTING; it does **not** write a Decision Event and does **not** create a glossary entry.
- A Musterkandidat is never auto-applied. Translation passes for new Segments do not consult Musterkandidaten — only confirmed glossary entries (T-5.2.1) are consulted.
- A Musterkandidat is offered to the user through a system surface that enumerates current candidates. Confirming or rejecting is a Sprint 3 concern (T-7.3.2). In this sprint, the candidate exists, is queryable, but is inert with respect to translation production.
- Auto-promotion from Stufe 2 to Stufe 3 is structurally impossible: the only path is an explicit user action invoked through T-7.3.2 (next sprint). H-7 enforced.
- Lernquellen-Asymmetrie per Dokument 1 §4.13 (and DBB §7.5): the granularity at which observations are partitioned across the five learning-source classes (bestätigte Referenzsätze, manuelle Nutzerregeln, akzeptierte KI-Vorschläge, korrigierte KI-Vorschläge, ignorierte KI-Vorschläge) is **not decided in this ticket**. The observation table records source-class metadata so a later refinement can partition without migration. No automatic upgrade path between classes is implemented.

## 3. Ticket sequence

Sprint-internal sequencing per DBB §10 Delivery-Reihenfolge, Schritte 6–7:

```
[Sprint 1 complete; common gate T-5.1.2 ∧ T-5.2.1 green]
                             │
                             v
                          T-6.1.1 (release gate)
                             │
                             v
                          T-7.1.1 (translation job + checkpoint)
                             │
                             v
                          T-7.1.2 (TRANSLATION-PO + revision-UUID)
                             │
              ┌──────────────┼──────────────┐
              v                             v
         T-7.2.1                       T-7.3.1
       (RULE_BINDING)              (Promotion 1–2)
              │                             │
              v                             v
         [Sprint 2 complete; T-7.3.2 enabled in Sprint 3]
```

Parallel windows: T-7.2.1 and T-7.3.1 may run in parallel after T-7.1.1 is green. Both depend on T-7.1.1 (the translation job machinery) but neither depends on the other.

T-7.2.1 may begin after T-7.1.1 is green; it does not require T-7.1.2 to complete first because RULE_BINDING-PO writes use the PROVENANCE-Kern directly and do not depend on TRANSLATION-PO format. However, integration testing of T-7.2.1 produces TRANSLATION-PO rows that must be present, so T-7.2.1's Definition of Done depends on T-7.1.2 being complete.

T-7.3.1 may begin after T-7.1.1 is green. Its observation source is the manual revisions produced through T-1.4.1, which exist independently of T-7.1.2.

## 4. Mandatory tests

| Test ID | Ticket | Check content | Setup note |
|---|---|---|---|
| Gate-Test-Blockiert-No-Go-Test | T-6.1.1 | Page with `ocr_status = no_go` (kritisch open) → gate result `blockiert` | Synthetic project with one F-01 unresolved |
| Gate-Test-F06-QR-Blockierung-Test | T-6.1.1 | Open F-06-QR anywhere in project → gate result `blockiert` | Project with F-06-QR unresolved on one page |
| Gate-Test-Offene-Conflict-Instance-Blockierung-Test | T-6.1.1 | Open `conflict_instance` row → gate result `blockiert` | Inject open conflict-instance from T-5.1.2 |
| Gate-Test-Glossar-Orphan-Blockierung-Test | T-6.1.1 | Glossary integrity violation (orphaned reference, inactive Konzept-ID still referenced) → `blockiert` | Inject orphan |
| Gate-Test-Alles-Erfuellt-Uebersetzungsreif-Test | T-6.1.1 | All five conditions met → `übersetzungsreif` | Clean project setup |
| Gate-Test-Mit-Warnung-Erfordert-Bestaetigung-Test | T-6.1.1 | Non-kritisch open instance + explicit user confirmation → `übersetzbar_mit_warnung`; without confirmation → stays `blockiert` | Two integration cases |
| Gate-Test-Kein-Auto-Translation-Start-Test | T-6.1.1 | `übersetzungsreif` does not by itself trigger translation; only an explicit user `uebersetzungsstart` Decision Event triggers T-7.1.1 | Reach übersetzungsreif; assert no T-7.1.1 job started; trigger user action; assert job started |
| Gate-Test-Live-State-Test | T-6.1.1 | Two consecutive gate evaluations across a state-changing action read fresh state, not cached | Evaluate; resolve a conflict; re-evaluate; assert different result |
| Gate-Test-Log-Eintrag-Immer-Test | T-6.1.1 | Every gate evaluation produces a Log-Eintrag via EVENTING, regardless of outcome | Three evaluations under three outcomes; assert three log entries |
| T-H1-01 | T-7.1.1 | Translation pass on Segment with `lock_flag = manual_local` → Segment skipped, not overwritten | Pre-set lock; run translation; assert Segment unchanged |
| T-H1-02 | T-7.1.1 | Translation pass on Segment with `lock_flag = manual_editorial` → Segment skipped | Same setup, level 2 |
| T-REC-03 | T-7.1.1 | Resumption deserializes context buffer correctly; post-resumption translation matches uninterrupted translation | Synthetic mid-job interruption with recorded context; assert byte-identical context after deserialization |
| Translation-Job-Lock-Live-Read-Test | T-7.1.1 | Lock-flag is read live before each Segment write, not from a job-start batch fetch | Set lock mid-job; assert subsequent Segments are skipped |
| Translation-Job-Skipped-Segments-Reported-Test | T-7.1.1 | Job summary at completion enumerates skipped (locked) Segments | Run job with N locked + M unlocked; assert summary lists N |
| T-REC-04 | T-7.1.2 | Resumption produces a Segment translation that differs from prior result → new revision-UUID issued; prior revision retained | Synthetic case: identical-input mid-job restart with mocked nondeterministic engine output |
| TRANSLATION-PO-Anlage-Test | T-7.1.2 | TRANSLATION-PO created after every emitted Segment translation; payload contains engine, input, output, terminology bindings, style anchors | – |
| TRANSLATION-PO-Identische-Ausgabe-Keine-Revision-Test | T-7.1.2 | Translation pass that produces identical output to prior `current_rev_uuid` text → no new revision-UUID | – |
| TRANSLATION-PO-Pruefung-Keine-Revision-Test | T-7.1.2 | Translation dry-run / check operation produces no revision-UUID; H-4 regression | Code review + integration test |
| TRANSLATION-PO-Provenance-Kern-Test | T-7.1.2 | TRANSLATION-PO written via PROVENANCE-Kern, never via direct DB insert | Code review |
| RULE-BINDING-PO-Sauber-Test | T-7.2.1 | Glossary entry applied to unlocked Segment → RULE_BINDING-PO created with correct payload | – |
| RULE-BINDING-Konflikt-Mit-Sperrflag-Conflict-Instance-Test | T-7.2.1 | Glossary entry against locked Segment → `conflict_instance` row with `state = offen`; no silent application | Pre-set lock + glossary entry |
| RULE-BINDING-Lokale-Ausnahme-Provenance-Test | T-7.2.1 | After conflict resolved as `lokale_ausnahme`, subsequent translation creates RULE_BINDING-PO with `ausnahme_flag = true` and the resolution `decision_event_uuid` | Resolve conflict; rerun pass |
| RULE-BINDING-Lookup-Sole-Entrypoint-Test | T-7.2.1 | Translation pipeline never bypasses GLOSSARY `lookup` via direct DB query | Code review of all glossary-touching paths |
| T-H2-01 | T-7.2.1 | Glossary vs lock-flag conflict produces conflict-instance, not silent application (regression + new path) | Pre-set lock + entry; trigger translation pipeline |
| T-KE-01 | T-7.2.1 | Glossary lookup integration in translation pipeline: explicit Konzept-ID for hits, `NO_ENTRY` for misses, never null | Various surface forms |
| T-H6-01 | T-7.2.1 | Glossary application against locked Segment never silently resolved (regression) | Code review + integration sweep |
| Promotion-Stufe1-Beobachtung-Test | T-7.3.1 | Manual Segment correction via T-1.4.1 (`change_source = manual`) creates an observation row attached to the revision | Manual correction; assert observation written |
| Promotion-Stufe2-Musterkandidat-Test | T-7.3.1 | After observation count crosses configurable threshold for a recurring pattern, a Musterkandidat is registered with a Log-Eintrag | Inject N matching observations; assert candidate registered + log entry |
| Promotion-Kein-Decision-Event-Bei-Beobachtung-Test | T-7.3.1 | Observation creation produces no Decision Event | Manual correction; assert decision_events delta = 0 |
| Promotion-Kein-Glossar-Eintrag-Bei-Kandidat-Test | T-7.3.1 | Musterkandidat registration does not create a glossary entry | Inject pattern; assert glossary unchanged |
| Promotion-Kandidat-Inert-In-Translation-Test | T-7.3.1 | Translation pass for new Segments does not consult Musterkandidaten — only confirmed glossary entries | Inject candidate matching new Segment; run translation; assert candidate not applied |
| Promotion-Schwellenwert-Konfigurations-Test | T-7.3.1 | Pattern threshold is read from configurable table, not hard-coded | Change config; rerun; assert effect |
| T-H7-01 | T-7.3.1 | Auto-promotion from Stufe 2 to Stufe 3 is structurally impossible — no code path exists outside T-7.3.2 | Code review + attempted internal API call → error |
| Promotion-Lernquellen-Source-Class-Recorded-Test | T-7.3.1 | Observation row records source-class metadata per Dokument 1 §4.13 (which of the five classes the observation came from) without yet partitioning behaviour | Manual correction; assert source_class field populated |

Invariants in scope this sprint: H-1, H-2, H-4, H-6, H-7. (H-5 carries forward as Sprint 0/1 regression; must remain green.)

New regressions from this sprint onward:

- Release gate auto-triggers translation start when `übersetzungsreif`.
- Release gate uses cached state instead of live query.
- Translation context buffer not in `resume_state`.
- Translation pipeline writes a Segment with `lock_flag ≠ none`.
- Lock-flag read once at job start instead of live before each Segment write.
- Translation pipeline produces revision-UUID for identical output.
- TRANSLATION-PO written without going through PROVENANCE-Kern.
- Glossary entry applied to locked Segment without routing through `conflict_instance`.
- Translation pipeline bypasses GLOSSARY `lookup` via direct DB query.
- Manual correction does not create observation row.
- Musterkandidat applied to translation production.
- Auto-promotion path Stufe 2 → Stufe 3 exists.
- Promotion threshold hard-coded.
- Observation row missing source-class metadata.

## 5. Definition of Done

Code:

- T-6.1.1, T-7.1.1, T-7.1.2, T-7.2.1, T-7.3.1 implemented, reviewed, and merged.
- Engineering Execution Baseline v1.0 DoD satisfied for every ticket.
- **Stilfeature-Test-Familien (CR-3) row substantively satisfied for T-7.3.1** (F2 family). The CR-2-defined F2 test families exercising the Lernquellen-Asymmetrie per Dokument 1 §4.13 must be present. Granularity per DBB §7.5 deliberately left open — but the source-class recording infrastructure is in place.
- All Sprint 0 and Sprint 1 regression tests still green.

Release gate:

- Gate-Test-Blockiert-No-Go-Test green.
- Gate-Test-F06-QR-Blockierung-Test green.
- Gate-Test-Offene-Conflict-Instance-Blockierung-Test green.
- Gate-Test-Glossar-Orphan-Blockierung-Test green.
- Gate-Test-Alles-Erfuellt-Uebersetzungsreif-Test green.
- Gate-Test-Mit-Warnung-Erfordert-Bestaetigung-Test green.
- Gate-Test-Kein-Auto-Translation-Start-Test green.
- Gate-Test-Live-State-Test green.
- Gate-Test-Log-Eintrag-Immer-Test green.

Translation job:

- T-H1-01 green.
- T-H1-02 green.
- T-REC-03 green.
- Translation-Job-Lock-Live-Read-Test green.
- Translation-Job-Skipped-Segments-Reported-Test green.

TRANSLATION-PO and revision-UUID:

- T-REC-04 green.
- TRANSLATION-PO-Anlage-Test green.
- TRANSLATION-PO-Identische-Ausgabe-Keine-Revision-Test green.
- TRANSLATION-PO-Pruefung-Keine-Revision-Test green.
- TRANSLATION-PO-Provenance-Kern-Test green.

RULE_BINDING:

- RULE-BINDING-PO-Sauber-Test green.
- RULE-BINDING-Konflikt-Mit-Sperrflag-Conflict-Instance-Test green.
- RULE-BINDING-Lokale-Ausnahme-Provenance-Test green.
- RULE-BINDING-Lookup-Sole-Entrypoint-Test green.
- T-H2-01 green.
- T-KE-01 green.
- T-H6-01 green.

Promotion Stufen 1–2:

- Promotion-Stufe1-Beobachtung-Test green.
- Promotion-Stufe2-Musterkandidat-Test green.
- Promotion-Kein-Decision-Event-Bei-Beobachtung-Test green.
- Promotion-Kein-Glossar-Eintrag-Bei-Kandidat-Test green.
- Promotion-Kandidat-Inert-In-Translation-Test green.
- Promotion-Schwellenwert-Konfigurations-Test green.
- T-H7-01 green.
- Promotion-Lernquellen-Source-Class-Recorded-Test green.

End-to-end demonstrable at sprint end:

- A project with all five release conditions met reaches `übersetzungsreif`. Translation does not start until the user explicitly issues the `uebersetzungsstart` action.
- A translation job runs through a multi-page project, skips locked Segments, persists checkpoints, produces TRANSLATION-PO rows for every emitted translation, and on mid-job interruption resumes with full context fidelity.
- A glossary entry that applies cleanly to an unlocked Segment produces a RULE_BINDING-PO. A glossary entry that would apply to a locked Segment instead produces an open `conflict_instance`, and the translation job records the Segment as awaiting resolution.
- A user manually correcting a translated Segment produces a Stufe-1 observation. After enough recurring corrections matching the same pattern, a Stufe-2 Musterkandidat is registered. Subsequent translations do not consume the Musterkandidat — they produce the same engine-default translation as before.

## 6. Risks

R-S2-01 — Release gate auto-triggers translation start when last `ocr_status` flips to `go`. Probability: high. Consequence: translation begins without active user release; ITB D.2 condition (no automatic start) is silently violated; the Decision Event for `uebersetzungsstart` is forged by the system rather than recorded from a user action. (DBB §A names the gate as unumgehbar; DBB Abkürzung 5 names this exact failure mode.) Review obligation: Gate-Test-Kein-Auto-Translation-Start-Test green; code review confirms there is no system-internal trigger between `übersetzungsreif` and T-7.1.1 job creation.

R-S2-02 — Release gate uses cached evaluation result. Probability: medium. Consequence: gate evaluates once, then continues to report `übersetzungsreif` even after a state-changing event (new conflict, new error class, glossary edit) should have moved it back to `blockiert`. Review obligation: Gate-Test-Live-State-Test green; code review confirms each invocation reads live tables.

R-S2-03 — Translation context buffer not serialized into `resume_state`. Probability: high. Consequence: resumption produces translations that differ from pre-interruption translation because the upstream context is reconstructed wrong; translation quality regresses silently across resumption boundaries. Review obligation: T-REC-03 green; code review of the resume_state schema confirms context fields present.

R-S2-04 — Lock-flag read once at job start, cached for the rest of the job. Probability: high. Consequence: a Segment locked partway through translation gets overwritten because the cache says it was unlocked when the job started; H-1 silently violated. Review obligation: Translation-Job-Lock-Live-Read-Test green; code review confirms `lock_flag` is fetched immediately before each write.

R-S2-05 — Every translation output produces revision-UUID regardless of identity with prior. Probability: high. Consequence: revisions table polluted with no-op entries; downstream history queries (Sprint 6) return endless duplicates; storage and query-time costs balloon. Review obligation: TRANSLATION-PO-Identische-Ausgabe-Keine-Revision-Test green; T-H4-01 regression remains green.

R-S2-06 — TRANSLATION-PO written via direct DB insert from inside the translation service. Probability: medium. Consequence: PO immutability and atomic-creation guarantees from PROVENANCE-Kern are bypassed; partial PO rows possible after mid-write crash. Review obligation: TRANSLATION-PO-Provenance-Kern-Test green; code review traces every TRANSLATION-PO write to `create_po`.

R-S2-07 — Glossary "wins silently" against locked Segment because "terminology has precedence per architecture". Probability: high. Consequence: H-2 and H-6 simultaneously violated; the conflict-instance pathway from Sprint 1 is bypassed; manual corrections silently overwritten by glossary application. (DBB Abkürzung 6 names this exact failure mode.) Review obligation: RULE-BINDING-Konflikt-Mit-Sperrflag-Conflict-Instance-Test green; T-H2-01 green; T-H6-01 green; code review traces every glossary-application path through `detect_conflict`.

R-S2-08 — Translation pipeline bypasses `lookup` via direct glossary DB query. Probability: medium. Consequence: terminology applied without going through the GLOSSARY service entrypoint; the `NO_ENTRY` sentinel discipline from Sprint 1 collapses; downstream code paths see null where the service contract requires the sentinel. Review obligation: RULE-BINDING-Lookup-Sole-Entrypoint-Test green; code review of all glossary-touching paths.

R-S2-09 — Auto-promotion from Stufe 2 to Stufe 3 implemented "when the Musterkandidat is obviously correct". Probability: medium. Consequence: H-7 silently violated; user confirmation step bypassed; learned style rules enter the system without nutzer-bestätigung. (T-7.3.1 ticket-level risk in DBB.) Review obligation: T-H7-01 green; Promotion-Kandidat-Inert-In-Translation-Test green; code review confirms there is no path from Stufe 2 to Stufe 3 outside T-7.3.2 (which is in Sprint 3).

R-S2-10 — Musterkandidat threshold hard-coded. Probability: high. Consequence: Sprint 3+ calibration of promotion sensitivity becomes a code change; Gold-Corpus-Tests cannot adjust the threshold post-hoc. Review obligation: Promotion-Schwellenwert-Konfigurations-Test green; code review confirms threshold reads from config.

R-S2-11 — Observation row missing source-class metadata for Lernquellen-Asymmetrie. Probability: medium. Consequence: future refinement (per DBB §7.5) requires migration of historical observations to add the field; partitioning behaviour cannot be retrofitted without data loss. Review obligation: Promotion-Lernquellen-Source-Class-Recorded-Test green; code review confirms source-class column exists and is populated on every observation.

R-S2-12 — Stufe-1 observation creates a Decision Event "because it represents a user decision". Probability: medium. Consequence: decision-event table flooded with implicit observation events; H-4 boundary between text-changing decisions and recordkeeping smudges. Review obligation: Promotion-Kein-Decision-Event-Bei-Beobachtung-Test green; code review traces all observation creation paths.

## 7. Transition to Sprint 3

Sprint 3 (Audit + Rule-Binding Completion) presupposes:

- T-7.1.2 green: Sprint 3's audit Befund-Tabelle (T-8.1.1) takes Segment-level inputs that are observable only after TRANSLATION-PO rows exist in the system.
- T-7.2.1 green (placed in this sprint per scoping decision): Sprint 3's audit can assume RULE_BINDING-PO rows are being produced. With T-7.2.1 here, Sprint 3 does not need to repeat it — but the conditional language in DBB §10 means a future replanning could move audit ahead of T-7.2.1 without breaking. For this canonization run, T-7.2.1 is in Sprint 2.
- T-7.3.1 green (placed in this sprint per scoping decision): Sprint 3's T-7.3.2 (Promotion Stufe 3) consumes Musterkandidaten registered here.

Sprint 3 mandatory entry: T-7.3.2 (since T-7.3.1 was placed here, T-7.3.2 follows in Sprint 3 per the conditional language). T-8.1.1 and T-8.1.2 form the bulk of Sprint 3 alongside T-7.3.2.

Sprint 3 may begin only after every Sprint 2 mandatory test in §4 is green.

## A. Hard Gates

HG-S2-1 — Common gate from Sprint 1 (`T-5.1.2 ∧ T-5.2.1` green) is a precondition for starting T-6.1.1. Per DBB §A this gate is unumgehbar.

HG-S2-2 — T-6.1.1 must be merged before any T-7.x ticket is started. Per DBB §A, T-6.1.1 → Gate für Schritt 7. Translation infrastructure cannot be built ahead of the release gate.

HG-S2-3 — T-7.1.1 lock-flag live-read test (Translation-Job-Lock-Live-Read-Test) must be green before T-7.1.2 merges. A translation job that overwrites locked Segments because of a stale lock-flag cache is a silent H-1 violation that downstream provenance cannot detect.

HG-S2-4 — T-REC-03 green is a precondition for T-7.1.2 merge. Without verified context-buffer round-trip, any TRANSLATION-PO produced after a resumption has incorrect provenance.

HG-S2-5 — T-7.2.1 conflict-instance routing test (RULE-BINDING-Konflikt-Mit-Sperrflag-Conflict-Instance-Test) must be green before merge. Per DBB Abkürzung 6, the silent glossary-vs-lock failure is a top-tier risk.

HG-S2-6 — T-7.3.1 H-7 test (T-H7-01) and inert-in-translation test (Promotion-Kandidat-Inert-In-Translation-Test) must both be green before merge. Per DBB §A, H-7 is unumgehbar; auto-promotion from Stufe 2 must be structurally impossible.

HG-S2-7 — Engineering Execution Baseline v1.0 DoD Stilfeature-Test-Familien (CR-3) row is **substantively** in scope for T-7.3.1 (F2 family). The CR-2-defined F2 test families must be present, not vacuously satisfied. (First sprint where CR-3 row is non-vacuous.)

HG-S2-8 — All Sprint 0 and Sprint 1 H-test regressions remain green: T-H1-01, T-H1-02, T-H2-01, T-H2-02, T-H4-01, T-H4-02, T-H5-01, T-H5-02, T-H6-01, T-H7-01.

## B. What deliberately does not belong in this sprint

- Promotion Stufe 3 (Bestätigung als Stilregel) — T-7.3.2 (Sprint 3). This sprint produces Musterkandidaten; their confirmation pathway is built next.
- Audit Befund-Tabelle and A-01–D-03 regelprüfung — T-8.1.1, T-8.1.2 (Sprint 3).
- Consistency engine K-01–K-07 — T-8.2.1 (Sprint 4).
- Preflight gates P-03, P-04, W-01–W-03, Hadith-Verifikationsstatus group — T-9.1.x (Sprint 4/5).
- Export artefact and EXPORT_EVENT — T-9.2.1 (Sprint 5).
- Provenance readout, history endpoints — WS-10 (Sprint 6).
- Stilfeature backlog families F1, F3, F4, F5 (CR-3) — deferred per Dokument C v1.1 §3 follow-on work. Only F2 is exercised here through T-7.3.1.
- Lernquellen-Asymmetrie partitioning granularity per DBB §7.5 — explicitly open. The source-class metadata is recorded but not yet used to differentiate behaviour across the five learning-source classes.
- Stilprofil-Versionierung, Stilbeleg, Phänomenfeld-Enum (Dokument B v1.2) — not in scope; deferred per Dokument C v1.1 §3.
- Audit integration of style-feature violations into A-01–D-03 — deferred per Dokument C v1.1 §3.
- UI for any module. Release gate dialog, translation progress display, conflict-resolution chooser, Musterkandidat surfacing are all backend-only this sprint.
- Calibration values: severity weights, promotion thresholds, conflict-resolution timeouts — all configurable, never pre-set.
- E-5 / Schnittstelle 5 live test package — parked.
- Real Shamela Ist-Aufnahme — parked.
- Multi-language support beyond AR→DE primary translation — Schnittstelle 3 is engaged in this sprint only insofar as T-7.1.1 produces translations; the AR→EN strang per §4.16 K-4 R-3 and the §4.15 Qurʾān-Stellen-Ausklammerung are not tested or wired in this sprint. Both remain canonical but inert here.

*Waraq Sprint-2 / Release Gate + Translation Core Delivery Plan v1.0 — End*