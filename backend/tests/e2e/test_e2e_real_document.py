"""M5 — End-to-end real-document integration test.

Walks the full canonical pipeline against a small public-domain
Arabic page (1 page, 5 lines from Surat al-Fatiha — universally
public domain). Uses live APIs:
- Gemini for OCR (free-tier; small budget)
- OpenAI for translation (paid; ~$0.01 per run)

Gated behind `WARAQ_RUN_LIVE_API=1` per the existing live-API
opt-in pattern (tests/ocr/test_ocr_baseline.py). Skipped by default
to avoid burning credits on routine test runs.

Run with:
    WARAQ_RUN_LIVE_API=1 .venv/bin/pytest tests/e2e -v -s

Pipeline stages exercised:
1. Project + Account seeding
2. Upload (start_upload + append_chunk + finalize_upload)
3. SCAN-PO creation per Page
4. OCR (real Gemini call) → Revision + OCR-PO per Segment
5. OCR review → page state GO
6. Release gate → start_translation Decision Event
7. Translation (real OpenAI call) → Revision + TRANSLATION-PO per Segment
8. Preflight → 4 Pflichtfragen-Bestätigungen + evaluate_preflight
9. Export → atomic EXPORT_EVENT + DOCX artefact
10. Download endpoint → rebuilt DOCX from revision_snapshot[]
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import seed_account_uuid
from tests.e2e._make_sample_pdf import make_sample_pdf
from waraq.export import ExportConfig, run_export_job
from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.ocr import run_ocr_job
from waraq.ocr.service import start_ocr_job
from waraq.preflight import (
    PFLICHTFRAGE_COUNT,
    confirm_pflichtfrage,
    evaluate_preflight,
    start_preflight_run,
)
from waraq.release_gate import start_translation
from waraq.schemas import Block, Project, Segment
from waraq.schemas.enums import JobState, OcrStatus
from waraq.translation.service import (
    TranslationContext,
    run_translation_job,
    start_translation_job,
)
from waraq.upload.service import append_chunk, finalize_upload, start_upload

_FIXTURE_DIR = Path(__file__).parent / "fixtures"
_SAMPLE_PDF = _FIXTURE_DIR / "sample_arabic.pdf"
_SAMPLE_PNG = _FIXTURE_DIR / "sample_arabic.png"


def _live_api_enabled() -> bool:
    return (
        bool(os.environ.get("GOOGLE_AI_API_KEY"))
        and bool(os.environ.get("OPENAI_API_KEY"))
        and os.environ.get("WARAQ_RUN_LIVE_API") == "1"
    )


@pytest.fixture(scope="module", autouse=True)
def _ensure_fixture_pdf() -> None:
    if not _SAMPLE_PDF.exists() or not _SAMPLE_PNG.exists():
        make_sample_pdf(_SAMPLE_PDF, _SAMPLE_PNG)


async def _make_openai_translator():
    """Build a minimal OpenAI-backed translator. The Translator type is
    `Callable[[str, TranslationContext], Awaitable[str]]`."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

    async def _translate(source_text: str, context: TranslationContext) -> str:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You translate classical Arabic Islamic texts into German. "
                        "Use Swiss German spelling (ss not ß). Return ONLY the translated text."
                    ),
                },
                {"role": "user", "content": source_text},
            ],
            temperature=0,
        )
        return (resp.choices[0].message.content or "").strip()

    return _translate


@pytest.mark.live_api
@pytest.mark.skipif(
    not _live_api_enabled(),
    reason="Set GOOGLE_AI_API_KEY + OPENAI_API_KEY + WARAQ_RUN_LIVE_API=1 to exercise the real pipeline",
)
@pytest.mark.asyncio
async def test_e2e_real_document_full_pipeline(
    db_session: Any, capsys: pytest.CaptureFixture
) -> None:
    """Programmatic E2E walk-through across all canonical phases."""
    from waraq.db import session as db_session_module

    db_session_module.get_settings.cache_clear()

    # --- Stage 1: account + project ----------------------------------------
    account_uuid = new_uuid()
    await seed_account_uuid(db_session, account_uuid)
    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="E2E Real Document")
    db_session.add(project)
    await db_session.flush()
    print(f"\n[1] project seeded: {project.project_uuid}")

    # --- Stage 2: upload ---------------------------------------------------
    pdf_bytes = _SAMPLE_PDF.read_bytes()
    upload_job = await start_upload(
        session=db_session,
        project=project,
        original_filename="sample_arabic.pdf",
        total_chunks=1,
        total_size_bytes=len(pdf_bytes),
    )
    await append_chunk(
        session=db_session, upload_job=upload_job, chunk_index=0, chunk_data=pdf_bytes
    )
    pages = await finalize_upload(session=db_session, upload_job=upload_job)
    assert len(pages) == 1, f"expected 1 page, got {len(pages)}"
    print(f"[2] upload finalized: {len(pages)} page(s) materialized")

    # --- Stage 3: per-page OCR + segment seeding ---------------------------
    image_bytes = _SAMPLE_PNG.read_bytes()
    segments: list[Segment] = []
    for page in pages:
        block = Block(
            block_uuid=new_uuid(),
            page_uuid=page.page_uuid,
            block_type="main_text",
            block_index=0,
        )
        db_session.add(block)
        await db_session.flush()
        seg = Segment(
            satz_uuid=new_uuid(),
            block_uuid=block.block_uuid,
            satz_index=0,
            lock_flag=LockFlag.NONE,
            text_content="",
        )
        db_session.add(seg)
        await db_session.flush()
        segments.append(seg)

        ocr_job = await start_ocr_job(session=db_session, page=page)
        text = await run_ocr_job(
            session=db_session,
            ocr_job=ocr_job,
            image_bytes=image_bytes,
            mime_type="image/png",
            target_segment=seg,
        )
        print(f"[3] OCR page {page.page_index}: {len(text)} chars: {text[:80]!r}...")
        # Mark page GO so the release gate is happy.
        page.ocr_status = OcrStatus.GO
    await db_session.flush()

    # --- Stage 4: release gate → start translation -------------------------
    de_start = await start_translation(session=db_session, project_uuid=project.project_uuid)
    print(f"[4] uebersetzungsstart DE written: {de_start.decision_event_uuid}")

    # --- Stage 5: translation ---------------------------------------------
    translator = await _make_openai_translator()
    job = await start_translation_job(
        session=db_session,
        project_uuid=project.project_uuid,
        segment_uuids=[s.satz_uuid for s in segments],
    )
    result = await run_translation_job(session=db_session, job=job, translator=translator)
    print(f"[5] translation done: {len(result.chunks)} chunks, {len(result.skipped)} skipped")
    # Refresh segments and dump the German.
    for seg in segments:
        await db_session.refresh(seg)
        print(f"    segment {seg.satz_index}: {seg.text_content!r}")

    # --- Stage 6: preflight -----------------------------------------------
    from tests.preflight._helpers import canonical_pflichtfrage_payload

    pf_run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
    for i in range(1, PFLICHTFRAGE_COUNT + 1):
        key, ans = canonical_pflichtfrage_payload(i)
        await confirm_pflichtfrage(
            session=db_session,
            project_uuid=project.project_uuid,
            preflight_run_uuid=pf_run.job_uuid,
            frage_index=i,
            frage_key=key,
            answer=ans,
        )
    pf_eval = await evaluate_preflight(
        session=db_session, project_uuid=project.project_uuid, preflight_run=pf_run
    )
    print(f"[6] preflight state: {pf_eval.state.value}")
    assert pf_eval.state.value in ("exportierbar", "exportierbar_mit_warnungen")

    # --- Stage 7: export ---------------------------------------------------
    cfg = ExportConfig(
        project_uuid=project.project_uuid,
        account_uuid=account_uuid,
        project_title="E2E Test Document",
        current_export_attempt_id=str(new_uuid()),
        preflight_run=pf_run,
    )
    export_result = await run_export_job(session=db_session, config=cfg)
    print(
        f"[7] export complete: po={export_result.export_event_po.po_uuid} "
        f"sha256={export_result.artefact_sha256[:16]}... "
        f"size={export_result.artefact_size_bytes}B"
    )
    assert export_result.job.state == JobState.COMPLETED.value
    assert export_result.export_event_po.payload["sha256"] == export_result.artefact_sha256

    # --- Stage 8: validate DOCX rebuild from snapshot ---------------------
    import io

    from docx import Document

    from waraq.export.docx_builder import build_translation_docx_from_snapshot

    rev_uuids = [
        __import__("uuid").UUID(s)
        for s in export_result.export_event_po.payload["revision_snapshot"]
    ]
    rebuilt = await build_translation_docx_from_snapshot(
        session=db_session,
        project_uuid=project.project_uuid,
        project_title="E2E Test Document",
        revision_uuids=rev_uuids,
    )
    doc = Document(io.BytesIO(rebuilt.bytes_))
    paragraphs_text = [p.text for p in doc.paragraphs]
    print(f"[8] rebuilt DOCX has {len(paragraphs_text)} paragraphs")
    # The rebuild should contain the OCR'd Arabic text.
    all_text = "\n".join(paragraphs_text)
    assert "بِسْمِ" in all_text or "بسم" in all_text, "rebuilt DOCX missing OCR'd Arabic text"
    print("[9] E2E pipeline complete ✓")
