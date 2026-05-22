# Latest Waraq Fix Plan

## Summary

We will fix the issues sequentially, with one user-testable checkpoint after each fix. The order starts with visible regressions and small workflow blockers, then moves into larger restructuring work: page/list correctness, workspace view structure, page-based OCR/translation editing, review/audit state synchronization, TOC/export structure, OCR recovery, difficulty/notifications/account/admin areas.

## Fix Sequence

### 1. Export Formatting Regression: DOCX/PDF Header And Arabic RTL

Status: validated in deployed app.

- Remove `STYLEREF` from generated DOCX headers completely; header should be plain project/book title only.
- Make Arabic DOCX paragraphs explicitly RTL/right-aligned at paragraph and run XML level, with Arabic complex-script font applied.
- Keep German/translation paragraphs left-aligned by default.
- Ensure PDF export inherits the corrected DOCX formatting through LibreOffice.
- User test: export DOCX and PDF; confirm no “Reference source not found”, Arabic is right-aligned, German text remains readable.

### 2. Duplicate Logical Pages And OCR Export Range

Status: validated in deployed app.

- Fix `/projects/{project_uuid}/pages` consumer behavior so the workspace sidebar displays one active logical page per `page_index`.
- Add frontend dedupe safeguard in `PageList` and OCR export default range.
- Normalize OCR export range display from duplicated values into compact ranges like `1-16`.
- User test: reload project; confirm page list has no duplicates and OCR export page range is clean.

### 3. Workspace View Mode Restructure

Status: validated in deployed app.

- Replace the flat toolbar with three primary modes: `Triple`, `Double`, `Solo`.
- Add second-level selector for `Double`: `Original / OCR`, `Original / Translation`, `OCR / Translation`.
- Keep second-level selector for `Solo`: `Original`, `OCR`, `Translation`.
- Preserve current pane rendering and URL behavior.
- User test: switch between all modes; confirm panes are correct and toolbar is simpler.

### 4. Page-Based OCR Read/Edit View

Status: validated in deployed app.

- Replace the compressed per-segment OCR display with a page-like OCR document pane.
- Render OCR as full-page Arabic text with preserved paragraph breaks, empty lines, RTL direction, readable Arabic typography, and stable page padding.
- In edit mode, show a large full-pane OCR editor by default, not a small manually-resized textarea.
- Preserve segment IDs internally for history, stale translation detection, and save operations.
- User test: open Solo OCR, Double Original/OCR, Double OCR/Translation, and Triple; confirm OCR view/edit feels like a full page.

### 5. Page-Based Translation Editor MVP

Status: validated in deployed app.

- Make translation read/edit view page-like rather than primarily row/segment-like.
- In Double and Triple views, support simple plain-text/paragraph editing with segment preservation.
- In Solo Translation, provide a larger document-style editor surface.
- Keep existing protected Quran/Hadith source popups functional.
- User test: edit translation in Solo and comparison views; confirm saves, stale OCR markers, and source popups still work.

### 6. Project Style Profile And Export Integration

Status: validated in deployed app.

- Introduce a project-level style/layout profile using canonical Waraq defaults plus saved overrides.
- Expose global style controls in Solo Translation for core styles: body translation, Arabic source, headings, quotes, Quran/Hadith blocks, footnotes, spacing, page/header/TOC-related options where already supported.
- Apply effective style profile consistently to Solo Translation, comparison panes, Book Preview, DOCX export, and PDF export.
- Book Preview MVP moved forward from fix 14 so style changes can be evaluated before export.
- Book Preview translation now preserves paragraph breaks and line breaks so style changes do not render as jammed text.
- Completed block-aware style pass: segment responses now expose block type; workspace/book preview/DOCX export apply distinct styles for body text, headings, quotes/marginalia, footnotes, and protected Quran/Hadith passages.
- OCR pages now respect the same project page width, and DOCX headers use the saved style profile.
- Public API change: add project style profile read/update endpoints and include active profile in export config.
- User test: change a style globally, view it in workspace, export DOCX/PDF, confirm export uses the changed style.

### 7. OCR Review Approval And Attention List Sync

Status: validated in deployed app.

- Connect page-level OCR review decisions to Attention List state.
- “Approve as GO” should resolve/accept non-blocking OCR findings for that page and remove them from active open attention items.
- Block simple approval when unresolved blocking or decision-required issues remain; show “resolve required issues first” or “approve with warning”.
- Re-entering review must not reopen accepted findings unless OCR is rerun, OCR text changes, user resets review, or new findings appear.
- Public API change: add issue-level resolution/acceptance state for OCR attention findings if current decision events are insufficient.
- Implemented page-level `approve-go` endpoint: writes an OCR-review Decision Event, resolves non-critical open OCR errors, refuses critical OCR errors/critical OCR confidence, and lets Audit hide accepted low-confidence/divergent OCR attention rows until fresh OCR appears.
- User test: approve a page; confirm related Attention List items disappear from open list but remain available in resolved/history filter.

### 8. Expanded Attention Item Review

Status: validated in deployed app.

- Improve expanded OCR issue rows to show original scan/crop, current accepted OCR reading, Gemini/OpenAI alternatives, active reading marker, highlighted text differences, confidence/reason label, and decision buttons.
- Add actions: accept current, accept alternative, approve with warning, mark unresolved, open page review, edit OCR text.
- Public API change: extend attention detail response with original page/crop render metadata, OCR alternatives, active candidate, and resolved/open state.
- Implemented expanded Audit row actions: original full-page preview, active OCR engine marker, highlighted non-current readings, accept current OCR, accept engine alternative, approve with warning, mark unresolved/re-enter review, and open page.
- Added backend `approve-warning` review endpoint and exposed `is_current` on OCR engine readings. Region crop metadata/retry remains queued for fix 10 DPI Compare, where the crop tool belongs.
- User test: open an OCR issue in Audit; confirm the difference and decision path are obvious without manually comparing full texts.

### 9. TOC/IVZ Workflow Clarification

Status: implemented locally, awaiting user validation.

- Make TOC panel explicitly distinguish `No TOC detected / page-by-page fallback`, `TOC detected`, `TOC requires attention`, and `Final TOC review`.
- Fallback must be visually marked and explicitly confirmable; it must not look like real confirmed chapter structure.
- Real TOC entries should show level, page, Arabic heading, German heading, ambiguity state, editing, and confirmation.
- Connect TOC decisions to export/preflight settings: header heading level, chapter break level, TOC front/back, Arabic chapter heading display.
- Public API change: extend TOC response with workflow state and confirmation state; add confirm/final-review endpoints.
- Implemented TOC workflow state and final-review confirmation endpoint. The panel now shows fallback vs detected TOC, attention reasons for missing headings/translations, export preflight setting guidance, confirmation state, and a final confirmation action.
- User test: open TOC before/after translation; confirm fallback vs real TOC is clear and export settings reflect decisions.

### 10. DPI Compare As OCR Recovery Tool

Status: implemented locally, awaiting user validation.

- Redesign DPI Compare as original reference left pane plus adjustable right pane.
- Add zoom, crop/region selection, and retry OCR for selected region or full page.
- Region retry must create a candidate and never silently replace full-page OCR.
- After retry, show old OCR vs new candidate vs scan/crop with highlighted differences and accept/keep/edit/discard actions.
- Public API change: add OCR retry endpoint accepting page UUID, DPI, crop coordinates, retry scope (`region` or `full_page`), and returning candidate result/version.
- Implemented non-destructive retry candidates through `POST /pages/{page_uuid}/ocr-retry-candidate`; candidates can use OpenAI or Gemini and are only saved after explicit accept through the normal manual OCR edit path.
- Updated DPI Compare into a recovery workspace with reference scan, adjustable retry scan, zoom, crop selection, region/full-page retry, editable candidate review, current-vs-candidate comparison, accept, and discard.
- User test: open attention issue, retry OCR on crop, accept candidate, confirm Attention List updates.

### 11. Difficulty Badge And Report

Status: implemented locally, awaiting user validation.

- Keep Difficulty badge in workspace as summary/entry point.
- Clicking it opens a compact page/project difficulty panel with reasons, confidence, engine agreement, layout/small-print/religious-text risks, and links to Audit, Attention List, and DPI Compare.
- Move full Difficulty Report into Audit/OCR Review area as summary/prioritization, not a duplicate task list.
- Implemented clickable Difficulty badge panel with score state, active segment count, main contributors, risk cards for OCR confidence, engine agreement, religious text, layout/small-print, consistency, and locks.
- Added direct navigation from the page badge to Audit, workspace, and DPI recovery; `?panel=dpi` now opens the DPI recovery tool on the selected page.
- User test: click Difficulty 0 and a higher-difficulty page; confirm reasons and navigation are useful.

### 12. Notifications Panel Wiring

Status: implemented locally, awaiting user validation.

- Connect notifications to workflow events: upload, OCR, OCR retry/review, translation, provider failure/restoration, preflight, export, TOC review, Quran/Hadith decisions, audit findings, account/access warnings.
- Notifications should be typed: info, success, warning, error, action required.
- Notifications should be project-linked and clickable to the relevant project/page/issue/export/review screen.
- Public API change: standardize notification payload target links and severity/type fields if missing.
- Added notification metadata fields for severity, target URL, action label, project/page/issue references, plus a migration for existing installations.
- Wired workflow notifications for upload completion, OCR auto-run start/completion/failure/cancel, OCR retry candidate creation, OCR review approvals, translation start/completion/failure/cancel, preflight start/evaluation, OCR export, translation export, TOC final review, and the existing 30-minute translation failure watcher.
- Updated the bell panel to show severity badges, workflow kind labels, email/read state, and clickable actions to the relevant project, page, Audit, or DPI recovery screen.
- User test: trigger OCR/export/translation events and confirm bell panel shows actionable notifications.

### 13. Account Settings And Usage

Status: implemented locally, awaiting user validation.

- Add Account Settings area from profile/dashboard navigation.
- Include profile/email/password management, notification preferences, account/access/subscription display.
- Add general usage statistics: projects, uploaded books, OCR pages, translated pages, storage, limits.
- Add API usage statistics: OpenAI/Gemini/Google Vision calls, token usage, OCR/translation call counts, estimated cost per project.
- Public API change: add account usage and API usage endpoints.
- Added `/me/profile`, `/me/password`, and `/me/usage` endpoints. Usage reports real project/page/OCR/translation/job/provenance counts and explicitly marks token/cost as unavailable until provider token metadata is stored.
- Added Settings navigation and a settings page with profile update, password change, notification preferences, general usage, provider call counts, job breakdowns, and token/cost availability notes.
- User test: open settings; confirm user can see profile, notifications, general usage, and API cost usage.

### 14. Remaining UI Areas

Status: implemented locally, awaiting user validation.

- Polish Book Preview / Live Book Preview beyond the MVP moved into fix 6.
- Complete Morphology UI: Arabic word click opens morphology side panel; add word-form frequency modal.
- Improve Diagnostics page with system, job, OCR, translation, API, retry, and error status.
- Connect Delete/Trash/Restore to 10-day trash retention behavior.
- Expand Admin/Admissions with applicant review, user access decisions, account levels, and user management.
- Surface archives/directories: Glossary, Terminology, Religious Formulas, Reference/Entity System, Style Profile Option B.
- Configured the Fly backend Docker image to install CAMeL Tools + `morphology-db-msa-r13` so morphology is installed on the next backend deploy and survives future redeploys.
- Morphology click analysis now opens a wider side-panel style dialog with local word-form frequency and common-form chips beside CAMeL analyses.
- Added Trash route with 10-day restore window, restore API, dashboard/sidebar links, and clearer delete dialog wording.
- Added Directories route for Glossary, Terminology, Religious Formulas, Reference/Entity System, and Style Profile Option B, each linked to its current working surface.
- Diagnostics now starts with an operational status overview for system, OCR, translation, morphology, references, retry, and errors.
- Admin panel now surfaces approval status, account level, admission review link, account counts, and pending-review count.
- Book Preview now exposes live preview stats for pages, translated anchors, and stale translations.
- User test: review each new navigation area and confirm it is visible, reachable, and not placeholder-only.

## Test Plan

- After each fix, run targeted backend/frontend checks only for the touched area, not the full suite by default.
- For frontend changes, run local app and manually test the exact user workflow before moving on.
- For export changes, inspect generated DOCX structure and manually open DOCX/PDF.
- For review/audit changes, verify both backend state and UI filters: open, resolved, accepted warning, historical.
- For API additions, add focused tests for response shape, ownership checks, and state transitions.

## Assumptions

- We will fix and deploy in the order above unless a production blocker appears.
- Existing segment/revision/provenance structures should be preserved; new state should extend them rather than replacing the audit model.
- Manual testing by the user after each fix is the gate before moving to the next fix.
