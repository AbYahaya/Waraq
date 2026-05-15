# Waraq Project Milestones

Client-facing delivery breakdown agreed 2026-05-03. Day budgets are the
agreed-with-client commitment. Canon mapping below is the internal execution
plan that operationalizes each milestone against the [canonical sprint set](docs/canon/de/baseline_delivery_plan_v1_0.md).

For *current state* (what's done, what's next, blockers): see [WORKLOG.md](./WORKLOG.md).

---

## Milestone 1 — Foundation / Architecture (4–5 days)

- User / Account system
- Project system (one book = one project)
- Database structure (Projects, Users, Revisions, Decision Events, Logs)
- UUID system (project, page, segment, etc.)
- File upload & storage
- Basic API structure
- Authentication (login, security)
- Basic admin structure
- Project lifecycle (create, open, save, delete, trash)
- *etc.* (all foundational system elements described in the project documents)

## Milestone 2 — Core Backend / Waraq Logic (10 days)

- Decision Event system
- Revision system
- Log system
- Segment / Page / Block / Sentence handling
- Lock system (segment-level editing protection)
- History tracking (segment, page, project)
- Reference / entity system
- Conflict handling (go / warning / blocked states)
- Guard-related backend structure
- Prevention of unwanted overwrites
- *etc.* (all core logic and rules defined in the project documents)

## Milestone 3 — OCR + Translation Pipeline (7 days)

- File upload (PDF / image)
- OCR integration
- Page detection and OCR output per page
- Block detection (main text, footnotes, headings, Qurʾān, Hadith, etc.)
- OCR review structure
- Sentence segmentation
- Chunking + context handling
- Translation pipeline (AI integration)
- Connection between OCR and translation
- Glossary influence on translation
- Qurʾān handling according to system rules
- Hadith verification structure
- Progress tracking
- Error handling (API failures, retries)
- Background processing (jobs)
- *etc.* (all pipeline-related functionality described in the project documents)

## Milestone 4 — Frontend / UI / Editor (7 days)

- Dashboard (projects, uploads, status)
- Main editor interface
- Arabic view
- Translation view
- Comparison view
- Original scan vs OCR comparison
- Page navigation
- Segment editing
- Morphology feature (click Arabic word → analysis)
- Word analysis (root, form, meaning, etc.)
- Interactive UI elements (click, highlight, sync)
- Admin panel
- *etc.* (all UI/UX and interaction features described in the project documents)

## Milestone 5 — Export / Preflight / Testing / Go-Live (14 days)

- Preflight system
- Export validation (critical / warning states)
- Guard checks (format, RTL, fonts, etc.)
- Hadith verification status integration
- Consistency checks
- DOCX export
- PDF export (digital & print base)
- OCR text export (separate)
- Headers, footnotes, section handling
- Format templates implementation
- Export logs
- Download system
- Shamela database
- Deployment (live website)
- Bug fixing & final testing
- End-to-end test with real document
- *etc.* (all export, validation, and deployment features described in the project documents)

---

**Total: 4.5 + 10 + 7 + 7 + 14 = ~42.5 days.**

---

## Mapping to canonical sprints

The canon defines an 8-sprint set (Sprint 0–6 + Sprint-OCR per [OCR Text Export Endfassung v1.3 §5](docs/canon/de/ocr_text_export_v1_3.md)) totalling 43 tickets. The milestones above re-organize that work for client delivery; this table shows what canonical work each milestone executes against.

| Milestone | Canon coverage | Tickets |
|---|---|---|
| **M1** | Pre-sprint setup + Sprint 0 | T-1.1.1 → T-4.1.3 (18 tickets) + auth scaffolding (Sprint −0.5) |
| **M2** | Sprint 1 + parts of Sprint 4 (consistency engine) + parts of Sprint 6 (lightweight history queries) + §4.19 Reference/Entity | T-4.2.1, T-4.2.2, T-4.3.1, T-5.1.1, T-5.1.2, T-5.2.1, T-8.2.1 (consistency), §4.19 reference data |
| **M3** | Sprint 2 + Sprint-OCR | T-6.1.1, T-7.1.1, T-7.1.2, T-7.2.1, T-7.3.1, T-OCR-EX-1, T-OCR-EX-2, T-OCR-EX-3 |
| **M4** | **Outside v1.0 canon** — product expansion stage per [Baseline Delivery Plan §4](docs/canon/de/baseline_delivery_plan_v1_0.md) | UI for all canonical phases (no canon tickets; built on top of M1+M2+M3 backend APIs) |
| **M5** | Sprint 3 + Sprint 4 + Sprint 5 + Sprint 6 + deployment + Shamela | T-7.3.2, T-8.1.1, T-8.1.2, T-9.1.1, T-9.1.2, T-9.2.1, T-10.1.1, T-10.1.2, T-10.2.1, T-OCR-EX-4 + Shamela (Schnittstelle 6) + go-live |

---

## Items in the milestone list that are outside v1.0 canon

These are scope items the user added beyond the canonical 43-ticket set. Each is
documented here so we don't silently re-baseline the canon.

| Item | In which milestone | Canon position | How handled |
|---|---|---|---|
| **User auth (login, security)** | M1 | Not in DBB Sprint 0; canon mentions Tier 0/1/2 in [Dokument 1 §2.3](docs/canon/de/dokument_1.md) | Built as **Sprint −0.5** scaffolding (FastAPI + bcrypt + JWT). Account_uuid integrates with canonical scope_type='account'. Not a canon amendment. |
| **Admin panel UI** | M1, M4 | §4.18.3 canonizes the Admin-Optimierungs-Eingabekanal (backend) but no admin UI in Sprint plans | Backend per §4.18.3 is canon. UI version is post-canonical product layer in M4. |
| **Frontend / UI / Editor entirely (M4)** | M4 | Explicitly out of v1.0 per Baseline Delivery Plan §4: *"UI build-out... product expansion stage"* | Built as post-canonical product UI on top of canonical backend. Not a canon amendment. |
| **PDF print export (PDF/X-1a, CMYK, 3mm bleed)** | M5 | **Already canonical** per [Formatvorlagen §2.1](docs/canon/de/formatvorlagen_baseline_v1_1.md) and [EEB §2.1](docs/canon/de/engineering_execution_baseline_v1_0.md) | Full PDF/X-1a in scope: WeasyPrint/ReportLab base → Ghostscript post-process → veraPDF validate. Adds ~2–3 days within M5 budget. |
| **Real Shamela** | M5 | Canonically parked per [Dokument 2 §4.3](docs/canon/de/dokument_2.md) "bis Nutzer ausdrücklich wieder aufgreift" | **Unparked** by user 2026-05-03. Modus A (OCR-Stage-3 plausibility) + Modus B (Lexikon-Workflow) + P-2 Hadith Pflichtquelle + Lisān/Tāj as eigenständig abfragbare Einheiten per §3.5. Pending: data source decision (BOK / OpenITI / scrape). |
| **Deployment / go-live** | M5 | Not in canon as a ticket; implementation detail | Standard ops work: Docker images, hosting target, secrets management, monitoring. |
| **End-to-end test with real document** | M5 | Aligned with canon spirit but precision depends on calibration | First-draft Arabic NLP for A-01–D-03; calibration values placeholder (gold-corpus-test post-v1.0). Test demonstrates flow correctness, not linguistic precision. |

---

## Canonical items deliberately deferred from v1.0 (per canon)

These are NOT cuts I made — they're canonically deferred per the source documents:

- **Stilfeature backlog families F1, F3, F4, F5** — deferred per [Dokument C v1.1 §3](docs/canon/de/dokument_c_v1_1_integrationsnachricht.md). Only F2 (Promotion 1-2-3) is exercised in the v1.0 sprint set.
- **Application of bestätigte Stilregel into translation production** — deferred per [DBB §7.5](docs/canon/de/delivery_backlog_baseline_v1_0.md) and Dokument C v1.1 §3.
- **Stilprofile Sprachpaar-Erweiterung** (Modellfrage B.1) — open per Dokument 1 §4.12.2; building only AR_DE in v1.0.
- **Adobe InDesign / Affinity Publisher export, additional export targets** — deferred per Baseline Delivery Plan §4.
- **Multi-language beyond AR→DE** — deferred per Baseline Delivery Plan §4.
- **Calibration values everywhere** (F-class severity, OCR confidence, K-rule thresholds, Stilfeature Belegdichte, L-24 Häufungsschwellen) — post-Gold-Corpus-Tests per Baseline Delivery Plan §4. Configurable shells in v1.0 with reasonable defaults.
- **AR-Referenzbestand source naming** — open per Dokument 1 §4.15.1; needs user decision before M3 (translation pipeline). Default to Tanzil's vocalized Hafs text as placeholder otherwise.
- **Heading-4/5/6 coverage gap** — gebundener Resthinweis per Dokument 2 §2D, anchored in Schluss-Audit (Paket 7).
- **scope_type enum extension** — decided per Dokument 2 §2D; ALT→NEU verankert in Schluss-Audit. Implementation supports `account` and `project` scope_types from Sprint 0.

---

## Hard rules across all milestones (CLAUDE.md / DBB §B / CAB §I.3)

- Coding-Freigabe required per milestone. Currently granted: M1.
- All H-1 to H-7 invariant tests green at all times.
- INVARIANT-Guard non-deactivatable (no `enabled` flag, no env override, no test bypass).
- 11 falsche Abkürzungen avoided (DBB §B). 21 universal niemals-automatisch items avoided (CAB §I.3).
- No silent canon amendment. Open points → CR draft → user approval → commit.
- Three identity types in three separate tables (Revision / Decision Event / Log-Eintrag).
- Provenance: scope_type + scope_uuid; never satz_uuid NOT NULL.
- EXPORT_EVENT atomic: only after artefact fully built.
- conflict_instance persistent (restart-survival mandatory).
- No auto-promotion Stufe 2 → bestätigte Stilregel; only via `bestätige_stilregel(musterkandidat_uuid)`.
- Lineage matching produces no Decision Events.
- Swiss German "ss" everywhere; identifier-like German terms verbatim.
