# Observations and Changes2 E2E Test Plan

Date: 2026-05-29

Scope: this plan verifies every implemented workstream from `observations-changes2-implementation-plan.md`.

Authoritative implementation scope:

- OCR read/edit view in comparison layouts
- Translation editor / Word-like style system
- OCR Review, Attention List, and issue lifecycle
- TOC / IVZ review screen
- DPI Compare / OCR retry recovery
- Reference stack wiring: sunnah.com, Shamela, dorar.net, CAMeL morphology, protected Qur'an carrier selection, and Hadith review decisions

## 0. Pre-Test Setup

### 0.1 Start a Clean Test Session

Action:

- Start the backend.
- Start the frontend.
- Open the app in a fresh browser session or private window.
- Use a test project with enough data to cover:
  - Arabic OCR pages
  - OCR/translation segments
  - at least one page with low-confidence or divergent OCR alternatives
  - at least one TOC/IVZ page
  - at least one page suitable for DPI retry/crop OCR

Expected result:

- Dashboard loads without console-breaking errors.
- Project opens successfully.
- Audit, OCR review, translation, TOC, and DPI recovery screens are reachable.

### 0.2 Database Migration Check

Action:

- From `backend`, run:

```bash
.venv/bin/alembic current
```

Expected result:

- Current migration is at the latest head.
- Migration `0028`, "Add persisted OCR attention issue lifecycle", has already been applied.
- Audit routes do not fail with missing table errors for `ocr_attention_issues` or `ocr_retry_candidates`.

### 0.3 Automated Health Checks

Action:

- From `backend`, run:

```bash
.venv/bin/python -m py_compile \
  waraq/translation_styles.py \
  waraq/style_profile.py \
  waraq/api/routers/segments_router.py \
  waraq/api/routers/style_profile_router.py \
  waraq/api/routers/audit_dashboard_router.py \
  waraq/api/routers/toc_router.py \
  waraq/api/routers/pages_router.py \
  waraq/api/routers/ocr_review_router.py \
  waraq/audit_dashboard/service.py \
  waraq/toc/service.py \
  waraq/ocr/diff_explainer.py \
  waraq/export/docx_builder.py
```

- From `frontend`, run:

```bash
npm run typecheck
npm run build
```

Expected result:

- Python compile check passes.
- TypeScript check passes.
- Frontend build passes.
- A Vite large chunk warning may appear because of TipTap; this is acceptable unless the build fails.

## 1. OCR Read/Edit View in Comparison Layouts

Goal: verify comparison layouts render OCR like the Solo OCR page, while fitting the full page width into the pane.

### 1.1 Solo OCR Reference Rendering

Action:

- Open a page in Solo OCR view.
- Check paragraph breaks, block spacing, Arabic text size, RTL alignment, and page-like frame.
- Enter OCR edit mode.

Expected result:

- OCR appears as a readable page-like document.
- Paragraph breaks and block structure are visible.
- Arabic text is properly RTL-aligned.
- Edit mode keeps the same page-like structure.

### 1.2 Original/OCR Comparison Rendering

Action:

- Switch to Original/OCR double view.
- Compare the OCR pane to the Solo OCR view.
- Resize the browser narrower and wider.

Expected result:

- OCR structure matches Solo OCR.
- Full OCR page width fits inside the OCR pane.
- No horizontal scroll is needed for the OCR page frame.
- Typography and padding scale down proportionally in narrow panes.
- Text remains readable and does not overlap neighboring UI.

### 1.3 OCR/Translation Comparison Rendering

Action:

- Switch to OCR/Translation double view.
- Inspect the OCR side.
- Enter OCR edit mode if available from this view.

Expected result:

- OCR rendering remains consistent with Solo OCR.
- OCR edit mode does not collapse into a compressed textarea-like view.
- Full page width remains fitted into the pane.

### 1.4 Triple View Rendering

Action:

- Switch to Triple view.
- Inspect Original, OCR, and Translation panes.
- Resize the browser to a practical laptop width.

Expected result:

- OCR pane still shows the full page width, scaled to fit.
- OCR content remains structurally readable despite the narrower pane.
- No horizontal OCR page scroll is required.
- Adjacent panes do not overlap or push OCR content out of view.

### 1.5 OCR Alignment Markers

Action:

- Use or create OCR text containing alignment markers such as `[[center]]...[[/center]]`.
- View the same page in Solo OCR and comparison OCR views.

Expected result:

- Centered or aligned OCR content renders according to the markers.
- Marker behavior is consistent across Solo, double, and triple layouts.

## 2. Translation Editor / Word-Like Style System

Goal: verify the translation editor supports canonical paragraph styles, global style templates, server fonts, persistence, and export consumption.

### 2.1 Editor Surface and Toolbar

Action:

- Open a translated page in Solo Translation or a layout that includes the translation pane.
- Enter translation edit mode.
- Inspect the toolbar.

Expected result:

- The editor is a document-style editing surface, not a plain textarea.
- Toolbar includes paragraph style, font, size, bold, italic, underline, strike, alignment, line height, Footnote, Quran, Hadith, Quote, Reset, Save style, and Save page controls.
- UI copy is in English.

### 2.2 Paragraph Style Application

Action:

- Select a paragraph or place the cursor inside one anchored segment.
- Change its paragraph style, for example from Body to Heading 1.
- Save the page.
- Refresh the browser.

Expected result:

- The selected paragraph visually changes to the selected style.
- The style survives refresh.
- Only the intended segment/paragraph changes style.
- The segment response includes the saved `translation_style_key`.

### 2.3 Global Style Template Editing

Action:

- Select a style, for example Body or Heading 1.
- Open/use the selected style-template editor.
- Change font size, line height, spacing, alignment, indentation, bold, italic, or display label.
- Save the style profile.
- Inspect all paragraphs using that same internal style.

Expected result:

- All paragraphs using that internal style update together.
- Paragraphs using other styles are not unintentionally changed.
- Saved settings survive refresh.
- Export/preflight behavior continues to rely on the internal style key, not the editable display label.

### 2.4 Server Font Library

Action:

- Open the style/font dropdown.
- Check available fonts.
- Run or trigger the style profile font endpoint if needed:

```text
GET /projects/{project_uuid}/style-profile/fonts
```

Expected result:

- Toolbar font choices come from server-available fonts.
- Available fonts include local server fonts such as Noto families.
- Missing canon-critical fonts are surfaced instead of silently replaced.
- Missing fonts currently expected unless installed separately:
  - `KFGQPC Uthmanic Script HAFS`
  - `Traditional Naskh`
  - `Calibri`

### 2.5 Missing Critical Font Warning

Action:

- Run the export/preflight path or open the UI area that surfaces guard-near preflight issues.
- Use a style profile that references a missing critical font.

Expected result:

- The app reports the missing critical font clearly.
- It does not silently fall back to another browser/server font while claiming full compliance.

### 2.6 Quran/Hadith/Quote Style Sequences

Action:

- Place the cursor in a paragraph with at least two following anchored paragraphs.
- Click Quran.
- Repeat on another set of paragraphs with Hadith.
- Repeat with Quote.
- Save and refresh.

Expected result:

- Quran applies the expected three-part style sequence to existing anchored paragraphs:
  - Quran text style
  - Quran translation/body style
  - Source note style
- Hadith applies the corresponding Hadith sequence.
- Quote applies the corresponding Quote sequence.
- Left rule, spacing, indentation, and style-specific formatting appear where configured.
- The applied styles persist after refresh.

Note:

- These buttons style existing anchored paragraphs. They are not expected to create new text segments.

### 2.7 Inline Formatting

Action:

- Select text inside a paragraph.
- Toggle bold, italic, underline, and strike.
- Save and refresh.

Expected result:

- Inline formatting appears in the editor.
- Formatting does not break paragraph anchoring or segment persistence.
- Saved page content remains editable after refresh.

### 2.8 DOCX Export Style Consumption

Action:

- Apply several paragraph styles and global style-template edits.
- Export DOCX.
- Open the DOCX.

Expected result:

- DOCX paragraphs reflect the selected internal paragraph styles.
- Font size, spacing, alignment, indentation, bold, italic, and left-rule style behavior are reflected where supported by export.
- Display-label edits do not break DOCX style mapping.

## 3. OCR Review, Attention List, and Issue Lifecycle

Goal: verify OCR issues have a persistent lifecycle, active attention stays focused, resolved states are filterable, and OpenAI difference explanations work.

### 3.1 Active Attention Loads

Action:

- Open the Project Audit page.
- Select Active attention / open findings.

Expected result:

- Active attention loads without server errors.
- Only unresolved active work is shown by default.
- Resolved, historical, superseded, ignored, or deleted findings are not mixed into the default active list.

### 3.2 Reason Labels and Grouping

Action:

- Open an expanded OCR issue row.
- Inspect reason labels and grouped issue details.

Expected result:

- Reasons are human-readable, for example low OCR confidence, divergent engines, critical confidence, layout/order uncertainty, or footnote/small print risk.
- Short explanations help clarify why the issue exists.
- Duplicate signals for the same page/block/segment are grouped where they share one decision context.

### 3.3 Expanded Scan Preview

Action:

- Expand an OCR issue row with source scan context.

Expected result:

- Original scan/crop preview is visibly enlarged.
- Preview is large enough to compare against OCR alternatives.
- Layout remains stable and does not hide issue actions.

### 3.4 OCR Alternative Highlighting

Action:

- Open an issue with Gemini and OpenAI or other alternative OCR readings.
- Compare the displayed alternatives.

Expected result:

- The currently active OCR reading is clearly identified.
- Differences between alternatives are highlighted inline.
- Highlighting is not based only on character count.

### 3.5 Explain Differences Toggle

Prerequisite:

- `OPENAI_API_KEY` is configured in the backend environment.
- Optional: `OPENAI_OCR_DIFF_MODEL` is configured if you want a model other than the default.

Action:

- Open an OCR issue with Gemini as the primary OCR and OpenAI as the comparison OCR.
- Click Explain differences.
- Wait for the explanation.
- Click Explain differences again.

Expected result:

- Button is visible and clickable.
- Explanation compares OpenAI against Gemini line by line.
- Explanation includes character-level notes where relevant.
- Explanation mentions likely Arabic OCR causes when applicable, such as harakat, hamza forms, dotting, ligatures, spacing, or normalization.
- Clicking the button again closes/hides the returned finding.

### 3.6 Accept Current OCR Reading

Action:

- Choose an active non-blocking OCR issue.
- Accept the current OCR reading.

Expected result:

- App shows a clear confirmation message.
- Issue is removed from Active attention.
- Issue appears in the resolved/history filter as accepted or resolved.
- Decision remains persisted after refresh.

### 3.7 Accept Alternative OCR Reading

Action:

- Choose an active issue with an alternative OCR reading.
- Accept the alternative reading.
- Refresh the page.

Expected result:

- OCR text updates to the accepted alternative where mapped.
- Issue moves out of Active attention.
- Resolved/history view records the decision.
- Updated OCR remains after refresh.

### 3.8 Approve With Warning

Action:

- Use a page or issue where only non-blocking warnings remain.
- Choose Approve with warning.

Expected result:

- Warning decision is persisted.
- Finding moves out of Active attention.
- Resolved/history view shows accepted with warning.
- Audit counters update.

### 3.9 Mark Unresolved

Action:

- Mark an issue unresolved.

Expected result:

- Issue remains visible as active unresolved work.
- Confirmation explains that the finding remains open.
- Page approval remains blocked if the issue is blocking or decision-required.

### 3.10 Ignore/Delete Filter Behavior

Action:

- Ignore or delete an OCR attention finding.
- Return to Active attention.
- Open Resolved OCR decisions and select the explicit Ignored / deleted filter.

Expected result:

- Ignored/deleted finding is hidden from Active attention.
- It appears only when the explicit Ignored / deleted filter is selected.
- Decision persists after refresh.

### 3.11 Page Approval Gate

Action:

- Open OCR page review for a page with unresolved blocking issues.
- Attempt Approve as GO.
- Resolve or downgrade blocking issues.
- Attempt approval again.

Expected result:

- Approve as GO is unavailable while unresolved blocking or decision-required findings remain.
- UI explains that required OCR issues must be resolved first.
- Approval becomes available after blocking issues are handled.
- Approval updates page OCR status, related finding states, Audit counters, and Attention List contents.

### 3.12 Re-Entering Review Does Not Reset Decisions

Action:

- Resolve or accept a finding.
- Leave the review page.
- Re-enter the same page review.
- Refresh the browser.

Expected result:

- Accepted/resolved finding remains resolved.
- It does not return to Active attention unless OCR is re-run, OCR text changes in a way that invalidates the decision, or the user explicitly resets review state.

### 3.13 Re-Run OCR Reopens Attention When Newer

Action:

- Approve a page or resolve an OCR finding.
- Re-run OCR for that page or mapped region.

Expected result:

- Newer OCR result can reopen attention if it invalidates the previous decision.
- Historical/resolved state remains available in history.
- Active attention reflects the latest OCR state.

### 3.14 Navigation Back to Focused Attention Item

Action:

- Open a page review from an Audit attention row.
- Use the provided back/navigation path to return.

Expected result:

- App returns to the relevant Audit attention context.
- The original/focused issue is easy to locate.

## 4. DPI Compare / OCR Retry Recovery

Goal: verify OCR retry does not silently replace whole pages, shows a review panel, persists candidates, and resolves linked findings correctly.

### 4.1 Open DPI Retry From Audit

Action:

- Open an OCR issue in Audit.
- Click Open DPI retry.

Expected result:

- DPI recovery opens with page/segment/issue context.
- The retry view knows the originating attention issue where available.

### 4.2 Retry Selected Region

Action:

- Select a crop/region.
- Run Retry selected region.

Expected result:

- OCR Retry Result Review panel opens.
- Panel shows original crop preview.
- Panel shows current accepted OCR text.
- Panel shows new OCR candidate.
- Panel shows highlighted differences.
- Panel shows mapping target: page, block, segment, or OCR finding context.
- UI clearly states whether acceptance updates a mapped region/segment or full page.

### 4.3 Retry Full Page

Action:

- Run Retry full page.

Expected result:

- OCR Retry Result Review panel opens.
- Panel clearly indicates full-page retry scope.
- It does not silently replace current OCR before confirmation.

### 4.4 Accept New Region OCR

Action:

- From selected-region retry review, click Accept new region OCR.

Expected result:

- Mapped segment OCR text updates.
- Linked finding is marked resolved/superseded by rerun where applicable.
- Old issue is removed from Active attention when the retry decision is newer than the OCR issue.
- Action remains visible in resolved OCR decision history.
- Retry candidate is persisted with crop, DPI, engine, candidate text, current text snapshot, and issue UUID where available.

### 4.5 Accept New Full-Page OCR

Action:

- From full-page retry review, click Accept new full-page OCR.

Expected result:

- UI clearly confirms full-page scope before acceptance.
- Accepted OCR updates according to the full-page mapped behavior.
- Action is logged in history.
- No selected crop result silently replaces the whole page without explicit full-page action.

### 4.6 Keep Current OCR

Action:

- Run a retry.
- Click Keep current OCR.

Expected result:

- Current OCR text remains unchanged.
- Retry result is dismissed or marked not accepted.
- Linked issue remains active unless another decision resolves it.

### 4.7 Edit Manually

Action:

- Run a retry.
- Click Edit manually.
- Modify candidate text.
- Accept the edited candidate.

Expected result:

- Edited candidate is used for the OCR update.
- History records that a retry/manual-edited result was accepted.
- Active attention updates according to the linked issue lifecycle.

### 4.8 Discard Retry Result

Action:

- Run a retry.
- Click Discard.

Expected result:

- Current OCR remains unchanged.
- Retry candidate does not resolve the issue.
- User can run another retry if needed.

## 5. TOC / IVZ Review Screen

Goal: verify the TOC screen functions as a structural manuscript review station with persisted decisions and a clear release gate.

### 5.1 Workflow Structure

Action:

- Open the TOC / IVZ screen for a project with detected TOC data.

Expected result:

- Screen is organized as a structural review station.
- Step 1 is clearly structural TOC confirmation before translation.
- Step 2 is shown as final translated TOC review after translation.
- UI includes workflow area, original scan panel, editable OCR text panel, structured TOC table, issue resolution panel, release gate, export settings, and heading-style customization.

### 5.2 Original TOC Scan Panel

Action:

- Use zoom in/out.
- Navigate between TOC lines/pages if available.
- Select a line in scan/OCR/table.

Expected result:

- Scan zoom works.
- Previous/next line navigation works.
- Selected-line highlight synchronizes with OCR text and structured TOC table.
- UI can hand off selected-area OCR to DPI recovery where supported.

### 5.3 Editable OCR Lines

Action:

- Edit an OCR line.
- Save it.
- Refresh the screen.
- Then cancel another edit.

Expected result:

- Saved OCR correction persists.
- Cancel discards unsaved correction.
- Corrected line is marked protected/manual where applicable.
- Re-detect does not silently overwrite manual OCR corrections.

### 5.4 Split and Merge OCR Lines

Action:

- Select an OCR line and split it.
- Select adjacent lines and merge-next.
- Refresh.

Expected result:

- Split creates separate persisted line entries.
- Merge combines the selected line with the next line.
- Changes survive refresh.
- Structured TOC suggestions/table update without losing manual protection.

### 5.5 Mark TOC / Not TOC

Action:

- Mark a line as TOC entry.
- Mark another line as not TOC.
- Refresh.

Expected result:

- Entry status persists.
- Structured TOC table reflects the TOC/non-TOC decision.
- Re-detect preserves confirmed manual entry decisions.

### 5.6 Structured TOC Table Actions

Action:

- Select a row.
- Edit heading text if available.
- Change heading level.
- Change target page.
- Relink to another heading.
- Confirm match.
- Mark a row as not TOC.
- Add a missing entry from the selected OCR/source/detected line.

Expected result:

- Table includes level, TOC page number, Arabic OCR heading, target page, target heading where available, status, translation heading preview, and actions.
- Changes are source-based and persisted.
- Add Entry does not behave like a free manual TOC builder; it uses selected source/detected line context.
- Confirmed target pages, levels, and entries survive refresh and re-detect.

### 5.7 Issue Resolution Panel

Action:

- Select TOC rows with different statuses: OK, missing, verify, mismatch if available.

Expected result:

- Panel explains what was detected in the TOC source.
- Panel explains what was detected on the target page.
- Panel explains why the match is OK, missing, verify, or mismatch.
- Panel offers relevant resolution actions.

### 5.8 Release Gate

Action:

- With blocking TOC issues present, inspect sidebar gate status, top status, issue count, and Confirm & Proceed button.
- Resolve blocking issues.
- Inspect the same gate surfaces again.

Expected result:

- All gate surfaces use one source of truth.
- Confirm & Proceed is disabled while blocking issues remain.
- Issue count and status update after resolutions.
- Confirm & Proceed becomes enabled only when blocking issues are resolved.

### 5.9 TOC and Heading Export Settings

Action:

- Change running-header level.
- Change chapter level.
- Change TOC position front/back.
- Toggle Arabic headings in translated body text.
- Change navigation/bookmark depth.
- Save to export profile.
- Refresh.

Expected result:

- Settings persist.
- Saved settings reload correctly.
- Settings are scoped to TOC/export behavior, not general body formatting.

### 5.10 Heading Style Customization

Action:

- Select H1 through H6 or translation/Arabic heading style options.
- Change heading style fields.
- Save heading style.
- Reset to baseline.

Expected result:

- Only heading-related styles are editable on this screen.
- Body, Quran, Hadith, quote, footnote, and general document styles are not exposed here.
- Saved heading style affects TOC preview and is available to Book Preview, DOCX export, and PDF export paths.
- Reset restores baseline heading style behavior.

### 5.11 Re-Detect TOC Protection

Action:

- Make manual OCR corrections.
- Confirm a target page.
- Confirm a heading level.
- Confirm a TOC entry.
- Run Re-detect TOC.

Expected result:

- Re-detect produces refreshed suggestions.
- It does not silently overwrite manually corrected OCR lines.
- It does not silently overwrite confirmed target pages, heading levels, or TOC entries.

## 6. Cross-Workflow Regression Tests

Goal: verify workstreams do not break each other.

### 6.1 OCR Decision to DPI Retry to Audit History

Action:

- Open an active OCR attention issue.
- Launch DPI retry from that issue.
- Accept a new region OCR candidate.
- Return to Audit.

Expected result:

- Active issue is removed or updated according to the accepted retry.
- Resolved/history view shows the superseded-by-rerun decision.
- Candidate and issue linkage survive refresh.

### 6.2 OCR Review to Translation View

Action:

- Accept or edit OCR text from OCR review.
- Open the same page in OCR/Translation or Triple view.

Expected result:

- OCR pane reflects the accepted/edited OCR text.
- Translation pane remains editable.
- Layout fitting in comparison views still works.

### 6.3 Translation Styles to Export

Action:

- Apply several translation paragraph styles.
- Edit the global style profile.
- Export DOCX.

Expected result:

- Export reflects current effective style profile.
- Segment paragraph style choices are honored.
- Missing critical fonts are surfaced before claiming full compliance.

### 6.4 TOC Settings to Export/Preview

Action:

- Change TOC export settings and heading styles.
- Open Book Preview or export path.

Expected result:

- TOC/heading choices are reflected where the preview/export path consumes them.
- General translation body styles remain controlled from the Translation editor/style system.

## 7. Reference Stack: sunnah.com, Shamela, dorar.net, CAMeL, Qur'an Carrier, and Hadith Review

Goal: verify the latest reference-stack fixes are wired end to end, visible in diagnostics, and usable by production hadith/protected-passage flows.

### 7.1 Environment and Settings Loader

Action:

- Confirm `SUNNAH_COM_API_KEY` is present in `backend/.env`.
- Restart the backend after editing `.env`.
- Open Diagnostics.
- Inspect the Environment status section.
- From `backend`, optionally run:

```bash
.venv/bin/python -c "from waraq.db.session import get_settings; print(bool(get_settings().sunnah_com_api_key))"
```

Expected result:

- Diagnostics shows `SUNNAH_COM_API_KEY (P-1 hadith)` as ready/wired.
- The backend command prints `True`.
- The app does not require starting the backend from the `backend` directory for `backend/.env` to be loaded.
- If the key is edited while the backend is already running, the old value remains until backend restart; this is expected because settings are cached.

### 7.2 Diagnostics Operational Overview

Action:

- Open Diagnostics.
- Inspect the Operational status overview.
- Compare it with the Environment status pills.

Expected result:

- Reference status reflects the sunnah.com key presence.
- The UI does not say sunnah.com is unwired when `sunnah_com_api_key_present` is true.
- No secret value is displayed anywhere; only presence/absence is shown.

### 7.3 Hadith Verification Without Manual sunnah.com Lookup Body

Action:

- Find or create a segment containing a recognizable hadith citation, for example `Sahih al-Bukhari 1`, `Bukhari, no. 1`, or an Arabic equivalent.
- In Diagnostics, paste that segment UUID into Hadith verification.
- Do not provide any manual sunnah lookup object.
- Click Verify.

Expected result:

- The backend infers the sunnah.com lookup from the segment text.
- `sources_skipped` does not include `sunnah_no_lookup_address` for a recognizable citation.
- If the key is valid and upstream is reachable, mandatory sources include a sunnah.com candidate.
- If sunnah.com is unreachable, the response records a clear `sunnah_unreachable:*` skip instead of crashing the verification flow.

### 7.4 Hadith Verification With No Recognizable sunnah.com Citation

Action:

- Use a segment that looks like hadith text but does not include a direct sunnah.com-style collection/number citation.
- Run Diagnostics Hadith verification.

Expected result:

- Verification still runs Shamela P-2 and dorar.net P-3 where possible.
- `sources_skipped` includes `sunnah_no_lookup_address`.
- The route returns a structured response rather than failing.
- If Shamela or dorar.net produce candidates, consensus and persistence continue without sunnah.com.

### 7.5 Shamela P-2 Lookup

Action:

- In Diagnostics, use the Shamela search section with Arabic hadith text known to exist in the local Shamela/Kutub-as-Sitta corpus.
- Run skeleton search.
- Then run Hadith verification on a segment containing the same or similar text.

Expected result:

- Shamela diagnostics returns local matches.
- Hadith verification includes Shamela candidates when local matches exist.
- Shamela remains usable without external network calls or API keys.
- Lack of a sunnah.com or dorar.net result does not stop Shamela-backed verification.

### 7.6 dorar.net P-3 Lookup

Action:

- Use a hadith-like segment suitable for dorar.net search.
- Run Hadith verification.
- Repeat once with normal network/API availability and once in a known unreachable/invalid configuration if practical.

Expected result:

- When dorar.net is reachable, dorar.net candidates can appear as mandatory hits.
- When dorar.net is unreachable or returns a Model U failure, the response includes a `dorar_unreachable:*` skip reason.
- dorar.net failure does not stop Shamela or sunnah.com candidates from being processed.

### 7.7 Mandatory Source Consensus and Persistence

Action:

- Run Hadith verification on a segment that returns at least one mandatory candidate.
- Note the returned `aggregate_uuid` and `single_source_uuids`.
- Refresh the page or call verification/review again.

Expected result:

- Verification returns a `run` object when candidates exist.
- `mandatory_count` reflects gathered P-1/P-2/P-3 hits.
- An active `HadithAggregateResult` is persisted.
- Source rows are persisted and linked to the aggregate.
- A new verification round supersedes prior active aggregate results instead of mutating old source rows.

### 7.8 Hadith Review Endpoint

Action:

- After a successful hadith verification, call:

```text
GET /segments/{satz_uuid}/hadith/review
```

- Inspect the returned aggregate, source rows, status, and extended source metadata.

Expected result:

- Response includes the active `aggregate_uuid`.
- Response includes source rows with source name, role, excerpt, locator where available, and reference flags.
- Response includes an open status when verification created one.
- Response includes available action types for the status class.
- Response includes extended source state metadata for E-1 through E-5.

### 7.9 Hadith H-1 Warning Decision

Action:

- Use or create a hadith verification result that produces an H-1/open warning status.
- Call:

```text
POST /segments/{satz_uuid}/hadith/status/{hadith_status_uuid}/decision
```

- Use body:

```json
{
  "action_type": "go_with_warning",
  "note": "E2E test acknowledgement"
}
```

Expected result:

- Response includes a `decision_event_uuid`.
- Status changes from `offen` to `quittiert`.
- The decision is recorded with `preflight_confirmation` semantics.
- Repeating the same decision on the already-acknowledged status returns a clear error rather than creating a duplicate decision.

### 7.10 Hadith H-2 Resolution Decision

Action:

- Use or create a hadith verification result with an H-2/open blocking status, for example a vocalization conflict.
- Call:

```text
POST /segments/{satz_uuid}/hadith/status/{hadith_status_uuid}/decision
```

- Use one canonical action type, for example:

```json
{
  "action_type": "vokalisierungskonflikt_manuell_entscheiden",
  "note": "E2E test resolution"
}
```

Expected result:

- Response includes a `decision_event_uuid`.
- Status changes from `offen` to `aufgeloest`.
- Unknown action types are rejected with a clear 400-level error.
- H-2 cannot be acknowledged with `go_with_warning`; it must use one of the seven canonical resolution action types.

### 7.11 CAMeL Morphology in Vocalization Comparison

Action:

- In Diagnostics, check morphology availability.
- Use the morphology diagnostic endpoint on an Arabic word that should return analyses.
- Run hadith verification on a case with vocalized variants if available.

Expected result:

- If CAMeL morphology DB is installed, diagnostics shows it as available and word analysis returns rows.
- Hadith consensus uses CAMeL lexeme refinement during vocalization comparison.
- If CAMeL is unavailable or has no useful analysis for a word, verification still works using text-only comparison.
- No hadith verification flow fails only because morphology data is missing.

### 7.12 Protected Hadith Translation Reference Payload

Action:

- Use a page/segment containing hadith text with a recognizable citation.
- Start translation for that page/project.
- Inspect the translation result/provenance context where available, or inspect persisted hadith aggregate/source rows after translation.

Expected result:

- Protected-passage handling tries hadith verification before general LLM translation handling for that segment.
- sunnah.com is attempted automatically when the segment includes a recognizable citation.
- Shamela and dorar.net candidates are still gathered according to availability.
- The translation provenance/reference payload identifies verified hadith sources.
- The flow does not silently fail the whole translation if one hadith source is unavailable.

### 7.13 Protected Qur'an Target Carrier Selection

Action:

- Use or create a segment containing a recognized Qur'an passage.
- Run the current translation flow normally.
- If a future target-language field is available, repeat with English target language.

Expected result:

- Current default behavior continues to use the German RWWAD carrier.
- When an English target language is passed by the backend caller, protected Qur'an translation selects `english_rwwad`.
- Existing project Qur'an snapshots are not reused when their stored `translation_key` differs from the requested target carrier.
- Missing local Qur'an carrier data returns a protected skip reason instead of sending Qur'an text to general LLM translation.

### 7.14 E-5 Extended Source State

Action:

- Run Hadith verification with manual extended set enabled.
- Inspect the returned `extended_sources_invoked` and Hadith Review extended source metadata.

Expected result:

- E-1 through E-4 remain visible as suspended structural sources.
- E-5 is visible as active special role metadata.
- Current E-5 runtime fetcher may return no hits until Official Live API details are implemented.
- The absence of E-5 hits is not treated as a crash.

### 7.15 Reference Stack Regression After Backend Restart

Action:

- Stop the backend.
- Start the backend from the repo root.
- Open Diagnostics and rerun Environment, Shamela search, morphology diagnostic, and Hadith verification.
- Stop the backend.
- Start the backend from the `backend` directory.
- Repeat the same checks.

Expected result:

- `backend/.env` is loaded in both startup locations.
- sunnah.com key presence is consistent.
- Shamela, CAMeL, and dorar.net behavior does not change only because the backend working directory changed.
- No diagnostics section reports a false "not wired" state caused by path resolution.

## 8. Known Acceptable Limitations During This Test Round

These are not failures against Observations and Changes2 unless the product scope is expanded.

- Quran/Hadith/Quote buttons style existing anchored paragraphs; they do not create new text segments.
- DPI selected-region acceptance updates the mapped OCR segment; it does not replace only a sub-segment character span.
- TOC Step 2 is scaffolded and becomes meaningful after translated TOC output exists.
- Exact canon font compliance requires installing missing fonts on the server:
  - `KFGQPC Uthmanic Script HAFS`
  - `Traditional Naskh`
  - `Calibri`
- Frontend build may warn about large chunks because of TipTap.
- E-5 is structurally represented but the concrete Official Live API integration remains a follow-up until API contract/key details are available.
- Protected Qur'an target-language carrier selection is implemented internally, but user-facing project/job target-language selection is still a follow-up.
- The backend Hadith Review endpoints are implemented; a dedicated frontend Hadith Review panel may still need UI work if it has not been added by the time this test is run.

## 9. Pass / Fail Summary Template

Use this section while testing.

| Area | Pass/Fail | Notes |
| --- | --- | --- |
| Pre-test setup |  |  |
| OCR comparison layouts |  |  |
| Translation editor/style system |  |  |
| OCR review/attention lifecycle |  |  |
| DPI retry recovery |  |  |
| TOC / IVZ review |  |  |
| Reference stack |  |  |
| Cross-workflow regressions |  |  |
