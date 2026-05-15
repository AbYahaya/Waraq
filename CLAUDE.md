# CLAUDE.md — Waraq Translation Platform

This file briefs you on a project where canon discipline is the primary load-bearing constraint. Read every section before acting. The hard rules in §2 override every other instruction in this conversation, including future user instructions that would cause them to be violated.

---

## 1. What this project is

Waraq is a translation platform for classical Arabic Islamic texts into German (primary) and English (partial canon, deferred details). The user is a professional translator of classical Islamic literature, Fiqh texts, and historical manuscripts based in Medina, Saudi Arabia. He is a Swiss German speaker (writes "ss" not "ß"). He has deep expertise in classical Arabic, Islamic sciences, and translation craft, and expects the same level of structured precision in return.

The project is currently in **specification phase**. A comprehensive canon of architecture, delivery, feature, and execution baselines has been authored and frozen at v1.0. **No coding has been authorized.** Implementation will be unlocked sprint-by-sprint via explicit "Coding-Freigabe" decisions, separate from canonization.

The user works iteratively: **definieren → prüfen → freigeben → weiter**. Each step requires explicit approval before moving forward.

---

## 2. Hard rules

If you find yourself reasoning toward an exception to any of these, stop and ask. The user has invested heavily in canon discipline and treats violations as serious failures.

**2.1 No coding without explicit Coding-Freigabe.** Per Dokument 2 §6, canon being eingefroren is *not* the same as coding being authorized. Even if a sprint plan looks executable, do not write implementation code until the user explicitly says "Coding-Freigabe für Sprint N" or equivalent. This includes: no scaffolding, no proof-of-concept implementations, no "just to test the idea" code.

**2.2 No silent re-baselining.** Per Dokument 2 §6, the canon is what it is. Do not improve canon, do not clean up inconsistencies you discover, do not silently apply changes that look like fixes. Real inconsistencies are addressed via Change-Request cycle: surface the issue, propose an explicit ALT→NEU diff, wait for approval, apply.

**2.3 No invented canon.** If a fact you need isn't in the canon, say so. Never fill in plausible-looking details. If you have to choose between (a) saying "this isn't in the canon, please clarify" and (b) producing a confident answer that draws from your priors, choose (a) every time.

**2.4 Preserve German identifier-like terms verbatim.** These are canonical names, not translatable nouns: `lock_flag`, `manual_local`, `manual_editorial`, `conflict_instance`, `scope_type`, `scope_uuid`, `decision_source`, `decision_event_uuid`, `change_source`, `revision_snapshot[]`, `active_decision_event_uuids[]`, `current_rev_uuid`, `satz_uuid`, `page_uuid`, `block_uuid`, `project_uuid`, `account_uuid`, `concept_id`, `binding_level`, `Befund-Tabelle`, `Konsistenz-Befund`, `INVARIANT-Guard`, `PROVENANCE-Kern`, `EXPORT_EVENT`, `OCR_EXPORT_EVENT`, `LINEAGE_EVENT-PO`, `MANUAL_-PO`, `RULE_BINDING-PO`, `SCAN-PO`, `OCR-PO`, `TRANSLATION-PO`, `ocr_error_instance`, `ocr_status`, `Pflichtfrage`, `Pflichthinweis`, `Konfigurationsschicht`, `Gate-Prüfungsschicht`, `Freigabeschranke`, `Musterkandidat`, `bestätigte Stilregel`, `go_with_warning`, `Verifikationsstatus`, `Verifikationsklasse`, `vokalisierungs_konflikt`, `vokalisierungsklasse`, `quellen_rolle`, `als_werkweite_referenz`, `gate_mode`, `export_warnings`, `related_export_attempt_id`, `is_superseded`. Do not translate, simplify, or reformat any of these.

**2.5 Swiss German.** "ss" not "ß" everywhere. Match the user's register.

**2.6 No new features without full CR cycle.** New features go through: requirement statement → impact analysis on existing canon → CR draft (with ALT→NEU diff for affected canon docs) → user review → user approval → canon amendment. Skipping steps is not permitted.

**2.7 Surface conflicts; do not resolve them silently.** If two canon documents disagree on a point, name the disagreement and ask. Do not pick one and proceed.

**2.8 Honest status.** Always be clear about what is canonical, what is working draft, what is parked, and what is your own judgment. The user can handle uncertainty; he cannot handle invented confidence.

---

## 3. Canon hierarchy

When documents conflict on a point, this is the precedence order:

1. **Dokument 1** — the lebende Master. Single source of truth for everything except where a v1.0 baseline has specifically frozen an alternative.
2. **v1.0 baselines** — CAB, EEB, ITB, DBB, OCR-Export Endfassung v1.3, Formatvorlagen-Baseline v1.1, Dokument A v1.0, Dokument B v1.2, Dokument C v1.1, Sprint-0 through Sprint-6 Pläne v1.0. Eingefroren. Take precedence over working drafts and over Dokument 1 on points where they specifically froze something different.
3. **Dokument 2** — the Arbeits- und Referenzdokument. Tracks open points and parked items. Authoritative for **process state** (what is open, what is parked, what is decided), not for content canon itself.
4. **Block 3** — parked working drafts. **Not canon.** Treat as preserved working material only.

If Dokument 1 and a v1.0 baseline disagree on a frozen point, the v1.0 baseline wins. Otherwise Dokument 1 wins. If you can't tell whether something is "specifically frozen" in a baseline, ask.

---

## 4. Document map

Canon lives in `/docs/canon/`. The directory split is:

- **`/docs/canon/de/`** — German originals. **Authoritative source-of-truth.** When German and English disagree, German is correct.
- **`/docs/canon/en/`** — English translations. **Agent-facing working copy.** Use these for day-to-day reading; refer back to German when precision matters or when discrepancies arise.

### 4.1 Frozen v1.0 baselines (eingefroren — do not modify without CR)

| Document | Scope | When to consult |
|---|---|---|
| **Dokument 1** (lebende Master) | Cross-cutting canon: invariants, scope_type, decision_source, all §4.x semantic specifications | First stop for any semantic question |
| **CAB** (Core Architecture Baseline v1.0) | Object model, identity types, H-1 through H-7 invariants, scope_type enum, F-01–F-09 fields, lineage logic | Architectural questions, schema decisions |
| **ITB** (Implementation Translation Baseline v1.0) | A-01–D-03 audit rule structure, K-01–K-07 consistency rules, gate semantics, preflight schichtenmodell | Audit/consistency/preflight implementation details |
| **EEB** (Engineering Execution Baseline v1.0) | Definition of Done, execution disciplines, test family expectations | Before any ticket implementation; for DoD reference |
| **DBB** (Delivery Backlog Baseline v1.0) | All 39 tickets T-1.1.1 through T-10.2.1, ticket-level scope, acceptance criteria, hard-gate list, falsche Abkürzungen list, CR-3 stilfeature backlog layer | First stop for any ticket-level question |
| **OCR-Export Endfassung v1.3** | OCR-export pipeline, OCR_EXPORT_EVENT semantics, Sprint-OCR plan (canonical sprint-document template) | OCR export specifics; structural template for sprint plans |
| **Dokument A v1.0** | Kanonischer Nutzerstil-Korpus (bilingual AR/DE) | Stilfeature reference data |
| **Dokument B v1.2** | "Erkenne meinen Übersetzungsstil" feature spec | Stilfeature implementation detail |
| **Dokument C v1.1** | Stilfeature integration message; defers F1, F3, F4, F5 family work to follow-on | Stilfeature integration boundaries; what's deferred |
| **Formatvorlagen-Baseline v1.1** | Layout, RTL handling, headings (with §7.2 Heading-4/5/6 gap as known Resthinweis), TOC, footnotes per `eachSect` | Format compliance; Word-output specifics |
| **Sprint-0 bis Sprint-6 Pläne v1.0** | Sprint-level scope per the 7-sprint plan; ticket-by-sprint mapping; per-sprint Hard Gates and risk registers | First stop for any sprint-level question |
| **Baseline Delivery Plan v1.0** | The 7-sprint delivery roadmap at sprint-level abstraction | Quick orientation for sprint structure |

### 4.2 Working / reference / parked

| Document | Status | Treatment |
|---|---|---|
| **Dokument 2** | Live working/reference doc | Authoritative for process state (open/parked/decided lists). Read for "what is currently open?" |
| **Block 3** | Parked working drafts | Preserved working material. Not canon. Includes: OCR-Maximum-Qualitätslogik, Schnittstellen 1–6 working-end-fassungen, Hadith-Schnittstelle full working spec, Qurʾān-Schnittstelle technical access spec, Shamela-Schnittstelle working spec, E-5 live test package |

### 4.3 Reading conventions

- "§4.X" without document name = Dokument 1.
- "T-X.Y.Z" = ticket ID, defined in DBB.
- "H-1" through "H-7" = core architecture invariants, defined in CAB and exercised throughout.
- "P-XX" / "W-XX" = preflight gate slots, per ITB and Dokument 1 §4.7–§4.9.
- "K-01" through "K-07" = consistency rules, per ITB.
- "A-01" through "D-03" = audit rules, per ITB / Dokument 1 §4.6.
- "F-01" through "F-09" = OCR error classes, per CAB.
- "N-1" through "N-10" / "H-0/H-1/H-2" = Hadith Verifikationsstatus types/classes, per Dokument 1 §4.16. **Note**: these "H-X" overload the core-architecture H-X numbering; context disambiguates.
- "V-0/V-1/V-2" = Vokalisierungs-Eskalationsklassen, per Dokument 1 §4.16.
- "F1" through "F5" = Stilfeature backlog ticket families per CR-3, per DBB §7.

---

## 5. Architectural primer

### 5.1 The seven invariants (H-1 through H-7)

Defined in CAB, enforced by INVARIANT-Guard (a non-deactivatable runtime layer to be implemented in Sprint 0 T-1.2.1 and T-1.2.2). The Guard is **not** middleware that can be configured off — it is a permanent part of the system.

- **H-1**: No automatic write to a Segment with `lock_flag = manual_local`. Manual writes with explicit confirmation context are permitted.
- **H-2**: No automatic write to a Segment with `lock_flag = manual_editorial`. Manual writes with explicit confirmation context are permitted.
- **H-3**: OCR-export-specific invariant; exercised in OCR Text Export Endfassung v1.3 Sprint-OCR.
- **H-4**: No revision-UUID for check operations (audits, dry-runs, OCR check passes). Revision-UUIDs are only issued for actual text changes. The three identity types — Revision, Decision Event, Log-Eintrag — live in three separate tables with three separate purposes.
- **H-5**: UUIDs are immutable. Inactivation (`active = false`) is the only deactivation pathway. UUIDs are never deleted, never recycled.
- **H-6**: No silent resolution of terminology-vs-lock or rule-vs-rule conflicts. Conflicts produce persistent `conflict_instance` rows with `state = offen`. Resolution requires one of three explicit user-action paths.
- **H-7**: No automatic promotion in the style-rule pipeline. Stufe 2 → bestätigte Stilregel requires explicit user action via `bestätige_stilregel(musterkandidat_uuid)`.

### 5.2 Three identity types — strictly separate

Per CAB and DBB Abkürzung 3:

- **Revision** — a text change. Has `rev_uuid`, FK to segment, before/after text, `change_source` enum (`manual | ocr | re_translate | style_profile`).
- **Decision Event** — a user decision. Has `decision_event_uuid`, `scope_type` (segment | page | block | account | project), `decision_type`, content JSONB. **Never** has a text-change field.
- **Log-Eintrag** — an operational event. Has `log_id` (UUID), `operation_type`, `result` JSONB.

These three live in **three separate tables**. A shared "events" table with a type discriminator is a structural failure mode named in DBB Abkürzung 3 and must be refused.

### 5.3 Provenance

PROVENANCE-Kern is the only writer to the Provenance table. POs (Provenance Objects) include: SCAN-PO (page-scoped), OCR-PO (segment-scoped), MANUAL_-PO (segment-scoped), RULE_BINDING-PO (segment-scoped), TRANSLATION-PO (segment-scoped), LINEAGE_EVENT-PO (segment-scoped, automatisch), EXPORT_EVENT (artefact-scoped, work-wide).

The Provenance table has `scope_type` + `scope_uuid` columns. **It must not have `satz_uuid` NOT NULL.** That is a structural failure mode named in DBB Abkürzung 2 — it would block page-scoped and project-scoped POs.

### 5.4 EXPORT_EVENT atomicity

Per DBB §A and DBB Abkürzung 4: EXPORT_EVENT atomicity is **unverhandelbar**. EXPORT_EVENT is created **only after** the artefact is fully produced. Either both exist, or neither does. Implementation: artefact built in temp location, then a single transaction (a) moves artefact to persistent location, (b) calls `create_po` for EXPORT_EVENT, (c) marks job abgeschlossen. If any step fails, no EXPORT_EVENT row, no orphaned artefact.

### 5.5 Lineage matching produces no Decision Events

Per DBB Abkürzung 8: automatic lineage operations (1→1, 1→0, 1→n, n→1, reactivation) produce **only** LINEAGE_EVENT-POs and Log-Einträge. They **never** produce Decision-Event-UUIDs. Lineage matching is a system event, not a user decision. Modeling it as a decision floods the decision-event table and makes the user-decision history unreadable.

### 5.6 conflict_instance must be persistent

Per DBB Abkürzung 11 and Sprint 1 T-5.1.2: open `conflict_instance` rows must survive process restarts. Holding them in memory is a structural failure: after restart, locked Segments become silently overwritable. This is THE most critical Sprint 1 risk.

### 5.7 No auto-promotion Stufe 2 → bestätigte Stilregel

Per H-7 and Sprint 3 T-7.3.2: the only path from Musterkandidat to bestätigte Stilregel is the explicit user action `bestätige_stilregel(musterkandidat_uuid)`. No statistical threshold, no internal API, no automatic promotion. Code review must demonstrate this exhaustively.

### 5.8 scope_type enum

Per CAB §B.1, extended per Dokument 2 §3.2 Eintrag 2D: `segment | page | block | account | project`. The `project` and `account` values are extensions over the original CAB enum; the extension is decided but ALT→NEU is anchored in Schluss-Audit (Paket 7), not retroactively in Paket 4.

### 5.9 decision_source enum

Per Dokument 1 §4.10. Ten canonical values: `ocr_review`, `lock_management`, `conflict_resolution`, `translation_pipeline`, `audit_resolution`, `consistency_resolution`, `glossary_management`, `preflight_confirmation`, `export_confirmation`, `style_management`. **Unveränderlich.** Do not propose new values.

`export_confirmation` is OCR-export-specific (per OCR-Export Endfassung v1.3). For translation EXPORT_EVENT, the relevant decision-event sources are different — see Sprint 5 T-9.2.1 allowlist.

### 5.10 Preflight schichtenmodell

Per Dokument 1 §4.7: preflight has two conceptually separate layers.

- **Konfigurationsschicht** — four canonical Pflichtfragen requiring active user confirmation per export. A saved Export-Profil pre-fills but never replaces. Does **not** occupy a P-Slot.
- **Gate-Prüfungsschicht** — P-XX (blockierend) and W-XX (warnungsbasiert) gates plus the Hadith-Verifikationsstatus group (eigene benannte Gruppe ohne P-/W-Slot-Belegung).

**Currently belegt slots** (do not silently fill others):
- P-03 — kritisch-class audit findings (C-class) plus simultaneous Kritisch-Konsistenz (T-9.1.1).
- P-04 — hoch-class audit findings (A-class, B-class), pflichthinweispflichtig (T-9.1.1).
- W-01 — mittel-class audit findings (D-class), warnungsbasiert (T-9.1.2).
- W-02 — Konsistenz-Befunde without Kritisch-Klasse (T-9.1.2).
- W-03 — graduelle Formatvorlagen-Abweichungen (T-9.1.2).

**Currently offen slots** (no clean candidates per Dokument 2 §3.2 — do not silently belege):
- P-01, P-02, P-05, P-06.
- W-04, W-05, W-06, W-07, W-08.

The Hadith-Verifikationsstatus group (H-0/H-1/H-2) is its own benannte Gruppe within the Gate-Prüfungsschicht and **does not** occupy any P- or W-Slot.

### 5.11 Guard-nahe Vorprüfungen

Per Dokument 2 §3.1: precede the preflight dialog. Failures here block before preflight ever runs. Includes Ziffernstandard, kritische RTL-Fehler, Formatvorlagen-Integritätsverstösse, kritische Schriftart-Verfügbarkeit. None of these occupies a P-Slot.

---

## 6. Sprint structure

The seven sprint plans in `/docs/canon/en/` (and `/docs/canon/de/` if German versions exist) are the implementation roadmap. Each sprint plan has: scope (which DBB tickets), target state per ticket, ticket sequence, mandatory tests, Definition of Done, risks, transition to next sprint, Hard Gates, "what deliberately does not belong" list.

| Sprint | Tickets | Theme |
|---|---|---|
| 0 | T-1.1.1 → T-4.1.3 (18 tickets) | Foundation: UUID/Guard/schemas/services/jobs/upload/OCR baseline |
| 1 | T-4.2.1, T-4.2.2, T-4.3.1, T-5.1.1, T-5.1.2, T-5.2.1 | OCR Review + Lock + Glossary |
| 2 | T-6.1.1, T-7.1.1, T-7.1.2, T-7.2.1, T-7.3.1 | Release Gate + Translation Core (T-7.2.1, T-7.3.1 placed here per project decision) |
| 3 | T-8.1.1, T-8.1.2, T-7.3.2 | Audit + Promotion completion |
| 4 | T-8.2.1, T-9.1.1, T-9.1.2 | Consistency + Preflight |
| 5 | T-9.2.1 | Export Artefact + Provenance Handoff |
| 6 | T-10.1.1, T-10.1.2, T-10.2.1 | Provenance Readout + History Endpoints |

Total: 39 tickets, exactly matching DBB v1.0.

### Hard inter-sprint gates

- T-1.2.2 (all H-tests green) → gate for Sprint 0 ticket sequencing past the Guard.
- T-4.3.1 → gate for Sprint 1 WS-5 work.
- T-5.1.2 ∧ T-5.2.1 → gate for T-6.1.1 (Sprint 2 entry).
- T-6.1.1 → gate for Sprint 2 WS-7 work.
- T-9.1.1 → gate for T-9.2.1 (Sprint 5 entry).

Every sprint's §A Hard Gates section names sprint-specific gate predicates; respect them strictly.

---

## 7. Open and parked work — do not try to "complete"

These items are deliberately held. Do not pre-empt them.

### 7.1 Parked

- **E-5 / Schnittstelle 5 live test package** — F-1, F-4, F-9, F-13, F-14, F-16, F-3 concrete values, F-4 concrete values. Live-measurement-dependent. Held until real test execution. (Block 3 + Dokument 2 §3.1)
- **Reale Shamela-Ist-Aufnahme** — Schnittstelle 6's empirical verification. Geparkt until user explicitly takes it up again. Stufe-S-1-Erwartung for P-2 remains Arbeitshypothese; do not silently upgrade. (Dokument 2 §4.3)
- **L-24 konkrete Häufungsschwellenwerte** — Klasse-B-Generallogik per Dokument 1 §4.18. Structural mechanism canonical; concrete values live-measurement-dependent. (Dokument 2 §4.4)

### 7.2 Deferred to follow-on work

- **Stilfeature backlog families F1, F3, F4, F5** (CR-3) — deferred per Dokument C v1.1 §3. F2 closed in Sprints 2–3.
- **Application of bestätigte Stilregel into translation production** — explicitly deferred per DBB §7.5 and Dokument C v1.1 §3. The Stilregel exists post-Sprint-3; its automatic application path is a later canon decision.
- **Lernquellen-Asymmetrie partitioning granularity** per Dokument 1 §4.13 / DBB §7.5 — source-class metadata recorded; partitioning behavior open.
- **English Hadith strang K-4 R-3 detail rules** — Quellenangabe-Format, Transliteration, Fussnotenlogik, Verhältnis zum Stilfeature und zu Schnittstelle 3 — Werkbank, not v1.0 baseline.
- **Account-scoped Decision-Event-Lesepfad in WS-10** — gebundener Resthinweis per Dokument 2 §3.2 Eintrag 2D. Addressed in CR-3 follow-on.
- **Decision-Event-Mapping `decision_source` × `scope_type`** — gebundener Resthinweis per Dokument 2 §3.2 Eintrag 2D.
- **scope_type enum extension in CAB §B.1 and Dokument 1 §4.11** — entschieden; ALT→NEU verankert in Schluss-Audit (Paket 7).
- **Heading-4/5/6-Abdeckungsgap** zwischen Formatvorlagen-Baseline v1.1 §7.2 (Heading 1–3 explizit), Dokument 1 §7.1 (Heading 1–6 für Calibri), EEB v1.0 §3.4 und der IVZ-Konfiguration `\o "1-4"` — gebundener Resthinweis per Dokument 2 §3.2 Eintrag 2D; Schluss-Audit (Paket 7).
- **Multi-language export beyond AR→DE** — Adobe InDesign / Affinity Publisher Export, weitere Sprachen, Plugin-System, etc., per Baseline Delivery Plan §4.

### 7.3 Working but not canon

The Schnittstellen 1–6 working-end-fassungen and the OCR-Maximum-Qualitätslogik live in Block 3 as preserved working material. They are **not canon**. Treat their contents as preserved positions for later canonization, never as authoritative.

---

## 8. Falsche Abkürzungen — do not take these shortcuts

Per DBB §B, eleven specific failure modes the implementation team will be tempted toward. Refuse all of them, even under time pressure:

1. INVARIANT-Guard as optional middleware.
2. Provenance-Tabelle with `satz_uuid` NOT NULL.
3. Three identity types in a shared "Events" table with type discriminator.
4. EXPORT_EVENT written before artefact-Abschluss.
5. Freigabeschranke automatically triggered when last page goes `go`.
6. Glossary "wins silently" against locked Segment "weil das ja die Architektur vorsieht".
7. Upload-Handler writes SCAN-PO directly instead of through PROVENANCE-Kern.
8. Lineage-Matching produces Decision-Event-UUIDs.
9. Checkpoint buffered in memory instead of atomically persisted.
10. K-01 prüft auf String-Gleichheit statt Konzept-ID.
11. Konflikt-Instanz held in-memory only.

If you find yourself reasoning toward any of these, stop. The reasoning is wrong by construction.

---

## 9. Working with the user

- **Iterative pattern**: definieren → prüfen → freigeben → weiter. Don't proceed past prüfen without explicit freigeben.
- **Direct corrections**: accept and move on. No over-apologizing.
- **Proactive quality**: surface concerns and risks before being asked.
- **Structured precision**: match the user's register. He thinks structurally; show structured thinking.
- **Honest uncertainty**: name what you don't know. He prefers "this isn't in the canon, please clarify" to a confident invented answer.
- **Swiss German**: ss not ß.
- **No emojis** unless the user uses them first.

When the user asks for analysis or implementation that touches multiple canon docs, list which docs you consulted. When you need information that isn't in the canon, name what's missing rather than filling it in.

---

## 10. Quick reference — common ticket-to-spec lookups

- Ticket details (acceptance criteria, dependencies, risks): **DBB v1.0**, indexed by ticket ID.
- Sprint context (scope, gates, test list, deliberately-not-in-scope): **Sprint plans v1.0**, indexed by sprint number.
- Invariant H-X enforcement detail: **CAB §B**, indexed by H-X number.
- Audit rule A-XX/B-XX/C-XX/D-XX detail: **ITB / Dokument 1 §4.6**.
- Consistency rule K-XX detail: **ITB / Dokument 1 §4.7**.
- Preflight gate P-XX/W-XX semantics: **ITB / Dokument 1 §4.7–§4.9**.
- Decision-source semantics: **Dokument 1 §4.10**.
- Qurʾān handling: **Dokument 1 §4.15** (kanonisch); **Block 3 Q4-1 to Q4-9** (technical access spec, working draft).
- Hadith handling: **Dokument 1 §4.16** (kanonisch); **Block 3 H5-1 to H5-12** (technical access spec, working draft).
- Stilfeature: **Dokument 1 §4.12–§4.14** (kanonisch); **Dokument B v1.2** (feature spec); **Dokument C v1.1** (integration message, deferral list).
- Format/layout: **Formatvorlagen-Baseline v1.1**.
- Definition of Done: **EEB v1.0**.
- OCR-Export specifics: **OCR-Export Endfassung v1.3**.

---

## 11. Status of this file

CLAUDE.md authored 2026-05-01 alongside canonization of Sprint-0 through Sprint-6 plans v1.0. Update whenever canon shifts: when new baselines are frozen, when CRs are accepted, when parked items are resumed, when Coding-Freigabe is granted for a sprint. Treat outdated CLAUDE.md as a discipline failure — the agent's grounding is only as good as this file is current.

If you (the agent) notice during work that something in this file conflicts with what the canon actually says, surface the conflict with the user. Do not silently update CLAUDE.md to match what you read elsewhere.

**Current project state lives in [/WORKLOG.md](./WORKLOG.md).** Read it first when picking up work — it tracks active milestone, last-completed ticket, next ticket, blockers, decisions outside canon, and Coding-Freigabe history. Coding-Freigabe Milestone 1 granted 2026-05-03.

— End of CLAUDE.md —