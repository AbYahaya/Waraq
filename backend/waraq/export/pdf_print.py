"""M5 — PDF print export pipeline.

Per MILESTONES.md M5 scope and Formatvorlagen-Baseline v1.1 §2.1:
the PDF print export converts the canonical DOCX artefact (built from
the EXPORT_EVENT's `revision_snapshot[]`) through:

    DOCX  →  LibreOffice headless  →  PDF (raw)
                                       │
                                       ▼
              Ghostscript -dPDFX  →  PDF/X-1a (print-grade)
                                       │
                                       ▼
                veraPDF (optional)  →  validation report

LibreOffice and Ghostscript are required system packages; veraPDF is
optional (validation-only, doesn't change the artefact). Validation
results are recorded in the response — a non-validating PDF is still
served, with the validation findings in the response payload, so the
user can decide whether to accept it. (Strict-mode rejection is a
post-v1.0 hardening.)

This module is **read-only** with respect to Waraq state — it never
writes a Revision, Decision Event, or PO. The PDF is a transformation
of an existing EXPORT_EVENT artefact.

Implementation note: subprocess invocations are wrapped with timeouts
and cleanup. Temporary files live under a per-call working directory
that's removed on success or failure (atomicity-friendly — no orphan
files on crash).
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
import uuid as _uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, kw_only=True, slots=True)
class PdfPrintResult:
    """The output of the PDF print pipeline."""

    bytes_: bytes
    sha256: str
    size_bytes: int
    is_pdf_x_1a: bool
    """True if the PDF/X-1a Ghostscript pass succeeded. False if the
    artefact is the raw LibreOffice output (post-process skipped or
    failed)."""
    verapdf_validation: dict[str, str | bool] | None = None
    """Populated when veraPDF is available + invoked. Keys:
    `valid` (bool), `summary` (str). None when veraPDF was skipped."""


class PdfPrintError(Exception):
    """Raised when the PDF pipeline cannot produce ANY PDF (LibreOffice
    failure). Ghostscript and veraPDF failures are non-fatal — the raw
    PDF is returned with appropriate flags."""


def _which(name: str) -> str | None:
    """Look up a system binary by name. Returns the resolved absolute
    path or None if not on PATH."""
    return shutil.which(name)


async def _run(
    args: list[str], cwd: Path | None = None, timeout: float = 60.0
) -> tuple[int, bytes, bytes]:
    """Run a subprocess and return (exit_code, stdout, stderr).

    Async-friendly via `asyncio.to_thread` so the event loop stays
    responsive during the LibreOffice call (which can take 5–15s
    cold-start).
    """

    def _sync_run() -> tuple[int, bytes, bytes]:
        proc = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr

    return await asyncio.to_thread(_sync_run)


async def _docx_to_pdf_libreoffice(docx_bytes: bytes, work_dir: Path, soffice_path: str) -> Path:
    """LibreOffice headless: DOCX → PDF.

    Produces `output.pdf` inside `work_dir`. Raises `PdfPrintError`
    on failure (LibreOffice returned non-zero or the expected output
    file is missing).
    """
    docx_path = work_dir / "input.docx"
    docx_path.write_bytes(docx_bytes)

    rc, _stdout, stderr = await _run(
        [
            soffice_path,
            "--headless",
            "--norestore",
            "--nofirststartwizard",
            "--convert-to",
            "pdf",
            "--outdir",
            str(work_dir),
            str(docx_path),
        ],
        cwd=work_dir,
        # LibreOffice cold-start can be slow on first invocation. 90s
        # comfortably covers the cold case.
        timeout=90.0,
    )
    pdf_path = work_dir / "input.pdf"
    if rc != 0 or not pdf_path.exists():
        raise PdfPrintError(
            f"LibreOffice headless conversion failed (rc={rc}): "
            f"{stderr.decode('utf-8', errors='replace')[:500]}"
        )
    return pdf_path


async def _ghostscript_pdf_x_1a(raw_pdf: Path, work_dir: Path, gs_path: str) -> Path | None:
    """Ghostscript: PDF → PDF/X-1a print-grade.

    Returns the path to the converted PDF on success, or None on
    failure (the caller falls back to the raw PDF). Failure is
    intentionally non-fatal — PDF/X-1a strictness is for downstream
    print providers; an unconverted PDF is still useful.
    """
    out_path = work_dir / "output_pdfx.pdf"
    rc, _stdout, _stderr = await _run(
        [
            gs_path,
            "-dPDFX",
            "-dBATCH",
            "-dNOPAUSE",
            "-dQUIET",
            "-sDEVICE=pdfwrite",
            "-sColorConversionStrategy=CMYK",
            "-sProcessColorModel=DeviceCMYK",
            "-dPDFSETTINGS=/prepress",
            "-dCompatibilityLevel=1.3",
            f"-sOutputFile={out_path}",
            str(raw_pdf),
        ],
        cwd=work_dir,
        timeout=60.0,
    )
    if rc != 0 or not out_path.exists():
        return None
    return out_path


async def _verapdf_validate(pdf: Path, work_dir: Path, verapdf_path: str) -> dict[str, str | bool]:
    """veraPDF CLI: validate PDF against the PDF/X-1a profile.

    Returns a small summary dict regardless of validation outcome —
    the artefact is served either way; the result is informational.
    """
    rc, stdout, stderr = await _run(
        [verapdf_path, "--flavour", "1a", "--format", "text", str(pdf)],
        cwd=work_dir,
        timeout=60.0,
    )
    text = (stdout or stderr).decode("utf-8", errors="replace")
    valid = ("PASS" in text) and (rc == 0)
    return {"valid": valid, "summary": text[:1024]}


async def docx_to_pdf_print(
    *,
    docx_bytes: bytes,
    enable_pdf_x_1a: bool = True,
    enable_verapdf: bool = True,
) -> PdfPrintResult:
    """Run the full DOCX → PDF print pipeline.

    Always produces a PDF (LibreOffice path is mandatory). PDF/X-1a
    post-processing and veraPDF validation are best-effort. The
    returned `PdfPrintResult.is_pdf_x_1a` flag indicates whether the
    Ghostscript stage succeeded.

    Args:
        docx_bytes: The source DOCX (as built by
            `build_translation_docx_from_snapshot`).
        enable_pdf_x_1a: When True, attempt the Ghostscript PDF/X-1a
            pass. Skipped if Ghostscript isn't on PATH.
        enable_verapdf: When True, attempt veraPDF validation. Skipped
            if veraPDF isn't on PATH.

    Raises:
        PdfPrintError: when LibreOffice is not available or its
            conversion fails. Ghostscript / veraPDF failures are
            non-fatal.
    """
    soffice = _which("soffice") or _which("libreoffice")
    if soffice is None:
        raise PdfPrintError(
            "LibreOffice headless is required for PDF print export but "
            "no `soffice` / `libreoffice` binary found on PATH. Install "
            "via `apt-get install libreoffice-core libreoffice-writer` "
            "or equivalent."
        )

    with tempfile.TemporaryDirectory(prefix="waraq-pdf-") as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        raw_pdf = await _docx_to_pdf_libreoffice(docx_bytes, tmpdir, soffice)

        final_pdf = raw_pdf
        is_pdf_x_1a = False
        if enable_pdf_x_1a:
            gs = _which("gs")
            if gs is not None:
                converted = await _ghostscript_pdf_x_1a(raw_pdf, tmpdir, gs)
                if converted is not None:
                    final_pdf = converted
                    is_pdf_x_1a = True

        verapdf_result: dict[str, str | bool] | None = None
        if enable_verapdf:
            verapdf = _which("verapdf")
            if verapdf is not None:
                verapdf_result = await _verapdf_validate(final_pdf, tmpdir, verapdf)

        bytes_ = final_pdf.read_bytes()

    import hashlib

    sha = hashlib.sha256(bytes_).hexdigest()
    return PdfPrintResult(
        bytes_=bytes_,
        sha256=sha,
        size_bytes=len(bytes_),
        is_pdf_x_1a=is_pdf_x_1a,
        verapdf_validation=verapdf_result,
    )


# Silence unused-import warning for symbols re-exported via __init__.
_ = _uuid


__all__ = [
    "PdfPrintError",
    "PdfPrintResult",
    "docx_to_pdf_print",
]
