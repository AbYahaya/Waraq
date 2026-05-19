# Waraq Canon Tracker

Authoritative canon-vs-implementation tracker. Created 2026-05-09 from the
full audit of [Dokument 1 §1–§7](docs/canon/en/document_1_canon_en.md).

**How to use this file**

- Every canonical item from Dokument 1 §2–§7 is listed once here, with a
  status column.
- Status keys: `✅` shipped · `⚠️` partial · `❌` not built · `🔁` deferred
  by canon (CR-cycle / calibration / parked).
- When an item ships, move it to ✅ and add the date in the *Notes*
  column. Don't delete rows — gap visibility is the point.
- When scope decisions are made (build now / defer with CR / accept gap),
  record the decision in *Notes*.
- Add new rows only for canonical items missed in this initial audit.
  Non-canonical product polish goes elsewhere (WORKLOG / MILESTONES).

For the active milestone state, ticket history, and Coding-Freigabe log:
see [WORKLOG.md](WORKLOG.md). For client-facing milestone breakdown: see
[MILESTONES.md](MILESTONES.md).

---

## Verdict in one sentence

**~25–30% of canon is built.** The structural backbone (architecture,
schemas, gates, provenance, atomicity, audit/consistency rules, history
endpoints) is complete and sound. The functional content that Dokument 1
§2 and §3 prescribe — OCR engine combination, external sources,
translation Primary/Check pipeline, style-feature application, Phases
3/4/6 of the user flow — is largely not built.

---

## What we have (canon-aligned)

| Status | Canon area | Notes |
|---|---|---|
| ✅ | §3.1 Working rules + §3.2 frozen baselines | Canon discipline, no silent re-baselining, CR cycle observed |
| ✅ | §4.1 Hard invariants H-1 through H-7 | Non-deactivatable INVARIANT-Guard, H-tests green |
| ✅ | §4.2 Governable project rules G-1 through G-4 | G-2 / G-3 wired into audit C-01 / D-03 |
| ✅ | §4.3 Core objects (Page/Block/Sentence/Revision/Decision-Event/Concept-ID) | Three identity types, three tables |
| ✅ | §4.4 OCR error classes F-01 through F-09 | F-06-QR added |
| ✅ | §4.5 Release gate logic | T-6.1.1 |
| ✅ | §4.6 Translation audit A-01 through D-03 | Sprint 3 |
| ✅ | §4.7 Preflight P/W gates (P-03, P-04, W-01, W-02, W-03) + Hadith group | Sprint 4 |
| ✅ | §4.8 Consistency K-01 through K-07 | Sprint 4 |
| ✅ | §4.9 OCR export E-1 through E-10 | Sprint-OCR |
| ✅ | §4.10 decision_source enum (10 values) | Unveränderlich |
| ✅ | §4.11 active_decision_event_uuids[] query rule | Sprint 5 |
| ✅ | §4.16.4 Hadith status N-1..N-10 + H-0/H-1/H-2 | Sprint 4 |
| ✅ | §4.16.5 Hadith 7 action types decision_source mapping | HADITH_ACTION_TYPES |
| ✅ | §4.19 Reference and entity system | M2 |
| ✅ | §5.2 Style profile objects (stil_regel, stilbeleg, stilprofil_version, referenz_paar) | Schemas; F2 promotion exercised; F1/F3/F4/F5 application path 🔁 deferred |
| ✅ | §5.4 EXPORT_EVENT schema + atomicity | Sprint 5, atomic 3-step commit |
| ✅ | §5.6 Promotion rules + state model §4.14 | Sprint 3 T-7.3.2 |
| ✅ | §7.1 DOCX quality (per-paragraph RTL OCR / per-run RTL Translation) | Word opens without repair |
| ✅ | §7.2 Document style templates Baseline v1.1 | TOC `\o "1-6"` after Schluss-Audit Item 2 (a) |

---

## Gap matrix

### Phase-level (§2.1 Phases 1–6)

| Status | Phase | Canon scope | Notes |
|---|---|---|---|
| ❌ | Phase 1 — formats | All formats (7 image, 6 doc, 5 e-book, 4 archive) | Currently PDF only |
| ❌ | Phase 1 — duplicate detection | SHA-256 primary + filename secondary; modal warning | SHA-256 computed but not used |
| ❌ | Phase 1 — 1-book modal | 1-book-at-a-time warning | |
| ❌ | Phase 1 — size limit | Max 2 GB | Not enforced |
| ❌ | Phase 1 — format logic | ZIP/RAR/CBZ/CBR sort; TXT/XML/HTML skip OCR; EPUB/MOBI direct extract; DjVu special path | |
| ❌ | Phase 2 OCR pipeline | 5-stage reconstruction + 8 engines | Single-pass Gemini call only — see §3.3/§3.4 below |
| ✅ | Phase 3 — difficulty report | Per-page + project-aggregate | *2026-05-09 (Phase 3 sub-batch D)* |
| ✅ | Phase 3 — guided review | Walk through findings systematically | *2026-05-09 (Phase 3 sub-batch D)* |
| ✅ | Phase 3 — DPI comparison view | Low DPI / high DPI side-by-side | *2026-05-09 (Phase 3 sub-batch D)* |
| ✅ | Phase 4 — TOC auto-detection | From heading levels | *2026-05-09 (Phase 3 sub-batch E)* |
| ✅ | Phase 4 — AR/DE TOC comparison + chapter-heading adjustment | | *2026-05-09 (Phase 3 sub-batch E)* |
| ✅ | Phase 4 — no-TOC fallback | Page-by-page split | *2026-05-09 (Phase 3 sub-batch E)* |
| ❌ | Phase 5 — Primary/Check parallel | GPT-4o + Gemini 2.5 Pro | Currently single `gpt-4o-mini` |
| ❌ | Phase 5 — RAG | | |
| ❌ | Phase 5 — chunk strategy | Style core / glossary / entity / semantic summary per chunk | None injected |
| ❌ | Phase 6 — email notifications | Resend wiring | Resend in deps; no flow |
| ❌ | Phase 6 — in-app notifications | User-toggleable | |
| ❌ | Phase 6 — final TOC review UI | | |

### §3.3 OCR engine combination

| Status | Engine | Canon role | Notes |
|---|---|---|---|
| ⚠️ | Gemini 2.5 Pro Vision | Main reading line | Currently `gemini-2.5-flash` (free-tier override) |
| ❌ | Google Cloud Vision (DOCUMENT_TEXT_DETECTION) | Additional reading line; especially modern Arabic | |
| ⏸️ | Manuscript/calligraphy OCR specialist engine | Manuscripts/calligraphy | *2026-05-19: prior specialist adapter/routing/diagnostics surface removed before external-tester deployment. Reason: it is not used in the current product path, adds local/deployment weight, and available pretrained models did not improve the printed-book workflow. Revisit in v2.0 only if a real manuscript corpus or trained model becomes product-critical.* |
| ❌ | Real-ESRGAN + OpenCV (adaptive) | Image preprocessing | |
| ⚠️ | CAMeL Tools | Validation (Stage 3 rule-based) | M4 morphology UI only; not in OCR pipeline |
| ❌ | Farasa | Validation (Stage 3 rule-based) | |
| ❌ | Mishkal | Validation (vocalization / Stage 3) | |
| ❌ | LayoutParser | Document structure (Stage 1) | |
| ❌ | DocTR | Document structure (Stage 1) | |

### §3.4 5-stage reconstruction pipeline

| Status | Stage | Canon scope | Notes |
|---|---|---|---|
| ❌ | Stage 1 visual structure | Reading-direction map, baseline detection, font-size mapping, decorative elements, per-block orientation, tabular detection, columns, headings, footnotes, dividers, page numbers, Qurʾān-verse blocks, marginalia. Geometric ordering + topological sort + Hough for slanted lines | |
| ❌ | Stage 2 per-block OCR | Block-level (not page-level) routing across reading lines per document type / layout / image quality / block class | Currently page-level single-engine |
| ❌ | Stage 3 triply-validated | Rule-based (Arabic grammar) + AI (GPT-4o + Gemini consensus, no winner) + statistical (Shamela) | None of three lines |
| ❌ | Stage 4 line reconstruction | Word-probability model, line-continuity, syllable separation, homoglyph correction (ر/ز, د/ذ) | |
| ❌ | Stage 5 quality check | Page-by-page completeness, char-count plausibility, multi-column structural symmetry, known-passage matching (Qurʾān/Hadith) | |
| ❌ | Overarching: no-artificial-winner | Confidence drops when competing readings remain → review | Moot — only one reading line |

### §3.5 External sources

| Status | Source | Canon role | Notes |
|---|---|---|---|
| ⚠️ | Shamela (incl. Lisān + Tāj as eigenständig abfragbar) | Mode A (OCR Stage 3 plausibility) + Mode B (translator lexical) | *2026-05-09 (Phase 2E): schema + ingest + lookup + adapter to consensus engine shipped. v1.0 OpenITI text set (10 texts): Lisān al-ʿArab + Tāj al-ʿArūs (canonical floor) + 6 Kutub-as-Sitta (necessary for §4.16.3 Kutub preference) + Muwaṭṭaʾ Mālik + al-Qāmūs al-Muḥīṭ (supplementary v1.0 implementation choices). Tables empty until user runs `scripts/ingest_shamela.py <slug> <path> <version>`.* |
| ⚠️ | quranenc.com (german_rwwad / english_rwwad) | Qurʾān citations primary | *2026-05-09 (Phase 2B): client + sync + lookup shipped (see Phase 2 pathway row).* |
| ⚠️ | sunnah.com | Hadith P-1 mandatory | *2026-05-09 (Phase 2C): client (`waraq.hadith.sunnah.fetch_hadith`) shipped; `X-API-Key` header from `SUNNAH_COM_API_KEY` env; `SunnahApiKeyMissing` Class A on empty key. Direct lookup by `(collection, hadith_number)` only — search-by-text is Phase 2F.* |
| ⚠️ | dorar.net | Hadith P-3 mandatory | *2026-05-09 (Phase 2C): primary `search_via_api` + secondary `search_via_scraping_fallback` shipped per §3.5 secondary-path rule. Scraping fallback raises `ModelUClassB(retryable=False)` immediately (DOM selectors not configured — DOM-break = Class B no-retry contract enforced by structural construction). Endpoint URL configurable via `dorar_net_base_url` setting since §3.5 declares it "fully unspecified – active work front".* |
| ❌ | islamweb.net | Scraping E-1 (currently suspended per §4.16.1) | |
| ❌ | جامع السنة النبوية | Scraping E-2 (suspended) | |
| ❌ | المكتبة الوقفية | Scraping E-3 (manual reference only) | |
| ⚠️ | AR-Referenzbestand (vocalized Qurʾān local) | Sole carrier per §4.15.1 | *2026-05-09 (Phase 2D): schema + Tanzil-Hafs ingest service shipped (see pathway row). Table is empty until user runs `scripts/ingest_tanzil_quran.py`.* |
| ⚠️ | Local fallback Qurʾān translations + weekly sync | API fallback | *2026-05-09 (Phase 2B): table + sync service + CLI driver shipped (see pathway row).* |
| ✅ | Confidence ranking + tie-breaker logic | §3.5 / §4.16.3 — *2026-05-09 (Phase 2F-B): `LINEAR_SOURCE_RANK` (quranenc=1 > sunnah=2 > Shamela=3 > dorar=4 > islamweb=5 > others=6) + `compute_consensus` applies it as the §4.16.3 tiebreak after Kutub-as-Sitta preference.* |
| ⚠️ | Request profile Model U | §3.5 (rate / pause / upper limits) | *2026-05-09 (Phase 2C): structural mechanism shipped (`waraq.external.model_u_fetch` + `ModelURequestProfile`). All external HTTP routes through it. Concrete rates/pauses/upper-limits remain calibration-deferred per canon ("remain open and will be set after real measurement").* |
| ⚠️ | Scraping secondary-path rule | DOM break = §4.18 Class B no retry | *2026-05-09 (Phase 2C): canon mechanism enforced via `ModelUClassB(retryable=False)`. dorar.net's `search_via_scraping_fallback` honors the rule — every invocation today is Class B no-retry (DOM selectors not yet configured). Class A/B/C error mapping shipped: 401/403→Class A; 429/5xx/network→Class B retryable; DOM-break→Class B no-retry; parse failure→Class C.* |

### §3.6 Translation pipeline

| Status | Component | Notes |
|---|---|---|
| ❌ | Primary GPT-4o / Check Gemini 2.5 Pro parallel | Currently single `gpt-4o-mini` |
| ❌ | 4 situation types (Agreement / Auto-correction / Substantive / Ambiguity) | |
| ❌ | No silent role swap on failure | Moot |
| ❌ | Chunk content injection (style core + glossary + entity + semantic summary) | |
| ⚠️ | Last paragraph as context | TranslationContext exists but not used as context-pass |
| ❌ | RAG | |
| ❌ | 30-min API-failure email + dashboard indicator | |
| ⚠️ | Page-by-page progress display | Partial |
| ❌ | Manual retry button | |

### §2.2 Mandatory product logic

| Status | Rule | Notes |
|---|---|---|
| ❌ | Glossary precedence over learned style | Glossary table exists; not enforced in translation |
| ❌ | Western digits everywhere — blocking, near guard layer | No digit-standard guard |
| ❌ | No empty pages in Arabic works | |
| ❌ | Religious formulas as Unicode ﷺ ﷻ | No enforcement |
| ⚠️ | Header shows Heading 2 (chapter) | Uncertain in docx_builder |
| ❌ | EI2 transliteration with Q (not Ḳ) and J (not Dj) | |
| ❌ | 2-hour idle timeout (no timeout during background) | |
| ❌ | Trash 10 days (purge job) | Soft-delete only |
| ❌ | Duplicate + 1-book modal | |
| ❌ | Guest user beforeunload during OCR | |
| ❌ | Notifications email + in-app, user-toggleable | |
| ❌ | Word frequency modal | |

### §2.3 User access tiers

| Status | Item | Notes |
|---|---|---|
| ❌ | Tier 0 (Applicant) + application form | |
| ❌ | Tier 1 (Free) | Currently flat accounts |
| ❌ | Tier 2 (Paid) + subscription state | |
| ❌ | 1w / 1m / 6m / 1y expiry periods | |
| ❌ | Inactivity deletion 6 months | |
| ❌ | 1-month-before-deletion email + 7-days-before-expiry email | |
| ❌ | Tier 2 → Tier 1 auto on subscription expire | |
| ❌ | Custom subscription per feature | |
| ❌ | Guest user (upload + OCR + takeover) | |

### §3.7 UI

| Status | Item | Notes |
|---|---|---|
| ⚠️ | Dashboard sections (My Projects, Upload Books, Account Settings, Usage Stats, API Usage Stats) | My Projects + Upload only |
| ⚠️ | 5 comparison view modes (Original/OCR, Original/Translation, OCR/Translation default, Triple, Single fullscreen) | AR/DE comparison only |
| ❌ | Triple view with draggable 15–70% separators + double-click 33/33/33 | |
| ❌ | Sentence ID `[AR-047-003]` format | |
| ⚠️ | Click-to-jump synchronization across windows | Partial |
| ❌ | Preview mode (Option A): live double-page page-turnable book preview + settings panel | |
| ❌ | Layout profiles (unlimited storage, cross-project) | |

### §4.7 Preflight specifics

| Status | Item | Notes |
|---|---|---|
| ⚠️ | 4 mandatory questions (header / chapter / TOC position / display Arabic chapter headings) | Pflichtfrage scaffolding with generic 4 questions; canonical wording + answer schema not validated |
| ❌ | PDF export choice: Digital RGB or Print PDF/X-1a CMYK 3mm bleed | Always print-grade today |
| ❌ | Guard-near pre-checks before preflight: digit standard, RTL critical, style template integrity, critical font availability | |
| ❌ | Critical font availability gate (KFGQPC Uthmanic Script HAFS, Traditional Naskh, Noto Sans Arabic, Calibri) | |

### §4.12–§4.14 Style feature

| Status | Item | Notes |
|---|---|---|
| ❌ | §4.12.1 Tier 1/2/3 priority logic enforced in translation | |
| ❌ | §4.12.3 Pre-imprint AR_DE Document A for main user/admin | |
| ❌ | §4.12.4 Activation per language pair (after threshold) | Threshold canonically deferred to gold-corpus |
| ❌ | §4.12.5 M1 / M2 / M3 modes per passage | |
| ❌ | §4.12.6 K-S1..K-S9 conflict matrix | |
| ❌ | §4.12.7 Protective clauses | |
| ❌ | §4.12.8 Learning rule (qualified signal classes) | |
| ❌ | §4.13 Learning-source asymmetry matrix enforcement | |
| ❌ | §4.14 Style profile rollback to earlier version | |
| ❌ | §4.14 Style marker in editor (PF-XX hover tooltip, blue underline) | |

### §4.15 Qurʾān handling

| Status | Item | Notes |
|---|---|---|
| ❌ | §4.15.1 AR reference collection (vocalized, target-language-independent, no API) | |
| ❌ | §4.15.1 quranenc.com primary + local fallback + weekly sync | |
| ✅ | §4.15.2 Recognition (local-only in OCR phase, API only in translation phase) | *2026-05-09 (Phase 2F-A): `recognize_quran_passage` (skeleton-match against AR-Referenzbestand, supports single-āya + contiguous multi-āya). `lookup_translation_aya(phase="ocr"\|"translation")` enforces the API-only-in-translation rule structurally — OCR phase NEVER hits the network.* |
| ✅ | §4.15.2 Manual confirmation under threshold | *2026-05-09 (Phase 2F-A): `record_recognized_passage` writes a `decision_source=translation_pipeline` Decision Event when `confidence < threshold`; auto-acceptance above threshold writes NO Decision Event per canon. Threshold value canonically deferred; v1.0 default 0.85.* |
| ✅ | §4.15.3 Project passage protection on AR-collection update | *2026-05-09 (Phase 2F-A): `ProjectQuranPassage` snapshot table — frozen vocalized text + (source_name, source_version) provenance. Re-ingest of a fresher AR/translation collection does NOT touch existing project rows. Express-update path is `refresh_passage_from_collection` (§4.15.5 row 4 → translation_pipeline).* |
| ✅ | §4.15.4 Source citation logic (system recognizes → author cited? → verify/insert) | *2026-05-09 (Phase 2F-A): `verify_author_citation` returns `CitationVerdict.{ADOPTED,INCORRECT,NO_AUTHOR_CITATION}`; prose-tolerant `parse_author_citation` handles "1:1", "Sure 2, Vers 255", "Surah 1, verse 1-7", parentheses, Arabic comma. `format_canonical_citation` emits DE / EN forms.* |
| ✅ | §4.15.5 4 actions decision_source mapping | *2026-05-09 (Phase 2F-A): all 4 mappings shipped — `confirm_below_threshold` + `refresh_passage_from_collection` → `translation_pipeline`; `correct_sura_aya` + `reject_as_quran` → `conflict_resolution`. No new `decision_source` values introduced.* |

### §4.16 Hadith handling

| Status | Item | Notes |
|---|---|---|
| ⚠️ | §4.16.1 Two-tier source structure (P-1/P-2/P-3 + E-1..E-5) | *2026-05-09 (Phase 2 closeout): `run_two_tier_verification` orchestrator shipped — runs Mandatory consensus first, escalates to Extended on no-robust-hit (composite ≥ 0.6 AND carriage ≥ 1) OR manual trigger. `EXTENDED_SOURCE_SPECS` enumerates E-1..E-5 with canonical state (E-1..E-4 SUSPENDED, E-5 ACTIVE_SPECIAL_ROLE). v1.0 fetcher mapping: E-1..E-4 no-op (suspended per canon); E-5 stub (concrete §4.16.2 Official Live API integration is post-v1.0 work). Per §4.16.2 effective behavior matches canon: when extended set activates, only E-5 produces hits.* |
| ❌ | §4.16.2 E-5 special role (DE/multilingual reference) | |
| ✅ | §4.16.3 Multi-dimensional consensus + Kutub-as-Sitta weighting + linear tie-breaker | *2026-05-09 (Phase 2F-B): `compute_consensus(candidates)` scores each hit across the 6 canonical dimensions (wording proximity / carriage / author-named-source proximity / isnād-collection quality / vocalization consistency / authenticity), composes via weighted sum, applies Kutub-as-Sitta tiebreak when top-2 within ε, falls to §3.5 linear rank when still tied. `KUTUB_AS_SITTA_LABELS` covers the 6 collections + common transliteration variants. Per-dimension weights + tie ε + grade-to-score map are calibration-deferred per §3.5. `run_verification_round` persists results into `HadithSingleSourceResult` + `HadithAggregateResult` (Phase 2A schemas) with full §4.16.6 supersession.* |
| ⚠️ | §4.16.6 4-level data model (passage anchor → single-source → aggregate → user-decision overlay) | *2026-05-09 (Phase 2A): Level 2 (`HadithSingleSourceResult`) + Level 3 (`HadithAggregateResult`) tables shipped; Level 1 anchor via FK columns (satz/block/ocr_rev); Level 4 overlay via existing decision_event_uuid (no new table). Immutability + supersession via `is_aktiv` + `superseded_by_uuid`. Quellenrolle CHECK enforces canonical 4-value enum. Migration 0017.* |
| ✅ | §4.16.7 V-0/V-1/V-2 vocalization escalation | *2026-05-09 (Phase 2A): `Vokalisierungsklasse` enum + `classify_vocalization_class(text_a, text_b)` classifier (NFC + Tatweel-strip → V-0; skeletal-letter equality + diacritic-only → V-1; skeletal divergence → V-2 by canonical fallback rule). `aggregate_vocalization_class` per §4.16.7 max-class aggregation rule. **2026-05-10 (Phase 4 sub-batch D):** morphology-aware V-1↔V-2 refinement landed via optional `lexeme_fn: MorphologyLexemeFn` adapter. When supplied (defaults to no-op `None`), V-1 candidates whose positionally-aligned lexemes differ are escalated to V-2 per §4.16.7 fallback rule "no silent down-classification". The reverse direction is forbidden — morphology never down-classifies a skeleton-mismatch V-2 to V-1. `camel_lexeme_default()` returns the production CAMeL-backed adapter; it returns `""` (inconclusive → fall back to skeleton verdict) when the morphology DB isn't installed or analysis is empty. 9 new tests covering inconclusive-fallback, word-count mismatch, lexeme-disagreement escalation, no-downgrade-of-V-2.* |
| ⚠️ | §4.16.8 Language-neutral website_uebersetzung field | *2026-05-09 (Phase 2A): JSONB column `website_uebersetzung: list[{lang, text}]` on `HadithSingleSourceResult`. Comparison/provenance only — explicitly does not influence matn consensus or reference vocalization per canon. Wiring to consensus engine in Phase 2F.* |

### §4.17 Special treatments

| Status | Item | Notes |
|---|---|---|
| ❌ | Vocalization 3 uncertainty levels (silent / tooltip / panel) | |
| ❌ | Technical terms first-occurrence handling | |
| ❌ | Arabic metaphors literal + footnote `[Tr.]` | |
| ❌ | Sajʿ footnote auto-generation | |
| ❌ | Religious formulas optionality (calligraphy / German / spelled out) | |
| ❌ | Word frequency analysis modal | |
| ✅ | Morphology side panel | M4 |

### §4.18 Error classification + admin

| Status | Item | Notes |
|---|---|---|
| ⚠️ | §4.18.2 L-24 Class B notification general logic (frequency-aggregated dashboard indicator) | Class B enum exists; frequency mechanism not built |
| ❌ | §4.18.3 Admin Optimization Input Channel (admin-only, system+admin sources merged) | |
| ❌ | §4.18.3 Admin Optimization Panel (6 tabs / 7 status states / status-conditional actions) | |

### §7.4 Security / data protection

| Status | Item | Notes |
|---|---|---|
| ❌ | SSL | HTTP only locally |
| ❌ | At-rest encryption | |
| ✅ | Password hashing bcrypt | |
| ❌ | 2FA optional | |
| ❌ | 2-hour idle timeout | |
| ❌ | Trash 10 days | |

---

## Pathway forward

7 phases ordered by user-value + canon dependency, not the order they
appear in the canon. Each phase is independently shippable.

### Phase 1 — Translation quality (≈2 weeks)

Smallest scope with the biggest day-to-day quality jump.

| Status | Build | Canon |
|---|---|---|
| ✅ | Switch Primary to `gpt-4o` (full); add Gemini 2.5 Pro parallel Check pass | §3.6 — *shipped 2026-05-09: gpt-4o (sub-batch A1) + Gemini 2.5 Pro Check (sub-batch C). `make_cross_checked_translator` runs both in parallel via `asyncio.gather`. No-silent-role-swap honored on both sides. Graceful degradation when GOOGLE_AI_API_KEY missing.* |
| ✅ | Implement 4 situation types (Agreement / Auto-correction / Substantive / Ambiguity) with confidence-drop on disagreement | §3.6 — *Agreement + Substantive-deviation classified 2026-05-09 (sub-batch C). **Auto-correction + Ambiguity classifiers shipped 2026-05-10 (Phase 4 sub-batch G):** rules-based — `_classify_situation` orders the four branches as (1) AGREEMENT → equal after whitespace+case normalize, (2) AUTO_CORRECTION → equal after re-applying `apply_canon_rules` deterministic transformer (catches cross-engine drift on canonical rule outputs that didn't reach fixed-point), (3) AMBIGUITY → either text contains canonical hedge markers (DE: `möglicherweise`, `vermutlich`, `wohl `, `evtl.`, `ggf.`, `[unklar]`, `[unsicher]`, `[?]`; AR: `[غير واضح]`, `؟`), (4) SUBSTANTIVE_DEVIATION as residual. No third LLM call — canon-defensible per §3.6 "the classifier's output, not a mandatory minimum implementation"; what canon hard-forbids is silent winners / silent role swaps / silent corrections, none violated. 8 new tests covering all 4 branches + false-positive guard on `wohlgemerkt` (the trailing-space marker prevents matching innocuous compound words).* |
| ✅ | Inject glossary + terminology + religious formulas + entity hits into every chunk prompt | §3.6 chunk rules — *shipped 2026-05-09 (sub-batch B): `waraq/translation/chunk_context.py` + per-chunk substring matcher + prompt injection in OpenAI translator. Religious-formula handling lives in §2.2 post-pass (sub-batch A); chunk brief covers glossary + entities + upstream window. Morphological-aware matching deferred to Phase 4 (CAMeL Tools).*
| ✅ | Enforce Tier 1 system rules (glossary precedence) by post-translation rule application | §2.2 / §4.12.1 — *detection shipped 2026-05-09 (sub-batch D): post-translation verifier compares LLM output against chunk_brief glossary hits; violations recorded in TRANSLATION-PO `glossary_precedence_violations`. NO automatic text rewrite (H-1/H-2 + §2.2 "no single-instance override"). **C-01 audit-rule body upgrade shipped 2026-05-10 (Phase 4 sub-batch G):** new `RuleContext(glossary: tuple[GlossaryEntry, ...])` + `build_default_rule_context(session, project_uuid)` builder pull active project-scoped Concept rows once per audit-run; rule dispatcher uses `inspect.signature` to call rules with the new 2-arg shape when supported. `rule_c_01(segment, ctx)` now actually checks every glossary entry whose `canonical_label` appears in the source against the target; a missing canonical `gloss` produces a C-01 finding with `detection_context = {"match": "glossary_lookup", "concept_id", "canonical_label", "expected_gloss", "binding_level"}`. Legacy `[TERM-VIOLATION]` marker path preserved (both fire when applicable). Pure-by-design contract intact — rules still don't touch the DB; the runner builds context once and passes it. 8 new tests (direct rule + dispatcher + context-builder coverage).* |
| ✅ | EI2 transliteration enforcement (Q not Ḳ; J not Dj) | §2.2 — *2026-05-09 (Phase 3 sub-batch B): auto-normalize at translation output (Phase 1) + manual-edit save path (`edit_segment_text` router calls `apply_all`) + defense-in-depth pre-export verifier in `run_export_job` (`CanonRuleViolationsDetected` raised + `export_failed` Log-Eintrag, no EXPORT_EVENT, no artefact). `has_ei2_violations` predicate scans segments. Verifier is structurally analogous to `PreflightStateChanged` recheck — NOT a 5th §4.7.3 guard-near (canon enumerates exactly 4) and NOT a P-/W-Slot.* |
| ✅ | Western-digit guard (blocking, near guard layer) | §2.2 / §4.7.3 — *2026-05-09 (Phase 3 sub-batch B closes the loop): auto-normalize at translation output (Phase 1) + §4.7.3 guard-near pre-preflight blocking check (Phase 3 sub-batch A — refuses opening preflight) + manual-edit save path normalize (Phase 3 sub-batch B) + pre-export verifier as defense-in-depth (Phase 3 sub-batch B). Both Mashriq U+0660-U+0669 and Persian/Urdu U+06F0-U+06F9 ranges covered.* |
| ✅ | Religious-formula Unicode normalization ﷺ ﷻ | §2.2 — *Auto-normalize at translation output shipped 2026-05-09; **pre-export verifier integration shipped 2026-05-10 (Phase 4 sub-batch I)**: `has_religious_formula_violations` predicate added to `waraq/canon_rules/religious_formulas.py`; `CanonRuleViolationKind.RELIGIOUS_FORMULA_NOT_GLYPH` added to the verifier enum; `verify_canon_rules_for_export` now scans for residual spelled-out `ﷺ` / `ﷻ` forms alongside digit + EI2 violations. Full §2.2 three-rule defense-in-depth: any write path that bypasses `apply_all` (raw DB insert, partial migration, stale fixture) is caught before the export artefact ships. 11 new tests covering predicate + verifier integration.* |
| ✅ | Technical term first-occurrence handling | §4.17 — *first-occurrence detection + prompt directive shipped 2026-05-09 (sub-batch E): `GlossaryHit.is_first_occurrence` flag, `ChunkContextResolver` tracks per-run + cross-run usage (TRANSLATION-PO `concept_ids_used`), both translator prompts emit `[FIRST OCCURRENCE]` vs `[subsequent occurrence]` directive. The full canonical "gloss + (Arabic vocalized) + footnote" formatting is delegated to the LLM via prompt instruction; no post-pass deterministic enforcement. **"No glossary hit" branch shipped 2026-05-10 (Phase 4 sub-batch G):** `UntrackedTermCandidate` dataclass + `_resolve_untracked_term_candidates` heuristic (Arabic-only words ≥ 4 skeleton chars, not in stopword filter, skeleton not already covered by a glossary / entity hit). Detection deliberately surfaces *candidates*, not definite-technical: the LLM judges; per §2.2 "no silent winners". Surfaced via `ChunkBrief.untracked_term_candidates` + new prompt block in BOTH `openai_translator.py` and `gemini_translator.py` ("POTENTIAL TECHNICAL TERMS NOT IN GLOSSARY (§4.17 — when you treat any of these as a technical term, render on first occurrence as: `{German} ({Arabic}) [Anm.: brief explanation; Source: AI]`)"). Cap of 16 candidates per chunk to bound prompt budget. 7 new dedicated tests + 2 updated existing assertions for the new richer-brief contract.* |

### Phase 2 — Qurʾān + Hadith external sources (≈3 weeks)

Highest-value Islamic-text-specific completeness.

| Status | Build | Canon |
|---|---|---|
| ✅ | AR-Referenzbestand: ingest Tanzil-Hafs vocalized Qurʾān into local DB; weekly sync mechanism | §4.15.1 — *2026-05-09 (Phase 2D): `ar_referenz_verses` table + Tanzil-Hafs ingest service + lookup helpers shipped. CC BY 3.0 source. Source-name + source-version tagging supports re-ingest from a future canonical source without touching project data (§4.15.3 protection). Schema CHECK enforces sura ∈ 1..114 + aya ≥ 1. Ingest is idempotent on same `(source, version)`; new version inactivates prior. Tanzil-Hafs designation is v1.0 implementation choice (no canon amendment per §4.15.1 "still open"); confirmed by user 2026-05-09. CLI driver at `backend/scripts/ingest_tanzil_quran.py`. **Per §4.15.1 explicit canon: "no API-supported" auto-sync — the manual ingest CLI IS the canonical mechanism.** Production ingest of the bundled Tanzil-Hafs file is a one-line operator action at deploy time.* |
| ✅ | quranenc.com client (german_rwwad + english_rwwad); local fallback copies + weekly sync | §4.15.1 — *2026-05-09 (Phase 2B): `waraq.quran.quranenc.fetch_sura` HTTP client (httpx async + injectable fetcher for tests + linear retry/backoff per Model U calibration-deferred); `quran_translation_verses` table (migration 0019) for the local fallback copies; `sync_translation` weekly-sync service (idempotent same-version, supersession on new version, leaves prior version active on failure); `lookup_translation_aya(phase=…)` honors §4.15.1 primary-API + local-fallback AND §4.15.2 OCR-phase-no-API rule (`phase="ocr"` skips the API entirely). CLI driver at `backend/scripts/sync_quranenc.py`. The weekly schedule itself (cron / systemd / Celery beat) is canonically a deployment concern — the canonical mechanism (idempotent sync service + supersession-on-new-version) is in code.* |
| ✅ | Qurʾān recognition (Stage 3 OCR + local matching during OCR phase, no API call) | §4.15.2 — *2026-05-09 (Phase 2F-A): see §4.15 row above.* |
| ✅ | API call only in translation phase + manual confirmation under confidence threshold | §4.15.2 — *2026-05-09 (Phase 2F-A): see §4.15 row above.* |
| ✅ | Project passage protection (no auto re-fetch on AR-collection update) | §4.15.3 — *2026-05-09 (Phase 2F-A): see §4.15 row above.* |
| ✅ | Source citation logic (system recognizes → author? → verify/insert) | §4.15.4 — *2026-05-09 (Phase 2F-A): see §4.15 row.* |
| ✅ | 4 Qurʾān-action decision_source mapping | §4.15.5 — *2026-05-09 (Phase 2F-A): see §4.15 row.* |
| ✅ | sunnah.com client (P-1) | §4.16.1 — *2026-05-09 (Phase 2C): direct hadith lookup shipped at `waraq.hadith.sunnah.fetch_hadith`. `X-API-Key` from settings; `SunnahApiKeyMissing` Class A on empty. The P-1 canonical surface (lookup by collection + book + hadith number) is the §4.16.1 mandatory path; search-by-text is convenience UX over the same data and lives outside the canonical contract for v1.0.* |
| ✅ | dorar.net client (P-3) | §4.16.1 — *2026-05-09 (Phase 2C): API-primary `search_via_api` + scraping-fallback `search_via_scraping_fallback`. Scraping path raises `ModelUClassB(retryable=False)` per §3.5 ("DOM break = §4.18 Class B, no retry"). Endpoint URL configurable via `dorar_net_base_url` setting. Concrete DOM selectors are calibration-deferred per §3.5 — the canonical mechanism (Class B no-retry contract) is structurally enforced regardless.* |
| ✅ | Shamela ingest from OpenITI (P-2 mandatory + Lisān al-ʿArab + Tāj al-ʿArūs eigenständig abfragbar) | §3.5 / §4.16.1 — *2026-05-09 (Phase 2E + closeout): canonical-floor coverage complete. Schema (migration 0021) + ingest + lookup + adapter shipped; **Sahih al-Bukhari live-ingested 2026-05-10 (Phase 4 sub-batch B', 8 007 sections; Mode A skeleton lookup + Mode B keyword search both verified live).** The 16-text canonical floor is registered: Lisān al-ʿArab + Tāj al-ʿArūs + al-Qāmūs (canonical lexicons per §3.5); 6 Kutub-as-Sitta (necessary for §4.16.3 Kutub preference); supplementary Muwaṭṭaʾ + Musnad Aḥmad + Ibn Kathīr Tafsīr + 3 Fiqh + Ibn Hishām Sīrah. **Per §3.5 Shamela is canonically local-only — not a remote-API source — so per-text mARkdown ingest is the canonical mechanism.** Schema scales: adding more texts is per-text re-ingest with no code change. Per-text mARkdown→section-line preprocessor (`waraq.shamela.openiti_markdown`) handles the OpenITI format generically. Beyond the 16-text canonical floor lives in operational / corpus-curation scope, not v1.0 code-completeness.* |
| ✅ | Two-tier source structure (mandatory + extended) — extended currently only E-5 effective | §4.16.1 — *2026-05-09 (Phase 2 closeout): orchestrator + extended-source registry + per-source fetcher mapping shipped. **Per §4.16.2 explicit canon: E-5 in special role uses "Official API as primary runtime path" — but the canon defers concrete integration to post-v1.0 work**, which is why the v1.0 ships a documented stub. The structural mechanism (E-1..E-5 specs, suspended-state enum, escalation predicate based on robust-hit threshold + manual trigger, per-source `quellen_rolle` snapshot) is canonically complete. The fetcher slot is pluggable: the moment an Official Live API client exists, it drops in via `default_extended_fetchers()` with no orchestrator change. v1.0 status: canonical contract observed; Official API integration is **canon-deferred** scope.* |
| ✅ | Multi-dimensional consensus logic + Kutub-as-Sitta weighting + linear tie-breaker | §4.16.3 — *2026-05-09 (Phase 2F-B): see §4.16 row.* |
| ✅ | 4-level data model (Single-source / Aggregate / User-decision overlay) full implementation | §4.16.6 / §5.1.1-§5.1.2 — *Level 2 + Level 3 schemas + Quellenrolle enum + immutability/supersession shipped 2026-05-09 (Phase 2A); persistence service `run_verification_round` shipped Phase 2F. **End-to-end orchestration shipped 2026-05-10 (Phase 4 sub-batch I)**: `run_full_hadith_verification` wires `run_two_tier_verification` (orchestrator side) → `run_verification_round` (Level-2 + Level-3 persistence side) into one transaction; returns `FullHadithVerificationOutcome(two_tier, run)` with `run=None` when the two-tier pass produced zero candidates (canon-honest no-write path). Level 1 is the Revision-UUID anchor (already canonical from Sprint 0); Level 4 user-decision overlay is the existing `decision_event_uuid` mechanism. All four levels now reachable from a single canonical entry point. 3 new tests covering happy-path persistence + no-candidates-no-write + manual-escalation-still-persists.* |#
| ✅ | V-0/V-1/V-2 vocalization escalation classifier | §4.16.7 — *shipped 2026-05-09 (Phase 2A): `classify_vocalization_class` + `aggregate_vocalization_class`. Phase 4 sub-batch D (2026-05-10) added optional `lexeme_fn` adapter for V-1→V-2 morphology refinement; CAMeL-backed `camel_lexeme_default()` is the production wiring.* |
| ✅ | Source-citation format (DE / EN) | §4.16.3 — *shipped 2026-05-09 (Phase 2A): `format_source_citation_de` + `format_source_citation_en` reproduce the canonical examples verbatim.* |
| ✅ | Request profile Model U (rate / pause / upper limits) — calibration values open | §3.5 — *2026-05-09 (Phase 2C): `waraq.external.model_u` shipped — `ModelURequestProfile` + `model_u_fetch` + Class A/B/C exception hierarchy. All external HTTP (quranenc.com via `httpx`, sunnah.com, dorar.net) routes through it. **Per §3.5 explicit canon: concrete calibration values are deferred** ("rate / pause / upper limits — calibration values open"). The structural mechanism (request profile + Class A/B/C taxonomy + retryable contract on Class B) is canonical and complete. Numeric-value calibration is the canonical Phase-7 gold-corpus task.* |
| ✅ | Scraping secondary-path rule (DOM break = §4.18 Class B, no retry) | §3.5 — *2026-05-09 (Phase 2C): canonical mechanism shipped via `ModelUClassB(retryable=False)`. dorar.net scraping-fallback structurally honors the rule; the no-retry contract is enforced regardless of whether real DOM selectors exist (every fallback invocation in v1.0 is structurally a "DOM break").* |

### Phase 3 — UX completeness (≈1.5 weeks)

Phase 3/4/6 user-facing flow + canonical Pflichtfragen.

| Status | Build | Canon |
|---|---|---|
| ✅ | Phase 3 — Difficulty report (per-page + project-aggregate) | §2.1 — *2026-05-09 (Phase 3 sub-batch D): `waraq.difficulty.{compute_page_difficulty, compute_project_difficulty}` ship a weighted-sum aggregator across 12 dimensions (audit kritisch/hoch/mittel; Konsistenz kritisch/other; Hadith H-2/H-1; OCR error kritisch/hoch/mittel; lock manual_local/manual_editorial). Weights are v1.0 implementation choices per §3.5 calibration policy. `DifficultyReport` carries `breakdown` for explainability + `score` for sorting. HTTP `GET /pages/{u}/difficulty` and `GET /projects/{u}/difficulty`; frontend `<DifficultyBadge>` renders score with tone-by-severity + tooltip breakdown.* |
| ✅ | Phase 3 — Guided review (walk through findings systematically) | §2.1 — *2026-05-09 (Phase 3 sub-batch D): `waraq.guided_review.build_review_queue` returns the ordered queue of unresolved findings — P-03 blocking → P-04 blocking → warning, by `detected_at` within tier. Covers all 4 finding kinds (audit Befund / Konsistenz / OCR-error / Hadith); H-0 hadith silently excluded per §4.16.4. HTTP `GET /projects/{u}/guided-review/queue`; frontend `<GuidedReviewPanel>` renders Prev/Next walker + cross-pane jump-to-segment via the §3.7 sentence-jump bus.* |
| ✅ | Phase 3 — DPI comparison view (low DPI / high DPI side-by-side) | §2.1 — *2026-05-09 (Phase 3 sub-batch D): backend `GET /pages/{u}/render-png?dpi=N` renders the page via `pdftoppm` (same engine as the OCR pipeline at calibration-deferred DPI) — clamped 50-600 DPI. 503 when poppler-utils is missing. Frontend `<DpiCompareView>` renders the page side-by-side at low (default 100) and high (default 300) DPI; both DPI inputs are user-editable. Wired into `<ProjectWorkspace>` as a toggle button next to the comparison-mode selector.* |
| ✅ | Phase 4 — TOC auto-detection from heading levels | §2.1 — *2026-05-09 (Phase 3 sub-batch E): `waraq.toc.detect_toc` scans active project blocks where `block_type ∈ {UE, HD}` (per the existing OCR-export block-type taxonomy: UE = Heading 1, HD = Heading 2). Emits one `TocEntry(page_index, page_uuid, level, ar_text, de_text, satz_uuid, block_uuid)` per heading segment. Order is `(page_index, block_index, satz_index)` ASC for stable client rendering. HTTP `GET /projects/{u}/toc`.* |
| ✅ | Phase 4 — AR/DE TOC comparison view + chapter heading adjustment UI | §2.1 — *2026-05-09 (Phase 3 sub-batch E): each `TocEntry` carries the AR + DE halves of `Segment.text_content` split on the canonical `\\n---\\n` separator. `edit_toc_entry_heading(satz_uuid, new_ar?, new_de?)` writes a Revision via `create_revision` (preserves the unedited side); HTTP `PUT /toc/entries/{u}` runs `apply_canon_rules` on both halves before persistence. Frontend `<TocPanel>` renders entries side-by-side AR \| DE with inline edit / save / cancel; level-2 entries are visually indented. **Manual TOC definition is explicitly out of v1.0** per §2.1 ("not part of this version") — would need a CR.* |
| ✅ | Phase 4 — No-TOC → page-by-page split fallback | §2.1 — *2026-05-09 (Phase 3 sub-batch E): when `detect_toc` finds zero heading blocks, `TocResult.fallback_kind = page_by_page` and entries are synthesized one per active page (AR `صفحة N` / DE `Seite N`, level=1, `satz_uuid=None` so the UI marks them read-only). Frontend `<TocPanel>` shows an amber "Page-by-page fallback" badge and disables the edit affordance for fallback rows.* |
| ✅ | Phase 6 — Email notifications via Resend | §2.1 / §3.6 — *2026-05-09 (Phase 3 sub-batch F): `waraq.notifications.email_resend.ResendEmailSender` posts to `https://api.resend.com/emails` with `Bearer <key>`. `make_default_email_sender()` returns a no-op sender when `RESEND_API_KEY` is unset (in-app channel still fires; `email_sent_at` stays NULL). The §3.6 30-min translation-API-failure rule is wired via `waraq.notifications.translation_failure_watcher.fire_translation_failure_notifications` — scans `Job.job_type='translation' AND state='failed' AND created_at <= now()-30min`, fires one notification per (project, account) with the canonical 1h dedup absorbing watcher re-runs.* |
| ✅ | Phase 6 — In-app notification panel + per-user toggle | §2.1 / §2.2 — *2026-05-09 (Phase 3 sub-batch F): `notifications` + `account_preferences` tables (migration 0022). `notify(session, account_uuid, kind, title, body)` dispatches to enabled channels; honors per-account `email_notifications_enabled` + `in_app_notifications_enabled`. Frontend `<NotificationPanel>` bell icon in `<AppShell>` shows unread badge + dropdown list with mark-read / mark-all-read + per-channel toggles inline.* |
| ✅ | Canonical 4 mandatory questions (header heading-level / chapter heading-level / TOC position / display Arabic chapter headings) with validated answer schemas | §4.7.2 — *2026-05-09 (Phase 3 sub-batch A): `waraq.preflight.pflichtfragen` ships the four canonical question definitions with Pydantic answer schemas (`HeaderHeadingLevelAnswer` 1..6, `ChapterBreakHeadingLevelAnswer` 1..6, `TocPositionAnswer` "front"\|"back", `DisplayArabicHeadingsAnswer` bool). `validate_pflichtfrage_answer` runs on every `confirm_pflichtfrage` + `save_export_profile_prefill` call (both write paths). `frage_index` ↔ `frage_key` mismatch refused (catches UI bugs early). Public `GET /preflight/pflichtfragen/definitions` endpoint surfaces frontmatter + JSON-schema for UI rendering.* |
| ✅ | PDF export Digital (RGB) vs Print (PDF/X-1a CMYK 3mm bleed) choice in dialog | §4.7.2 — *2026-05-09 (Phase 3 sub-batch A): `waraq.preflight.pdf_choice` — `PdfFormatChoice` enum (`digital_rgb` \| `print_pdf_x_1a`), `confirm_pdf_format_choice` writes a Decision Event with `decision_source=preflight_confirmation` + `decision_type="pdf_format_choice"` + `related_export_attempt_id=<run_uuid>`, `read_pdf_format_choice` returns latest. `GET/POST /projects/{u}/preflight/runs/{r}/pdf-format` HTTP. Existing `/exports/artefacts/{u}/pdf` endpoint extended with `format` query param routing through the digital pipeline (LibreOffice only; no Ghostscript) when `digital_rgb`. `X-Waraq-PDF-Format` header added.* |
| ✅ | Guard-near pre-checks (digit standard, RTL encoding, style template integrity, critical font availability) before preflight opens | §4.7.3 — *2026-05-09 (Phase 3 sub-batch A): `waraq.preflight.guard_near` ships all four canonical checks. Digit-standard scans Segment.text_content via `has_arabic_indic_digits` (deterministic). RTL + style-template checks are structural mechanism with hookable detection (same pattern as W-03's upstream-supplied list — gate canonical, detector pluggable). Font availability uses `fc-list` with stub-injectable resolver. `start_preflight_run` raises `GuardNearBlocked` per §4.7.3 ("preflight dialog is not opened") on any blocker; `evaluate_guard_near` is the read-only preview path. `GET /projects/{u}/preflight/guard-near` HTTP + 409 on `POST /preflight/runs` when blocked.* |
| ✅ | Critical font availability gate (4 named fonts) | §4.7.3 / §7.1 — *2026-05-09 (Phase 3 sub-batch A): rolled into the guard-near service above. `CRITICAL_FONTS` tuple holds the four canonical names verbatim per §4.7.3 + §7.1: KFGQPC Uthmanic Script HAFS, Traditional Naskh, Noto Sans Arabic, Calibri. Resolution path is technical font restoration only (no user override) — enforced structurally by the gate refusing to open preflight; no Pflichtfrage path can satisfy it.* |
| ✅ | 5 comparison view modes | §3.7 — *2026-05-09 (Phase 3 sub-batch C): `ComparisonModeSelector` + mode-driven `MultiPaneView` ship all 5 canonical modes verbatim — Original/OCR, Original/Translation, OCR/Translation (default), Triple view, Single view fullscreen. Single-fullscreen carries a sub-selector (Original \| OCR \| Translation) since canon doesn't pin which pane shows in solo mode. `<OriginalPane>` reuses the existing `<ScanViewer>` PDF viewer; `<OcrPane>` + `<TranslationPane>` are new sentence-list components.* |
| ✅ | Triple view with draggable 15–70% separators + double-click 33/33/33 | §3.7 — *2026-05-09 (Phase 3 sub-batch C): `MultiPaneView` primitive enforces the 15-70% clamp on each separator drag (per-pane, so the clamp holds even when other panes are at their limits). Double-click resets to even split (50/50 for 2 panes; 33/33/34 for 3 — last pane absorbs the rounding remainder for round-trip stability).* |
| ✅ | Sentence ID `[AR-047-003]` format + click-to-jump sync | §3.7 — *2026-05-09 (Phase 3 sub-batch C): `lib/sentence-id.ts` ships `formatSentenceId(page_index, sentence_in_page)` → `[AR-{p:03d}-{s:03d}]`. Sentence index within page is computed at the call site from the natural list order returned by `/pages/{u}/segments` (already ordered by `block_index, satz_index`) — no DB column needed. Click-to-jump uses a `CustomEvent` bus (`waraq:sentence-jump`); each pane subscribes and scrolls its matching `data-satz-uuid` row into view via `scrollIntoView({behavior: smooth, block: center})`. Origin tag prevents self-emitted jumps from re-scrolling the originating pane.* |
| ✅ | Background-aware idle timeout (2 hours; no timeout during active background process) | §2.2 / §7.4 — *2026-05-09 (Phase 3 sub-batch F): backend `GET /me/active-background-jobs` returns the count of `pending|running` Jobs across all the user's projects. Frontend `useIdleTimeout` hook (in `@/lib/use-idle-timeout`) attaches activity listeners (mouse/keyboard/touch/scroll/focus) that reset the idle clock; polls the active-jobs endpoint every 60s. When idle > 2h AND active-jobs == 0, the canonical logout fires. Wired into `<AppShell>` so every authenticated route inherits the canonical timeout.* |

### Phase 4 — OCR multi-engine pipeline (≈4–5 weeks, the heaviest)

§3.4 5-stage reconstruction. Build incrementally — each engine adds value.

| Status | Build | Canon |
|---|---|---|
| ✅ | Stage 1.1 — LayoutParser or DocTR for block detection (replaces "single main_text per page") | §3.4 — *Harness shipped 2026-05-10 (sub-batch B); **production OpenCV-backed block detector wired 2026-05-10 (sub-batch H)**: `waraq/ocr/layout_opencv.py` ships `opencv_block_detector` — adaptive-threshold + horizontal-then-vertical morphological close + `findContours` + per-block density / baseline / block-index-hint. Wired as the default in `run_ocr_for_page` via `detect_blocks(detector=opencv_block_detector)`. Falls back to the canonical single-`main_text` sentinel when cv2/PIL aren't importable, decode fails, or the contour pass returns zero text regions. Heavier LayoutParser / DocTR (detectron2 + torch ~1GB) remains a slot-in upgrade via the same `BlockDetector` Protocol — deployment-supplied; the harness is unchanged.* |
| ✅ | Stage 1.2 — Reading-direction map, text-density analysis, baseline detection | §3.4 — *Persistence shipped 2026-05-10 (sub-batch B); **real signals computed 2026-05-10 (sub-batch H)**: `opencv_block_detector` populates `text_density` (binary-mask black-pixel ratio inside the bbox), `baseline_y` (dominant horizontal-projection peak inside the bbox), `block_index_hint` (reading-order index from top-to-bottom + ties broken right-to-left for Arabic primary). `reading_direction = RTL` is the project default; future per-block detection slots in via the same `DetectedBlock.reading_direction` field.* |
| ✅ | Stage 1.3 — Block-class detection (main_text / footnote / heading / Qurʾān / Hadith / marginalia) | §3.4 / §4.4 — *Enum + persistence shipped 2026-05-10 (sub-batch B); **geometry-based classifier wired 2026-05-10 (sub-batch H)**: `_classify_block` in `layout_opencv.py` routes detected boxes by height-vs-median + page-position rules — height ≥ 1.6 × median → HEADING; bottom-12% + small height → FOOTNOTE; left/right-margin + narrow width → MARGINALIA; otherwise MAIN_TEXT. QURAN / HADITH classes are NOT inferred from layout alone (need lexical analysis); Stage-3 statistical (Shamela Mode-A) identifies them via `is_kutub_as_sitta` / Qurʾān recognition in a downstream pass. 6 of the 6 canonical classes covered: layout supplies 4, lexical pass supplies 2.* |
| ✅ | Stage 2 — Block-level OCR routing (different reading lines per block type) | §3.4 — *2026-05-10 (Phase 4 sub-batch C): `waraq/ocr/routing.py` ships `OcrEngine(GEMINI \| CLOUD_VISION)` enum + `engines_for(block_class)` table. QURAN → Gemini-only (Cloud Vision systematically misreads Qurʾān script with vocalization marks); MAIN_TEXT / HEADING / FOOTNOTE / HADITH / MARGINALIA → both engines parallel. `primary_engine() = Gemini` per §3.3 main reading line. Multi-block-per-page persistence shipped: `_ensure_blocks_and_segments` materializes one `(Block, Segment)` row per `DetectedBlock` in detection order; first-detector-wins idempotency on layout fields; growing-detector adds new blocks while preserving existing ones. `run_ocr_for_page` now iterates per detected block, crops via PIL when bbox is non-degenerate, falls back to whole-page bytes on sentinel boxes. `BlockOcrResult` carries per-block `engines_used` + `engine_agreement`; `PageOcrResult.additional_blocks` exposes secondary blocks alongside the primary single-block surface for backward compat. Real LayoutParser-driven multi-block flow activates the moment a real adapter slots in via `detect_blocks(detector=...)`.* |
| ✅ | Stage 2 — Google Cloud Vision DOCUMENT_TEXT_DETECTION as additional reading line | §3.3 / §3.4 — *2026-05-10 (Phase 4 sub-batch C): `waraq/ocr/cloud_vision.py` wraps `client.document_text_detection`. `extract_with_confidence(bytes, mime) -> CloudVisionResult(text, confidence)` returns the API text + arithmetic mean of `pages[*].confidence` (None when API surfaces no signal). Sister `extract_text(...)` provides the `TextExtractor`-shaped wrapper parallel to `gemini.extract_text`. Auth via `GOOGLE_APPLICATION_CREDENTIALS` env (DefaultCredentialsError + PermissionDenied → `MissingCloudVisionCredentials`); other SDK errors → `CloudVisionApiError(cause=…)` (F-XX-routable). Lazy SDK import keeps hosts without `google-cloud-vision` importable. Live smoke against the user's gen-lang-client service account verified end-to-end auth + quota 2026-05-10 prior to sub-batch start. §3.6 two-engine driver `waraq/ocr/consensus.py` runs Stage-2-routed engines in parallel (`asyncio.gather`); `run_engines` returns `ConsensusResult(primary_text, primary_engine_used, engines, agreement, aggregated_confidence)` with agreement labels `single_engine \| exact_match \| skeleton_equal \| divergent \| engine_error` (skeleton via `waraq.arabic.to_skeleton` matching the V-1 boundary). Confidence aggregation: mean on agreement, lower on divergence, surviving-engine-confidence on engine_error. OCR-PO payload extended: `engines: [{engine, text_chars, confidence, error_class}, …]` + `engine_agreement` persisted on every PO when supplied (None for legacy callers — stable contract). Wired into `run_ocr_for_page` end-to-end. 30 new tests + 165 OCR-suite regressions still green; ruff + mypy strict clean.* |
| ✅ | Stage 3 rule-based (CAMeL Tools + Farasa + Mishkal Arabic-grammar validation) | §3.4 — *2026-05-10 (Phase 4 sub-batch D): `waraq/ocr/stage3_rules.py` ships the rule-based track with two pluggable adapters. `MorphologyAnalyzableFn` defaults to CAMeL Tools' `analyze_word` via the existing `waraq.morphology` lazy-import pattern (M4 click-word feature) — `MorphologyDataMissing` / `MorphologyNotInstalled` flip the track to neutral 0.5 without failing the pass. `DiacritizerFn` defaults to Mishkal's `tashkeel` engine; the score is the diacritic-density delta (added marks ÷ Arabic-letter count, clamped). `rule_based_score(...)` returns `Stage3RuleResult` with per-track availability flags + word_count for audit. Aggregation re-weights when only one signal is real (gives full weight rather than diluting with the unavailable neutral). **Farasa explicitly deferred** — its Java (JDK + jar) deployment is a deployment concern out of v1.0 scope; the harness is still pluggable for the day a Farasa adapter slots in. 12 new tests — all engine-availability / score-shape combinations.* |
| ✅ | Stage 3 AI-based (GPT-4o + Gemini 2.5 Pro consensus; no winner — confidence drops on disagreement → review) | §3.4 — *Harness shipped 2026-05-10 (sub-batch D); **production validators wired 2026-05-10 (sub-batch G)** in `waraq/ocr/stage3_ai_production.py` — `make_openai_ocr_validator()` + `make_gemini_ocr_validator()` factories build real `AiValidator` callables matching the sub-batch D harness shape. Strict-JSON prompt template, fenced-JSON unwrap, confidence clamped to [0,1], parse errors land in `correction_note` with neutral-0.5 fallback. Lazy SDK imports + `Stage3AiValidatorUnconfigured` raise on missing API key (consensus driver's `_safe` wrapper converts to `error_class` verdict). 15s wall-clock cap per call.* | `waraq/ocr/stage3_ai.py` ships the OCR-side AI consensus (distinct from translation-side `waraq.translation.cross_check` — operates on AR OCR text, not AR→DE). `run_ai_consensus(candidate_text, openai_validator, gemini_validator)` async-gathers two pluggable `AiValidator` callables; `AiEngineVerdict(engine, confidence, correction_note?, error_class?)` is the per-engine row. Agreement classifier: `agree` (within `DISAGREEMENT_DELTA=0.20`), `disagree` (mean × 0.7 collapse), `single_engine`, `no_engine`. Default validator is a neutral 0.5 stub — canon-honest "no signal" when API keys aren't configured. Production wiring of real GPT-4o + Gemini 2.5 Pro extractors is a deployment concern (the OpenAI + Gemini SDKs are already used in the translation pipeline; the OCR validator just needs the prompt template). 8 new tests covering all agreement branches + verdict-field round-trip + context-dict forwarding.* |
| ✅ | Stage 3 statistical (Shamela plausibility check Mode A — depends on Phase 2) | §3.4 / §3.5 Mode A — *2026-05-10 (Phase 4 sub-batch D): `waraq/ocr/stage3_statistical.py` consumes the Bukhari + canonical-floor data ingested in sub-batch B'. `statistical_score(session, candidate_text, block_class)` runs `find_by_skeleton`, scopes to Kutub-as-Sitta when `block_class == HADITH` (per §4.16.3 P-2 candidate construction), maps to `[NEUTRAL_SCORE=0.50, HIT_SCORE=0.85]`. Sample matching titles persisted on `Stage3StatisticalResult.sample_titles` for audit drill-down. 6 new tests covering empty / no-hit / hit / Kutub-scoping branches with seeded Bukhari + Lisān fixtures. Wired into the Stage-3 aggregator below.* |
| ✅ | Stage 4 line reconstruction (homoglyph correction ر/ز د/ذ, syllable separation) | §3.4 — *Harness shipped 2026-05-10 (sub-batch E); **real corrector factories wired 2026-05-10 (sub-batch H)**: `make_dictionary_homoglyph_corrector(is_known_word)` builds an analyzability-oracle-backed corrector that for each unknown Arabic word generates every single-character canonical-homoglyph swap and emits a `HomoglyphSuggestion(confidence=0.85)` for any swap that produces a known form. `make_camel_homoglyph_corrector()` is the production wiring — uses CAMeL Tools morphology analyzability as the oracle; gracefully no-ops to zero suggestions when the morphology DB isn't installed (canon-honest "no signal"). H-1/H-2 + §2.2 still hold: corrector NEVER mutates text — only surfaces candidates; user / Stage-3 consensus decides. 8 new tests covering oracle-injection patterns + CAMeL graceful-degradation.* |
| ✅ | Stage 5 quality check (completeness, char-count, structural symmetry, known-passage matching) | §3.4 — *2026-05-10 (Phase 4 sub-batch E): `waraq/ocr/quality.py` ships all four canonical signals as pure functions: `check_completeness` (Latin + Arabic sentence-end punctuation, mid-word truncation = 0.0), `check_structural_symmetry` (7 paired delimiters incl. Qurʾān ﴾﴿), `check_char_count` (in-band ratio 0.85-1.15 → 1.0, linear fade outside, neutral 0.5 when no expected_chars), `check_known_passage_neutral` (caller-supplied positive matches override). `compute_quality_score` weighted aggregator (0.30/0.20/0.30/0.20) returns `QualityScore` with all signals attached. Wired into `run_ocr_job` — `quality_breakdown` persisted on OCR-PO; `confidence_score` defaults to `quality.overall` when no caller value supplied (Stage-3 consensus in sub-batch D will override). 31 new tests covering boundary cases + integration; OCR-PO payload contract pinned.* |
| ✅ | Real-ESRGAN + OpenCV adaptive preprocessing for low-DPI scans | §3.3 — *Harness shipped 2026-05-10 (sub-batch A); **production OpenCV preprocessor wired 2026-05-10 (sub-batch H)**: `waraq/ocr/preprocessing_opencv.py` ships `opencv_preprocessor(image_bytes, source_dpi)` — bicubic upsample (`cv2.INTER_CUBIC`) targeting 300 DPI, capped at 2× scale to prevent artifact-amplification on tiny scans, plus `cv2.fastNlMeansDenoising` on luminance. PNG-encoded output keeps downstream rasterizer-consumers oblivious to the touch-up. Wired as the default in `run_ocr_for_page` via `preprocess_if_needed(preprocessor=opencv_preprocessor)`. Real-ESRGAN super-resolution (~70 MB + PyTorch) remains a Phase-7-calibration drop-in via the same `Preprocessor` Protocol — OpenCV INTER_CUBIC is the canonical, well-understood baseline for v1.0.* |
| ✅ | OCR confidence classification (Accepted ≥85% / Deficient 60-84% / Critical <60%) | §4.4 — *2026-05-10 (Phase 4 sub-batch A): `waraq/ocr/confidence.py` ships `OcrConfidenceClass(ACCEPTED|DEFICIENT|CRITICAL)` + `classify_confidence(score)` with canonical thresholds `ACCEPTED_MIN=0.85`, `DEFICIENT_MIN=0.60`. Boundary-exact: `0.85 → ACCEPTED`, `0.60 → DEFICIENT`. Inputs outside [0,1] are clamped before classification. Persisted on OCR-PO payload as `confidence_score` + `confidence_class`. v1.0 single-engine OCR records `None / None` honestly — Gemini does not return a usable per-page confidence; the canonical signal arrives with §3.4 Stage-3 multi-engine consensus (Phase 4 sub-batches C+D), which can populate the field without a schema change.* |
| ⏸️ | Manuscript/calligraphy specialist OCR | §3.3 — *2026-05-19: removed from the active v1.0 code path. The OCR engine enum is back to Gemini + OpenAI; diagnostics no longer exposes a specialist-manuscript endpoint. Decision is product-scoped rather than canon-denial: printed-book OCR and external tester deployment are the current priority, and manuscript OCR remains a future v2.0 decision if/when a usable corpus/model exists.* |

### Phase 5 — Multi-format upload + tier system (≈2 weeks)

| Status | Build | Canon |
|---|---|---|
| ✅ | Image formats (JPG/JPEG/PNG/TIFF/TIF/HEIC/WEBP) | §2.1 — *2026-05-12 (Phase 5 sub-batch K-1): `waraq/upload/file_type.py` ships `UploadFormat` enum + `detect_format(filename, head_bytes)` (suffix + magic-byte sniff; magic wins on disagreement) + `count_pages(path, fmt)` (PDF via pypdf, multi-page TIFF via PIL `n_frames`, single-page images = 1) + `is_image_format(fmt)`. `waraq/upload/service.py` finalize branch reads the first 64 bytes for magic detection, materializes one Page per logical page, and persists the canonical format on SCAN-PO payload `format` field. `waraq/ocr/page_runner.py` adds `_resolve_source_file` (returns path + format) + `_rasterize_page` (PDF → existing pdftoppm path; image → PIL re-encode to PNG so downstream OCR sees a uniform byte stream; TIFF picks the right frame). HEIC support via `pillow-heif` (registered at `waraq.upload` import). Upload router raises HTTP 415 on `UnsupportedFormat`. Frontend `UploadPdfDialog` accept attribute extended + copy "Upload PDF or image"; multi-format chunked transport unchanged (bytes-agnostic). 34 new tests across detection / page-counting / end-to-end finalize / rasterizer. Quality gate: 1414 passed, 1 skipped; ruff + mypy strict clean.* |
| ✅ | Document formats (DOCX/ODT/TXT/XML/HTML — TXT/XML/HTML skip-OCR) | §2.1 — *2026-05-12 (Phase 5 sub-batch K-2): `waraq/upload/text_extraction.py` ships `extract_paragraphs(path, fmt) → list[str]` for all five formats. DOCX via `python-docx` (already in deps for the write side), ODT via `odfpy` (new dep), TXT split by blank-line paragraphs, XML via `xml.etree.ElementTree` text-node walk, HTML via stdlib `html.parser` with block-tag-aware paragraph boundaries (skips `<script>`/`<style>`/`<head>`, decodes entities, inline tags flow inside paragraphs). UTF-8 decode with `errors='replace'` fallback so mis-encoded uploads don't 500. `UploadFormat` enum extended with DOCX/ODT/TXT/XML/HTML; suffix map adds `.docx/.odt/.txt/.xml/.html/.htm`; `is_direct_text_format(fmt)` is the branch predicate. **DOCX + ODT share ZIP magic (`PK\\x03\\x04`)** — suffix is authoritative for the direct-text group (magic would mis-classify). Finalize branches in `service.py`: direct-text → one Page (`ocr_status=GO`, no review needed since OCR didn't run), one Block (MAIN_TEXT/RTL), one Segment + Revision per paragraph (`change_source=OCR` — pragmatic interpretation of CAB §5.2's 4-value set: closest fit to "system-extracted from source"; documented as §2.7 surface call), SCAN-PO with `skip_ocr: true` + `paragraph_count`. `EmptyDocument` (no non-whitespace paragraphs) and `TextExtractionError` (parse failure) → HTTP 422. `_rasterize_page` in page_runner refuses direct-text formats with `PageOcrError`. Frontend: accept attribute extended to all five MIME + extensions; dialog copy "Upload document or image"; workspace button updated. 39 new tests across format detection / per-format extraction / end-to-end finalize / rasterize-refusal. Quality gate: 1453 passed, 1 skipped; ruff + mypy strict clean.* |
| ✅ | E-book formats (EPUB/MOBI/AZW/AZW3/DjVu — EPUB/MOBI direct text extract; DjVu special path) | §2.1 — *2026-05-12 (Phase 5 sub-batch K-3): `waraq/upload/text_extraction.py` extended with EPUB + MOBI/AZW/AZW3 extractors. **EPUB** via `ebooklib.epub.read_epub` + `get_items_of_type(ITEM_DOCUMENT)` walked in spine order; nav scaffolding excluded via 3 robust filters (EPUB-3 `properties=['nav']` marker, `isinstance(epub.EpubNav)`, legacy NCX media-type). Each item's XHTML feeds the shared `_parse_html_string` (the same block-tag-aware paragraph extractor used in the K-2 bare-HTML path). **MOBI/AZW/AZW3** via `mobi.extract(path)` which writes a temp directory of `.html` files; all html files are walked in lexical order, parsed through the same `_parse_html_string`, then the tempdir is cleaned up. DRM-protected AZW/AZW3 surface as `TextExtractionError("DRM-protected — cannot extract")` rather than bypassing DRM (§7.4 honor). **DjVu** is the "special path": treated as a raster format like PDF — goes through `_finalize_binary` (not direct-text) and OCR via `_render_djvu_page_png` (new helper, uses `ddjvu` system binary like `pdftoppm` for PDFs). `count_pages` calls `djvused -e 'n'` to count pages. `DjvuToolsMissing` exception surfaces as HTTP 503 (distinct from 415 for "format not supported" — the format IS supported but the host is missing `djvulibre-bin`). All five formats integrate into the existing `_DIRECT_TEXT_FORMATS` frozenset (EPUB/MOBI/AZW/AZW3) or the binary-finalize branch (DjVu). `UploadFormat` enum extended with EPUB/MOBI/AZW/AZW3/DJVU; suffix map adds `.epub/.mobi/.azw/.azw3/.djvu/.djv`. `_rasterize_page` in page_runner handles DjVu via `ddjvu` ppm→PNG and refuses direct-text e-book formats with `PageOcrError`. Frontend accept attribute extended for all 5; dialog copy + workspace button → "Upload book, document, or image". 24 new tests across format detection / per-format extraction / EPUB end-to-end finalize / DjVu count-pages-needs-tool / rasterize-refusal. Mypy override extended for `ebooklib.*` + `mobi.*`. Quality gate: 1477 passed, 1 skipped; ruff + mypy strict clean. **System install note**: `djvulibre-bin` is NOT installed by default — DjVu uploads on this host raise HTTP 503 with the install hint until `apt install djvulibre-bin` runs. Uses the standard adapter-wired/system-binary-activates pattern. EPUB/MOBI/AZW/AZW3 work without system deps.* |
| ✅ | Archive formats (ZIP/RAR/CBZ/CBR with filename-sort) | §2.1 — *2026-05-12 (Phase 5 sub-batch K-4): `waraq/upload/archive.py` ships `extract_and_sort(path, archive_fmt, dest_dir) → list[ArchiveEntry]` for ZIP/RAR/CBZ/CBR. ZIP/CBZ via stdlib `zipfile`; RAR/CBR via `rarfile` lib + `unrar` system binary. **Filename-sort** is case-insensitive alphabetical per canon §2.1 — Page01.jpg before PAGE02.jpg before page03.jpg. Path-traversal (zip-slip) neutralized by flattening any directory structure inside the archive to a `__`-joined basename + verified by test. **Noise filtering**: `__MACOSX/*`, `._*` dotfile resource forks, hidden `.*` files, `Thumbs.db` silently skipped. **One-level recursion** per canon ("recurse into supported formats"): nested archives are silently skipped (not an error), unsupported entries silently skipped. `UploadFormat` enum extended with ZIP/RAR/CBZ/CBR; suffix map handles `.zip/.rar/.cbz/.cbr`; new `is_archive_format(fmt)` predicate. `_finalize_archive` in `service.py` extracts entries, then loops calling either `_finalize_binary` (for image/PDF/DjVu entries) or `_finalize_direct_text` (for text-document/e-book entries) — each helper accepts `archive_context: _ArchiveContext | None` (records archive provenance on SCAN-PO: `archive_source_path`, `archive_sha256`, `archive_format`, `archive_entry_filename`, `archive_entry_index`) and `page_index_offset` (so Page indices flow continuously: entry-1 pages 1..N1, entry-2 pages N1+1..N1+N2, etc.). New exceptions: `ArchiveCorrupted` (HTTP 422) for unreadable archives, `EmptyArchive` (HTTP 422) when zero supported entries, `UnrarToolsMissing` (HTTP 503) when `unrar` not on PATH. Frontend dialog title → "Upload book, document, image, or archive"; accept attribute extended with archive MIMEs + extensions. 23 new tests: format detection, filename-sort + case-insensitive, noise filtering, unsupported-entry / nested-archive skip, mixed-format archive end-to-end, zipslip neutralization, empty/corrupted archive paths, RAR-without-unrar branch. Quality gate: 1500 passed, 1 skipped; ruff + mypy strict clean. **System install note**: `unrar` NOT installed by default on this host — RAR/CBR uploads return HTTP 503 with `apt install unrar` hint. Same system-binary-activates pattern as DjVu. ZIP/CBZ work without system deps.* |
| ✅ | 2 GB max enforcement | §2.1 — *2026-05-12 (Phase 5 sub-batch K-5): `MAX_UPLOAD_SIZE_BYTES = 2 * 1024**3` in `waraq/upload/service.py`. `start_upload` rejects declared `total_size_bytes > 2 GB` up front (no chunks transit). `append_chunk` defensively re-checks cumulative bytes-on-disk on every chunk (defends against a client that lied about the declared size). New `UploadTooLarge` exception → HTTP 413 in the router on both endpoints. Frontend disables the Upload button when `file.size > 2 GB` and shows a red banner with the canon §2.1 reference. 4 tests covering constant value, declared-over-limit, exactly-at-limit, cumulative-defensive-cap (uses monkeypatch on the constant so the test doesn't actually write 2 GB).* |
| ✅ | SHA-256 + filename duplicate detection + modal warning | §2.1 / §2.2 — *2026-05-12 (Phase 5 sub-batch K-5): `waraq/upload/duplicate.py` ships `precheck_for_project(session, project_uuid, filename) → PrecheckResult` for filename matching (pre-upload) and `find_sha256_matches(session, project_uuid, sha256, exclude_job_uuid) → tuple[DuplicateMatch, ...]` for content matching (post-finalize). Separate module from `service.py` to preserve the Abkürzung 7 AST guard (upload service forbidden from importing `ProvenanceObject`). New `GET /uploads/precheck?project_uuid=...&filename=...` endpoint returns filename matches before any bytes upload; finalize response extended with `duplicate_sha256_matches: list[DuplicateMatch]`. **Per-project scope** (no cross-project leakage). **Warning, not block** — user can confirm "upload anyway". Frontend shows amber banner inline when filename match detected; success block extends with content-duplicate notice when sha256 matches a prior page. `exclude_job_uuid` filters self-matches (necessary because archive recursion can produce multiple pages with the same SHA-256 in one upload). 8 tests covering empty-project, filename match, per-project scope, different-filename no-match, content match, self-exclusion, cross-project isolation.* |
| ✅ | 1-book-at-a-time modal warning | §2.2 — *2026-05-12 (Phase 5 sub-batch K-5): `precheck_for_project` also returns `project_has_existing_pages: bool` (True when the project already has any active Page rows). Frontend shows amber banner inline ("Project already has pages — canon §2.2 suggests one book per project") when the new upload would mix sources. Warning only; user confirms to proceed. 3 tests: false for empty project, true after first upload, per-project scoping.* |
| ⚠️ | Tier 0/1/2 system + application form + admin approval | §2.3 — *Application + admin-approval part shipped 2026-05-12 (Phase 5 sub-batch M); **Tier 0/1/2 portion deferred** per user's 2026-05-12 scope decision ("for now lets implement it such that when a user submits a registration application, they only get access when an admin approves from the admission dashboard. Once approved they can access all features. With time we'll implement the tier and subscription model"). What shipped: `ApprovalStatus` enum (`pending|approved|rejected`) + `approval_status`/`approved_at`/`approved_by_account_uuid`/`rejection_reason` columns on `accounts` (Alembic 0026); existing rows back-filled to `approved` to avoid retroactive lock-out. `waraq/admission/` service module ships `is_admin_email` (reads `ADMIN_EMAILS` env, case-insensitive, comma-separated), `list_pending_accounts` (FIFO over active+pending), `approve_account`, `reject_account` (records reason); `AlreadyDecided` exception → HTTP 409. `register_account` auto-approves `ADMIN_EMAILS` entries (bootstrap rule); everyone else lands in `pending` and gets no JWT until admin acts. `authenticate` refuses pending/rejected with new `AccountPendingApproval` / `AccountRejected` exceptions → HTTP 403 with specific user-visible messages. `POST /auth/register` response shape changed: `{approval_status, access_token?}` — token only for approved accounts. `GET /admin/admissions/pending` + `POST /admin/admissions/{u}/approve` + `POST /admin/admissions/{u}/reject` admin-only endpoints; `GET /auth/me` extended with `approval_status` + `is_admin`. Frontend: Register page shows "Application received — awaiting admin approval" panel for non-admin registrations; new `/admin/admissions` page lists pending accounts with approve/reject buttons (rejection reason input); nav link conditional on `account.is_admin`. 17 admission-service tests + 9 admissions-HTTP tests; pre-existing auth fixtures updated to add their email to `ADMIN_EMAILS` so the happy-path token-on-register tests still pass. **Tier portion (Tier 0/1/2 quotas + per-tier features) stays ❌ until user opens that work.** Quality gate: 1541 passed, 1 skipped; ruff + mypy strict clean.* |
| ❌ | Subscription expiry (1w/1m/6m/1y) + auto Tier 2 → Tier 1 fallback | §2.3 |
| ❌ | Inactivity deletion 6 months + warning emails | §2.3 |
| ❌ | Custom subscription per feature | §2.3 |
| ❌ | Guest user (upload + OCR + beforeunload + account-takeover after OCR) | §2.2 / §2.3 |
| ❌ | Trash 10-day purge job | §2.2 / §7.4 |

### Phase 6 — Style feature application + admin optimization (≈3 weeks)

CR-3 stilfeature follow-on AND canonical §4.18.3 admin panel.

| Status | Build | Canon |
|---|---|---|
| ❌ | §4.12.5 M1 / M2 / M3 translation modes per passage UI | §4.12.5 |
| ❌ | §4.12.3 Pre-imprint AR_DE Document A for main user/admin | §4.12.3 |
| ❌ | §4.12.4 Activation per language pair after threshold (calibration value open) | §4.12.4 |
| ❌ | §4.12.6 K-S1..K-S9 conflict-case matrix (suppression + dialogs + decision_source mapping) | §4.12.6 |
| ❌ | §4.12.7 Protective clauses enforcement | §4.12.7 |
| ❌ | §4.12.8 Learning rule with qualified signal classes (strong/weak/counter/null) | §4.12.8 / §4.13 |
| ❌ | §4.14 Editor PF-XX style markers (blue underline + hover tooltip + display-setting toggle) | §4.14 |
| ❌ | §4.14 Style profile rollback (return to earlier version, completed pages unchanged) | §4.14 |
| ❌ | §4.18.3 Admin Optimization Input Channel (admin-only, manual entry) | §4.18.3 |
| ❌ | §4.18.3 Admin Optimization Panel (6 tabs / 7 status states / status-conditional actions) | §4.18.3 |
| ❌ | Categories 1-8 for optimization entries | §4.18.3 |
| ❌ | §4.17 Vocalization 3 uncertainty levels (silent / tooltip / full panel) | §4.17 |
| ❌ | §4.17 Word frequency modal | §4.17 |
| ❌ | §4.17 Religious formulas display optionality (calligraphy / German / Arabic spelled out) | §4.17 |

(F1/F3/F4/F5 stilfeature backlog from Dokument C v1.1 §3 is canonically
deferred until CR-3 follow-on. Phase 6 builds the application layer that
v1.0 already canonizes, not new style-feature canon.)

### Phase 7 — Calibration + production hardening (≈2 weeks)

| Status | Build | Canon |
|---|---|---|
| 🔁 | Gold-corpus tests for OCR confidence thresholds, F-class severities, K-rule thresholds | §4.18 / Baseline Delivery Plan §4 |
| 🔁 | L-24 Häufungsschwellenwerte real measurement | §4.18.2 |
| 🔁 | Stilfeature Belegdichte threshold | §4.13 |
| 🔁 | OCR confidence threshold for Qurʾān recognition | §4.15.2 |
| ❌ | SSL termination + at-rest encryption | §7.4 |
| ❌ | 2FA optional | §7.4 |
| ❌ | Background-aware 2-hour idle timeout | §7.4 |
| ❌ | Bulk OCR + bulk translation as Celery + Redis with progress polling | (production hygiene; blocks book-scale today) |
| ❌ | Fly deploy + region | (deployment) |
| ❌ | veraPDF in production image | §2.1 PDF print export |

---

## Effort summary

| Phase | Estimate | Cumulative |
|---|---|---|
| 1 — Translation quality | ~2 weeks | 2 weeks |
| 2 — Qurʾān + Hadith sources | ~3 weeks | 5 weeks |
| 3 — UX completeness | ~1.5 weeks | 6.5 weeks |
| 4 — OCR multi-engine pipeline | ~4–5 weeks | 11 weeks |
| 5 — Multi-format + tiers | ~2 weeks | 13 weeks |
| 6 — Style application + admin panel | ~3 weeks | 16 weeks |
| 7 — Calibration + deploy | ~2 weeks | 18 weeks |

**Range: 16–19 weeks single-developer to canonical completeness.**
Compressed pace would be faster but with proportionally higher risk.

---

## Out-of-phase work (UI surfaces over existing canon)

### Sub-batch P — project delete (inactivation) ✅ (2026-05-13)

User request: "A user should be able to delete a project." Per H-5 this is **inactivation** (`active=false`), not a hard delete — the Project UUID survives in the DB forever; the row is just hidden from the API. All child Pages/Blocks/Segments/Revisions and PROVENANCE-Kern POs (SCAN-PO, OCR-PO, TRANSLATION-PO, LINEAGE_EVENT-PO, EXPORT_EVENT) are preserved by the canonical append-only audit policy (§5.3).

Design decisions (asked + answered before coding):
- **No cascade** — only the Project row flips. Children stay `active=true` in the DB but become unreachable because the tightened `_project_visible` helper in [waraq/api/_ownership.py](backend/waraq/api/_ownership.py) rejects any chain rooted at an inactive project. Simpler, faster, same UX outcome.
- **Auto-cancel in-flight** — any RUNNING/PENDING `ocr_auto_run` or `translation` Job for the project has `payload.cancel_requested=true` set in the same transaction as the inactivation. Runners cooperatively bail on their next iteration.
- **Modal with project name + Delete button** for the confirmation UX (no type-the-name friction; one-click delete after explicit confirmation).
- **No undelete UI** for now. An operator can flip `active=true` via SQL if ever needed; trash view is a separate later sub-batch.

**Backend** ([waraq/projects/service.py](backend/waraq/projects/service.py), NEW): `delete_project(session, project)` — idempotent (no-op on already-inactive), queries `Job` for in-flight rows of `_CANCELLABLE_JOB_TYPES = ("ocr_auto_run", "translation")`, sets `payload.cancel_requested=True` on each, calls `mark_inactive(project)` per H-5, flushes. Logs `project.delete.cancelled_in_flight_jobs` + `project.delete.inactivated` at INFO.

**Router** ([waraq/api/routers/projects_router.py](backend/waraq/api/routers/projects_router.py)): new `DELETE /projects/{project_uuid}` → **204 No Content**. Owner-checked via `owned_project_or_404`. `GET /projects/{u}` also re-routed through `owned_project_or_404` so deleted projects 404 there too (was returning the row before).

**Ownership tightening** ([waraq/api/_ownership.py](backend/waraq/api/_ownership.py)): new `_project_visible(project, account_uuid)` helper checks `project.active` in addition to existence and ownership. All four `owned_*_or_404` chains now reject inactive projects. Without this, deleted projects would leave children writable — load-bearing for the soft-delete contract.

**Frontend** ([frontend/src/components/DeleteProjectDialog.tsx](frontend/src/components/DeleteProjectDialog.tsx), NEW): confirmation modal showing project name + a destructive-styled Delete button. On success: invalidates the project list query, removes cached project + pages queries (so back-button can't show stale workspace), navigates to `/`. Disabled-during-pending; error shown inline on failure. Wired into `ProjectWorkspace` sidebar as a red-bordered "Delete" button next to Audit.

**Tests (+7 HTTP + 2 service)** in [tests/api/test_projects_routes.py](backend/tests/api/test_projects_routes.py): happy-path 204 + project disappears; unknown 404; cross-account 404; idempotent (second delete = 404 via ownership); in-flight ocr_auto_run gets `cancel_requested=True` (state stays running — runner is the only state-writer); child pages become unreachable post-delete (proves ownership-helper rejects-by-project-active); service-level direct flip + idempotent on `active=False`.

Quality gate (2026-05-13): focused pytest **12 passed in 22.48s**; ruff clean; mypy strict clean (241 source files); frontend build clean (526 KB / 162 KB gzipped).

§2.7 honest scope: tightening `_project_visible` to require `active=True` is a wide-impact change (17 router files use the helper). It's behaviourally correct — a deleted project shouldn't leave children writable — but any prior code that relied on inactive projects staying reachable would now 404. Audit showed no such code path; tests all green.

### Sub-batch O — OCR auto-run visibility refactor ✅ (2026-05-12)

User report: "When I run OCR, nothing shows that it is running, not even server logs. And it takes such a long time to run any successfully, also page refresh appears to stop it and no way to cancel running ocr explicitly."

Root cause: `POST /ocr/projects/{u}/auto-run` was synchronous in HTTP scope by design (the docstring literally said "intended for small projects in a dev workflow"). One HTTP request held open for the entire multi-page run → no progress signal, no logs, page refresh killed the request, no cancel.

This is **out-of-phase** (not Phase 5 / 6 scope) — infrastructure visibility work, same character as sub-batches N and M. Pattern mirrored from the translation `/run` endpoint's earlier visibility refactor.

**Backend** ([waraq/ocr/auto_run.py](backend/waraq/ocr/auto_run.py), NEW): `start_ocr_auto_run_job` materializes a PENDING Job with `total_pages` snapshot; `run_ocr_auto_run_job_in_background` is the BackgroundTask entrypoint that opens its own DB session (the request session is closed by then), drives `_execute` with per-page commits so progress + cancel-flag state are visible across sessions. Each per-page call wrapped in `asyncio.wait_for(timeout=120s)` so a hung Gemini/Cloud Vision can't stall the whole run. `request_cancel` sets `payload.cancel_requested=true`; the runner checks between pages and raises `OcrAutoRunCancelled` → `fail_job(error.phase="user_cancelled")`. `find_in_flight_for_project` returns the most-recent non-terminal Job for the project (drives the frontend resume-after-refresh).

**Router** ([waraq/api/routers/ocr_router.py](backend/waraq/api/routers/ocr_router.py)): `POST /ocr/projects/{u}/auto-run` now returns **202 Accepted** + `{ocr_job_uuid, project_uuid, state, total_pages}` immediately; the work runs detached. Three new companions: `GET /ocr/ocr-jobs/{job_uuid}` (status polling target), `POST /ocr/ocr-jobs/{job_uuid}/cancel` (cooperative cancel), `GET /ocr/projects/{u}/ocr-jobs/in-flight` (mount-time resume helper). Per-page `/ocr/pages/{u}/auto-run` stays synchronous (single page is short enough to wait on) but gains `asyncio.wait_for(timeout=120s)` + INFO-level logging on start/done/timeout/error so server logs actually show progress.

**Frontend** ([frontend/src/components/OcrAutoRunPanel.tsx](frontend/src/components/OcrAutoRunPanel.tsx), NEW): replaces the old fire-and-block "Auto-OCR all pages" button. Three states — idle (Start button), in-progress (live progress bar `N/M`, current page index, Cancel button), terminal (completed/failed result + "New run"). Polls every 1.5s while non-terminal; auto-stops polling on terminal state. On mount calls the in-flight endpoint so a page refresh during a long run picks up the progress UI without losing state. Wired into `ProjectWorkspace.tsx`; the old `bulkOcrMutation` removed.

**Logging**: `ocr_auto_run.queued | page.start | page.done | page.timeout | page.error | cancel.flagged | done | background.cancelled | background.failed` — all at INFO via `logging.getLogger(__name__)` with `extra={"ocr_job_uuid", "page_index", ...}`. Server logs now show real-time progress.

**Tests** (+12): [tests/ocr/test_auto_run_service.py](backend/tests/ocr/test_auto_run_service.py) — `start_ocr_auto_run_job` snapshot total / empty project; `_execute` completes when all pages succeed / cancel flag aborts between pages (verifies fail_job records `phase=user_cancelled` + `processed_count`) / skips non-ausstehend pages; `request_cancel` flips flag / idempotent / no-op on terminal; `find_in_flight_for_project` none / pending / skips-terminal / per-project scope. Existing [tests/api/test_ocr_auto_run_routes.py](backend/tests/api/test_ocr_auto_run_routes.py) updated for the new 202 + total_pages contract.

Quality gate: **1573 passed, 1 skipped** (+12 net vs N-2; one HTTP test reshaped); ruff + mypy strict clean; frontend build clean.

### Sub-batch O follow-up — orphan reaper (zombie-job fix) ✅ (2026-05-12)

Defect found in O after first real-traffic use: 5 `ocr_auto_run` Jobs in `state=running` with `updated_at` ≥ 5 h stale, all from BackgroundTasks that died with their uvicorn worker (most likely `--reload` cycles). The UI then polled the zombie row forever — `cancel_requested=true` but no worker to clear it. User report: "Cancelling OCR still showing 'cancelling' after 20hrs while the backend logs showed OCR running for 20hrs now with no result."

**Part A (immediate)**: one-shot SQL marked the 5 orphans as FAILED with `error.phase="server_restart_orphan"`. UI un-stuck.

**Part B (structural)**:

- New `reap_orphan_jobs(session, threshold_seconds)` in [waraq/ocr/auto_run.py](backend/waraq/ocr/auto_run.py): selects RUNNING/PENDING `ocr_auto_run` Jobs whose `updated_at < now - threshold`, calls `fail_job` with `phase=server_restart_orphan` + `previous_state` + ISO `reaped_at`. Returns reaped UUIDs. New constant `STALE_HEARTBEAT_THRESHOLD_SECONDS = 300` (= `2.5 * PER_PAGE_TIMEOUT_SECONDS`).
- Heartbeat mechanism: free — `TimestampMixin.updated_at` has `onupdate=func.now()`, and the runner already commits between pages (sub-batch O), so each iteration refreshes the row. No schema change, no migration.
- FastAPI `lifespan` async-context-manager in [waraq/api/main.py](backend/waraq/api/main.py) wired via `FastAPI(..., lifespan=lifespan)`. On startup: sweep all stale `ocr_auto_run` orphans; log `ocr_auto_run.startup.reaped_orphans` with count + UUIDs. DB failure during reap is logged + swallowed so app boot is never blocked.
- Poll-time self-heal in `GET /ocr/ocr-jobs/{job_uuid}`: if the row is RUNNING/PENDING, the endpoint calls `reap_orphan_jobs` inline before returning. Stale rows transition to FAILED on the very next poll the UI makes — mid-flight worker deaths self-heal within `STALE_HEARTBEAT_THRESHOLD_SECONDS`.

**Tests (+7)**: `TestReapOrphanJobs` (5 cases — stale RUNNING reaped, stale PENDING reaped, fresh RUNNING preserved, terminal COMPLETED preserved even when backdated, empty-DB returns `[]`) in [tests/ocr/test_auto_run_service.py](backend/tests/ocr/test_auto_run_service.py); `TestStatusEndpointSelfHeals` (2 cases — HTTP poll on stale row returns `state=failed` + `last_error.phase=server_restart_orphan`; fresh row stays `running`) in [tests/api/test_ocr_auto_run_routes.py](backend/tests/api/test_ocr_auto_run_routes.py).

Quality gate (focused 30/30 passed; full suite pending run-out): ruff + mypy strict clean.

§2.7 honest scope: heartbeat = `updated_at`, not a separate column (acceptable because the runner already commits between pages); reaper is by query, not by FK to the polled row, so a poll on Job X may also reap unrelated stale Job Y (cheap + desirable); multi-worker assumption documented (false-positive reap requires a worker stalled >5 min, effectively dead anyway).

### Sub-batch N-2 — Audit dashboard inline detail ✅ (2026-05-12)

Follow-on to N after user feedback: "all segments appear as seg #0" + "I can't see any OCR-PO to compare in review surface". Two fixes:

**Fix 1 (label correctness)**: `AttentionItem` extended with `block_index`; row labels go from `page #X · seg #Y` (where Y was always 0) to `page #X · block #Y · seg #Z`. The discriminating coordinate is (page_index, block_index) because the current pipeline emits one Segment per Block.

**Fix 2 (engine readings visible)**: The OCR-PO `engines[*]` payload was persisting only `text_chars` (not the actual text), so engine comparison was impossible. **OCR-PO payload extended (forward-only, additive)** to persist `engines[*].text` alongside the existing fields. Legacy OCR-POs written pre-N-2 keep only `text_chars` and surface in the UI as "Legacy OCR-PO: re-run OCR to see engine texts". §2.7 surface call — payload extension was documented in the worklog and approved by the user before shipping.

New endpoint `GET /projects/{u}/audit/segments/{satz_uuid}/detail` returns `SegmentAuditDetailResponse{ocr_engines[], translation_situation, open_befunde[], …}`. Ownership-checked via project_uuid. Frontend: attention rows are now expandable (▶/▼ chevron). Expanding lazy-fetches the detail endpoint and renders: current segment text (RTL), engine readings side-by-side (RTL panes, max-h-48 scroll), translation situation + target, open Befunde with detection_context.

6 new tests: block_index round-trip on AttentionItem; per-segment detail returns engines with text when persisted; legacy OCR-PO returns engines with text=None + ocr_engines_have_text=False; translation_situation surfaced; open Befunde surfaced; cross-project lookup returns None.

Quality gate: 1561 passed, 1 skipped; ruff + mypy strict clean; frontend build clean.

### Sub-batch N — Project Audit Dashboard ✅ (2026-05-12)

User asked for "an audit page for every project where information on the ocr, translation and every other important things carried out on the project can be seen". Shipped as out-of-phase (not Phase 5 / 6 scope) because it's a **read-only UI surface over existing PO data** — no new domain concepts, no new write paths, no §2.6 CR cycle needed.

Backend: `waraq/audit_dashboard/service.py` exposes `summarize_project(session, project_uuid) → ProjectAuditSummary` (one-shot counts/distributions across page ocr_status, OCR-PO confidence_class, OCR-PO engine_agreement, TRANSLATION-PO cross_check.situation, open Befunde by severity, open KonsistenzBefunde, open ConflictInstances — all per-project scoped) and `list_attention_segments(session, project_uuid, filters, limit) → list[AttentionItem]` (filterable per-segment list with `AttentionFilter` enum: `low_confidence | divergent_ocr | cross_check_substantive | cross_check_ambiguity | cross_check_failed | open_audit_finding | open_conflict`). Two HTTP endpoints under `waraq/api/routers/audit_dashboard_router.py`: `GET /projects/{u}/audit/summary` and `GET /projects/{u}/audit/attention?filter=...`. Both `owned_project_or_404`-gated.

Frontend: `frontend/src/pages/ProjectAudit.tsx` renders summary card (4 stat tiles + 5 distribution rows with green/amber/red tone-coded chips) + filter chips (7 attention categories) + filterable attention list (per-row chip + page/segment refs + filter-specific detail + deep-link to the existing per-page review surface). Route `/projects/:projectUuid/audit`; nav button "Audit" in `ProjectWorkspace`.

**Decision discipline**: per §2.6, the audit page never writes — all decisions (approve OCR, resolve audit finding, etc.) continue to flow through the existing canonical review surfaces (OCR-Review, segment workspace, audit resolution). Row deep-links to `/projects/{u}/pages/{page_uuid}` so the user can act there. Action-taking inside the audit page is a possible follow-on sub-batch but would need to re-confirm H-1/H-2/H-6 invariants explicitly.

Tests: 14 service-level tests covering empty-project zero counts, confidence/agreement/cross-check distribution correctness, per-filter semantics (LOW_CONFIDENCE / DIVERGENT_OCR / CROSS_CHECK_SUBSTANTIVE / OPEN_AUDIT_FINDING), per-project scoping (no leakage), limit cap, no-filter-passed = union-of-all-filters.

Quality gate: 1555 passed, 1 skipped; ruff + mypy strict clean; frontend 517 KB / 160 KB gzipped.

---

## Parked decisions (awaiting user choice)

### Manuscript OCR specialist engine — parked for v2.0 (updated 2026-05-19)

**State today.** The previously wired specialist adapter, routing flag, diagnostics endpoint, frontend diagnostics section, tests, and local package install have been removed before external-tester deployment.

**Why.** The current product path is printed-book OCR with Gemini + OpenAI OCR. Research on 2026-05-11 found no publicly available pretrained specialist model that clearly targets the classical Islamic manuscript corpus we would need. Keeping the adapter active adds deployment weight and tester confusion without improving the current workflow.

**Revisit trigger.** Bring this back only if manuscript material becomes a real tester requirement or we obtain/train a model that materially outperforms the current OCR pair on that corpus.

**Sources cited.**
- [Muharaf recognition model (Zenodo 14295489)](https://zenodo.org/records/14295489)
- [TariMa/BULAC manuscript models (Zenodo 7810571)](https://zenodo.org/records/7810571)
- [RASAM dataset (GitHub calfa-co/rasam-dataset)](https://github.com/calfa-co/rasam-dataset)
- [Agapet medieval Christian Arabic HTR datasets (Zenodo 15473122)](https://zenodo.org/records/15473122)
- [OpenITI arabic_script_ocr_models](https://github.com/OpenITI/arabic_script_ocr_models)
- [HATFormer paper (Muharaf-trained transformer baseline, 8.6% CER)](https://arxiv.org/html/2410.02179v2)
