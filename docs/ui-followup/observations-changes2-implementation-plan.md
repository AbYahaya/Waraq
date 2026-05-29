# Observations and Changes2 Implementation Plan

Date captured: 2026-05-28

## Source of Truth

`Observations and Changes2.pdf` is the authoritative follow-up scope for the next implementation pass.

Anything from `Observations and Changes.pdf` that is not mentioned again in `Observations and Changes2.pdf` is treated as already implemented or outside the current fix round.

Original references:

- `../../Observations and Changes.pdf`
- `../../Observations and Changes2.pdf`

Visual references rendered from `Observations and Changes2.pdf`:

- Translation editor current state: `assets/changes2-translation-editor-current.png`
- Translation editor target direction: `assets/changes2-translation-editor-target.png`
- OCR review rerun state: `assets/changes2-ocr-review-rerun.png`
- Attention List expanded issue view: `assets/changes2-attention-list-expanded.png`
- Attention List reason/label examples: `assets/changes2-attention-list-reasons.png`
- TOC / IVZ mockup: `assets/changes2-toc-ivz-mockup.png`

## 1. OCR Read/Edit View in Comparison Layouts

Latest status: implemented in this follow-up pass.

Solo OCR view is correct and should remain the reference implementation.

Implemented changes:

- Make OCR rendering in Original/OCR, OCR/Translation, and Triple views match the Solo OCR page view.
- Preserve paragraph breaks, visible block structure, spacing, RTL alignment, and readable Arabic sizing in comparison panes.
- Ensure OCR edit mode uses the same page-like structure in every layout.
- Avoid a separate compressed comparison rendering path.
- Fit the full OCR page width into narrow comparison panes.
- Scale OCR typography and page padding down proportionally in comparison panes instead of using horizontal scroll.
- Support OCR inline alignment markers such as `[[center]]...[[/center]]`, matching the app's existing alignment-marker model.

Implementation notes:

- Updated `Waraq/frontend/src/components/OcrPane.tsx`.
- Comparison modes already reused `OcrPane`; the mismatch came from responsive pane width shrinking the document frame.
- The OCR pane now measures available width and scales its page-like OCR rendering to fit.
- Verified with `npm run typecheck`; run `npm run build` after any additional edits.

## 2. Translation Editor / Word-Like Style System

Latest status: not acceptable yet; major redesign required.

Required changes:

- Replace the simplified style profile panel with a Word-like document editor toolbar.
- Add a Paragraph Style dropdown, not a generic formatting dropdown.
- List canonical paragraph styles from `Formatvorlagen Baseline v1.1`, for example:
  - `Body_DE`
  - `Body_DE_NoIndent`
  - `Heading 1` through `Heading 6`
  - `UeberschriftAR_1` through `UeberschriftAR_6`
  - `Quran_AR`, `Quran_DE`, `Quran_Quelle`
  - `Hadith_AR`, `Hadith_DE`, `Hadith_Quelle`
  - `Zitat_AR`, `Zitat_DE`, `Zitat_Quelle`
  - title, footnote, and TOC styles where applicable
- Keep character/inline styles separate from paragraph styles, for example:
  - `Begriff_AR`
  - `FussN_AR`
  - `FN_Uebersetzer`
  - `FN_Herausgeber`
  - `FN_Verlag`
- Store two separate values for every style:
  - `internal_style_key`: fixed canonical key, not editable by the user.
  - `display_label`: editable user-facing alias.
- Ensure export, preflight, template mapping, and style-integrity logic always use `internal_style_key`, never `display_label`.
- Add "Edit style..." / advanced style settings for global style-level edits.
- Allow users to adjust style-level properties defined in `Formatvorlagen Baseline v1.1`, including:
  - font family
  - font size
  - line spacing
  - spacing before
  - spacing after
  - first-line indent
  - left indent
  - paragraph alignment
  - RTL / LTR behavior
  - border / left rule for Quran, Hadith, and Quote block styles
  - tab stops where applicable, especially TOC-related styles
- Make style edits apply globally to all text using that style, not only the selected paragraph.
- Make Quran/Hadith/Quote buttons insert or apply structured block sequences:
  - Quran block: `Quran_AR` -> `Quran_DE` -> `Quran_Quelle`
  - Hadith block: `Hadith_AR` -> `Hadith_DE` -> `Hadith_Quelle`
  - Quote block: `Zitat_AR` -> `Zitat_DE` -> `Zitat_Quelle`
- Preserve baseline-defined indentation, spacing, and left border/rule for those block styles.
- Add account/project font-library support.
- Ensure fonts used in the editor are also available to server-side DOCX/PDF export.
- Never silently replace missing fonts with browser or server fallbacks.
- Treat missing critical baseline fonts as blocking before preflight:
  - `KFGQPC Uthmanic Script HAFS`
  - `Traditional Naskh`
  - `Noto Sans Arabic`
  - `Calibri`
- Ensure Solo Translation, Double views, Triple view, Book Preview, DOCX export, PDF export, and preflight all consume the active effective style profile.

Clarity to resolve during implementation:

- Decide whether to introduce a rich-text editor dependency such as TipTap/ProseMirror or continue with custom editor components.
- Confirm whether critical font files are already available on the server, or whether missing fonts should first be handled through upload/selection.
- Confirm how much of the font-library workflow should ship in the first pass versus the style-model foundation.

Visual references:

![Translation editor current state](assets/changes2-translation-editor-current.png)

![Translation editor target direction](assets/changes2-translation-editor-target.png)

## 3. OCR Review, Attention List, and Issue Lifecycle

Latest status: partially implemented in this follow-up pass.

Implemented in this pass:

- Added an Audit read path for resolved OCR review decisions:
  - `GET /projects/{project_uuid}/audit/ocr-review-decisions`
  - Uses existing page-level OCR review Decision Events as the source of truth.
- Added Audit tabs:
  - Active attention
  - Resolved OCR decisions
- Kept active attention focused on unresolved work.
- Grouped duplicate OCR attention signals for the same page/block/segment, so low confidence and divergent engines appear as one review group where they share a decision context.
- Added clearer reason labels and short explanations.
- Added action-result messages after OCR review actions.
- Enlarged the original scan preview in expanded OCR issue rows.
- Added inline difference highlighting for OCR engine alternatives.
- Added OpenAI-backed OCR difference explanations for alternative engine readings.
- Added ignored/deleted OCR attention decisions as segment-level Decision Events.
- Ignored/deleted OCR findings are hidden from Active attention and shown only inside an explicit `Ignored / deleted` filter in Resolved OCR decisions.
- Added `superseded by OCR retry` as a segment-level Decision Event state and explicit resolved filter.
- DPI retry acceptance now records candidate UUID, segment UUID, scope, engine, DPI, crop, changed flag, and character count on the superseded decision.
- Added navigation from page review back to the focused Audit attention item.

Existing backend behavior confirmed:

- Page approval already persists OCR review Decision Events.
- Page approval resolves non-blocking OCR error rows.
- Accepted OCR-PO attention rows are suppressed when the page-level OCR review decision is newer than the OCR result.
- Re-running OCR after approval naturally reopens active attention because the OCR-PO is newer than the prior decision.
- Ignored/deleted OCR attention rows are suppressed only when the segment-level ignore/delete Decision Event is newer than the OCR result.
- Superseded OCR attention rows are suppressed only when the segment-level superseded Decision Event is newer than the OCR result.

OCR difference note:

- Current inline highlighting remains a deterministic visual aid.
- OpenAI now acts as the reviewer/agent layer for full Arabic OCR-difference explanations. It compares Gemini as the primary OCR reading against OpenAI as the comparison reading, maps how OpenAI differs from Gemini line by line, adds character-level notes, and explains likely Arabic-specific causes such as harakat, hamza forms, dotting, ligatures, spacing, and normalization. It requires `OPENAI_API_KEY`; `OPENAI_OCR_DIFF_MODEL` can override the default `gpt-4o`.

Still remaining:

- A full persisted OCR finding lifecycle with explicit states beyond current `offen` / `aufgeloest` plus Decision Events:
  - decision required
  - accepted with warning
  - unresolved
  - historical
- Separate explicit filters for lifecycle states beyond the current Active / Resolved / Superseded / Ignored-deleted views.
- True crop-level issue mapping and region-specific OCR lifecycle. The current retry endpoint returns an unsaved candidate and maps to page/segment plus optional crop metadata, but does not persist candidates or bind a crop to a specific issue/finding ID.
- Stronger backend-level issue grouping if future UI/API consumers need grouped findings server-side.

Required changes:

- Add one unified OCR finding lifecycle:
  - open
  - decision required
  - accepted / resolved
  - accepted with warning
  - unresolved
  - superseded by rerun OCR
  - historical
  - deleted / ignored
- Make "Approve as GO" persist a review decision and move non-blocking findings into resolved/accepted state.
- After "Approve as GO", update:
  - page OCR status
  - related OCR finding states
  - Audit counters
  - Attention List contents
- Default Attention List should show active unresolved work only.
- Add Audit filters or tabs:
  - Open findings
  - Blocking / decision required
  - Warnings
  - Accepted / resolved
  - Accepted with warning
  - Historical / superseded
  - Deleted / ignored
- Keep resolved or accepted findings available in a separate resolved/history view.
- Re-entering review must not reset accepted/resolved findings unless:
  - OCR is re-run
  - OCR text changes in a way that invalidates the previous decision
  - user explicitly resets review state
- "Approve as GO" must be unavailable if unresolved blocking or decision-required findings remain.
- Show "Resolve required OCR issues first" where blocking issues remain.
- Offer "Approve with warning" where only non-blocking warnings remain.
- Make issue-level actions persist and move findings into the correct state:
  - Accept current OCR reading
  - Accept alternative reading
  - Approve with warning
  - Mark unresolved
  - Edit OCR text
  - Open page review
  - Rerun OCR for this page/region if applicable
- After an action, show a clear confirmation message, for example:
  - "Finding accepted and moved to Resolved findings."
  - "Finding remains open because OCR confidence is still critical."
- Group multiple findings for the same page/block/segment into one finding group where they share one decision context.
- Improve reason labels so the user understands why the issue exists:
  - Low OCR confidence
  - Divergent engines
  - Critical confidence
  - Layout/order uncertainty
  - Footnote/small print risk
- Add short definitions/explanations for reason labels.
- Add inline difference highlighting between OCR alternatives.
- Do not rely only on character-count differences.
- Make the original scan/crop larger in the expanded issue view.
- Show which OCR reading is currently active.
- Add navigation back from page review to the exact Attention List item.
- Allow OCR rerun for a specific page/region after approval where applicable.

Clarity to resolve during implementation:

- Confirm the best persisted state model based on existing OCR finding tables and decision-event patterns.
- Confirm whether "deleted / ignored" is a soft state only or should hide findings from all normal history views.

Visual references:

![OCR review rerun state](assets/changes2-ocr-review-rerun.png)

![Attention List expanded issue view](assets/changes2-attention-list-expanded.png)

![Attention List reason examples](assets/changes2-attention-list-reasons.png)

## 4. TOC / IVZ Review Screen

Latest status: needs implementation according to the mockup and described workflow.

Required changes:

- Build the TOC / IVZ screen as a structural manuscript review station, not just a table.
- Make it clear that Step 1 is structural TOC confirmation before translation.
- Make it clear that Step 2 is final translated TOC review after translation.
- Include the main functional areas:
  - top workflow area
  - original TOC scan panel
  - editable OCR text panel
  - structured TOC table
  - issue resolution panel
  - release gate / confirm and proceed
  - TOC and heading export settings
  - heading-style customization only
- Original TOC scan panel must support:
  - original TOC page scan
  - zoom in / zoom out
  - page navigation if TOC spans multiple pages
  - selected-line highlight
  - synchronization with OCR text and structured TOC table
  - rerun OCR for TOC page
  - optional selected-area OCR if supported
- OCR text panel must support:
  - editable OCR lines
  - save/cancel correction
  - split line
  - merge lines
  - mark line as TOC entry
  - mark line as not TOC
  - synchronization with scan and structured table
  - protection of manual OCR corrections from silent overwrite
- Structured TOC table should include:
  - level
  - TOC page number
  - Arabic OCR heading
  - target page
  - target heading where space allows
  - status
  - German heading preview
  - actions
- Structured TOC table actions should support:
  - select row
  - edit heading
  - change heading level
  - change target page
  - relink to another heading
  - confirm match
  - mark as not TOC entry
  - add missing entry from selected OCR/source/detected line
- "Add Entry" must be controlled and source-based, not a free manual TOC builder.
- Issue Resolution panel must explain:
  - what was detected in the TOC source
  - what was detected on the target page
  - why the match is OK, missing, verify, or mismatch
  - what the user can do to resolve it
- Release Gate must use one source of truth across:
  - sidebar gate status
  - top status
  - issue count
  - Confirm & Proceed button
- Confirm & Proceed must be disabled while blocking TOC issues remain.
- TOC and heading export settings must support:
  - which heading level appears in running headers
  - which heading level marks chapters
  - TOC position: front or back
  - whether Arabic headings appear in translated body text
  - navigation/bookmark depth
  - save to export profile
- Heading style customization on this screen is limited to heading styles only:
  - H1 through H6
  - German heading style
  - Arabic heading style
- Do not include full document formatting here; body, Quran, Hadith, quote, footnote, and general layout styles belong in the Solo Translation editor / document formatting area.
- Add "Save heading style" and "Reset to baseline" actions.
- Make clear that heading style changes affect:
  - TOC preview
  - Book Preview
  - DOCX export
  - PDF export
- Re-detect TOC must produce suggestions and must not silently overwrite:
  - manually corrected OCR lines
  - confirmed target pages
  - confirmed heading levels
  - confirmed TOC entries

Clarity to resolve during implementation:

- Confirm whether selected-area OCR already exists for TOC pages, or should be deferred behind a disabled/coming-later control.
- Confirm whether final Step 2 translated TOC review should be built in the first pass or scaffolded with state and placeholder behavior.

Visual reference:

![TOC / IVZ mockup](assets/changes2-toc-ivz-mockup.png)

## 5. DPI Compare / OCR Retry Recovery

Latest status: setup stage is good; retry result review is missing.

Required changes:

- Keep the current DPI comparison setup stage.
- After "Retry selected region" or "Retry full page", show an OCR Retry Result Review panel or modal.
- The result review must include:
  - original crop / page region
  - current accepted OCR text
  - new OCR candidate
  - highlighted differences
  - confidence / reason labels
  - mapping target: page, block, segment, or OCR finding
  - original issue type if opened from Attention List
  - issue ID or page/block/segment reference
  - whether accepting the candidate will resolve the issue
- Add decision actions:
  - Accept new region OCR
  - Accept new full-page OCR
  - Keep current OCR
  - Edit manually
  - Discard retry result
- On accept:
  - update mapped OCR text
  - mark linked finding as resolved / replaced / accepted
  - remove old issue from active Attention List
  - keep the action in history/logs
- Re-running OCR for a selected crop must never silently replace the whole page.
- The UI must clearly ask whether the user wants to replace only the mapped region/segment or the entire page OCR result.

Clarity to resolve during implementation:

- Confirm whether selected-region OCR exists backend-side.
- If selected-region OCR is not available, decide whether first pass should implement full-page retry plus UI scaffolding for region retry.
- Confirm how OCR retry candidates should be versioned and linked to the original OCR finding.

## Implementation Order

Recommended order:

1. OCR comparison rendering consistency.
2. OCR finding lifecycle and Attention List state model.
3. DPI retry result review, connected to the lifecycle model.
4. TOC / IVZ structural review screen.
5. Translation editor and canonical style system.

Reasoning:

- OCR comparison rendering is the smallest and most isolated follow-up.
- OCR finding lifecycle should come before DPI retry because retry acceptance depends on correct issue states.
- TOC / IVZ is a large workflow but can be built after the review-state model is stable.
- The translation editor/style system is the largest architectural item because it touches frontend editing, backend persistence, preflight, DOCX export, PDF export, and font availability.

## Parked Follow-Up: True Crop-to-Finding Mapping

Workstream 3 is functionally complete within the current codebase model, but true crop-to-specific-finding mapping requires a backend schema/model upgrade.

Current limitation:

- OCR retry candidates are returned as temporary API responses, not persisted records.
- Active OCR attention items are derived from OCR-PO payloads and Decision Events, not stored as first-class issue rows.
- Accepted retry decisions can store crop metadata, candidate UUID, page UUID, segment UUID, engine, DPI, and scope in the Decision Event, but cannot point to a stable crop-level OCR finding ID because that ID does not exist yet.

Required future model:

- Add a persisted OCR attention issue table with stable issue UUIDs, project/page/block/segment references, issue type, state, source OCR-PO UUID, and timestamps.
- Add a persisted OCR retry candidate table with candidate UUID, linked issue UUID where available, page/segment references, crop box, engine, DPI, candidate text, current-text snapshot, status, actor, and timestamps.
- Link accepted/rejected/edited retry decisions to both the candidate UUID and the issue UUID.
- On candidate acceptance, update OCR text, mark the linked issue as resolved/replaced/superseded, and keep the action in Decision Events/history.
- Region retries should resolve only the mapped segment/issue unless the user explicitly chooses full-page replacement.

This should be implemented before claiming precise crop-level lifecycle support in the UI.
