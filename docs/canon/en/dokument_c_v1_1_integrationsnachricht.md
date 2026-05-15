<!-- Source: Google Drive doc 1MZ5M8hIBRIzmIwcOBHisg_6YFSQRq1oQRGAr2hBVsZY (Dokument C v1.1 — Integrationsnachricht Stilfeature) -->
<!-- Pulled: 2026-05-01. Place at /docs/canon/dokument_c_v1_1_integrationsnachricht.md -->

# WARAQ — DOKUMENT C v1.1

## Integration notice: "Recognize my translation style"

Successor version to Dokument C v1.0

No code. No coding release. No silent architecture change. No silent re-baselining. No new feature broadening. This document is the integration notice. It contains no implementation and no code. It is the basis on which the actual change requests and implementation readiness are then carried forward.

Classification of this version: Dokument C v1.1 is the successor version to Dokument C v1.0. Dokument C v1.1 is no new baseline shift, no implementation release, and introduces no new architecture. Dokument A and Dokument B v1.2 remain unchanged and frozen. The OCR-export final version v1.3 remains separately frozen and separated from the style feature.

## PRECEDENCE LOGIC (UNCHANGEABLE — NOT SHIFTED ANYWHERE IN THIS DOCUMENT)

1. Already-released general system rules (Dokument 1 and Baselines v1.0)
2. Canonical user style (Dokument A + Dokument B v1.2)
3. Individual reference sentences (reference corpus from Dokument A — as structured bilingual Stilbelege)

## 1. CLASSIFICATION OF THE FEATURE WITHIN THE EXISTING WARAQ CANON

### 1.1 What now newly applies

With the freezing of Dokument A and Dokument B v1.2 the following holds:

| Document | Status | Rank in precedence logic |
|---|---|---|
| Waraq Core Architecture Baseline v1.0 | Frozen, canonical | Rank 1 (system rules) |
| Waraq Implementation Translation Baseline v1.0 | Frozen, canonical | Rank 1 (system rules) |
| Waraq Engineering Execution Baseline v1.0 | Frozen, canonical | Rank 1 (system rules) |
| Waraq Delivery Backlog Baseline v1.0 | Frozen, canonical | Rank 1 (system rules) |
| OCR-Export-Endfassung v1.3 | Frozen, canonical, separated from style feature | Not part of this feature's precedence logic |
| Dokument A — Kanonischer Nutzerstil-Korpus v1.0 | Frozen, canonical | Rank 2 (user style) |
| Dokument B v1.2 — Feature specification "Recognize my translation style" | Frozen, canonical | Rank 2 (user style) |
| Individual reference sentences (reference corpus Dokument A) | Valid as Stilbelege | Rank 3 |

### 1.2 Classification within the existing product workflow

The feature "Recognize my translation style" is to be assigned to the existing product workflow:

- Phase 5 — Translation: the Stilprofil acts as an additional layer on the AI translation suggestion. Option A (AI standard) remains the starting point.
- Stilprofil Option B (per Dokument B v1.2): the feature is the structured operationalization of this concept. It does not replace the concept but defines how the Stilprofil is built up, learned, versioned, and applied.
- "Recognize my style" algorithm: Dokument B v1.2 is authoritative for style questions within rank 2. General system rules from rank 1 are not affected and not overridden by this. No general precedence rule between Dokument B v1.2 and a higher-ranking source is derived from it.

### 1.3 What the feature is not

- No replacement for Option A (AI standard)
- No intervention in the OCR phase or the OCR-export track
- No redefinition of glossary, transliteration, terminology index, religious formulas, or Qurʾān-verse / hadith handling
- No new baseline for the overall system
- No standalone translation module

## 2. CONFIRMATION: NO OVERWRITING OF EXISTING SYSTEM RULES

### 2.1 Express confirmation [KANON]

Dokument A and Dokument B v1.2 do not overwrite any existing system rules. In detail:

| System rule | Status after freezing of Dokument A + B v1.2 |
|---|---|
| Transliteration EI2 (Q/J) | Unchanged. Stilprofil entries that contradict are suppressed. |
| Glossary (precedence, never automatically overwritable) | Unchanged. Glossary always has precedence over Stilprofil. |
| Terminology index | Unchanged. Precedence over Stilprofil. |
| Religious-formulas index | Unchanged. Precedence over Stilprofil. |
| Qurʾān reference handling per §4.15 (Arabic Qurʾān reference stock for Arabic reference text and vocalization; quranenc.com or local fallback copy for target-language translations) | Unchanged. External source has precedence. Stilprofil does not apply to Qurʾān-verse texts. |
| Hadith handling (verification-source hierarchy) | Unchanged. Verification logic has precedence. |
| Specialist-term handling (first / subsequent occurrence) | Unchanged. |
| OCR-export track (final version v1.3) | Unchanged. Stilprofil does not apply to OCR-export DOCX. |
| Hard invariants H-1 to H-7 | Unchanged. |
| Governable Project Rules G-1 to G-4 | Unchanged. |
| Delivery Backlog Baseline v1.0 | Style-feature backlog layer (CR-3, §7) anchored; implementation sprint tickets / coding release open. |

### 2.2 Manual style rules are also subordinate [KANON]

Manually entered user style rules (Dokument B v1.2 §3.1) are also fully subject to the precedence logic. They cannot override any system rule.

## 3. NECESSARY FOLLOW-ON WORK

The freezing of Dokument A and Dokument B v1.2 produces a series of follow-on tasks that have not yet been carried out. These follow-on tasks are listed here in structured form — they are not yet tickets and not yet released implementation CRs. They are the starting point for the next work phase.

### 3.1 Formal integration analysis

The following questions must be formally answered before the implementation readiness of the feature:

| Question | Status |
|---|---|
| Which existing baselines must be adjusted to take in the feature? | Open — analysis required |
| Which existing tables / data-model objects must be extended? | Open — analysis required |
| How does the feature behave with respect to the existing translation-job model (recovery, provenance)? | Open — analysis required |
| How is the Stilprofil represented in the provenance model / EXPORT_EVENT? | Open — analysis required |
| How does the Stilprofil behave with respect to the existing revision model? | Open — analysis required |
| How are Stilprofil versions taken into account in the work-wide consistency check (K-01–K-07)? | Open — analysis required |
| How does the feature behave with respect to the translation audit (A-01–D-03)? | Open — analysis required |

### 3.2 Necessary CRs and document changes

The following documents and baselines are touched by the feature. The schema and layer anchors for CR-1 / CR-2 / CR-3 are anchored in the cleaned baselines; the outstanding implementation CRs / sprint tickets / coding release remain open:

| Affected document / baseline | Type of touch | CR status |
|---|---|---|
| Waraq Core Architecture Baseline v1.0 | Extension: Stilprofil objects, learning logic, versioning | Schema anchor anchored (CR-1, §B.6 / §B.7); implementation CRs open |
| Waraq Engineering Execution Baseline v1.0 | Extension: execution rules for Stilprofil application, job model | Layer anchor anchored (CR-2, §11); implementation CRs open |
| Waraq Delivery Backlog Baseline v1.0 | Style-feature backlog layer | Layer anchor anchored (CR-3, §7); implementation sprint tickets / coding release open |
| Sprint planning | The feature needs its own sprint slot | Not yet planned — no instruction |
| Waraq Implementation Translation Baseline v1.0 | Style-feature violations in audit structure (A-01–D-03) | Layer anchor anchored (CR-2, §4.6a); implementation CRs open |

### 3.3 Affected core objects, tables, and rules

On the basis of Dokument B v1.2 the following new core objects are identified that do not yet exist in the Architecture Baseline:

| New object | Origin | State |
|---|---|---|
| stil_regel (with all fields from Dok. B v1.2 §5.2) | Dokument B v1.2 | Identified, not yet in Baseline |
| stilbeleg (bilingual structured Stilbeleg, Dok. B v1.2 §4.2) | Dokument B v1.2 | Identified, not yet in Baseline |
| stilprofil_version (versioning model, Dok. B v1.2 §9.2) | Dokument B v1.2 | Identified, not yet in Baseline |
| referenz_paar (confirmed AR/DE pair as training source) | Dokument B v1.2 | Identified, not yet in Baseline |
| Phenomenon-field enum PF-01 to PF-12 | Dokument B v1.2 §4.3 | Identified, not yet in Baseline |
| State-model enum for stil_regel.status | Dokument B v1.2 §8.2 | Identified, not yet in Baseline |
| Regeltyp enum (invariant / präferenz / tendenz / kandidat) | Dokument B v1.2 §6 | Identified, not yet in Baseline |

Existing objects that will presumably need to be extended:

| Existing object | Type of extension | State |
|---|---|---|
| account | Linkage with active Stilprofil | Analysis pending |
| decision_event | Check whether Stilprofil decisions are modeled as decision events | Analysis pending |
| Translation-job / recovery model | Integration of the Stilprofil version into the job context | Analysis pending |
| Provenance model / EXPORT_EVENT | Whether and how the applied Stilprofil version is represented in the export provenance | Analysis pending |

### 3.4 Audit and quality logic

The following audit and quality logic is defined by Dokument B v1.2 and must, at implementation readiness, be formally integrated into the existing audit structure (A-01–D-03):

| Audit aspect | Origin | State |
|---|---|---|
| Logging of every Stilprofil application (version, entries, time) | Dok. B v1.2 §11.4 | Defined, not yet in Audit Baseline |
| Logging of every conflict with system rules (incl. state transition) | Dok. B v1.2 §8.4 | Defined, not yet in Audit Baseline |
| Logging of every Stilprofil version change (delta) | Dok. B v1.2 §9.2 | Defined, not yet in Audit Baseline |
| No covert style application — every application is identifiable | Dok. B v1.2 §11.2 | Defined, not yet in Audit Baseline |
| Phenomenon-field coverage display (for user) | Dok. B v1.2 §10.4 | Defined — config, not yet specified |

## 4. CANONICAL vs. CONFIGURABLE vs. CALIBRATABLE — OVERVIEW

### 4.1 What is canonical (unchangeable, no discretion)

- account binding absolute (no sharing function in this feature)
- only confirmed bilingual material as learning source
- explicit user activation and user confirmation on every Stilbeleg
- learning-source asymmetry (accepted AI suggestions may not produce invariants or strong rules)
- invariant arises only through explicit user action — never through statistics
- no covert style application
- system rule always has precedence — also over manual style rules
- completed pages are never altered by later Stilprofil changes
- full logging and auditability
- Stilprofil does not apply to OCR-export track
- Stilprofil rollback function is active by default (cf. Dokument B v1.2 §9.4)

### 4.2 What is product-configurable

- subscription enablement of the feature (yes/no)
- which account classes get access
- phenomenon-field coverage display (presentation form)
- UI design of the rollback control (cf. Dokument B v1.2 §9.4; the function itself is active by default)

### 4.3 What is calibratable (not yet fixed)

- minimum number of reference sentences for activation
- confidence thresholds: candidate → tendency → preference
- confidence threshold for automatic application (preference)
- minimum evidence density per phenomenon field (PF-01 to PF-12)

All calibration points are to be fixed after gold-corpus tests. They are not open architecture decisions but open measurement values.

## 5. CONFLICTS WITH EXISTING RULES — EXCLUSION LIST

The following conflicts are already structurally excluded by the precedence logic and Dokument B v1.2. They must neither arise during implementation nor be silently tolerated:

| Possible conflict | Exclusion mechanism |
|---|---|
| Stilprofil overwrites glossary entry | System-rule precedence; status `unterdrückt_durch_systemregel` |
| Stilprofil overwrites transliteration rule | System-rule precedence; spelling adapted |
| Stilprofil overwrites terminology index | System-rule precedence; status `unterdrückt_durch_systemregel` |
| Stilprofil overwrites religious formula | System-rule precedence; status `unterdrückt_durch_systemregel` |
| Stilprofil applies itself to Qurʾān references per §4.15 | Structurally excluded; Stilprofil does not apply to Qurʾān-verse context |
| Stilprofil applies itself to hadith texts | Structurally excluded; verification logic has precedence |
| Stilprofil acts on OCR-export DOCX | Structurally excluded; OCR export is source text |
| Accepted AI suggestions produce invariant | Structurally excluded by learning-source asymmetry |
| Statistics alone produce invariant | Structurally excluded; invariant only through explicit user action |
| Manual style rule overrides system rule | Structurally excluded; system rule always has precedence |
| Stilprofil of one account acts on another account | Structurally excluded; account binding absolute |
| Unconfirmed material flows into Stilprofil | Structurally excluded; only confirmed material |
| Completed pages are altered retroactively | Structurally excluded; unchangeability |
| Silent style application without identification | Structurally excluded; transparency obligation |

## 6. ACCOUNT BINDING AND NON-GLOBALITY

### 6.1 Principle [KANON]

The Stilprofil is absolutely account-bound. It is at no point a global standard and does not apply to other accounts.

### 6.2 Requirements for account binding

| Aspect | Requirement |
|---|---|
| Data storage | All Stilprofil objects (`stil_regel`, `stilbeleg`, `stilprofil_version`, `referenz_paar`) must be bound to an `account_uuid` |
| Queries | Every query on Stilprofil objects must carry `account_uuid` as a mandatory filter |
| Application | Stilprofil application to a translation suggestion uses exclusively the Stilprofil of the currently authenticated account |
| No cross-account access | No mechanism may make Stilprofil data of one account accessible to another account |
| No global aggregation | The system must not derive or apply cross-account style patterns |
| Sharing function | Not part of this feature. If desired later: separate CR required |

## 7. JOINT TREATMENT OF DOKUMENT A AND DOKUMENT B v1.2 AS BASIS FOR IMPLEMENTATION READINESS

### 7.1 Relationship of the two documents to each other

| Document | Role |
|---|---|
| Dokument A | Substantive style basis: reference corpus, hard style invariants, phenomenon fields, error negative list. Not a standalone implementation instruction. |
| Dokument B v1.2 | Structured feature specification: data-model objects, learning logic, conflict logic, state model, versioning, audit logic. Not a standalone implementation instruction. |
| Dokument A + B v1.2 jointly | Together they form the substantive and structural basis on which implementation readiness must be built up. Neither alone is complete. |

### 7.2 What is still missing for full implementation readiness

| Missing step | Precondition |
|---|---|
| Formal integration analysis (§3.1) | Must be completed before the first implementation CR |
| Implementation CRs for the baselines named in §3.2 | Only after integration analysis and explicit instruction |
| Ticket definition in the Delivery Backlog | Only after implementation-CR release |
| Sprint planning | Only after ticket definition and explicit instruction |
| Calibration of the open thresholds (§4.3) | After gold-corpus tests — not mandatorily to be fixed before first implementation |
| Coding release | Only after completed integration analysis, released implementation CRs, and ticket definition |

### 7.3 Order of follow-on steps (orienting; not a sprint plan)

The following order results from the existing CR and implementation process of the Waraq canon. It is orienting, not a binding sprint plan and not yet an instruction:

1. Formal integration analysis (§3.1 of this document)
2. Implementation CR opening for the baselines named in §3.2
3. CR cycle: analysis → decisions → CRs → tickets → sprint → release
4. Ticket definition and intake into the Delivery Backlog
5. Sprint-slot planning (only on explicit instruction)
6. Coding release (only on explicit instruction)

## 8. CURRENT ACTION STATUS

What is now frozen:

| Document | Status |
|---|---|
| Dokument A — Kanonischer Nutzerstil-Korpus v1.0 | Frozen |
| Dokument B v1.2 — Feature specification "Recognize my translation style" | Frozen |
| OCR-Export-Endfassung v1.3 | Frozen, separated from style feature |
| Dokument C v1.1 — Integration notice | Frozen as integration frame (§3 follow-on work open) |

What is now open:

- Formal integration analysis (no instruction issued)
- Implementation CRs for the baselines named in §3.2 (not opened)
- Ticket definition (not created)
- Sprint planning (no instruction)
- Calibration values (after gold-corpus tests)
- Coding release (not issued)

What is now not happening:

- No code
- No coding release
- No implementation
- No silent re-baselining
- No new feature broadening
- No new architecture without CR

Dokument C v1.1 — Integration notice "Recognize my translation style" — successor version to Dokument C v1.0. Dokument A and Dokument B v1.2 are frozen and count as the canonical basis for all further steps. OCR-Export-Endfassung v1.3 remains separately frozen and separated from the style feature. Next step only on explicit user instruction.