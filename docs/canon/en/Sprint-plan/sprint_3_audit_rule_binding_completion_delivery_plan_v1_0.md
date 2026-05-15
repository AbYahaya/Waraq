<!-- Authored: 2026-05-01. -->
<!-- Status: Authored to replace presumed-lost original v1.0 per option (c). -->
<!-- Anchored to: Baseline Delivery Plan v1.0 §2 (Sprint 3 scope description, conditional content); DBB v1.0 §10 Delivery-Reihenfolge Schritte 7 (continuation) and 8; DBB v1.0 ticket definitions T-8.1.1, T-8.1.2, T-7.3.2; DBB v1.0 §A Hard Delivery-Gates; DBB v1.0 §7 Stilfeature-Strang Backlog-Schicht (CR-3); Engineering Execution Baseline v1.0 (DoD); Implementation Translation Baseline v1.0 (A-01–D-03 audit structure); Core Architecture Baseline v1.0 (H-4, H-7); Dokument 1 §4.6 (Audit-Severitätsklassen). -->
<!-- Replaces: any presumed-lost prior "Waraq Sprint-3 / Audit + Rule-Binding Completion Delivery Plan v1.0" referenced in Dokument 2 §1 and Baseline Delivery Plan §1. -->
<!-- Scoping decision: T-7.2.1 was placed in Sprint 2; T-7.3.1 was placed in Sprint 2. T-7.3.2 (Promotion Stufe 3) follows here. T-7.2.1 is therefore not in this sprint. -->
<!-- Structural template: ocr_text_export_v1_3.md §5 Sprint Plan Sprint-OCR v1.3. -->

# Waraq Sprint-3 / Audit + Rule-Binding Completion Delivery Plan v1.0

Status: Working basis. No coding release. No silent re-baselining.

## Start condition

Sprints 0–2 fully completed. All Sprint 0–2 mandatory tests green. Translation pipeline is producing TRANSLATION-PO rows (T-7.1.2). RULE_BINDING-PO rows are being produced for clean glossary applications and `conflict_instance` rows are being created for glossary-vs-lock collisions (T-7.2.1). Promotion Stufe-1 observations and Stufe-2 Musterkandidaten are being recorded (T-7.3.1) but remain inert with respect to translation production. Release gate operational with no automatic translation start (T-6.1.1).

## 1. Scope

| Ticket | Designation |
|---|---|
| T-8.1.1 | AUDIT: Befund-Tabelle and audit-run logic; no corrections, no revision-UUIDs |
| T-8.1.2 | AUDIT: Regelprüfung A-01 through D-03 with severity classification |
| T-7.3.2 | Promotion pipeline Stufe 3: user confirmation of Musterkandidat as bestätigte Stilregel |

Deliberately not in this sprint: consistency engine K-01–K-07 (T-8.2.1 — Sprint 4), preflight gates and gate-prüfungsschicht (T-9.1.x — Sprint 4/5), export artefact (T-9.2.1 — Sprint 5), provenance readout (WS-10 — Sprint 6). T-7.2.1 already in Sprint 2; not repeated. Stilfeature backlog families F1, F3, F4, F5 (CR-3) — deferred per Dokument C v1.1 §3 follow-on work; F2 (Promotion) completes here through T-7.3.2. No UI for any module. No calibration values: severity weight tables, audit-run scheduling cadences, promotion confirmation thresholds — all configurable, never pre-set.

This is a 3-ticket sprint by design. The smaller scope creates slack to absorb any Sprint-2 carry-over (notably T-7.3.1 if it slipped) without rescheduling subsequent sprints.

## 2. Sprint target state

**T-8.1.1 — Audit Befund-Tabelle and audit-run logic**
- Befund-Tabelle implemented as its own table, separate from Revision and Decision Event. Schema: `befund_uuid`, `satz_uuid` FK, `regelkennung` (e.g., A-01, B-02, C-03, D-01), `verstossklasse` enum, `schweregrad` enum (`kritisch | hoch | mittel`), `auflösungsstatus` enum (`offen | aufgelöst | quittiert`), `detected_at`, `resolved_at?`, `resolution_decision_event_uuid?` FK.
- Audit-run is a job (job_type = audit) consuming Sprint 0 T-2.1.1 state machine.
- Audit-run reads Segment text and TRANSLATION-PO payloads to produce findings; never writes to Revision, never writes to Segment, never writes to TRANSLATION-PO.
- Each audit-run produces a Log-Eintrag via EVENTING with run start, end, finding count by severity.
- No revision-UUID is issued by any code path inside the AUDIT module. H-4 enforced.
- No automatic correction of findings. The Befund row is the output; resolution is a separate concern.
- Befund rows are immutable in their detection content (`regelkennung`, `verstossklasse`, `schweregrad`, `detected_at` cannot be mutated). Only the resolution fields (`auflösungsstatus`, `resolved_at`, `resolution_decision_event_uuid`) may be set on transition `offen → aufgelöst | quittiert`.
- AUDIT does not share a schema with REVISION via FK that suggests audit findings are text revisions.

**T-8.1.2 — Regelprüfung A-01 through D-03**
- All 12 audit rules implemented as discrete check functions:
  - A-01 through A-03: Glossary / Konzept-ID adherence rules.
  - B-01 through B-03: Terminology consistency rules.
  - C-01 through C-03: Critical content-integrity rules (e.g., Qurʾān/Hadith handling violations, religious-formula violations).
  - D-01 through D-03: Style and formatting rules.
- Severity assignment per Dokument 1 §4.6:
  - C-class violations → `schweregrad = kritisch` → `verstossklasse = blockierend`. These block the eventual export gate (P-03 in Sprint 4).
  - A-class violations → `schweregrad = hoch` → `verstossklasse = pflichthinweis`. These require explicit per-finding user resolution before export (P-04 in Sprint 4/5).
  - B-class violations → `schweregrad = hoch` → `verstossklasse = pflichthinweis`. Same treatment as A-class.
  - D-class violations → `schweregrad = mittel` → `verstossklasse = hinweis`. These produce warnings (W-01 in Sprint 4/5) but do not block.
- Severity weights and verstossklasse mappings read from a configurable table — never hard-coded constants.
- A finding's resolution paths:
  - `aufgelöst` requires a Decision Event (`scope_type = segment`, `decision_type = audit_befund_aufgelöst`) created via T-1.4.2; resolution may involve a manual Segment edit (which produces its own revision-UUID via T-1.4.1 separately) or an explicit "no change needed, this is intentional" annotation.
  - `quittiert` ("acknowledged without change") is permitted only for `mittel`-severity findings; never for `kritisch` or `hoch`. Quittierung still requires a Decision Event (`decision_type = audit_befund_quittiert`).
- No automatic quittierung on any severity. The user must act.
- Audit findings do not stop the translation flow during translation execution. Per Dokument 2 §2.6 / §3.6, findings are persisted and carried forward to preflight (Sprint 4/5) — they do not interrupt T-7.1.1 mid-job.

**T-7.3.2 — Promotion Stufe 3**
- User reviews Musterkandidaten registered by T-7.3.1 (Sprint 2). The system surface enumerates current candidates with their evidence (the underlying Stufe-1 observations).
- User action `bestätige_stilregel(musterkandidat_uuid)` is the **only** code path from Stufe 2 to bestätigte Stilregel. No internal API, no automatic threshold, no statistical promotion.
- Confirmation creates a Decision Event via T-1.4.2 with `scope_type = project`, `decision_type = stilregel_bestaetigung`, content referencing the Musterkandidat and the user's annotation.
- Confirmed Stilregel is a new entity, distinct from the Musterkandidat that produced it. The Musterkandidat is marked `bestätigt`, retains its observation evidence, and becomes immutable in its observation linkage.
- Confirmed Stilregel does **not** automatically apply to translation production in this sprint. It exists in the system, queryable, but its application pathway into RULE_BINDING is deferred (this is a CR-3 F2 boundary that the canon explicitly defers per DBB §7.5 and Dokument C v1.1 §3 follow-on work).
- Rejection action `verwerfe_musterkandidat(musterkandidat_uuid)` permitted; creates a Decision Event with `decision_type = musterkandidat_verworfen`. Rejected candidates are marked `verworfen` and remain queryable for audit purposes; they cannot be re-confirmed without producing fresh observations from new manual corrections.
- H-7 is the load-bearing invariant: at no point may a Musterkandidat transition to bestätigte Stilregel except through the explicit user action above. Code review must demonstrate this exhaustively.
- Lernquellen-Asymmetrie per Dokument 1 §4.13 / DBB §7.5: the source-class metadata recorded on observations in Sprint 2 is preserved on the confirmed Stilregel. Granularity of how source-class influences confirmation eligibility (whether all five classes can produce confirmable candidates, or only some) is **still deliberately open** per DBB §7.5. The infrastructure does not differentiate; the user-facing surface presents all candidates uniformly. Future refinement work can layer source-class-aware filtering without migration.

## 3. Ticket sequence

Sprint-internal sequencing per DBB §10 Delivery-Reihenfolge, Schritte 7 (T-7.3.2) and 8 (T-8.1.x):

```
[Sprint 2 complete]
        │
        v
T-8.1.1 (Befund-Tabelle, audit-run skeleton)
        │
        v
T-8.1.2 (A-01 through D-03 regelprüfung)

T-7.3.2 (Promotion Stufe 3) — parallel to T-8.1.x
                              starts after Sprint 2's T-7.3.1 is green
                              independent of T-8.1.x scope
```

T-7.3.2 has no dependency on T-8.1.x and may run fully in parallel. Its only Sprint-3 prerequisite is T-7.3.1 from Sprint 2 (already green at sprint start).

T-8.1.2 follows T-8.1.1 strictly: the regelprüfung functions write to the Befund-Tabelle, which T-8.1.1 establishes.

## 4. Mandatory tests

| Test ID | Ticket | Check content | Setup note |
|---|---|---|---|
| T-H4-02 | T-8.1.1 | Audit-run produces no revision-UUID; no Decision Event for findings themselves (only for resolutions) | Run audit pass; assert revisions delta = 0, decision_events delta only for explicit resolutions |
| Audit-Befund-Tabelle-Eigene-Tabelle-Test | T-8.1.1 | Befund-Tabelle is its own table; not an FK extension of Revision or Decision Event | DB introspection |
| Audit-Befund-Immutable-Detection-Test | T-8.1.1 | After Befund creation, `regelkennung`, `verstossklasse`, `schweregrad`, `detected_at` cannot be mutated | Attempt mutation → error |
| Audit-Befund-Resolution-Mutable-Only-Test | T-8.1.1 | Only resolution fields (`auflösungsstatus`, `resolved_at`, `resolution_decision_event_uuid`) may be updated post-creation | Attempt update on resolution fields → success; on detection fields → error |
| Audit-Run-Log-Eintrag-Test | T-8.1.1 | Every audit-run produces one Log-Eintrag with start, end, finding count by severity | Run audit pass; assert log entry shape |
| Audit-Kein-Auto-Korrektur-Test | T-8.1.1 | Audit-run never writes to Segment, never writes to TRANSLATION-PO, never writes to Revision | Run audit pass on synthetic project; assert tables unchanged except Befund and Log-Eintrag |
| Audit-Job-State-Machine-Test | T-8.1.1 | Audit-run uses Sprint 0 T-2.1.1 job state machine; deferred → auto-retry; fehlgeschlagen → no auto-retry | Force failure mid-run; assert state behaviour |
| Audit-A-Klasse-Hoch-Pflichthinweis-Test | T-8.1.2 | A-01 violation → `schweregrad = hoch`, `verstossklasse = pflichthinweis` | Synthetic A-01 violation; assert classification |
| Audit-B-Klasse-Hoch-Pflichthinweis-Test | T-8.1.2 | B-01 violation → `schweregrad = hoch`, `verstossklasse = pflichthinweis` | Synthetic B-01 violation |
| Audit-C-Klasse-Kritisch-Blockierend-Test | T-8.1.2 | C-01 violation → `schweregrad = kritisch`, `verstossklasse = blockierend` | Synthetic C-01 violation |
| Audit-D-Klasse-Mittel-Hinweis-Test | T-8.1.2 | D-01 violation → `schweregrad = mittel`, `verstossklasse = hinweis` | Synthetic D-01 violation |
| Audit-Severity-Konfigurations-Test | T-8.1.2 | Severity weights and verstossklasse mappings read from configurable table | Change config; rerun; assert effect |
| Audit-Aufloesung-Decision-Event-Test | T-8.1.2 | Resolution `offen → aufgelöst` requires a Decision Event with `decision_type = audit_befund_aufgelöst` | Resolve finding; assert decision_event present and linked |
| Audit-Quittierung-Nur-Mittel-Test | T-8.1.2 | Attempted quittierung on `kritisch` or `hoch` finding → error; on `mittel` finding → permitted with Decision Event | Three integration cases |
| Audit-Kein-Auto-Quittierung-Test | T-8.1.2 | No code path exists that quittiert a finding without a user-initiated Decision Event | Code review + attempted internal API call → error |
| Audit-Findings-Stoppen-Translation-Flow-Nicht-Test | T-8.1.2 | Audit findings detected during or before translation do not interrupt T-7.1.1 mid-job | Synthetic project with pre-existing findings; run translation; assert job runs to completion |
| T-H7-01 | T-7.3.2 | Auto-promotion path Stufe 2 → bestätigte Stilregel structurally impossible — only the user-action code path exists | Code review + attempted internal API call → error |
| Promotion-Stufe3-Bestaetigung-Decision-Event-Test | T-7.3.2 | `bestätige_stilregel` creates Decision Event with correct `scope_type` and `decision_type` | User action; assert decision_event |
| Promotion-Stufe3-Stilregel-Distinct-Entity-Test | T-7.3.2 | Confirmed Stilregel is a new entity, distinct from the Musterkandidat | Confirm; assert Stilregel record exists separately, Musterkandidat marked `bestätigt` |
| Promotion-Stufe3-Verwerfung-Test | T-7.3.2 | `verwerfe_musterkandidat` creates Decision Event with `decision_type = musterkandidat_verworfen`; candidate marked `verworfen` | User action; assert state |
| Promotion-Stufe3-Stilregel-Inert-In-Translation-Test | T-7.3.2 | Confirmed Stilregel does not automatically apply to translation production this sprint | Confirm Stilregel matching new Segment; run translation; assert Stilregel not applied |
| Promotion-Stufe3-Verworfener-Kandidat-Nicht-Wieder-Bestaetigbar-Test | T-7.3.2 | Verworfener Kandidat cannot be re-confirmed without fresh observations | Reject candidate; attempt re-confirm → error |
| Promotion-Stufe3-Source-Class-Preserved-Test | T-7.3.2 | Source-class metadata from observations preserved on confirmed Stilregel | Confirm candidate built from known source-class observations; assert metadata propagation |

Invariants in scope this sprint: H-4, H-7. (H-1, H-2, H-5, H-6 carry forward as Sprint 0–2 regressions; all must remain green.)

New regressions from this sprint onward:

- Audit-run produces revision-UUID.
- Befund-Tabelle merged into Revision or Decision Event schema.
- Audit-run writes to Segment, TRANSLATION-PO, or Revision.
- Befund detection fields mutated post-creation.
- Audit severity hard-coded.
- Audit auto-quittierung exists.
- Audit findings stop translation flow.
- Quittierung permitted on `kritisch` or `hoch` findings.
- Auto-promotion path Stufe 2 → bestätigte Stilregel.
- Confirmed Stilregel auto-applies to translation production (this is the deferred boundary; auto-application becomes possible only in a future sprint after explicit canon decision).
- Verworfener Kandidat re-confirmable without fresh observations.
- Source-class metadata lost between observation and confirmed Stilregel.

## 5. Definition of Done

Code:

- T-8.1.1, T-8.1.2, T-7.3.2 implemented, reviewed, and merged.
- Engineering Execution Baseline v1.0 DoD satisfied for every ticket.
- **Stilfeature-Test-Familien (CR-3) row substantively satisfied for T-7.3.2** (F2 family completion). The CR-2-defined F2 test families exercising user-initiated promotion confirmation must be present.
- All Sprint 0–2 regression tests still green.

Audit infrastructure:

- T-H4-02 green.
- Audit-Befund-Tabelle-Eigene-Tabelle-Test green.
- Audit-Befund-Immutable-Detection-Test green.
- Audit-Befund-Resolution-Mutable-Only-Test green.
- Audit-Run-Log-Eintrag-Test green.
- Audit-Kein-Auto-Korrektur-Test green.
- Audit-Job-State-Machine-Test green.

Audit regelprüfung:

- Audit-A-Klasse-Hoch-Pflichthinweis-Test green.
- Audit-B-Klasse-Hoch-Pflichthinweis-Test green.
- Audit-C-Klasse-Kritisch-Blockierend-Test green.
- Audit-D-Klasse-Mittel-Hinweis-Test green.
- Audit-Severity-Konfigurations-Test green.
- Audit-Aufloesung-Decision-Event-Test green.
- Audit-Quittierung-Nur-Mittel-Test green.
- Audit-Kein-Auto-Quittierung-Test green.
- Audit-Findings-Stoppen-Translation-Flow-Nicht-Test green.

Promotion Stufe 3:

- T-H7-01 green.
- Promotion-Stufe3-Bestaetigung-Decision-Event-Test green.
- Promotion-Stufe3-Stilregel-Distinct-Entity-Test green.
- Promotion-Stufe3-Verwerfung-Test green.
- Promotion-Stufe3-Stilregel-Inert-In-Translation-Test green.
- Promotion-Stufe3-Verworfener-Kandidat-Nicht-Wieder-Bestaetigbar-Test green.
- Promotion-Stufe3-Source-Class-Preserved-Test green.

End-to-end demonstrable at sprint end:

- An audit-run on a project produces Befund rows for all 12 rules where violations exist, with correct severity classification per Dokument 1 §4.6, without writing to any other table.
- A C-class finding cannot be quittiert; a D-class finding can be quittiert, with the action recorded as a Decision Event.
- Audit findings present on a project do not block T-7.1.1 from running and completing — the findings persist and are queryable for the future preflight gates (Sprint 4/5).
- A user reviewing the Musterkandidaten surface from Sprint 2 can confirm one candidate (creating a bestätigte Stilregel) and reject another. Both actions produce Decision Events. The confirmed Stilregel exists as a new entity but does not automatically modify any subsequent translation output in this sprint.
- A rejected Musterkandidat cannot be re-confirmed without fresh manual corrections producing new observations.

## 6. Risks

R-S3-01 — Audit-run writes revision-UUIDs "to document what was checked". Probability: high. Consequence: H-4 silently violated; revisions table polluted with non-text-change entries; downstream history queries (Sprint 6) report audit checks as text edits. (DBB Abkürzung 3-related.) Review obligation: T-H4-02 green; code review of every AUDIT module path confirms `create_revision` is never called.

R-S3-02 — Befund-Tabelle merged into Revision or Decision Event via FK or shared schema. Probability: medium. Consequence: H-4 boundary collapses; audit findings indistinguishable from text revisions or user decisions in downstream queries. (DBB ticket-level risk for T-8.1.1.) Review obligation: Audit-Befund-Tabelle-Eigene-Tabelle-Test green; DB schema review confirms three separate tables: Revision, Decision Event, Befund.

R-S3-03 — Audit-run writes to Segment or TRANSLATION-PO during a check pass. Probability: medium. Consequence: audit becomes a side-effect-producing operation; subsequent reads see audit-modified state; H-4 violated. Review obligation: Audit-Kein-Auto-Korrektur-Test green; AUDIT module code review confirms no write paths to those tables.

R-S3-04 — Severity weights hard-coded. Probability: high. Consequence: Sprint 4 preflight (P-03 / P-04 / W-01) cannot be calibrated; Gold-Corpus-Tests post-hoc retuning becomes a code change. Review obligation: Audit-Severity-Konfigurations-Test green; code review confirms weights table is configurable.

R-S3-05 — Critical findings classified as warnings to avoid blocking export. Probability: medium. Consequence: C-class violations (Qurʾān/Hadith integrity, religious-formula violations) silently leak through to export; downstream P-03 gate (Sprint 4/5) cannot block what was never marked blocking. (DBB ticket-level risk for T-8.1.2.) Review obligation: Audit-C-Klasse-Kritisch-Blockierend-Test green; code review of severity assignment.

R-S3-06 — Auto-quittierung implemented for high-severity findings. Probability: low–medium. Consequence: pflichthinweise quittiert without user action; preflight gate P-04 (Sprint 4/5) sees fewer findings than actually exist; export proceeds with unresolved obligations. Review obligation: Audit-Kein-Auto-Quittierung-Test green; Audit-Quittierung-Nur-Mittel-Test green.

R-S3-07 — Audit findings interrupt translation flow. Probability: medium. Consequence: T-7.1.1 jobs fail unnecessarily mid-run; throughput drops; user experience degrades; canon rule (Dokument 2 §2.6: "Audit-Befunde stoppen den Flow nicht") silently violated. Review obligation: Audit-Findings-Stoppen-Translation-Flow-Nicht-Test green; code review confirms no synchronous AUDIT call from inside T-7.1.1.

R-S3-08 — Auto-promotion Stufe 2 → bestätigte Stilregel implemented "when the candidate is statistically obvious". Probability: medium. Consequence: H-7 silently violated; user confirmation step bypassed; learned style rules enter the system without nutzer-bestätigung; downstream RULE_BINDING (a future sprint) consumes auto-promoted rules as if user-confirmed. (DBB Abkürzung 6-related; DBB ticket-level risk for T-7.3.2.) Review obligation: T-H7-01 green; code review traces the only path from Musterkandidat to bestätigte Stilregel through `bestätige_stilregel(musterkandidat_uuid)`.

R-S3-09 — Confirmed Stilregel applied to translation production this sprint. Probability: medium. Consequence: the deferred boundary (per DBB §7.5 and Dokument C v1.1 §3) is silently crossed; the canonical position that style-rule application is **not yet** wired into RULE_BINDING is undermined; later canon decisions about source-class differentiation are pre-empted. Review obligation: Promotion-Stufe3-Stilregel-Inert-In-Translation-Test green; code review confirms RULE_BINDING (T-7.2.1 from Sprint 2) does not consult the bestätigte Stilregel table.

R-S3-10 — Verworfener Kandidat re-confirmable without fresh observations. Probability: low. Consequence: a user who rejects a candidate, then changes their mind without producing new corrections, can resurrect it; the rejection signal is meaningless. Review obligation: Promotion-Stufe3-Verworfener-Kandidat-Nicht-Wieder-Bestaetigbar-Test green; code review of the re-confirm path confirms it requires fresh observations linked to the surface form.

R-S3-11 — Source-class metadata lost between Stufe 2 and Stufe 3. Probability: medium. Consequence: future Lernquellen-Asymmetrie partitioning per DBB §7.5 cannot be retrofitted without migration; observations recorded with source-class become indistinguishable at the confirmed-Stilregel level. Review obligation: Promotion-Stufe3-Source-Class-Preserved-Test green; code review confirms metadata field carries through.

## 7. Transition to Sprint 4

Sprint 4 (Consistency + Preflight) presupposes:

- T-8.1.1 green: Sprint 4's T-9.1.1 / T-9.1.2 preflight gates consume Befund rows produced by audit-run. The Befund-Tabelle and its severity classification are inputs to P-03, P-04, W-01.
- T-8.1.2 green: severity classification per Dokument 1 §4.6 is established; preflight gate semantics (kritisch → P-03, hoch → P-04, mittel → W-01) can be wired.
- T-7.3.2 green: closes the F2 (Promotion) family per CR-3. Sprint 4 has no further F2 dependency.

Sprint 4 starts T-8.2.1 (consistency engine K-01–K-07), which depends on T-7.2.1 (Sprint 2) and T-5.2.1 (Sprint 1) — both already green at Sprint 4 start.

Sprint 4 may begin only after every Sprint 3 mandatory test in §4 is green.

## A. Hard Gates

HG-S3-1 — T-8.1.1 must complete before T-8.1.2 starts. Per DBB §10, T-8.1.2's regelprüfung functions write to the Befund-Tabelle that T-8.1.1 establishes.

HG-S3-2 — T-H4-02 (no revision-UUID for audit operations) must be green before T-8.1.2 merges. Per DBB §A and the H-4 invariant, audit must be a pure-observation operation.

HG-S3-3 — T-8.1.2 Audit-C-Klasse-Kritisch-Blockierend-Test must be green before merge. C-class findings are the load-bearing input to P-03 in Sprint 4; mis-classification here propagates undetectably.

HG-S3-4 — T-7.3.2 H-7 test (T-H7-01) must be green before merge. Per DBB §A, H-7 is unumgehbar; auto-promotion to bestätigte Stilregel must be structurally impossible.

HG-S3-5 — T-7.3.2 Promotion-Stufe3-Stilregel-Inert-In-Translation-Test must be green before merge. The deferred boundary between confirmation and application is canonical (DBB §7.5, Dokument C v1.1 §3); crossing it silently in this sprint would constitute hidden canon drift.

HG-S3-6 — All Sprint 0–2 H-test regressions remain green: T-H1-01, T-H1-02, T-H2-01, T-H2-02, T-H4-01, T-H4-02, T-H5-01, T-H5-02, T-H6-01, T-H7-01.

HG-S3-7 — Engineering Execution Baseline v1.0 DoD Stilfeature-Test-Familien (CR-3) row substantively in scope for T-7.3.2 (F2 family completion). The CR-2-defined F2 test families must be present; second sprint where this row is non-vacuous.

## B. What deliberately does not belong in this sprint

- Consistency engine K-01–K-07 — T-8.2.1 (Sprint 4). Audit and consistency are distinct: audit applies discrete rules per Segment/finding; consistency examines work-wide identity-based patterns.
- Preflight gates P-03, P-04, W-01–W-03, Hadith-Verifikationsstatus group — T-9.1.x (Sprint 4/5). Sprint 3 produces the audit findings; the gates that consume them are next.
- Export artefact and EXPORT_EVENT — T-9.2.1 (Sprint 5).
- Provenance readout, history endpoints — WS-10 (Sprint 6).
- T-7.2.1 RULE_BINDING — already in Sprint 2; not repeated.
- Application of confirmed Stilregel into translation production — explicitly deferred per DBB §7.5 and Dokument C v1.1 §3. The Stilregel exists; its automatic application path is a later canon decision.
- Stilfeature backlog families F1, F3, F4, F5 (CR-3) — deferred per Dokument C v1.1 §3 follow-on work. Only F2 is exercised here through T-7.3.2 completion.
- Lernquellen-Asymmetrie partitioning behaviour per Dokument 1 §4.13 / DBB §7.5 — explicitly open. Source-class metadata is preserved; no source-class-aware filtering is implemented.
- Audit integration of style-feature violations into A-01–D-03 — deferred per Dokument C v1.1 §3.4. The audit structure exists and is wired for translation findings, but style-feature-specific audit rules are not added.
- Cross-rule audit interactions (e.g., a single Segment violating both A-01 and C-02 simultaneously) — handled by the Befund-Tabelle producing one row per (Segment, regelkennung) tuple; downstream gate logic (Sprint 4/5) decides aggregation.
- UI for any module. Befund browsing surface, audit-run trigger, Musterkandidat confirmation surface — all backend-only this sprint.
- Calibration values: severity weight tables, audit-run scheduling cadences, promotion confirmation thresholds — all configurable, never pre-set.
- E-5 / Schnittstelle 5 live test package — parked.
- Real Shamela Ist-Aufnahme — parked.

*Waraq Sprint-3 / Audit + Rule-Binding Completion Delivery Plan v1.0 — End*