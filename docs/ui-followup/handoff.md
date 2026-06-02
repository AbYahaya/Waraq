# UI Follow-Up Handoff

Date: 2026-05-28

## Purpose

Use this handoff when context is exhausted or a new session needs to continue the UI follow-up work efficiently.

## Active Scope Rule

`Observations and Changes2.pdf` is the authoritative follow-up scope.

Anything from `Observations and Changes.pdf` that is not repeated in `Observations and Changes2.pdf` should be treated as already implemented or outside the current fix pass.

## Key Files

- Main implementation plan: `Waraq/docs/ui-followup/observations-changes2-implementation-plan.md`
- Latest source PDF: `Waraq/Observations and Changes2.pdf`
- Earlier source PDF: `Waraq/Observations and Changes.pdf`
- Visual references: `Waraq/docs/ui-followup/assets/`

Important visual assets:

- `changes2-translation-editor-current.png`
- `changes2-translation-editor-target.png`
- `changes2-ocr-review-rerun.png`
- `changes2-attention-list-expanded.png`
- `changes2-attention-list-reasons.png`
- `changes2-toc-ivz-mockup.png`

## Remaining Workstreams

1. OCR read/edit view in comparison layouts
   - Implemented in `Waraq/frontend/src/components/OcrPane.tsx`.
   - OCR page frame now fits the full page width into the available pane.
   - OCR read/edit containers measure pane width and scale typography/padding down proportionally in narrow comparison panes.
   - Horizontal OCR scrolling is intentionally avoided.
   - OCR text rendering now supports inline alignment markers such as `[[center]]...[[/center]]`.
   - Verified with `npm run typecheck`; run `npm run build` after any additional edits.

2. Translation editor / Word-like style system
   - Implemented.
   - TipTap / ProseMirror is now the approved editor foundation and installed in the frontend package.
   - Editable translation mode now uses a TipTap editor instead of the old textarea, while preserving segment anchors.
   - Added Word-like translation toolbar with paragraph style, font, size, bold, italic, underline, strike, alignment, line-height, footnote/Quran/Hadith/quote style actions, save style, and save page controls.
   - Added canonical first-pass style definitions in `Waraq/frontend/src/lib/translation-styles.ts`.
   - Added per-style `translation_style_templates` in the project style profile. Each style carries display label, font, size, line height, spacing, DOCX size, alignment, first-line indent, left indent, left-rule flag, italic, and bold.
   - Added selected style-template editor; changes apply globally to all paragraphs using that style after saving.
   - Segment paragraph style keys persist as segment-scoped Decision Events with `decision_type=translation_paragraph_style_update`, `decision_source=style_management`, and `content.internal_style_key`.
   - Added `PUT /segments/{satz_uuid}/translation-style`.
   - Segment API responses now include `translation_style_key`.
   - DOCX export now reads saved style keys and per-style templates, mapping them to DOCX paragraph styles and applying saved font/size/spacing/alignment/indent/bold/italic values.
   - Added `GET /projects/{project_uuid}/style-profile/fonts` for server font-library visibility.
   - Toolbar uses server-available fonts and surfaces missing critical fonts from guard-near preflight.
   - Quran/Hadith/Quote buttons apply three-part style sequences to the current and following anchored paragraphs. They do not create brand-new segments because the current text model requires segment anchors for persistence/history.
   - Local font check found `Noto Sans Arabic` available; likely missing/needs install: `KFGQPC Uthmanic Script HAFS`, `Traditional Naskh`, and `Calibri`.

3. OCR review, Attention List, and issue lifecycle
   - Implemented.
   - Existing backend page approval already persists OCR review Decision Events, resolves non-blocking OCR error rows, and suppresses accepted OCR-PO attention rows when the approval is newer than the OCR result.
   - Added `GET /projects/{project_uuid}/audit/ocr-review-decisions` as a resolved/history read path over OCR review Decision Events.
   - Audit page now has `Active attention` and `Resolved OCR decisions` tabs.
   - Active OCR attention now groups duplicate low-confidence/divergent-engine signals for the same page/block/segment.
   - Expanded OCR issue view now shows reason definitions, clearer action-result messages, a larger original scan preview, and inline difference highlighting.
   - Added segment-level OCR attention decisions for ignored/deleted findings via Decision Events; ignored/deleted findings are hidden from Active attention and visible only inside the explicit `Ignored / deleted` resolved-decision filter.
   - Added return navigation from page review back to the focused Audit attention item.
   - OCR engine differences now keep deterministic inline highlighting and add an OpenAI-backed reviewer endpoint, `POST /projects/{project_uuid}/audit/segments/{satz_uuid}/ocr-difference-explanation`, for Arabic-specific explanations. Gemini is treated as the primary OCR reading, OpenAI as the comparison reading, and the returned explanation maps how OpenAI differs from Gemini line by line plus character-level notes. It requires `OPENAI_API_KEY`; optional model override is `OPENAI_OCR_DIFF_MODEL` and defaults to `gpt-4o`.
   - Added explicit `superseded by OCR retry` lifecycle handling. Accepting a DPI retry candidate saves OCR text, creates an OCR Review Decision Event with `decision_type=ocr_attention_superseded_by_rerun`, suppresses the active attention item when newer than the OCR-PO, and shows it only in the explicit resolved `Superseded by retry` filter.
   - DPI retry acceptance records trace metadata in the superseded decision: candidate UUID, page UUID, segment UUID, scope, engine, DPI, crop, changed flag, and character count.
   - Added persisted OCR lifecycle tables via migration `0028`: `ocr_attention_issues` and `ocr_retry_candidates`.
   - Active OCR attention now has stable issue UUIDs, persisted state, source OCR-PO UUIDs, and group keys.
   - Resolved OCR decisions expose accepted, warning, unresolved, superseded, historical, and ignored/deleted filters.
   - OCR retry candidates are persisted and can link to an OCR issue UUID; accepted candidates link back to the superseded Decision Event.
   - Current text replacement remains segment-level because the app's OCR text model is segment-level; crop boxes are persisted for audit/history.

4. TOC / IVZ review screen
   - Implemented in `Waraq/frontend/src/components/TocPanel.tsx`, `Waraq/backend/waraq/toc/service.py`, and `Waraq/backend/waraq/api/routers/toc_router.py`.
   - Rebuilt from the mockup as a structural manuscript review station, then corrected after user testing to start with TOC source-page detection/confirmation instead of dumping page-by-page fallback rows.
   - Backend now scores pages for TOC-likeness using title, line-ending page number, dot-leader, short-line density, and adjacent-page continuity signals.
   - `GET /projects/{project_uuid}/toc` now returns `source_candidates`, `selected_source_page_indices`, and `source_selection_state`.
   - Added `POST /projects/{project_uuid}/toc/source-decision` for accepting detected source pages, setting a manual source-page range, choosing no TOC/page-by-page fallback, or returning to auto detection.
   - Confirmed/detected TOC source pages are parsed into editable source lines and structured entries, then matched to nearby body headings using target page and fuzzy heading-text similarity.
   - If no TOC is detected, the UI now shows a clear no-TOC state with "Use page-by-page fallback" instead of a confusing 1-row-per-page active table.
   - Release gate now blocks translation while detected/source-page TOC structure requires Phase 4 confirmation.
   - Step 2 final translated TOC review now has a persisted confirmation endpoint and UI action; export preflight blocks when translated TOC review is required but unconfirmed.
   - TOC export settings now prefill the Translate & Export preflight Pflichtfragen, while preserving the required active per-export confirmation.
   - Includes top workflow steps, original scan panel, editable TOC OCR text, structured TOC table, issue resolution, release gate, export settings, and heading-style customization.
   - Original scan panel supports page render, zoom, previous/next line navigation, selected-line highlight, and re-detect messaging.
   - OCR text panel persists save/cancel correction, split, merge-next, mark TOC, mark not TOC, and protected/manual correction indicators via TOC Decision Events.
   - Structured table supports row selection, heading edit, persisted relink, persisted confirm-match, status display, translation preview, and add-entry from selected OCR source line.
   - `GET /projects/{project_uuid}/toc` now returns replayed `ocr_lines`, line keys, manual/protected flags, entry status, target-page fields, and latest export settings.
   - Added persisted endpoints for TOC line decisions, entry decisions, export settings, and re-detect requests. Re-detect preserves manual line/entry decisions by replaying them after detection.
   - Heading style customization is limited to heading styles and persists heading-relevant fields through the project style-profile endpoint.
   - Step 2 final translated review is scaffolded as a workflow phase for post-translation review.
   - Selected-area TOC OCR routes to the existing DPI recovery flow for the selected source page.
   - Re-detect messaging states that manual OCR corrections and confirmed decisions are preserved.

5. DPI Compare / OCR retry recovery
   - Implemented for the current page/segment lifecycle model.
   - Current low/high DPI setup is preserved.
   - Post-retry review now shows original crop/page preview, current OCR, new candidate, highlighted differences, mapping target, source attention context, acceptance effect, and explicit accept/keep/edit/discard actions.
   - Audit attention rows now include `Open DPI retry`, opening the workspace DPI panel with source attention context.
   - Acceptance updates OCR text, creates a `ocr_attention_superseded_by_rerun` Decision Event, suppresses the old active attention item when newer than the OCR-PO, and keeps the action in resolved OCR decision history.
   - True issue/candidate persistence is now implemented through `ocr_attention_issues` and `ocr_retry_candidates`; crop text replacement remains segment-level.

## Recommended Implementation Order

1. OCR comparison rendering consistency. Done.
2. OCR finding lifecycle and Attention List state model.
3. DPI retry result review connected to the lifecycle model.
4. TOC / IVZ structural review screen.
5. Translation editor and canonical style system.

## Open Questions to Answer During Implementation

- Should the translation editor use a rich-text editor library such as TipTap/ProseMirror, or continue with custom components?
- Are critical baseline font files available on the server, or should upload/selection be implemented first?
- Does backend OCR already support selected-region OCR and mapping back to page/block/segment?
- Should selected-area OCR controls be active now or scaffolded as disabled until backend support exists?
- Should TOC final Step 2 translated review ship in the first pass or be scaffolded after Step 1 structural review?
- Should `deleted / ignored` findings remain visible in normal history, or only in an explicit historical/ignored filter?
  Answered: deleted / ignored findings should only appear inside an explicit ignored/deleted filter.

## Notes for Future Sessions

- Keep UI copy in English.
- Keep canonical internal style keys stable even when user-facing labels are editable.
- Do not reintroduce items from the first observations document unless they are also present in the second document or the user explicitly asks for them.
- Main sidebar navigation now uses `Workspace` instead of `Projects`. It opens the last remembered `/projects/...` workspace URL from `frontend/src/lib/workspace-memory.ts`; if no valid remembered workspace exists, it stays disabled.
- Project workspace sidebar intentionally includes a `Dashboard` shortcut beneath the project difficulty badge.
- Project workspace sidebar is internally scrollable so added controls do not compress the page list or overflow awkwardly.
- View state that should survive refresh is stored in URL params. Workspace uses `view`, `pane`, `edit`, and `panel`; Book Preview uses `preview` and `preview_style`; TOC uses `toc_phase`; DPI Compare uses `ref_dpi`, `retry_dpi`, `dpi_zoom`, and `dpi_engine`; Audit uses `tab`, `filter`, and `resolved`; Admin uses `account`.
- Workspace view state is URL-derived in `ProjectWorkspace.tsx`; do not reintroduce mirrored React state plus URL-sync effects for `view`/`pane`/`edit`/`panel`, because clicking another page can otherwise cause a Solo/Double oscillation. `PageList.tsx` preserves `location.search` when navigating between project pages.
- Unsaved action/draft state such as dialog contents, passwords, OCR retry crop boxes, and unaccepted OCR candidates is intentionally not persisted unless it becomes server-backed.
- Before implementing, inspect existing frontend components in `Waraq/frontend/src/components/` and related backend routers/services in `Waraq/backend/waraq/`.
- The second observations document includes images; local rendered versions are already saved under `Waraq/docs/ui-followup/assets/`.
- Reference stack gap pass, 2026-06-01:
  - Added `backend/waraq/hadith/citation_extract.py` for sunnah.com citation extraction.
  - `backend/waraq/api/routers/hadith_router.py` now reads sunnah.com API key through `get_settings()`, infers direct sunnah.com lookups from segment text, creates open hadith status rows after verification, and exposes `/review` plus `/status/{hadith_status_uuid}/decision` endpoints.
  - `backend/waraq/translation/protected_passages.py` now tries sunnah.com when a citation is present, records/reuses hadith statuses, and can select `english_rwwad` for protected Qur'an translations when a caller passes an English target language. Current translation jobs still do not pass a target language, so default behavior remains German.
  - `backend/waraq/hadith/consensus.py` now uses CAMeL lexeme refinement for vocalization comparison when available.
  - `backend/waraq/api/routers/diagnostics_router.py` now reports sunnah.com key presence from the app settings loader.
  - `backend/waraq/db/session.py` now explicitly includes `backend/.env` as a settings source, avoiding false "not wired" diagnostics when the backend process is started from another working directory. Existing running servers still need restart after `.env` edits because settings are cached.
  - Verified with backend py_compile and API import. Targeted hadith-router pytest timed out after collection under `timeout 30`; no traceback.
  - Follow-ups: frontend Hadith Review panel, first-class project/job target-language setting, and concrete E-5 Official Live API integration once API contract/key details are available.
- Hadith detector follow-up, 2026-06-02:
  - User tested segment `e9827205-6ba9-4fbd-90af-3c41087ae75d`; `/hadith/review` returned `aggregate_uuid: null`.
  - Root cause found in `translation/protected_passages.py`: protected translation marker detection did not catch phrasing like `أن رسول الله ﷺ قال` / `وفي رواية`.
  - Expanded `_looks_like_hadith` markers and added regression assertions in `backend/tests/translation/test_protected_passages.py`.
  - Verified with `py_compile waraq/translation/protected_passages.py` and `pytest tests/translation/test_protected_passages.py -q`.
- Hadith no-candidate behavior, 2026-06-02:
  - User manually verified the same segment and got `mandatory_count: 0`, `extended_count: 0`, `sunnah_no_lookup_address`, `dorar_unreachable:ModelUClassA`, and `run: null`.
  - Added shared `backend/waraq/hadith/detection.py`.
  - Protected translation now records H-2/N-7 and skips with `hadith_external_verification_unavailable` when hadith-like text has no external candidates, preventing silent ordinary LLM translation.
  - Manual hadith verification now records H-2/N-7 in the no-candidate hadith-like/manual-extended case, so `/hadith/review` can show an open status even without aggregate/source rows.
  - Verified with py_compile, `pytest tests/translation/test_protected_passages.py -q`, and API import.
