# **DOCUMENT 2 – WORKING AND REFERENCE DOCUMENT**

Cleaned full-text version.

## **1. REFERENCE TO THE CANONICAL STATE**

The living master document (Document 1) is the sole canonical primary source.

Additional authoritative individual documents (all frozen):

  - Waraq Core Architecture Baseline v1.0
  - Waraq Implementation Translation Baseline v1.0
  - Waraq Engineering Execution Baseline v1.0
  - Waraq Delivery Backlog Baseline v1.0
  - Sprint-0 through Sprint-6 plans v1.0
  - OCR Export Final Version v1.3
  - Document A – Canonical User Style Corpus v1.0
  - Document B v1.2 – Feature Specification "Recognize my translation style"
  - Document C v1.1 – Integration Notice
  - Canonical Document Style Templates Baseline v1.1

## **2. FROZEN POINTS**

### **2.1 Frozen Across the Board**

  - All baselines and documents listed above.
  - OCR Export Final Version v1.3: frozen, ready for implementation, no coding release.
  - Document A, Document B v1.2, Document C v1.1: frozen, canonical.
  - Document Style Templates Baseline v1.1: frozen.
  - Style feature priority logic (Tier 1 / Tier 2 / Tier 3): immutable.
  - decision_source enum (10 values): immutable.
  - Audit matrix A-01–D-03: baseline-based frozen.

### **2.2 Separation Rules**

  - OCR export strand from style feature: absolutely separated.
  - Preflight configuration layer from gate-check layer: conceptually separated.
  - Word panel strand from interface strand: separate work fronts.

### **2.3 Newly Frozen – P-Slot Occupation Logic**

|  |  |
| :-: | :-: |
| **Decision** | **Content** |
| P-01–P-02 / P-05–P-06 – Occupation logic | Free slots are occupied exclusively by blocking states already established in the existing canon. |
| P-01–P-02 / P-05–P-06 – Candidate state | Currently no clean candidates identifiable. Slots remain open. |

### **2.4 Newly Frozen – W-Slot Minimal Model II and P-03**

|  |  |
| :-: | :-: |
| **Decision** | **Content** |
| W-01 / W-02 / W-03 – Occupation Minimal Model II | W-01 = Medium audit findings. W-02 = K-01–K-07 consistency warnings. W-03 = Gradual document style template deviations. |
| P-03 – Structural role in preflight | Independent blocking gate in the preflight gate-check layer, structurally on par with P-04. |

### **2.5 Newly Frozen – Critical Font Availability and W-04 through W-08**

|  |  |
| :-: | :-: |
| **Decision** | **Content** |
| Critical font availability – placement | Guard-near before the preflight dialog. If one of the four critical fonts is missing, the preflight dialog is not opened. Resolution only by technical restoration. No P-slot occupied. |
| W-04 through W-08 – Candidate state | No further clean candidates currently identifiable in the existing canon of publication export. Slots remain open. No directional binding pre-empted. No new warning-based states introduced. |

### **2.6 Newly Frozen – Translation Pipeline Behavior, Qurʾān Recognition Rules, Shamela Modes, OCR Quality Principle**

|  |  |
| :-: | :-: |
| **Decision** | **Content** |
| Check model correction right (§3.6) | Four situation types: agreement → primary adopted; objective deterministic finding → auto-correction, logged; substantively interpretive → confidence drops, review; genuine ambiguity → user notice. Model assignment remains open. |
| No silent role swap (§3.6) | Primary path failure → no silent switch; check path failure → primary continues, affected passages count as not cross-checked and are logged. |
| Audit findings in translation flow (§3.6) | A-01 through D-03 do not stop the flow; findings persisted and carried forward in preflight. |
| Qurʾān vocalization rule (§4.15) | After accepted recognition: quranenc.com sole text carrier. No free choice case. Only the recognition question is verifiable. |
| Qurʾān API call timing (§4.15) | First external API call only in translation phase. No external call in OCR phase. |
| Qurʾān confidence protection (§4.15) | Below threshold: manual confirmation upstream. Threshold open. |
| Qurʾān project-passage protection (§4.15) | Existing project passages remain unchanged on changes to local copy. No silent overwriting. |
| Shamela usage modes (§3.5) | Mode A (OCR-internal, system-triggered in OCR Stage 3) and Mode B (user-driven, lexicon workflow in translation phase). |
| Shamela Lisān/Tāj (§3.5) | Treated as independently queryable units within Shamela. |
| OCR quality principle (§3.4) | No artificial winner with unresolved ambiguity after running through the prescribed reconstruction stages. Confidence drops, review prioritized. |

### **2.7 Newly Frozen – Hadith Integration**

|  |  |
| :-: | :-: |
| **Decision** | **Content** |
| Hadith source structure (§4.16) | Two-tier: mandatory set (sunnah.com, Shamela, dorar.net) and extended set (islamweb.net, جامع السنة النبوية, المكتبة الوقفية, جامع الكتب التسعة, موسوعة الأحاديث النبوية). المكتبة الوقفية deliberately as escalation source in the extended set, not in the mandatory set (adopted integration state). |
| Hadith consensus logic (§4.16) | Multidimensional comparison and consensus logic (wording proximity, carriage, author proximity, isnād, vocalization, authenticity). Linear confidence ranking (§3.5) as tie-breaker. |
| Kutub as-Sitta (§4.16) | Strong weighting factor, no absolute precedence. More wording-faithful, robust hit outside it can break precedence; deviation visible in review. |
| Hadith decision_event mapping (§4.16) | 7 action types → translation_pipeline (2) + conflict_resolution (5). No new decision_source value. |
| Hadith vocalization principle (§4.16) | Reference matn and reference vocalization as separately determinable fields. No sole text carrier (delineation from §4.15). Relevant conflicts → user involvement → conflict_resolution. Concrete escalation criterion closed. |

### **2.8 Newly Frozen – Consolidation of Interface 5**

|  |  |
| :-: | :-: |
| **Decision** | **Content** |
| Mandatory set (§4.16) | P-1 sunnah.com, P-2 Shamela, P-3 dorar.net remain mandatory sources. Unchanged. |
| E-1 islamweb.net (§4.16) | Option B decided: documented, factually suspended. |
| E-2 جَامِعُ السُّنَّةِ النَّبَوِيَّة (§4.16) | Highly reliably identified as Alifta-/Harf variant. Option B decided: documented, factually suspended. |
| E-3 المكتبة الوقفية (§4.16) | Option B decided: documented, factually suspended; only kept as a possible manual reference source. |
| E-4 جَامِعُ الكُتُبِ التِّسْعَة (§4.16) | Option B decided: documented, factually suspended. |
| E-5 مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة (§4.16) | Option B decided: not suspended. Special role "German translation source / multilingual reference source". No broad corpus replacement source. No API full-text search path. Technical connection via official API and official bulk downloads. |
| Exclusion (§4.16) | hadithportal.com excluded as a source for hadith verification. |
| Escalation logic (§4.16) | When the extended set is automatically activated, in practice exclusively E-5 in special role is effective, as long as E-1–E-4 remain suspended. Two-tier structure mandatory/extended structurally unchanged. |

### **2.9 Newly Frozen – Canonization Round K-1 / K-2 / K-3 Hadith Strand**

|  |  |
| :-: | :-: |
| **Decision** | **Content** |
| Vocalization escalation criterion (§4.16) | Classes V-0 (automatically tolerable) / V-1 (logging-mandatory without escalation) / V-2 (escalation-mandatory) with typology, aggregation rule (highest class wins), fallback rule (in doubt V-2). Field vokalisierungs_konflikt strictly binary (no / yes); class differentiation exclusively via the derived vokalisierungsklasse. With unclear type assignment the field remains yes; ambiguity is documented only in logging or in the conflict reasoning. Closes the residual openness named in §4.16 regarding the concrete escalation criterion. |
| Hadith verification status (§4.16) | Passage types N-1 through N-10; verification classes H-0 (review-internally tolerable) / H-1 (logging-mandatory, warning-capable) / H-2 (export-blocking until resolution). Resolution exclusively via the 7 canonized action types. Marking "for later clarification" does not lift H-2. No audit case within the meaning of §4.6. No new decision_source values. |
| Gate placement of hadith verification status (§4.7) | Independent named group "Hadith Verification Status" within the existing gate-check layer. No new layer. No occupation of open P-01/P-02/P-05/P-06 or W-04–W-08 slots. H-2 blocking, H-1 warning-based (go_with_warning analogous to §4.9 E-1, decision_source preflight_confirmation per §4.10). Slot-independently managed; later formal slot occupation remains possible. |
| Data model of hadith multi-source result objects (§4.16 / Chapter 5) | Four logical levels (passage anchor / single-source reading / aggregated overall result / user decision overlay). quellen_rolle is mandatory snapshot field per single-source reading (values pflicht / erweitert_aktiv / erweitert_sonderrolle / erweitert_suspendiert), fixed at the time of the verification run; no dynamic back-derivation. Derived, not persisted: entscheidungsstatus, vokalisierungsklasse, hadith_stellen_typ, hadith_verifikationsklasse. satz_uuid is mandatory once sentence segmentation is available for the passage. Immutability analogous to §4.9 E-10. No new core objects. No new decision_source values. |

### **2.10 Newly Frozen – Partial Canonization K-4 R-1 / R-2 (English Hadith Strand)**

|  |  |
| :-: | :-: |
| **Decision** | **Content** |
| English hadith strand – partial canonization R-1 / R-2 (§4.16 / §5.1.1) | English-language website translations from hadith verification sources (P-1 sunnah.com, E-5 hadeethenc.com) are managed in website_uebersetzung with lang = "en". Entries arise independently of the project target language and act exclusively as provenance and comparison material. Display as comparison language in the hadith review is permissible, not mandatory, generates no own decision_event. No effect on matn consensus, reference matn, reference vocalization, primary translation. No new field, no new decision_source value, no new architecture. R-3 structural decision canonized: English hadith output as own primary production path from the Arabic matn, parallel and structurally equivalent to the German hadith output; no-cascade rule for the hadith matn translation. Detailed R-3 rules (source citation format, transliteration, footnote logic, relationship to style feature and Interface 3) remain workbench. |

### **2.11 Newly Frozen – Qurʾān Carrier Structure M3**

|  |  |
| :-: | :-: |
| **Decision** | **Content** |
| Q4-9 AR reference collection status (§4.15) | AR reference collection is an independent local collection, independent of the translation fallback copies. Used in a target-language-independent manner. At no point API-supported, no API primary path, no fallback status. Canonically named APIs (quranenc.com DE and EN) and their local fallback copies concern exclusively the translation carriers, not the AR reference collection. AR source designation and AR update mechanism remain expressly open (Interface 4 detail points). |

### **2.12 Newly Frozen – Interface 5 Structural Follow-ups A-4 / A-6 / A-7 / A-8**

|  |  |
| :-: | :-: |
| **Decision** | **Content** |
| A-4 HTML stripping (Model R, §5.1.1) | For sources with markup response, the raw body is persisted in matn_arabisch_raw; matn_arabisch contains the deterministically derived text version. Text-proximity, comparison, and consensus logic operate on matn_arabisch. For sources without markup, matn_arabisch_raw is omitted. |
| A-6 Scraping secondary path (Model D, §3.5) | Scraping is strict secondary path relative to an existing API of the same source. For dorar.net: API path primary, scraping only as fallback. DOM break = §4.18 Class B failure without retry; no silent self-healing at runtime. |
| A-7 Request profile of external sources (Model U, §3.5) | External HTTP-based sources (APIs and scraping paths) follow a uniform conservative request profile. Local sources excluded; Shamela explicit exception. Concrete rates, pauses, upper limits, and resumption times remain open and will be set after real measurement. |
| A-8 E-5 runtime mode (§4.16) | Official Live API primary runtime path. Official bulk downloads secondary auxiliary and analysis path, not runtime source for hadith verification. No offline index as normal path. No frontend scraping as normal model. |

## **3. OPEN POINTS**

### **3.1 Class 1 – Confirmed and Canonically Frozen**

**Audit and consistency points:**

  - C-01, C-02
  - L-01, L-07–L-09, L-13, L-15–L-17, L-19–L-21, L-23, L-25
  - L-02–L-06, L-10–L-12, L-14
  - Audit matrix A-01 through D-03

**Translation pipeline and API behavior:**

  - API failure channel
  - Dashboard status indicator
  - Persistence of style markers
  - Style feature calibration values
  - Translation pipeline model assignment (§3.6): Primary GPT-4o / Check Gemini 2.5 Pro; system-wide; role logic unchanged; OCR Stage 3 unaffected by this
  - OCR Stage 3 model assignment (§3.4): GPT-4o + Gemini 2.5 Pro in parallel as consensus signal providers within the AI validation line; no primary/check roles; disagreement prioritized into OCR review, no artificial winner; revisability analogous to §3.6
  - Check model correction right (four situation types)
  - No silent role swap of translation AI
  - Audit findings do not stop translation flow

**Preflight and gates:**

  - Document style template / RTL / digit placement
  - Preflight layered model
  - Document style template integrity violations resolution path and check timing
  - P-01–P-02 / P-05–P-06 occupation logic and candidate state
  - W-01 / W-02 / W-03 occupation (Minimal Model II)
  - P-03 structural role in preflight
  - Critical font availability placement
  - W-04–W-08 candidate state

**Qurʾān strand (§4.15):**

  - Qurʾān vocalization rule (sole text carrier after acceptance)
  - Qurʾān API call timing (only translation phase)
  - Qurʾān confidence protection (manual confirmation, threshold open)
  - Qurʾān project-passage protection (no silent overwriting)
  - Qurʾān passage handling: 4 action types plus auto-acceptance; decision_source mapping translation_pipeline for confirmation and for express user action to update an already stored Qurʾān passage, conflict_resolution for correction and rejection; auto-acceptance without decision_event; no new decision_source values; structurally analogous to §4.16
  - Exclusion of accepted Qurʾān passages in the translation flow (§3.6): accepted Qurʾān passages per §4.15 are managed as protected passages; what is excluded is the accepted Qurʾān passage itself, not the surrounding chunk; canonical Arabic reference text and canonical target-language translation from the carrier strands per §4.15; glossary, style profile, and RAG do not act on the protected passage; the rest of the translation flow is unaffected; no new architecture; the hadith side is not subject of this regulation

**Shamela and OCR quality principle:**

  - Shamela usage modes (Mode A = OCR Stage 3 / Mode B = lexicon workflow)
  - Shamela Lisān/Tāj as independent query units
  - OCR quality principle (no artificial winner after reconstruction stages)
  - Cleanup of Interface 1 / 2 against §3.4: AI-based validation is one of the three §3.4 Stage 3 validation lines; within the AI line the canonized rules apply (GPT-4o and Gemini 2.5 Pro as equal-rank consensus signal providers, no primary/check roles, no artificial winner on disagreement within the AI line, revisability analogous to §3.6); the OCR quality principle §3.4 takes effect when, after running through the prescribed reconstruction stages, multiple strong competing readings remain; the concrete weighting and trigger matrix between the three lines remains open

**Hadith strand (§4.16):**

  - Hadith source structure two-tier (mandatory + extended)
  - Hadith consensus logic (multidimensional + tie-breaker)
  - Kutub as-Sitta (strong weighting factor, no absolute precedence)
  - Hadith decision_event mapping (7 action types)
  - Hadith vocalization principle (separate fields, no sole text carrier)
  - Hadith source state of the extended set: E-1 Option B; E-2 Option B with identification as Alifta-/Harf variant; E-3 Option B with role of manual reference source; E-4 Option B; E-5 Option B with special role German translation source / multilingual reference source; exclusion of hadithportal.com; escalation logic in practice only E-5 effective
  - Vocalization escalation criterion: classes V-0/V-1/V-2 with aggregation and fallback rules; vokalisierungs_konflikt strictly binary (no / yes) with class differentiation only via the derived vokalisierungsklasse and ambiguity only in logging or in the conflict reasoning
  - Hadith verification status: passage types N-1 through N-10, classes H-0/H-1/H-2, resolution exclusively via the 7 action types, no audit case
  - Gate placement of hadith verification status: independent named group within the gate-check layer without new layer and without P/W slot occupation; H-2 blocking; H-1 warning-based with go_with_warning analogous to §4.9 E-1 and decision_source preflight_confirmation
  - Data model of hadith multi-source result objects: four logical levels; quellen_rolle as mandatory snapshot per single-source reading without dynamic back-derivation; entscheidungsstatus and class states derived and not persisted; satz_uuid mandatory once sentence segmentation is available; immutability analogous to §4.9 E-10; no new core objects; no new decision_source values
  - English hadith strand partial canonization R-1/R-2: English-language website translations from P-1 and E-5 as language-neutral reference and comparison field in §4.16 / §5.1.1; entries project-target-language-independent; display as comparison language in review permissible and not mandatory; no own decision_event; no effect on matn consensus, reference matn, reference vocalization, primary translation; R-3 structural decision canonized; detailed R-3 rules remain workbench

**Interface 5 structural follow-ups:**

  - A-4 HTML stripping (Model R, §5.1.1)
  - A-6 Scraping secondary path (Model D, §3.5)
  - A-7 Request profile (Model U, §3.5)
  - A-8 E-5 runtime mode (§4.16)
  - All structurally canonical; concrete values dependent on live measurement and parked

**Error and classification system:**

  - L-24 Class B general logic (§4.18): aggregated user information via dashboard status indicator on frequency per Track 2; existing special cases unaffected; concrete frequency threshold values as workbench dependent on live measurement

**Parked – Interface 5 Live Test Package:** The live- and API-test-dependent residual points are parked until real execution. Includes:

  - E-5 test operation questions F-1 / F-4 / F-9 / F-13 / F-14 / F-16
  - F-3 concrete values (rates, backoff pauses, upper limits, resumption times, frequency threshold §4.18 Track 2)
  - F-4 concrete values (timeout and retry values per source)

No silent pre-emption. No reconstruction without real measurement. The associated execution-ready test-run block (operator short version, compact return format, completion and closure matrix) is managed as a separate operative workbench/auxiliary block in Block 3 ("Interface 5 – Live Test Package (parked)") and only fed back upon real execution.

### **3.2 Class 2 – Provisional / Recommended / Pending**

#### **2A – Audit Matrix**

Baseline-based reconciled. Consistent with §4.6.

#### **2B – Style Feature Integration E-1 through E-8**

Resolved. For this working state, the designation "E-1 through E-8" is treated as the designation of the eight main sections §1–§8 of Document C v1.1. Document C v1.1 is formally confirmed as integration framework (see Class 1 entry).

The follow-up tasks named in Document C v1.1 §3 remain expressly open and are not subject of this confirmation:

  - formal integration analysis
  - CRs for Core Architecture Baseline / Engineering Execution Baseline / Delivery Backlog Baseline
  - extension of existing objects (account, decision_event, translation job/recovery, provenance/EXPORT_EVENT)
  - audit integration into A-01–D-03 structure
  - ticket definition
  - sprint planning
  - calibration of the open thresholds after gold-corpus tests
  - coding release

#### **2C – Group 3 UI Defaults**

All confirmed and incorporated.

#### **2D – Open Individual Points**

  - **L-24:** Class B general logic not canonically formulated. Separately open without priority number.
  - **Background archive list (early phase, Nos. 6–10):**
      
      - No. 8 (entity database): in today's canon functionally absorbed into the reference and entity system.
      - No. 6 (translation memory) and No. 7 (vocalization corrections): partially functionally covered, but not managed as own archive category.
      - No. 9 (hadith verification cache): not explicitly managed in today's canon, remains for now an implementation/performance question.
      - No. 10 (بلاغة learning archive): not represented in today's canon, remains a re-visit for a later style feature / coding release step.
      - scope_type enum extension (DBB substance finding Package 4): The scope_type enum value space is fixed in the current Core Architecture Baseline §B.1 with `segment, page, block, account`; the Delivery Backlog Baseline v1.0 additionally actively uses the value `project` (T-1.3.1, T-1.3.2, T-4.3.1, T-6.1.1, T-7.3.2, T-8.2.1, T-9.1.1, T-10.1.2, T-10.2.1). Both concepts are legitimate: `account` account-wide for style profiles per §4.12.2 / §5.2; `project` work-wide. Document 1 §4.11 mentions in the query rule `active_decision_event_uuids[]` only `segment` and `page` and leaves the remaining values implicit. Decided: The enum value space is extended to `segment | page | block | account | project`. This extension is a canon change to Core Architecture Baseline §B.1 and to Document 1 §4.11 (incl. query rule). It is not retro-incorporated within Package 4 but carried as confirmed finding and anchored cleanly in the closing audit (Package 7) as ALT→NEW block in CAB §B.1 and Document 1 §4.11. DBB v1.0 remains unchanged in wording; consistency with the decided end state is given.
      - No silent canon follow-up. No discard. Bound residual notice.
      - Heading 4/5/6 coverage gap (cleanup finding Document Style Templates Baseline v1.1, Chat {AKTUELLER_CHAT}): The core table of Document Style Templates Baseline v1.1 §7.2 contains for the German Heading series only Heading 1, Heading 2, and Heading 3. The TOC configuration of the same baseline expressly presupposes Heading 4 with `TOC \o "1-4"`. Document 1 §7.1 expressly names for Calibri "Heading 1–6"; Engineering Execution Baseline v1.0 §3.4 confirms Heading 1–6 as part of the critical font availability for Calibri. There is thus a substance gap between three canonical sources: Document Style Templates Baseline v1.1 §7.2 (Heading 1–3 explicit) versus Document 1 §7.1 / EEB v1.0 §3.4 (Heading 1–6) versus TOC configuration of the same Document Style Templates Baseline (Heading 1–4 presupposed). Possible resolution directions: (a) document implicit inheritance of Heading 3 for levels 4/5/6; (b) include Heading 4/5/6 as own rows in the core table; (c) resolve inconsistency between Doc. 1 §7.1 / EEB §3.4 and the Document Style Templates Baseline differently. Independent resolution in a cleanup round would be a canon change and has therefore been omitted. Resolution will be anchored cleanly in the closing audit (Package 7) as an ALT→NEW block in Document Style Templates Baseline v1.1 §7.2 and possibly in Document 1 §7.1 and EEB v1.0 §3.4. Document Style Templates Baseline v1.1, Document 1 §7.1, and EEB v1.0 §3.4 remain unchanged in wording; consistency with the decided end state is to be established.
      - No silent canon follow-up. No discard. Bound residual notice.
      - Account-scoped decision-event read path: account-scoped decision events (in particular style profile decisions with decision_source = style_management) are canonically present, but currently lack an explicit scope-separated read path in the history layer (WS-10). This gap is held as bound residual notice and will be addressed in the context of style feature follow-up work (Document C v1.1 §3 and DBB §7). No pre-emption in the current backlog. Decision-event mapping decision_source × scope_type:
      - The mapping between decision_source and permissible scope_type is not centrally defined in the current canon but distributed across multiple documents (CAB §B–§C, Document 1 §4.x, DBB T-x.x.x, OCR Export v1.3). A complete and consistent mapping table is currently not present. This gap is held as bound residual notice and requires systematic, source-supported consolidation before possible canonization. No implicit condensation or pre-emption.

#### **2E – Gate Linking P-01–P-06 / W-01–W-08**

**Canonically confirmed:**

  - Guard-near blockades before preflight: digit standard, critical RTL errors, document style template integrity violations, critical font availability.
  - Preflight layered model: configuration obligations vs. gate checks.
  - P-03: independent blocking gate, on par with P-04.
  - P-04: High audit findings.
  - W-01: Medium audit findings.
  - W-02: K-01–K-07.
  - W-03: Gradual document style template deviations.
  - Hadith verification status as independent named group within the gate-check layer (without new layer, without P/W slot occupation; H-2 blocking, H-1 warning-based).

**Still open:**

  - P-01–P-02 / P-05–P-06: no clean candidates. Slots open.
  - W-04 through W-08: no clean candidates in the existing canon. Slots open. No directional binding.

#### **2F – External Sources / Interface Working Drafts**

**OCR maximum quality logic:** Own final version of the working draft present. Full text carried as separate final version. Not yet canon. Structurally decided as working state (Block 3 Final Version 1 Point 8.2): project-wise activation with block-class-controlled depth; minimal anchoring via a project flag for the maximum mode and a provenance field for the active OCR mode per OCR run at block level, without new core object and with open final field naming; activation as log entry at project level in the project log, without decision_event per §4.10 and without new decision_source value. Work category automatic, thresholds, escalation numbers, further additional engines/providers beyond Google Cloud Vision, cost/latency limits, candidate matrix persistence form, UI display, and final field naming remain open. Google Cloud Vision (DOCUMENT_TEXT_DETECTION) is added in the canon as additional OCR reading line; the concrete primary role and weighting remain gold-corpus-dependent.

**Interface 1 – OCR main engine:** Final version of working draft present, plus sharpened additional final version in maximum mode. Full text carried as separate final version. Not yet canon.

**Interface 2 – OCR semantic supplementary validation:** Final version of working draft present, plus sharpened additional final version in maximum mode. Full text carried as separate final version. Not yet canon.

**Interface 3 – Translation AI:** Final version of working draft present. Full text carried as separate final version. Not yet canon.

**Interface 4 – Qurʾān interface:** Final version 3 (working draft, 8 points) present. Technical access specification created as separate full-text working state (Q4-1 through Q4-9). API endpoints and response format verified from public documentation. Access paths per trigger, timeout/retry, error classes, logging, versioning, and object linking refined as working draft. Critical open finding: API per documented state delivers only translations, not Arabic reference text (Variant A as working hypothesis). 10 explicit open points documented (Q4-9). Point 5 of Final Version 3 unchanged: local fallback basis = complete data state. Full text carried as separate working state. Not yet canon.

**Interface 5 – Hadith interface:**

Cleaned final version of working draft present (8 points). No silent drift.

*Canonizations:*

  - Source structure, consensus logic, Kutub as-Sitta, decision_event mapping, vocalization principle canonized. Integration blocks A-1–A-5 and B-1–B-4 incorporated.
  - Source state of the extended set consolidated (E-1, E-2, E-3, E-4 suspended; E-5 in special role), exclusion of hadithportal.com, effect on escalation logic.
  - Vocalization escalation criterion V-0/V-1/V-2 in §4.16; hadith verification status N-1 through N-10 / H-0/H-1/H-2 in §4.16; gate placement as independent named group within the gate-check layer in §4.7; data model of multi-source result objects in four logical levels with quellen_rolle as mandatory snapshot, derived states, and immutability analogous to §4.9 E-10 in §4.16 / Chapter 5.
  - Partial canonization: K-4 R-1/R-2 (English-language website translations as language-neutral reference and comparison field in §4.16 / §5.1.1).

*Status of Interface 5 overall:*

  - Source front closed.
  - Central Interface 5 semantics (vocalization escalation, verification status / preflight placement, multi-source data model) canonized.
  - English strand R-1/R-2 partially canonized.
  - Remaining technical elaboration (search modes, user logic details, traceability fine-work, K-4 R-3 of the English strand) remains working draft.

*Workbench still carried:* Nine Block 3 full-text working states for Interface 5:

1.  Technical access specification H5
2.  Pre-verification sunnah.com / dorar.net
3.  Pre-verification islamweb.net
4.  Pre-verification جَامِعُ الكُتُبِ التِّسْعَة
5.  Pre-verification مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة
6.  Identification / clarification E-2
7.  E-5 test operation
8.  English hadith strand
9.  Real Shamela actual-state survey hadith reference

The canonized partial areas vocalization escalation criterion, preflight placement of hadith verification status, and data model of multi-source result objects are no longer part of the workbench but part of the canon (§4.16 / §4.7 / §5.1.1 / §5.1.2).

*Remaining residual openness:*

  - Test operation questions on E-5 (API field structure, harakāt return, HTML markup, rate limit, versioning mechanics, bulk download field scope).
  - In β test operation, workbench partial findings on F-1 through F-16 are collected (no canon effect; see E-5 test operation work block).

*English hadith strand K-4 R-3 – differentiated workbench state:*

  - Structurally derivable from existing canon and no longer an independent workbench question:
      
      - Source citation format EN (§4.16 already canonical)
      - Transliteration (§2.2 EI2 with Q/J language-pair-independent)
      - Relationship to Interface 3 (§3.6 role logic language-pair-independent per §8 verification block entry on non-AR source language behavior; own primary production path and no-cascade rule per §4.16)
  - Genuine workbench and still blocked:
      
      - Footnote logic in the English strand (no robust basis in the current material)
      - Relationship to style feature in English output (coupled to blocked E-1–E-8 front)

*Further workbench points:*

  - Real Shamela actual-state survey (for P-2 connection, parked).
  - Operative peripheral questions (F-2 through F-6 of the residual openness matrix).
  - Live test package for F-1 / F-4 / F-9 / F-13 / F-14 / F-16 as well as concrete values for F-3 and F-4: managed as separate full-text work block "Interface 5 – Live Test Package (parked)" in Block 3; parked until real execution.

**Interface 6 – Shamela / lexicon interface:**

Final Version 5 is present as full separate full-text working state. Authoritative is the detailed version (not the more compact bundled short version). Together with the three Interface 6 work blocks (technical access layer T6-1–T6-6, verification framework A-1–A-6 / V-1–V-10, test protocol real actual-state survey Steps 1–4) and the work block playback and evaluation logic Shamela actual-state survey, Final Version 5 forms the complete current working state of Interface 6.

Status: working draft, not yet canon. No incorporation into Document 1. No silent canonization.

The real Shamela actual-state survey is parked indefinitely and will only be processed again when the user expressly takes it up again. Until then, no further substantive theory work on the Shamela access layer and no silent pre-emption of results that presuppose real verification.

**Work block – Interface 6 – Playback and evaluation logic Shamela actual-state survey:** Separate full-text working state. Status: working draft, not yet canon. Function: closes the gap between filled-in test protocol and structured return of the real actual-state survey to the working state. Defines adoption, evaluation, and follow-up path logic (R-1 through R-7). No results pre-empted. No architecture change.

**Work block – Interface 6 – Operative execution template Shamela actual-state survey:** Separate full-text working state. Status: operative auxiliary document, not canon. Contains execution instructions (Steps 1–4), survey template, and return format. No results contained.

**Work block – Technical access specification Interface 4 – Qurʾān interface:** Separate full-text working state. Status: working draft, not yet canon. API endpoints verified from public documentation. 10 open points expressly documented (Q4-9).

**Model assignment:**

  - §3.6 translation pipeline: canonically confirmed (Primary GPT-4o / Check Gemini 2.5 Pro). Provisionally canonical and revisable per §3.6 revisability clause on the appearance of newer or clearly better models (including within the same family) in a structured decision. Role logic and separation from the OCR Stage 3 assignment remain unaffected.
  - §3.4 OCR Stage 3: canonically confirmed (GPT-4o + Gemini 2.5 Pro in parallel as consensus signal providers within the AI validation line; no primary/check roles; disagreement prioritizes the passage into OCR review, no artificial winner). Provisionally canonical and revisable analogous to §3.6 in case of newer or clearly better models (including within the same family) in a structured decision; no silent model-switching change. Revision concerns exclusively the model choice, not the consensus architecture.

**Interface 7 and further:** not yet started.

**All external sources individually** (endpoints, auth, rate limits, error behavior, scraping): unspecified – active work front.

#### **2G – Interface 6 – Stabilized Analysis Levels State**

Three levels before the lexical footnote entry:

**Level 1 – Morphological short analysis:** Compact word identification (word, root, part of speech, wazn, short meaning). No project effect. Short meaning is pure user orientation, not part of the search logic.

**Level 2 – Lexicon state:**

  - Arabic original excerpt always visible.
  - Hits per source separately (Lisān / Tāj).
  - Optional German working aid (AI-generated, clearly marked).
  - Three-stage classification:
      
      - lexically backed
      - indirectly backed
      - manual without robust lexicon backing
  - Search-path transparency with indirect evidence.

**Source basis selection (intermediate step before Level 3):**

  - Options: only Lisān / only Tāj / both / own manual synthesis.
  - Mandatory when both sources have hits.
  - With hit in only one source: source basis selection omitted; the relevant source is the sole available source basis.

**Level 3 – Footnote generator:**

  - Predefined or user-defined style.
  - On confirmation: footnote is created and registry entry in category "Lexical entries" automatically generated.
  - Additional question "Also earmark as terminology rule?" (optional).
  - Source backing level as metadata on each footnote.

#### **2H – Interface 6 – Access and Search Logic**

Cleaned provisional final version present. Detailed full text is present as separate Final Version 5 and is carried as independent full-text working state.

**Core decisions of this work block:**

  - Shamela entire collection = escalation search space, not third equivalent lexicon source.
  - Three-stage search run:
      
      - Stage 1: exact
      - Stage 2: extended
      - Stage 3a: coarser lexicon search
      - Stage 3b: escalation Shamela entire collection
  - Stage 3b is triggered only on explicit user request (Variant B). Later hybrid logic (Variant C) remains as possible refinement open.
  - Qualitative test logic for "robust" anchored as structured guideline ordering (5 dimensions: source type, form proximity, meaning proximity, support breadth, with Shamela additionally work authority).
  - Optional morphological-contextual footnote draft as fallback when lexicon hit is missing – clearly marked as working hypothesis, only on user request, no equivalence to lexical backing.
  - Delineation fallback vs. §4.17: separate strands for this working state; overlap with technical terms without hits expressly named; combination/priority rule deliberately kept open.
  - Shamela two usage modes: Mode A (OCR-near, system-triggered), Mode B (user-driven, lexicon workflow).

Status: working draft, not yet canon. No incorporation into Document 1.

#### **2I – Word Analysis Panel – Work Strand (separate from interfaces)**

  - Large word panel draft present (3 panel types: Noun / Verb / Particle; 4 analysis layers). Not canon.
  - **Noun panel:** stabilized working draft, provisionally parked. Replacement candidate for §4.17. Direction decisions provisionally adopted:
      
    1.  Replacement instead of supplement of §4.17.
    2.  Side panel remains.
    3.  Word form frequency analysis remains separate modal dialog.
    4.  Uncertainty logic harmonized with existing thresholds (> 85% / 50–85% / < 50%).
    5.  §4.17 fields = minimal core; deep fields context-/type-dependent.
  - Three refinements incorporated:
      
    1.  Root as mandatory field in the header area; Block 4 only for deep derivation.
    2.  Block 2 with primary and secondary classifications.
    3.  Compatibility table restricted to nouns.
  - **Verb panel / particle panel:** not yet further developed. Follow the same structural principle.

#### **2J – Style Feature Integration Notice Document C v1.1**

Document C v1.1 §1–§8 formally confirmed as integration framework:

  - Placement in Waraq canon (§1).
  - Confirmation of non-overriding of existing system rules including subordination of manual style rules (§2 with [CANON] markers §2.1 and §2.2).
  - Canonical / configurable / calibratable – overall overview (§4).
  - Conflict exclusion list (§5).
  - Account binding principle with [CANON] marker §6.1 (§6).
  - Order of follow-up steps orienting (§7.3).

No baseline shift, no implementation release, no new architecture. No change to Document 1; the three [CANON]-marked principles are already anchored in Document 1 §4.12 (style feature priority logic) and §5.2 (account binding).

The follow-up tasks named in Document C v1.1 §3 (formal integration analysis §3.1, CRs §3.2, new core object integration into baselines §3.3, audit integration §3.4) remain expressly open and are not silently pre-empted.

## **4. NEXT WORK FRONT**

### **4.1 Priority 1 – Fully Specify External Sources**

  - Interface working drafts 1–6 present (full texts carried as separate final versions).
  - OCR maximum quality logic present as own final version.

**Interface 4:** Technical access specification created as working draft (Q4-1 through Q4-9). Critical open finding (Arabic reference text via API) documented. 10 open points expressly named.

**Interface 6:** Final Version 5 is present as full full-text working state. Together with the three Interface 6 work blocks (technical access layer, verification framework, test protocol), the work block playback/evaluation logic, and the operative execution template, it forms the complete current working state of Interface 6.

**Real Shamela actual-state survey for Interface 6:** parked. No active next operative step. Will only be processed again when the user expressly takes it up again. As long as the actual-state survey is parked, the following applies:

  - no further substantive theory work on the Shamela access layer
  - no playback / evaluation R-1 through R-7
  - no hadith-related P-2 reconciliation

The Stage S-1 expectation for P-2 remains expressly working hypothesis and is not silently promoted.

**Interface 5 – Status:**

  - Source front closed. Mandatory set P-1/P-2/P-3 unchanged.
  - Extended set canonically consolidated (E-1/E-2/E-3/E-4 Option B suspended; E-2 highly reliably identified as Alifta-/Harf variant; E-3 only as a possible manual reference source; E-5 Option B not suspended in special role "German translation source / multilingual reference source"). hadithportal.com expressly excluded.
  - Structural follow-ups A-4 / A-6 / A-7 / A-8 canonized.
  - Live/API-test-dependent residual points (E-5 test operation questions F-1 / F-4 / F-9 / F-13 / F-14 / F-16; F-3 concrete values; F-4 concrete values) parked until real execution; associated execution-ready test-run block managed as separate operative full-text work block "Interface 5 – Live Test Package (parked)" in Block 3.
  - Vocalization escalation criterion, preflight placement of hadith verification status, and data model of multi-source result objects remain canonized.
  - Partial canonization K-4 R-1/R-2 remains canonized.

**K-4 R-3 differentiated:**

  - Cleanly derivable from the existing canon and no longer managed as independent workbench questions: source citation format EN, transliteration, relationship to Interface 3 (own primary production path from the Arabic matn, structurally equivalent to the German path, no-cascade rule, §3.6 role logic language-pair-independent).
  - Workbench, not silently followed up: footnote logic in the English strand and relationship to style feature in English output. Resumption of these two partial points requires a robust basis for the English footnote convention or the wording of Document C v1.1 for the style-feature relationship.
  - The concrete English Qurʾān translation at the translation-key level (§4.15) remains parked unaffected by this.

**Real Shamela actual-state survey for P-2:** parked. The hadith-related P-2 reconciliation remains parked and follows temporally the resumption of the real actual-state survey.

**Conclusion:** No active open Interface 5 work front with the currently available material.

### **4.2 Priority 2 – Completed**

The formal confirmation of the Style Feature Integration Notice Document C v1.1 (§1–§8) is completed (see §3 Class 1, entry 2J). The §3 follow-up tasks from Document C v1.1 remain expressly open and are not pulled without an explicit user assignment.

### **4.3 Parked (No Active Expansion)**

  - **Word panel strand:** Noun panel stabilized and parked. Verb/particle panel only after resumption.
  - **Real Shamela actual-state survey Interface 6 incl. playback/evaluation R-1 through R-7 and hadith-related P-2 reconciliation:** parked. Will only be processed again when the user expressly takes it up again. No silent pre-emption of real results. Stage S-1 expectation for P-2 remains working hypothesis. The consolidation state of the extended set remains unaffected by later real results, as long as no express resumption occurs.
  - **Interface 5 – Live Test Package** (E-5 test operation questions F-1 / F-4 / F-9 / F-13 / F-14 / F-16; F-3 concrete values; F-4 concrete values): parked until real execution; managed as separate full-text work block "Interface 5 – Live Test Package (parked)" in Block 3. Will only be processed again once a filled-in return format from real measurement is available.
  - **L-24 frequency threshold values Class B general logic:** structural mechanism canonical in §4.18; concrete threshold values coupled to the live test package (F-3 frequency threshold §4.18 Track 2) and remain parked until real measurement.

### **4.4 Separately Open (Without Priority Number)**

  - L-24 concrete frequency threshold values of the Class B general logic: still open, dependent on live measurement and coupled to the parked Interface 5 live test package. The structural mechanism of the Class B general logic is canonical in §4.18: aggregated user information via dashboard status indicator on frequency per Track 2; existing special cases remain unaffected. Do not merge with the API failure special case.

## **5. LATER IDEAS / LATER POSSIBLE FEATURES**

  - Adobe InDesign / Affinity Publisher export.
  - Further languages (French, Turkish) and source languages (Persian, Ottoman).
  - Plugin system.
  - Upload own Word document as export target.
  - Enterprise contracts with OpenAI / Google.
  - Further layout templates.
  - Collaboration / comment system.
  - Automated error resolution process (basic structure decided, details open).

## **6. THINGS NOT YET PERMITTED**

  - No code without explicit coding release.
  - No silent architectural changes.
  - No new sprint planning without explicit assignment.
  - No new features without complete CR pass.
  - No silent re-baselining.
  - No reformulation of the existing canon.
  - OCR export strand remains separated from style feature.
  - No coding release before external sources are fully specified.
  - Do not merge word panel strand with interface strand.

## **7. PERSONAL PROFILE OF THE USER**

  - Professional translator of Arabic Islamic works into German.
  - Translates primarily classical Islamic literature, Fiqh texts, historical manuscripts.
  - Deep expertise in Arabic language, Islamic sciences, and translation.
  - Based in Medina (Saudi Arabia).
  - Thinks very structuredly and precisely – expects the same.
  - Expects proactive quality thinking – never wait until asked.
  - Gives clear corrections – accept directly without excessive apology.
  - Speaks German (Swiss style: "ss" instead of "ß").
  - Works iteratively: define → check → release → continue.

## **8. VERIFICATION BLOCK FOR NEW CHAT**

**Style feature priority logic?** Tier 1: System rules. Tier 2: User style (Document A + Document B v1.2). Tier 3: Reference sentences.

**T-7.3.1 / T-7.3.2?** Baseline-side fully defined (Delivery Backlog Baseline v1.0). Sprint placement deliberately conditional (T-7.3.1 optional in Sprint 2, T-7.3.2 conditional in Sprint 3 if T-7.3.1 present). No implementation release.

**E-1 through E-8 style feature?** Resolved. For this working state, the designation "E-1 through E-8" is treated as the designation of the eight main sections §1–§8 of Document C v1.1. Document C v1.1 formally confirmed as integration framework. §3 follow-up tasks (integration analysis, CRs, ticket definition, sprint planning, audit integration, calibration, coding release) remain expressly open. No change to Document 1.

**OCR export vs. style feature?** Absolutely separated.

**Without coding release?** No code, no implementation.

**Document style template source file?** FINAL.docx – all values in Baseline v1.1 canonical.

**Largest open gap before code?** External sources not specified. Interface working drafts 1–6 present (full texts carried as separate final versions), not yet canon.

**Audit matrix status?** Baseline-based reconciled. P-03 and P-04 canonically confirmed.

**Style profile shareable?** No. Absolutely account-bound.

**L-24 status?** Structurally canonized in §4.18 (aggregated user information via dashboard status indicator on frequency per Track 2; special cases unaffected). Concrete frequency threshold values dependent on live measurement; coupled to the parked live test package.

**Translation pipeline model assignment?** Canonically confirmed for §3.6: Primary GPT-4o, Check Gemini 2.5 Pro. System-wide. Role logic unchanged. Provisionally canonical, revisable in a structured decision in case of newer or clearly better models (including within the same family); no silent model-switching change.

**OCR Stage 3 (§3.4 semantic reconstruction) model assignment?** Canonically confirmed: GPT-4o + Gemini 2.5 Pro in parallel as consensus signal providers within the AI validation line. No primary/check roles. Disagreement of both models does not act as artificial winner but lowers confidence and prioritizes the passage into OCR review per the §3.4 quality principle. Provisionally canonical, revisable analogous to §3.6 in a structured decision in case of newer or clearly better models (including within the same family); no silent model-switching change. Revision concerns exclusively the model choice, not the consensus architecture.

**Qurʾān passage handling?** Canonized in §4.15. Four action types plus auto-acceptance. decision_source translation_pipeline on confirmation and on express user action to update an already stored Qurʾān passage; conflict_resolution on correction and rejection. Auto-acceptance without decision_event. No new decision_source values.

**Translation AI – exclusion of accepted Qurʾān passages?** Accepted Qurʾān passages per §4.15 are managed as protected passages. What is excluded is the accepted Qurʾān passage itself, not the surrounding chunk. Canonical Arabic reference text and canonical target-language translation come from the carrier strands per §4.15. Glossary, style profile, and RAG do not act on the protected passage. The rest of the translation flow is unaffected. The hadith side is not subject of this regulation.

**Interface 1 / 2 – cleanup against §3.4?** AI-based validation is one of the three §3.4 Stage 3 validation lines. Within the AI line: GPT-4o and Gemini 2.5 Pro as equal-rank consensus signal providers, no primary/check roles, no artificial winner on disagreement within the AI line, revisability analogous to §3.6. OCR quality principle §3.4 takes effect with multiple strong competing readings after running through the reconstruction stages. Concrete weighting and trigger matrix between the three lines open.

**Preflight layers?** Configuration obligations (4 mandatory questions) and gate checks conceptually separated.

**P-03 status?** Independent blocking gate, on par with P-04. Confirmed.

**W-01 / W-02 / W-03?** Minimal Model II confirmed. W-01 = Medium audit findings. W-02 = K-01–K-07. W-03 = Gradual document style template deviations.

**W-04 through W-08?** Open. No clean candidates in the existing canon. No directional binding.

**P-01–P-02 / P-05–P-06?** Occupation logic confirmed. No clean candidates. Slots open.

**Critical font availability?** Canonically confirmed as guard-near before preflight dialog. No P-slot occupied.

**Interface working drafts?** 1 (OCR main engine), 2 (OCR semantic supplementary validation), 3 (translation AI), 4 (Qurʾān), 5 (hadith), 6 (Shamela/lexicon) – all present as working drafts, full texts carried as separate final versions, not yet canon. OCR maximum quality logic present as own final version. Google Cloud Vision (DOCUMENT_TEXT_DETECTION) added in the canon as additional OCR reading line; the concrete primary role and weighting remain gold-corpus-dependent. Technical access specification Interface 4 present as separate full-text working state.

**Interface 4 special?** Point 5 refined: local fallback basis = complete Qurʾān data state. Technical access specification (Q4-1 through Q4-9) present as working draft. Critical open finding: API delivers only translations, not Arabic reference text (Variant A as working hypothesis). 10 open points documented.

**Interface 5 – canonization state?** Source front closed. Five partial areas from the hadith integration canonized. Mandatory set P-1/P-2/P-3 unchanged. Extended set canonized: E-1, E-2 (highly reliably identified as Alifta-/Harf variant), E-3 (only manual reference source), E-4 each per Option B documented, factually suspended. E-5 per Option B not suspended, in special role "German translation source / multilingual reference source" (no corpus replacement source, no API full-text search path, connection via official API and official bulk downloads). hadithportal.com expressly excluded. Canonized: vocalization escalation criterion V-0/V-1/V-2; hadith verification status N-1 through N-10 / H-0/H-1/H-2; gate placement of hadith verification status as independent named group within the gate-check layer; data model of multi-source result objects in four logical levels. Partially canonized: K-4 R-1/R-2 (English-language website translations as language-neutral reference and comparison field). Nine Block 3 full texts still carried as workbench. Open in particular: test operation questions on E-5, English strand K-4 R-3, remaining operative peripheral questions, real Shamela actual-state survey (from Interface 6, parked).

**Next work step?** Condensation and conclusion of the remaining genuine residual openness Interface 5 (E-5 test operation questions, English hadith strand K-4 R-3, remaining operative peripheral questions). Real Shamela actual-state survey, playback R-1 through R-7, and hadith-related P-2 reconciliation are parked and not part of the active work front.

**Working drafts present?** Yes – full texts carried as separate Final Versions 1–5. Additionally:

  - Five Interface 6 work blocks (technical access layer, verification framework, test protocol, playback/evaluation logic, operative execution template).
  - One Interface 4 work block (technical access specification Q4-1 through Q4-9).
  - Nine Interface 5 work blocks (technical access specification hadith, pre-verification sunnah.com / dorar.net, pre-verification islamweb.net, pre-verification جَامِعُ الكُتُبِ التِّسْعَة, pre-verification مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة, identification/clarification E-2, E-5 test operation, English hadith strand, real Shamela actual-state survey hadith reference).

The H5 working state contains the cleaned incorporation of the sunnah/dorar findings. islamweb, الوقفية, E-4, and E-2 are managed separately as documented suspension findings; E-5 is managed separately as non-suspended special role. Not merely referenced.

**Interface 6 – current state?**

  - Analysis level (3 levels + source basis selection) stabilized.
  - Access/search logic completed as cleaned provisional final version (detailed version authoritative).
  - Final Version 5 present as full full-text working state.
  - Three Interface 6 work blocks (technical access layer, verification framework, test protocol), work block playback/evaluation logic, and operative execution template carried as further full-text working states.
  - Interface 6 as working state complete.
  - Real Shamela actual-state survey parked; will only be processed again when the user expressly takes it up again.
  - Playback R-1 through R-7 and hadith-related P-2 reconciliation thus also parked.
  - Still working draft, not yet canon.

**Word panel strand?** Own work strand, separate from interfaces. Noun panel stabilized, parked, replacement candidate for §4.17. Verb/particle panel not yet developed.

**Hadith integration blocks?** Incorporated. Completed.

**Check model correction right?** Four situation types. Objective deterministic → auto-correction (logged). Interpretive → confidence drops, review. Ambiguity → user notice. Model assignment open.

**Silent role swap of translation AI?** Forbidden. Primary fails → chunk waits. Check fails → primary continues, affected passages count as not cross-checked.

**Audit findings in translation flow?** Do not stop the flow. Are persisted and carried forward in preflight.

**Qurʾān vocalization after recognition?** Separate carrier structure. Arabic Qurʾān reference collection = sole text carrier for Arabic reference text and vocalization; independent local collection, independent of the translation fallback copies; at no point API-supported. quranenc.com (or local fallback copy of the german_rwwad translation on API failure) = sole text carrier for the German translation. No choice case. Only the recognition question is verifiable. Concrete source designation of the AR reference collection and its update mechanism still open (Interface 4 detail points).

**Qurʾān API call when?** Only in translation phase. No external call in the OCR run.

**Qurʾān confidence below threshold?** Manual confirmation upstream. Threshold open.

**Qurʾān project passages on update of the local copy?** Remain unchanged. No silent overwriting.

**Shamela modes?** Mode A = OCR-internal (Stage 3). Mode B = user-driven, lexicon workflow in translation phase.

**Shamela Lisān/Tāj?** Independently queryable units within Shamela.

**OCR unresolved ambiguity?** No artificial winner after running through the prescribed reconstruction stages. Confidence drops, review prioritized.

**Hadith source structure?** Two-tier: mandatory (sunnah.com, Shamela, dorar.net) + extended (E-1 islamweb.net, E-2 جَامِعُ السُّنَّةِ النَّبَوِيَّة highly reliably identified as Alifta-/Harf variant, E-3 المكتبة الوقفية as deliberate escalation source, E-4 جَامِعُ الكُتُبِ التِّسْعَة, E-5 مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة). Consolidation state of the extended hadith source set: E-1, E-2, E-3, E-4 per Option B documented, factually suspended; E-3 only as a possible manual reference source. E-5 per Option B not suspended, in special role "German translation source / multilingual reference source" (no corpus replacement source, no API full-text search path, connection via official API and official bulk downloads). hadithportal.com expressly excluded. Escalation logic: on automatic activation, in practice only E-5 effective.

**Hadith consensus logic?** Multidimensional. Linear ranking as tie-breaker.

**Kutub as-Sitta?** Strong weighting factor, no absolute precedence.

**Hadith decision_events?** 7 action types → translation_pipeline (2) + conflict_resolution (5).

**Hadith vocalization?** Separate fields, no sole text carrier. Conflicts → user → conflict_resolution.

**Vocalization escalation criterion?** Canonized. Classes V-0 (automatically tolerable), V-1 (logging-mandatory, no escalation), V-2 (escalation-mandatory). Aggregation rule highest class wins; fallback rule in doubt V-2. Field vokalisierungs_konflikt strictly binary (no / yes); class differentiation exclusively via the derived vokalisierungsklasse. With unclear type assignment the field remains yes; ambiguity is documented only in logging or in the conflict reasoning.

**Hadith verification status?** Canonized. Passage types N-1 through N-10. Verification classes H-0 (review-internally tolerable), H-1 (logging-mandatory, warning-capable), H-2 (export-blocking until resolution). Resolution exclusively via the 7 canonized action types. No audit case. Marking "for later clarification" does not lift H-2.

**Gate placement of hadith verification status?** Canonized. Independent named group within the existing gate-check layer per §4.7. No new layer. No occupation of open P/W slots. H-2 blocking; H-1 warning-based with go_with_warning analogous to §4.9 E-1, decision_source preflight_confirmation.

**Data model of hadith multi-source result objects?** Canonized. Four levels (passage anchor / single-source reading / aggregated overall result / user decision overlay). quellen_rolle is mandatory snapshot field per single-source reading (pflicht / erweitert_aktiv / erweitert_sonderrolle / erweitert_suspendiert), fixed at the time of the verification run, no dynamic back-derivation. Derived, not persisted: entscheidungsstatus, vokalisierungsklasse, hadith_stellen_typ, hadith_verifikationsklasse. satz_uuid is mandatory once sentence segmentation is available for the passage. Immutability analogous to §4.9 E-10. No new core objects. No new decision_source values.

**English hadith strand?** Partially canonized (K-4 R-1/R-2): English-language website translations from P-1 and E-5 as language-neutral reference and comparison field in §4.16 / §5.1.1. Entries project-target-language-independent. Display as comparison language in review permissible, not mandatory, no own decision_event. No effect on matn consensus, reference matn, reference vocalization, primary translation. Structural decision K-4 R-3 canonized: English hadith output as own primary production path from the Arabic matn, parallel and structurally equivalent to the German hadith output; no-cascade rule for the hadith matn translation. Detailed R-3 rules (source citation format, transliteration, footnote logic, relationship to style feature and Interface 3) remain workbench.

**E-5 test operation?** Workbench. β partial findings present (F-1 through F-16); not canon.

  - Verified in β: F-1 for AR and EN (DE unclear due to tool limit), F-2 (harakāt complete in AR API), F-3 (no HTML in JSON text fields), F-8 (68 languages).
  - Partially verified in β: F-6, F-7, F-12, F-15.
  - Time-dependent open: F-4, F-5, F-9, F-14, F-16.
  - No β statement on F-10, F-11.

**Non-AR source language behavior of translation AI?** §3.6 role logic applies language-pair-independently for EN→DE and DE→EN. The §4.15 exclusion of accepted Qurʾān passages is bound to the accepted Qurʾān recognition, not to the source language; it takes effect also with EN→DE and DE→EN when an accepted Qurʾān recognition is present at the passage. For DE→EN, the concrete English target-language carrier at the translation-key level per §4.15 remains open. Hadith side with non-AR source languages and K-4 R-3 remain outside this placement.

**English hadith strand K-4 R-3?** Differentiated workbench state. Structurally derivable from existing canon: source citation format EN (§4.16), transliteration EI2 with Q/J (§2.2, language-pair-independent), relationship to Interface 3 (own primary production path per §4.16, §3.6 role logic language-pair-independent per previous §8 entry). Still workbench: relationship to style feature in English output (coupled to E-1–E-8). The footnote logic of the English hadith strand is per §4.16 structurally aligned to the German logic; concrete English marker abbreviations are expressly not fixed there. No change to Document 1. The English target-language carrier of the Qurʾān translation at the translation-key level is per §4.15 set as english_rwwad; local fallback copy analogous to german_rwwad. Option A (AI translation per defined system style) applies system-side equally for German and English. Option B (style feature) is in the canonical specification state elaborated for the existing AR→DE style feature strand (Document B v1.2). The relationship style feature ↔ English output remains a later own follow-up in the context of the §3 follow-up tasks Document C v1.1 and is not silently pre-empted today.

## **VERSION STATE**

**Status:** Working and reference document – cleaned full-text version. Document 1 remains unchanged as sole canonical primary source.

**Canonization state:**

  - Canonized partial areas of Interface 5 are part of the canon and no longer part of the open work front: vocalization escalation criterion V-0/V-1/V-2; hadith verification status N-1 through N-10 / H-0/H-1/H-2; gate placement as independent named group within the gate-check layer without new layer and without P/W slot occupation; data model of multi-source result objects in four logical levels.
  - Partially canonized: K-4 R-1/R-2 (English-language website translations as language-neutral reference and comparison field in §4.16 / §5.1.1).
  - Interface 6 present as full working state.

**Parked:**

  - Real Shamela actual-state survey: will only be processed again when the user expressly takes it up again.
  - Playback R-1 through R-7 and hadith-related P-2 reconciliation.
  - Stage S-1 expectation for P-2 remains working hypothesis and is not silently promoted.

**Next substantive work area** (not active next operative step without express user assignment):

  - E-5 test operation questions
  - English hadith strand K-4 R-3
  - Remaining operative peripheral questions Interface 5

**Protective rule:** Real results from Interface 6 may not silently change the consolidation state of the extended hadith source set. Still working draft, not yet canon, insofar as not expressly canonized. No silent canonization. No silent re-baselining.
