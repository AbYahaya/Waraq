# Waraq Frontend Handover

Last updated: 2026-06-09

This document is for the frontend developer building the authentic Waraq frontend. The current frontend in `frontend/` is a working test harness and reference implementation, but it is expected to be discarded once the new frontend is complete and verified against the deployed backend.

## 1. Product Summary

Waraq is a web application for turning scanned Arabic Islamic books into reviewed OCR text, German translation, structured table of contents, and exportable DOCX/PDF output. The app is not a generic OCR/translation toy; it has canon rules around:

- OCR review status and audit decisions.
- Translation release gates and preflight export checks.
- Qur'an protection and source translation.
- Hadith verification through Shamela, Sunnah, and Dorar where available.
- Segment-level provenance, locks, history, and style/export rules.
- Project/account scoped glossary and entity handling.

The new frontend should feel like a serious production workspace for editors, not a landing page.

## 2. Deployment And API Base

Current deployed backend:

```text
https://waraq-backend-yabdulrauf.fly.dev
```

Local backend:

```text
http://127.0.0.1:8000
```

Backend docs are available from FastAPI:

```text
GET /docs
GET /openapi.json
```

Recommended frontend env:

```bash
VITE_API_URL=https://waraq-backend-yabdulrauf.fly.dev
```

All protected endpoints require:

```http
Authorization: Bearer <access_token>
```

Backend CORS must include the new frontend origin. On Fly this is set through `CORS_ORIGINS`.

## 3. Auth And Account Flow

Auth endpoints:

```http
POST /auth/register
POST /auth/login
GET  /auth/me
GET  /me/profile
PUT  /me/profile
PUT  /me/password
GET  /me/usage
```

Login body:

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

Login response:

```json
{
  "access_token": "...",
  "token_type": "Bearer"
}
```

Registration has an admission gate. Non-admin accounts can return `approval_status: "pending"` and no token. Admin users are determined by backend `ADMIN_EMAILS`, not by a database role.

`/auth/me` returns:

```ts
type Account = {
  account_uuid: string;
  email: string;
  display_name: string | null;
  active: boolean;
  approval_status: "pending" | "approved" | "rejected";
  is_admin: boolean;
};
```

Frontend behavior:

- Store bearer token securely enough for the app context. Existing frontend uses Zustand/local browser state.
- On 401, clear token and redirect to login.
- Show admin admission tools only when `is_admin === true`.
- Pending users should see an approval-pending screen, not a broken dashboard.

## 4. Core Object Model

Important IDs:

- `project_uuid`: project/book workspace.
- `page_uuid`: uploaded page.
- `block_uuid`: OCR block on page.
- `satz_uuid`: segment/sentence/paragraph unit. Most editing, translation, lock, history, hadith, and audit workflows are segment-scoped.
- `rev_uuid`: revision ID for OCR or translation text change.
- `po_uuid`: provenance object UUID, used for exports and evidence.
- `job_uuid`: upload/OCR/translation/preflight job.

Core response shapes:

```ts
type Project = {
  project_uuid: string;
  account_uuid: string;
  name: string;
  active: boolean;
};

type Page = {
  page_uuid: string;
  project_uuid: string;
  page_index: number;
  ocr_status: "ausstehend" | "in_review" | "go" | "go_with_warning" | "no_go";
  active: boolean;
};

type Segment = {
  satz_uuid: string;
  block_uuid: string;
  block_type?: string | null;
  satz_index: number;
  lock_flag: "none" | "manual_local" | "manual_editorial";
  current_rev_uuid: string | null;
  text_content: string | null;
  translation_style_key?: string | null;
  active: boolean;
};

type Job = {
  job_uuid: string;
  job_type: string;
  state: "pending" | "running" | "paused" | "completed" | "failed";
  project_uuid: string | null;
  payload: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  error: Record<string, unknown> | null;
};
```

## 5. Recommended App Structure

Minimum production navigation:

- Login / Register / Pending Approval.
- Dashboard: project list, new project, trash/restore.
- Project Workspace:
  - Project sidebar with upload, OCR, page list, translation/export, audit, TOC, guided review, dashboard shortcut.
  - Page viewer with scan preview, OCR pane, translation pane.
  - Mode controls: single/fullscreen, split OCR/translation, preview/read/edit.
- Audit Dashboard:
  - Project summary.
  - Attention list.
  - OCR review decisions.
  - Segment audit detail.
- TOC / IVZ Review.
- Preflight + Export dialog.
- Hadith Review panel.
- Glossary / Entities management.
- Account settings, notifications, usage.
- Admin admissions and admin project/account overview.

Do not rebuild the current test frontend visually. Use it only to understand workflows and request patterns.

## 6. Projects

Endpoints:

```http
POST   /projects
GET    /projects
GET    /projects/trash
GET    /projects/{project_uuid}
GET    /projects/{project_uuid}/translation-availability
POST   /projects/{project_uuid}/restore
DELETE /projects/{project_uuid}
```

Project deletion is soft-delete/trash. Trash entries include `deleted_at`, `restore_until`, `days_remaining`, and `restorable`.

UX requirements:

- Dashboard should clearly distinguish active and trashed projects.
- New project button should create a project and open workspace.
- `Workspace` navigation should remember last opened project on the client; backend does not maintain “last workspace.”

## 7. Upload Flow

Endpoints:

```http
GET  /uploads/projects/{project_uuid}/precheck?filename=<name>
POST /uploads
POST /uploads/{job_uuid}/chunks/{chunk_index}
GET  /uploads/{job_uuid}
POST /uploads/{job_uuid}/finalize
```

Flow:

1. User picks file.
2. Call upload precheck.
3. Show warnings for filename duplicates or existing pages.
4. Start upload with `project_uuid`, `original_filename`, `total_chunks`, `total_size_bytes`.
5. Upload chunks as multipart/form-data.
6. Finalize.
7. Backend creates pages.
8. Refresh project pages.

The backend supports chunked upload. The UI should show progress and recoverable errors.

Duplicate warnings are not hard blocks:

- Filename match: warn before upload.
- SHA-256 match: reported after finalize.
- Existing pages in project: warn because Waraq is currently one-book-at-a-time per project.

## 8. Pages, Scan Preview, OCR Text

Endpoints:

```http
GET /projects/{project_uuid}/pages
GET /pages/{page_uuid}
GET /pages/{page_uuid}/source-pdf
GET /pages/{page_uuid}/render-png
GET /pages/{page_uuid}/segments
GET /segments/{satz_uuid}
PUT /segments/{satz_uuid}/text
```

Workspace page view should:

- Show page list with scroll.
- Show scan preview from `/pages/{page_uuid}/render-png`.
- Show OCR text from `/pages/{page_uuid}/segments`.
- Let user edit OCR segment text through `PUT /segments/{satz_uuid}/text`.
- Preserve page/workspace view state across refresh using URL params or equivalent robust state.

Important: OCR and translation text are segment-based. Do not build a flat text editor that loses segment identity.

## 9. OCR Auto-Run And OCR Review

OCR endpoints:

```http
POST /ocr/jobs
POST /ocr/jobs/{job_uuid}/run/{satz_uuid}
POST /ocr/pages/{page_uuid}/run
POST /ocr/projects/{project_uuid}/run
GET  /ocr/jobs/{job_uuid}
POST /ocr/jobs/{job_uuid}/cancel
GET  /ocr/projects/{project_uuid}/active-job
```

OCR review endpoints:

```http
POST /pages/{page_uuid}/ocr-review/enter
POST /pages/{page_uuid}/ocr-review/findings
POST /pages/{page_uuid}/ocr-review/approve-go
POST /pages/{page_uuid}/ocr-review/approve-warning
POST /pages/{page_uuid}/ocr-review/resolve-no-go
```

OCR retry candidate:

```http
POST /pages/{page_uuid}/ocr-retry-candidate
```

OCR statuses:

- `ausstehend`: not reviewed/ready.
- `in_review`: page is in review.
- `go`: accepted.
- `go_with_warning`: accepted with warning.
- `no_go`: blocked until resolved.

UX requirements:

- Project-level “Run OCR” should show a job progress state and poll `/ocr/jobs/{job_uuid}`.
- Per-page OCR should be available.
- User should be able to enter OCR review and approve/reject with reasons.
- DPI/alternative OCR candidate review is backend-backed through retry candidate endpoints and audit decisions.

## 10. Translation Flow

Endpoints:

```http
GET  /projects/{project_uuid}/release-gate
POST /projects/{project_uuid}/release-gate/confirm-warning
POST /projects/{project_uuid}/release-gate/start-translation

POST /projects/{project_uuid}/translation-jobs
POST /translation-jobs/{job_uuid}/run
GET  /translation-jobs/{job_uuid}
POST /translation-jobs/{job_uuid}/cancel

PUT /segments/{satz_uuid}/translation-text
PUT /segments/{satz_uuid}/translation-style
```

Flow:

1. Check release gate.
2. If warnings require confirmation, confirm.
3. Call `start-translation` to set canonical translation-start decision.
4. Create translation job with selected segment UUIDs.
5. Run job.
6. Poll job until completed/failed.
7. Refresh segments.

Current engine behavior:

- Gemini is primary translation engine.
- OpenAI is optional check engine.
- User-facing output is the primary engine output.
- Cross-check data is recorded in translation provenance/audit when both engines run.
- If a page has failed segments, the translation service skips failed chunks and continues where possible; user can rerun failed pages/segments later.

Translation edit UX:

- Allow editing translated text segment-by-segment.
- Apply text formatting without losing segment identity.
- Save should activate when text/style changed.
- Refresh must preserve saved font/style/text changes.
- Read mode must be read-only.

## 11. Style System And Book Preview

Endpoints:

```http
GET /projects/{project_uuid}/style-profile
GET /projects/{project_uuid}/style-profile/fonts
PUT /projects/{project_uuid}/style-profile
PUT /segments/{satz_uuid}/translation-style
```

The style profile controls screen preview and DOCX/PDF export defaults. Segment style keys include normal text, headings, quote/protected blocks, footnotes, source notes, and hadith/Qur'an related styles.

The new frontend should provide:

- Word-like toolbar for translation/book preview editing.
- Paragraph style selector.
- Font family/size, bold/italic/underline/strike where backend-supported.
- Page preview modes:
  - translated only.
  - translated + OCR.
- Downloadable preview/export outputs.

Known caution: if the new frontend implements rich text, it must preserve backend segment boundaries. Backend currently stores segment translation text and paragraph style key; arbitrary inline rich text persistence may require backend extension if not already represented in revisions.

## 12. Glossary, Entities, Rule Binding, Conflicts

Glossary:

```http
POST  /glossary/lookup
GET   /glossary/entries
POST  /glossary/entries
PATCH /glossary/entries/{concept_id}
```

Entities:

```http
POST  /entities/lookup
GET   /entities
POST  /entities
PATCH /entities/{entity_id}
```

Rule binding:

```http
POST /segments/{satz_uuid}/rule-binding
```

Conflicts:

```http
GET  /segments/{satz_uuid}/conflicts
GET  /pages/{page_uuid}/conflicts
GET  /projects/{project_uuid}/conflicts
POST /conflicts/{conflict_uuid}/resolve/local-exception
POST /conflicts/{conflict_uuid}/resolve/glossary-change
POST /conflicts/{conflict_uuid}/resolve/lock-release
```

Frontend should make these usable but not noisy:

- Glossary and entities should be searchable and editable.
- Segment conflicts should show near the segment.
- Project conflicts should surface in audit/review.
- Lock-related conflicts require explicit resolution.

## 13. Segment Locks

Endpoints:

```http
POST   /segments/{satz_uuid}/lock
DELETE /segments/{satz_uuid}/lock
```

Lock body:

```json
{
  "level": "manual_local",
  "note": "optional"
}
```

Valid levels:

- `manual_local`
- `manual_editorial`

Locked segments reject some edits through backend invariant guards. The UI must show lock state clearly and avoid presenting edits as if they will save normally.

## 14. Qur'an Handling

Qur'an handling is mostly automatic in translation:

- Inline Qur'an spans like `﴿...﴾ [النساء: ٤٨]` can be recognized.
- The backend uses local Qur'an reference text and quranenc translations.
- Protected Qur'an passages should show provenance/source info instead of looking like anonymous LLM output.

Diagnostics:

```http
GET /diagnostics/quran/verse?sura=4&aya=48
GET /diagnostics/quran/translation?sura=4&aya=48&key=german_rwwad
```

UX requirement:

- Show “Qur'an source” / protected-source provenance for recognized passages.
- Do not underline or visually mark an entire segment if only a small inline Qur'an span is protected.
- Do not force protection for partial Qur'anic phrases used as grammar examples.

## 15. Hadith Verification

Backend endpoints:

```http
POST /segments/{satz_uuid}/hadith/verify
GET  /segments/{satz_uuid}/hadith/review
POST /segments/{satz_uuid}/hadith/status/{hadith_status_uuid}/decision
```

Verify request:

```json
{
  "sunnah_lookup": {
    "collection": "bukhari",
    "hadith_number": 1
  },
  "dorar_query": "optional free-text query",
  "manually_trigger_extended": false
}
```

All fields are optional.

Important source behavior:

- Shamela: local DB skeleton lookup. This is the easiest source to verify.
- Sunnah: direct lookup only. It needs `collection + hadith_number`; it is not a free-text search in this implementation.
- Dorar: free-text API search using configured base URL. If the Dorar API shape changes or endpoint is wrong, the backend returns skip reasons.

Verify response includes:

```ts
type HadithVerifyResponse = {
  satz_uuid: string;
  extended_set_triggered: boolean;
  extended_trigger_reason: string | null;
  extended_sources_invoked: string[];
  mandatory_count: number;
  extended_count: number;
  sources_skipped: string[];
  citations: Array<{
    source_name: string;
    quellen_rolle: string;
    matn_excerpt: string;
  }>;
  run: null | {
    aggregate_uuid: string;
    single_source_uuids: string[];
    superseded_aggregate_uuid: string | null;
  };
};
```

Review response includes:

```ts
type HadithReviewResponse = {
  satz_uuid: string;
  aggregate_uuid: string | null;
  vokalisierungsklasse: string | null;
  vokalisierungs_konflikt: boolean;
  reference_matn_excerpt: string | null;
  sources: Array<{
    single_source_uuid: string;
    source_name: string;
    quellen_rolle: string;
    matn_excerpt: string;
    collection_label: string | null;
    locator: string | null;
    authenticity_grade: string | null;
    is_reference_matn: boolean;
    is_reference_vocalization: boolean;
  }>;
  status: null | {
    hadith_status_uuid: string;
    hadith_stellen_typ: string;
    hadith_klasse: string;
    state: string;
    action_types: string[];
  };
  extended_sources: Array<{ source_id: string; name: string; state: string }>;
};
```

Required new frontend feature:

Build a real Hadith Review panel. The current frontend does not have a full production UI for this. It only has diagnostics, guided review references, difficulty/preflight counts, and some protected provenance support.

Hadith Review panel should:

- Work from selected segment.
- Show “Verify Hadith” action.
- Show Shamela/Sunnah/Dorar source cards.
- Show source excerpts, collection/locator, authenticity grade.
- Show `sources_skipped` in plain English.
- Show H-1/H-2 status and allowed decision actions.
- Let user post decisions through `/decision`.
- Link from preflight/audit/guided-review hadith blockers directly to this panel and segment.

Interpretation:

- `mandatory_count > 0` and `run != null`: verification found source candidates and persisted consensus.
- `aggregate_uuid != null` in review: active hadith verification result exists.
- `status != null` but `aggregate_uuid == null`: backend detected hadith-like text but no external candidate was available.
- `sunnah_no_lookup_address`: not a failure; no direct Sunnah collection/number was available.
- `sunnah_api_key_missing`: backend key missing/not loaded.
- `dorar_unreachable:ModelUClassA`: likely Dorar endpoint/config/request issue.
- `dorar_unreachable:ModelUClassB`: upstream/network/temporary or unsupported scraping fallback.

## 16. TOC / IVZ Workflow

Endpoints:

```http
GET  /projects/{project_uuid}/toc
POST /projects/{project_uuid}/toc/source-decision
POST /projects/{project_uuid}/toc/line-decision
POST /projects/{project_uuid}/toc/entry-decision
PUT  /projects/{project_uuid}/toc/export-settings
POST /projects/{project_uuid}/toc/redetect
POST /projects/{project_uuid}/toc/translated-review/confirm
POST /projects/{project_uuid}/toc/confirm
PUT  /toc/entries/{satz_uuid}
```

TOC page should be simple and explanatory:

1. Source pages: show detected candidates and allow manual correction.
2. OCR lines: mark/unmark TOC lines, correct, split, merge.
3. Entries: confirm/relink target headings/pages, set level.
4. Export settings: TOC position, heading levels, Arabic heading inclusion, navigation depth.
5. Translated TOC review.
6. Final confirmation.

`GET /projects/{project_uuid}/toc` returns everything needed for display:

- `entries`
- `ocr_lines`
- `source_candidates`
- `selected_source_page_indices`
- `workflow_state`
- `requires_attention`
- `attention_reasons`
- translated review state
- export settings summary

## 17. Audit Dashboard And Attention List

Endpoints:

```http
GET  /projects/{project_uuid}/audit/summary
GET  /projects/{project_uuid}/audit/attention
GET  /projects/{project_uuid}/audit/ocr-review-decisions
POST /projects/{project_uuid}/audit/ocr-attention/{issue_uuid}/decision
POST /projects/{project_uuid}/audit/ocr-differences/explain
GET  /projects/{project_uuid}/audit/segments/{satz_uuid}
```

Audit UI should include:

- Summary cards: OCR status, confidence, engine agreement, translation cross-check, findings.
- Attention list with filters.
- Explicit filter for deleted/ignored/historical items. Do not show ignored/deleted in normal list.
- OCR review decision history.
- Segment detail with engine readings, OCR/translation provenance, conflict/status data.
- “Explain differences” toggle that calls the backend and can be closed/toggled off.

OCR difference explainer uses OpenAI as third agent to compare Gemini/OpenAI OCR readings where available.

## 18. Guided Review And Difficulty

Endpoints:

```http
GET /pages/{page_uuid}/difficulty
GET /projects/{project_uuid}/difficulty
GET /projects/{project_uuid}/guided-review/queue
```

Difficulty breakdown includes:

- Audit findings.
- Consistency findings.
- Hadith H-1/H-2.
- OCR errors.
- Locks.

Guided review queue items:

```ts
type GuidedReviewItem = {
  kind: "audit_befund" | "konsistenz_befund" | "ocr_error" | "hadith";
  finding_uuid: string;
  tier: "p_03_blocking" | "p_04_blocking" | "warning";
  severity: string;
  detected_at: string;
  satz_uuid: string | null;
  page_uuid: string | null;
};
```

The guided review panel should jump to the segment/page and open the appropriate review panel: OCR, audit, hadith, conflict, etc.

## 19. Preflight And Export

Preflight endpoints:

```http
GET  /preflight/pflichtfragen/definitions
GET  /projects/{project_uuid}/preflight/guard-near
POST /projects/{project_uuid}/preflight/runs
POST /projects/{project_uuid}/preflight/runs/{run_uuid}/pflichtfragen
POST /projects/{project_uuid}/preflight/runs/{run_uuid}/pdf-format
GET  /projects/{project_uuid}/preflight/runs/{run_uuid}/pdf-format
POST /projects/{project_uuid}/preflight/runs/{run_uuid}/warnings
POST /projects/{project_uuid}/preflight/runs/{run_uuid}/evaluate
```

Export endpoints:

```http
POST /projects/{project_uuid}/exports
GET  /exports/artefacts/{po_uuid}
GET  /exports/artefacts/{po_uuid}/pdf
```

PDF choices:

- `digital_rgb`
- `print_pdf_x_1a`

Export request:

```json
{
  "project_uuid": "same-as-path",
  "project_title": "Book title",
  "preflight_run_uuid": "..."
}
```

Export error handling:

- `409` with `reason: "canon_rule_violations"` includes segment UUIDs and violation kinds. UI should show a fix list with direct links to affected segments.
- Preflight state changes also return 409.
- Download DOCX from `/exports/artefacts/{po_uuid}`.
- Download PDF from `/exports/artefacts/{po_uuid}/pdf`.

## 20. OCR Export

Endpoints:

```http
POST /projects/{project_uuid}/ocr-export/gate
POST /projects/{project_uuid}/ocr-export/confirm
POST /projects/{project_uuid}/ocr-export/run
GET  /ocr-export/artefacts/{po_uuid}
```

This exports OCR text rather than translation. Treat as a separate export flow.

## 21. Notifications And Background Jobs

Endpoints:

```http
GET  /me/notifications
POST /me/notifications/{notification_uuid}/read
POST /me/notifications/read-all
GET  /me/notifications/preferences
PUT  /me/notifications/preferences
GET  /me/active-background-jobs
```

Use notifications for:

- Translation started/completed/failed.
- Preflight started/evaluated.
- Export ready.
- TOC confirmation.
- OCR jobs where surfaced.

The backend currently uses HTTP background tasks rather than a separate worker. The UI should poll job endpoints and tolerate backend restarts.

## 22. History And Provenance

Endpoints:

```http
GET /segments/{satz_uuid}/history
GET /pages/{page_uuid}/history
GET /projects/{project_uuid}/history
GET /history/segment/{satz_uuid}
GET /history/page/{page_uuid}
GET /history/project/{project_uuid}
GET /history/log
```

Segment history includes:

- revisions
- decision events
- provenance objects
- log entries
- conflicts
- Qur'an passage metadata where present

Build a “History / Sources” drawer for selected segment. This is important for trust: users need to know whether text came from OCR, manual edit, translation, protected Qur'an, hadith verification, etc.

## 23. Diagnostics

Diagnostics are useful for developers/admins, not core user workflow:

```http
GET /diagnostics/environment
GET /diagnostics/segments/{satz_uuid}/ocr-po
GET /diagnostics/quran/verse
GET /diagnostics/quran/translation
GET /diagnostics/shamela/search
GET /diagnostics/morphology/analyze
```

Do not expose diagnostics as a main user page unless behind admin/dev mode.

## 24. Admin

Endpoints:

```http
GET  /admin/accounts
GET  /admin/projects
GET  /admin/admissions/pending
POST /admin/admissions/{account_uuid}/approve
POST /admin/admissions/{account_uuid}/reject
```

Admin UI should include:

- Pending admissions.
- Approve/reject with note for rejection.
- Account/project overview.

Only show when `/auth/me.is_admin` is true. Backend still enforces auth.

## 25. Current Frontend Reference Files

The current frontend is disposable, but these files are useful references:

```text
frontend/src/lib/api.ts                 # fetch wrapper and auth header behavior
frontend/src/lib/queries.ts             # query keys and many response DTOs
frontend/src/lib/types.ts               # common TS types
frontend/src/pages/ProjectWorkspace.tsx # current workspace behavior
frontend/src/pages/ProjectAudit.tsx     # audit surface
frontend/src/components/TocPanel.tsx    # current TOC workflow
frontend/src/components/TranslationExportDialog.tsx
frontend/src/components/TranslationPane.tsx
frontend/src/pages/Diagnostics.tsx
```

Use these for API behavior, not visual design.

## 26. UX Requirements From Recent Testing

These are user-validated requirements:

- UI copy must be English.
- Workspace sidebar should contain project workflow controls, page list, upload, OCR, translate/export, audit difficulty, TOC/review links, and dashboard shortcut.
- Other app pages keep the normal app sidebar.
- Workspace sidebar must scroll internally.
- Page list must scroll.
- Top navigation should be sticky.
- OCR and translation panes can have internal scrollbars while global scroll remains usable.
- Workspace/page view state should survive refresh.
- Other page view state should survive refresh where meaningful.
- Read mode must be read-only.
- Translation pane should not be accidentally redesigned if a specific pane is already working.
- Book preview/export preview should match downloaded output as closely as technically possible.
- Export/preflight options must be understandable.
- Preview/download should support translated-only and translated+OCR outputs.
- Hadith review UI is missing and should be built.
- Deleted/ignored audit items belong in an explicit filter, not the default attention list.

## 27. Known Backend/Workflow Gaps To Design Around

These are not frontend bugs:

- Hadith review has backend endpoints but no complete current production UI.
- Sunnah.com requires direct collection + hadith number; free text search is not implemented.
- Dorar endpoint shape may need deployment/config calibration.
- Rich inline text styling beyond segment text/style key may need backend extension if the new frontend wants full word-processor inline formatting persistence.
- Current PDF validation with veraPDF is skipped unless veraPDF is installed in deployment.
- Background jobs are HTTP-background-task driven, not a separate Celery worker.

## 28. Recommended E2E Build Order For New Frontend

1. Auth, admission states, token handling.
2. Dashboard/project CRUD/trash.
3. Project workspace shell with pages, scan preview, OCR/translation panes.
4. Upload and page creation.
5. OCR run + OCR review status.
6. Translation release gate + job run/polling.
7. Translation editor + style profile + preview.
8. Audit dashboard and attention list.
9. TOC workflow.
10. Preflight + export DOCX/PDF.
11. Hadith review panel.
12. Glossary/entities/conflicts/locks/history.
13. Notifications, account settings, admin.

## 29. Quick Smoke Test Script

Use this sequence after the new frontend can log in:

1. Login.
2. Create project.
3. Upload a PDF.
4. Confirm pages appear.
5. Run OCR on one page.
6. Confirm OCR segments appear.
7. Approve OCR page.
8. Start translation gate and translate one page.
9. Confirm translated text appears and survives refresh.
10. Open audit summary.
11. Open TOC panel.
12. Run preflight.
13. Export DOCX.
14. Download DOCX.
15. Download PDF.
16. For a hadith segment, run hadith verify and show review panel.

## 30. Example Fetch Wrapper

```ts
const API_BASE = import.meta.env.VITE_API_URL.replace(/\/+$/, "");

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = authStore.getToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  const contentType = res.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? await res.json().catch(() => null)
    : await res.text();
  if (!res.ok) {
    throw { status: res.status, body, detail: body?.detail ?? String(body) };
  }
  return body as T;
}
```

## 31. Final Notes For The Frontend Developer

- Treat `/openapi.json` as the source of truth when types are unclear.
- Prefer generated API types from OpenAPI if possible.
- Preserve UUIDs and segment identity through every UI action.
- Do not hide backend skip reasons; translate them into understandable user messages.
- Poll jobs rather than assuming immediate completion.
- Never present diagnostics-only behavior as normal user workflow.
- Build the authentic UI around workflows: Upload → OCR → Review → Translate → Audit/TOC → Preflight → Export.
