<!-- Source: Google Drive doc 17efXPBQfgolkvk5yjUn-xOKt2KWPlRnDTd4S5x-ATOo (CORE ARCHITECTURE BASELINE v1.0). German originals at /docs/canon-de/. -->

# WARAQ CORE ARCHITECTURE BASELINE v1.0

## Local Reconciliation Note

### Validity in the current canon

The baseline remains frozen and is listed in Document 1 §3.2 as a canonical baseline. In the areas listed below, later canon decisions take precedence. The baseline remains usable as a background and terminology source in those areas but is no longer the sole basis for decisions.

### Superseded / re-located passages

| Baseline passage | Current canon | Type of supersession |
|---|---|---|
| A.2 H-3 (export required questions) — contains footnote numbering as required question 3 | Document 1 §4.7 — required questions: (1) header, (2) chapter break, (3) TOC position, (4) display Arabic chapter headings in body; footnote numbering no longer a required question | Replaced — new composition of the four required questions |
| F.2 — required questions occupy P-01 | Document 1 §4.7 — required questions are an independent configuration layer, do not occupy P-01; P-01 open | Re-located — required questions are configuration layer, not gate occupancy |
| F.2 — occupancy of P-02, P-05, P-06 and W-04 through W-08 | Document 1 §4.7 — P-02, P-05, P-06 and W-04 through W-08 open, no candidates | Set to open — baseline occupancy lapses |
| F.2 W-07 (critical font availability) | Document 1 §4.7 — guard-near before preflight dialog, no W slot occupied | Re-located — guard-near precheck instead of preflight gate |
| F.2 — digit standard / RTL / document-style integrity not explicitly located before preflight | Document 1 §4.7 — guard-near before preflight dialog, blocking without slot occupancy | Added — new guard-near precheck stage |
| F.2 W-02 ("Unverified hadith locations") | Document 1 §4.7 — W-02 occupied by K-01 to K-07 consistency warnings; hadith verification status is its own named group inside the gate-check layer, H-2 blocking, H-1 warning-capable, no P/W slot occupied | Re-located — hadith non-verification in its own gate group per §4.7 / §4.16, W-02 occupied differently |
| D.1 F-06-HD — consequence "under W-02 in preflight" | Document 1 §4.16 + §4.7 — verification classes N-1 through N-10 / H-0/H-1/H-2; resolution exclusively via the seven canonized action types; `go_with_warning` analogous to §4.9 E-1, `decision_source preflight_confirmation` | Replaced — finer verification status structure, no blanket W-02 placement |
| F.3 K-02 formula consistency "Critical" | Document 1 §4.8 — K-01 through K-07 not export-blocking; exception only via §4.6 audit gate | Re-located — blocking effect runs through §4.6, not directly through K-02 |
| I.2 Conflict B (hadith source conflict, six cases) | Document 1 §4.16 — multidimensional consensus and comparison logic, mandatory set plus extended set per the consolidated state, verification classes, multi-source result objects in four levels | Added/extended — baseline logic remains compatible, but structurally superseded by significantly finer canon |
| B.6 — language-pair model question B.1 (no `sprachpaar` mandatory field, three model variants open, current state Model 3 / AR→DE default) | Document 1 §5.2 — `sprachpaar` as mandatory field in all four style profile objects; Document 1 §4.12.2 — language-pair binding canonical; Document 1 §4.12.3 — pre-population main user/admin AR_DE | Replaced — model question decided, `sprachpaar` is a mandatory field |
| J — language-pair extension of style profile objects marked open | Document 1 §5.2 / §4.12.2 / §4.12.3 — canonically decided | Replaced — no longer an open decision |

### Continues to apply unchanged

A.1, A.2 (H-1 through H-7, except H-3 per the table above), A.3 (G-1 through G-4), B.2, B.3, B.4, B.5, C.1, C.2, C.3, C.4, C.5, C.7, C.8, D.1 (F-01 through F-09 including severity matrix and aggregation logic — except the F-06-HD placement per the table above), D.2 (release gate OCR → translation Go/No-Go), G.1 through G.9 (job model and recovery), H.1, H.3, H.4 (provenance model and Why-panel otherwise), I.1 (canonical severity table), I.3 (universal Never-Automatic list).

### CR-1 clarification

The following passages are extended at the schema level by CR-1 and are therefore no longer part of "Continues to apply unchanged":

- B.1 — Decision-Event UUID: anchoring of a formal `scope_type` enum and a formal `decision_source` enum (ten values, here authoritatively `style_management`).
- C.6 — Revision model: decision events reference `scope_type`, `scope_uuid` and `decision_source` per B.1.
- H.2 — EXPORT_EVENT schema: nullable provenance field `active_stilprofil_version_uuid` (foreign key on `stilprofil_version` from B.6).
- J — Open decisions: extended by the language-pair extension of the style profile objects (model question B.1 from B.6); the baseline wording on this model question is superseded by Document 1 §5.2 / §4.12.2 / §4.12.3 per the table above.

Additionally newly introduced by CR-1: B.6 (style profile core object family) and B.7 (style profile field enums); the baseline wording on the language-pair model question in B.6 is superseded per the table above.

### Reading note on Sections E and F

Sections E (audit) and F (preflight and consistency check) are no longer a primary basis for decisions overall. For these areas, current canon per Document 1 §4.6 / §4.7 / §4.8 / §4.16 applies first; the baseline serves there exclusively as a background and terminology source. For all other sections the baseline remains the primary reference.

From here the original baseline text follows verbatim and unchanged, except for the schema extensions anchored by CR-1.

# WARAQ CORE ARCHITECTURE BASELINE — Version 1.0 (Consolidated Master Version)

## A. FOUNDATIONAL PRINCIPLES / SYSTEM LAWS

### A.1 System architecture principle

Waraq is a professional publishing platform for Arabic → German/English book translations. The goal is print-ready books from Arabic scans/PDFs. Every technical decision serves process reliability before new features.

The system is divided into two non-overridable layers:

- **Hard invariants** — Technical system laws without exception. Not overridable by user decision, configuration, or context. Run as a blocking layer in every phase.
- **Governable Project Rules** — Project-wide commitments that beat all automatic system components, but can be overridden by an explicit, documented user decision at a specific location. Override is always visible and logged.

### A.2 Hard invariants (complete list)

**H-1 — Manual corrections are never silently overwritten.** No automatic process ever changes a manually locked text state without an explicit user action with a confirmation dialog. Applies absolutely in every phase for every system component.

**H-2 — No automatic change of segments with active segment lock flag.** A segment with active segment lock flag (Lock Level 1 or 2) is not changed by any automatic operation. If a Global Terminology Layer (Lock Level 3) or a Governable Project Rule claims application to such a segment, an open, visible, decision-requiring conflict arises. No automatic resolution.

**H-3 — No export without active mandatory confirmations.** Every export requires the active answering of four required questions: (1) Which heading level appears in the header? (2) Which heading level marks a chapter break? (3) Footnote numbering per chapter or continuous? (4) TOC position front or back? Saved export profiles pre-fill fields but do not replace active confirmation.

**H-4 — No revision UUID for pure check or analysis operations.** A new text revision is created exclusively on actual change to the text state. Check, analysis, and verification operations without text change generate exclusively entries in the event log. Binding decisions without text change generate decision events, not text revisions.

**H-5 — Internal UUIDs are never recycled, changed, or deleted.** Once assigned, a UUID stays in the system permanently. On inactivity it is marked inactive, never removed.

**H-6 — Conflict between global rule claim and manual segment decision is never silently resolved.** If a Global Terminology Layer or Governable Project Rule claims application to a segment with active segment lock flag, an always visible, open, decision-requiring conflict arises. No automatic winner.

**H-7 — Manual corrections are not automatically generalized as a style rule.** A manual correction is initially exclusively a local fact at the affected segment. Promotion to a pattern candidate or a confirmed style rule follows an explicit three-stage pipeline with user confirmation.

### A.3 Governable Project Rules (complete list)

**G-1 — Western digits in the translation.** Standard: Western digits (0–9) everywhere in the German and English output. Arabic original text remains unchanged. Overridable by explicit user decision at a specific location (e.g., deliberately leaving an Arabic digit in an original quotation). Documented as a local exception.

**G-2 — Glossary and terminology decisions.** Standard: All entries apply to the entire project and beat all automatic system components. On conflict with segment lock flag (Lock Level 1 or 2): open, visible, decision-requiring conflict. Three options: (a) local exception, (b) adjust glossary entry, (c) lift segment lock flag. Overridable only by explicit user decision at a specific location.

**G-3 — Display rules for religious formulas.** Standard: Formulas are output per registry entry. Non-registered formulas are output with a marker and prompt for definition (→ missing registry entry, no Critical violation). Overridable only by changing the registry entry itself.

**G-4 — Style profile scope.** Standard: Style profile applies to all segments without active segment lock flag. Overridable via Lock Level 1/2, page-level completion mark, or explicit exclusion.

## B. CORE OBJECTS AND IDENTITIES

### B.1 Identity model

All internal processes reference exclusively opaque immutable UUIDs. Human-readable display keys are exclusively metadata for display and navigation. Display keys can change, UUIDs never.

**Page-UUID** — Opaque immutable UUID per logical page in the project state. Generated when the page is first created in the project. Display key: `[PG-{page-number}]`. Two page concepts kept clearly separate:

- *Physical page in upload/scan:* The concrete image file or PDF page as uploaded. Referenced via the SCAN PO type in the provenance graph.
- *Logical page in project state:* The Page-UUID as the canonical identity of the page within the project. Page-level states hang on it: completion mark, OCR release status, error class profile of the page.

All blocks and segments of a page reference their Page-UUID. On page replacement (better scan): the Page-UUID of the logical page is preserved. Only the SCAN PO is updated (new physical page). OCR result and segments are recomputed and matched against existing satz_uuids via lineage logic (B.3). Never changed, recycled, or deleted. On inactivity: marked inactive.

**Block-UUID** — Opaque immutable UUID per layout block. Generated on first creation. References the Page-UUID of the parent logical page. Display key: `[BL-{page}-{block-type}-{sequence}]`. Block-type abbreviations: MT (main text), FN (footnote), RN (margin note), QR (Qurʾān verse), HD (hadith), UE (heading), BI (image). Never changed, recycled, or deleted. On inactivity: marked inactive.

**Satz-UUID** — Opaque immutable UUID per semantic unit. References the Block-UUID of the parent block. Display key: `[AR-{page}-{sentence}]`. Each Satz-UUID is directly linked to the corresponding translation unit. This link is permanent. Never changed, recycled, or deleted.

**Revisions-UUID** — Opaque UUID per text-revision event, linked to a Satz-UUID. Display key: `[REV-{display-key-of-segment}-v{N}]`. Created only on actual text change. Never created for check or analysis operations.

**Decision-Event-UUID** — Opaque UUID per decision event. Generates no Revisions-UUID. Only created for binding decisions without text change.

Decision-Event schema (excerpt):

- `scope_type`: formal enum with values `segment`, `page`, `block`, `account`, `project`. Determines the scope of the decision.
- `scope_uuid`: UUID of the scope per `scope_type`. With `scope_type = segment` references a Satz-UUID, with `page` a Page-UUID, with `block` a Block-UUID, with `account` an `account_uuid`, with `project` a `project_uuid`.
- `decision_source`: formal enum that classifies the source of the decision. The baseline anchors here only the formal ten-value enum and the value `style_management` authoritative here, with the domain "style profile decisions" (style rule confirmation, style rule blocking, profile rollback, configuration changes). The remaining nine values are canonized in Document 1 §4.10 and not additionally listed here.

Distinction: do not confuse with the log ID of an analysis/check event. Decision-Event-UUIDs reside in the decision log and are part of the revision model. Log IDs of analysis/check events reside only in the event log and are not part of the revision model.

### B.2 Page-level states

All page-level states attach to the Page-UUID of the logical page:

- Completion mark (→ C.5): navigation status, not a lock flag
- OCR release status (→ D.2): Go / Go with Warning / No-Go
- Error class profile (→ D.1): set of active error classes per page
- Job checkpoints (→ G.4/G.5): processing progress of the page
- Provenance object SCAN (→ H.2): reference to physical scan file

Page-level decision events (e.g., setting completion mark) reference the Page-UUID, not a Satz-UUID.

### B.3 Lineage logic (segment level)

Matching priority on page replacement and re-segmentation:

1. First try matching on existing internal UUIDs.
2. If semantic continuity is plausibly recognizable: existing UUID is preserved.
3. New UUID only if a truly new or unassignable segment arises.
4. Old UUID becomes inactive only if no viable matching exists anymore.

Permitted lineage relations:

- **1→1 (standard match):** Segment A corresponds to Segment A'. UUID preserved. New text revision if text has changed.
- **1→n (split):** Segment A is recognized as two segments A' and A''. UUID of A is preserved as origin UUID, becomes inactive. A' and A'' receive new UUIDs with metadata: "Created from split of [UUID-A]". Revision history of A fully preserved.
- **n→1 (merge):** Segments A and B are recognized as one segment. UUIDs of A and B are preserved as origin UUIDs, become inactive. New segment receives new UUID with metadata: "Created from merge of [UUID-A] and [UUID-B]".
- **1→0 (segment disappears):** UUID of A is marked inactive, not deleted. Metadata: "Inactive since [timestamp], trigger: [cause]". Revision history fully preserved. Translation link is preserved as an inactive link.
- **Reappearance after inactivity:** First try matching against inactive UUIDs. If plausible: inactive UUID reactivated, no new UUID assigned. Revision history continues seamlessly.

### B.4 Concept ID

Internal identity of a defined conceptual unit in the glossary or terminology registry. Decoupled from surface form. Different Arabic forms can reference the same concept ID. The same form, with different meaning, can have different concept IDs. Use: basis for terminological consistency check (K-01), first-occurrence logic (K-07), and all registry-based comparisons.

### B.5 Source attributes (hadith provenance schema)

Structured description schema for every hadith source. No platform names as authority.

| Attribute | Values |
|---|---|
| Source Class | Primary manuscript / Critical edition / Digital edition text / Aggregated database text / Search-index result / Translation |
| Edition Identified | Yes (with edition info) / Partially / No |
| Wording Match Level | Exact / Slightly diverging / Significantly diverging / Unknown |
| Isnād Match Level | Identical / Structurally similar / Diverging / No isnād recognized |
| Variant State | No variant recognized / Editorial variant / True variant dispute |
| Editorial Status | Critically edited / Standard edition / Uncritical edition / Unknown |
| Access Layer | Direct source reference / Aggregator-mediated / Scraping |

### B.6 Style profile core object family

Standalone core object family on the identity layer. The family comprises four objects, each with its own UUID, analogous to the other core objects. All four objects carry `account_uuid` as a mandatory field. Field definitions follow Document 1 §5.2 and are not redefined here.

**stil_regel** — Own UUID. Mandatory: `account_uuid`. Schema fields (CR-1 portion):

- `status`: value range per status enum from B.7. Schema default on creation: `in_prüfung`. Transition conditions are not stated here.
- `regeltyp`: value range per regeltyp enum from B.7. Schema default on creation: `kandidat`. Transition conditions are not stated here.

Further fields per Document 1 §5.2.

**stilbeleg** — Own UUID. Mandatory: `account_uuid`. Fields per Document 1 §5.2.

**stilprofil_version** — Own UUID. Mandatory: `account_uuid`. Fields per Document 1 §5.2.

**referenz_paar** — Own UUID. Mandatory: `account_uuid`. Fields per Document 1 §5.2.

**Marked open model question B.1 — language-pair extension of style profile objects.** The language-pair extension of the style profile objects is explicitly open. Three model variants are in scope but not decided in the baseline:

- Model 1: two style profiles per account (separate `stilprofil_version` lines per language pair);
- Model 2: one style profile per account with language-pair-tagged examples and rules (`sprachpaar` field in `referenz_paar` and `stil_regel`, possibly `stilbeleg`);
- Model 3: keep current AR→DE default.

Current state: Model 3 per Document 2 §8 verification block. Until the model decision, no `sprachpaar` mandatory field is introduced in the style profile objects of this family; multi-profile structures per account are likewise not laid out. The model decision is part of the §3 follow-on work in Document C v1.1 and is taken there.

### B.7 Style profile field enums

Enum definitions for the fields of the style profile object family from B.6. Schema anchoring of value lists; no transition conditions or learning logic in the baseline.

- **status** (six values per Document 1 §4.14): `aktiv`, `in_prüfung`, `unterdrückt_durch_systemregel`, `nur_kontextuell_zulässig`, `deaktiviert`, `vom_nutzer_gesperrt`.
- **regeltyp** (four values per Document 1 §5.5): `invariant`, `präferenz`, `tendenz`, `kandidat`.
- **belegtyp**, **auslöser**, **invariant_quelle**, **erstellt_aus**: each with value lists per Document 1 §5.2.
- **phänomenfeld** (twelve values per Document 1 §5.3): PF-01, PF-02, PF-03, PF-04, PF-05, PF-06, PF-07, PF-08, PF-09, PF-10, PF-11, PF-12.

## C. PROTECTION, DECISION, AND REVISION MODEL

### C.1 Segment protection: two types kept clearly separate

**Segment lock flag (Lock Level 1 and 2):** Technical flag directly on the segment. Prevents automatic change of exactly that segment. Scope: always only the affected segment, never the whole page.

**Global Terminology Layer (Lock Level 3):** Not a segment lock flag. Special case of a Governable Project Rule (G-2). When it acts on a concrete segment it claims application — it does not override an active segment lock flag. Conflict is always open, visible, and decision-requiring.

### C.2 Lock Level 1 — Local segment correction

Definition: segment lock flag `manual_local`. Manual correction of a single segment without global meaning. Scope: exactly the affected segment. Other segments on the same page untouched. What is locked: this segment against re-OCR, re-translate, style profile application. Promotion pipeline: system registers the correction as local observation (Stage 1). No automatic forwarding. On conflict with Global Terminology Layer: open, visible, decision-requiring conflict (H-6). Three options: (a) local exception, (b) adjust global rule, (c) lift segment lock flag. Released by: explicit click with confirmation dialog and display of prior state. UI: discreet symbol on the segment. Hover: original text / corrected text / timestamp.

### C.3 Lock Level 2 — Editorial segment decision

Definition: segment lock flag `manual_editorial`. Deliberate substantive or translatorial decision. Scope: exactly the affected segment. What is locked: this segment against all automatic processes fully. Promotion pipeline: editorial decisions can be marked as a pattern candidate by the user explicitly — never automatically. On conflict with Global Terminology Layer: identical to Lock Level 1 — open conflict, H-6. Released by: explicit user action with confirmation dialog and clear-text warning, including date of decision. UI: more prominent symbol than Lock Level 1. Hover with decision text, optional note, timestamp. Highlighted as "editorial decision" in revision history.

### C.4 Global Terminology Layer (Lock Level 3)

Definition: special case of a Governable Project Rule. Project-wide rule binding, not a segment lock flag. Entered in the glossary or terminology registry with a concept ID. Against automatic system components: wins. Style profile, re-translate, engine output are overwritten. On conflict with Lock Level 1 or 2: no automatic winner. Three options: (a) local exception, (b) adjust glossary entry, (c) lift segment lock flag. Released by: only direct change in the glossary or terminology registry, not via inline editing. UI: own marker. Hover: glossary source, entry, scope, timestamp. In registry: all linked segments listed.

### C.5 Page-level completion mark

Definition: navigation status of a page. Not a segment lock flag. Not a technical protection mechanism. Effect: segments without active lock flag are skipped on batch operations and shown as completed in the style profile dialog. What it does not do: set a segment lock flag. Block any access. Released by: simple un-marking without confirmation dialog.

### C.6 Revision model: three layers strictly separated

**Text revision** — When: exclusively on actual change to the text state of a segment. Triggers: manual text correction, OCR recompute with diverging result, re-translation with diverging result, style profile application that actually changes text. Stored with: Revisions-UUID, Satz-UUID, before/after text, source of change, timestamp, confidence value if automatic. In UI: in segment history as "Text revision" with diff view.

**Decision Event** — When: on binding decision without text change. Triggers: setting lock flag, resolving conflict, confirming or rejecting pattern candidate, setting completion mark, choosing vocalization variant without text change, documenting local exception. Stored with: Decision-Event-UUID, `scope_type` and `scope_uuid` per B.1, `decision_source` per B.1, decision type, content, timestamp. Generates no Revisions-UUID. In UI: in segment history as "Decision event", visually separated from text revisions, on the same timeline. Page-level decision events accessible in page history. Account-scoped decision events are assigned to the account, not to a single segment or page history. Distinction: documents a binding user decision. Never replaceable by an analysis/check event for substantive purposes. Analysis/check events have a log ID in the event log, not a Decision-Event-UUID.

**Analysis/check event** — When: on every check or analysis operation without text change and without binding decision. Triggers: OCR quality check, hadith verification run, style profile analysis without text change, export-run event (whether successful or blocked). Stored with: own log ID in event log (not part of revision model), timestamp, operation type, result. Generates no Revisions-UUID and no Decision-Event-UUID. In UI: only in the separate event log, not in segment history. Distinction: analysis/check events are never binding substantive decisions. They can contribute to a decision gate but themselves document neither a user decision nor a normative release decision. Their log ID is not part of the decision model.

### C.7 Promotion pipeline: Local observation → Pattern candidate → Confirmed rule

**Stage 1 — Local observation:** Manual correction is exclusively a local fact. No automatic forwarding, no link to other locations.

**Stage 2 — Pattern candidate:** The system may passively aggregate multiple observations. If structural similarity is recognized: identify pattern candidate. A pattern candidate is not applied, leads to no text change. Offered to the user exclusively in the "Recognize my style" dialog for review.

**Stage 3 — Confirmed rule:** Only by explicit user confirmation in the dialog or by user-activated promotion logic. Applies exclusively to segments without active segment lock flag.

### C.8 Hierarchy of protection layers

| Layer | What it is | Scope | Overridable | Conflict behavior | Effect type |
|---|---|---|---|---|---|
| Hard invariants | Absolute system laws | Whole system | No | Always win | Absolutely blocking |
| Governable Project Rules | Project-wide commitments | Whole project | Yes — explicit, documented | Beat automation | Blocking with exception option |
| Global Terminology Layer (Lock Level 3) | Project-wide rule binding, no lock flag | All occurrences of a concept ID | Yes — local exception | Beats automation; conflict against Lock Level 1/2 always open | Blocking against automation |
| Editorial segment decision (Lock Level 2) | Segment lock flag | Exactly the affected segment | Only explicit release | Beats automation; conflict against Lock Level 3 open | Blocking at segment |
| Local segment correction (Lock Level 1) | Segment lock flag | Exactly the affected segment | Only explicit release | Beats automation; conflict against Lock Level 3 open | Blocking at segment |
| Page-level completion mark | Navigation status | Page, soft | Yes — anytime | No conflict | Navigational, soft protection |
| Navigation/display states | Display | Display only | Yes — anytime | No conflict | Purely navigational |

## D. OCR DIAGNOSTICS AND RELEASE GATE

### D.1 OCR error profile: diagnostic model

The OCR error profile is not a quality score. It is a segment-precise error class system that reports per page and per block what kind of problem is present, why, and what consequences follow.

**Error classes**

**F-01 — Reading order unstable.** Detection: geometric analysis and semantic reconstruction contradict each other. Topological sort yields ambiguous result. Severity: Critical. Consequence: block marked unconfirmed. Mandatory check. Translation release blocked. UI: both variants side by side. User chooses actively.

**F-02 — Column separation uncertain.** Detection: column separation line not unambiguous. Text blocks overlap geometrically. Severity: Critical for multi-column texts; Medium for single-column with margin notes. Consequence: blocks marked "column assignment uncertain". Mandatory check if Critical. Translation release blocked if Critical and unconfirmed.

**F-03 — Margin note collides with main text.** Detection: margin-note block geometrically overlapping with main-text block. Line mixing detected. Severity: Medium. Consequence: blocks marked with type uncertainty. Options: as margin note / main text / image / skip. Warning, no block. Contributes to aggregation logic.

**F-04 — Footnote area questionable.** Detection: separating line between main text and footnotes not recognized. Sequence numbers not assignable. Severity: Medium. Consequence: footnote blocks marked unconfirmed. Notice. Warning, no block. Contributes to aggregation logic.

**F-05 — Heading detection unstable.** Detection: block classified as heading, semantic reconstruction contradicts. Or: ambiguous hierarchy assignment. Severity: High — affects TOC build and export logic. Consequence: flag "heading uncertain". Mandatory check. No direct translation block, but TOC confirmation Phase 4 is triggered. To be carried as: high error class with structural block effect via Phase 4.

**F-06-QR — Qurʾān verse match uncertain.** Detection: block identified as Qurʾān verse but no secured match in verification sources. Severity: Critical. Exact wording is non-negotiable for Qurʾān verses. Permitted resolution paths (exclusively):

- Verified by external source
- Manually corrected and then verified
- Reclassified as non-Qurʾān verse (with reason)
- Treated as image/facsimile without textual translation
- Removed from translation flow

Not permitted: block remains classified as Qurʾān verse and is taken into translation as "not verified". Consequence: mandatory panel without close option until resolution chosen. Translation release blocked for affected block.

**F-06-HD — Hadith match uncertain.** Detection: block identified as hadith, no secured match. Severity: High. Permitted resolution paths: verified, manually assigned, or explicitly marked as not verified (permitted, marker stays visible until export). Consequence: warning, no translation block. Unverified locations appear in export preflight under W-02 (note: superseded by Document 1 §4.16 + §4.7).

**F-07 — Image dominance too high.** Detection: share of non-textual pixels exceeds calibratable threshold. Severity: Critical if entire page; Medium if single block. Consequence: options panel: as image, manually transcribe, better scan, skip. Translation release blocked until option chosen.

**F-08 — Semantic reconstruction contradicts geometry.** Detection: both orderings yield plausible text, no clear superiority. Severity: Medium to Critical. Consequence: both variants stored. Mandatory check. Translation release blocked until decided.

**F-09 — Residual skew not fully corrected.** Detection: after Hough transformation residual baseline deviations remain above calibratable tolerance value. Severity: Medium. Consequence: increased OCR uncertainty for this page. Notice. Warning, no block. Contributes to aggregation logic.

**OCR severity matrix**

| Error class | Severity | Review required | Translation block | Aggregation |
|---|---|---|---|---|
| F-01 | Critical | Yes | Yes | No |
| F-02 | Critical / Medium | Yes if Critical | Yes if Critical | No |
| F-03 | Medium | No — options | No | Yes |
| F-04 | Medium | No — notice | No | Yes |
| F-05 | High | Yes | No — TOC duty | No |
| F-06-QR | Critical | Yes — mandatory panel | Yes (strict) | No |
| F-06-HD | High | Yes | No — marker | No |
| F-07 | Critical / Medium | Yes | Yes if Critical | No |
| F-08 | Medium–Critical | Yes | Yes until decided | No |
| F-09 | Medium | No — notice | No | Yes |

**Aggregation logic.** A high density of non-critical OCR problems can sharpen the overall state. Affects F-03, F-04, F-09 in large quantity as well as combinations of multiple medium error classes. On exceeding a calibratable threshold: release state changes to a heightened warning level with explicit summary "Problem density elevated". Generates no new blocking category. Thresholds are exclusively calibratable configuration values, not hard-coded.

### D.2 Release gate between OCR review and translation

The release gate is an explicit Go/No-Go check after OCR review and before translation start. No automatic start.

**Three exit states**

- **Translation-ready (Go):** All pages without open Critical error classes. All mandatory checks completed. TOC structure confirmed or no TOC. Aggregation logic does not trigger heightened warning level.
- **Translatable with warning (Go with Warning):** At least one non-Critical open error class. No open Critical. Or: aggregation logic triggers heightened warning level. User confirms explicitly with full warning list.
- **Translation blocked (No-Go):** At least one open Critical error class without resolution. Or: F-05 mandatory check not completed. Or: release conditions not met.

**Release conditions**

- Condition 1: All open Critical error classes must be resolved by user decision. Until calibration: each individual open Critical error class without resolution blocks.
- Condition 2: All mandatory checks with block effect resolved by user decision.
- Condition 3: If TOC detected: TOC confirmation Phase 4 completed, unresolved headings (F-05 mandatory) resolved.
- Condition 4: All F-06-QR blocks resolved by one of the five permitted resolution paths.
- Condition 5: On heightened warning level from aggregation logic: explicit user confirmation with visible problem-density summary.

**TOC phases: two distinct purposes**

- Phase 4 — Structural TOC check: After OCR, before translation release. Purpose: identify chapter headings, confirm hierarchy. Structural decision. Prerequisite for Condition 3.
- Phase 6 — Final TOC review: After translation completion, before export. Purpose: check that headings transferred correctly, chapter naming accepted. Substantive final check. Not a repeat of Phase 4.

UI: release-gate screen shows overall status, complete blocking or warning list, confirmation button. Never automatic: translation starts without explicit user release. F-06-QR taken into translation without permitted resolution.

## E. TRANSLATION AUDIT AND RULE CHECK

> *Note: Section E is no longer the primary basis for decisions. Current canon: Document 1 §4.6 + Implementation Translation Baseline v1.0.*

### E.1 Founding principle

No overall score. The audit checks per segment whether concrete defined rules were followed or violated. Each violation has a violation class, severity, and consequence. The audit runs in parallel with translation output.

### E.2 Registry types and binding levels

Terminology registry and glossary: entries are user-set binding determinations. Deviation = violation of G-2. Severity: Critical.
Religious formulas registry: entries are likewise binding determinations. Binding level identical to terminology registry. Deviation = violation of G-3. Severity: Critical.

### E.3 Rule categories

**Category A — Particle fidelity:**
- A-01 إِنَّ / أَنَّ not transferred — High (mandatory notice)
- A-02 لَ (emphasis) not transferred as emphasis — Medium
- A-03 فَ not transferred context-sensitively — Medium
- A-04 أَمَّا...فَ construction not fully transferred — High (mandatory notice)

**Category B — Structural fidelity:**
- B-01 Idāfa too freely resolved — High
- B-02 Dual not visible — High
- B-03 Gender difference not transferred — Medium
- B-04 Conditional clause not text-near — Medium

**Category C — Terminology and citations:**
- C-01 Terminology entry violated — Critical (blocking)
- C-02 Islamic technical term without first-occurrence handling — High
- C-03 Translator addition not marked — High

**Category D — Stylistics and rhetoric:**
- D-01 Metaphor/idiom not literal with footnote — Medium
- D-02 Sajʿ without note in footnote — Medium
- D-03 Religious formula violates registry — Critical (blocking)

### E.4 Violation classes and consequences

| Class | Severity | Consequence before export |
|---|---|---|
| Critical | Registry violation (C-01, D-03) | Location blocked until resolved |
| High | Mandatory notice | Decided actively per location before export |
| Medium | Notice | Export with warning possible |

## F. EXPORT PREFLIGHT AND WORK-WIDE CONSISTENCY CHECK

> *Note: Section F is no longer the primary basis for decisions. Current canon: Document 1 §4.7 / §4.8.*

### F.1 Order before export

1. Work-wide consistency check (F.3)
2. Export preflight (F.2)
3. Export

### F.2 Export preflight / preflight logic

(Baseline wording on P-01…P-06 / W-01…W-08 superseded. Current canon: Document 1 §4.7. Occupied gates: P-03, P-04, W-01, W-02, W-03. Open: P-01, P-02, P-05, P-06, W-04…W-08. Guard-near prechecks before preflight dialog: digit standard, RTL encoding/application, document-style integrity, critical font availability.)

### F.3 Work-wide consistency check

K-01 terminological consistency, K-02 formula consistency, K-03 person names/entities consistency, K-04 transliteration pattern consistency, K-05 source treatment consistency, K-06 structural consistency, K-07 first-occurrence consistency.

(Baseline K-02 as "Critical" superseded: K-01–K-07 not export-blocking per se; exception only via §4.6 audit gate. See Document 1 §4.8.)

## G. WORKFLOW ROBUSTNESS / JOB MODEL / RECOVERY

### G.1 Three process levels

- **Client-bound processes:** require active data transfer from the client. Cannot continue without connection. Concerns: upload jobs.
- **Server-side decoupled processes:** run fully on the server. Independent of browser, session, and client connection after start. Concerns: OCR jobs, translation jobs, follow-on processing.
- **Session-dependent UI visibility:** ability of the user to see job state. Pure display layer. Affects neither job state nor progress.

### G.2 Job states

- **Active:** Job runs.
- **Deferred:** Transient external state. Cause outside the job (API outage, brief network interruption, rate limit). Auto-retry permitted. No user intervention required. Distinction from Paused: Deferred is transient and externally caused.
- **Paused:** Job halted, not terminal. Resume from checkpoint. No auto-retry. Resumable only by user action. Can be triggered by decision gate, upload interruption, or explicit user action. Distinction from decision gate: Paused is a job state; decision gate is a workflow state that can trigger Paused.
- **Failed:** Terminal error state. No auto-retry. Resumable only by explicit user instruction.
- **Partially failed:** Applies only when it is clearly identifiable which units have failed terminally. Completed units remain.

### G.3 Transient vs. terminal

- **Transient → Deferred, auto-retry permitted:** External API service temporarily unreachable, brief network interruption, temporary resource shortage, rate limit.
- **Terminal → Failed, no auto-retry:** Internal error after exhaustion of retry budget, structurally defective input, external API with reproduced substantive error.
- **Auto-retry budget:** Configurable number of attempts. After exhaustion: state changes from Deferred to Failed.

### G.4 Upload jobs (client-bound)

Chunk-based. Server stores after each chunk persistently with hash checksum. Resume from last confirmed chunk, never restart. State transitions: Browser closed → Paused. Transient network interruption → Deferred. Timeout without reactivation → cleanup after configured period. Notification before cleanup: only if a delivery channel exists. Otherwise UI hint as long as session reachable. A completed upload is fully decoupled from the downstream OCR job. OCR job continues thereafter as a server-side decoupled process.

### G.5 OCR jobs and translation jobs (server-side decoupled)

Browser closed or session end (logged in): job continues. No state change. OCR checkpoint granularity: after each page and after each critical pipeline step. Translation checkpoint granularity: after each chunk. Context buffer (last paragraph) preserved also in Deferred and Paused states. API outage → Deferred. Auto-retry. User notified if delivery channel exists. Internal error → Failed for affected unit. Job continues on other units (Partially failed). No auto-retry. User instruction required. Decision gate reached → Paused until decision. Conflict on resume: if already output and resume yields different result: new result stored as new text revision, not silently overwritten.

### G.6 Behavior after event

| Event | Upload job | Server-side job | UI visibility |
|---|---|---|---|
| Browser closed (logged in) | Paused | Continues | Lost until next login |
| Browser closed (guest, job running) | Paused | Runs until timeout | Lost |
| Network interruption (transient) | Deferred | Deferred | Interrupted |
| Session timeout, no active job | – | – | Ends |
| Session timeout, active job (logged in) | – | Continues | Lost until login |
| Internal server error | Paused | Partially failed | Depends |
| Explicit cancel | Paused | Paused | Visible |

### G.7 Guest users

Upload jobs: pause on browser close. Resume only if session ID still valid. Server-side jobs after completed upload: run until configured timeout. Result reachable when browser reopened. Account creation after job completion: project transferred to account. No delivery channel: UI hint as long as session reachable. UI hints: during upload: "Do not close the browser until an account has been created." After upload completion: "Processing in progress — create account now to secure project." After completion: "Without account, your result will be deleted after [timeout]."

### G.8 Page replacement and partial recompute

Only the replaced page is recomputed. All other pages unchanged. Sequence: Upload job (client-bound) → after completion OCR job (server-side decoupled) → matching against existing Satz-UUIDs (lineage logic B.3) → translation only for segments with changed OCR text → manually edited segments: explicit user query. Page-UUID of the replaced page preserved; only SCAN PO is updated. Never automatic: re-OCR of other pages. Re-translation of unchanged segments. Overwriting of manually edited segments.

### G.9 Cleanup and expiration rules

Upload jobs: cleaned up after configured timeout without reactivation. OCR and translation job metadata: kept permanently (logged-in users). Guest user jobs: cleaned up after configured timeout without account creation. Failed jobs: stay marked. No automatic restart. Project cleanup: only by explicit user action. Trash 10 days. Never automatic: forced full restart on interruption. Auto-retry for terminally failed job parts. Notification via non-existent channel. Recompute of completed pages on page replacement. Overwriting of manually edited segments on resume. Restart of failed jobs without user instruction.

## H. PROVENANCE / WHY-PANEL / HISTORY

### H.1 Founding principle

Every segment carries a complete, gapless origin history. The internal model is a segment-centric provenance graph. Each provenance object (PO) primarily references the Segment-UUID and optionally a Revisions-UUID or Decision-Event-UUID. There is no serialized linear path. Multiple POs of the same type can exist in parallel or distributed in time. Exception: the EXPORT_EVENT PO type is primarily defined work-wide (→ H.2). Segments reference it via its Export-UUID — not the other way around. The "Why?" panel is a filtered, decision-relevant narrative view of this graph — not the model itself.

**Separation of internal model and UI:** Provenance visible in the UI must never be misleadingly truncated or silently merged. The UI must make all provenance elements relevant to the concrete decision visible. Not every internal technical metadata level must always be fully expanded in the main panel. Summarized representations are permitted, provided a Details action makes the full state accessible.

### H.2 Provenance object types

**SCAN PO type** — Reference to origin scan. Fields: Segment-UUID, page reference, Block-UUID, file path, upload timestamp, file format. On page replacement: lineage type in metadata. No manual intervention possible.

**OCR PO type** — OCR run result. Fields: Segment-UUID, Revisions-UUID, engine name + version, confidence indicator (qualitative), active error classes, timestamp. Multiple possible (per run).

**VOCALIZATION PO type** — Vocalization decision. Fields: Segment-UUID, Revisions-UUID if text change, method (Original / AI / Manual), confidence if AI, chosen variant if conflict, all alternative variants with semantic difference.

**TRANSLATION PO type** — Translation decision. Fields: Segment-UUID, Revisions-UUID, engine name + version, applied style rule (name, confidence), chunk context reference, timestamp. Multiple possible.

**RULE_BINDING PO type** — Application of a glossary, terminology, or formula rule. Fields: Segment-UUID, optional Revisions-UUID, registry type, concept ID, entry, scope, timestamp. If local exception: exception flag + reason + Decision-Event-UUID of the corresponding user decision.

**SOURCE_VERIFICATION PO type** — Source verification for Qurʾān or hadith. Fields: Segment-UUID, verification type (QR / HD), all sources found with full source attributes, chosen resolution path, timestamp. Multiple possible on re-verification.

**MANUAL_\*** **PO type** — Manual intervention at a specific level (OCR, vocalization, translation, rule level). Fields: Segment-UUID, Revisions-UUID or Decision-Event-UUID (depending on whether text change occurred), Lock Level (1 or 2), text state before/after if text change, optional user note, timestamp.

**EXPORT_EVENT PO type (export event)** — Work- and artifact-related provenance object. Created exclusively on successful export. Primary scope is the entire work / produced artifact, not individual segments. Fields (work-wide): Export-UUID (own UUID of the export event), work reference, export type, timestamp, export configuration (answers to all four required questions), snapshot of all currently active revision states of contained segments (as ordered reference list of Revisions-UUIDs), all Decision-Event-UUIDs active at the time, reference to produced export artifact, `active_stilprofil_version_uuid` (nullable provenance field; foreign key on `stilprofil_version` from B.6; without effect on existing query logic and without intervention in existing provenance aggregation). Segment linkage: segments reference the EXPORT_EVENT via its Export-UUID — not the other way around. The export event itself is primarily defined work-wide. The "Why?" panel of a segment shows linked export events of the work state, not "segment-own" exports. A blocked or aborted export attempt creates no EXPORT_EVENT, only an export-run event in the event log (analysis/check event with log ID).

### H.3 The "Why?" panel

Trigger: click on any segment. Display principle: filtered narrative view. Only PO types present for this segment are shown. Order is readable, not the internal graph structure.

**Concrete contents**

- Origin: page, block, upload timestamp, format. Link to original page. On page replacement: lineage type.
- OCR: active revision, engine, confidence indicator, error classes if present. Diff option if multiple revisions. Details action opens all OCR POs.
- Vocalization: only if not original-vocalized. Method, confidence. All alternative variants with semantic difference preserved also after decision.
- Translation: active revision, engine, applied style rule. Manually edited: notice with date. Details action opens all TRANSLATION POs.
- Rule binding: all active RULE_BINDING POs. Concept ID, registry type, entry, date. Local exceptions explicitly with reason.
- Source verification: if QR or HD. Verification type, resolution path. With variant constellation: all competing sources with full source attributes individually visible — never summarized.
- Manual intervention: all MANUAL_\* POs chronologically. Level, Lock Level, before/after, date, optional note.
- Export events: all EXPORT_EVENT entries in which this segment was contained, chronologically. Shown as: "Contained in export [export type] dated [date], work state revision [N]." Click opens the work-wide export entry. The panel shows linked export events of the work state — no segment-own exports.

### H.4 Appearance in other views

- Segment view: provenance indicators (symbol per active PO type). Hover: short version.
- Revision history: full timeline of all text revisions and decision events (by Decision-Event-UUID). Event log separately accessible for analysis/check events (by log ID) and export-run events.
- Review (OCR, TOC, final review): provenance accessible at any time without context switch.
- Export events in segment view: segments show linked export events as references to the work-wide EXPORT_EVENT entry. The display reads "This segment was contained in export [X]" — not "This segment has its own export".

Never automatic: silent merging of two POs. Removal of a PO even when superseded. Competing sources reduced to one without user decision. EXPORT_EVENT changed after completion. Uncertain decisions shown silently as secured.

## I. CROSS-CUTTING RULES / CONFLICT LOGIC / CANONICAL SEVERITIES

### I.1 Canonical severity table

Uniform tripartite division across all models. Meaning varies by context:

| Severity | OCR diagnostics | Translation audit | Work-wide consistency |
|---|---|---|---|
| Critical | Blocks translation release | Blocks export location until resolved | Blocks export (P-06) |
| High | Review required, structural effect | Mandatory notice, individual decision before export | Mandatory decision before export (P-06) |
| Medium | Warning, no block | Notice, export possible | Notice, export possible (W-08) |

### I.2 Conflict matrix

- **Conflict A — Geometric OCR order vs. semantic reconstruction.** Decision logic (qualitative): if semantic reconstruction clearly dominates: it wins. If geometric analysis clearly dominates: it wins. On true indecision: user notice with juxtaposition. Thresholds: calibratable configuration values after gold-corpus tests. Never automatic: final ordering on true ambiguity without user confirmation.
- **Conflict B — Hadith source conflict.** Six cases. Superseded by Document 1 §4.16 (multidimensional consensus and comparison logic).
- **Conflict C — Manual single correction vs. style profile pattern.** Segment lock flag blocks style profile application. Style profile registers as local observation, never to be applied. One-time hint when contradicting a learned pattern. Never automatic: style pattern adjustment or segment change without user confirmation.
- **Conflict D — Template default value vs. user rule on export.** User rule always wins after active confirmation. Export audit shows deviation explicitly. Never automatic: template value passing through without active confirmation.
- **Conflict E — Glossary vs. style profile for the same term.** Glossary (Governable Project Rule G-2) wins against style profile (automatic system component). Never automatic: glossary entry overwritten by style profile.
- **Conflict F — Vocalization uncertainty vs. translation output.** Three qualitative levels: high confidence = silent. Medium confidence = tooltip. Low confidence = full panel with all variants, semantic difference, translation preview. Thresholds: calibratable configuration values after benchmarking. Never automatic: translation finalized at low confidence without user notice.

### I.3 Universal Never-Automatic list

No system component may ever automatically:

- Change a text state with active segment lock flag
- Silently resolve a conflict between global rule claim and active segment lock flag
- Generalize a manual correction as a style rule without promotion pipeline and user confirmation
- Create a Revisions-UUID for a pure check or analysis operation
- Store a binding decision without text change as a text revision (instead: decision event with Decision-Event-UUID)
- Confuse or treat as equivalent the log ID of an analysis/check event with a Decision-Event-UUID
- Recycle, change, or delete an internal UUID (Page, Block, Segment, Revision, Decision Event)
- Perform an export without active confirmation of all four required questions
- Output a religious formula without registry comparison
- Write Arabic digits into the translation (except documented local exception)
- Finalize a hadith assignment in true variant dispute without user notice
- Remove an inactive UUID
- Delete a vanished segment from revision history
- Promote a pattern candidate to a confirmed style rule without user confirmation
- Assign a Satz-UUID to another segment or reuse it
- Trigger a forced full restart of a job on interruption
- Restart failed jobs without user instruction
- Confuse or merge export-run event and EXPORT_EVENT
- Globally normalize consistency violations without user decision
- Reduce competing hadith sources to one without user decision
- Take an F-06-QR block into translation without permitted resolution

## J. OPEN DECISIONS FOR LATER PHASE

The following points are deliberately not finalized. They require empirical data, product-strategy decisions, or external benchmarks:

**Calibratable thresholds (after gold-corpus tests and benchmarking):**

- Confidence bounds for OCR Conflict A (geometry vs. semantics)
- Confidence bounds for vocalization levels (high / medium / low)
- Threshold for image dominance (F-07)
- Tolerance for residual skew (F-09)
- Aggregation logic threshold for non-critical OCR problem density
- Page coverage threshold for release gate (currently: each open critical error class blocks)

**Product-strategy decisions:**

- Exact guest-user timeout values
- Exact upload chunk sizes and retry budgets
- Concrete UI design (symbol language, panel layout, color system)
- Concrete realization of the "Recognize my style" dialog
- Implicit promotion logic for pattern candidates (whether and under what conditions activatable)
- Adobe InDesign / Affinity Publisher export (saved for later phase)
- Further languages and source languages (saved for later phase)
- Language-pair extension of the style profile objects (model question B.1 from B.6 — three model variants in scope, not decided in baseline; superseded: canonically decided in Document 1 §5.2 / §4.12.2 / §4.12.3)

**Content inputs still pending:**

- Example sentences for Option B (personal translation style) to complete the style profile
- Final quality audit after example sentences

— End of version —