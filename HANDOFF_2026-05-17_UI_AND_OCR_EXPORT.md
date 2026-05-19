# Handoff 2026-05-17

Purpose: compact resume note for the next agent/session after context compaction.

Read order:
1. This file
2. [WORKLOG.md](./WORKLOG.md)
3. Relevant files linked below

## What Was Done

- Redesigned the frontend shell and dashboard to match the provided reference more closely:
  - branded left sidebar
  - calmer top header
  - new dashboard hero and empty state
  - English-only visible labels in the main workspace shell
- Main frontend files changed:
  - [frontend/src/components/AppShell.tsx](./frontend/src/components/AppShell.tsx)
  - [frontend/src/pages/Dashboard.tsx](./frontend/src/pages/Dashboard.tsx)
  - [frontend/src/pages/ProjectWorkspace.tsx](./frontend/src/pages/ProjectWorkspace.tsx)
  - [frontend/src/components/PageList.tsx](./frontend/src/components/PageList.tsx)
  - [frontend/src/components/OcrReviewBar.tsx](./frontend/src/components/OcrReviewBar.tsx)
  - [frontend/src/index.css](./frontend/src/index.css)

- Fixed one OCR export download bug:
  - newly created OCR export events now persist the selected export config
  - download rebuild now uses saved `page_range`, `block_types_enabled`, `markings_enabled`, and `mode`
- Files changed for that fix:
  - [backend/waraq/ocr_export/service.py](./backend/waraq/ocr_export/service.py)
  - [backend/waraq/api/routers/ocr_export_router.py](./backend/waraq/api/routers/ocr_export_router.py)
  - [backend/tests/api/test_ocr_export_routes.py](./backend/tests/api/test_ocr_export_routes.py)

- Found and fixed the more serious OCR export bug:
  - OCR text export was outputting translated German text for Arabic-source projects
  - root cause: translation writes to `segments.text_content`, and OCR export had been reading `segments.text_content` directly
  - fix: OCR export now resolves the latest non-`re_translate` revision per segment instead of trusting the mutable current cache
- Files changed for that fix:
  - [backend/waraq/ocr_export/docx_builder.py](./backend/waraq/ocr_export/docx_builder.py)
  - [backend/tests/ocr_export/test_ocr_export.py](./backend/tests/ocr_export/test_ocr_export.py)

- Started the broader source-vs-translation restructuring:
  - added a shared backend resolver for canonical source/target lookup from revision history
  - rewired the highest-risk consumers away from ambiguous direct reads of `segments.text_content`
- New shared resolver:
  - [backend/waraq/text_state.py](./backend/waraq/text_state.py)
- Consumers already migrated to the shared resolver:
  - [backend/waraq/ocr_export/docx_builder.py](./backend/waraq/ocr_export/docx_builder.py)
  - [backend/waraq/export/docx_builder.py](./backend/waraq/export/docx_builder.py)
  - [backend/waraq/api/routers/hadith_router.py](./backend/waraq/api/routers/hadith_router.py)
  - [backend/waraq/toc/service.py](./backend/waraq/toc/service.py)
  - [backend/waraq/translation/service.py](./backend/waraq/translation/service.py)
  - [backend/waraq/translation/persistence.py](./backend/waraq/translation/persistence.py)
  - [backend/waraq/rule_binding/service.py](./backend/waraq/rule_binding/service.py)
  - [backend/waraq/consistency/rules.py](./backend/waraq/consistency/rules.py)

- Fixed the `Translate & export` reopen gate bug:
  - the dialog had been treating "translation completed in this open modal session" as the only condition for enabling preflight
  - closing and reopening the dialog reset local state, forcing the user to rerun translation even when persisted translation revisions already existed
  - fix: added a lightweight project-level translation availability endpoint and changed the dialog to treat persisted project translation as a valid ready state for preflight
- Files changed for that fix:
  - [backend/waraq/api/routers/projects_router.py](./backend/waraq/api/routers/projects_router.py)
  - [backend/waraq/api/schemas.py](./backend/waraq/api/schemas.py)
  - [backend/tests/api/test_projects_routes.py](./backend/tests/api/test_projects_routes.py)
  - [frontend/src/components/TranslationExportDialog.tsx](./frontend/src/components/TranslationExportDialog.tsx)
  - [frontend/src/lib/types.ts](./frontend/src/lib/types.ts)

- Fixed the translation export download-path bug:
  - `Download DOCX` / `Download PDF` in the translation export dialog were fetching raw `/exports/...` paths instead of the API-prefixed route
  - in this frontend setup that can download a tiny non-document response instead of the actual artefact bytes
  - fix: switched the dialog to use `apiPath(...)` like the working OCR export flow, and added a content-type sanity check before saving the blob
- File changed for that fix:
  - [frontend/src/components/TranslationExportDialog.tsx](./frontend/src/components/TranslationExportDialog.tsx)

- Restructured project-workspace edit mode:
  - edit mode no longer swaps to a separate single-column editor
  - the same workspace modes (`Orig|OCR`, `Orig|DE`, `OCR|DE`, `Triple`, `Solo`) now remain available in edit mode
  - OCR and Translation panes can both be edited inline when edit mode is active
  - added a page-scoped translation runner button in the workspace toolbar
- Files changed for that restructuring:
  - [frontend/src/pages/ProjectWorkspace.tsx](./frontend/src/pages/ProjectWorkspace.tsx)
  - [frontend/src/components/OcrReviewBar.tsx](./frontend/src/components/OcrReviewBar.tsx)
  - [frontend/src/components/OcrPane.tsx](./frontend/src/components/OcrPane.tsx)
  - [frontend/src/components/TranslationPane.tsx](./frontend/src/components/TranslationPane.tsx)
  - [frontend/src/components/PageTranslationPanel.tsx](./frontend/src/components/PageTranslationPanel.tsx)
  - [frontend/src/lib/segment-history.ts](./frontend/src/lib/segment-history.ts)

- Added dedicated manual translation editing on the backend:
  - new route `PUT /segments/{satz_uuid}/translation-text`
  - writes a manual `re_translate` revision so target-side edits stay distinct from OCR/source-side edits
- Files changed for that backend support:
  - [backend/waraq/api/schemas.py](./backend/waraq/api/schemas.py)
  - [backend/waraq/api/routers/segments_router.py](./backend/waraq/api/routers/segments_router.py)
  - [backend/tests/api/test_pages_segments_routes.py](./backend/tests/api/test_pages_segments_routes.py)

- Upgraded project-level translation availability from "exists" to "freshness-aware":
  - the endpoint now reports translated, fresh-translated, stale-translated, and untranslated segment counts
  - a translation is considered stale when the latest source-side revision is newer than the latest `re_translate` revision for that segment
  - the translation export dialog now unlocks preflight only when the whole project has a fully fresh translation state
- Files changed for that upgrade:
  - [backend/waraq/api/schemas.py](./backend/waraq/api/schemas.py)
  - [backend/waraq/api/routers/projects_router.py](./backend/waraq/api/routers/projects_router.py)
  - [backend/tests/api/test_projects_routes.py](./backend/tests/api/test_projects_routes.py)
  - [frontend/src/lib/types.ts](./frontend/src/lib/types.ts)
  - [frontend/src/components/TranslationExportDialog.tsx](./frontend/src/components/TranslationExportDialog.tsx)

- Translation now receives full-page OCR context per segment:
  - each translation chunk now carries transient page-level source context built from the current page's ordered OCR/source text
  - OpenAI + Gemini prompts now explicitly tell the models to use the full page flow for context while translating only the current span
  - standalone page-number / pagination-marker segments are handled deterministically and passed through unchanged instead of producing refusal-style explanatory output
- Files changed for that translation-context upgrade:
  - [backend/waraq/translation/service.py](./backend/waraq/translation/service.py)
  - [backend/waraq/translation/openai_translator.py](./backend/waraq/translation/openai_translator.py)
  - [backend/waraq/translation/gemini_translator.py](./backend/waraq/translation/gemini_translator.py)

- Audit detail now exposes translation engines explicitly:
  - the segment detail payload now includes translation primary/check engine labels from the TRANSLATION-PO cross-check payload
  - the frontend audit detail panel now shows `Primary` and `Check` engine names next to the translation cross-check situation
- Files changed for that audit clarification:
  - [backend/waraq/audit_dashboard/service.py](./backend/waraq/audit_dashboard/service.py)
  - [backend/waraq/api/routers/audit_dashboard_router.py](./backend/waraq/api/routers/audit_dashboard_router.py)
  - [frontend/src/pages/ProjectAudit.tsx](./frontend/src/pages/ProjectAudit.tsx)

- Relaxed the per-page OCR timeout:
  - the single-page OCR route was still hard-bounded by the shared per-page timeout and could return 504 on real pages before OCR completed
  - `OCR_PER_PAGE_TIMEOUT_SECONDS` is now configurable via env and defaults to 600s instead of 240s
  - this is a stopgap to reduce false timeout failures while the deeper "page-wide OCR instead of internal segmentation" redesign is still pending
- File changed for that fix:
  - [backend/waraq/ocr/auto_run.py](./backend/waraq/ocr/auto_run.py)

- Switched OCR page runs to page-wide mode by default:
  - the page runner now treats the full page as one `MAIN_TEXT` OCR unit by default instead of first splitting it with the OpenCV block detector
  - this is controlled by `OCR_PAGE_WIDE_MODE` and currently defaults to enabled (`1`)
  - the older segmented layout path is still available behind `OCR_PAGE_WIDE_MODE=0`
- File changed for that behavior change:
  - [backend/waraq/ocr/page_runner.py](./backend/waraq/ocr/page_runner.py)

- Fixed the immediate page-wide OCR regression and then reduced its runtime cost:
  - imported the missing `ReadingDirection` enum that had broken the first page-wide OCR path
  - hardened project OCR auto-run so unexpected exceptions fail the job instead of leaving the UI apparently running forever
  - strengthened the Gemini OCR prompt to preserve visible line breaks, paragraph breaks, blank separator lines, page numbers, and running headers instead of reflowing text
  - page-wide OCR retains the canonical double-engine OCR plus Stage-3 validator flow by default
  - the single-engine page-wide path still exists only as an explicit env fallback
  - env toggles:
    - `OCR_PAGE_WIDE_MULTI_ENGINE=1` by default
    - `OCR_PAGE_WIDE_STAGE3=1` by default
- Files changed for that follow-up:
  - [backend/waraq/ocr/page_runner.py](./backend/waraq/ocr/page_runner.py)
  - [backend/waraq/ocr/auto_run.py](./backend/waraq/ocr/auto_run.py)
  - [backend/waraq/ocr/gemini.py](./backend/waraq/ocr/gemini.py)

## Key Diagnosis

The current data model mixes source and translation concerns.

- `create_revision()` always updates `segments.current_rev_uuid` and `segments.text_content`
  - [backend/waraq/revision/service.py](./backend/waraq/revision/service.py)
- translation persistence uses that same revision service with `change_source = re_translate`
  - [backend/waraq/translation/persistence.py](./backend/waraq/translation/persistence.py)
- so after translation, `segments.text_content` may hold target-language text
- meanwhile:
  - OCR pane works around this by reading history and picking the oldest non-translation revision
    - [frontend/src/components/OcrPane.tsx](./frontend/src/components/OcrPane.tsx)
  - Translation pane reads the latest `re_translate` revision from history
    - [frontend/src/components/TranslationPane.tsx](./frontend/src/components/TranslationPane.tsx)
  - OCR export had been using `segments.text_content` directly
    - now patched in [backend/waraq/ocr_export/docx_builder.py](./backend/waraq/ocr_export/docx_builder.py)

This means the app currently has an inconsistent text model:
- some features assume `text_content` is source
- some assume it is current target
- some assume combined `source\n---\ntarget`
- some reconstruct from revisions

The restructuring direction now in code is:
- latest non-`re_translate` revision = canonical source-side text
- latest `re_translate` revision = canonical target-side text
- `segments.text_content` is treated as a mutable fallback / compatibility cache, not the authoritative read path for mixed source-target logic

## Current Truth

After the latest patch:

- new OCR exports should download with the correct export protocol metadata
- OCR text export should now export Arabic/source-side text again, even after translation has run
- translation jobs now send Arabic/source-side text to the translator even when a prior German translation already exists
- translation persistence now compares against the latest resolved target-side text rather than the mutable cache
- translation DOCX export, TOC detection/editing, hadith verification, glossary matching, and consistency checks now read canonical source/target state via the shared resolver
- `Translate & export` now lets the user open preflight after reopening the dialog as long as the project already has persisted translation revisions
- page-level workspace editing now marks translations as outdated when a newer OCR/source revision exists for the same segment
- manual translation edits clear that outdated state naturally by writing a newer `re_translate` revision
- translation export preflight no longer unlocks merely because some translation exists; it now requires all project segments to be freshly translated relative to the latest OCR/source edits
- translation no longer treats isolated pagination-only segments as normal prose chunks; page markers are preserved without commentary
- new OCR page runs now default to one full-page OCR segment instead of internal multi-block segmentation
- page-wide OCR still defaults to the heavier canonical path: Gemini + OpenAI OCR + Stage-3 OCR validation
- this means real-world runtime can still be high, and any future speedup work should preserve that verification guarantee unless the user explicitly opts out
- `GET /ocr/projects/{project_uuid}/ocr-jobs/in-flight` only tracks project-wide auto-run jobs; it is expected to return `null` during a single-page `Run OCR` action because per-page OCR is still a synchronous request, not a detached tracked job

But:

- old OCR export events created before the metadata fix may still download with incorrect protocol values
- not every consumer has been migrated yet
- the broader source/translation storage model is still inconsistent and needs further restructuring
- OCR persistence/review is still structurally based on `Block` + `Segment` rows, but new page runs now default to one full-page `MAIN_TEXT` block/segment instead of multi-block layout splitting
- the stronger OCR prompt should improve paragraph/blank-line fidelity, but there is not yet a dedicated structural post-processor for whitespace/layout reconstruction beyond what the OCR engine returns

## Recommended Next Task

Continue the focused restructuring pass on source vs translation text storage.

Recommended objective:
- define one canonical rule for where Arabic source lives
- define one canonical rule for where translated target text lives
- remove the current mix of:
  - mutable `segments.text_content`
  - history reconstruction
  - implicit `source\n---\ntarget` splitting

Likely investigation targets:
- [backend/waraq/revision/service.py](./backend/waraq/revision/service.py)
- [backend/waraq/audit/rules.py](./backend/waraq/audit/rules.py)
- [backend/waraq/audit/service.py](./backend/waraq/audit/service.py)
- [backend/waraq/audit_dashboard/service.py](./backend/waraq/audit_dashboard/service.py)
- [backend/waraq/canon_rules/verifier.py](./backend/waraq/canon_rules/verifier.py)
- [backend/waraq/preflight/guard_near.py](./backend/waraq/preflight/guard_near.py)
- [frontend/src/components/OcrPane.tsx](./frontend/src/components/OcrPane.tsx)
- [frontend/src/components/TranslationPane.tsx](./frontend/src/components/TranslationPane.tsx)

Why audit is still open:
- `backend/waraq/audit/rules.py` is intentionally DB-free and still derives source/target from `segment.text_content`
- a clean fix likely means enriching the audit runner context in [backend/waraq/audit/service.py](./backend/waraq/audit/service.py) so rules can read pre-resolved source/target without adding DB access to individual rule functions

## Suggested Restructuring Direction

Prefer one of these, and make the whole app consistent:

Option A:
- keep source and target in distinct fields/models
- safest long-term

Option B:
- keep current revision-history approach, but formally define:
  - latest non-translation revision = source
  - latest translation revision = target
- then stop relying on `segments.text_content` for ambiguous read paths

Current implementation status:
- this option is now partially implemented in [backend/waraq/text_state.py](./backend/waraq/text_state.py)
- the next pass should keep migrating remaining ambiguous readers onto that helper or an equivalent runner-level snapshot

## Verification Notes

- Frontend build passed during the UI redesign work.
- Python compile checks passed for the latest backend edits, including the shared text-state restructuring wave.
- Full pytest runs were not executed in this sandbox because the available venv does not include `pytest`.

## User Context

- User explicitly approved moving from UI redesign into critical restructuring.
- User reported OCR export producing German explanatory text from an Arabic OCR source that had later been translated.
- This report was valid and led to the OCR export source-selection fix above.

- Fixed a UI refresh bug in single-page OCR:
  - `Run OCR` could return 200 and persist new OCR text, but the workspace still looked unchanged
  - root cause: the success path invalidated the page-segments query but not the per-segment history queries
  - the OCR pane prefers source text from history, so stale history could mask the new OCR revision
- File changed for that fix:
  - [frontend/src/components/OcrReviewBar.tsx](./frontend/src/components/OcrReviewBar.tsx)

- Improved Cloud Vision fallback OCR structure handling:
  - when Gemini OCR is unavailable, Cloud Vision OCR now reconstructs text from the document structure tree instead of trusting flattened `full_text_annotation.text`
  - this preserves paragraph boundaries, line endings, and page-number/header paragraphs better in page-wide OCR
  - Stage-2/Stage-3 verification flow was left intact; this change improves the candidate text entering that pipeline
- Files changed for that fallback improvement:
  - [backend/waraq/ocr/cloud_vision.py](./backend/waraq/ocr/cloud_vision.py)
  - [backend/tests/ocr/test_cloud_vision_adapter.py](./backend/tests/ocr/test_cloud_vision_adapter.py)

- Replaced Cloud Vision as the active secondary OCR engine with OpenAI OCR:
  - non-QURAN OCR routing now uses `Gemini + OpenAI`
  - the page runner now injects the new OpenAI OCR adapter instead of Cloud Vision for Stage-2 OCR consensus
  - the OCR consensus and Stage-3 verification flow remain in place; this is an engine swap, not a downgrade
  - Cloud Vision code still exists in the repo but should be treated as sidelined from the main OCR path
- Files changed for that engine migration:
  - [backend/waraq/ocr/openai_ocr.py](./backend/waraq/ocr/openai_ocr.py)
  - [backend/waraq/ocr/routing.py](./backend/waraq/ocr/routing.py)
  - [backend/waraq/ocr/consensus.py](./backend/waraq/ocr/consensus.py)
  - [backend/waraq/ocr/page_runner.py](./backend/waraq/ocr/page_runner.py)
  - [backend/tests/ocr/test_stage2_routing_and_consensus.py](./backend/tests/ocr/test_stage2_routing_and_consensus.py)
  - [backend/tests/ocr/test_stage3_aggregator.py](./backend/tests/ocr/test_stage3_aggregator.py)
  - [backend/tests/ocr/test_kraken_adapter.py](./backend/tests/ocr/test_kraken_adapter.py)
  - [backend/tests/audit_dashboard/test_service.py](./backend/tests/audit_dashboard/test_service.py)

- Improved page-wide OCR paragraph preservation without restoring persistent page segmentation:
  - page-wide OCR still persists one page-level segment/block
  - this pass originally experimented with internal multi-region OCR to recover spacing, but that increased Gemini request count, latency, and unpredictability
- File changed for that layout-aware OCR assembly:
  - [backend/waraq/ocr/page_runner.py](./backend/waraq/ocr/page_runner.py)

- Fixed bulk OCR cancel responsiveness:
  - project-wide OCR cancel no longer waits only for the next page boundary
  - the runner now polls the cancel flag while the current page OCR task is still in flight and terminates the job promptly when cancellation is requested
  - added regression coverage for cancelling during a long-running page OCR
- Files changed for that cancel fix:
  - [backend/waraq/ocr/auto_run.py](./backend/waraq/ocr/auto_run.py)
  - [backend/tests/ocr/test_auto_run_service.py](./backend/tests/ocr/test_auto_run_service.py)

- Hardened bulk OCR cancellation again:
  - added an in-process live-task registry for the current page OCR task per auto-run job
  - the cancel endpoint now directly cancels the live page task in addition to setting `cancel_requested=true`
  - added regression coverage for cancelling a registered live page task

- Fixed restart/refresh resurrection of cancelled OCR jobs:
  - the orphan reaper now immediately fails `cancel_requested=true` OCR auto-run jobs even if their heartbeat is still fresh
  - the `/ocr/projects/{project_uuid}/ocr-jobs/in-flight` resume endpoint now runs the orphan reaper before returning a job
  - this prevents a restarted backend from reviving stale `Cancelling…` UI state for dead bulk OCR jobs
- Files changed for that stale-cancel fix:
  - [backend/waraq/ocr/auto_run.py](./backend/waraq/ocr/auto_run.py)
  - [backend/waraq/api/routers/ocr_router.py](./backend/waraq/api/routers/ocr_router.py)
  - [backend/tests/ocr/test_auto_run_service.py](./backend/tests/ocr/test_auto_run_service.py)
  - [backend/tests/api/test_ocr_auto_run_routes.py](./backend/tests/api/test_ocr_auto_run_routes.py)

- Tightened OCR engine output handling for page numbers and refusal text:
  - Gemini and OpenAI OCR prompts now explicitly say to preserve the numeral glyph system exactly as printed
  - added OCR postprocessing that strips obvious assistant commentary/refusal tails before consensus and persistence
  - added regression coverage for the OpenAI refusal-tail case reported by the user
- Hardened OCR behavior further after live user reports:
  - Gemini OCR now retries short bursts of `429` / quota-style failures with configurable backoff instead of failing immediately
  - new env knobs in code: `GEMINI_OCR_MAX_ATTEMPTS` default `3`, `GEMINI_OCR_RETRY_BACKOFF_SECONDS` default `2`
  - OCR refusal/apology cleanup was broadened to catch more OpenAI-style English assistant lines such as `Sorry`, `I'm sorry`, `I can't help with that`, and `How else can I help`
  - diagnosis: Gemini "too many requests" was being amplified by the internal multi-region page-wide OCR experiment plus Gemini-backed verification
  - diagnosis: OpenAI page-number inconsistency is partly cleaned up by sanitizer/prompt hardening, but if the model truly misses a tiny footer number the next correct fix is page-number-specific footer/header detection during page assembly rather than more prompt tuning
- Files changed for that OCR-output cleanup:
  - [backend/waraq/ocr/postprocess.py](./backend/waraq/ocr/postprocess.py)
  - [backend/waraq/ocr/gemini.py](./backend/waraq/ocr/gemini.py)
  - [backend/waraq/ocr/openai_ocr.py](./backend/waraq/ocr/openai_ocr.py)
  - [backend/tests/ocr/test_postprocess.py](./backend/tests/ocr/test_postprocess.py)

- Simplified the page-wide OCR architecture again:
  - page-wide OCR now does one full-page OCR call per active engine instead of splitting the page into multiple internal OCR regions
  - this keeps the persisted model and the OCR execution model aligned around the page as the primary unit
  - expected effects: fewer Gemini requests per page, fewer rate-limit bursts, lower latency, and easier debugging of OCR disagreements
  - tradeoff: paragraph and blank-line fidelity now depends more directly on the engines/prompts and less on region-level reconstruction, so if layout fidelity is still not good enough the next fix should be structural postprocessing or dedicated footer/header detection rather than reintroducing multi-call OCR fan-out
- Files changed for that simplification:
  - [backend/waraq/ocr/page_runner.py](./backend/waraq/ocr/page_runner.py)

- Hardened translation against dropped page numbers and silent partial output:
  - added a deterministic line-tag protocol so translators now receive tagged source lines like `[[L0001]] ...`
  - both OpenAI and Gemini translators are now instructed to return every tag exactly once and in order
  - pagination/marker lines are treated as protected passthrough lines and are restored exactly from source instead of trusting the model
  - blank lines are also represented explicitly in the protocol so the model cannot silently collapse them without failing validation
  - translation output is now parsed and validated; if tags are missing or content is empty for a text line, that response is rejected and retried instead of being accepted as a completed translation
  - this directly targets three live issues: page numbers being translated or dropped, inconsistent carry-through of page markers, and pages being marked translated even when only the first few lines were returned
  - follow-up fix: long page-wide translations are now automatically split into smaller tagged batches before calling OpenAI/Gemini, then reassembled after validation
  - this addresses real failures like `missing translation line tag L0031`, where a model returned the first part of a long page and silently dropped the tail
  - new env knobs in code: `TRANSLATION_BATCH_MAX_LINES` default `20`, `TRANSLATION_BATCH_MAX_CHARS` default `2500`
- Files changed for that translation hardening:
  - [backend/waraq/translation/line_protocol.py](./backend/waraq/translation/line_protocol.py)
  - [backend/waraq/translation/openai_translator.py](./backend/waraq/translation/openai_translator.py)
  - [backend/waraq/translation/gemini_translator.py](./backend/waraq/translation/gemini_translator.py)
  - [backend/waraq/translation/service.py](./backend/waraq/translation/service.py)
  - [backend/tests/translation/test_line_protocol.py](./backend/tests/translation/test_line_protocol.py)

- Added a first protected-passage pass ahead of the normal LLM translators:
  - translation now checks each segment for protected Qur'an/Hadith handling before calling OpenAI/Gemini
  - Qur'an:
    - if the segment is recognized as Qur'an via the local AR reference matcher, the app now pulls the German Rwwad verse translation via the quranenc-backed lookup and uses that output directly instead of letting the LLM translate the Arabic OCR
    - newly recognized Qur'an passages are snapshotted into `project_quran_passages` with the resolved translation text
  - Hadith:
    - the app now runs a conservative reference-verification pass before LLM translation
    - if a verified German source translation exists in the hadith verification results, that text is used directly
    - if no verified German source translation exists, the segment is skipped with a protected-passage reason instead of being translated by the general LLM path
    - a blocking Hadith status is recorded so the unresolved passage can surface in the existing preflight/guided-review model
  - false-positive guard:
    - the Hadith pass only activates when there is an exact Shamela hit or obvious Hadith-style markers, to avoid over-triggering on ordinary Arabic prose
  - current limitation:
    - this first pass works at the current segment unit; with the current page-wide persistence model, it protects pages/segments that are fully recognizable as Qur'an/Hadith more reliably than mixed commentary pages with short embedded quotations
- Files changed for protected-passage handling:
  - [backend/waraq/translation/protected_passages.py](./backend/waraq/translation/protected_passages.py)
  - [backend/waraq/translation/service.py](./backend/waraq/translation/service.py)
  - [backend/tests/translation/test_protected_passages.py](./backend/tests/translation/test_protected_passages.py)

- Refined the protected-passage model for verified Hadith:
  - the earlier first pass treated verified Hadith too aggressively by substituting a source-side German translation when present or blocking the segment when it was absent
  - the current behavior is now:
    - Qur'an still stays on the canonical reference path and uses the protected snapshot/reference translation directly
    - verified Hadith now ALLOWS the normal OpenAI/Gemini translation path to run
    - the verified hadith reference stack is attached to the translation provenance payload as `protected_reference`
  - the persisted `protected_reference` payload is display-ready and currently carries:
    - `kind`, `title`, `subtitle`
    - a `sources` string list for workspace display
    - for Hadith, the source lines include source name, role, collection/locator/grade when available, translation-language availability, and markers for reference-matn / reference-vocalization winners
  - this metadata now flows through:
    - `TranslationContext.protected_reference` in the live translation loop
    - `TRANSLATION-PO.payload.protected_reference` in the translation persistence hook
    - `/segments/{satz_uuid}/history` via the existing provenance-object rollup
  - the Project Workspace translation pane now reads that metadata from segment history:
    - protected translations show a hover title summarizing the reference stack
    - a `Qur'an source` / `Verified sources` button opens a dialog with the full recorded source lines
    - for protected-reference rows, click-on-translation now opens the source dialog; editing remains available via the explicit edit button
- Files changed for the verified-Hadith refinement:
  - [backend/waraq/translation/protected_passages.py](./backend/waraq/translation/protected_passages.py)
  - [backend/waraq/translation/service.py](./backend/waraq/translation/service.py)
  - [backend/waraq/translation/persistence.py](./backend/waraq/translation/persistence.py)
  - [backend/tests/translation/test_protected_passages.py](./backend/tests/translation/test_protected_passages.py)
  - [frontend/src/lib/segment-history.ts](./frontend/src/lib/segment-history.ts)
  - [frontend/src/components/TranslationPane.tsx](./frontend/src/components/TranslationPane.tsx)

- Hardened Qur'an source display in the workspace:
  - the translation pane previously relied only on the latest translation provenance object for protected-source display
  - that was fragile for Qur'an passages because source display could disappear when the latest translation-related state did not carry `protected_reference`
  - the segment-history endpoint now also exposes the latest non-rejected `project_quran_passages` snapshot for the segment as `quran_passage`
  - frontend fallback logic now:
    - first searches translation provenance objects from newest to oldest for a `protected_reference`
    - if none is found, it builds a Qur'an source summary directly from `history.quran_passage`
  - practical effect: translated Qur'an text now still shows its source on hover/click even when provenance metadata is missing on the latest translation PO
- Files changed for the Qur'an source fallback:
  - [backend/waraq/api/routers/history_router.py](./backend/waraq/api/routers/history_router.py)
  - [frontend/src/lib/queries.ts](./frontend/src/lib/queries.ts)
  - [frontend/src/lib/segment-history.ts](./frontend/src/lib/segment-history.ts)

- Prepared frontend/backend for external tester deployment:
  - backend now reads `CORS_ORIGINS` from settings and installs FastAPI `CORSMiddleware` when configured
  - frontend now supports `VITE_API_URL`; when unset it keeps the existing local `/api` proxy behavior, and when set it calls the deployed backend directly
  - added `frontend/.env.example`
  - updated deployment docs so Vercel through GitHub + Fly uses:
    - frontend `VITE_API_URL=https://<backend>.fly.dev`
    - backend `CORS_ORIGINS=https://<frontend>.vercel.app`
  - verification passed:
    - `python3 -m py_compile backend/waraq/api/main.py backend/waraq/db/session.py`
    - `npm run build` in `frontend`
- Files changed for deployment readiness:
  - [backend/waraq/api/main.py](./backend/waraq/api/main.py)
  - [backend/waraq/db/session.py](./backend/waraq/db/session.py)
  - [backend/.env.example](./backend/.env.example)
  - [frontend/src/lib/api.ts](./frontend/src/lib/api.ts)
  - [frontend/.env.example](./frontend/.env.example)
  - [frontend/README.md](./frontend/README.md)
  - [infra/DEPLOY.md](./infra/DEPLOY.md)

- Removed the retired Kraken OCR path before Vercel/Fly external testing:
  - deleted the backend adapter and its dedicated test
  - removed the `KRAKEN` engine enum, `use_kraken` routing flag, and consensus runner branch
  - removed the backend diagnostics endpoint, frontend diagnostics card, environment pill, and mypy override
  - removed active product/test/deployment-doc references; specialist manuscript OCR remains parked for v2.0 in the canon tracker
  - uninstalled local backend venv package `kraken 7.0.2`
  - verification to rerun after this edit:
    - `python3 -m py_compile backend/waraq/ocr/routing.py backend/waraq/ocr/consensus.py backend/waraq/api/routers/diagnostics_router.py backend/waraq/upload/archive.py`
    - `backend/.venv/bin/pytest tests/ocr/test_stage2_routing_and_consensus.py`
    - `npm run build` in `frontend`
- Files changed for Kraken removal:
  - [backend/waraq/ocr/routing.py](./backend/waraq/ocr/routing.py)
  - [backend/waraq/ocr/consensus.py](./backend/waraq/ocr/consensus.py)
  - [backend/waraq/api/routers/diagnostics_router.py](./backend/waraq/api/routers/diagnostics_router.py)
  - [frontend/src/pages/Diagnostics.tsx](./frontend/src/pages/Diagnostics.tsx)
  - [backend/tests/ocr/test_stage2_routing_and_consensus.py](./backend/tests/ocr/test_stage2_routing_and_consensus.py)
  - [backend/tests/ocr/test_kraken_adapter.py](./backend/tests/ocr/test_kraken_adapter.py)
  - [backend/waraq/ocr/kraken.py](./backend/waraq/ocr/kraken.py)
  - [backend/pyproject.toml](./backend/pyproject.toml)
  - [API_KEYS.md](./API_KEYS.md)
  - [TEST_PLAN.md](./TEST_PLAN.md)
  - [CANON_TRACKER.md](./CANON_TRACKER.md)
