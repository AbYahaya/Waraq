# Waraq E2E Test Plan — Phases 1–4

**Goal:** confirm every Phase 1–4 feature is reachable from the running app and produces the expected canonical output. Each section has: (1) prerequisites, (2) steps, (3) expected result, (4) what a failure looks like.

**Audience:** the project owner (you), running the app locally before Phase 5.

---

## 0. Boot the app

```bash
# Backend (one terminal)
cd /home/abyahaya/Waraq/Waraq/backend
set -a && source .env && set +a
.venv/bin/uvicorn waraq.api.main:app --reload --port 8000

# Frontend (another terminal)
cd /home/abyahaya/Waraq/Waraq/frontend
npm run dev
```

Frontend opens at `http://localhost:5173`. Backend OpenAPI at `http://localhost:8000/docs`.

**Login:** use any account you've registered, or hit `/register` to create one. Once logged in, you'll see the app shell with a `Diagnostics` link in the top nav.

---

## 1. Diagnostics page — environment + data probes

Open **`/diagnostics`** from the top nav. This is the lean test surface — nothing pretty, just verifies every Phase 1–4 backend feature is wired and the data we ingested is reachable.

### 1.1 — Environment status pills

**Step:** load the page; the first section auto-loads.

**Expected:** six pills:
- ✓ OPENAI_API_KEY
- ✓ GOOGLE_AI_API_KEY
- ✓ GOOGLE_APPLICATION_CREDENTIALS (Cloud Vision)
- ✗ SUNNAH_COM_API_KEY (P-1 hadith) — *red, you don't have one yet*
- ✓ CAMeL morphology DB
- ✗ kraken (manuscript OCR) — *red until you `pip install kraken` and download a model; the adapter is wired, just inactive*

**If failing:** verify `backend/.env` has the corresponding keys; verify Cloud Vision JSON path is correct; verify CAMeL DB present at `~/.camel_tools/`. The kraken pill is expected red on a fresh install — see §9 for the activation walk-through.

### 1.2 — Tanzil-Hafs Qurʾān verse lookup (Phase 2D)

**Step:** Sura `1`, Āya `1`, click **Lookup**.

**Expected:** Arabic text rendered RTL — **`بِسۡمِ ٱللَّهِ ٱلرَّحۡمَٰنِ ٱلرَّحِيمِ`**. Footer shows `tanzil-hafs-uthmani@risan-quran-json-mirror-1.0`.

**Try other ayas:** Sura `2`, Āya `255` (Āyat al-Kursī) should return its full vocalized form. Sura `114`, Āya `6` returns the last verse.

**If failing:** the AR-Referenzbestand is empty. Re-run `python scripts/ingest_tanzil_quran.py data/tanzil/quran-uthmani.txt risan-quran-json-mirror-1.0`.

### 1.3 — quranenc translation lookup (Phase 2B)

**Step:** Sura `1`, Āya `1`, key `german_rwwad`, click **Lookup**.

**Expected:** **`Im Namen Allahs, des Allerbarmers, des Barmherzigen.`** Footer: `german_rwwad@local_fallback`.

**Switch to `english_rwwad`** + click Lookup again: **`In the Name of Allah, the Most Compassionate, the Most Merciful.`** (or similar — the exact text comes from quranenc.com).

**If failing:** quranenc cache empty. Re-run `python scripts/sync_quranenc.py both`.

### 1.4 — CAMeL Tools morphology (Phase 4 sub-batch J operator step 3)

**Step:** word `بِسْمِ`, click **Analyze**.

**Expected:** Several analyses (probably 1–3 rows). Each row shows `diac | lex | root | pos | gloss`. For `بِسْمِ` you should see the lex `إِسْم` (noun "name"), root `س.م.و` or similar, pos `noun`.

**Try other words:**
- `قال` → `قَال` lex, root `ق.و.ل`, pos `verb`
- `العلماء` → noun, root `ع.ل.م`
- `بسم` (no diacritics) → multiple analyses since the form is ambiguous

**If failing:** CAMeL DB not installed. Run `.venv/bin/camel_data -i morphology-db-msa-r13`.

### 1.5 — Shamela search (Phase 4 sub-batch B' + sub-batch D Stage-3 statistical)

**Step:** Query `إنما الأعمال بالنيات`, mode `Mode A — skeleton`, `Kutub-as-Sitta only` checked, click **Search**.

**Expected:** **1+ hit** — `صحيح البخاري §1`, marked `[Kutub]`. The matn excerpt shows `إنما الأعمال بالنيات وإنما لكل امرئ ما نوى`.

**Try Mode B (keyword):** Query `الأعمال`, mode `Mode B — keyword`, uncheck Kutub-only. Should return hits across the corpus.

**Try a non-Hadith query:** Query `gibberish text not in any source`. Expected: `0 hits`.

**If failing:** Bukhari corpus not ingested. Re-run `python scripts/fetch_openiti.py sahih_bukhari` (or check session resume notes).

### 1.6 — OCR-PO inspector (Phase 4 sub-batch C/D/E/G/H — Stage 2/3/4/5)

**Step:** *(needs a segment with OCR done)* — see §3 below to OCR a page first. Then come back here with a `satz_uuid` (find one in the workspace URL or the page's segment list). Paste the UUID, click **Inspect**.

**Expected:** JSON payload with these keys (sub-batch C through H all visible in one place):
```json
{
  "model": "gemini-2.5-flash",
  "text_chars": <int>,
  "text_changed": true,
  "rev_uuid": "...",
  "ocr_job_uuid": "...",
  "confidence_score": <0-1 float>,
  "confidence_class": "accepted" | "deficient" | "critical",
  "was_preprocessed": false,        // true when source was < 200 DPI
  "source_dpi": 200,
  "quality_breakdown": {
    "overall": <0-1>, "completeness": <0-1>,
    "structural_symmetry": <0-1>, "char_count": <0-1>, "known_passage": <0-1>
  },
  "homoglyph_suggestion_count": <int>,
  "homoglyph_suggestions": [...],   // CAMeL-backed candidate flags
  "engines": [
    {"engine": "gemini",        "text_chars": ..., "confidence": null,  "error_class": null},
    {"engine": "cloud_vision",  "text_chars": ..., "confidence": <0-1>, "error_class": null}
  ],
  "engine_agreement": "exact_match" | "skeleton_equal" | "divergent" | "single_engine" | "engine_error",
  "stage3": {
    "confidence":  <0-1>,
    "stage2_score": <0-1>,
    "divergence_penalty_applied": false,
    "rules": {"score": <0-1>, "morphology_available": true, ...},
    "statistical": {"score": <0-1>, "hit_count": <int>, "scoped_to_kutub_as_sitta": false, ...},
    "ai": {"score": <0-1>, "agreement": "agree" | "disagree" | "single_engine" | "no_engine",
           "verdicts": [{"engine": "openai/gpt-4o", ...}, {"engine": "google/gemini-2.5-pro", ...}]}
  }
}
```

**This single payload is the canonical "everything Phase 4 produced" view.**

**If failing:**
- `payload: null` → segment hasn't been OCR'd yet
- `engines: null` → multi-engine wiring not invoked (legacy single-engine path)
- `stage3: null` → Stage-3 aggregator not invoked
- `morphology_available: false` → CAMeL DB missing
- `ai.verdicts[*].error_class: "Stage3AiValidatorUnconfigured"` → API keys missing in `.env`

### 1.7 — Hadith verification (Phase 4 sub-batch I + J)

**Step:** *(needs a segment with Arabic Hadith text)* — easiest path:
1. Go to your project workspace
2. Pick a page that has a Hadith
3. Find the segment UUID containing a Hadith matn

Paste the satz_uuid, leave "Manually trigger extended" unchecked, click **Verify**.

**Expected:** Mandatory hits ≥ 1 (P-2 Shamela path always runs against Bukhari). The citation list shows `shamela [pflicht]` rows. The "skipped" line shows `sunnah_no_lookup_address` (you didn't pass a sunnah lookup) and `sunnah_api_key_missing` would also appear if you did. Run summary shows the persisted aggregate UUID + N single-source UUIDs.

**Try with a non-Hadith segment:** mandatory_count = 0, run is null, sources_skipped lists the reasons.

**Try with manual extended trigger:** Same payload + `extended_set_triggered: true`, `extended_trigger_reason: "manual"`. v1.0 extended fetchers all return empty hits, so `extended_count` stays 0 — but the trigger fired.

---

## 2. Translation pipeline (Phase 1)

### 2.1 — Open a project, run translation

**Pre:** project with a few OCR'd pages whose segments contain Arabic source text.

**Step:**
1. Workspace → click **Start translation** (the release-gate panel)
2. Wait for the translation Job to complete (progress bar in the top right)

**Expected:**
- Each segment fills with German on the right pane
- TRANSLATION-PO records show `engine: "openai/gpt-4o"` + `cross_check.situation` (one of `agreement | auto_correction | substantive_deviation | ambiguity | check_failed`)
- Auto-normalize fired: digits are Western (no `٠١٢٣`), `ﷺ` glyph instead of `صلى الله عليه وسلم` if the LLM emitted the long form, EI2 transliteration with `Q` not `Ḳ` and `J` not `Dj`

### 2.2 — Glossary precedence (Tier 1) — Phase 1 sub-batch D

**Pre:** add a glossary entry via the workspace glossary panel (e.g., canonical_label `الإجماع`, gloss `Konsens`).

**Step:** Re-run translation on a segment containing `الإجماع`.

**Expected:** German output uses `Konsens` (the canonical gloss). If the LLM used a different rendering, a `glossary_precedence_violations` entry lands on the TRANSLATION-PO (visible via `/segments/{u}/history`).

### 2.3 — Untracked technical-term handling — Phase 4 sub-batch G

**Step:** translate a segment containing an Islamic technical term NOT in your glossary (e.g., `الصلاة`).

**Expected:** the LLM emits the §4.17 first-occurrence pattern: `Salāh (الصلاة) [Anm.: das rituelle Pflichtgebet im Islam; Source: AI]` (form may vary; the `[Source: AI]` marker is the canonical signal that this isn't from the glossary).

**Verify in OCR-PO inspector (§1.6 above):** `chunk_brief.untracked_term_candidates[]` lists this surface form.

---

## 3. OCR pipeline (Phase 4)

### 3.1 — Upload a PDF and run OCR on a page

**Step:**
1. Dashboard → New project → upload an Arabic PDF
2. Open a page → click **Run OCR**
3. Wait for the OCR Job

**Expected:**
- Page goes from `ausstehend` → `vorgeschlagen` → `bearbeitet` after review
- The OCR-PO inspector (§1.6) shows the full payload — Stage-2 with both engines if Cloud Vision is reachable, Stage-3 with rules + statistical + AI tracks
- Multi-block: if the page has clear sections (heading + body + footnote), `additional_blocks` in the page-OCR response shows them; the OpenCV detector segments by morphological close + contours

### 3.2 — Confidence taxonomy — Phase 4 sub-batch A

**Expected:** `confidence_class` is one of `accepted` (≥0.85), `deficient` (≥0.60), `critical` (<0.60).

### 3.3 — Multi-engine + Stage-3 disagreement collapse — Phase 4 sub-batch C/D

**Expected scenario:** when Gemini and Cloud Vision disagree on a page, `engine_agreement: "divergent"`. If any of the three Stage-3 tracks reports < 0.5, `stage3.divergence_penalty_applied: true` and the final confidence is multiplied by 0.7.

### 3.4 — Stage-3 AI validators (Phase 4 sub-batch G + J)

**Expected:** `stage3.ai.verdicts` contains 2 entries — `openai/gpt-4o` and `google/gemini-2.5-pro`, each with a real `confidence` value and possibly a `correction_note`. If any `error_class` is set, that engine's call failed; the consensus driver downgrades gracefully.

### 3.5 — Homoglyph candidates — Phase 4 sub-batch E + H

**Expected:** when CAMeL morphology is available (it is, post-operator-step-3), `homoglyph_suggestions` lists candidates. Each suggestion has `position`, `original`, `replacement`, `confidence`, `rationale`. Per H-1/H-2 + §2.2 these are NEVER auto-applied — the user must accept each.

---

## 4. Audit + preflight + export (Phase 1 + Phase 3)

### 4.1 — Audit findings + C-01 glossary lookup — Phase 4 sub-batch G

**Step:** with a glossary populated (§2.2), translate a segment, then trigger an audit job from the workspace audit panel.

**Expected:** audit findings page lists violations. C-01 entries with `match: "glossary_lookup"` carry `concept_id`, `canonical_label`, `expected_gloss` in their detection_context.

### 4.2 — Preflight pflichtfragen + religious-formula verifier — Phase 1 + sub-batch I

**Step:** open the export dialog from the workspace.

**Expected:**
- Four Pflichtfragen prompted: page range, block types, layout-feature confirmations
- Confirming each fires a `decision_source=preflight_confirmation` Decision Event
- If any segment has spelled-out `صلى الله عليه وسلم` (not the glyph), the §2.2 verifier raises `CanonRuleViolationsDetected` with `kind: "religious_formula_not_glyph"` — export refuses, no artefact, no EXPORT_EVENT

### 4.3 — Atomic EXPORT_EVENT — Sprint 5

**Expected:** export succeeds → DOCX downloadable from `/exports/artefacts/{po_uuid}`. EXPORT_EVENT-PO contains `revision_snapshot[]` (the H-5 immutable record). `X-Waraq-PDF-X-1a` header on the PDF endpoint shows whether veraPDF validated.

---

## 4a. kraken manuscript / calligraphy OCR (Phase 4 sub-batch kraken)

This is the third reading-line engine per §3.3, for **handwritten or calligraphic** Arabic scans where Gemini-Vision and Cloud Vision DOCUMENT_TEXT_DETECTION reliably fail. Project-flag gated — does NOT run in the default OCR pipeline. The Diagnostics page exposes a direct test surface so you can confirm the adapter works on your manuscript material without first wiring the flag into the workspace UI.

### 4a.1 — Adapter wired without installing kraken

**Step:** open `/diagnostics`, scroll to section 8 (**kraken manuscript OCR**). Upload any image (PNG/JPEG/TIFF), click **Recognise**.

**Expected (when kraken is NOT installed in the venv):** structured error message:
> kraken not installed in this venv. Install via `pip install kraken` and download a recognition model (e.g. `kraken get arabic_best`).

The model path indicator shows the default `arabic_best.mlmodel` (or whatever `KRAKEN_MODEL_PATH` is set to). `available: no`. **This is the canon-honest no-signal state — the adapter is wired but the package isn't installed.** Section 1's `kraken (manuscript OCR)` pill is red, which matches.

### 4a.2 — Activate kraken end-to-end

**Step:**
1. `cd /home/abyahaya/Waraq/Waraq/backend && .venv/bin/pip install kraken`
2. Download a recognition model — for classical Arabic, the OpenITI / kraken-doc convention is:
   ```bash
   cd /home/abyahaya/Waraq/Waraq/backend
   .venv/bin/kraken get arabic_best
   ```
   (Or grab any kraken `.mlmodel` and point `KRAKEN_MODEL_PATH` at it in `backend/.env`.)
3. Restart the backend.
4. Reload `/diagnostics`. The `kraken (manuscript OCR)` pill should now be **green**.
5. Upload a handwritten Arabic page scan (or a calligraphic excerpt) in section 8, click **Recognise**.

**Expected:** RTL-rendered Arabic text panel + numeric `confidence` between 0 and 1 (mean of per-character confidences across all predicted lines). The text quality on a good handwritten scan is the value-add over Gemini/Cloud Vision; on a printed scan, expect noisier output than the other two engines (which is why kraken is gated, not default).

### 4a.3 — Wiring kraken into the multi-engine pipeline

**Today (v1.0):** kraken's eligibility in `engines_for(block_class, *, use_kraken=...)` and `run_engines(..., kraken_fn=..., use_kraken=...)` is structurally present at the function-call boundary. No project-edit UI exists yet to flip the flag per-project; the diagnostics endpoint above is the canonical test surface for v1.0.

**Future (canon-amendment-shaped):** when canon specifies a project-flag schema (e.g. `Project.ocr_use_kraken: bool`), the column plumbs into the existing `use_kraken` kwarg without changing routing-table semantics. **No code-changes-deferred to "make kraken work" — it works today, it's just gated.**

### 4a.4 — What kraken does NOT do

- **Qurʾān blocks:** even with `use_kraken=True`, the QURAN block class stays Gemini-only. Qurʾān script is canonically printed, and kraken's manuscript orientation would degrade rather than help on the Mushaf. Test: in the future workspace path where kraken is enabled per-project, a page mixing Qurʾān + main_text will route only the main_text blocks through kraken.
- **eScriptorium:** the Django web frontend over kraken — explicitly out of scope per the project owner. The human-correction loop is the existing OCR-Review UI.
- **Training new models:** kraken's training pipeline (`ketos train …`) is a deployment / curation concern, not a v1.0 application feature. Use the provided `arabic_best` model or any pretrained `.mlmodel`.

**If failing:**
- "kraken not installed" → step 1 in §4a.2
- "kraken recognition model not found at …" → step 2 in §4a.2 (or fix `KRAKEN_MODEL_PATH`)
- "kraken model load failed" → the file at `KRAKEN_MODEL_PATH` exists but isn't a valid model. Re-download.
- HTTP 413 → image larger than 20 MB. Crop or downsample.

---

## 4b. Multi-format upload (Phase 5 sub-batch K-1)

K-1 extends the upload flow from PDF-only to PDF + image formats per canon §2.1. The chunked transport is unchanged — the new code branches at finalize (page count) and at OCR (rasterize).

### 4b.1 — Upload a JPG / PNG / WEBP

**Step:** open a project workspace → click **Upload PDF or image** → pick a `.jpg`, `.png`, or `.webp` file → Upload.

**Expected:**
- Upload succeeds; "Finalized — 1 page materialized" appears
- The new page shows in the workspace pages list
- Workspace SCAN-PO has `format: "jpeg" | "png" | "webp"` (visible via `/diagnostics/segments/{satz_uuid}/ocr-po` if you OCR the page first)

### 4b.2 — Upload a multi-page TIFF (scanned book)

**Step:** upload a `.tif` or `.tiff` file with multiple frames.

**Expected:**
- Number of materialized pages = number of TIFF frames
- Each SCAN-PO has `format: "tiff"` + the correct `page_index_in_source` (1, 2, 3, …)
- Running OCR on page N extracts frame N (not always frame 0)

### 4b.3 — Upload a HEIC (iPhone scan)

**Step:** upload a `.heic` or `.heif` file (an iPhone photo of a book page works).

**Expected:**
- Upload succeeds (HEIC opener is registered at module import via `pillow_heif`)
- 1 page materialized
- SCAN-PO `format: "heic"`
- OCR works — kraken/Gemini/Cloud Vision all receive the PNG re-encoding

### 4b.4 — Upload a misnamed file (`book.pdf` whose body is a JPEG)

**Step:** rename a JPEG to `.pdf` and upload.

**Expected:** finalize succeeds, page is materialized, but SCAN-PO format reads `"jpeg"` not `"pdf"`. **Magic-byte detection wins over filename** — the canonical defense against misnamed uploads.

### 4b.5 — Upload an unsupported format (`.epub`)

**Step:** upload an `.epub` file (K-3 e-book territory, not yet supported).

**Expected:** **HTTP 415 Unsupported Media Type** at finalize. The chunk transport accepts the bytes (it's format-agnostic); validation runs at finalize. Error message: `"Unsupported upload format: suffix='epub', head_bytes_prefix=b'PK\\x03\\x04…'"`.

**If failing:**
- 500 instead of 415 → unsupported error not wrapped in HTTPException
- Upload accepted but no SCAN-PO → format detection silently fell through

---

## 4c. Direct-text document upload (Phase 5 sub-batch K-2)

K-2 extends the upload flow to DOCX/ODT/TXT/XML/HTML — formats whose text is extracted at upload time and written directly to Segments, bypassing the OCR pipeline.

### 4c.1 — Upload a TXT file

**Step:** open a project workspace → click **Upload document or image** → pick a `.txt` file containing several paragraphs separated by blank lines → Upload.

**Expected:**
- Upload succeeds; "Finalized — 1 page materialized" appears
- The page opens with **one Segment per paragraph** already populated (no "Run OCR" needed)
- The page's `ocr_status` is **`go`** (terminal) — no OCR review ceremony
- SCAN-PO `format: "txt"` + `skip_ocr: true` + `paragraph_count: N`

### 4c.2 — Upload a DOCX file

**Step:** upload a `.docx` (Word document) with several paragraphs.

**Expected:** same shape as TXT — one Page, one Block (MAIN_TEXT), one Segment per `python-docx` paragraph. SCAN-PO `format: "docx"` + `skip_ocr: true`.

### 4c.3 — Upload an ODT file

**Step:** upload an `.odt` (LibreOffice / OpenDocument) file.

**Expected:** one Segment per ODF `text:p` element. SCAN-PO `format: "odt"`.

### 4c.4 — Upload XML or HTML

**Step:** upload a `.xml` or `.html` file.

**Expected:**
- **XML**: text nodes extracted (tags stripped), paragraph-split. Order preserved.
- **HTML**: block-level tags (`<p>`, `<div>`, `<li>`, `<h1..6>`) form paragraph boundaries. Inline tags (`<span>`, `<b>`) flow inside the surrounding paragraph. `<script>` / `<style>` / `<head>` content is excluded. HTML entities decoded.

### 4c.5 — Empty document → HTTP 422

**Step:** upload a `.txt` file containing only whitespace (spaces + newlines, no actual text).

**Expected:** **HTTP 422 Unprocessable Entity**, message `"Document at … contains no non-whitespace paragraphs"`. No Page materialized.

### 4c.6 — Malformed XML → HTTP 422

**Step:** upload an `.xml` file with an unclosed tag.

**Expected:** **HTTP 422** with the parse error embedded in the detail message.

### 4c.7 — Try to run OCR on a direct-text page

**Step:** after uploading a `.txt` file (per 4c.1), click "Run OCR" on the resulting page.

**Expected:** the OCR endpoint **refuses** with: `"OCR is not applicable to direct-text format 'txt' — text was extracted at upload time. Open the page directly."` The page already has its Segments populated; there's nothing to OCR.

### 4c.8 — UTF-8 / Arabic text round-trip

**Step:** upload a `.txt` containing Arabic paragraphs.

**Expected:** the Arabic text appears in Segments unchanged (UTF-8 decoded correctly, RTL block direction). The translation pipeline can run on these segments directly (Phase 1 release-gate "Start translation" works).

**If failing:**
- Arabic mojibake (`?????` or wrong characters) → encoding fallback to `errors='replace'` fired on what was actually a Windows-1256 file
- Run OCR succeeds where it should refuse → page_runner direct-text refusal not wired

---

## 4d. E-book upload (Phase 5 sub-batch K-3)

K-3 extends the upload flow to EPUB/MOBI/AZW/AZW3 (direct-text extraction) and DjVu (raster format, OCR pipeline like PDF).

### 4d.1 — Upload an EPUB

**Step:** open a project workspace → click **Upload book, document, or image** → pick a `.epub` file → Upload.

**Expected:**
- Upload succeeds; "Finalized — 1 page materialized" appears
- The page opens with Segments **in spine order** (chapter 1's paragraphs before chapter 2's, etc.)
- Nav/TOC scaffolding is NOT in the segments (the EPUB's auto-generated table of contents is filtered out)
- `ocr_status: go`, SCAN-PO `format: "epub"`, `skip_ocr: true`

### 4d.2 — Upload a MOBI / AZW / AZW3

**Step:** upload a non-DRM `.mobi`, `.azw`, or `.azw3` file.

**Expected:** same shape as EPUB — paragraphs extracted, Segments materialized, no OCR needed. SCAN-PO `format: "mobi"` / `"azw"` / `"azw3"`.

### 4d.3 — Upload a DRM-protected Kindle file

**Step:** upload a `.azw3` purchased from the Kindle store (DRM-protected).

**Expected:** **HTTP 422** with message:
> AZW3 file appears DRM-protected — extraction refused. Remove DRM (legally) before uploading.

No DRM bypass — §7.4 IP-rights honor. The application refuses cleanly rather than producing garbled text.

### 4d.4 — Upload a DjVu (host without djvulibre-bin)

**Step:** upload a `.djvu` file.

**Expected** (current host state): **HTTP 503 Service Unavailable** with message:
> djvused not found on PATH. DjVu uploads need the djvulibre-bin package — install via `apt install djvulibre-bin`.

This is the canon-honest "adapter wired, system bin missing" state. Mirrors the kraken pattern.

### 4d.5 — Activate DjVu support

**Step:**
1. `sudo apt install djvulibre-bin` (gets you `ddjvu`, `djvused`, `djvudump`)
2. Restart the backend
3. Re-upload the same DjVu file

**Expected after install:**
- Upload succeeds — N pages materialized (one per DjVu page, counted via `djvused`)
- SCAN-PO `format: "djvu"`
- **OCR is required** to populate Segments (unlike EPUB/MOBI which extract text directly). DjVu pages go through the standard `Run OCR` flow; `ddjvu` rasterizes each page to PNG and the existing Gemini + Cloud Vision pipeline runs on it.

### 4d.6 — Try to run OCR on an EPUB page

**Step:** after uploading a `.epub` (per 4d.1), click "Run OCR" on the resulting page.

**Expected:** the OCR endpoint **refuses** with: `"OCR is not applicable to direct-text format 'epub' — text was extracted at upload time."` Same refusal as K-2's `txt` case.

### 4d.7 — Arabic-text round-trip

**Step:** upload an EPUB containing classical Arabic text (UTF-8 encoded XHTML).

**Expected:** Arabic Segments appear unchanged, RTL block direction, ready for translation pipeline.

**If failing:**
- EPUB pages but no Segments → nav-only EPUB (no body paragraphs)
- "DRM-protected" error on a non-DRM file → false positive in the DRM sniff; report which file
- DjVu uploads succeed but OCR fails → `pdftoppm` works but `ddjvu` doesn't; check `djvulibre-bin` install

---

## 4e. Archive upload (Phase 5 sub-batch K-4)

K-4 extends the upload flow to ZIP/RAR/CBZ/CBR. Archive entries are extracted, **alphabetized by filename**, and each supported entry is processed through the existing per-format finalize logic. Each resulting Page records BOTH its inner-file provenance (image SHA, paragraph count, etc.) AND its enclosing-archive provenance (`archive_source_path`, `archive_entry_filename`, `archive_entry_index`).

### 4e.1 — Upload a CBZ (comic book ZIP of images)

**Step:** open a project workspace → click **Upload book, document, image, or archive** → pick a `.cbz` file containing several JPGs named `page_01.jpg`, `page_02.jpg`, etc. → Upload.

**Expected:**
- Upload succeeds; N pages materialized (one per image inside the archive)
- Pages appear **in filename-sorted order**, regardless of how the archive was originally built
- Each Page's SCAN-PO has `format: "jpeg"` + `archive_format: "cbz"` + `archive_entry_filename: "page_NN.jpg"` + `archive_entry_index: N`
- Run OCR works on each page just like a directly-uploaded JPG

### 4e.2 — Upload a ZIP with mixed formats

**Step:** upload a `.zip` containing e.g. `01_scan.jpg`, `02_notes.txt`, `03_other.png`.

**Expected:**
- 3 pages materialized in filename-sorted order
- Page 1 (jpg) has `ocr_status: ausstehend` (image needs OCR) — `format: "jpeg"`, `archive_format: "zip"`
- Page 2 (txt) has `ocr_status: go`, Segments already populated with paragraphs from the .txt — `format: "txt"`, `skip_ocr: true`, `archive_format: "zip"`
- Page 3 (png) has `ocr_status: ausstehend` (image needs OCR) — `format: "png"`, `archive_format: "zip"`

### 4e.3 — Upload a RAR / CBR (host without unrar)

**Step:** upload a `.rar` or `.cbr` file.

**Expected** (current host state): **HTTP 503 Service Unavailable** with message:
> unrar not found on PATH. RAR/CBR uploads need the `unrar` system binary — install via `apt install unrar`.

Mirrors the DjVu pattern. Adapter wired; system bin activates.

### 4e.4 — Activate RAR/CBR support

**Step:**
1. `sudo apt install unrar`
2. Restart the backend
3. Re-upload the same RAR file

**Expected after install:** archive processes identically to ZIP — entries extracted, filename-sorted, recursed into. SCAN-PO `archive_format: "rar"` or `"cbr"`.

### 4e.5 — Upload an empty or junk archive

**Step:** upload a ZIP containing only `.exe` / `.dll` / `Thumbs.db` files (no supported formats).

**Expected:** **HTTP 422** with message:
> Archive '<name>' contains no supported entries (supported formats are PDF, images, documents, e-books — nested archives are not recursed).

### 4e.6 — Upload a corrupted archive

**Step:** upload a file named `.zip` whose content isn't actually a ZIP.

**Expected:** **HTTP 422** with `"Could not open ZIP <name>"` and the underlying error.

### 4e.7 — Noise filtering (macOS resource forks)

**Step:** upload a CBZ created on macOS — it'll contain `__MACOSX/*` resource-fork entries alongside the real pages.

**Expected:** only the real pages materialize as Pages. `__MACOSX`, `._*`, and `Thumbs.db` entries are silently filtered.

### 4e.8 — Nested archives are NOT recursed

**Step:** upload a ZIP containing another ZIP inside it.

**Expected:** the nested ZIP is **silently skipped** (canon §2.1 says "recurse into supported formats"; archive-of-archive is silent). The user gets a clear "no supported entries" 422 if the nested archive was the only thing inside, or just the non-archive entries if there were other supported files.

### 4e.9 — Filename-sort verification

**Step:** upload a CBZ where the entries are stored in reverse order (e.g. `page_05.jpg` first, then `page_01.jpg`).

**Expected:** Pages still materialize in filename-sorted order (`page_01.jpg` is page 1, `page_05.jpg` is page 5). The canon "filename-sort" requirement is honored regardless of archive internal ordering.

**If failing:**
- Pages in archive-order rather than filename-order → sort not applied
- HTTP 500 on RAR → router didn't catch UnrarToolsMissing
- Archive provenance missing on SCAN-PO → `_ArchiveContext` not threaded through `_finalize_binary` / `_finalize_direct_text`

---

## 4f. Cross-cutting upload checks (Phase 5 sub-batch K-5)

K-5 closes the K theme. Three canon rows working together to warn the user about pathological uploads — without blocking them (except the hard 2 GB cap).

### 4f.1 — 2 GB hard cap (canon §2.1 row 5)

**Step:** in the upload dialog, pick a file larger than 2 GB (or try declaring `total_size_bytes > 2 GB` via the API).

**Expected:**
- Frontend: **Upload button disabled**, red banner inline: "File exceeds 2 GB limit. Canon §2.1 caps uploads at 2 GB."
- Direct API call (e.g. via curl with declared `total_size_bytes = 3_000_000_000`): **HTTP 413** with detail "Upload size N bytes exceeds the 2147483648-byte (canon §2.1 2 GB) maximum."
- The defensive cap also fires if a client lied about the declared size and tries to push past 2 GB cumulatively across chunks.

### 4f.2 — Filename duplicate warning (canon §2.1 / §2.2 row 6)

**Step:**
1. Upload a file named `scan.jpg` into a project. Wait for finalize.
2. Pick the same filename `scan.jpg` again (any content) in the same project's upload dialog.

**Expected:**
- The dialog shows an **amber banner** when the file is picked (before any bytes upload): "Filename already in this project — N existing page(s) came from an earlier upload with the same filename."
- Lists up to 5 matching page indices.
- **Upload button stays enabled** — the warning is informational; the user can proceed if intentional.
- Upload proceeds normally on click; pages materialize alongside the existing ones.

### 4f.3 — Content (SHA-256) duplicate warning (canon §2.1 / §2.2 row 6)

**Step:** upload the SAME file content (e.g., the same PDF) twice into a project. The second upload uses a different filename.

**Expected:**
- The pre-upload filename precheck shows no match (different filename).
- After finalize completes, the success block shows an amber sub-section: "Content already in this project (N matching page(s))". Tells the user that the bytes match a prior page — they can delete the new pages from the workspace if it was an accident.

### 4f.4 — 1-book-at-a-time warning (canon §2.2 row 7)

**Step:**
1. Upload any file into an empty project. Wait for finalize.
2. Pick a different filename for upload into the SAME project.

**Expected:**
- Amber banner: "Project already has pages — Canon §2.2 suggests one book per project. This upload will add pages alongside existing ones."
- Suppressed if the filename also matches (the more-specific filename warning shows instead).
- Upload proceeds on click — warning is informational.

### 4f.5 — Per-project scoping

**Step:** upload `scan.jpg` into Project A. Then create Project B and pick `scan.jpg` in B's upload dialog.

**Expected:**
- **No filename warning** in Project B (the filename match is per-project, no cross-project leakage).
- **No project-has-pages warning** (Project B is empty).

### 4f.6 — Direct API precheck (developer use)

**Step:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/uploads/precheck?project_uuid=$PROJECT&filename=test.jpg"
```

**Expected:** JSON response:
```json
{
  "filename_matches": [...],
  "project_has_existing_pages": true | false
}
```

**If failing:**
- Banner shows but Upload button blocked → 2 GB cap accidentally triggered (file actually under 2 GB? check `file.size`)
- Filename warning doesn't fire → confirm the prior upload's `Job.payload.original_filename` matches exactly (case-sensitive)
- Cross-project leakage → verify the project_uuid is passed correctly and the helper filters Page.project_uuid

---

## 4g. Admin admission gate (Phase 5 sub-batch M)

M ships the simplified §2.3 row 8 — application + admin approval. Tier 0/1/2 + subscription / inactivity-deletion / guest / trash purge (rows 9–13) stay deferred for a later sub-batch. Approved users get full access to all features.

### 4g.1 — Register a non-admin account

**Step:** open `/register`, enter a NEW email (not in `ADMIN_EMAILS`) + password + display name → Create account.

**Expected:**
- Form replaced by an amber panel: **"Application received — your account `<email>` is awaiting administrator approval"**
- No automatic login (no token issued)
- "Back to sign in" link visible
- In the DB, the account exists with `approval_status='pending'`

### 4g.2 — Try to log in as a pending user

**Step:** at `/login`, use the email/password just registered.

**Expected:** **HTTP 403** with the message embedded inline: "Your account is awaiting administrator approval. You will be able to log in once an admin approves your application."

### 4g.3 — Admin registration auto-approves

**Step:** register with an email that IS in `backend/.env`'s `ADMIN_EMAILS` (e.g. `ab@gmail.com` if it's set there).

**Expected:**
- Standard immediate-login flow (token issued, dashboard loads)
- `account.approval_status === "approved"` on `/auth/me`
- `account.is_admin === true`
- "Admissions" nav link visible

### 4g.4 — Admin approves a pending user

**Step:**
1. Log in as the admin
2. Click **Admissions** in the top nav → goes to `/admin/admissions`
3. The pending account from §4g.1 appears in the list with **Approve** + **Reject** buttons
4. Click **Approve**

**Expected:**
- Row disappears from the pending list (it just became approved)
- The applicant can now log in (`/login`) with their original credentials and gets full access

### 4g.5 — Admin rejects with a reason

**Step:** register a fresh pending account → log in as admin → at `/admin/admissions`, click **Reject** → enter `"Spam application"` in the reason field → **Confirm reject**.

**Expected:**
- Row disappears from pending
- When the applicant tries to log in: **HTTP 403** with message: `"Your account registration was rejected. Reason: Spam application"`

### 4g.6 — Non-admin can't see admissions

**Step:** log in as an approved non-admin → check the top nav.

**Expected:**
- No "Admissions" link visible
- Direct navigation to `/admin/admissions` → page renders but `GET /admin/admissions/pending` returns **HTTP 403** ("Admin role required"); the error block surfaces

### 4g.7 — Admin overturns a rejection

**Step:** after §4g.5, the same user is in `rejected` state. Admin re-applies via `/admin/admissions` (the rejected user doesn't appear in "pending" anymore — this would need a UI extension to list rejected users; for now use curl):

```bash
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/admin/admissions/$REJECTED_UUID/approve
```

**Expected:** account flips to `approved`; `rejection_reason` cleared; login now succeeds.

### 4g.8 — Bootstrap rule

**Step:** with an empty database (or a fresh dev environment), register the FIRST account with an email that's in `ADMIN_EMAILS`.

**Expected:** that account is auto-approved immediately even though no other admin exists yet. Without this rule, the first user could never approve themselves and no one else could ever be approved.

**If failing:**
- Pending registration still gets a token → backend not reading `approval_status` correctly; check the `if account.approval_status == APPROVED` branch in `auth_router.py`
- Admin can see admissions but approve does nothing → router 404 (account inactive or UUID typo)
- "Admissions" link never appears → check `/auth/me` returns `is_admin: true` for your email; check `ADMIN_EMAILS` env matches exactly (case-insensitive)

---

## 4h. Project audit dashboard (sub-batch N, out-of-phase)

N adds a per-project audit page that aggregates OCR confidence, engine agreement, translation cross-check, audit findings, and open conflicts into a single "where do I stand?" view. Read-only: decisions still flow through the canonical review surfaces.

### 4h.1 — Open the audit dashboard

**Step:** open a project workspace → click the **Audit** button (new, alongside Upload / Auto-OCR / Translate & export).

**Expected:** `/projects/:projectUuid/audit` loads showing:
- **4 headline stats**: Pages, Segments, Open findings, Open conflicts
- **5 distribution rows**: Page OCR status, OCR confidence, Engine agreement, Translation cross-check, Open audit findings — each as tone-coded chips (green/amber/red)
- **7 filter chips** (Low OCR confidence / Divergent engines / Substantive deviation / Translation ambiguity / Cross-check failed / Open audit finding / Open conflict)
- **Attention list** below — by default shows segments matching ANY filter category

### 4h.2 — Apply a filter

**Step:** click "Low OCR confidence" chip.

**Expected:** the attention list refreshes to only segments with `confidence_class ∈ {deficient, critical}`. Each row shows the class + score in the detail column. "Open page" link deep-links to that page's workspace.

### 4h.3 — Multiple filters (union)

**Step:** click "Low OCR confidence" AND "Substantive deviation" both active.

**Expected:** list shows segments matching EITHER filter (one row per matched filter per segment — a segment with both low confidence AND a substantive cross-check deviation appears twice with different chip colors).

### 4h.4 — Empty project

**Step:** open the audit page of a fresh project with no pages.

**Expected:** all summary numbers = 0; attention list shows "No segments are flagged across all attention categories." italic placeholder.

### 4h.5 — Per-project isolation

**Step:** open project A's audit page (with activity) and project B's (empty).

**Expected:** B's dashboard shows zero counts — no leakage from A. (Verified by backend test as well: `test_per_project_scope_no_leakage`.)

### 4h.6 — Direct API check

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/projects/$PROJECT_UUID/audit/summary"

curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/projects/$PROJECT_UUID/audit/attention?filter=low_confidence&filter=divergent_ocr&limit=50"
```

**Expected:** summary returns the `ProjectAuditSummaryResponse` shape (all distributions as numeric counts); attention returns `{items: [...]}` with each item carrying `(page_index, satz_index, filter_matched, detail)`.

### 4h.7 — Read-only confirmation

**Step:** look for any "Approve" / "Resolve" / "Reject" button on the audit page.

**Expected:** **None visible**. Per the §2.6 scope decision, the audit page is read-only — all decisions happen via the deep-link to the page workspace. If a future sub-batch wires action-taking, this expectation changes.

**If failing:**
- Summary loads but distributions all zero on a populated project → check `summarize_project` join is reaching Page through Block correctly
- Attention list empty even though Befunde exist → confirm Befunde have `aufloesungsstatus='offen'` (resolved ones are excluded by design)
- Deep-link to page workspace 404s → page is inactive; check `page.active = true`
- Audit page shows for non-owner of project → ownership check broke; see `owned_project_or_404`

---

## 4i. OCR auto-run progress + cancel (sub-batch O, out-of-phase)

Replaces the old fire-and-block "Auto-OCR all pages" button. Now: live progress bar, server logs, page-refresh resume, cancel button.

### 4i.1 — Start an auto-run

**Step:** open a project with ≥1 `ausstehend` page → in the workspace sidebar, click **Auto-OCR all pages**.

**Expected:**
- Button is replaced inline by a progress panel showing `Auto-OCR running (0/N)` + a thin blue progress bar
- Server logs (uvicorn stdout) now show `ocr_auto_run.queued` then `ocr_auto_run.page.start` / `.page.done` per page
- Progress bar advances every ~1.5s as the poll picks up the next `processed_count` increment

### 4i.2 — Page refresh during a long run

**Step:** while auto-run is in progress, hit the browser refresh button.

**Expected:**
- Workspace reloads
- Progress panel appears in its previous state — same job_uuid, current page index, processed count
- No state lost; no need to restart

(Mechanism: `OcrAutoRunPanel` calls `GET /ocr/projects/{u}/ocr-jobs/in-flight` on mount and resumes the same job_uuid.)

### 4i.3 — Cancel mid-run

**Step:** during auto-run, click **Cancel** on the progress panel.

**Expected:**
- Button label flips to "Cancelling…" (cooperative — cancel takes effect at the next page boundary, worst case 120s into the current page)
- Server log: `ocr_auto_run.cancel.flagged`
- After current page finishes: panel flips to red "Auto-OCR failed (user_cancelled)" + "New run" button
- Pages already processed before cancel stay persisted (their OCR-POs survive)

### 4i.4 — Per-page timeout

**Step:** (synthetic test) — simulate a hung Gemini call by setting `GOOGLE_AI_API_KEY` to an invalid value while a run is in flight, or just wait if Gemini happens to be slow.

**Expected:** the page eventually times out at 120 s; panel flips to red `Auto-OCR failed (page_timeout)`; server log shows `ocr_auto_run.page.timeout` with the page_index + timeout_s.

### 4i.5 — Already-OCR'd pages are skipped

**Step:** auto-run a project where some pages are already `go`/`go_with_warning`/`no_go` (i.e. not `ausstehend`).

**Expected:**
- The 202 response's `total_pages` reflects only the `ausstehend` snapshot at click time, not the full page count
- The runner skips non-ausstehend pages (logged as skipped); `skipped_count` increments
- Terminal panel says "Auto-OCR complete — N processed, K skipped"

### 4i.6 — Per-page synchronous endpoint (still works)

**Step:** in the workspace, click "Run OCR" for a single page (not the bulk button).

**Expected:** synchronous as before — UI shows a spinner until completion (10–30 s). New: bounded by `PER_PAGE_TIMEOUT_SECONDS=120s`; if Gemini hangs, you get **HTTP 504** instead of an indefinite wait. Server logs `ocr.page.start` / `.page.done` for visibility.

### 4i.7 — Direct API check (developer use)

```bash
# Start auto-run
JOB=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/ocr/projects/$PROJECT/auto-run" | jq -r .ocr_job_uuid)

# Poll status
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/ocr/ocr-jobs/$JOB" | jq .

# Cancel
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/ocr/ocr-jobs/$JOB/cancel" | jq .

# In-flight for the project (mount-time resume)
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/ocr/projects/$PROJECT/ocr-jobs/in-flight" | jq .
```

**If failing:**
- Progress bar stuck at 0/N → BackgroundTask not running; check uvicorn isn't in `--reload` mode mid-restart; check logs for `ocr_auto_run.background.failed`
- Cancel takes >120s → expected; cooperative cancel waits for the current page to finish or time out
- Page refresh loses progress → in-flight endpoint returned null incorrectly; check the Job's `state` (should be PENDING or RUNNING for resume)
- 504 on per-page → Gemini/Cloud Vision actually exceeded 120s; check API key + rate limits

---

## 5. Hadith verification end-to-end (Phase 4 sub-batch I + J)

### 5.1 — Lookup-only Hadith verify

Already covered in §1.7 — paste a satz_uuid, click Verify. Returns mandatory + extended hits + persisted Level-2/3 rows.

### 5.2 — Hadith with sunnah.com lookup

**Pre:** if you ever obtain a `SUNNAH_COM_API_KEY`, set it in `backend/.env` and restart the backend.

**Step:** in the diagnostics page, hadith section — click Verify with a request body that includes:
```json
{ "sunnah_lookup": { "collection": "bukhari", "hadith_number": 1 } }
```
*(This requires hand-editing the request via curl/devtools since the Diagnostics UI only exposes the manual-extended toggle.)*

**Expected:** `mandatory_count` increases by 1 (the sunnah.com hit). `sources_skipped` no longer contains `sunnah_api_key_missing`.

---

## 6. Quality-gate signals (post-test)

After your manual walkthrough, a clean state should look like:

```bash
# Backend regression suite
cd /home/abyahaya/Waraq/Waraq/backend
.venv/bin/python -m pytest tests/ --ignore=tests/e2e -q
# Expected: 1300+ passed, 1 skipped (live-API e2e)

# Frontend type-check + build
cd /home/abyahaya/Waraq/Waraq/frontend
npm run build
# Expected: 0 errors, ~500KB JS bundle gzipped to ~155KB
```

---

## 7. Known limits (canon-deferred — NOT bugs)

| Limit | Why it's OK |
|---|---|
| Sunnah.com P-1 returns `sunnah_api_key_missing` | You don't have an API key yet; the canonical mechanism is wired |
| Dorar.net scraping fallback returns no-retry Class B | Per §3.5 "DOM break = Class B, no retry"; concrete DOM selectors are calibration-deferred |
| Shamela has only 16 texts (Bukhari ingested live; the rest registered) | Per §3.5 canonical floor; broader corpus is curation scope |
| E-1..E-5 extended fetchers return empty hits | Per §4.16.2 Official Live API is post-v1.0 |
| LayoutParser / Real-ESRGAN not installed | Per Phase 4 sub-batch H, OpenCV variants are the v1.0 production path |
| kraken pill red until installed + model downloaded | Adapter wired; activation is per-host. See §4a |
| Frontend is the M4 layer + Diagnostics page only | A proper Phase-5 UI is the next user-decided sprint |

---

## 8. Failure-mode quick reference

| Symptom | Likely cause | Fix |
|---|---|---|
| Diagnostics environment shows ✗ on OPENAI_API_KEY | `backend/.env` not loaded | restart `uvicorn` after `set -a && source .env && set +a` |
| `is_available: false` on morphology DB | CAMeL data missing | `.venv/bin/camel_data -i morphology-db-msa-r13` |
| Tanzil verse lookup `found: false` | AR-Referenzbestand not ingested | `.venv/bin/python scripts/ingest_tanzil_quran.py data/tanzil/quran-uthmani.txt risan-quran-json-mirror-1.0` |
| quranenc translation `found: false` | First sync not run | `.venv/bin/python scripts/sync_quranenc.py both` |
| OCR fails 502 from upstream | Gemini/Cloud Vision rate-limited or auth wrong | check `.env` keys; check Cloud Vision JSON path |
| Hadith verify `mandatory_count: 0` on a known-Hadith segment | Segment text doesn't skeleton-match Bukhari | normal — Bukhari is one collection; many Hadith are in other collections we haven't ingested |

---

**This plan covers every Phase 1–4 ✅ row in CANON_TRACKER.md.** Once you've walked through it and everything reports as expected, the application is verified end-to-end ready for Phase 5.
