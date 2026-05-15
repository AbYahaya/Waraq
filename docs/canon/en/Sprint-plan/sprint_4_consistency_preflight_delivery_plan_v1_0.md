<!-- Authored: 2026-05-01. -->
<!-- Status: Authored to replace presumed-lost original v1.0 per option (c). -->
<!-- Anchored to: Baseline Delivery Plan v1.0 §2 (Sprint 4 scope description, including belegte/offene Gates-Liste); DBB v1.0 §10 Delivery-Reihenfolge Schritt 9; DBB v1.0 ticket definitions T-8.2.1, T-9.1.1, T-9.1.2; DBB v1.0 §A Hard Delivery-Gates; Engineering Execution Baseline v1.0 (DoD); Implementation Translation Baseline v1.0 (Preflight-Schichtenmodell, Gate-Prüfungsschicht); Dokument 1 §4.6 (Audit-Severitätsklassen), §4.7 (Gate-Prüfungsschicht), §4.8 (W-Klasse), §4.9 E-1 (go_with_warning), §4.10 (decision_source preflight_confirmation), §4.16 (Hadith-Verifikationsstatus), §4.18 Spur 2 (Klasse-B-Generallogik); Dokument 2 §2.3 (P-Slot-Belegungslogik), §2.4 (W-Slot Minimalmodell II + P-03), §2.5 (W-04–W-08 offen), §2.9 (Gate-Verortung Hadith-Verifikationsstatus). -->
<!-- Replaces: any presumed-lost prior "Waraq Sprint-4 / Consistency + Preflight Delivery Plan v1.0" referenced in Dokument 2 §1 and Baseline Delivery Plan §1. -->
<!-- Structural template: ocr_text_export_v1_3.md §5 Sprint Plan Sprint-OCR v1.3. -->

# Waraq Sprint-4 / Consistency + Preflight Delivery Plan v1.0

Status: Working basis. No coding release. No silent re-baselining.

## Start condition

Sprints 0–3 fully completed. All Sprint 0–3 mandatory tests green. Audit Befund-Tabelle operational with all 12 rules A-01 through D-03 producing severity-classified findings (T-8.1.1, T-8.1.2). Translation pipeline producing TRANSLATION-PO and RULE_BINDING-PO rows (T-7.1.x, T-7.2.1). Glossary service with explicit `NO_ENTRY` sentinel and Konzept-ID resolution operational (T-5.2.1). Promotion pipeline closed: Stufen 1–2 in Sprint 2, Stufe 3 in Sprint 3.

## 1. Scope

| Ticket | Designation |
|---|---|
| T-8.2.1 | CONSISTENCY: Konsistenz-Befund-Tabelle and identity-/reference-based check K-01 through K-07 |
| T-9.1.1 | PREFLIGHT: Pflichtfragen-Bestätigung (configuration layer), P-03 (kritisch), P-04 (Pflichthinweise), Exportlauf-Ereignis |
| T-9.1.2 | PREFLIGHT: belegte W-Gates (W-01, W-02, W-03), Hadith-Verifikationsstatus group, exportierbar_mit_warnungen state |

Deliberately not in this sprint: export artefact erzeugung and EXPORT_EVENT (T-9.2.1 — Sprint 5), provenance readout and history endpoints (WS-10 — Sprint 6). P-01 / P-02 / P-05 / P-06 and W-04 through W-08 are explicitly **offen** per Dokument 2 §2.3, §2.5: no candidates exist in the canon; this sprint must not silently fill them. Stilfeature backlog families F1, F3, F4, F5 (CR-3) — deferred per Dokument C v1.1 §3 follow-on work; F2 closed in Sprints 2–3. Stilfeature audit integration into A-01–D-03 — deferred per Dokument C v1.1 §3.4. No UI for any module. No calibration values: K-rule subject-type weight tables, severity aggregation thresholds, Häufungsschwelle für L-24 Klasse-B-Generallogik per Dokument 1 §4.18 — all configurable, never pre-set.

## 2. Sprint target state

**T-8.2.1 — Consistency engine K-01 through K-07**

The engine performs identity-based or reference-based checks. Each K-rule prüft against its passende Identitätstyp; **no rule is reduced to plain string equality**.

- Konsistenz-Befund-Tabelle implemented as its own table, distinct from Befund-Tabelle (T-8.1.1). Schema: `konsistenz_befund_uuid`, `subject_type` enum, `subject_key`, `verstossklasse` enum, `betroffene_segment_uuids[]`, `vorschlag` JSONB, `auflösungsstatus` enum (`offen | aufgelöst | quittiert`), `detected_at`, `resolved_at?`, `resolution_decision_event_uuid?` FK.
- `subject_type` enum coverage per K-rule:
  - K-01 (terminological consistency): `subject_type = concept_id`. Inconsistency detected when the same Konzept-ID is rendered with materially different translations across Segments — never on string equality of surface forms.
  - K-02 (formula and index consistency): `subject_type = formel_verzeichnis_id`. Religious formulas and standard index entries checked against their Verzeichnis-Identität.
  - K-03 (entity consistency): `subject_type = entity_id`. Named entities checked against their Entitäten-ID.
  - K-04 (transliteration consistency): `subject_type = transliterations_muster`. Transliteration patterns checked against the project-bound transliteration scheme.
  - K-05 (source-citation consistency): `subject_type = source_identity`. Quellenangabe checked against the source-identity record.
  - K-06 (structural pattern consistency): `subject_type = structural_key`. Recurring structural patterns (e.g., section heading conventions, footnote markers) checked against the project's structural key.
  - K-07 (cross-rule terminological consistency): `subject_type = concept_id`. Same Identitätstyp as K-01 but with cross-rule scope — checks consistency of terminology across rule applications, not just against a single Konzept-ID.
- For each K-rule, the check function reads only its passende Identitätstyp records and the relevant Segment text. No K-rule reads `surface_form` directly for equality comparison.
- Inconsistency detection produces a Konsistenz-Befund row with `state = offen`. The `vorschlag` field carries a system suggestion (e.g., "use rendering X across all 17 affected Segments") — but is **never automatically applied**. Resolution requires a Decision Event with `scope_type = project` and `decision_type = konsistenzgruppe_verbindlich`.
- Konsistenz-Befund rows are routed to PREFLIGHT (T-9.1.1 / T-9.1.2) per §4.7 / §4.8: a finding is W-02 (warning-class) by default; if it simultaneously violates a Kritisch-Klasse per §4.6, it routes to P-03 instead. The routing is computed at preflight evaluation, not stored in the Konsistenz-Befund row itself.
- No K-rule normalizes surface forms automatically. No K-rule creates glossary entries automatically.
- Engine is invoked as a job (job_type = consistency) using Sprint 0 T-2.1.1 state machine. Log-Eintrag for every run.
- **Critical structural property**: each K-rule must be implementable against its own subject_type without retrofitting K-02–K-06 onto concept_id. Any implementation that pauschalierte K-01's concept_id approach onto K-02–K-06 is a structural failure (DBB ticket-level risk for T-8.2.1).

**T-9.1.1 — Preflight: configuration layer + P-03 + P-04 + Exportlauf-Ereignis**

Preflight is structurally split per §4.7: **Konfigurationsschicht** (the four Pflichtfragen) and **Gate-Prüfungsschicht** (P-XX and W-XX gates). The two are conceptually separate; this ticket establishes both for the canonically belegt scope.

- **Konfigurationsschicht — vier Pflichtfragen.** Active confirmation required for each of the four canonical export-configuration questions (concrete questions defined in product configuration; Pflicht is canonical, the four-count is canonical, the questions themselves are configurable per Dokument 2 §2.3). Each Pflichtfrage-Bestätigung creates a Decision Event with `scope_type = project` and `decision_source = preflight_confirmation` per Dokument 1 §4.10.
- A saved Export-Profil may **pre-fill** Pflichtfragen but never **replaces** an active confirmation. The user must actively confirm at the time of export, even if all four are pre-filled identically to a saved profile.
- The Konfigurationsschicht does not occupy any P-Slot. Failure to actively confirm one or more Pflichtfragen produces preflight state `blockiert` with a distinct reason (Konfigurationsschicht unvollständig), separate from any P-XX gate.
- **Gate-Prüfungsschicht — P-03 (kritisch).** P-03 evaluates kritisch-class findings: any open `Befund` row from T-8.1.2 with `schweregrad = kritisch` (C-class violations) AND any open `Konsistenz-Befund` row that simultaneously violates a Kritisch-Klasse per §4.6. P-03 evaluates AND any kritische OCR-Fehlerklassen still unresolved at this stage (carry-forward from T-4.3.1). Open kritisch finding → P-03 → preflight state `blockiert`.
- **Gate-Prüfungsschicht — P-04 (Pflichthinweise).** P-04 evaluates hoch-severity findings: open `Befund` rows with `schweregrad = hoch` (A-class and B-class violations from T-8.1.2). Each P-04 finding requires individual user resolution (`aufgelöst`); `quittiert` is **not permitted** for P-04 per Sprint 3's Audit-Quittierung-Nur-Mittel rule. Open P-04 finding → preflight state `blockiert`.
- P-03 and P-04 are structurally distinct: per Dokument 2 §2.4, P-03 is "eigenständiges blockierendes Gate, strukturell gleichrangig neben P-04". Implementation must treat them as two parallel evaluations producing two distinct blocking-reason codes when blocking.
- **Exportlauf-Ereignis** — a Log-Eintrag (Log-ID via EVENTING) is produced on every preflight evaluation regardless of outcome. This is the Exportlauf-Ereignis, established here for the first time per Baseline Delivery Plan §2 ("Exportlauf-Ereignis (Log-ID) erstmals angelegt"). Sprint 5's T-9.2.1 reuses this same log family; this ticket initiates it.
- State machine: `nicht_gestartet → läuft → exportierbar | blockiert`. (The W-1/W-2/W-3 path to `exportierbar_mit_warnungen` is added in T-9.1.2.)
- No automatic resolution of any P-XX finding. No automatic Pflichtfrage-Bestätigung. The user acts on every gate.

**T-9.1.2 — Preflight: belegte W-Gates + Hadith-Verifikationsstatus + exportierbar_mit_warnungen**

Adds the warnungsbasiert gates and the Hadith-Verifikationsstatus group to the preflight machinery established in T-9.1.1. Adds the `exportierbar_mit_warnungen` state.

- **W-01 (Mittel-Audit-Befunde).** W-01 evaluates open `Befund` rows from T-8.1.2 with `schweregrad = mittel` (D-class violations). W-01 findings are warnings — they do not block export, but they trigger `exportierbar_mit_warnungen` state if any are present. Per T-8.1.2, mittel-severity findings may be `quittiert`; quittierte W-01 findings drop out of the gate evaluation.
- **W-02 (Konsistenzwarnungen K-01 through K-07).** W-02 evaluates open `Konsistenz-Befund` rows from T-8.2.1 that do **not** simultaneously violate a Kritisch-Klasse (those route to P-03). W-02 findings are warnings.
- **W-03 (graduelle Formatvorlagen-Abweichungen).** W-03 evaluates style-template deviations that are graduelle (gradient, soft) rather than strukturell (which would be kritisch). The classification is per the canonical Formatvorlagen-Baseline v1.1; integrity violations of the strukturell kind block via Guard-nahe Vorprüfungen (which precede the preflight dialog per Dokument 2 §3.1) and never reach W-03.
- **Hadith-Verifikationsstatus group per §4.7 / §4.16 / Dokument 2 §2.9.** This is an **eigene benannte Gruppe innerhalb der Gate-Prüfungsschicht**. It does **not** occupy any P-Slot or W-Slot. Implementation must not silently route H-1 or H-2 cases into open W-XX slots.
  - H-2 (export-blockierend bis Auflösung): unresolved Hadith-Verifikationsstatus N-1 through N-10 cases at H-2 classification block export. State: `blockiert`. Resolution exclusively via the 7 kanonisierten Handlungstypen per §4.16 (no audit-style quittierung).
  - H-1 (protokollpflichtig, warnungsfähig): Hadith cases at H-1 classification are warnings. They support `go_with_warning` analog §4.9 E-1: the user may proceed with explicit warning-acknowledgement, which creates a Decision Event with `decision_source = preflight_confirmation` per §4.10. State: contributes to `exportierbar_mit_warnungen`.
  - H-0 (review-intern tolerierbar): H-0 cases do not contribute to gate evaluation at all.
- **`exportierbar_mit_warnungen` state.** Reached when no blocking gate (P-03, P-04, H-2, Konfigurationsschicht-incomplete) is open AND at least one warning gate (W-01, W-02, W-03, Hadith H-1) has open content. Transition `blockiert → exportierbar_mit_warnungen | exportierbar` requires explicit user confirmation **per warning gate**. Each per-gate confirmation creates a Decision Event with `scope_type = project` and `decision_source = preflight_confirmation`.
- Each per-warning confirmation is its own Decision Event. A bulk "accept all warnings" action is permitted as a UX convenience but must produce N distinct Decision Events for N warning gates, not one merged event.
- **No silent slot fill.** P-01, P-02, P-05, P-06, W-04 through W-08 must not be implemented in this sprint. The preflight evaluation code must explicitly enumerate only the belegte slots; any code path that creates a finding for an offen slot is a canon violation per Dokument 2 §6.
- Pflichthinweis (P-04) is **never** routed into a W-Klasse to allow export. Per DBB ticket-level risk: "Pflichthinweis-Klasse (P-04) als W-Warnung behandelt – blockiert Export nicht mehr, wenn nötig" must be structurally impossible.
- State machine: `nicht_gestartet → läuft → exportierbar | exportierbar_mit_warnungen | blockiert`. The `exportierbar_mit_warnungen` state requires the per-gate confirmation chain; without it, the state stays `blockiert`.

## 3. Ticket sequence

Sprint-internal sequencing per DBB §10 Delivery-Reihenfolge, Schritt 9, with parallelism per ticket dependencies:

```
[Sprint 3 complete]
        │
        v
T-8.2.1 (consistency engine K-01–K-07)
        │   ─ may run in parallel with T-9.1.1 once Konsistenz-Befund schema exists
        v
T-9.1.1 (Preflight Konfigurationsschicht + P-03 + P-04 + Exportlauf-Ereignis)
        │
        v
T-9.1.2 (W-01/W-02/W-03 + Hadith-Verifikationsstatus + exportierbar_mit_warnungen)
        │
        v
[Sprint 4 complete]
```

Parallel windows: T-8.2.1 and T-9.1.1 may run partially in parallel — once T-8.2.1 has its Konsistenz-Befund schema in place, T-9.1.1 can wire P-03's consumption of consistency findings without waiting for the full K-01–K-07 implementation. T-9.1.2 strictly follows T-9.1.1 because the W-state machinery extends the P-state machinery.

## 4. Mandatory tests

| Test ID | Ticket | Check content | Setup note |
|---|---|---|---|
| Konsistenz-Befund-Eigene-Tabelle-Test | T-8.2.1 | Konsistenz-Befund-Tabelle is its own table, distinct from Befund-Tabelle | DB introspection |
| K-01-Concept-ID-Basis-Test | T-8.2.1 | K-01 inconsistency detected on concept_id basis, not surface-form string equality | Two Segments with same surface form but distinct Konzept-IDs → no false alarm; same Konzept-ID with materially different translations → finding |
| K-02-Formel-Verzeichnis-Identitaet-Test | T-8.2.1 | K-02 inconsistency detected against formel_verzeichnis_id | Synthetic case with two divergent renderings of same formel-Identität |
| K-03-Entitaet-ID-Test | T-8.2.1 | K-03 inconsistency detected against entity_id | Synthetic case |
| K-04-Transliterations-Muster-Test | T-8.2.1 | K-04 inconsistency detected against transliteration scheme | Synthetic case with two transliterations of same source string |
| K-05-Quellenidentitaet-Test | T-8.2.1 | K-05 inconsistency detected against source_identity | Synthetic case |
| K-06-Strukturelles-Muster-Test | T-8.2.1 | K-06 inconsistency detected against structural_key | Synthetic case with divergent structural patterns |
| K-07-Cross-Rule-Concept-ID-Test | T-8.2.1 | K-07 cross-rule consistency detected on concept_id basis | Synthetic case spanning multiple rules |
| K-Identitaetstyp-Trennung-Test | T-8.2.1 | Each K-rule reads only its passende Identitätstyp; K-02–K-06 do not delegate to concept_id | Code review of each K-rule's check function |
| Konsistenz-Vorschlag-Kein-Auto-Anwendung-Test | T-8.2.1 | `vorschlag` field never auto-applied; resolution requires Decision Event | Inject finding; assert no auto-application; resolve via DE; assert change |
| Konsistenz-Routing-W02-vs-P03-Test | T-8.2.1 ↔ T-9.1.1/T-9.1.2 | Konsistenz-Befund without Kritisch-Klasse → W-02 at preflight; with simultaneous Kritisch-Klasse → P-03 | Two integration cases |
| Konsistenz-Engine-Job-State-Test | T-8.2.1 | Consistency-run uses Sprint 0 T-2.1.1 state machine; deferred → auto-retry; fehlgeschlagen → no auto-retry | Force failure mid-run |
| Pflichtfrage-Active-Confirmation-Required-Test | T-9.1.1 | Export blocked when any of the four Pflichtfragen lacks active confirmation, even if a saved Export-Profil pre-fills them | Pre-fill via profile but skip active confirmation; assert blockiert |
| Pflichtfrage-Decision-Event-preflight-confirmation-Test | T-9.1.1 | Each Pflichtfrage-Bestätigung creates a Decision Event with `scope_type = project` and `decision_source = preflight_confirmation` | Confirm each of four; assert four Decision Events with correct fields |
| Pflichtfrage-Profile-Prefills-But-Not-Replaces-Test | T-9.1.1 | Saved profile pre-fills Pflichtfragen but never replaces the active confirmation step | Profile present + no confirmation → blockiert; profile present + confirmation → exportierbar (or onward state) |
| P-03-Kritisch-Audit-Blockierung-Test | T-9.1.1 | Open C-class Befund row → P-03 → preflight blockiert | Synthetic C-01 violation |
| P-03-Kritisch-OCR-Fehlerklasse-Carry-Forward-Test | T-9.1.1 | Unresolved kritisch OCR-Fehlerklasse from T-4.3.1 still blocks at P-03 | Synthetic project with F-01 unresolved at preflight |
| P-03-Kritisch-Konsistenz-Test | T-9.1.1 | Konsistenz-Befund simultaneously violating a Kritisch-Klasse → P-03 | Synthetic case |
| P-04-Hoch-Pflichthinweis-Blockierung-Test | T-9.1.1 | Open A-class or B-class Befund row → P-04 → preflight blockiert | Synthetic A-01 violation |
| P-03-P-04-Strukturell-Distinct-Test | T-9.1.1 | P-03 and P-04 produce distinct blocking-reason codes when both block | Inject both kritisch and hoch findings; assert two distinct reasons |
| Exportlauf-Ereignis-Immer-Test | T-9.1.1 | Every preflight evaluation produces a Log-Eintrag, regardless of outcome | Three evaluations under three outcomes; assert three log entries |
| Pflichtfrage-Konfigurationsschicht-Kein-P-Slot-Test | T-9.1.1 | Konfigurationsschicht failure does not occupy a P-XX slot; produces a distinct blocking reason | Code review + integration test |
| Preflight-State-Machine-Blockiert-Exportierbar-Test | T-9.1.1 | State transitions per the §2 spec hold | Run four state transitions; assert each |
| Preflight-Kein-Auto-Aufloesung-Test | T-9.1.1 / T-9.1.2 | No automatic resolution of any P- or W- finding; no automatic Pflichtfrage-Bestätigung | Integration sweep |
| W-01-Mittel-Warnung-Test | T-9.1.2 | Open D-class Befund row → W-01 → exportierbar_mit_warnungen (after explicit confirmation) | Synthetic D-01 violation |
| W-01-Quittiert-Drops-Out-Test | T-9.1.2 | Quittierte W-01 finding (per T-8.1.2's `quittiert` path for mittel-severity) does not contribute to gate | Quittiere; rerun preflight; assert no W-01 trigger |
| W-02-Konsistenz-Warnung-Test | T-9.1.2 | Open Konsistenz-Befund (without Kritisch-Klasse) → W-02 | Synthetic case |
| W-03-Graduelle-Formatvorlagen-Test | T-9.1.2 | Graduelle Formatvorlagen-Abweichung → W-03 | Synthetic case (strukturelle Abweichungen are guard-nah, not W-03) |
| Hadith-H2-Blockiert-Test | T-9.1.2 | Hadith-Verifikationsstatus H-2 case → preflight blockiert; not a W-Slot | Synthetic H-2 case (e.g., N-5 unresolved) |
| Hadith-H1-Warnung-go-with-warning-Test | T-9.1.2 | Hadith-Verifikationsstatus H-1 case supports `go_with_warning` per §4.9 E-1; produces Decision Event with `decision_source = preflight_confirmation` | Synthetic H-1 case + confirmation |
| Hadith-H0-Kein-Gate-Trigger-Test | T-9.1.2 | Hadith H-0 case does not contribute to gate evaluation | Synthetic H-0 case; assert no gate effect |
| Hadith-Eigene-Gruppe-Kein-P-W-Slot-Test | T-9.1.2 | Hadith-Verifikationsstatus group occupies no P- or W-Slot; routed as eigene benannte Gruppe per §4.7 / §2.9 | Code review + DB introspection of evaluation result objects |
| Exportierbar-Mit-Warnungen-Per-Gate-Confirmation-Test | T-9.1.2 | Transition to `exportierbar_mit_warnungen` requires per-warning-gate confirmation; bulk accept produces N distinct Decision Events | Two integration cases (single warning, multiple warnings) |
| Pflichthinweis-Nicht-Als-W-Klasse-Test | T-9.1.2 | P-04 (Pflichthinweis) is never routed into W-XX to allow export | Code review + attempted internal API path → error |
| Kein-Stiller-Slot-Fill-P01-P02-P05-P06-Test | T-9.1.1 / T-9.1.2 | No code path exists that creates a finding for P-01, P-02, P-05, or P-06 slots in this sprint | Code review of preflight evaluation; assert enumeration is exactly P-03, P-04 |
| Kein-Stiller-Slot-Fill-W04-W05-W06-W07-W08-Test | T-9.1.1 / T-9.1.2 | No code path exists that creates a finding for W-04 through W-08 slots in this sprint | Code review; assert enumeration is exactly W-01, W-02, W-03 |

Invariants in scope this sprint: none new — Sprint 4 establishes consistency and preflight machinery, but the H-XX-invariants (H-1 through H-7) are not directly exercised by new code paths. (Hadith H-0/H-1/H-2 are **not** the same H-XX as the system invariants; the canon uses overlapping nomenclature here. The Hadith-Verifikationsstatus is governed by §4.16, not by Core Architecture H-1–H-7.) All Sprint 0–3 H-test regressions must remain green throughout.

New regressions from this sprint onward:

- K-01 reduced to surface-form string equality.
- K-02 through K-06 generalized to concept_id.
- Konsistenz-Vorschlag auto-applied without Decision Event.
- Saved Export-Profil treated as active Pflichtfrage-Bestätigung.
- Pflichtfrage-Bestätigung created without `decision_source = preflight_confirmation`.
- P-03 and P-04 collapsed into a single blocking reason.
- P-04 (Pflichthinweis) routed to W-XX.
- Exportlauf-Ereignis missing from preflight evaluations.
- Preflight evaluation produces findings for P-01, P-02, P-05, P-06, W-04, W-05, W-06, W-07, or W-08 slots.
- Hadith-Verifikationsstatus group occupying a P- or W-Slot.
- H-2 (Hadith) treated as warning-class.
- Bulk warning-confirmation produces a single Decision Event instead of N per-gate events.
- Konfigurationsschicht failure occupying a P-XX slot.

## 5. Definition of Done

Code:

- T-8.2.1, T-9.1.1, T-9.1.2 implemented, reviewed, and merged.
- Engineering Execution Baseline v1.0 DoD satisfied for every ticket.
- Stilfeature-Test-Familien (CR-3) row vacuously satisfied — no F2 or F3 tickets in this sprint.
- All Sprint 0–3 regression tests still green.

Consistency engine:

- Konsistenz-Befund-Eigene-Tabelle-Test green.
- K-01-Concept-ID-Basis-Test green.
- K-02-Formel-Verzeichnis-Identitaet-Test green.
- K-03-Entitaet-ID-Test green.
- K-04-Transliterations-Muster-Test green.
- K-05-Quellenidentitaet-Test green.
- K-06-Strukturelles-Muster-Test green.
- K-07-Cross-Rule-Concept-ID-Test green.
- K-Identitaetstyp-Trennung-Test green.
- Konsistenz-Vorschlag-Kein-Auto-Anwendung-Test green.
- Konsistenz-Routing-W02-vs-P03-Test green.
- Konsistenz-Engine-Job-State-Test green.

Preflight Konfigurationsschicht:

- Pflichtfrage-Active-Confirmation-Required-Test green.
- Pflichtfrage-Decision-Event-preflight-confirmation-Test green.
- Pflichtfrage-Profile-Prefills-But-Not-Replaces-Test green.
- Pflichtfrage-Konfigurationsschicht-Kein-P-Slot-Test green.

Preflight Gate-Prüfungsschicht (P-Gates):

- P-03-Kritisch-Audit-Blockierung-Test green.
- P-03-Kritisch-OCR-Fehlerklasse-Carry-Forward-Test green.
- P-03-Kritisch-Konsistenz-Test green.
- P-04-Hoch-Pflichthinweis-Blockierung-Test green.
- P-03-P-04-Strukturell-Distinct-Test green.
- Pflichthinweis-Nicht-Als-W-Klasse-Test green.

Preflight Gate-Prüfungsschicht (W-Gates):

- W-01-Mittel-Warnung-Test green.
- W-01-Quittiert-Drops-Out-Test green.
- W-02-Konsistenz-Warnung-Test green.
- W-03-Graduelle-Formatvorlagen-Test green.

Preflight Hadith-Verifikationsstatus group:

- Hadith-H2-Blockiert-Test green.
- Hadith-H1-Warnung-go-with-warning-Test green.
- Hadith-H0-Kein-Gate-Trigger-Test green.
- Hadith-Eigene-Gruppe-Kein-P-W-Slot-Test green.

Preflight state machine + logging:

- Exportlauf-Ereignis-Immer-Test green.
- Preflight-State-Machine-Blockiert-Exportierbar-Test green.
- Exportierbar-Mit-Warnungen-Per-Gate-Confirmation-Test green.
- Preflight-Kein-Auto-Aufloesung-Test green.

Slot discipline:

- Kein-Stiller-Slot-Fill-P01-P02-P05-P06-Test green.
- Kein-Stiller-Slot-Fill-W04-W05-W06-W07-W08-Test green.

End-to-end demonstrable at sprint end:

- A consistency-run on a project produces Konsistenz-Befund rows for every K-rule whose passende Identitätstyp shows divergence — without false alarms from surface-form coincidence (K-01) and without forcing K-02–K-06 through concept_id.
- A preflight evaluation on a project with no findings, all four Pflichtfragen actively confirmed, no open conflicts, and no Hadith H-2 cases reaches `exportierbar`.
- A preflight evaluation on a project with one open C-01 finding and three pre-filled-but-unconfirmed Pflichtfragen reaches `blockiert` with two distinct blocking reasons (P-03 + Konfigurationsschicht).
- A preflight evaluation on a project with three open D-01 findings and one open Hadith H-1 case reaches `exportierbar_mit_warnungen` only after the user actively confirms each of the four warnings, producing four distinct Decision Events with `decision_source = preflight_confirmation`.
- An attempt to file a finding under P-01, P-02, P-05, P-06, or any of W-04 through W-08 fails with an explicit "slot offen, Belegung nicht erlaubt" error — these slots are structurally inert this sprint.

## 6. Risks

R-S4-01 — K-01 implemented on string equality of surface forms instead of Konzept-ID basis. Probability: high. Consequence: bewusst verschiedene Übersetzungen derselben Oberflächenform produce false alarms; legitime lokale Ausnahmen (resolved via Sprint 1 conflict-instance pathway) are flagged as inconsistencies; the consistency engine becomes a noise source that users learn to ignore. (DBB Abkürzung 10 names this exact failure mode.) Review obligation: K-01-Concept-ID-Basis-Test green; code review of K-01's check function confirms it queries Konzept-ID, not surface_form.

R-S4-02 — K-02 through K-06 generalized to Konzept-ID. **Probability: high. Severity: structural.** Consequence: K-02 (formel/Verzeichnisidentität), K-03 (Entitäten-ID), K-04 (Transliterationsmuster), K-05 (Quellenidentität), K-06 (struktureller Schlüssel) become structurally incorrect or never trigger; the canon's identity-/reference-based architecture per DBB ticket-level risk is silently flattened. Review obligation: K-Identitaetstyp-Trennung-Test green; code review of every K-rule's check function confirms it reads its own subject_type, never delegates to concept_id. **This is the second most-named risk in the DBB for this ticket and must not be deferred.**

R-S4-03 — Konsistenz-Vorschlag automatically applied. Probability: medium. Consequence: terminology decisions made by the system on the user's behalf without explicit Decision Event; H-7 (no automatic style-rule promotion) silently violated by analogy. Review obligation: Konsistenz-Vorschlag-Kein-Auto-Anwendung-Test green; code review of resolution paths.

R-S4-04 — Saved Export-Profil treated as active Pflichtfrage-Bestätigung. Probability: high. Consequence: export proceeds with stale or assumed answers to the four Pflichtfragen; the Konfigurationsschicht's purpose (fresh active confirmation per export) is silently violated; downstream EXPORT_EVENT (Sprint 5) carries unreliable export_config. (DBB ticket-level risk for T-9.1.1.) Review obligation: Pflichtfrage-Profile-Prefills-But-Not-Replaces-Test green; Pflichtfrage-Active-Confirmation-Required-Test green.

R-S4-05 — Pflichthinweis (P-04) routed into W-XX to permit export. Probability: medium. Consequence: P-04 stops blocking; A-class and B-class violations leak through to export; the preflight architecture's distinction between Pflichthinweis (individual resolution required) and Hinweis (warning, may proceed) silently collapses. (DBB ticket-level risk for T-9.1.2.) Review obligation: Pflichthinweis-Nicht-Als-W-Klasse-Test green; code review of every gate-routing path.

R-S4-06 — P-01, P-02, P-05, P-06, W-04, W-05, W-06, W-07, W-08 silently filled. Probability: medium. Consequence: the canon's explicit "offen, keine sauberen Kandidaten" position per Dokument 2 §2.3 / §2.5 is violated; future canonization of those slots becomes impossible without retrofitting; the principle "kein stilles Re-Baselining" per Dokument 2 §6 broken. Review obligation: Kein-Stiller-Slot-Fill-P01-P02-P05-P06-Test green; Kein-Stiller-Slot-Fill-W04-W05-W06-W07-W08-Test green; code review enumerates exactly the 5 belegt slots: P-03, P-04, W-01, W-02, W-03.

R-S4-07 — Hadith-Verifikationsstatus group placed into a P-Slot or W-Slot. Probability: medium. Consequence: per Dokument 2 §2.9, the group is **eigene benannte Gruppe innerhalb der Gate-Prüfungsschicht** without slot occupancy; placing it into a slot would silently consume one of the offen slots and make later canonization impossible. Review obligation: Hadith-Eigene-Gruppe-Kein-P-W-Slot-Test green; code review of preflight result-object structure.

R-S4-08 — Hadith H-2 treated as warning-class. Probability: medium. Consequence: export-blockierend Hadith cases (per §4.16) leak through to export as warnings; the structural distinction H-1 (warnungsbasiert) vs H-2 (blockierend) collapses. Review obligation: Hadith-H2-Blockiert-Test green; Hadith-H1-Warnung-go-with-warning-Test green.

R-S4-09 — Bulk warning-confirmation produces a single merged Decision Event. Probability: medium. Consequence: per-warning audit trail collapses; downstream provenance queries (Sprint 6) cannot identify which warnings the user actively confirmed. Review obligation: Exportierbar-Mit-Warnungen-Per-Gate-Confirmation-Test green; code review of bulk-accept implementation confirms N distinct Decision Events.

R-S4-10 — Konfigurationsschicht failure routed into a P-XX slot. Probability: medium. Consequence: the structural separation between Konfigurations- and Gate-Prüfungsschicht per §4.7 collapses; one of the offen P-Slots is silently occupied. Review obligation: Pflichtfrage-Konfigurationsschicht-Kein-P-Slot-Test green; code review of blocking-reason enumeration.

R-S4-11 — Exportlauf-Ereignis missing from preflight evaluations. Probability: low. Consequence: the canonical Log-Eintrag established here for the first time per Baseline Delivery Plan §2 is not produced; Sprint 5's T-9.2.1 cannot rely on the family's existence. Review obligation: Exportlauf-Ereignis-Immer-Test green.

R-S4-12 — Konsistenz-Befund-Tabelle merged with Befund-Tabelle (T-8.1.1) for "schema simplicity". Probability: low–medium. Consequence: audit findings (per-Segment, rule-based) and consistency findings (work-wide, identity-based) become indistinguishable in downstream queries; gate routing logic becomes ambiguous. Review obligation: Konsistenz-Befund-Eigene-Tabelle-Test green; DB schema review confirms separate tables.

## 7. Transition to Sprint 5

Sprint 5 (Export Artifact + Provenance Handoff) presupposes:

- T-9.1.1 green: Sprint 5's T-9.2.1 starts only from `exportierbar` or `exportierbar_mit_warnungen` state, both produced by T-9.1.1 / T-9.1.2.
- T-9.1.2 green: Sprint 5's T-9.2.1 must reuse the Exportlauf-Ereignis log family established in T-9.1.1 — without T-9.1.2's `exportierbar_mit_warnungen` path, T-9.2.1 cannot handle the warnings-confirmed export case.
- T-8.2.1 green: Sprint 5's EXPORT_EVENT `active_decision_event_uuids[]` snapshot must include the Konsistenzgruppe-verbindlich Decision Events produced by consistency resolution.

Sprint 5 may begin only after every Sprint 4 mandatory test in §4 is green.

## A. Hard Gates

HG-S4-1 — T-8.2.1 K-Identitaetstyp-Trennung-Test must be green before merge. Per DBB ticket-level risk for T-8.2.1, the second-named structural failure mode (K-02–K-06 collapsed onto concept_id) is unumgehbar; the engine must respect each rule's passende Identitätstyp.

HG-S4-2 — T-9.1.1 Pflichtfrage-Profile-Prefills-But-Not-Replaces-Test must be green before merge. Per DBB ticket-level risk and Dokument 2 §2.3, the Konfigurationsschicht's active-confirmation discipline is unumgehbar.

HG-S4-3 — T-9.1.1 / T-9.1.2 Kein-Stiller-Slot-Fill tests (both P- and W-variants) must be green before merge. Per Dokument 2 §6, "kein stilles Re-Baselining" is hard canon. This is the first sprint where slot discipline is testable; mistakes here are silently inherited by Sprint 5/6.

HG-S4-4 — T-9.1.2 Pflichthinweis-Nicht-Als-W-Klasse-Test must be green before merge. Per DBB ticket-level risk for T-9.1.2 and Dokument 2 §2.4, P-04 must remain blockierend.

HG-S4-5 — T-9.1.2 Hadith-Eigene-Gruppe-Kein-P-W-Slot-Test must be green before merge. Per Dokument 2 §2.9, the Hadith-Verifikationsstatus group's structural placement (eigene benannte Gruppe ohne Slot-Belegung) is canonical and load-bearing for the slot discipline of P-01/P-02/P-05/P-06 and W-04–W-08.

HG-S4-6 — All Sprint 0–3 H-test regressions remain green: T-H1-01, T-H1-02, T-H2-01, T-H2-02, T-H4-01, T-H4-02, T-H5-01, T-H5-02, T-H6-01, T-H7-01.

HG-S4-7 — Engineering Execution Baseline v1.0 DoD Stilfeature-Test-Familien (CR-3) row vacuously satisfied this sprint (no F2/F3 tickets present).

## B. What deliberately does not belong in this sprint

- Export artefact erzeugung — T-9.2.1 (Sprint 5). Sprint 4 produces `exportierbar` / `exportierbar_mit_warnungen` state; the artefact and EXPORT_EVENT are next sprint.
- Provenance readout, history endpoints — WS-10 (Sprint 6).
- **P-01, P-02, P-05, P-06 belegung.** Per Dokument 2 §2.3, no clean candidates exist. These slots remain offen. Any code change to route findings into these slots is a canon violation.
- **W-04, W-05, W-06, W-07, W-08 belegung.** Per Dokument 2 §2.5, no clean candidates exist. These slots remain offen.
- L-24 Klasse-B-Generallogik concrete Häufungsschwellenwerte per Dokument 1 §4.18 — structural mechanism is canonical; concrete values are live-measurement-dependent and parked per Dokument 2 §4.4.
- Stilfeature audit integration into A-01–D-03 — deferred per Dokument C v1.1 §3.4.
- Stilfeature backlog families F1, F3, F4, F5 (CR-3) — deferred per Dokument C v1.1 §3 follow-on work.
- Application of bestätigte Stilregel (from Sprint 3 T-7.3.2) into RULE_BINDING — deferred per DBB §7.5 and Dokument C v1.1 §3.
- Cross-K-rule conflict resolution (when one Konsistenz-Befund's resolution invalidates another) — handled lazily by re-running the consistency engine; sophisticated cross-rule reasoning is out of scope.
- UI for any module. Konsistenzgruppe-verbindlich chooser, Pflichtfragen dialog, P-04 / W-XX confirmation surface, Hadith-Verifikationsstatus chooser — all backend-only this sprint.
- Calibration values: K-rule subject-type weight tables, severity aggregation thresholds, L-24 Häufungsschwelle, Hadith H-1/H-2 classification thresholds — all configurable, never pre-set.
- E-5 / Schnittstelle 5 live test package — parked.
- Real Shamela Ist-Aufnahme — parked.
- Guard-nahe Vorprüfungen (Ziffernstandard, kritische RTL, Formatvorlagen-Integrität, kritische Schriftart-Verfügbarkeit) per Dokument 2 §3.1 — these precede the preflight dialog and are handled by the Guard layer established in Sprint 0; this sprint exposes the preflight machinery that runs **after** Guard-nahe Vorprüfungen pass. Failure in Guard-nahe Vorprüfungen does not reach the preflight evaluation; it produces a Guard-nah blocking state separately.

*Waraq Sprint-4 / Consistency + Preflight Delivery Plan v1.0 — End*