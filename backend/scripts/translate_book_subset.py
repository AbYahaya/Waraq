"""One-shot pipeline driver for the user's Arabic PDF subset.

Mirrors `tests/e2e/test_e2e_real_document.py` but parameterized for an
arbitrary PDF + page count. Saves the resulting DOCX (and PDF if
LibreOffice + Ghostscript are available) to `/tmp`.

Run with:
    cd backend
    set -a && source .env && set +a
    .venv/bin/python scripts/translate_book_subset.py <pdf_path> <n_pages>
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pypdf

from waraq.db.session import _engine, _sessionmaker, get_settings
from waraq.export import ExportConfig, run_export_job
from waraq.export.pdf_print import PdfPrintError, docx_to_pdf_print
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
from waraq.schemas import Account, Block, Page, Project, Segment
from waraq.schemas.enums import OcrStatus
from waraq.translation.openai_translator import make_openai_translator
from waraq.translation.service import (
    run_translation_job,
    start_translation_job,
)
from waraq.translation.persistence import make_translation_persistence_hook


def _extract_pdf_subset(src: Path, n_pages: int, start_page_idx: int) -> Path:
    """Extract `n_pages` pages from `src` starting at `start_page_idx`
    (0-indexed). Returns path to a temp PDF."""
    reader = pypdf.PdfReader(str(src))
    writer = pypdf.PdfWriter()
    end = min(start_page_idx + n_pages, len(reader.pages))
    for i in range(start_page_idx, end):
        writer.add_page(reader.pages[i])
    out = Path(tempfile.mkstemp(prefix="subset_", suffix=".pdf")[1])
    with out.open("wb") as f:
        writer.write(f)
    return out


def _render_page_pngs(pdf_path: Path, out_dir: Path, dpi: int = 200) -> list[Path]:
    """Use poppler's `pdftoppm` to render each page to PNG in `out_dir`.
    Returns the list of generated PNG paths in page order."""
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / "page"
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(prefix)],
        check=True,
    )
    return sorted(out_dir.glob("page-*.png"))


async def _seed_account(session) -> tuple[Account, Project]:
    account = Account(
        account_uuid=new_uuid(),
        email=f"book-smoke-{new_uuid()}@waraq.test",
        password_hash="x",
        active=True,
    )
    session.add(account)
    await session.flush()
    project = Project(
        project_uuid=new_uuid(),
        account_uuid=account.account_uuid,
        name="Book subset smoke",
    )
    session.add(project)
    await session.flush()
    return account, project


async def main(pdf_path: str, n_pages: int = 3, start_page: int = 30) -> None:
    src = Path(pdf_path).resolve()
    if not src.exists():
        print(f"PDF not found: {src}")
        sys.exit(1)
    print(f"\n[input] {src.name} → extracting {n_pages} pages starting at index {start_page}")
    subset_pdf = _extract_pdf_subset(src, n_pages, start_page)
    print(f"[input] subset → {subset_pdf} ({subset_pdf.stat().st_size} bytes)")

    work_dir = Path(tempfile.mkdtemp(prefix="waraq-book-"))
    page_pngs = _render_page_pngs(subset_pdf, work_dir / "pngs")
    print(f"[input] rendered {len(page_pngs)} page PNG(s) at 200 dpi")

    # Cache-clear so the script picks up env values from the shell.
    get_settings.cache_clear()
    _engine.cache_clear()
    _sessionmaker.cache_clear()
    sm = _sessionmaker()

    async with sm() as session, session.begin():
        # --- Stage 1: account + project ----------------------------------
        account, project = await _seed_account(session)
        print(f"[1] project seeded: {project.project_uuid}")

        # --- Stage 2: skip chunked upload, materialize pages directly ---
        # We don't need the SCAN-PO chain or the PDF-stored bytes for a
        # smoke-quality run; the OCR pass + downstream provenance is what
        # matters for the artefact.
        pages: list[Page] = []
        for idx, _png in enumerate(page_pngs, start=1):
            page = Page(page_uuid=new_uuid(), project_uuid=project.project_uuid, page_index=idx)
            session.add(page)
            await session.flush()
            pages.append(page)
        print(f"[2] {len(pages)} page(s) materialized")

        # --- Stage 3: per-page OCR + segment seeding ---------------------
        segments: list[Segment] = []
        for page, png_path in zip(pages, page_pngs):
            block = Block(
                block_uuid=new_uuid(),
                page_uuid=page.page_uuid,
                block_type="main_text",
                block_index=0,
            )
            session.add(block)
            await session.flush()
            seg = Segment(
                satz_uuid=new_uuid(),
                block_uuid=block.block_uuid,
                satz_index=0,
                lock_flag=LockFlag.NONE,
                text_content="",
            )
            session.add(seg)
            await session.flush()
            segments.append(seg)

            ocr_job = await start_ocr_job(session=session, page=page)
            text = await run_ocr_job(
                session=session,
                ocr_job=ocr_job,
                image_bytes=png_path.read_bytes(),
                mime_type="image/png",
                target_segment=seg,
            )
            print(
                f"[3] OCR p{page.page_index}: {len(text)} chars: {text[:80]!r}…"
            )
            page.ocr_status = OcrStatus.GO
        await session.flush()

        # --- Stage 4: release gate → start_translation -------------------
        de_start = await start_translation(
            session=session, project_uuid=project.project_uuid
        )
        print(f"[4] uebersetzungsstart DE: {de_start.decision_event_uuid}")

        # --- Stage 5: translation ----------------------------------------
        translator = make_openai_translator()
        job = await start_translation_job(
            session=session,
            project_uuid=project.project_uuid,
            segment_uuids=[s.satz_uuid for s in segments],
        )
        hook = make_translation_persistence_hook(engine_identifier="openai/gpt-4o-mini")
        result = await run_translation_job(
            session=session, job=job, translator=translator, on_segment_translated=hook
        )
        print(
            f"[5] translation done: {len(result.chunks)} chunk(s), "
            f"{len(result.skipped)} skipped"
        )
        for seg in segments:
            await session.refresh(seg)

        # --- Stage 6: preflight ------------------------------------------
        pf_run = await start_preflight_run(
            session=session, project_uuid=project.project_uuid
        )
        for i in range(1, PFLICHTFRAGE_COUNT + 1):
            await confirm_pflichtfrage(
                session=session,
                project_uuid=project.project_uuid,
                preflight_run_uuid=pf_run.job_uuid,
                frage_index=i,
                frage_key=f"frage_{i}",
                answer={"value": "yes"},
            )
        pf_eval = await evaluate_preflight(
            session=session, project_uuid=project.project_uuid, preflight_run=pf_run
        )
        print(f"[6] preflight state: {pf_eval.state.value}")

        # --- Stage 7: export ---------------------------------------------
        cfg = ExportConfig(
            project_uuid=project.project_uuid,
            account_uuid=account.account_uuid,
            project_title=src.stem[:80],
            current_export_attempt_id=str(new_uuid()),
            preflight_run=pf_run,
        )
        export_result = await run_export_job(session=session, config=cfg)
        print(
            f"[7] export ✓  PO={export_result.export_event_po.po_uuid} "
            f"sha256={export_result.artefact_sha256[:16]}… "
            f"size={export_result.artefact_size_bytes}B"
        )

        # --- Stage 8: rebuild DOCX from snapshot, save to /tmp ----------
        from waraq.export.docx_builder import build_translation_docx_from_snapshot

        rev_uuids = [
            __import__("uuid").UUID(s)
            for s in export_result.export_event_po.payload["revision_snapshot"]
        ]
        rebuilt = await build_translation_docx_from_snapshot(
            session=session,
            project_uuid=project.project_uuid,
            project_title=src.stem[:80],
            revision_uuids=rev_uuids,
        )
        out_docx = Path("/tmp/waraq_book_output.docx")
        out_docx.write_bytes(rebuilt.bytes_)
        print(f"[8] DOCX → {out_docx} ({out_docx.stat().st_size} bytes)")

        # --- Stage 9: PDF (best-effort, requires LibreOffice + gs) ------
        try:
            pdf_result = await docx_to_pdf_print(docx_bytes=rebuilt.bytes_)
            out_pdf = Path("/tmp/waraq_book_output.pdf")
            out_pdf.write_bytes(pdf_result.bytes_)
            print(
                f"[9] PDF  → {out_pdf} ({out_pdf.stat().st_size} bytes) "
                f"PDF/X-1a={pdf_result.is_pdf_x_1a}"
            )
        except PdfPrintError as exc:
            print(f"[9] PDF skipped: {exc}")

        print("\n--- segment outputs ---")
        for seg in segments:
            print(f"\n  [satz {seg.satz_index}]")
            print(f"  text: {seg.text_content[:300]!r}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: translate_book_subset.py <pdf_path> [n_pages] [start_page]")
        sys.exit(1)
    pdf = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    start = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set; source backend/.env first.")
        sys.exit(1)
    if not os.environ.get("GOOGLE_AI_API_KEY"):
        print("GOOGLE_AI_API_KEY not set; source backend/.env first.")
        sys.exit(1)
    asyncio.run(main(pdf, n_pages=n, start_page=start))
