# **DOCUMENT 1 – LIVING MASTER DOCUMENT (CANON)**

Sole canonical primary source – cleaned full-text version.

CRITICAL: No reformulation of substance. No simplification that changes meaning. No silent re-baselining. This cleaned version contains exclusively cosmetic, structural, and linguistic-substantive sharpenings. Substantive content is unchanged.

## **1. PROJECT IDENTITY**

  - **Name**: Waraq (ورق) – Arabic for "leaf/page."
  - **Short description**: Professional publishing platform for Arabic→German/English book translations.
  - **Goal**: Produce print-ready books from Arabic scans/PDFs.
  - **Problem**: Professional translators of Islamic and historical Arabic texts have no specialized tool that unites OCR, translation, style profile, registries, and export in a single end-to-end workflow.
  - **Target audience**: Publishers and translators of Islamic and historical Arabic texts.
  - **Access**: Internal tool with application system – administrator decides on access.
  - **Core promise**: From Arabic scan to print-ready German or English book in a single, auditable workflow.

**Supported language combinations:**

  - Arabic → German
  - Arabic → English
  - English → German
  - German → English

**Translation transfer:** AR→DE already established → EN taking the German style into account.

## **2. ESTABLISHED CONCEPT**

### **2.1 Mandatory Modules and Features**

**Phases:**

  - **Phase 1 – Upload:** all formats, duplicate detection (SHA-256 content hash primary, filename secondary), 1 book at a time, max. 2 GB.
  - **Phase 2 – OCR:** 5-stage reconstruction pipeline (Gemini 2.5 Pro Vision + kraken + Real-ESRGAN + CAMeL Tools + Farasa + Mishkal + LayoutParser + DocTR).
  - **Phase 3 – OCR review:** difficulty report, guided review, DPI comparison view.
  - **Phase 4 – TOC confirmation:** Arabic/German comparison view, adjust chapter headings. No TOC detected → page-by-page split. Manual TOC definition is not part of this version. Separate CR if desired later.
  - **Phase 5 – Translation:** GPT-4o + Gemini 2.5 Pro in parallel, RAG, chunk strategy.
  - **Phase 6 – Notification + TOC confirmation:** user informed, final TOC review.

**Visible archives and registries (5 items):**

1.  Glossary (precedence over learned style, never automatically overwritable)
2.  Terminology registry
3.  Religious formulas registry
4.  Reference and entity system
5.  Style profile Option B (account-bound)

**Style feature "Recognize my translation style":** Fully specified in Document A v1.0, Document B v1.2, and Document C v1.1.

**Export:** DOCX (Word template Option B), PDF digital and print, OCR Export DOCX (separate from publication export).

**Upload file formats:**

  - Images: JPG, JPEG, PNG, TIFF, TIF, HEIC, WEBP
  - Documents: PDF, DOCX, ODT, TXT, XML, HTML
  - E-books: EPUB, MOBI, AZW, AZW3, DjVu
  - Archives: ZIP, RAR, CBZ, CBR
  - Maximum size: 2 GB

**Format logic:**

  - ZIP/RAR/CBZ/CBR → automatic page sorting by filename
  - TXT/XML/HTML → OCR skipped
  - EPUB/MOBI/AZW → direct text extraction
  - DjVu → special OCR path

### **2.2 Mandatory Product Logic**

  - Glossary always takes precedence over learned style. No single-instance override of a glossary entry in context is possible. Anyone wishing to deviate must change or delete the entry.
  - No empty pages in Arabic works.
  - Western digits everywhere – never Arabic-Indic digits. Violations of the digit standard are handled near the guard layer and are blocking. No audit case, no user judgment – direct system mechanism.
  - Religious formulas as calligraphy/Unicode: ﷺ, ﷻ.
  - Header shows Heading 2 (chapter), not Heading 1.
  - On export, the user is asked which heading level marks chapters – never assume.
  - Transliteration standard: EI2 with Q (instead of Ḳ) and J (instead of Dj).
  - No timeout during an active background process, otherwise 2 hours.
  - Trash: 10 days.
  - Duplicate and 1-book warning: modal popup.
  - Guest user beforeunload warning: active as long as OCR is running.
  - Notifications are sent by default via email and in-app. Email can be disabled by the user.
  - Morphology panel: side panel.
  - Word form frequency analysis: modal dialog.

### **2.3 User Access System**

|  |  |  |
| :-: | :-: | :-: |
| **Tier** | **Name** | **Function** |
| 0 | Applicant | Application form only |
| 1 | Full Version Free | Everything fully available |
| 2 | Full Version Paid | Everything fully available |

**Expiry periods:** 1 week / 1 month / 6 months / 1 year.

**Inactivity deletion:** 6 months (except with active subscription).

**Warnings:**

  - 1 month before inactivity deletion via email.
  - 7 days before subscription expiry via email.

**Subscription expiry:** Upon expiry of a paid subscription (Tier 2), automatic switch to Tier 1 (Full Version Free), without functional restriction. Ongoing projects remain fully accessible.

**Custom subscription (yes/no):** Recognize my style, glossary, terminology registry, religious formulas registry, reference folder, max. pages per work, max. works total.

**Guest user:** Upload without account, no editing (buttons inactive), can switch views. Closing the browser before OCR completion → data lost. As long as OCR is running, a beforeunload warning is active. OCR completed → account creation and project takeover possible.

## **3. ESTABLISHED ARCHITECTURE**

### **3.1 Absolutely Mandatory Working Rules**

  - No silent architectural changes – every change only as an explicit CR.
  - No code without explicit coding release from the user.
  - No new features without a complete CR pass (analysis → decisions → CRs → tickets → sprint → release).
  - No silent re-baselining.
  - No new sprint planning without an explicit assignment.
  - Shortly before exhaustion of the context window (~70%): inform the user immediately, then create handover documents.

### **3.2 Released Baselines**

|  |  |
| :-: | :-: |
| **Document** | **Version** |
| Waraq Core Architecture Baseline | v1.0 |
| Waraq Implementation Translation Baseline | v1.0 |
| Waraq Engineering Execution Baseline | v1.0 |
| Waraq Delivery Backlog Baseline | v1.0 |
| Sprint-0 through Sprint-6 plans | v1.0 |
| OCR Export Consolidated Final Version | v1.3 |
| Document A – Canonical User Style Corpus | v1.0 |
| Document B – Style Feature Specification | v1.2 |
| Document C – Style Feature Integration Notice | v1.1 |
| Canonical Document Style Templates Baseline | v1.1 |

**3.3 OCR Engine Combination**

The OCR engine combination is based on a multi-stage, cross-engine system. The concrete role distribution among the OCR engines is provisionally canonical and revisable.

Current OCR reading lines:

Main reading line / vision OCR: Gemini 2.5 Pro Vision.

Additional OCR reading line: Google Cloud Vision (DOCUMENT_TEXT_DETECTION), particularly for modern printed Arabic scans.

Manuscripts and calligraphy: kraken + eScriptorium.

Image preprocessing: Real-ESRGAN + OpenCV (adaptive).

Validation: CAMeL Tools + Farasa + Mishkal.

Document structure: LayoutParser + DocTR.

The concrete selection, weighting, and role distribution of the OCR reading lines may be adjusted depending on document type, page structure, block class, and empirical test results. For modern printed Arabic scans, Google Cloud Vision may be deployed as base or primary reader, provided structured gold-corpus tests confirm this.

Changes to OCR engine assignment are made exclusively on the basis of structured empirical tests (gold-corpus evaluation) and are canonically determined in a separate decision process. The underlying consensus principle from §3.4 is unaffected by this.

**3.4 OCR – 5-Stage Reconstruction Pipeline**

Stage 1 – Visual Structure Analysis: reading-direction map, text-density analysis, baseline detection, font-size mapping, isolation of decorative elements, page orientation per block, tabular structures, text columns, heading blocks, footnote area, divider lines, page numbers, Quranic verse blocks, marginalia.

For column and block ordering: geometric ordering analysis (x, y, width, height), topological sorting as a graph, exact localization of column dividers, cross-validation with OCR text, anchor elements as reference points, slanted lines via Hough transform.

Stage 2 – OCR per text block (separately, not whole page). A text block may be read by one or more OCR reading lines. The choice of reading line depends on document type, layout complexity, image quality, and block class. The OCR reading lines considered include in particular Gemini 2.5 Pro Vision, Google Cloud Vision (DOCUMENT_TEXT_DETECTION), and kraken/eScriptorium for manuscript and calligraphy cases. The concrete assignment remains provisional and is validated by gold-corpus tests.

Stage 3 – Semantic Reconstruction (triply validated):

Rule-based: Arabic grammar.

AI-based: GPT-4o and Gemini 2.5 Pro in parallel as consensus signal providers within the AI validation line. Both models are equal in rank; within the AI line there are no primary/check roles. In case of disagreement between the two models, no artificial winner is formed; instead confidence drops and the passage is prioritized into OCR review (see quality principle at the end of §3.4).

Statistical: Shamela database.

The §3.6 model assignment (Primary GPT-4o / Check Gemini 2.5 Pro) applies exclusively to the translation pipeline and remains unaffected by this AI validation line.

Revisability of AI model choice in Stage 3: provisionally canonical. A revision of the concrete model choice is made exclusively in a structured decision in case of newer or clearly better models, including within the same model family. No silent model-switching change. The revision concerns exclusively the model choice, not the consensus architecture within the AI validation line.

The consensus principle of semantic reconstruction is independent of the concrete selection of OCR reading lines. Additional OCR reading lines such as Google Cloud Vision do not change the principle of consensus formation but provide additional reading signals for evaluating a block.

Stage 4 – Line reconstruction: word probability model, line continuity score, syllable separation detection, homoglyph correction (ر/ز, د/ذ etc.).

Stage 5 – Quality check: page-by-page completeness check, character-count plausibility, structural symmetry in multi-column layouts, matching of known passages (Quran, hadith).

Overarching OCR quality principle: If, after running through the prescribed reconstruction stages, multiple strong competing readings remain, no artificial winner is formed. Confidence drops, the passage is prioritized in OCR review.

### **3.5 External Sources and Databases**

**Offline local (server-side):**

  - **مكتبة الشاملة (Shamela)** – complete database including Lisān al-ʿArab and Tāj al-ʿArūs. Lisān al-ʿArab (20+ volumes) and Tāj al-ʿArūs (40 volumes) are treated within Shamela as independently queryable units; searching within individual works is possible, not only across the entire collection.
  - Shamela is used in two functionally separated modes:
      
      - **Mode A – OCR-internal:** system-triggered in OCR Stage 3 (semantic reconstruction) as plausibility check of recognized text fragments.
      - **Mode B – user-driven:** lexical research and footnote creation in the translation phase.
  - The data source is the same in both modes; trigger, purpose, and result processing differ.

**APIs:**

  - quranenc.com – Quranic verses (german_rwwad for German, english_rwwad for English)
  - sunnah.com – hadith verification
  - dorar.net – hadith

**Web scraping (Playwright):** islamweb.net, جامع السنة النبوية, المكتبة الوقفية.

**Scraping secondary-path rule:** Scraping is a strict secondary path relative to an existing API of the same source. For dorar.net: API path primary, scraping only as fallback when the API does not cover the required functionality. A DOM break is treated as a §4.18 Class B failure without retry; no silent self-healing at runtime.

**Request profile of external sources (Model U):** External HTTP-based sources (APIs and scraping paths) follow a uniform conservative request profile. Local sources are excluded; Shamela as a local collection is an explicit exception. Concrete rates, pauses, upper limits, and resumption times remain open and will be set after real measurement.

**Confidence ranking of hadith sources:** quranenc > sunnah > Shamela > dorar > islamweb > others.

For hadith verification (§4.16), the linear confidence ranking is refined by a domain-specific multidimensional comparison and consensus logic; the linear ranking applies in this case as a tie-breaker when the consensus logic does not yield a clear winner.

**Arabic Qurʾān reference collection (AR reference collection):** Independent local collection with vocalized Arabic Qurʾān text. Canonical carrier for Arabic reference text and vocalization per §4.15. Concrete source designation and update mechanism still open.

**Local fallback Qurʾān translations:** Complete local copies of the german_rwwad and english_rwwad translations. Primary is always quranenc.com API. Fallback only on API failure. Weekly automatic sync for updates.

**Specification status of external sources:**

  - All external sources: API endpoints, authentication, rate limits, error behavior, and scraping structures are fully unspecified – active work front.
  - Interface working drafts (1 OCR main engine, 2 OCR semantic supplementary validation, 3 translation AI, 4 Qurʾān, 5 hadith, 6 Shamela/lexicon) exist but are not yet canon.
  - Model assignment Primary/Check for translation AI is canonically established in §3.6; OCR Stage 3 has its own logic (see §3.4).

### **3.6 Translation Pipeline**

**Model assignment:**

  - **Primary** (lead translation draft): GPT-4o.
  - **Check** (parallel counter-translation and quality check): Gemini 2.5 Pro.
  - The assignment applies system-wide for the §3.6 translation pipeline. The model assignment in OCR semantic reconstruction (§3.4 Stage 3) is unaffected and remains independent.

**Revisability of the model assignment:** The concrete model assignment (Primary GPT-4o / Check Gemini 2.5 Pro) is provisionally canonical and reflects the currently best available state. It remains binding until reassessed and explicitly revised in a structured decision. A reassessment is particularly indicated when newer or clearly better models become available – including within the same model family. The revision concerns exclusively the concrete model choice; the role logic of this section and the separation from the OCR Stage 3 assignment remain unaffected. No silent model-switching change.

**Check model correction right:** The check model has no general silent correction right. Four situation types apply:

1.  **Agreement:** Primary output is adopted.
2.  **Objective deterministic finding:** Auto-correction is enforced; always logged and viewable by the user.
3.  **Substantive interpretive deviation:** no silent correction; confidence drops; the passage is marked for review.
4.  **Genuine ambiguity despite cross-check:** user notice; no silent decision.

**No silent role swap between primary and check path on failure:**

  - If the primary path fails, the check path does not silently take over the primary role; the chunk waits or enters a wait state with auto-retry.
  - If the check path fails, the primary output continues; the affected passages are considered not cross-checked and are logged accordingly.

**Audit findings:** Substantive audit findings (A-01 through D-03) do not stop the translation flow. They are persisted as findings and carried forward in the preflight logic (§4.6 / §4.7).

**API failure behavior:** On API failure: silent background marking of the affected passage, dashboard status indicator, automatic retry, manual retry button available to the user. After 30 minutes without recovery, active user information via in-app and email is triggered. The dashboard status indicator persists unchanged.

**Chunk and context rules:**

  - Chunks never end mid-sentence.
  - Each chunk contains: style core, glossary entries, entity database, semantic summary.
  - The last paragraph of the previous chunk serves as context.
  - RAG for scalability.

**Other:**

  - Progress display page-by-page.
  - Notifications by default via email and in-app. Email can be disabled by the user.

### **3.7 User Interface**

**Dashboard:** My Projects, Upload Books, Account Settings, Usage Statistics, API Usage Statistics.

**Main editor:** Login → Dashboard → Open project → Choose view [Arabic / Translation / Comparison] → automatically in editing mode.

**Toolbar:** View tabs / Preview / Save / Export.

**Comparison views (5 modes):**

1.  Original book / OCR
2.  Original book / Translation
3.  OCR / Translation (default)
4.  Triple view
5.  Single view fullscreen

**Triple view:** draggable separators 15–70%, double-click = 33/33/33%.

**Synchronization:**

  - Page-level between original book and OCR.
  - Sentence-level between OCR and translation (always active).
  - Sentence ID in the format [AR-047-003].
  - Click on sentence → all windows jump to that location.

**Preview mode (Option A):** settings panel and live book preview (double page, page-turnable). Settings: page format, German and Arabic typography, quote elements, header and footer, TOC, footnotes, chapter start.

**Layout profiles:** unlimited storage, cross-project.

## **4. ESTABLISHED LOGIC AND RULES**

### **4.1 Hard Invariants H-1 through H-7**

Full definitions in Core Architecture Baseline v1.0.

### **4.2 Governable Project Rules G-1 through G-4**

Full definitions in Core Architecture Baseline v1.0.

### **4.3 Core Objects and Identities**

Full definitions in Core Architecture Baseline v1.0: Page-UUID, Block-UUID, Sentence-UUID, Revision-UUID, Decision-Event-UUID, Concept-ID, source attributes. Protection model with lock level 1/2/3, revision model, promotion pipeline.

### **4.4 OCR Error Classes F-01 through F-09**

Full definitions with severity matrix and aggregation logic in Core Architecture Baseline v1.0.

**OCR quality classification:**

  - ✅ **Accepted:** confidence ≥ 85% and all validations confirmed.
  - 🟡 **Deficient:** confidence 60–84% or one condition not met.
  - 🔴 **Critical:** confidence < 60% or reading order contradictory or > 15% words impossible.

**OCR display (maximally simple):** Noto Sans Arabic, 14 pt. Headings only bold and with greater spacing. Quranic verses and hadiths only indented with edge rule. Footnotes 11 pt with separator line.

### **4.5 Release Gate Logic (Go/No-Go)**

Full definitions in Core Architecture Baseline v1.0.

### **4.6 Translation Audit A-01 through D-03**

The audit categories A-01 through D-03 are divided into three classes. The authoritative source for the full category definitions and their classification is the Implementation Translation Baseline v1.0. The reconciliation has been performed.

**Scope boundaries:**

  - Quranic verse and hadith handling are independent strands (§4.15 / §4.16) and not part of this audit strand.
  - Style feature logic is strictly separated.
  - Violations of document style templates, RTL encoding/RTL application, and digit standards are not part of this audit strand – they are handled near the guard layer (§4.7).

**Confirmed principles:**

  - No overall score. The audit checks per segment whether concrete defined rules have been observed or violated.
  - A violation has a class, a severity, and a consequence.
  - The audit runs in parallel to the translation output.
  - Ignoring an audit finding is always logged (audit_resolution decision_event, decision = ignored).

**Three classes:**

**Critical – blocking** (passage blocked until resolved, P-03):

  - C-01: Terminology entry violated – Terminology registry or Glossary (violation of G-2).
  - D-03: Religious formula not per registry (violation of G-3).

**High – mandatory notice** (must be actively decided per passage before export, P-04):

  - A-01: إِنَّ / أَنَّ not transferred.
  - A-04: أَمَّا...فَ construction not fully transferred.
  - B-01: Idāfa resolved too freely.
  - B-02: Dual not visible.
  - C-02: Islamic technical term without first-occurrence handling.
  - C-03: Translator's addition not marked.

**Medium – notice** (export with warning possible, W-01):

  - A-02: لَ (emphasis) not transferred as emphasis.
  - A-03: فَ not transferred context-sensitively.
  - B-03: Gender difference not transferred.
  - B-04: Conditional clause not text-faithful.
  - D-01: Metaphor or idiom not literal with footnote.
  - D-02: Sajʿ without notice in footnote.

**Consequence logic:**

  - **Critical:** Ignoring not possible – blockade.
  - **High:** Ignoring requires active decision per passage – is logged.
  - **Medium:** Ignoring triggers go_with_warning on export – is logged.

### **4.7 Export Preflight P-01 through P-06 / W-01 through W-08**

Full definitions in Engineering Execution Baseline v1.0.

#### **4.7.1 Preflight Layered Model (canonically confirmed)**

The preflight dialog contains two conceptually independent layers:

**Layer 1 – Configuration obligations:** The 4 mandatory questions form an independent configuration layer in the preflight dialog. They request necessary export parameters and do not check any finding in the document. They do not automatically occupy P-01 through P-06.

**Layer 2 – Gate checks:** Blocking P-gates (P-01 through P-06) and warning-based W-gates (W-01 through W-08) check facts in the document or export state against defined conditions.

#### **4.7.2 Mandatory Questions on Export (Configuration Layer)**

1.  Which heading level should be displayed in the header?
2.  Which heading level marks chapter breaks?
3.  Position of the TOC (front / back)?
4.  Display Arabic chapter headings in the body text (yes/no)?

**PDF export:** Digital (RGB) or Print (PDF/X-1a, CMYK, 3 mm bleed).

#### **4.7.3 Guard-near Handling Before Preflight (canonically confirmed)**

  - **Digit standard violations:** guard-near; blocking; no audit case, no user judgment – direct system mechanism. Check before preflight dialog.
  - **Critical RTL encoding/RTL application errors:** guard-near; integrity violation; blocking. Check before preflight dialog.
  - **Document style template integrity violations:** guard-near; blocking. Check immediately before opening of the preflight dialog; if a violation exists, the preflight dialog is not opened. Resolution requires technical removal of the violation.
  - **Critical font availability:** guard-near; blocking; check before preflight dialog. If one of the four critical fonts (KFGQPC Uthmanic Script HAFS, Traditional Naskh, Noto Sans Arabic, Calibri) is missing, the preflight dialog is not opened. Resolution requires technical restoration of the font; mere user confirmation does not suffice. No P-slot is occupied.
  - **Gradual document style template deviations:** warning-based; non-blocking. Reach the preflight dialog. Occupy W-03.

#### **4.7.4 Occupied Gates (confirmed)**

  - **P-03:** independent blocking gate in the preflight gate-check layer, structurally on par with P-04.
  - **P-04:** High audit findings – strongest structural fit as a blocking preflight gate.
  - **W-01:** Medium audit findings (A-02, A-03, B-03, B-04, D-01, D-02), occupied via §4.6.
  - **W-02:** K-01 through K-07 consistency warnings – independent group.
  - **W-03:** Gradual document style template deviations – independent slot.

#### **4.7.5 Independent Named Group – Hadith Verification Status**

Independent named group within the gate-check layer: **Hadith Verification Status.** The group is not a new layer and does not occupy any of the open P or W slots. It carries two state classes per §4.16:

  - **H-2 blocking:** passage not exportable as long as H-2 persists; resolution exclusively via the action types canonized in §4.16.
  - **H-1 warning-based:** passage exportable with go_with_warning confirmation, applied consistent with §4.9 E-1; decision_source preflight_confirmation per §4.10.

No new decision_source values. No change to the 7 canonized action types. H-0 passages do not generate a group entry. The gate effect of the group is managed slot-independently; a later formal occupation of open P/W slots remains possible without silently changing this canon.

#### **4.7.6 Still Open**

  - **P-01, P-02, P-05, P-06:** No clean candidates currently identifiable in the existing canon of publication export. Slots remain open for now.
  - **W-04 through W-08:** No further clean candidates currently identifiable in the existing canon of publication export. Slots remain open. No directional binding pre-empted. No new warning-based states introduced.

### **4.8 Work-wide Consistency Check K-01 through K-07**

Full definitions in Engineering Execution Baseline v1.0.

K-01 through K-07 are not export-blocking. They generate warnings. Exception: If a K-violation simultaneously violates a Critical class within the meaning of §4.6, the audit gate applies. Gradual document style template deviations fall under W-03 – warning-based, non-blocking.

### **4.9 OCR Export Final Version v1.3 – Mandatory Decisions E-1 through E-10**

|  |  |
| :-: | :-: |
| **No.** | **Decision** |
| E-1 | go_with_warning permitted with double warning |
| E-2 | Two modes: working state / released state |
| E-3 | Hard conflicts block; editorial residual uncertainties = warning |
| E-4 | Text exactly as present – no harakat addition |
| E-5 | Default: MT + UE; optional: FN, QR, HD, RN |
| E-6 | Editorial markings: user decision |
| E-7 | DOCX is part of the feature |
| E-8 | Own PO type: OCR_EXPORT_EVENT |
| E-9 | Own function get_ocr_exports_for_segment() |
| E-10 | Strict versioning: ocr_revision_snapshot[], active_decision_event_uuids[] |

**OCR Export DOCX – formally mandatory requirements:**

  - Per-paragraph RTL.
  - True DOCX footnotes.
  - Block-type structure (MT/UE; optional FN/QR/HD/RN).
  - Harakat exactly as present.
  - Editorial markings as DOCX comments when activated.
  - DOCX opens in Word without repair.
  - No Option B template, no book layout – simple working document.
  - Separated from style feature.

**Hard conflicts (always blocking):**

  - F-06-QR without resolution.
  - F-07 critical.
  - F-08 undecided.
  - conflict_instance with unclear text state.
  - Inactive segments without lineage resolution.
  - Critical RTL encoding problems.

### **4.10 decision_source Enum (10 values, non-overlapping)**

|  |  |
| :-: | :-: |
| **Value** | **Domain** |
| ocr_review | OCR error class resolution |
| lock_management | Setting/clearing of lock flags |
| conflict_resolution | Conflict resolution |
| glossary_management | Entry change in the maintenance registries Glossary, Terminology Registry, and Religious Formulas Registry. Scope boundary: no application to style rule changes (style_management), no application to conflict resolutions without registry change (conflict_resolution), no application to audit-finding resolutions (audit_resolution). |
| export_confirmation | Only OCR export mandatory questions |
| preflight_confirmation | Only final publication export |
| translation_pipeline | Translation phase |
| audit_resolution | Audit-finding resolution |
| consistency_resolution | Consistency-group resolution |
| style_management | Style profile decisions |

### **4.11 Query Rule** **active_decision_event_uuids[]** **(deterministic, v1.3)**

exported_segment_uuids =

  SELECT satz_uuid FROM segments

  WHERE current_rev_uuid IN ocr_revision_snapshot[]

    AND active = true

exported_page_uuids =

  SELECT page_uuid FROM pages

  WHERE page_number IN export_config.page_range

    AND project_uuid = current_project_uuid

    AND active = true

current_export_confirmation_uuids =

  SELECT decision_event_uuid FROM decision_events

  WHERE decision_source = 'export_confirmation'

    AND related_export_attempt_id = current_export_attempt_id

    AND is_superseded = false

active_decision_event_uuids[] =

  SELECT decision_event_uuid FROM decision_events

  WHERE is_superseded = false

    AND decision_source IN ('ocr_review', 'lock_management', 'conflict_resolution')

    AND ((scope_type = 'segment' AND scope_uuid IN exported_segment_uuids)

      OR (scope_type = 'page'    AND scope_uuid IN exported_page_uuids))

  UNION

  current_export_confirmation_uuids

This OCR-export query rule is snapshot-specific and is deliberately limited to segment- and page-scoped decision events as well as the mandatory-question confirmations of the current OCR export attempt. It does not restrict the general scope_type enum. The general scope_type enum encompasses, per Core Architecture Baseline §B.1: segment, page, block, account, project.

### **4.12 Style Feature – Priority Logic, Conflict-Case Matrix, Learning Rule**

#### **4.12.1 Priority Logic (immutable)**

  - **Tier 1 – General system rules (always take precedence):** transliteration (EI2 Q/J), glossary, terminology registry, religious formulas registry, Quranic verse handling (quranenc.com), hadith handling, technical-term handling, all other canonical standards.
  - **Tier 2 – Canonical user style:** Document A (User Style Corpus v1.0) and Document B v1.2 (Feature Specification).
  - **Tier 3 – Individual reference sentences:** Only as structured bilingual style examples – never as a silent substitute for system rules.

A style profile suggestion that conflicts with Tier 1 is not executed. Silent override of a Tier 1 system rule by the style feature is excluded. The only permissible permanent deviation from a registry entry is changing or deleting the registry entry itself.

Per conflict location, the user has exclusively the action types defined in the conflict-case matrix. The respective action is logged via the appropriate canonical decision_source value per §4.10. No action introduces a new decision_source value.

#### **4.12.2 Style Profile Language-Pair Binding**

The style feature "Recognize my translation style" is account-bound and language-pair-specific. The scope of a style profile is exactly one (account_uuid, language_pair) pair.

  - **Language-pair enum:** AR_DE, AR_EN, EN_DE, DE_EN.
  - Style profiles are not transferred between accounts or between language pairs of the same account.
  - No cross-account transfer.
  - No cross-language-pair transfer.

#### **4.12.3 Pre-imprint State**

  - For the main user/admin in the language pair AR_DE, the canonical user style corpus (Document A v1.0) is set as a pre-imprint.
  - In all other (account_uuid, language_pair) pairs – including AR_EN, EN_DE, and DE_EN for the main user/admin – the style profile starts empty.

#### **4.12.4 Activation per Language Pair**

The style feature is only activatable in an (account_uuid, language_pair) pair once the account has produced enough confirmed translation texts in that language pair. "Confirmed" refers to translation texts created or expressly confirmed by the user themselves and confirmed reference sentences; corrected AI suggestions act per §4.13 as counter-signal and do not automatically count as positive style examples.

The concrete activation threshold is set after gold-corpus tests (calibration value per §4.14). Until the threshold is set, M3 outside of the pre-imprinted main-user/admin AR_DE configuration cannot be activated.

#### **4.12.5 Translation Modes Per Passage**

In the translation view, selectable per passage:

  - **M1:** empty / translate manually yourself.
  - **M2:** AI translation per predefined word-faithful translation logic, observing Tier 1 system rules.
  - **M3:** AI translation per personal style profile (Tier 2). M3 is available only when a style profile is active for the active (account_uuid, language_pair) pair.

#### **4.12.6 Style Feature Conflict-Case Matrix**

|  |  |  |  |  |
| :-: | :-: | :-: | :-: | :-: |
| **ID** | **Situation** | **System reaction** | **User options** | **decision_source** |
| K-S1 | Style profile suggestion ≠ glossary entry | Style profile suggestion suppressed; glossary value set; conflict indicator at the passage | a) change glossary entry · b) override individual passage manually · c) set style rule to only_contextually_permitted or deactivated | a) glossary_management · b) translation_pipeline · c) style_management |
| K-S2 | Style profile suggestion ≠ terminology registry entry | Style profile suggestion suppressed; terminology value set; conflict indicator at the passage | a) change terminology registry entry · b) override individual passage manually · c) set style rule to only_contextually_permitted or deactivated | a) glossary_management · b) translation_pipeline · c) style_management |
| K-S3 | Style profile suggestion ≠ religious formulas registry entry | Style profile suggestion suppressed; registry value set; conflict indicator at the passage | a) change religious formulas registry entry · b) override individual passage manually · c) set style rule to only_contextually_permitted or deactivated | a) glossary_management · b) translation_pipeline · c) style_management |
| K-S4 | Passage is an accepted Qurʾān/hadith passage per §4.15 / §4.16 | Passage protected; style rule does not act; no conflict dialog; no learning effect; no logging as style-rule violation | none | no decision_event on style feature side |
| K-S5 | Style profile suggestion touches technical term first-occurrence per §4.17 | First-occurrence rule enforced; style profile suggestion suppressed at first occurrence; from second occurrence of the same technical term, the style profile acts normally | a) form first occurrence correctly · b) restrict style rule contextually to "not at first occurrence" · c) override individual passage manually | a) audit_resolution (C-02) · b) style_management · c) translation_pipeline |
| K-S6 | Reference sentence contradicts later manual user rule | Manual rule takes precedence over reference sentence per §4.13; reference sentence does not act as silent substitute | a) keep or promote manual rule · b) remove reference sentence from corpus · c) mark reference sentence as only_contextually_permitted | style_management |
| K-S7 | Accepted AI suggestion is later corrected by the user | Correction overrides the passage; correction acts at the learning level exclusively as counter-signal per §4.13; correction never itself becomes a rule | a) leave correction in place (counter-signal automatic) · b) additionally create manual style rule | a) translation_pipeline · b) style_management |
| K-S8 | Single-passage deviation without rule-change request | Passage manually overridden; glossary, registries, and style rules unchanged; no learning signal beyond the normal §4.13 measure; no automatic promotion to rule | a) manual translation at this passage | translation_pipeline |
| K-S9 | A single-passage deviation is to become a permanent rule | Explicit user step; two paths | a) create registry entry (glossary / terminology / religious formulas) · b) create or promote style rule | a) glossary_management · b) style_management |

#### **4.12.7 Protective Clauses Concerning the Conflict-Case Matrix**

  - K-S4 (protected passages) does not generate a conflict dialog, learning effect, or logging as a style-rule violation.
  - K-S6 and K-S7 modify the style profile exclusively via the promotion rules per §5.6 and the learning-source asymmetry per §4.13.
  - K-S8 is never automatically a new style rule; K-S8 becomes a rule only when the user expressly chooses K-S9.
  - Registries (glossary, terminology, religious formulas) are never modified by the style feature. Registry changes are made exclusively via the registry maintenance path and are logged in all three registries via decision_source = glossary_management. Style feature logic does not perform registry changes.

#### **4.12.8 Style Feature Learning Rule**

**Learning occurs:**

  - on explicit user action (creating manual style rule, promotion, confirmed reference sentence, registry change);
  - as weak reinforcement of existing rules through accepted AI suggestions without promotion to invariant;
  - as counter-signal through corrections of accepted AI suggestions, without the correction itself becoming a rule.

**Learning does not occur:**

  - from protected passages per K-S4;
  - from single-passage deviations per K-S8 without explicit K-S9 action;
  - from ignored AI suggestions (null signal);
  - from conflicts against Tier 1 system rules, neither in the direction of the suppressed style suggestion nor as a style signal in the direction of the registry value.

Without explicit user action, there is no path to invariant.

### **4.13 Learning-Source Asymmetry of the Style Feature (CANON)**

|  |  |  |  |  |  |
| :-: | :-: | :-: | :-: | :-: | :-: |
| **Source** | **Strong rules** | **Invariants** | **Reinforce** | **Candidates** | **Non-use** |
| Confirmed reference sentences | Yes | No (only via confirmation) | Yes | Yes | – |
| Manual user rules | Yes | Yes – directly | Yes | Yes | – |
| Accepted AI suggestions | No | No | Yes (existing) | Yes (weak) | – |
| Corrected AI suggestions | No | No | No | No | Counter-signal |
| Ignored AI suggestions | No | No | No | No | Null signal |

**Protective clause:** The matrix defines the qualitative direction of effect per learning source. Concrete learning weights, evidence-density thresholds, and promotion thresholds are expressly not part of this matrix and are set exclusively as calibration values per §4.14 after gold-corpus tests.

**Signal classes:**

  - **strong:** manual user rule or confirmed reference sentence – can themselves be a rule.
  - **weak:** accepted AI suggestion – reinforces existing rules, candidate.
  - **counter-signal:** corrected AI suggestion – acts exclusively against the original suggestion direction, never itself a rule.
  - **null:** ignored AI suggestion.

Accepted AI suggestions never automatically generate an invariant or a strong rule. Corrected AI suggestions act exclusively as counter-signal. Ignored AI suggestions are null signal. A promotion beyond preference to invariant and a demotion from invariant require an explicit user action per §5.6. There is no automatic path to invariants from learning sources.

### **4.14 State Model Style Rules**

|  |  |
| :-: | :-: |
| **Status** | **Meaning** |
| active | Rule active and applied |
| in_review | Candidate – no application |
| suppressed_by_system_rule | System rule takes precedence |
| only_contextually_permitted | Not in all contexts |
| deactivated | Temporarily deactivated |
| locked_by_user | Permanently locked |

**Style profile marker:** Style-influenced passages in the editor are indicated by subtle underlining (blue tone) and hover tooltip with rule designation (PF-XX). Disabled in the display settings.

**Display setting style marker:** stored at account level.

**Style profile rollback:** Active by default for all users with the style feature unlocked. Return to earlier style_profile_version possible; already-completed pages are not changed in the process.

**Style feature calibration values:** are set after gold-corpus tests.

### **4.15 Quranic Verse Handling (canonical)**

#### **4.15.1 Carrier Structure**

After accepted Qurʾān recognition, a separate carrier structure applies:

  - **Arabic reference text and vocalization:** Arabic Qurʾān reference collection (AR reference collection). Independent local collection. Target-language-independent. At no point API-supported; no API primary path and no fallback status. Concrete source designation and update mechanism still open.
  - **German translation:** primary carrier is quranenc.com API (german_rwwad). Fallback on API failure is the local copy of the german_rwwad translation. Weekly automatic sync for updates.
  - **English translation:** primary carrier is quranenc.com API (english_rwwad). Fallback on API failure is the local copy of the chosen English translation. Weekly automatic sync, analogous to the German translation.

The canonically named APIs (quranenc.com DE and EN) and their local fallback copies concern exclusively the translation carriers, not the AR reference collection.

A deviation between OCR vocalization and the AR reference collection does not generate a free choice case. Only the upstream recognition question is verifiable: is the passage recognized as a Qurʾān passage with sufficient confidence?

#### **4.15.2 Recognition, Confidence, and API Timing**

  - The first external API call (quranenc.com) occurs only in the translation phase. During the OCR run only local matching takes place; no external call in the OCR phase.
  - When confidence of Qurʾān recognition is below the defined threshold: manual confirmation by the user is upstream; no automatic API call. Threshold still open.
  - Detected error in Quranic verses: warn icon inline, persisted until correction by the user.

#### **4.15.3 Protection of Existing Project Passages**

Qurʾān passages already stored in projects remain unchanged on changes to the Arabic Qurʾān reference collection or to the local fallback copy of the translation. No automatic re-fetch, no silent overwriting of existing project passages.

#### **4.15.4 Source Citation**

  - Order in the text: Arabic → German translation → source citation.
  - Quranic verse source citation is invoked via the context menu on the block.
  - Fallback to local Quran copy: log entry in project log.

**Source citation logic:**

1.  System recognizes Quranic verse.
2.  Did the author provide a source citation?
      
      - **Yes:** System verifies. Correct → adopt. Incorrect → inform user.
      - **No:** Passage remains empty.
3.  In both cases: User is given the option to insert canonical source citation.

#### **4.15.5 Qurʾān Passage Handling – decision_source Mapping**

|  |  |
| :-: | :-: |
| **Action** | **decision_source** |
| Manual confirmation when confidence is below threshold | translation_pipeline |
| Correction of the Sura/Āya assignment | conflict_resolution |
| Rejection as Qurʾān passage ("do not treat as Qurʾān") | conflict_resolution |
| Express user action to update an already stored Qurʾān passage following an update of the AR reference collection or local fallback copy of the translation | translation_pipeline |

Automatic acceptance with confidence above threshold generates no decision_event. No new decision_source values. The matrix is structurally analogous to the hadith action-types matrix in §4.16.

### **4.16 Hadith Handling**

#### **4.16.1 Verification Sources (two-tier)**

**Mandatory set** (fully searched on every hadith verification run):

  - P-1: sunnah.com (API)
  - P-2: Shamela (local)
  - P-3: dorar.net (= الدُّرَرُ السَّنِيَّة)

**Extended set** (automatically activated when the mandatory set yields no robust hit; can also be triggered manually by the user at any time):

  - E-1: islamweb.net – documented, factually suspended.
  - E-2: جَامِعُ السُّنَّةِ النَّبَوِيَّة – highly reliably identified as Alifta-/Harf variant; documented, factually suspended.
  - E-3: المكتبة الوقفية – documented, factually suspended; only kept as a possible manual reference source.
  - E-4: جَامِعُ الكُتُبِ التِّسْعَة – documented, factually suspended.
  - E-5: مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة – not suspended, kept in special role (see §4.16.2).

**Express exclusion:** hadithportal.com is excluded as a source for hadith verification.

**Note:** The two-tier source structure (mandatory/extended) is a deliberate sharpening from the hadith integration. المكتبة الوقفية appears in the extended set as an escalation source, not in the mandatory set.

#### **4.16.2 Special Role of E-5**

E-5 is kept as "German translation source / multilingual reference source" and not as a broad corpus replacement source.

  - No API full-text search path.
  - Technical connection via the official API and the official bulk downloads.
  - **Official Live API:** primary runtime path.
  - **Official bulk downloads:** secondary auxiliary and analysis path, not runtime source for hadith verification.
  - No offline index as normal path.
  - No frontend scraping as normal model.

**Effect on the escalation logic:** As long as E-1, E-2, E-3, and E-4 are factually suspended, when the extended set is automatically activated, in practice exclusively E-5 in the described special role is effective. The two-tier structure mandatory/extended remains structurally preserved. Evaluation of hits from the extended set follows the same consensus and comparison logic as for the mandatory set.

#### **4.16.3 Consensus Logic**

Hadith verification works with a multidimensional comparison and consensus logic across all active sources. Comparison is by:

  - Wording proximity
  - Carriage by multiple sources
  - Proximity to the source named by the author
  - Isnād/collection reference
  - Vocalization consistency
  - Authenticity signals

The linear confidence ranking (§3.5) acts as tie-breaker when the consensus logic does not yield a clear winner.

**Kutub as-Sitta:** strong weighting factor in conflicts, no absolute precedence. With equally strong hits, Kutub-as-Sitta sources are preferred. A more wording-faithful, robust hit outside the Kutub as-Sitta can break precedence; the deviation is made visible in review.

**Authenticity grade:** optionally displayable.

**Source citation format:**

  - **German:** (Sahih al-Bukhari, Nr. 1; Sahih Muslim, Nr. 1907)
  - **English:** (Sahih al-Bukhari 1; Sahih Muslim 1907)

#### **4.16.4 Hadith Verification Status**

Each hadith passage receives, after completion of the multi-source verification and after each subsequent user interaction, a state type and a derived verification class.

**Passage types:**

  - **N-1:** fully verified and automatically accepted.
  - **N-2:** verified with logging-mandatory residual finding (V-1 vocalization residual, single mandatory-source failure with robust consensus, missing Kutub-as-Sitta signal with robust consensus outside it).
  - **N-3:** verified with active user decision.
  - **N-4:** unresolved, actively "marked for later clarification" by the user.
  - **N-5:** total verification failure without user decision.
  - **N-6:** author source conflict unresolved.
  - **N-7:** no hit, no decision.
  - **N-8:** V-2 vocalization conflict unresolved.
  - **N-9:** treated as "not as hadith".
  - **N-10:** "continue without verification" expressly chosen.

**Verification classes:**

  - **H-0** (review-internally tolerable, not export-blocking): N-1, N-3, N-9.
  - **H-1** (logging-mandatory, not export-blocking, warning-capable): N-2, N-10.
  - **H-2** (export-blocking until resolution): N-4, N-5, N-6, N-7, N-8.

Resolution of H-2 exclusively via the 7 action types canonized in §4.16.5. No new decision_source values. Marking "for later clarification" is not a decision_event and does not lift H-2.

**Placement in the export preflight:** independent named group "Hadith Verification Status" within the gate-check layer per §4.7. Hadith verification status is not an audit case within the meaning of §4.6.

#### **4.16.5 Hadith-specific decision_event Mapping**

|  |  |
| :-: | :-: |
| **Action type** | **decision_source** |
| Adopt verified version instead of author wording | translation_pipeline |
| Choose full text instead of short version | translation_pipeline |
| Retain author wording despite conflict | conflict_resolution |
| Change source citation or expressly not change | conflict_resolution |
| Continue without robust external verification | conflict_resolution |
| Do not treat passage as hadith | conflict_resolution |
| Decide vocalization conflict manually | conflict_resolution |

#### **4.16.6 Data Model of Multi-source Result Objects**

Hadith results are managed in four logical levels:

  - **Level 1 – Passage anchor:** via Block-UUID, Sentence-UUID, and OCR Revision-UUID.
  - **Level 2 – Single-source reading:** per source and verification run; multiple single-source objects of the same source in the same run are permitted (hit variants).
  - **Level 3 – Aggregated overall result:** per verification run, references the single-source objects and determines reference matn and reference vocalization.
  - **Level 4 – User decision overlay:** exclusively via decision_event_uuid per §4.10 and §4.11; no own superseding logic in the result object.

**Source role (mandatory snapshot field):** values pflicht, erweitert_aktiv, erweitert_sonderrolle, erweitert_suspendiert. The value is fixed at the time of the verification run; no dynamic back-derivation against the current canon. hadithportal.com may not be carried in the source enum (canonical exclusion). E-5 carries the role value erweitert_sonderrolle.

**Derived states** (not independently persisted, deterministically derivable from Level 2/3/4):

  - entscheidungsstatus (decision status)
  - vokalisierungsklasse (vocalization class) (V-0 / V-1 / V-2)
  - hadith_stellen_typ (hadith passage type) (N-1 through N-10)
  - hadith_verifikationsklasse (hadith verification class) (H-0 / H-1 / H-2)

**Fallback rule:** in case of ambiguity, the higher class or the riskier state is applied.

**Immutability analogous to §4.9 E-10:** Single-source objects and the overall result are immutable after creation with respect to provenance and single-source references. decision_event_uuids grow exclusively through new decision_events (superseding per §4.11). A new verification round generates a new overall result with its own UUID; the old one is preserved as provenance (is_aktiv = false). No new core objects. No new decision_source values.

#### **4.16.7 Hadith Vocalization**

**Carrier principle:** Reference matn and reference vocalization are managed as separately determinable fields. In the normal case, both come from the same source. When another source delivers the vocalization better, the vocalization source can be determined and logged separately. Unlike Qurʾān (§4.15), with hadith there is deliberately no sole text carrier. With relevant vocalization conflicts, the user is involved; the decision is logged as a decision_event under conflict_resolution.

**Vocalization escalation criterion:** Deviations between vocalization versions are assigned to one of three relevance classes.

  - **V-0 (automatically tolerable):** orthographic-technical variants without sound or meaning change (Tatweel, Unicode normalization, pure rendering variants, non-overlapping partial vocalization in special positions). Automatic adoption. No logging obligation at the passage level.
  - **V-1 (logging-mandatory, no escalation):** deviations without meaning change that must remain visible for traceability (vocalization-density differences, Shadda without word-identity change, Hamzat al-Waṣl/Qaṭʿ without meaning change, name vocalization variants with classically permissible double form). Automatic choice of reference vocalization from the best source. Documentation in passage logging. No active user intervention. No decision_event on inaction.
  - **V-2 (escalation-mandatory):** deviations with meaning, iʿrāb, sarf, isnād-identification, or matn-lexeme change (case/mood deviation, active/passive or stem change, Shadda with word-identity change, Hamza with meaning change, name/nisba vocalization with identification consequence, matn-lexeme deviation via vocalization). No automatic adoption. Active user resolution per the canonized action types. decision_source conflict_resolution.

**Aggregation rule:** With multiple deviations in one passage, the highest occurring class applies for the passage (V-0 < V-1 < V-2). **Fallback rule:** with ambiguity of the type assignment, the higher class is applied; no silent down-classification.

The field vokalisierungs_konflikt remains strictly binary (no / yes). Class differentiation runs exclusively via the derived vokalisierungsklasse. If the type assignment is unclear in an individual case, vokalisierungs_konflikt remains yes; the ambiguity is documented only in logging or in the conflict reasoning.

#### **4.16.8 Language-neutral Reference and Comparison Field**

Website translations from hadith verification sources are managed in the single-source result object as part of the field website_uebersetzung (see §5.1.1). When a source delivers an English-language translation for the matched hadith, this is entered with lang = "en" in website_uebersetzung.

  - These entries arise independently of the project's target language and independently of whether English is an output language in the relevant project.
  - The entries act exclusively as provenance and comparison material.
  - They have no influence on matn consensus, reference matn, reference vocalization, or on the primary translation output.
  - They may be made visible in the hadith review panel as a comparison language, including in projects with another target language; the display is not mandatory and generates no own decision_event.

**English hadith output:** is its own primary production path from the Arabic matn, parallel and structurally equivalent to the German hadith output. It is not derived from the German primary translation. A cascade AR→DE→EN for the hadith matn translation is excluded (no-cascade rule).

The English hadith output follows for footnotes the same structural footnote logic and the same template and category set as the German output; concrete English marker abbreviations are not fixed here. Source citation format and transliteration remain language-specifically governed (§4.16.3 for source citation format DE/EN; §2.2 for transliteration). Relationship to the style feature and to Interface 3 remains expressly open.

### **4.17 Special Treatments**

**Vocalization handling:** Adopt as in original. Internally always vocalized. Optional display: AI-vocalized in color A, manually corrected in color B. Three uncertainty levels:

  - High (> 85%): silent.
  - Medium (50–85%): tooltip.
  - Low (< 50%): full panel.

**Technical terms:**

  - First occurrence: German technical translation + (Arabic vocalized) + footnote.
  - From second occurrence: only transliteration.
  - When no hit: AI-generated footnote with [Source: AI] marker.

**Arabic metaphors:** full recognition. Treatment: literal + footnote [Tr.].

**Sajʿ:** footnote "In the Arabic original formulated as Sajʿ." Kashida activated by default.

**Religious formulas:** as calligraphy/Unicode: ﷺ, ﷻ. Optionality: calligraphy / German translation / Arabic spelled out.

**Morphology panel:** When clicking on an Arabic word, the following are displayed: part of speech, root, wazn, conjugation table, nominalizations, iʿrāb, translation suggestions. Display location: side panel.

**Word form frequency analysis:** When correcting a word, all forms with frequency are displayed. Per form: own translation field and decision. Display location: modal dialog.

### **4.18 Error Classification System**

#### **4.18.1 Track 1 – Error Resolution**

  - **Class A (user error/data error):** inform user, document.
  - **Class B (external error):** retry, fallback. (General logic see §4.18.2.)
  - **Class C (system-fixable):** full process up to code update.

#### **4.18.2 General Logic Class B Notification (L-24)**

  - Class B errors are always logged.
  - Active user notification does not occur per individual case but is aggregated via the dashboard status indicator on reaching a frequency threshold per Track 2.
  - Already-canonized special cases with their own rule remain unaffected: §3.6 translation AI 30-min rule with in-app and email; §4.15 Qurʾān fallback with log entry without user interrupt; guard-near blockades per §4.7.
  - Concrete frequency threshold values are dependent on live measurement and remain workbench until real measurement; the structural mechanism is canonical.

#### **4.18.3 Track 2 – Process Optimization**

**Trigger:** Frequency pattern → periodic evaluation → optimization proposal → confirmation → implementation.

**Admin Optimization Input Channel:**

  - In addition to automatic frequency-pattern detection, an internal optimization input window is available to the main user/admin. Through this channel, the main user/admin can manually feed in observations, process problems, error notices, UI/flow remarks, optimization proposals, or desired improvements. Examples: position of a morphology window, arrangement of a button, desired document style template in export, recurring usability problems, recognized process errors, or technical anomalies.
  - **Visibility and authorization:** The input channel is visible exclusively to the main user/admin. Normal users (Tiers 1 and 2 per §2.3) have no access.
  - **Processing:** Admin inputs are fed into the same Track 2 flow as automatically detected frequency patterns. Both input sources (`system` and `admin`) traverse identically the steps: capture → classify → link with error/process data → prepare as optimization proposal → proposal state. There is no admin special path and no admin bypass option.
  - **Effect boundary:** An admin input is input into the optimization process, not a decision. It triggers no automatic architecture, canon, or code change. The further path to analysis, CR, ticket, sprint, and implementation runs exclusively via the status-based Admin Optimization Panel per §4.18.

**Admin Optimization Panel:**

The Admin Optimization Panel manages all optimization entries from the sources `system` and `admin` in a status-based interface. The display is in tabs. An entry is always in exactly one main tab.

Tabs:

1\. Inbox / Proposals: new automatically generated or manually entered optimization entries that have not yet been classified.

2\. Continue observing: entries that are not yet decision-ready and continue to be collected, condensed, or reconciled with future error/process data.

3\. Released for analysis: entries that have been released for technical or specialist analysis. After completion of the analysis, they receive an analysis finding.

4\. Prepare as CR: entries whose analysis has shown that a canonical, architectural, or process change is likely required and is to be prepared as a Change Request.

5\. Tickets: entries that are technically decided and can be earmarked as a developer task or transferred to later implementation planning.

6\. Archived / discarded: entries that are ignored, completed, discarded, or deliberately not pursued further.

Each entry contains at minimum: title, source (`system` / `admin`), category, affected area, description, linked error/process data, status, priority, last edit timestamp, and next permissible action.

**Status-dependent actions in the Admin Optimization Panel:**

The available actions depend on the status of the entry. Not all actions are offered in every status.

Status `vorschlag` (proposal) / Tab "Inbox / Proposals":

Permissible actions: ignore, continue observing, release for analysis.

Not permissible: prepare directly as CR, earmark directly as ticket.

Status `weiter_beobachten` (continue observing) / Tab "Continue observing":

Permissible actions: release for analysis, continue observing further, ignore.

Not permissible: prepare directly as CR, earmark directly as ticket.

Status `analyse_freigegeben` (released for analysis) / Tab "Released for analysis":

Permissible actions: enter analysis finding, return to continue observing, ignore.

Not permissible: re-release for analysis, direct ticket without analysis finding.

Status `analyse_abgeschlossen` (analysis completed):

Permissible actions: prepare as CR, continue observing, ignore.

Not permissible: direct ticket as long as no CR decision or equivalent technical decision basis exists.

Status `cr_vorbereitung` (CR preparation) / Tab "Prepare as CR":

Permissible actions: create CR draft, discard CR, return to analysis, earmark as ticket after confirmed CR basis.

Not permissible: direct implementation.

Status `ticket_vorgemerkt` (ticket earmarked) / Tab "Tickets":

Permissible actions: prioritize ticket, assign ticket to a later planning, defer ticket, close ticket.

Not permissible: automatic sprint inclusion or automatic implementation without separate release.

Basic rule: Analysis = understanding the problem. CR = official description of a desired change. Ticket = prepared developer task. Implementation only after separate sprint/implementation release.

**Categories for optimization entries:**

Optimization entries are assigned to at least one category:

1\. Error source: recurring error or technical defect.

2\. Process problem: flow is unclear, unnecessarily slow, error-prone, or generates unnecessary user work.

3\. UI/UX remark: arrangement, visibility, usability, or display of an element.

4\. Export/formatting problem: document style templates, layout, DOCX/PDF output, footnotes, headings, or registers.

5\. OCR/recognition problem: OCR quality, layout recognition, block assignment, columns, footnotes, harakāt, Qurʾān/hadith recognition.

6\. Translation/style problem: translation logic, style profile, glossary, terminology, religious formulas, or technical terms.

7\. Interface/source problem: external API, scraping path, local data source, Shamela, Qurʾān or hadith interface.

8\. General improvement proposal: other optimization without already determined technical cause.

A category is a working classification and not a decision. The category may be adjusted during the analysis process.

**Protective clause Admin Optimization Process:**

No optimization entry – neither from automatic pattern detection nor from admin input – directly leads to an architecture change, canon change, code change, sprint inclusion, or implementation. Each entry remains a proposal or work item until the main user/admin expressly confirms the next permissible process step. Confirmation of a process step does not replace coding release.

### **4.19 Reference and Entity System**

**Categories:** Scholars and persons / Historical places / Units of measurement / Arabic books / Dynasties and epochs.

**Sources for short bios:** سير أعلام النبلاء, تهذيب التهذيب, وفيات الأعيان, الأعلام للزركلي.

**Sources for Arabic books:** كشف الظنون, الأعلام, معجم المؤلفين, فهرست ابن النديم.

## **5. ESTABLISHED DATA MODEL**

### **5.1 Core Objects**

Page-UUID, Block-UUID, Sentence-UUID, Revision-UUID, Decision-Event-UUID, Concept-ID, source attributes.

#### **5.1.1 Hadith Single-source Result Object (per §4.16 data model)**

**Mandatory fields:**

  - einzelquelle_uuid
  - gesamtergebnis_uuid
  - quelle_id
  - quellen_rolle (mandatory snapshot field)
  - treffer_status
  - technischer_status
  - zugriffszeitpunkt

**Mandatory when** **treffer_status = treffer****:**

  - matn_arabisch

**Optional:**

  - matn_arabisch_raw
  - matn_vokalisiert
  - isnad
  - sammlung
  - werk_nummer
  - direktlink
  - hukm
  - hukm_quelle
  - website_uebersetzung (list of {lang, text}, multilingual; entries are managed per delivered language of the respective source, independently of the project's target language)

**Derived:**

  - textnaehe
  - autorquelle_match
  - fehlerklasse_418 (per §4.18)

**Property:** immutable after creation.

**HTML stripping (Model R):** For sources whose matn response contains markup, the delivered raw body is persisted in matn_arabisch_raw; matn_arabisch contains the deterministically derived text version. Text-proximity, comparison, and consensus logic operate on matn_arabisch. For sources without markup, matn_arabisch_raw is omitted.

**Source role (****quellen_rolle****):** mandatory snapshot field. Values pflicht, erweitert_aktiv, erweitert_sonderrolle, erweitert_suspendiert. The value is fixed at the time of the verification run. No dynamic back-derivation against the current canon. hadithportal.com may not be carried in the source enum (canonical exclusion).

**Enums:**

  - treffer_status: treffer / kein_treffer / technischer_fehler / quelle_suspendiert / quelle_nicht_durchsucht.
  - technischer_status: ok / timeout / retry_erfolgreich / dom_bruch / parse_fehler / quelle_suspendiert / quelle_nicht_durchsucht / http_4xx / http_5xx.

#### **5.1.2 Hadith Overall Result Object (per §4.16 data model)**

**Mandatory fields:**

  - gesamtergebnis_uuid
  - block_uuid
  - ocr_revision_uuid
  - lauf_zeitpunkt
  - is_aktiv
  - autorwortlaut
  - einzelquellen_uuids
  - eskalation_ausgefuehrt
  - eskalation_quellen_aktiv
  - ausgefallene_quellen
  - konsens_status
  - kutub_as_sitta_signal
  - kutub_as_sitta_abweichung_aktiv
  - vokalisierungs_konflikt
  - decision_event_uuids

**Mandatory once sentence segmentation is available for the passage:**

  - satz_uuid

**Mandatory with robust consensus:**

  - referenz_matn
  - referenz_matn_quelle_uuids

**Optional:**

  - autor_genannte_quelle
  - ocr_konfidenz
  - referenz_vokalisierung
  - referenz_vokalisierung_quelle_uuid

**Derived, not persisted** (deterministically from mandatory and optional fields, referenced single-source readings, and active decision_events):

  - entscheidungsstatus (values ohne_aktive_entscheidung / translation_pipeline / conflict_resolution / gemischt; derived from non-superseded decision_events per §4.11)
  - vokalisierungsklasse
  - hadith_stellen_typ
  - hadith_verifikationsklasse

**Enums:**

  - konsens_status: konsens / mehrheit / tie_breaker / kein_konsens / kein_treffer.
  - vokalisierungs_konflikt: nein / ja (strictly binary).

**Class differentiation** (V-0/V-1/V-2): runs exclusively via the derived vokalisierungsklasse. If the type assignment is unclear in an individual case, vokalisierungs_konflikt remains yes; the ambiguity is documented only in logging or in the conflict reasoning.

**Property:** Per passage and OCR revision exactly one active overall result (is_aktiv = true). Immutable after creation with respect to einzelquellen_uuids, autorwortlaut, ocr_revision_uuid, lauf_zeitpunkt.

### **5.2 Style Profile Objects (from Document B v1.2)**

**stil_regel:** stil_regel_uuid, account_uuid, sprachpaar, dimension, phänomenfeld (PF-01–PF-12), arabisches_muster, bevorzugte_wiedergabe, konfidenz (Float 0.0–1.0), belege_uuids[], status (enum), regeltyp (enum), invariant_quelle (enum), erstellt_aus (enum), erstellt_at, zuletzt_aktualisiert_at.

**stilbeleg:** beleg_uuid, account_uuid, sprachpaar, arabisches_muster, arabischer_kontext, deutsche_wiedergabe, phänomenfeld, belegtyp, regeltyp, konfidenz, referenz_paar_uuid, nutzer_bestätigt, erstellt_at.

**stilprofil_version:** stilprofil_version_uuid, account_uuid, sprachpaar, version_nummer, erstellt_at, auslöser (enum), delta (JSON), is_aktiv.

**referenz_paar:** referenz_paar_uuid, account_uuid, sprachpaar, arabischer_text, deutscher_text, bestätigt_at.

**sprachpaar enum:** AR_DE, AR_EN, EN_DE, DE_EN. Mandatory field in all four style profile objects.

**Account binding:** All style profile objects are bound to account_uuid and sprachpaar. Scope of exactly one (account_uuid, sprachpaar) pair. No cross-account access. No cross-language-pair access.

### **5.3 Phenomenon Field Enum PF-01 through PF-12**

|  |  |
| :-: | :-: |
| **No.** | **Phenomenon field** |
| PF-01 | Particle handling |
| PF-02 | Sentence linking and repetition |
| PF-03 | Idāfa handling |
| PF-04 | Masdar/verb relationship |
| PF-05 | Technical equations |
| PF-06 | Handling of Qurʾān and Ḥadīṯ quotations |
| PF-07 | Isnād/ḥadīṯ-critical technical language |
| PF-08 | Use of brackets |
| PF-09 | Religiously polemical terms |
| PF-10 | Legal-contractual metaphor |
| PF-11 | Register height |
| PF-12 | Errors that must not happen again (negative list) |

### **5.4 EXPORT_EVENT Schema**

ocr_export_uuid, project_uuid, export_mode, gate_mode, export_config, ocr_revision_snapshot[], active_decision_event_uuids[], export_warnings[], artefact_ref, created_at, active_stilprofil_version_uuid (nullable). Immutable after creation.

### **5.5 Rule Type Enum**

invariant / präferenz / tendenz / kandidat.

### **5.6 Promotion Rules**

|  |  |  |
| :-: | :-: | :-: |
| **From** | **To** | **Condition** |
| kandidat | tendenz | Minimum evidence density or user confirmation |
| tendenz | präferenz | Higher evidence density or user confirmation |
| präferenz | invariant | Only by explicit user action [CANON] |
| invariant | präferenz | Only by explicit user action [CANON] |
| any type | vom_nutzer_gesperrt | Explicit user action or repeated correction signal |

## **6. ESTABLISHED DECISIONS**

All canonically confirmed individual decisions are incorporated in the respective sections of this document.

## **7. ESTABLISHED QUALITY REQUIREMENTS**

### **7.1 DOCX Quality Requirements**

  - DOCX opens in Word without repair.
  - Per-paragraph RTL (OCR Export DOCX) / Per-run RTL (Translation DOCX).
  - Fonts provided server-side.

**Critical fonts** (export blocked on missing font, no silent fallback):

|  |  |  |
| :-: | :-: | :-: |
| **Font** | **Used in** | **Criticality** |
| KFGQPC Uthmanic Script HAFS | Quran_AR | Critical – no alternative |
| Traditional Naskh | Hadith_AR, Zitat_AR, Titel_AR, Titel_AR_Untertitel | Critical |
| Noto Sans Arabic | UeberschriftAR_1–6, Begriff_AR, FussN_AR | Critical |
| Calibri | Body_DE, Titel_DE, Heading 1–6, FN_Uebersetzer, FN_Herausgeber, FN_Verlag | Critical |

**Placement in the export process:** canonically confirmed as guard-near before the preflight dialog. If one of the four critical fonts is missing, the preflight dialog is not opened. Resolution only by technical restoration of the font. No P-slot is occupied.

### **7.2 Document Style Templates Baseline v1.1**

Fully canonical. All values adopted unchanged; core table see Document Style Templates Baseline v1.1.

### **7.3 OCR Quality Standards**

OCR display maximally simple: Noto Sans Arabic, 14 pt. Headings only bold with greater spacing. Quranic verses and hadiths only indented with edge rule. Footnotes 11 pt with separator line.

### **7.4 Security and Data Protection**

  - SSL and at-rest encryption.
  - Password hashing (bcrypt/Argon2), 2FA optional.
  - No timeout during an active background process, otherwise 2 hours.
  - Trash: 10 days.

## **VERSION STATE**

**Status:** Living master document – cleaned full-text version. Sole canonical primary source.

**Canonized contents (hadith verification semantics, preflight placement, data model, and English strand):**

  - Vocalization escalation criterion V-0/V-1/V-2 with aggregation and fallback rules; field vokalisierungs_konflikt strictly binary (§4.16.7).
  - Hadith verification status N-1 through N-10 with classes H-0/H-1/H-2 (§4.16.4).
  - Gate placement of hadith verification status as independent named group within the gate-check layer without new layer and without P/W slot occupation (§4.7.5).
  - Data model of multi-source result objects in four logical levels with quellen_rolle as mandatory snapshot and derived states (§4.16.6 / §5.1.1 / §5.1.2).
  - Partial canonization of the English hadith strand K-4 R-1/R-2: English-language website translations from hadith verification sources as language-neutral reference and comparison field (§4.16.8 / §5.1.1).

**Canonized contents (consolidation of Interface 5):**

  - Mandatory set P-1/P-2/P-3 unchanged.
  - E-1/E-2/E-3/E-4 documented per Option B, factually suspended; E-2 highly reliably identified as Alifta-/Harf variant; E-3 only as a possible manual reference source.
  - E-5 per Option B not suspended, in special role "German translation source / multilingual reference source".
  - hadithportal.com expressly excluded.
  - Escalation logic in practice only E-5 effective on automatic activation (§4.16).

**Canonized contents (hadith integration):**

  - Two-tier source structure mandatory/extended (§4.16.1).
  - Consensus logic with linear ranking as tie-breaker (§3.5 / §4.16.3).
  - Kutub as-Sitta as strong weighting factor (§4.16.3).
  - decision_event mapping 7 action types (§4.16.5).
  - Vocalization principle separate fields without sole text carrier (§4.16.7).

**Canonized contents (translation pipeline behavior, Qurʾān recognition rules, Shamela modes, OCR quality principle):**

  - Check model correction right (§3.6).
  - No silent role swap (§3.6).
  - Audit findings do not stop translation flow (§3.6).
  - Qurʾān vocalization rule (§4.15).
  - Qurʾān API call timing (§4.15).
  - Qurʾān confidence protection (§4.15).
  - Qurʾān project-passage protection (§4.15).
  - Shamela usage modes and Lisān/Tāj as query units (§3.5).
  - OCR quality principle no artificial winner (§3.4).

**Open work front:**

  - Interface working drafts 1–6 in progress, not yet canon.
  - Maximum mode not canonized.
  - Word panel work strand running separately, not yet canon.
  - Open items expressly kept open. No silent re-baselining.
