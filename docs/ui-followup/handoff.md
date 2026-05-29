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
   - Major redesign required.
   - Add Paragraph Style dropdown with canonical Waraq styles.
   - Separate paragraph styles from character styles.
   - Persist `internal_style_key` and editable `display_label`.
   - Add global style editing, structured Quran/Hadith/Quote blocks, font-library handling, and export/preflight integration.

3. OCR review, Attention List, and issue lifecycle
   - Mostly implemented.
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
   - Still remaining: a true crop-level OCR issue mapping model. The current retry endpoint returns an unsaved candidate and maps only to a page/segment plus optional crop rectangle; it does not persist candidate rows or bind a crop to a specific attention issue/finding ID.

4. TOC / IVZ review screen
   - Build from the mockup as a structural manuscript review station.
   - Include scan panel, editable TOC OCR text, structured table, issue resolution, release gate, export settings, and heading-style customization.
   - Re-detect must never silently overwrite manual decisions.

5. DPI Compare / OCR retry recovery
   - Current setup stage is acceptable.
   - Add post-retry result review with original crop, current OCR, new candidate, highlighted differences, mapping target, issue reference, and accept/reject/edit actions.
   - Acceptance must update OCR text and linked finding state.

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
- Before implementing, inspect existing frontend components in `Waraq/frontend/src/components/` and related backend routers/services in `Waraq/backend/waraq/`.
- The second observations document includes images; local rendered versions are already saved under `Waraq/docs/ui-followup/assets/`.
