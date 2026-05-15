# **BLOCK 3 – SEPARATE FULL-TEXT WORKING STATES**

Cleaned full-text version.

**IMPORTANT:** These working states are not reference notes. They are real, carried-forward full texts and must be treated as such.

## **FINAL VERSION 1 – OCR MAXIMUM QUALITY LOGIC**

including the tightened addendum final versions for Interface 1 and Interface 2

**Status:** Working draft. Not yet canon. Not incorporated into Document 1 or Document 2. No code. No CRs. No silent architectural changes.

### **Point 1 – Goal and Position in the Overall System**

The OCR maximum quality logic is not a replacement for the existing OCR pipeline, but its uncompromising quality tightening.

It builds on the existing Waraq canon:

  - OCR is established as a 5-stage reconstruction pipeline.
  - The existing engine combination is already in place:
  - Gemini 2.5 Pro Vision
  - Google Cloud Vision (DOCUMENT\_TEXT\_DETECTION) as additional OCR reading line
  - kraken / eScriptorium
  - Real-ESRGAN + OpenCV
  - CAMeL Tools / Farasa / Mishkal
  - LayoutParser / DocTR
  - OCR is processed block by block; the page is the checkpoint unit.
  - OCR review, difficulty report, and DPI comparison view are already provided.

**New guiding rule of this working draft:** Waraq does not treat OCR as "read once and output," but as a multi-stage inspection and consensus system that exhausts all available means to produce the best possible OCR text.

**Primary goal:**

  - maximally correct characters
  - maximally correct word boundaries
  - maximally correct reading direction
  - maximally correct ḥarakāt and special characters, where present
  - maximum reliability for Qurʾān, hadith, name, isnād, and specialized passages

**Secondary goal:**

  - never conceal uncertainty
  - intelligently prioritize weak spots
  - enforce review only where the machine, despite maximum inspection, cannot produce a robust winner

### **Point 2 – Multi-Pass Preprocessing Instead of One-Pass Render**

Each OCR-relevant page is processed not in just one image version but in multiple technical versions.

**2.1 Standard variants per page**

  - original render
  - higher-DPI render
  - contrast-enhanced variant
  - denoised variant
  - deskewed variant
  - dewarped / undistorted variant
  - binarized variant
  - color-preserving variant

**2.2 Goal of multi-pass preprocessing** Different OCR engines react differently to low print quality, skew, edge distortion, fine ḥarakāt, tightly set footnotes, multi-column layouts, historical print images, and manuscript/calligraphy components. For this reason the same block is read in several technically different source images.

**2.3 Working rule** No preprocessing variant automatically counts as "the best." Preprocessing is a generation space for multiple OCR paths, not a silent one-time fix.

### **Point 3 – Hard Layout and Block Logic Before Every OCR**

**3.1 Mandatory segments:** main text, heading, subheading, footnote, marginal note, table/list area, Qurʾān block, hadith block, page number/column header, ornament/decorative element/separator line.

**3.2 Reading direction and block order:** Hard pre-check for: column structure, order of blocks, line direction, reading-direction map, baseline position, margin zones, indentation and footnote reference.

**3.3 Goal:** OCR must not be unleashed directly on the entire page, but only on structured blocks with known function.

### **Point 4 – Multi-Engine Committee Instead of Single Engine**

**4.1 Principle:** No block in maximum mode should depend on only one OCR engine. Instead, a committee of engines is deployed per block.

**4.2 Core roles of the engines:**

  - **A – Standard / print-scan reading lines:** Gemini 2.5 Pro Vision and Google Cloud Vision (DOCUMENT\_TEXT\_DETECTION). For modern printed Arabic scans, Google Cloud Vision can be used as base or primary reader, provided gold-corpus tests confirm this.
  - **B – Special-case / manuscript reader:** kraken / eScriptorium for manuscripts, calligraphy, difficult historical blocks
  - **C – Layout / detection support:** LayoutParser / DocTR for block localization and structure
  - **D – Linguistic / plausibility support:** CAMeL Tools / Farasa / Mishkal in semantic reconstruction

**4.3 Maximum extension:** In maximum mode a block is read independently by several readers. Minimum conceivable roles: visual primary reader, secondary reader, special-case reader, arbitration reader, language checker, corpus checker.

**4.4 No blind majority rule:** "2 vs. 1" alone does not decide. The engine majority is only a signal, not automatically the winner. Within the AI validation line per §3.4 stage 3, GPT-4o and Gemini 2.5 Pro are equal-ranked consensus signalers per the canonical model assignment §3.4; no primary/check roles within the AI line. Revisability of the concrete model choice analogous to §3.6. The OCR quality principle (no artificial winner, confidence drops, review prioritized) takes effect as canonically per §3.4 when, after running through the prescribed reconstruction stages, several strong competing readings remain. The concrete weighting and triggering matrix between the three §3.4-stage-3 validation lines (rule-based, AI-based, statistical) remains open.

### **Point 5 – Consensus, Inspection, and Escalation Logic**

**5.1 Basic principle:** Not the first reading wins, but the most robust reading after several inspection levels.

**5.2 Four consensus levels:**

  - **Level A – Surface consensus:** Comparison by character sequence, word boundaries, line structure, agreement among multiple renders/engines.
  - **Level B – Layout consensus:** Does the reading fit the block class, line length, column/footnote structure, context of neighboring lines?
  - **Level C – Language consensus:** Morphologically plausible Arabic? Obvious non-words? Impossible inflection? Suspicious homoglyph errors?
  - **Level D – Knowledge consensus:** Check against Qurʾān, hadith, Shamela, later lexica/terminology, known religious formulas.

**5.3 Special rule for semantically sensitive blocks:** Qurʾān, hadith, isnād, name, and lexically sensitive blocks are inspected more strictly than ordinary running text.

**5.4 No silent pseudo-victory:** If several strong competing readings remain: confidence down, review relevance up, prioritize the passage.

### **Point 6 – Escalation Loops for High-Risk Blocks**

**6.1 When escalation occurs:** Several engines contradict each other, confidence too low, block class = Qurʾān/hadith/isnād/manuscript/footnote-fineprint, layout unstable, language check reports improbabilities, corpus comparison contradicts main reading, OCR error class points to high risk.

**6.2 Escalation measures:** Re-cropping, re-reading at multiple zoom levels, alternative preprocessing variants, including surrounding lines, re-checking block class, switching in special engine, switching in LLM arbitration, additional corpus comparisons, generating variant matrix.

**6.3 Guiding rule:** In maximum mode, effort is not a counter-argument as long as it raises OCR quality.

**6.4 Practical safeguard:** Block escalates, page remains checkpoint, the overall job does not stop automatically.

### **Point 7 – Quality Metrics, Review, and User Experience**

**7.1 No single confidence number:** Quality separated by character stability, word stability, line stability, block stability, layout consistency, language plausibility, corpus proximity, special-block reliability (Qurʾān/hadith/isnād), degree of technical degradation.

**7.2 User interface:** Live the user continues to see only intelligible page states, not raw OCR internal logic.

**7.3 OCR review:** First to the top: unresolved Qurʾān conflicts, unresolved hadith conflicts, blocks with high engine divergence, blocks with low corpus plausibility, footnote/fineprint high-risk, reading-direction/column conflicts.

**7.4 What the user sees at difficult passages:** original block/crop, strongest reading, alternative reading(s), intelligible reason for uncertainty, optional Qurʾān/hadith/Shamela hint, why the passage was prioritized.

### **Point 8 – Persistence, Traceability, and Open Items**

**8.1 What should be persisted internally:** preprocessing variant(s) used, chosen block class, active OCR paths/engines, technical failures/degradations, candidate readings, decision-bearing path, reasons for escalation, reasons for review marking, corpus-supported conflicts/confirmations, page/block prioritization.

**8.2 Structurally decided (working state, not canon):**

*Activation level:* project-wise activation of the engine committee on blocks by the user; within an activated project, the block class controls the concrete inspection depth per Interface 1 Point 3. Global and pure block-wise activation discarded. Work-category automatic intentionally kept open, not silently introduced.

*Data-model / persistence anchoring:* project flag for maximum mode at project level; provenance field for the active OCR mode (standard / maximum) per OCR run at block level. No new core object. The final field naming remains open.

*Activation logging:* log entry at project level in the project log. No decision\_event per §4.10. No new decision\_source values.

**8.3 Still open** Exact maximum number of escalation runs, hard threshold values standard/maximum mode, additional further engines/providers beyond Google Cloud Vision, cost/latency limits, exact persistence form of the candidate matrix, automatic activation by work category, exact UI presentation of alternative readings, final field naming in the data model. The concrete primary role and weighting of Google Cloud Vision remains gold-corpus-dependent.

### **Interface 1 – OCR Main Engine (Tightened Addendum Final Version Maximum Mode)**

**Status:** This addendum final version does not replace the existing final version of Interface 1, but tightens it for OCR maximum mode.

**Point 1 – Trigger:** OCR main engine remains responsible after upload for all OCR-required file types. In maximum mode, multi-pass preprocessing space per page is generated (original render, higher DPI, contrast-enhanced, denoised, deskewed, dewarped, binarized, color-preserving).

**Point 2 – Access type:** In maximum mode extended to engine committee at block level: preprocessing local, layout/detection local, external OCR reading lines (Gemini 2.5 Pro Vision and Google Cloud Vision DOCUMENT\_TEXT\_DETECTION), special-case readers local, additional counter-readers/checkers depending on block class, semantic add-on validation in Interface 2. For modern printed Arabic scans, Google Cloud Vision can be used as base or primary reader, provided gold-corpus tests confirm this. The AI validation line within stage 3 follows the canonical model assignment §3.4 (GPT-4o + Gemini 2.5 Pro in parallel as equal-ranked consensus signalers within the AI line, no primary/check roles, revisability analogous to §3.6).

**Point 3 – Order / priority:** Block class governs the multi-reading requirement:

  - **Standard** book text / modern printed Arabic scans → Google Cloud Vision and/or Gemini 2.5 Pro Vision as base/main reading line plus counter-reader according to confidence situation,
  - footnotes → additional zoom/render variants,
  - Qurʾān/hadith/isnād → strict multi-inspection,
  - manuscript → kraken/eScriptorium as special-case reader,
  - layout-unstable → additional order check.

**Point 4 – Timeout / retry:** Technical retry (API error, module failure) vs. qualitative escalation (engine contradiction, instability, high-risk block). Both clearly separated.

**Point 5 – Fallback:** No silent professional engine swap, no silent role swap, no pseudo-confidence. Three groups:

  - A: Single path fails.
  - B: Main reader present, but contradiction high.
  - C: No robust agreement → review prioritized, no artificial winner.

**Point 6 – UI visibility:** Live: processed / pending / problematic. In OCR review: intelligently prioritized by Qurʾān conflicts, hadith conflicts, engine divergence, language/corpus plausibility, layout instability, footnote risk.

**Point 7 – Logging:** Extended by: preprocessing variants, block class, active OCR reading lines (including Gemini 2.5 Pro Vision and/or Google Cloud Vision, where used), active readers/counter-readers, escalation reasons, degradation markers, alternative candidate readings, decision-bearing path, prioritization reason.

**Point 8 – Flow rule:** Block may pass through many internal inspections. Page remains checkpoint. Overall job does not stop. Problematic blocks escalated and prioritized. Technical degradation and qualitative residual uncertainty are carried forward, not hidden.

**Core rule:** Maximum mode increases the depth of inspection, not the monolithic nature of the job.

### **Interface 2 – OCR Semantic Add-On Validation (Tightened Addendum Final Version Maximum Mode)**

**Status:** This addendum final version does not replace the existing final version of Interface 2, but tightens it for OCR maximum mode.

**Point 1 – Trigger:** Semantic add-on validation in maximum mode inspects the candidate matrix of a block (multiple readings from various OCR reading lines such as Gemini 2.5 Pro Vision and Google Cloud Vision, preprocessing variants, zoom/crop levels). The AI-based validation is one of the three §3.4-stage-3 validation lines (rule-based, AI-based, statistical). Within the AI validation line, the canonized rules per §3.4 apply: GPT-4o and Gemini 2.5 Pro as equal-ranked consensus signalers, no primary/check roles, no artificial winner in case of disagreement within the AI line, revisability analogous to §3.6. The AI validation line is triggered by strong candidate divergence, layout instability, Qurʾān/hadith/isnād high risk, language/corpus ambiguity. The concrete weighting and triggering matrix between the three §3.4-stage-3 validation lines remains open.

**Point 2 – Access type:** Three strands (rule-based, statistical, AI-based) plus four inspection levels: surface consensus, layout consensus, language consensus, knowledge consensus. Interface 2 in maximum mode becomes the arbitration and consensus layer.

**Point 3 – Order / priority:** Within the AI validation line, GPT-4o and Gemini 2.5 Pro are equal-ranked consensus signalers per the canonical model assignment §3.4; no artificial winner in case of disagreement within the AI line. When, after running through the prescribed reconstruction stages, several strong competing readings remain, the canonical OCR quality principle §3.4 takes effect (no artificial winner, confidence drops, passage prioritized into OCR review). Decisive is the most robust overall constellation. Special rule: For Qurʾān/hadith/isnād/high-risk no automatic final victory in case of competing readings → review prioritization. The concrete weighting and triggering matrix between the three §3.4-stage-3 validation lines remains open.

**Point 4 – Timeout / retry:** Technical cases (AI timeout, Shamela not available) vs. qualitative cases (several plausible readings, no clear arbitration). No robust winner → confidence down, review up, no artificial closing victory.

**Point 5 – Fallback:** Three groups:

  - A: technical failure.
  - B: weak/neutral signal.
  - C: unresolved ambiguity despite maximum inspection → review, no silent closing victory.

Within the AI validation line, disagreement between GPT-4o and Gemini 2.5 Pro leads to declining confidence and review prioritization per the canonical model assignment §3.4; no artificial winner within the AI line. The OCR quality principle §3.4 takes effect when, after running through the prescribed reconstruction stages, several strong competing readings remain.

**Protective clause:** Unresolved ambiguity is itself a quality finding in its own right.

**Point 6 – UI visibility:** Live: page status. In review derivable: semantically uncertain, sources contradictory, several strong readings, decided without AI arbitration, Qurʾān/hadith high risk, layout/reading-direction conflict, strongly uncertain.

**Point 7 – Logging:** Extended by: candidate matrix, number of competing readings, type of consensus/non-consensus, corpus confirmation/contradiction, special-block marking, reason for review prioritization, reason why no winner was formed.

**Point 8 – Flow rule:** Additional consensus/arbitration loops increase inspection intensity, but do not produce a monolith. Unresolved block is marked and prioritized. Unresolved ambiguity is a legitimate output state.

**Core rule:** Maximum inspection may lead to more depth, but not to silent pseudo-confidence and not to monolithic abort behavior.

## **FINAL VERSION 2 – INTERFACE 3 – TRANSLATION AI**

**Status:** Working draft. Not yet canon. Not incorporated into Document 1 or Document 2.

### **Point 1 – Trigger**

The translation AI is invoked after completed OCR review and TOC confirmation. It runs chunk-wise and RAG-based; chunks never end mid-sentence. Per chunk, two models run in parallel: primary (leading translation draft) GPT-4o, check (parallel counter-translation and quality inspection) Gemini 2.5 Pro, per the canonical model assignment in §3.6. The assignment is provisionally canonical and revisable in a structured decision in case of newer or clearly better models (also within the same family); no silent model-change alteration. The role logic remains unchanged.

**Exclusion of accepted Qurʾān passages:** Accepted Qurʾān passages per §4.15 are tracked as protected passages in chunking. The accepted Qurʾān passage itself is excluded, not the surrounding chunk. For the protected passage, the canonical Arabic reference text and the canonical target-language translation per §4.15 are inserted from the respective carrier strands:

  - Arabic Qurʾān reference holdings as text carrier for Arabic reference text and vocalization.
  - quranenc.com or local fallback copy of the Qurʾān translation in the respective target language.

Glossary, style profile, and RAG do not act on the protected Qurʾān passage. The remaining translation flow within the chunk remains unaffected and follows the normal flow of the translation AI. Rejected Qurʾān passages per §4.15 follow the normal flow. The treatment of verified hadith passages in relation to the translation AI is not the subject of this regulation and is reserved for the hadith strand elaboration.

### **Point 2 – Access Type**

  - **Primary path:** GPT-4o – leading translation draft (model API external).
  - **Check path:** Gemini 2.5 Pro – parallel counter-translation and quality inspection (model API external).
  - **RAG basis and glossary/terminology/style profile:** local.

Two external dependencies simultaneously. Assignment canonical per §3.6, provisionally canonical and revisable per §3.6 revisability clause.

### **Point 3 – Order / Priority**

The check model has no general silent right of correction.

  - For objective deterministic findings: auto-correction, always logged and viewable.
  - For substantial/interpretive deviations: confidence drops, passage marked for review.
  - For genuine ambiguity: user notice, no silent decision.

### **Point 4 – Timeout / Retry**

Separate timeouts per model path. Automatic retry available. Chunk marked, the rest continues. Additionally, a manual retry button is available to the user (canonical §3.6).

Primary-path failure: no silent role swap, chunk in wait state with auto-retry. After 30 min without recovery: active user information via in-app + email (canonical special case §3.6). Concrete timeout and retry values remain open and depend on live measurement.

### **Point 5 – Fallback**

|  |  |
| :-: | :-: |
| **Situation** | **Behavior** |
| One model path timeout | automatic retry, then chunk marked |
| Primary failed | no silent role swap, wait state |
| Check path failed | primary continues, chunk marked as "unchecked" |
| Both failed | wait state and auto-retry |

Across all failure constellations, a manual retry button is available to the user (canonical §3.6). Active user information after 30 min without recovery via in-app + email (canonical special case §3.6).

Other class-B errors of the translation AI that do not fall under this 30-min special case are logged and reported in aggregate via the dashboard status indicator as soon as the clustering threshold per §4.18 Track 2 is reached (canonical class-B general logic). Concrete clustering threshold values depend on live measurement.

System-wide dead: job paused, resume possible.

**Protective clause:** There is no silent role swap.

### **Point 6 – UI Visibility**

Page-by-page progress display. Chunk states: processed / pending / unchecked / problematic. Auto-corrections discreetly marked, viewable on request. Review markings visible with reason type. Dashboard status indicator on API failure persists until recovery.

### **Point 7 – Logging**

**Internal:** leading model per chunk, check-model finding, type of finding (objective/interpretive), auto-corrections with diff, confidence, failures, retry, wait state/auto-retry, review markings with reason.

**For users:** derived status view.

### **Point 8 – Flow Rule**

Chunk-wise, not monolithic. Individual chunk failures do not stop the overall job. No silent role swap. Overall job only enters wait state on system-wide total failure. Substantive audit findings (A-01 through D-03) do not stop flow; they are persisted and carried forward in preflight. Auto-corrections always logged and never silent.

## **FINAL VERSION 3 – INTERFACE 4 – QURʾĀN INTERFACE**

**Status:** Working draft. Not yet canon. Not incorporated into Document 1 or Document 2.

### **Point 1 – Trigger**

Three triggers:

  - **A (OCR stage 1):** Block flagged, no API call.
  - **B (OCR stage 5):** Local matching → verse metadata, no API call.
  - **C (Translation phase):** API call quranenc.com, only here external.

Recognized and accepted verses are not translated by AI, but served by a canonical source.

### **Point 2 – Input**

Sura number, āya start/end (from B), language/translation version (german\_rwwad), match confidence (internal, automatically governs auto vs. manual).

**Vocalization rule:** After accepted recognition, quranenc.com is the sole text carrier. No free choice case. Only the recognition question is subject to inspection.

### **Point 3 – Output**

Canonical Arabic text (vocalized, overrides OCR), German translation (german\_rwwad), sura/āya verified, source identifier, fallback indicator.

Feeds the source-citation logic:

  - Author has a source citation → system verifies.
  - None → passage remains empty, user receives an option.

### **Point 4 – Error Behavior**

  - API failure: silent fallback to local copy (logging only).
  - Verse not found: warning icon and log entry.
  - Local copy also unavailable: warning icon and log entry.
  - Confidence below threshold: manual confirmation upstream.

### **Point 5 – Authentication and Connection Parameters**

API endpoint, auth, rate limit, timeout, retry: all unspecified (active work front). Local fallback copy: canonically present, complete.

### **Point 6 – Linkage with Internal Objects**

  - **Block UUID:** carrier of the verse metadata.
  - **Sentence UUID:** carrier of the canonical output.
  - **Source attributes:** sura, āya range, source identifier, fallback indicator.
  - **Decision-event UUID:** for manual confirmation/rejection.

### **Point 7 – Versioning**

Traceable: active Qurʾān copy, primary API or fallback, sura/āya combination, translation version, manual confirmation, change to local copy.

**Core rule:** Already saved project passages remain unchanged when the local copy changes. No silent overwriting.

### **Point 8 – Open Items**

Confidence threshold value, API endpoint/auth/rate limit/timeout/retry, versioning of german\_rwwad, modeling of verse metadata B, English Qurʾān translation.

## **FINAL VERSION 4 – INTERFACE 5 – HADITH INTERFACE**

**Status:** Working draft. Not yet canon. Not incorporated into Document 1 or Document 2.

**Canonization state:**

  - Hadith integration: five sub-areas canonized (source structure, consensus logic, Kutub as-Sitta, decision\_event assignment, vocalization principle). Integration blocks A-1 through A-5 and B-1 through B-4 incorporated.
  - Consolidation state of the extended hadith source set: E-1/E-2/E-3/E-4 Option B suspended, E-5 in special role; hadithportal.com excluded.
  - Hadith verification semantics and data model: vocalization escalation criterion V-0/V-1/V-2, hadith verification status N-1 through N-10 / H-0/H-1/H-2, gate localization, multi-source result objects data model, K-4 R-1/R-2 language-neutral reference field English.

### **Active Working Basis (historical workbench state, preserved here as development trail; superseded by canon §4.16)**

6 active sources: الدُّرَرُ السَّنِيَّة, جَامِعُ الكُتُبِ التِّسْعَة, Sunnah.com, مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة, Islamweb, Shamela. المكتبة الوقفية not part of the active search base.

**Note:** This original listing is superseded by the hadith integration (two-tier source structure mandatory/extended in §4.16) and the consolidation state of the extended hadith source set (E-1/E-2/E-3/E-4 effectively suspended, E-5 in special role, hadithportal.com excluded). Authoritative is the canonical state in Document 1 §4.16.

### **Point 1 – Trigger**

  - OCR stage 1: hadith block flagged.
  - OCR stage 5: local matching.
  - Before translation: check confidence.
  - Translation phase: external multi-source retrieval.

First external call only in translation phase.

### **Point 2 – Input**

Recognized Arabic reference text, match confidence, source named by the author, classification exact/short version/summary, isnād/matn hints.

**Normalization:** Search without/with ḥarakāt, OCR distortions, partial wording, matn/isnād separation, short version vs. full hadith.

### **Point 3 – Output**

Multi-source result per source: hit status, matn, vocalization, isnād, collection/work/number, direct link, website translation, authenticity/ḥukm, deviation, text proximity, technical status.

Three target outputs:

  - **A:** reference matn.
  - **B:** reference vocalization.
  - **C:** provenance/comparison package.

German translation by Waraq AI; website translations extracted and comparable.

### **Point 4 – Error Behavior**

  - **Group A:** technical source error – others continue.
  - **Group B:** substantive non-hit – weak signal.
  - **Group C:** total verification failure – warning icon, log entry, review panel, no automatic insertion.

### **Point 5 – Fallback and Comparison Logic**

Mandatory search across all active sources.

**Search modes:** exact wording, partial wording, source+wording, short version, isnād start, normalized OCR variant, without/with ḥarakāt.

**Comparison by:** wording proximity, multi-source carriership, author-source proximity, isnād reference, vocalization consistency, authenticity signals, website translation availability, Kutub as-Sitta signal.

### **Point 6 – User Logic and Conflict Cases**

  - **Case A:** consensus.
  - **Case B:** author names source, fits.
  - **Case C:** author names source, wording conflict.
  - **Case D:** no source named.
  - **Case E:** no source returns a hit → 5 user options.

7 decision\_event-relevant actions.

### **Point 7 – Isnād Logic and Provisional Traceability**

At minimum traceable: author wording, searched sources, reference-matn sources, vocalization source, verification sources, source conflicts, website translations, manual decisions, zero hits.

### **Point 8 – Still Open Items (workbench state at creation; many canonized in the meantime)**

Technical access specification per source, confidence threshold value, final variant display, UI short version vs. full hadith, multi-source result objects data model, decision\_source assignment, vocalization rule, English hadith strand, linkage capability جامع الكتب التسعة, relationship to §4.16, traceability logic.

## **FINAL VERSION 5 – INTERFACE 6 – SHAMELA / LEXICON INTERFACE**

**Status:** Working draft. Not yet canon. Not incorporated into Document 1 or Document 2.

Authoritative is the detailed version. Together with the Interface 6 working blocks (technical access layer, verification framework, inspection protocol, playback/evaluation logic, operational implementation template), this final version forms the complete current working state of Interface 6.

The substantive state can be fully derived from Document 2 §2F, §2G, and §2H.

### **Stabilized Core Decisions**

  - Shamela overall holdings = escalation search space, not a third lexicon source of equal type.
  - Three-stage search:
      
      - Stage 1 exact
      - Stage 2 extended
      - Stage 3a coarser lexicon search
      - Stage 3b escalation Shamela overall holdings
  - Stage 3b is triggered only on explicit user request (Variant B). Later hybrid logic (Variant C) remains open as possible refinement.
  - Qualitative inspection logic for "robust" anchored as structured guiding-criteria sequence (5 dimensions).
  - Optional morphological-contextual footnote draft as fallback when no lexicon hit is found.
  - Boundary fallback vs. §4.17: separate strands, consolidation deliberately open.
  - Shamela has two usage modes: Mode A (OCR-near, system-triggered), Mode B (user-controlled, lexicon workflow).

### **Three Levels Before the Lexical Footnote Entry**

1.  Level 1 – Morphological short analysis.
2.  Level 2 – Lexicon situation (with three-stage classification).
3.  Source-base selection (intermediate step).
4.  Level 3 – Footnote generator.

**Next operational step:** Real Shamela actual-state survey (currently parked; will only be reprocessed when the user expressly takes it up again).

## **WORKING BLOCK – INTERFACE 6 – TECHNICAL ACCESS LAYER SHAMELA / LISĀN / TĀJ**

**Status:** Working draft. Not yet canon. Not incorporated into Document 1 or Document 2. No code. No CRs. No silent architectural changes. Hadith search in Shamela remains part of Interface 5, not Interface 6. Word panel strand remains separate.

### **T6-1 – Permissible Assumptions About the Local Shamela Holdings**

  - **Assumption A-1 – Database format:** Shamela stores works in a structured format (historically SQLite-based, bok files). The actual format of the deployed Shamela version must be verified before implementation. No specific format is assumed as given.
  - **Assumption A-2 – Work identification:** Each work within Shamela has a unique work ID (BkId or comparable). The concrete designation and structure of the work IDs must be verified.
  - **Assumption A-3 – Text granularity:** Shamela works are internally divided into addressable text units (pages, sections, or comparable). Whether these units are page-based, chapter-based, or otherwise organized must be verified per work or per Shamela version.
  - **Assumption A-4 – Full-text search:** The Shamela holdings are full-text searchable (not only via metadata). Whether this search runs via its own internal indexing or via external full-text indexing must be verified.
  - **Assumption A-5 – Lisān and Tāj as works:** Lisān al-ʿArab and Tāj al-ʿArūs are present as individual identifiable works in the Shamela holdings and can be addressed specifically via their work IDs. The concrete work IDs must be verified.
  - **Assumption A-6 – Vocalization in the holdings:** The degree of vocalization varies within the Shamela holdings from work to work and where applicable within a work. Search queries must work both with and without ḥarakāt.

**Rule:** None of these assumptions may be silently treated as verified.

### **T6-2 – Logical Access Units**

  - **Unit L – Lisān al-ʿArab:** Primary lexicon source. Search restrictable to this work.
  - **Unit T – Tāj al-ʿArūs:** Equal-ranked alongside Lisān.
  - **Unit G – Shamela overall holdings:** Only in Stage 3b and Mode A. No equal lexicon status.

### **T6-3 – Minimum Technical Search Capabilities Per Stage**

  - **Stage 1 – Exact search (L and/or T):** Exact character-string search, with and without ḥarakāt, hit position with context.
  - **Stage 2 – Extended search (L and/or T):** Root-based, partial-word search. Root source (internal or external) open.
  - **Stage 3a – Coarser lexicon search (L and/or T):** Semantically loosened, neighboring entries, phonetically similar, homoglyphs. Transparency marker "indirect evidence."
  - **Stage 3b – Escalation (G):** Only on explicit user request. Overall holdings. Qualitative inspection logic (5 dimensions).

### **T6-4 – Access Paths Mode A vs. Mode B**

  - **Mode A – OCR-internal:** System-triggered, OCR stage 3, search space G, Stages 1+2, no user feedback, performance-critical.
  - **Mode B – User-controlled:** Explicit action, translation phase, search space L/T (Stages 1–3a) and optionally G (3b), full user feedback path, interactive latency.

**Separation rule:** Same data source, same access layer, but trigger, search space, search depth, result usage, and user interaction differ.

### **T6-5 – Mandatory Technical Preconditions Before Implementation**

V-1 through V-10: all open. See verification framework.

### **T6-6 – Deliberately Open Items**

Concrete database format, external indexing, hybrid logic 3b (Variant C), boundary §4.17, word panel strand, hadith search (→ Interface 5), UI trigger Mode B.

## **WORKING BLOCK – INTERFACE 6 – VERIFICATION FRAMEWORK SHAMELA / LISĀN / TĀJ**

**Status:** Working draft. Not yet canon. No results contained.

### **Part 1 – Assumptions A-1 Through A-6**

  - **A-1 (database format):** Direct inspection of file system + DB viewer. Verified upon clear identification on ≥ 3 works. Follow-up question: native vs. external indexing.
  - **A-2 (work identification):** Metadata-DB inspection, sample ≥ 10. Verified upon clear stable schema. Follow-up question: search-space control L/T/G.
  - **A-3 (text granularity):** Table structure ≥ 3 works. Verified upon consistent addressable subdivision. Follow-up question: hit-position format V-7.
  - **A-4 (full-text search):** Test query and timing. Verified upon functioning work-restrictable search in acceptable time. Follow-up question: indexing technology.
  - **A-5 (Lisān/Tāj present):** Work IDs and sample (ك-ت-ب). Verified upon finding both works with plausibly complete holdings. Follow-up question: in case of absence → re-evaluate Level-2 logic.
  - **A-6 (vocalization):** 30 text excerpts (10 Lisān, 10 Tāj, 10 others). Verified upon documented degree. Follow-up question: search normalization V-5.

### **Part 2 – Preconditions V-1 Through V-10**

  - **V-1 (database format):** = A-1. Blocks almost everything.
  - **V-2 (work-ID schema):** = A-2. Blocks search-space control.
  - **V-3 (text granularity):** = A-3. Blocks V-7.
  - **V-4 (full-text search):** = A-4 + decision native/external. Depends on V-1.
  - **V-5 (normalization):** Ḥarakāt stripping, Unicode normalization, Hamza/Alif variants. Depends on A-6 + V-1.
  - **V-6 (root assignment):** Shamela-internal or external (CAMeL/Farasa). Depends on V-1.
  - **V-7 (return format):** Fields per hit, context scope, position information. Depends on V-2 + V-3.
  - **V-8 (latency):** Target values Mode A (batch) + Mode B (interactive). Depends on V-4.
  - **V-9 (hit count):** Maximum, pagination, mode differences.
  - **V-10 (error behavior):** Per error category: notification/warning/skip/blockade. Consistency with §4.18.

### **Part 3 – Inspection Order**

1.  **Step 1 (basis):** V-1 / A-1 → first.
2.  **Step 2 (core structure):** V-2 / A-2 + V-3 / A-3 + A-5 + A-6 → in parallel after Step 1.
3.  **Step 3 (search architecture):** V-4 + V-5 + V-6 → after Steps 1+2.
4.  **Step 4 (specification):** V-7 + V-8 + V-9 + V-10 → after Steps 2+3.

## **WORKING BLOCK – INTERFACE 6 – INSPECTION PROTOCOL REAL SHAMELA ACTUAL-STATE SURVEY**

**Status:** Working draft. Fillable inspection protocol. Not yet canon. No results contained. Fields with \_\_\_\_\_ are to be filled in by the inspector. Inspection order: Step 1 → 2 → 3 → 4.

(Currently parked, will only be reprocessed when the user expressly takes it up again.)

### **Step 1 – Basis**

**A-1 / V-1 – Database format:**

  - Installation path: \_\_\_\_\_
  - Directory structure (top 2 levels): \_\_\_\_\_
  - File types in holdings: \_\_\_\_\_
  - Table structure of sample work: \_\_\_\_\_
  - Central metadata DB present (yes/no): \_\_\_\_\_
  - If yes – table structure: \_\_\_\_\_
  - Shamela version: \_\_\_\_\_
  - Other / anomalies: \_\_\_\_\_
  - Status: ☐ verified ☐ not verified ☐ unclear

### **Step 2 – Core Structure**

**A-2 / V-2 – Work identification:**

  - Field name work ID: \_\_\_\_\_
  - ID type: \_\_\_\_\_
  - Sample of 10 works (ID | title | author): 1. \_\_\_\_\_ 2. \_\_\_\_\_ 3. \_\_\_\_\_ 4. \_\_\_\_\_ 5. \_\_\_\_\_ 6. \_\_\_\_\_ 7. \_\_\_\_\_ 8. \_\_\_\_\_ 9. \_\_\_\_\_ 10. \_\_\_\_\_
  - Uniqueness confirmed (yes/no): \_\_\_\_\_
  - Status: ☐ verified ☐ not verified ☐ unclear

**A-5 – Lisān and Tāj as works:**

  - Lisān al-ʿArab – work ID: \_\_\_\_\_
  - Lisān – sample ك-ت-ب found (yes/no): \_\_\_\_\_
  - Lisān – number of text units/pages: \_\_\_\_\_
  - Tāj al-ʿArūs – work ID: \_\_\_\_\_
  - Tāj – sample ك-ت-ب found (yes/no): \_\_\_\_\_
  - Tāj – number of text units/pages: \_\_\_\_\_
  - Status: ☐ verified ☐ not verified ☐ unclear

**A-3 / V-3 – Text granularity:**

  - Work 1 (Lisān/Tāj) – fields: \_\_\_\_\_
  - Work 1 – sample values (3 entries): \_\_\_\_\_
  - Work 1 – continuously numbered (yes/no): \_\_\_\_\_
  - Work 2 (other) – fields: \_\_\_\_\_
  - Work 3 (non-lexicon) – fields: \_\_\_\_\_
  - Consistency between works (yes/no/partial): \_\_\_\_\_
  - Status: ☐ verified ☐ not verified ☐ unclear

**A-6 – Vocalization:**

  - Lisān – predominant vocalization degree: \_\_\_\_\_
  - Lisān – consistent (yes/no): \_\_\_\_\_
  - Tāj – predominant vocalization degree: \_\_\_\_\_
  - Tāj – consistent (yes/no): \_\_\_\_\_
  - General holdings – predominant: \_\_\_\_\_
  - General holdings – consistent (yes/no): \_\_\_\_\_
  - Status: ☐ verified ☐ not verified ☐ unclear

### **Step 3 – Search Architecture**

**V-4 – Full-text search capability:**

  - Single-work search functions (yes/no): \_\_\_\_\_
  - Single work – response time: \_\_\_\_\_
  - Overall holdings search functions (yes/no): \_\_\_\_\_
  - Overall holdings – response time: \_\_\_\_\_
  - FTS index present (yes/no): \_\_\_\_\_
  - External indexing required (yes/no/unclear): \_\_\_\_\_
  - Status: ☐ verified ☐ not verified ☐ unclear

**V-5 – Vocalization normalization:**

  - Search with ḥarakāt – hits (yes/no): \_\_\_\_\_
  - Search without ḥarakāt – hits (yes/no): \_\_\_\_\_
  - Tatweel handling: \_\_\_\_\_
  - Hamza variants: \_\_\_\_\_
  - Alif Maqsura/Ya: \_\_\_\_\_
  - Normalization required at (query/index/both): \_\_\_\_\_
  - Status: ☐ verified ☐ not verified ☐ unclear

**V-6 – Root assignment source:**

  - Root field present in Lisān (yes/no): \_\_\_\_\_
  - Root field present in Tāj (yes/no): \_\_\_\_\_
  - If yes – field name: \_\_\_\_\_
  - Sample correct (yes/no): \_\_\_\_\_
  - External path required (yes/no): \_\_\_\_\_
  - Status: ☐ verified ☐ not verified ☐ unclear

### **Step 4 – Specification**

**V-7 – Result return format:**

  - Available fields per hit: \_\_\_\_\_
  - Context scope: \_\_\_\_\_
  - Page reference present (yes/no): \_\_\_\_\_
  - Sufficient for Mode A (yes/no): \_\_\_\_\_
  - Sufficient for Mode B (yes/no): \_\_\_\_\_
  - Status: ☐ verified ☐ not verified ☐ unclear

**V-8 – Latency:**

  - Single work – mean: \_\_\_\_\_ ms / maximum: \_\_\_\_\_ ms
  - Overall holdings – mean: \_\_\_\_\_ ms / maximum: \_\_\_\_\_ ms
  - Acceptable for Mode A (yes/no/unclear): \_\_\_\_\_
  - Acceptable for Mode B (yes/no/unclear): \_\_\_\_\_
  - Status: ☐ verified ☐ not verified ☐ unclear

**V-9 – Hit count / pagination:**

  - Hits common word single work: \_\_\_\_\_
  - Hits common word overall holdings: \_\_\_\_\_
  - Pagination required (yes/no): \_\_\_\_\_
  - Status: ☐ verified ☐ not verified ☐ unclear

**V-10 – Error behavior:**

  - Behavior on missing work ID: \_\_\_\_\_
  - Behavior on missing file: \_\_\_\_\_
  - Error message intelligible (yes/no): \_\_\_\_\_
  - Crash behavior (yes/no): \_\_\_\_\_
  - Status: ☐ verified ☐ not verified ☐ unclear

### **Closing Fields**

  - Inspector: \_\_\_\_\_
  - Date: \_\_\_\_\_
  - Shamela version: \_\_\_\_\_
  - Server / environment: \_\_\_\_\_
  - Overall status: ☐ Step 1 ☐ Step 2 ☐ Step 3 ☐ Step 4
  - Open items / anomalies: \_\_\_\_\_

## **WORKING BLOCK – INTERFACE 6 – PLAYBACK AND EVALUATION LOGIC SHAMELA ACTUAL-STATE SURVEY**

**Status:** Working draft. Not yet canon. Not incorporated into Document 1 or Document 2. No code. No CRs. No silent architectural changes. No real verification contained. No results contained.

(Currently parked, follows the real actual-state survey.)

### **R-1 – Principles of Playback**

  - **R-1.1** Sole permissible input is a filled-in inspection protocol (Steps 1–4) with real field data and a status set per inspection point.
  - **R-1.2** No inspection point may be treated as verified without a filled-in protocol field. Empty fields with status set to "verified" are a contradiction and force a clarifying inquiry.
  - **R-1.3** Inspection results are first taken in as raw data, not directly integrated into the working state. Only after evaluation (R-3) and follow-up-path assignment (R-4) does an integration-ready state arise.
  - **R-1.4** Results from the real actual-state survey may not silently change the existing architecture. If a result suggests an architecture adjustment, this is documented as an open item and decided separately.

### **R-2 – Acceptance of Inspection Results**

  - **R-2.1 – Formal check on receipt:** Status set per inspection point? Field data filled in? Inspection order observed? Metadata complete?
  - **R-2.2 – Handling of incomplete protocol:** Step 1 missing → no later step evaluable. Individual fields missing → affected point = "unclear." Clarifying inquiry.
  - **R-2.3 – Partial playback:** Permissible (only Step 1 or 1+2). Evaluation only for available steps. Remainder = "pending."

### **R-3 – Evaluation Logic Per Status**

  - **Verified:** Assumption is promoted to verified finding. Dependent preconditions unlocked. Follow-up question from verification framework becomes active.
      
  - **Not verified:** Three subtypes:
      
      - partly different (access logic adjustable?)
      - not present (blocker)
      - fundamentally different (architecture finding)
  - No silent adjustment.
      
  - **Unclear:** Two subtypes:
      
      - methodologically unclear (supplementary inspection measure)
      - substantively unclear (document differentiated handling)

### **R-4 – Follow-Up Paths Per Inspection Point**

Detailed follow-up-path tables for Step 1 (A-1/V-1), Step 2 (A-2/V-2, A-5, A-3/V-3, A-6), Step 3 (V-4, V-5, V-6), Step 4 (V-7, V-8, V-9, V-10) – each with behavior on verified / not verified / unclear.

### **R-5 – Threshold: Working State vs. Integration-Ready Specification**

  - **R-5.1** Point remains working state on status "unclear" or unresolved dependency.
  - **R-5.2** Ready for specification block on: verified + all dependencies verified + follow-up question nameable.
  - **R-5.3** The boundary is never silently crossed.
  - **R-5.4** Even with fully verified Steps 1–4, the overall block remains a working draft until an explicit canonization decision.

### **R-6 – Overall Evaluation Schema**

After full playback: number of verified/not verified/unclear per step, blocker list, active follow-up questions, specification-ready points, points requiring clarification, compatibility statement on the existing access logic. Generated as an independent working state.

### **R-7 – Deliberately Open Items**

Format of the evaluation block, intermediate evaluation blocks for partial playback, findings affecting other interfaces, documentation of architecture-adjustment need.

## **WORKING BLOCK – INTERFACE 6 – OPERATIONAL IMPLEMENTATION TEMPLATE SHAMELA ACTUAL-STATE SURVEY**

**Status:** Operational auxiliary document. Not canon. No architecture change. Not incorporated into Document 1 or Document 2.

(Currently parked.)

### **Implementation Instructions**

Step-by-step instructions (Steps 1–4) for the inspector with real system access. Per step: what is concretely opened/checked, what is documented, what counts as sufficient, when "unclear" is set. **Basic rule:** estimate nothing, guess nothing.

### **Data-Collection Template**

Compact fillable template structured by Step 1 / 2 / 3 / 4 with all fields and status checkboxes (verified / not verified / unclear).

### **Return Format**

Compressed format for return to the Co-Pilot: metadata → Steps 1–4 → open anomalies. Only fillable structure, no explanatory text.

## **WORKING BLOCK – TECHNICAL ACCESS SPECIFICATION INTERFACE 4 – QURʾĀN INTERFACE**

**Status:** Working draft. Not yet canon. Not incorporated into Document 1 or Document 2. No code. No CRs. No silent architectural changes.

### **Q4-1 – Source Structure and Access Paths**

#### **Q4-1.1 – Primary Source**

  - **API:** quranenc.com
  - **Base URL:** https://quranenc.com/api/v1/
  - **Authentication:** None documented. The API is, as of current state, publicly accessible without API key or token.
  - **Translation key for German:** german\_rwwad (Rowwad Translation Center)
  - **HTTP method:** GET
  - **Protocol:** HTTPS

#### **Q4-1.2 – Relevant Endpoints (Verified from Public API Documentation)**

**Endpoint 1 – Single verse:** GET /translation/aya/{translation\_key}/{sura\_number}/{aya\_number}

  - Input: translation\_key (e.g., german\_rwwad), sura\_number (1–114), aya\_number (1–n)
  - Return: JSON object with fields sura, aya, translation, footnotes

**Endpoint 2 – Entire sura:** GET /translation/sura/{translation\_key}/{sura\_number}

  - Input: translation\_key, sura\_number (1–114)
  - Return: JSON array, each element with sura, aya, translation, footnotes

**Endpoint 3 – Available translations:** GET /translations/list/\[\[{language}\]\]/?localization={language\_iso\_code}

  - Return: JSON array with key, language\_iso\_code, version, last\_update, title, description
  - Use: Version check of the german\_rwwad translation in weekly reconciliation.

#### **Q4-1.3 – Critical Finding: Arabic Reference Text**

The quranenc.com API delivers, per documented state, only translations (fields: translation, footnotes), not the Arabic original text with vocalization.

§4.15 defines quranenc.com as the sole text carrier for Arabic reference text, vocalization, and German translation. Since the API apparently does not deliver the Arabic text, two possible resolutions arise:

  - **Variant A:** The Arabic reference text and vocalization always come from the local fallback copy (which, per Final Version 3 Point 5, contains the complete data state). The API delivers only the German translation. The local copy is thus not only fallback but the primary carrier of the Arabic text.
  - **Variant B:** There is an undocumented or separate endpoint for the Arabic Qurʾān text at quranenc.com.

**Status of this finding:** Closed by the canonical state in Document 1 §4.15. Variant A is canonized. The Arabic reference text (incl. vocalization) is sourced from the Arabic Qurʾān reference holdings, which constitute an independent local holding and are not served via quranenc.com or any other API at any time. The question of a separate Arabic API endpoint (Variant B) is therefore no longer relevant. No longer a working hypothesis.

#### **Q4-1.4 – Local Fallback**

Two separate local holdings (canonical §4.15):

**(a) Local fallback copy/copies of the translation:** Complete local copy of the german\_rwwad translation. Fallback for the German translation on quranenc.com API failure. Must at minimum encompass:

  - all 114 suras and āyāt
  - German translation (german\_rwwad)
  - footnotes (insofar as present in german\_rwwad)
  - version identifier of the german\_rwwad translation
  - date of last reconciliation

The same applies to the local fallback copy of the English Qurʾān translation per §4.15; concrete translation key open.

**(b) Arabic Qurʾān reference holdings:** Independent local holdings with vocalized Arabic Qurʾān text (ʿUthmānic spelling). Sole text carrier for Arabic reference text and vocalization (§4.15). Target-language-independent. Not API-supported. Independent of the translation fallback copies. Concrete source designation, data format, storage location, and update mechanism open.

### **Q4-2 – Access Path Per Trigger**

#### **Q4-2.1 – Trigger A: OCR Stage 1 (Visual Structure Analysis)**

  - **Action:** Block flagged as potential Qurʾān block.
  - **Access:** No data access. No API call. No local lookup.
  - **Output:** Block label "Qurʾān candidate" attached to block UUID.
  - No external call in the OCR phase (canonically confirmed §4.15).

#### **Q4-2.2 – Trigger B: OCR Stage 5 (Quality Inspection)**

  - **Action:** Local matching of the OCR text against the local Qurʾān copy.
  - **Access:** Local only. No API call.
  - **Matching logic:** OCR text fragment is searched against the Arabic Qurʾān reference holdings (§4.15). On hit: sura, āya start, āya end, match confidence are stored as verse metadata at block UUID.
  - **Output:** Verse metadata (sura, āya range, confidence) or no match.
  - Confidence threshold for automatic acceptance: still open.

#### **Q4-2.3 – Trigger C: Translation Phase**

  - **Action:** First and only external API call.
  - **Precondition:** Qurʾān recognition from Stage 5 is present and accepted (automatically or manually confirmed).
  - **Access:** API call to quranenc.com.
  - **Primary endpoint:** Single verse (/translation/aya/german\_rwwad/{sura}/{aya}) per āya in the recognized range. For contiguous ranges, alternatively sura endpoint (/translation/sura/german\_rwwad/{sura}) and local filtering on the relevant āya range.
  - **Process the return:**
      
      - translation field = German translation.
      - footnotes field = footnotes.
      - sura/aya fields = verification against local metadata.
  - **Arabic reference text:** From the Arabic Qurʾān reference holdings (§4.15, canonically the sole text carrier, not API-supported).
  - **Fallback on API failure:** Silent switch to the local copy for the German translation. Log entry in the project log. Set fallback indicator on the passage. No user popup on fallback – only log entry.

### **Q4-3 – Timeout / Retry / Failure Handling**

#### **Q4-3.1 – API Timeout**

Still open: concrete timeout value cannot be set without latency measurement. **Working hypothesis:** 10 seconds per request as baseline, adjustable after real measurement.

#### **Q4-3.2 – Retry Logic**

  - 1× automatic retry on timeout or HTTP 5xx error.
  - No retry on HTTP 4xx (client error = structural problem).
  - Between first attempt and retry: short pause (working hypothesis 2 seconds).

#### **Q4-3.3 – Failure Handling**

|  |  |
| :-: | :-: |
| **Situation** | **Behavior** |
| API timeout after retry | Silent fallback to local copy. Log entry. Fallback indicator. |
| HTTP 404 (verse not found), locally present | Fallback to local copy. Log entry. Fallback indicator. Additional anomaly marker: API and local holdings may diverge. |
| HTTP 404 (verse not found), also not locally present | Warning icon at the passage. Log entry. Manual clarification by user required. |
| HTTP 4xx (other client error) | Log entry. Passage marked. No retry. |
| HTTP 5xx after retry | Silent fallback to local copy. Log entry. Fallback indicator. |
| Local copy also unavailable | Warning icon. Log entry. Passage blocked until clarification. |
| Network error (DNS, TLS) | Treated as API timeout. |

#### **Q4-3.4 – No User Interrupt on Fallback**

The fallback to the local copy does not interrupt the translation flow. The user is not actively informed (no modal, no toast). The information is traceable in the project log and via the fallback indicator at the affected passage.

### **Q4-4 – Error Classes and Mapping to §4.18**

|  |  |  |
| :-: | :-: | :-: |
| **Error type** | **Class (§4.18)** | **Treatment** |
| API timeout / HTTP 5xx | Class B (external error) | Retry → fallback → log |
| HTTP 404 verse not found | Class B (external error) | Local fallback if present → log + anomaly marker |
| Local copy corrupt / missing | Class C (system-fixable) | Blockade → technical recovery |
| Matching error (wrong verse recognized) | Class A (user/data error) | User corrects in review |
| Confidence below threshold | Not an error | Normal flow → manual confirmation |

**Notification channel for class-B errors:** aggregated user information via dashboard status indicator on clustering per §4.18 Track 2 (canonical). Already-canonized special cases with own rule remain unaffected:

  - Translation AI 30-min rule §3.6
  - Qurʾān fallback log without user interrupt §4.15 / Q4-3.4
  - Guard-near blockades §4.7

Concrete clustering threshold values depend on live measurement.

### **Q4-5 – Logging / Provenance**

#### **Q4-5.1 – Logged Per Qurʾān Passage in the Project**

  - sura / āya range
      
  - Arabic reference-text source: Arabic Qurʾān reference holdings (§4.15, canonically sole text carrier, not API-supported)
      
  - Translation source: quranenc.com API or local fallback copy of the translation
      
  - Translation version (german\_rwwad version from /translations/list; analogously for the English Qurʾān translation per §4.15)
      
  - Translation fallback indicator (yes/no)
      
  - Confidence of recognition (from OCR Stage 5)
      
  - **Passage state:** accepted as Qurʾān passage OR rejected as Qurʾān passage (not treated as Qurʾān). Only accepted passages receive the Qurʾān carrier fields named here (sources, translation version, fallback indicator). Rejected passages are documented as an independent passage state with timestamp and decision\_event\_uuid and carry no Qurʾān carrier fields.
      
  - **Acceptance path** (only for accepted passages):
      
      - automatically accepted (confidence above threshold value)
      - manually confirmed (confidence below threshold value, user confirmation of the system-suggested assignment)
      - manually corrected (user changes sura/āya assignment relative to the system suggestion)
  - On explicit user action to update an already-saved Qurʾān passage after an update of the Arabic Qurʾān reference holdings or the local fallback copy of the translation per §4.15, the acceptance-path value of the updated passage is set per the new state; the update itself is logged via the decision\_event.
      
  - Timestamp of the API call or fallback access
      
  - decision\_event\_uuid per the canonical action-types matrix §4.15: translation\_pipeline on manual confirmation and on explicit user action to update an already-saved Qurʾān passage; conflict\_resolution on correction and on rejection. No decision\_event on automatic acceptance.

#### **Q4-5.2 – Logged System-Wide**

  - API failures with timestamp and HTTP status
  - Fallback activations
  - Weekly reconciliation results (version change yes/no)

### **Q4-6 – Versioning of the Local Fallback Copy**

#### **Q4-6.1 – Weekly Automatic Reconciliation**

Waraq calls the endpoint /translations/list/de weekly. From the response, the object with key: "german\_rwwad" is extracted. Fields version and last\_update are compared with the locally stored state.

#### **Q4-6.2 – On Detected Version Change**

  - New full pull of the german\_rwwad translation is downloaded (all 114 suras via sura endpoint).
  - Old state is archived (not overwritten).
  - New state is marked as the active local copy.
  - Log entry with old and new version.

#### **Q4-6.3 – Protection of Existing Project Passages (Canonical §4.15)**

Qurʾān passages already saved in projects remain unchanged when the local fallback copy changes. No automatic re-fetch. No silent overwriting. The passage carries the version identifier with which it was generated. Only on explicit user action (e.g., "update verse") is the passage checked against the current copy.

#### **Q4-6.4 – Arabic Text on Updates**

The Arabic Qurʾān reference holdings are canonically (§4.15) not part of the quranenc.com API reconciliation and not part of the weekly version check of the translation fallback copies. The update mechanism for the Arabic Qurʾān reference holdings is to be specified independently and remains open.

### **Q4-7 – Confidence Threshold and Manual Confirmation**

#### **Q4-7.1 – Basic Principle (Canonical §4.15)**

If the confidence of Qurʾān recognition is below the defined threshold value: manual confirmation by the user upstream. No automatic API call. Only after confirmation is the verse treated as recognized and the translation-phase access (Q4-2.3) triggered.

#### **Q4-7.2 – Concrete Threshold Value**

Still open. Must be set after test runs with real OCR results. **Working hypothesis:** Adoption of the existing OCR confidence thresholds (85% for automatic acceptance, below that manual confirmation). No silent setting.

#### **Q4-7.3 – User Interaction on Manual Confirmation**

**User sees:** OCR text fragment, suggested sura/āya, confidence value.

**User-action types** per the canonical matrix §4.15:

  - **Confirm** → decision\_source = translation\_pipeline (acceptance path: manually confirmed)
  - **Correct** (different sura/āya) → decision\_source = conflict\_resolution (acceptance path: manually corrected)
  - **Reject** (not as Qurʾān) → decision\_source = conflict\_resolution (no accepted Qurʾān passage state; independent passage state per Q4-5.1)

Each of these actions generates a decision\_event. Automatic acceptance with confidence above threshold value generates no decision\_event. The fourth action of the matrix (explicit user action to update an already-saved Qurʾān passage) is not triggered in this dialog but via the update path described in Q4-6.3 and is logged with decision\_source = translation\_pipeline.

### **Q4-8 – Linkage with Internal Objects**

  - **Block UUID:** carrier of the block class "Qurʾān" and the verse metadata from OCR Stage 5.
  - **Sentence UUID:** carrier of the canonical output (Arabic text + German translation).
  - **Source attributes:** sura, āya range, source identifier (API/fallback), fallback indicator, translation version.
  - **Decision-event UUID:** Per the canonical action-types matrix §4.15. decision\_source assignment: translation\_pipeline on manual confirmation and on explicit user action to update an already-saved Qurʾān passage; conflict\_resolution on correction and on rejection. No decision\_event on automatic acceptance.

### **Q4-9 – Explicit List of Open Items**

1.  **Arabic reference text via API** → CLOSED by §4.15 (Variant A canonical; Arabic Qurʾān reference holdings independently local, not API-supported).
2.  **Concrete confidence threshold value** → open (live test after real OCR results).
3.  **Concrete timeout value** → open (live measurement, conservative request profile §3.5).
4.  **Rate limit** → open (live test).
5.  **Update mechanism Arabic Qurʾān reference holdings** → open (§4.15).
6.  **English Qurʾān translation** → CLOSED by §4.15 (quranenc.com primary with translation key english\_rwwad; local fallback copy of the English Qurʾān translation analogous to the German strand).
7.  **Versioning of german\_rwwad in detail** → open (design question comparison mechanism version string/timestamp).
8.  **Notification channel class B** → CLOSED by §4.18 Track 2 dashboard aggregation.
9.  **Data format and storage location of the two local holdings:**
      
      - (a) Arabic Qurʾān reference holdings → open.
      - (b) local fallback copy/copies of the Qurʾān translation(s) (German and English) → open.
10. **Source-citation format in export** → open (downstream design question).

**Qurʾān-passage handling / decision\_source matrix** → CLOSED by §4.15.

## **WORKING BLOCK – TECHNICAL ACCESS SPECIFICATION INTERFACE 5 – HADITH INTERFACE**

**Status:** Working draft. Not yet canon. Not incorporated into Document 1 or Document 2. No code. No CRs. No silent architectural changes.

**Canonical basis:** §4.16 Document 1. **Substantive basis:** Final Version 4 (Block 3).

Five sub-areas from the hadith integration canonized (source structure, consensus logic, Kutub as-Sitta, decision\_event assignment, vocalization principle). Consolidation state of the extended hadith source set incorporated. Hadith verification semantics and data model canonized (vocalization escalation criterion, hadith verification status, gate localization, data model). This working block specifies the technical access layer in detail without changing the canonized substantive decisions.

### **H5-1 – Source Structure and Access Paths**

#### **H5-1.1 – Mandatory Set (Fully Searched on Every Hadith Verification Run)**

##### **Source P-1: sunnah.com**

  - **Access type:** API (external)
  - **Base URL:** https://api.sunnah.com/v1/
  - **Authentication:** API key required (header X-API-Key). Key is requested by creating a GitHub issue on the repository sunnah-com/api (template "Request for API access"). Free of charge. No self-service – key is granted manually by the sunnah.com team. Processing time not guaranteed. Key must be actively requested before implementation and stored server-side. Plan in lead time.
  - **HTTP method:** GET
  - **Protocol:** HTTPS
  - **Language:** Arabic and English translations available. German translation: per pre-verification not part of the API holdings (closed finding).
  - **Primary data structure:** collections → books → chapters → hadiths.
  - **Official API specification:** OpenAPI v1.0, publicly viewable at github.com/sunnah-com/api/blob/master/spec.v1.yml.

**Verified endpoints (from OpenAPI specification v1.0):**

  - GET /collections – All available collections
  - GET /collections/{collectionName} – Single collection
  - GET /collections/{collectionName}/books – Books of a collection
  - GET /collections/{collectionName}/books/{bookNumber} – Single book
  - GET /collections/{collectionName}/books/{bookNumber}/chapters – Chapters of a book
  - GET /collections/{collectionName}/books/{bookNumber}/hadiths – Hadiths of a book
  - GET /collections/{collectionName}/hadiths/{hadithNumber} – Single hadith by collection + number
  - GET /hadiths – Hadiths with structured filters (collection, bookNumber, chapterId, hadithNumber)
  - GET /hadiths/{urn} – Single hadith by URN
  - GET /hadiths/urns – Multiple hadiths by URN list
  - GET /hadiths/random – Random hadith

**Primary search path:** Exclusively structured lookups via collection + book + hadith number, URN, or filter parameters at the /hadiths endpoint. This path presupposes that the author names a source or that the local Shamela matching (OCR Stage 5) has already delivered a collection/number. With no source citation by the author and no Shamela hit, this path alone is not sufficient – in this case the mandatory search relies on the text search of the other mandatory sources (P-2 Shamela full-text search, P-3 dorar.net).

**Closed finding – No full-text search in the official API:** The OpenAPI specification v1.0 contains no endpoint for full-text search in the matn or isnād. The /hadiths endpoint accepts exclusively structured filter parameters (collection, bookNumber, chapterId, hadithNumber). None of these parameters allows a text search. The sunnah.com website does offer full-text search (with wildcards, fuzzy search, boolean operators), but this search function is not exposed via the official API. The earlier working hypothesis of an endpoint GET /hadiths?q={query} is thereby refuted. No longer an open item.

**Hadith response structure (verified from OpenAPI spec):** Each hadith object contains: collection (string), bookNumber (string), chapterId (string), hadithNumber (string), hadith (array with language-specific objects). Each language-specific object contains: lang (string, e.g., en, ar), chapterNumber, chapterTitle, urn (integer), body (string, hadith text in HTML markup), grades (array with ratings: graded\_by + grade).

**Body format:** The body text contains HTML markup (e.g., \<p\>-tags). For comparison with OCR text, HTML stripping must be provided in result processing.

**Authenticity grade:** The grades field is structured as an array with graded\_by (string) + grade (string). Multiple ratings per hadith are possible. Whether the field is consistently filled across all hadiths requires test operation with a real API key.

**Pagination:** All list endpoints support limit (max 100, default 50) and page (default 1). Response contains total, limit, previous, next.

**Collection coverage (verified from developer page):**

  - **Kutub as-Sitta (all 6):** Sahih al-Bukhari, Sahih Muslim, Sunan an-Nasa'i, Sunan Abi Dawud, Jami\` at-Tirmidhi, Sunan Ibn Majah.
  - **Other verified collections:** Muwatta Malik, Musnad Ahmad, Sunan ad-Darimi, An-Nawawi's 40 Hadith, Riyad as-Salihin, Al-Adab Al-Mufrad, Ash-Shama'il Al-Muhammadiyah, Mishkat al-Masabih, Bulugh al-Maram, Collections of Forty, Hisn al-Muslim.
  - **Not listed:** Al-Mustadrak (al-Hakim), Majma' az-Zawa'id. Whether further, non-website-listed collections are available must be verified by API query (GET /collections) with a real key.

**Rate limit:** Not documented in the OpenAPI specification. Whether an undocumented limit exists cannot be determined without test operation. Conservative request behavior recommended.

##### **Source P-2: Shamela (مكتبة الشاملة) – local**

  - **Access type:** Local (server-side)
  - **Technical access layer:** Fully specified in Interface 6 (working blocks T6-1 through T6-6, verification framework, inspection protocol). Interface 5 uses the same technical access layer as Interface 6, but in its own functional mode.
  - **Functional mode for hadith:** Shamela in the hadith context is searched as a verification source – not as a lexicon source (that is Interface 6 / Mode B). The search runs over the overall holdings (not just Lisān/Tāj), targeted at hadith collections and works with hadith reference.
  - **Search space:** Primarily hadith collections within Shamela (Kutub as-Sitta, Musnad Ahmad, Muwatta, Sunan ad-Darimi, al-Mustadrak, Majmaʿ az-Zawāʾid, etc.). Secondarily: overall holdings on extended search.
  - **Dependency:** Technical availability and search capability depend on the real Shamela actual-state survey (Interface 6, currently parked). Until then: working hypothesis that Shamela is full-text searchable and that hadith collections are present as identifiable works.

**Boundary to Interface 6:** Interface 6 defines the generic access mechanism to Shamela (data format, search capability, indexing). Interface 5 defines the hadith-specific search path, search space, and result processing. No double specification of the technical base layer.

##### **Source P-3: dorar.net (الدُّرَرُ السَّنِيَّة)**

  - **Access type:** API-prioritized. Scraping as secondary fallback path.
  - **Base URL:** https://dorar.net/
  - **Authentication:** None documented. Publicly accessible.
  - **Protocol:** HTTPS

**API access (primary):** dorar.net provides an official API service for the hadith encyclopedia (الموسوعة الحديثية). The existence of the API service is officially documented on the dorar.net page "خدمة واجهة الموسوعة الحديثية API," which describes the service and contains usage examples (JavaScript). The service provides search results via JSON. On the official page, a JSONP usage example for client-side JavaScript access is shown – this does not mean that the API is fundamentally or exclusively JSONP-based. For server-side access (as with Waraq), standard HTTP requests with JSON response are the expected normal case.

The deeper technical specification (exact endpoint URLs, complete parameter list, response-parsing details, versioning) is not exhaustively documented on the official page. The most detailed available documentation comes from an open-source third-party proxy (dorar-hadith-api, MIT license, github.com/AhmedElTabarani/dorar-hadith-api). This proxy explicitly distinguishes between the API path (official dorar API) and the site path (website scraping) and serves as a reverse-engineering basis for the endpoint and parameter specification.

**Verified capabilities** (officially documented: basics; practically observable: details):

  - Text search in matn (Arabic)
  - Filter by collection/work (via book-ID parameter)
  - Filter by muhaddith (via muhaddith-ID parameter)
  - Filter by transmitter (via rawi-ID parameter)
  - Filter by authenticity grade (via grade parameter)
  - Return of takhrij (reference to other collections)
  - Return of authenticity grade (grade) and explanation (explainGrade)
  - JSON response

**Response fields** (from third-party proxy documentation, practically observable): hadith (matn, HTML markup), rawi, mohdith/mohdithId, book/bookId, numberOrPage, grade, explainGrade, takhrij, hadithId, hasSimilarHadith, hasAlternateHadithSahih, hasUsulHadith.

**Body format:** Hadith texts are delivered in HTML markup. HTML stripping is required in result processing.

**Scraping access (secondary, only as fallback path):** If the API access does not cover the full required functional scope, is not stably usable, or does not support individual search modes, the dorar.net search mask can be used as a secondary access path via scraping (Playwright). This path is subject to the general scraping stability rules (H5-11) but takes effect only when the API path is not sufficient for the concrete query. The scraping path delivers in part different/additional fields (e.g., thematic categories).

**Collection coverage:** The dorar.net hadith encyclopedia covers a broad holding that goes beyond the Kutub as-Sitta. The complete listing of all searchable books and muhaddithun is documented via filter lists of the third-party proxy. Exact reconciliation against the Waraq need requires inspection of these lists.

**Critical findings:**

  - **Finding 1 – Deeper endpoint specification:** Exact endpoint URLs and parameter encoding of the original API (not the proxy) must be verified before implementation by inspection of the dorar.net network requests (browser DevTools) or analysis of the proxy source code.
  - **Finding 2 – Rate limit:** Not documented. Must be determined via cautious test operation. Conservative request behavior until clarification.
  - **Finding 3 – Stability:** Since the API is not officially versioned and the deeper specification is not exhaustively documented, there is no stability guarantee. Endpoints, parameters, and response formats may change without prior announcement. A monitoring mechanism for endpoint availability and response consistency must be provided.
  - **Finding 4 – Ḥarakāt sensitivity:** Whether the text search works ḥarakāt-insensitively cannot be deduced from the available documentation and requires test operation.

#### **H5-1.2 – Extended Set (Consolidation State of the Extended Hadith Source Set Authoritative)**

  - **Source E-1: islamweb.net** – Option B effectively suspended. Web scraping candidate without API. See Block 3 pre-verification.
  - **Source E-2: جامع السنة النبوية** (Alifta-/Harf variant) – Option B effectively suspended. No API. Scraping candidate on government infrastructure.
  - **Source E-3: المكتبة الوقفية** – Option B effectively suspended. Tracked only as possible manual reference source.
  - **Source E-4: جَامِعُ الكُتُبِ التِّسْعَة** (Arabia-IT) – Option B effectively suspended. Mobile App only, no web/API integration.
  - **Source E-5: مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة** (hadeethenc.com) – Option B not suspended. Special role "German translation source / multilingual reference source." Official API, bulk downloads. No API full-text search path.

**Exclusion:** hadithportal.com explicitly excluded.

**Escalation logic:** On automatic activation of the extended set, effectively only E-5 active as long as E-1–E-4 remain suspended.

#### **H5-1.3 – No Local Fallback Holdings for Hadith (Boundary to §4.15)**

Unlike for Qurʾān (§4.15), there is intentionally no sole text carrier and no complete local fallback copy for hadith. Verification is multidimensional and cross-source. There is no situation in which a single local holding could take over the entire hadith verification.

### **H5-2 – Access Path Per Trigger**

  - **H5-2.1 – Trigger A (OCR Stage 1, visual structure analysis):** Block flagged as potential hadith block. No data access, no external call.
  - **H5-2.2 – Trigger B (OCR Stage 5, quality inspection):** Local matching against Shamela hadith holdings (Mode A). No external API call. Provisional hadith metadata (work, number, matn fragment, confidence).
  - **H5-2.3 – Trigger C (before translation, confidence check):** Confidence ≥ threshold → automatic to translation-phase verification; confidence \< threshold → manual confirmation; no OCR hit → directly into multi-source verification with OCR raw text.
  - **H5-2.4 – Trigger D (translation phase, multi-source verification):**
      
      - Step 1 mandatory search P-1/P-2/P-3 in parallel.
      - Step 2 mandatory evaluation per §4.16 consensus logic.
      - Step 3 extended set automatically activated (effectively only E-5 active), manually triggerable.
      - Step 4 result merging; three target outputs A (reference matn), B (reference vocalization), C (provenance/comparison package); linear ranking as tie-breaker; Kutub as-Sitta as weighting factor.

### **H5-3 – Timeout / Retry / Failure Handling**

  - **H5-3.1 – Timeout values per source (all working hypotheses):**
      
      - sunnah.com API: 10 s
      - Shamela local: 5 s
      - dorar.net API: 10 s
      - dorar.net scraping fallback: 15 s
      - islamweb.net / جامع السنة / الوقفية scraping: 15 s each
      - E-4 / E-5: depending on access type
  - **H5-3.2 – Retry logic:**
      
      - API sources 1× retry on timeout/5xx, no retry on 4xx, pause 2 s.
      - Scraping 1× retry on timeout/load error, no retry on 4xx/DOM break, pause 3 s.
      - Shamela local 1× retry on DB lock/IO, no retry on empty result.
  - **H5-3.3 – Failure handling:**
      
      - Single-source failure → source marked as failed, the rest continues.
      - All mandatory failed → try extended set, then warning icon and review.
      - All failed → total verification failure (N-5, H-2).
  - **H5-3.4 – No blockade of the translation flow:** Hadith verification failures do not block flow. Preflight localization of unverified passages per §4.16 hadith verification status.

### **H5-4 – Search Modes and Normalization**

  - **H5-4.1 – Search modes:** S-1 exact wording, S-2 partial wording, S-3 source+wording, S-4 short version, S-5 isnād start, S-6 normalized OCR variant, S-7 without ḥarakāt.
  - **H5-4.2 – Normalization:** Ḥarakāt stripping in parallel, tatweel removal, hamza normalization, Alif-Maqsura/Ya variants, Tāʾ Marbūṭa/Hāʾ, OCR-typical confusions as variants.
  - **H5-4.3 – Search strategy per source** (as described in the original H5 working state; sunnah.com structured lookups only, Shamela full-text searchable within works \[working hypothesis\], dorar.net API text search with filter, extended scraping sources).

### **H5-5 – Result Object Per Source and Overall Result**

Canonized as multi-source data model (four levels, §4.16 / Chapter 5). Original field lists here as workbench derivation:

  - **H5-5.1 – Single-source result object:** quelle\_id, treffer\_status, matn\_arabisch, matn\_vokalisiert, isnad, sammlung, werk\_nummer, direktlink, hukm, hukm\_quelle, website\_uebersetzung, textnaehe, technischer\_status, zugriffszeitpunkt. Specified: einzelquelle\_uuid, gesamtergebnis\_uuid, quellen\_rolle mandatory snapshot; website\_uebersetzung as list of {lang, text}; enums treffer\_status and technischer\_status extended by quelle\_suspendiert / quelle\_nicht\_durchsucht / http\_4xx / http\_5xx.
  - **H5-5.2 – Overall result object:** autorwortlaut, autor\_genannte\_quelle, referenz\_matn, referenz\_matn\_quelle, referenz\_vokalisierung, referenz\_vokalisierung\_quelle, provenienz\_paket, konsens\_status, kutub\_as\_sitta\_signal, kutub\_as\_sitta\_abweichung\_aktiv, eskalation\_ausgefuehrt, ausgefallene\_quellen, vokalisierungs\_konflikt (strictly binary, class differentiation via derived vokalisierungsklasse), decision\_events. **Derived states:** entscheidungsstatus, vokalisierungsklasse, hadith\_stellen\_typ, hadith\_verifikationsklasse.

### **H5-6 – User Interaction and Conflict Cases**

  - Case A: consensus, automatic.
  - Case B: author source confirmed, automatic.
  - Case C: author-source conflict, three user options.
  - Case D: no author source, user decision.
  - Case E: no hit, five user options.

Plus vocalization conflict (separately determinable, V-2 → user involvement).

All actions mapped to the 7 canonized types per §4.16.

### **H5-7 – Error Classes and Mapping to §4.18**

Complete error-type table as in the original H5 working state; class A/B/C per §4.18. Notification channel class B (L-24) open.

### **H5-8 – Logging / Provenance**

**Per hadith passage:** author wording, searched sources and results, reference matn and source, reference vocalization and source, consensus status, Kutub as-Sitta signal, escalation, failed sources, authenticity grade, website translations, author source, vocalization conflict status, decision\_events, single-source hit objects.

**System-wide:** source failures, DOM breaks, API-key issues, clustering patterns.

### **H5-9 – Linkage with Internal Objects**

  - **Block UUID:** block class "hadith," provisional metadata.
  - **Sentence UUID:** translation output.
  - **Source attributes.**
  - **Decision-event UUID:** per the 7 action types.

### **H5-10 – Parallelization and Performance**

  - Mandatory sources in parallel.
  - Extended set (effectively only E-5) in parallel.
  - Aggregation point after all mandatory responses.
  - Maximum wait times (working hypotheses): mandatory 20 s, escalation 30 s.

### **H5-11 – Scraping Maintenance and Stability Assurance**

Applies to all scraping sources (dorar.net fallback, islamweb.net, جامع السنة, الوقفية, موسوعة الأحاديث as scraping case). DOM break = class B without retry. No silent self-healing.

### **H5-12 – Explicit List of Open Items (Workbench State, Partly Canonized/Closed)**

**Operational tasks:**

  - request sunnah.com API key
  - verify complete collection list via API
  - authenticity-grade consistency via test operation
  - implement HTML stripping
  - reverse-engineer dorar.net endpoints
  - empirically determine rate limits
  - test ḥarakāt sensitivity
  - monitoring for dorar.net
  - inspect scraping selectors
  - set confidence thresholds
  - timeout values after measurement
  - remaining test-operation questions for E-5 (see separate E-5 test-operation working block)

**Closed (extended set source situation):** source situation of the extended set.

**Closed (hadith verification semantics and data model):** vocalization escalation criterion, multi-source result objects data model, preflight localization of unverified hadith passages, English strand K-4 R-1/R-2.

**Partly open:** English strand K-4 R-3 (output strand).

**Still open:** notification channel class B (L-24), real Shamela actual-state survey (P-2 viability, parked).

## **WORKING BLOCK – PRE-VERIFICATION INTERFACE 5 – sunnah.com and dorar.net**

**Status:** Working draft. Not yet canon.

(Substantively fully preserved as in the previous state.)

**Core findings:**

  - sunnah.com API exists, key via GitHub issue.
  - No full-text search.
  - Kutub as-Sitta fully covered.
  - Musnad Ahmad and Darimi listed.
  - Al-Mustadrak / Majma' az-Zawa'id not listed.
  - Rate limit undocumented.
  - dorar.net API officially documented, JSON.
  - No official full-text/endpoint specification.
  - Third-party proxy as reverse-engineering basis.
  - HTML stripping required.
  - Rate limit undocumented.
  - Stability not guaranteed.
  - Scenario-3 risk finding documented: dorar.net as the only external text search in the absence of a Shamela hit.

## **WORKING BLOCK – PRE-VERIFICATION INTERFACE 5 – islamweb.net**

**Status:** Working draft. Not yet canon. Option B decided (effectively suspended).

(Substantively fully preserved.)

**Core findings:**

  - Web-based hadith access only via library section.
  - No API.
  - No structured hadith objects.
  - No web-based takhrij.
  - High implementation effort with little added value.

## **WORKING BLOCK – IDENTIFICATION AND TECHNICAL CLARIFICATION INTERFACE 5 – E-2 / "جَامِعُ السُّنَّةِ النَّبَوِيَّة"**

**Status:** Working draft. Not yet canon. Reliably identified as Alifta-/Harf variant, Option B decided (effectively suspended).

(Substantively fully preserved.)

**Core findings:**

  - Saudi Arabian Riʾāsa al-Iftāʾ and Egyptian Harf Company.
  - Web version sunnah.alifta.gov.sa and www.alifta.net.
  - Mobile App.
  - Historical desktop version.
  - 33 matn books and 55–75 auxiliary works.
  - 261,000+ ahadith.
  - No API.
  - Scraping candidate on government infrastructure with uncertainties.

## **WORKING BLOCK – PRE-VERIFICATION INTERFACE 5 – جَامِعُ الكُتُبِ التِّسْعَة**

**Status:** Working draft. Not yet canon. Option B decided (effectively suspended).

(Substantively fully preserved.)

**Core findings:**

  - Umbrella term.
  - Active variant Arabia-IT Mobile App iOS/Android without web/API.
  - Historical Harf desktop outdated.
  - Static PDFs.
  - Substantive redundancy with mandatory set.

## **WORKING BLOCK – PRE-VERIFICATION INTERFACE 5 – مَوْسُوعَةُ الأَحَادِيثِ النَّبَوِيَّة**

**Status:** Working draft. Not yet canon. Option B decided (not suspended, special role "German translation source / multilingual reference source").

(Substantively fully preserved.)

**Core findings:**

  - hadeethenc.com, IslamHouse family.
  - Official REST API v1 with five endpoints, no authentication, JSON, HTTPS.
  - No full-text search via API.
  - Official bulk downloads Excel/PDF per language.
  - Curated thematic encyclopedia of approx. 3,000 entries in 7 main categories.
  - German and English translation available.
  - Institutional sponsorship.
  - Structural parallel to §4.15 quranenc.com.

## **WORKING BLOCK – VOCALIZATION ESCALATION CRITERION INTERFACE 5 – HADITH**

**Status:** Substantively canonized in §4.16 (classes V-0/V-1/V-2, aggregation rule, fallback rule, vokalisierungs\_konflikt strictly binary with class differentiation via vokalisierungsklasse). The block remains here as derivation full text carried forward. No canon effect from this block itself; authoritative is §4.16.

(Typology T-1 through T-9 with relevance classes V-0/V-1/V-2, escalation rule, user interaction per the 7 action types, residual openness R-1 through R-10 substantively fully preserved as in the original working version.)

## **WORKING BLOCK – PREFLIGHT LOCALIZATION OF UNVERIFIED HADITH PASSAGES – INTERFACE 5**

**Status:** Substantively canonized in §4.16 and §4.7 (passage types N-1 through N-10, verification classes H-0/H-1/H-2, gate localization as a separately named group within the gate-inspection layer without a new layer and without P-/W-slot occupation, H-2 blocking, H-1 warning-based with go\_with\_warning analogous to §4.9 E-1 and decision\_source preflight\_confirmation). The block remains here as derivation full text carried forward. No canon effect from this block itself.

(Typology N-1 through N-10 with class assignment H-0/H-1/H-2, state rule per passage, user interaction, residual openness R-1 through R-10 substantively fully preserved as in the original working version.)

## **WORKING BLOCK – DATA MODEL MULTI-SOURCE RESULT OBJECTS – INTERFACE 5**

**Status:** Substantively canonized in §4.16 and Chapter 5 (four logical levels, quellen\_rolle as mandatory snapshot without dynamic re-derivation, derived states entscheidungsstatus / vokalisierungsklasse / hadith\_stellen\_typ / hadith\_verifikationsklasse, satz\_uuid as mandatory once sentence segmentation is present, immutability analogous to §4.9 E-10). The block remains here as derivation full text carried forward. No canon effect from this block itself.

(Four levels, single-source result object fields, overall result object fields, derived state logic, residual openness R-1 through R-11 substantively fully preserved as in the original working version.)

## **WORKING BLOCK – E-5 TEST OPERATION AND TECHNICAL VERIFICATION – hadeethenc.com**

**Status:** Working draft. Workbench. Not yet canon. β partial findings from earlier test operation collected (F-1 through F-16) – not canon, no impact on Document 1 or Document 2.

### **β findings (workbench state)**

**Verified in β:**

  - F-1 (only for AR and EN; structural asymmetry AR vs. non-AR; field reference only in AR)
  - F-2 (ḥarakāt complete in AR fields from API)
  - F-3 (no HTML in JSON text fields)
  - F-8 (language list 68 languages)

**Partly verified in β:**

  - F-6 (Excel link structurally evidenced for all 68 languages; column scope/encoding/ḥarakāt handling not covered)
  - F-7 (PDF only for 7 languages, no PDF for German; suitability check local index not covered)
  - F-12 (website translation structurally evidenced; substantive fit to data model not fully covered)
  - F-15 (German coverage approx. 20–21% sample; quality sample and systematic coverage matrix not covered)

**Unclear due to tool limit of the earlier test environment** (no negative finding deducible):

  - F-1 DE-API direct call
  - F-12 DE-API direct call
  - F-13 misbehavior

**Time-dependent open** (not simulatable, real test operation required):

  - F-4, F-5, F-9, F-14, F-16

**No β statement on:** F-10, F-11.

### **Open Test-Operation Questions F-1 Through F-16**

  - **F-1** Field structure /hadeeths/one/ per language
  - **F-2** Ḥarakāt return
  - **F-3** HTML markup in response
  - **F-4** Rate limit
  - **F-5** Stability and versioning
  - **F-6** Excel bulk (field scope, encoding, ḥarakāt)
  - **F-7** PDF bulk (suitability local index)
  - **F-8** Language list via API
  - **F-9** Versioning mechanics
  - **F-10** Consistency API vs. bulk download
  - **F-11** Front-end search as scraping path
  - **F-12** Website translation as data-model reference field
  - **F-13** Misbehavior
  - **F-14** Latency profile
  - **F-15** German coverage and quality sample
  - **F-16** ID stability

### **Test Plan Inspection Blocks T-1 Through T-8**

Language list, single-hadith field structure, authenticity grade/takhrij, Excel bulk, PDF bulk, rate-limit/stability/latency, versioning/ID stability, defensive front-end search.

### **Minimum Conditions for Later Canonization**

  - F-1 and F-2 at least differentiated
  - F-3 at least confirmed/differentiated
  - F-8 at least confirmed
  - F-6 or F-7 at least differentiated
  - F-4 at least differentiated
  - F-9 at least differentiated
  - F-16 at least confirmed

### **Residual Openness R-1 Through R-10**

Timeout values, rate-limit policy, scraping path, ID instability worst case, bulk-download pipeline, systematic German completeness analysis, English-strand linkage, style-feature boundary, §4.18 compatibility, data protection/license.

## **WORKING BLOCK – ENGLISH HADITH STRAND – INTERFACE 5**

**Status:** Substantively partly canonized in §4.16 and §5.1.1 (R-1 English as reference field / R-2 English as comparison language). R-3 (English as output strand, Waraq AI as primary producer, no-cascade rule for hadith, English source-citation/transliteration/footnote/style-feature logic) remains workbench. The block remains here as derivation full text carried forward.

(Three roles R-1/R-2/R-3, symmetric matn handling, asymmetric translation level, user interaction per project language combination, residual openness R-1 through R-10 substantively fully preserved as in the original working version.)

## **WORKING BLOCK – REAL SHAMELA ACTUAL-STATE SURVEY – INTERFACE 6 / HADITH REFERENCE**

**Status:** Working draft. Not yet canon. Parked. Will only be reprocessed when the user expressly takes it up again.

Stage S-1 expectation for P-2 remains a working hypothesis; no silent promotion. Real results from Interface 6 may not silently change the consolidation state of the extended hadith source set.

(Methodology with four-status classification, permissible assumptions, hadith-relevant access situation, three implementation stages S-1/S-2/S-3, consequences for H5, residual openness R-1 through R-11 substantively fully preserved as in the original working version.)

## **WORKING BLOCK – INTERFACE 5 – LIVE TEST PACKAGE (PARKED)**

**Status:** Operational workbench/auxiliary block. Not canon. Not incorporated into Document 1. No canon effect. Content is structurally complete and waits exclusively for real external execution and the playback of a filled-in return format. Real results may not silently change the already-canonized state (in particular A-4 / A-6 / A-7 / A-8, §4.16 E-5 special role, §3.5 Model U, §5.1.1 HTML stripping); entries occur only after explicit release.

### **Purpose**

Closure of the live- and API-test-dependent residual items:

  - E-5 test-operation questions F-1 / F-4 / F-9 / F-13 / F-14 / F-16
  - F-3 concrete values (rates, backoff, upper limits, resumption, clustering threshold §4.18 Track 2)
  - F-4 concrete values (timeout and retry values per source)

### **Part 1 – Execution-Ready Test-Run Block**

#### **T-A – E-5 Test Operation (hadeethenc.com)**

**Goal:** Closure of F-1, F-4, F-9, F-13, F-14, F-16; completion of partial findings on F-6, F-7, F-12, F-15.

**Preconditions:** official API base URL confirmed; no authentication required; stable network connection; inspection time and time zone documentable.

**T-A.1 Language list** GET /languages (or documented equivalent endpoint). Data collection: number of languages, ISO codes list, presence of de and en, content type, raw response (truncated).

**T-A.2 Single-hadith field structure** (fixed reference hadith ID)

  - A.2.1 Retrieve AR
  - A.2.2 Retrieve EN
  - A.2.3 Retrieve DE (closes F-1 DE)
  - A.2.4 Retrieve another language (asymmetry control)

Data collection per case: field-name list, presence/absence reference, ḥarakāt handling in matn, HTML markup yes/no, grade field name+value, takhrij field, ID schema.

**T-A.3 Authenticity grade and takhrij** 10 hadiths from various categories AR. Data collection: consistency of field names, grade value range, multiple ratings yes/no, takhrij structuring.

**T-A.4 Bulk-download field scope**

  - A.4.1 Excel bulk DE: column names, number of rows, encoding, ḥarakāt handling.
  - A.4.2 PDF bulk of one language: field scope, suitability local index.

**T-A.5 Rate limit / stability / latency**

  - A.5.1 20 sequential requests, 1 s spacing
  - A.5.2 20 requests burst
  - A.5.3 5 requests – 10 min pause – 5 requests

Data collection per series: latency min/max/median/P95, HTTP status codes, rate-limit headers, error rate, recovery behavior.

**T-A.6 Versioning / ID stability**

  - A.6.1 Generate snapshot of 10-ID set.
  - A.6.2 After ≥ 7 days retrieve the same set again.

Data collection: version field present, content identity, ID stability.

**T-A.7 Misbehavior**

  - A.7.1 Non-existent hadith ID
  - A.7.2 Wrong language code
  - A.7.3 Malformed request path

Data collection: HTTP status code, response body, timeout behavior.

**T-A.8 German coverage matrix** DE hadith list against AR master list (Excel bulk or list endpoint). Data collection: coverage rate in %, non-covered categories.

#### **T-B – Timeout/Retry Calibration**

**Goal:** Calibrated timeout and retry values per external source.

**T-B.1 Latency profile per source** (20 sequential retrievals; 10 for scraping): sunnah.com, dorar.net API, dorar.net scraping, E-5 (from A.5.1), islamweb.net, جامع السنة, الوقفية, Shamela local. Data collection: min, max, median, P95.

**T-B.2 Stability 24 h per source** (100 retrievals distributed). Data collection: outlier rate \> 3× median, timeout rate, time-of-day pattern.

**T-B.3 Retry behavior per source** (10 controlled error scenarios). Data collection: success rate first retry, time to success.

#### **T-C – Rates / Backoff / Clustering Thresholds**

**Goal:** Calibrated rates, backoff, upper limits, resumption, clustering threshold §4.18 Track 2.

**T-C.1 Rate upper limit per source** – stepwise increase to the first stable occurrence of 429/503/DOM break/timeout clustering. Data collection: threshold in req/min or req/h, response type at the limit.

**T-C.2 Backoff effect per source** (10 s / 60 s / 300 s). Data collection: minimum pause until first successful resumption, minimum pause until full normal rate.

**T-C.3 Clustering threshold §4.18 Track 2** – derive from B.2. Data collection: threshold proposal per source (errors/100 req; errors/h; errors/day).

**T-C.4 Overall budget per source.** Data collection: target rate, backoff plan, resumption time, clustering threshold – as proposal matrix.

### **Part 2 – Operator Short Form (Minimum Block First Closure Run)**

**Preparation:**

  - hadeethenc.com test-ready
  - fix and note one reference hadith ID

**Step 1 – Language list**

  - call /languages once
  - note: number of languages, DE yes/no, EN yes/no

**Step 2 – Field structure of the same hadith ID**

  - retrieve AR → field names, reference yes/no, ḥarakāt, HTML, grade, ID schema
  - retrieve EN → field names, reference yes/no, HTML
  - retrieve DE → field names, reference yes/no, HTML

**Step 3 – Latency series with spacing**

  - 20 retrievals of the same AR hadith ID, 1 s spacing each
  - log latency in ms and status code per request
  - at the end min, max, median, P95; note rate-limit headers

**Step 4 – Latency series burst**

  - 20 retrievals without spacing
  - log latency and status code per request
  - at the end min, max, median, P95, error rate

**Return:**

  - enter values into the return format (Part 3)
  - leave blank what was not measured

### **Part 3 – Compact Return Format**

WARAQ LIVE TEST RUN RETURN

  

Inspector:           \_\_\_\_\_

Date start:          \_\_\_\_\_

Date end:            \_\_\_\_\_

Environment / network: \_\_\_\_\_

Time zone:           \_\_\_\_\_

  

\===== T-A  E-5 TEST OPERATION =====

  

Reference hadith ID: \_\_\_\_\_

  

T-A.1 Language list

  Endpoint:            \_\_\_\_\_

  Number of languages: \_\_\_\_\_

  DE present:          \_\_\_\_\_

  EN present:          \_\_\_\_\_

  Content-Type:        \_\_\_\_\_

  Anomalies:           \_\_\_\_\_

  Status: ☐

  

T-A.2 Single-hadith field structure

  A.2.1 AR field names:                  \_\_\_\_\_

  A.2.1 AR reference present:            \_\_\_\_\_

  A.2.1 AR ḥarakāt:                      \_\_\_\_\_

  A.2.1 AR HTML markup:                  \_\_\_\_\_

  A.2.2 EN field names:                  \_\_\_\_\_

  A.2.2 EN reference present:            \_\_\_\_\_

  A.2.3 DE field names:                  \_\_\_\_\_

  A.2.3 DE reference present:            \_\_\_\_\_

  A.2.3 DE deviations from AR:           \_\_\_\_\_

  A.2.4 Other language:                  \_\_\_\_\_

  Status: ☐

  

T-A.3 Authenticity grade / takhrij

  Sample size:                       \_\_\_\_\_

  Field name grade:                  \_\_\_\_\_

  Value range grade:                 \_\_\_\_\_

  Multiple ratings:                  \_\_\_\_\_

  Takhrij structuring:               \_\_\_\_\_

  Consistency (high/medium/low):     \_\_\_\_\_

  Status: ☐

  

T-A.4 Bulk downloads

  A.4.1 Excel DE column count:         \_\_\_\_\_

  A.4.1 Excel DE column names:         \_\_\_\_\_

  A.4.1 Excel DE encoding:             \_\_\_\_\_

  A.4.1 Excel DE ḥarakāt:              \_\_\_\_\_

  A.4.1 Excel DE row count:            \_\_\_\_\_

  A.4.2 PDF language:                  \_\_\_\_\_

  A.4.2 PDF field scope:               \_\_\_\_\_

  A.4.2 PDF index suitability:         \_\_\_\_\_

  Status: ☐

  

T-A.5 Rate limit / stability / latency

  A.5.1 20 seq 1s  Min/Max/Median/P95 ms: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  A.5.1 HTTP status codes:                 \_\_\_\_\_

  A.5.2 Burst 20    Min/Max/Median/P95 ms: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  A.5.2 HTTP status codes:                 \_\_\_\_\_

  A.5.2 Error rate:                        \_\_\_\_\_

  A.5.3 5+pause+5 anomalies:               \_\_\_\_\_

  Rate-limit headers:                      \_\_\_\_\_

  Status: ☐

  

T-A.6 Versioning / ID stability

  Snapshot date:                  \_\_\_\_\_

  Rerun date:                     \_\_\_\_\_

  Version field present (name):   \_\_\_\_\_

  Content identity:               \_\_\_\_\_

  ID stability:                   \_\_\_\_\_

  Status: ☐

  

T-A.7 Misbehavior

  A.7.1 Non-existent ID  – status / body: \_\_\_\_\_ / \_\_\_\_\_

  A.7.2 Wrong language code – status / body: \_\_\_\_\_ / \_\_\_\_\_

  A.7.3 Malformed path     – status / body: \_\_\_\_\_ / \_\_\_\_\_

  Timeout behavior:                          \_\_\_\_\_

  Status: ☐

  

T-A.8 German coverage

  Method:                             \_\_\_\_\_

  AR master list count:               \_\_\_\_\_

  DE list count:                      \_\_\_\_\_

  Coverage rate %:                    \_\_\_\_\_

  Non-covered categories:             \_\_\_\_\_

  Status: ☐

  

\===== T-B  TIMEOUT/RETRY CALIBRATION =====

  

T-B.1 Latency profile (Min/Max/Median/P95 ms)

  sunnah.com:         \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  dorar.net API:      \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  dorar.net scraping: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  E-5:                \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  islamweb.net:       \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  جامع السنة:         \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  الوقفية:            \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  Shamela local:      \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  Status: ☐

  

T-B.2 Outliers / stability 24h (outliers / timeout rate / time-of-day pattern)

  sunnah.com:         \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  dorar.net API:      \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  dorar.net scraping: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  E-5:                \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  islamweb.net:       \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  جامع السنة:         \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  الوقفية:            \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  Shamela local:      \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  Status: ☐

  

T-B.3 Retry behavior (success % / time to success)

  sunnah.com:         \_\_\_\_\_ / \_\_\_\_\_

  dorar.net API:      \_\_\_\_\_ / \_\_\_\_\_

  dorar.net scraping: \_\_\_\_\_ / \_\_\_\_\_

  E-5:                \_\_\_\_\_ / \_\_\_\_\_

  islamweb.net:       \_\_\_\_\_ / \_\_\_\_\_

  جامع السنة:         \_\_\_\_\_ / \_\_\_\_\_

  الوقفية:            \_\_\_\_\_ / \_\_\_\_\_

  Shamela local:      \_\_\_\_\_ / \_\_\_\_\_

  Status: ☐

  

\===== T-C  RATES / BACKOFF / CLUSTERING THRESHOLDS =====

  

T-C.1 Rate upper limit (req/min or req/h / response type at the limit)

  sunnah.com:         \_\_\_\_\_ / \_\_\_\_\_

  dorar.net API:      \_\_\_\_\_ / \_\_\_\_\_

  dorar.net scraping: \_\_\_\_\_ / \_\_\_\_\_

  E-5:                \_\_\_\_\_ / \_\_\_\_\_

  islamweb.net:       \_\_\_\_\_ / \_\_\_\_\_

  جامع السنة:         \_\_\_\_\_ / \_\_\_\_\_

  الوقفية:            \_\_\_\_\_ / \_\_\_\_\_

  Status: ☐

  

T-C.2 Backoff effect (minimum pause until resumption / until normal rate)

  sunnah.com:         \_\_\_\_\_ / \_\_\_\_\_

  dorar.net API:      \_\_\_\_\_ / \_\_\_\_\_

  dorar.net scraping: \_\_\_\_\_ / \_\_\_\_\_

  E-5:                \_\_\_\_\_ / \_\_\_\_\_

  islamweb.net:       \_\_\_\_\_ / \_\_\_\_\_

  جامع السنة:         \_\_\_\_\_ / \_\_\_\_\_

  الوقفية:            \_\_\_\_\_ / \_\_\_\_\_

  Status: ☐

  

T-C.3 Clustering threshold §4.18 Track 2 (errors/100 req / errors/h / errors/day)

  sunnah.com:         \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  dorar.net API:      \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  dorar.net scraping: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  E-5:                \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  islamweb.net:       \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  جامع السنة:         \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  الوقفية:            \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  Status: ☐

  

T-C.4 Overall budget (target rate / backoff plan / resumption / clustering threshold)

  sunnah.com:         \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  dorar.net API:      \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  dorar.net scraping: \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  E-5:                \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  islamweb.net:       \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  جامع السنة:         \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  الوقفية:            \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_ / \_\_\_\_\_

  Status: ☐

  

\===== CLOSURE =====

  

Completed sub-tests:                 \_\_\_\_\_

Open sub-tests:                      \_\_\_\_\_

Anomalies across all sources:        \_\_\_\_\_

Overall status: ☐ T-A  ☐ T-B  ☐ T-C

  

### **Part 4 – Closure Matrix**

|  |  |  |  |
| :-: | :-: | :-: | :-: |
| **Finding** | **Closes** | **Result** | **Document area** |
| A.1 Language list | F-8 | Confirmation of β finding | §4.16 |
| A.2.3 DE field structure | F-1 DE | Canonizable mini-block | §5.1.1 / §4.16 |
| A.2.1 ḥarakāt AR | F-2 (E-5) | Confirmation of β finding | §4.16 |
| A.2 HTML markup presence | F-3 (E-5) | Confirmation of β finding | §4.16 / §5.1.1 |
| A.3 grade field structure | F-6 Model H | check under schema filter | §5.1.1 |
| A.4.1 Excel field scope | F-6 | Canonizable mini-block | §4.16 / §5.1.1 |
| A.4.2 PDF field scope | F-7 | Mini-block or workbench | §4.16 |
| A.4 vs A.2 consistency | F-10 | Workbench remains open | — |
| A.5 latency profile E-5 | F-14 | Canonizable mini-block | §3.5 Model U |
| A.5 rate-limit headers / burst | F-4 rate E-5 | Canonizable mini-block | §3.5 Model U |
| A.6 version field | F-9 | Canonizable mini-block | §4.16 |
| A.6 ID stability | F-16 | Canonizable mini-block | §4.16 / §5.1.1 |
| A.7 misbehavior | F-13 | Canonizable mini-block | §4.16 / §4.18 |
| A.8 DE coverage rate | F-15 | Canonizable mini-block | §4.16 |
| — | F-11 | Expansion path / optional | — |
| — | F-12 | already canonized (R-1/R-2) | — |
| B.1 latency profiles all sources | F-4 timeouts | Canonizable mini-block | §3.5 Model U |
| B.2 outliers / timeout rates | F-4 retry | Canonizable mini-block | §3.5 Model U / §4.18 |
| B.3 retry success rates | F-4 upper limits | Canonizable mini-block | §3.5 Model U |
| C.1 rate upper limits | F-3 rate | Canonizable mini-block | §3.5 Model U |
| C.2 backoff recovery | F-3 backoff | Canonizable mini-block | §3.5 Model U |
| C.3 clustering thresholds | F-3 §4.18 Tr.2 | Canonizable mini-block | §4.18 Track 2 |
| C.4 overall budget per source | F-3 cons. | Canonizable mini-block | §3.5 Model U |
| — | F-4 Model W | Workbench remains open | — |
| — | Model A | Expansion path / optional | — |
| — | Model S | Expansion path / optional | — |

**End of Block 3.**
