"""M5 — Translation-export download endpoints.

Mirrors `ocr_export_router.py`'s download pattern. Per the
2026-05-04 + 2026-05-06 EXPORT_EVENT addressing decisions, the
EXPORT_EVENT-PO carries artefact identity (filename, sha256,
size_bytes) and the snapshot arrays in payload — but NOT the bytes.

The download endpoints **rebuild the DOCX on demand** from the
`revision_snapshot[]` UUIDs in the PO payload. This uses the
immutable `Revision.after_text` (per H-5) so the rebuild captures the
exact text state at export time.

Endpoints:
- `GET /exports/artefacts/{po_uuid}`     — DOCX bytes (rebuilt).
- `GET /exports/artefacts/{po_uuid}/pdf` — PDF print-grade artefact
   (DOCX → LibreOffice → Ghostscript PDF/X-1a → veraPDF validate).
   Requires `libreoffice` + `gs` on the host (in the Fly Docker image
   when present); veraPDF validation is best-effort.

Both are deliberate v1.0 simplifications consistent with OCR-export's
download path. Post-v1.0 work moves bytes to durable content-addressed
storage; the EXPORT_EVENT row schema does not change.
"""

from __future__ import annotations

import io
import uuid as _uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from waraq.api._ownership import owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.export import ExportConfig, run_export_job
from waraq.export.docx_builder import (
    build_translation_docx_from_snapshot,
    docx_config_from_export_payload,
)
from waraq.export.exceptions import (
    CanonRuleViolationsDetected,
    ExportNotInExportableState,
    PreflightStateChanged,
)
from waraq.export.pdf_print import PdfPrintError, docx_to_pdf_print
from waraq.identity import new_uuid
from waraq.preflight import PdfFormatChoice
from waraq.preflight.service import JOB_TYPE as PREFLIGHT_JOB_TYPE
from waraq.schemas import Job, ProvenanceObject
from waraq.schemas.enums import POType, ScopeType

router = APIRouter(tags=["export"])


async def _resolve_export_event_po(
    session: DbSession, po_uuid: _uuid.UUID, account_uuid: _uuid.UUID
) -> ProvenanceObject:
    """Look up an EXPORT_EVENT-PO + verify ownership.

    Shared by the DOCX and PDF endpoints. Refuses non-EXPORT_EVENT POs
    (OCR_EXPORT_EVENT uses a different download path) and any PO whose
    project the caller doesn't own.
    """
    po: ProvenanceObject | None = await session.get(ProvenanceObject, po_uuid)
    if po is None or po.po_type != POType.EXPORT_EVENT.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artefact not found")
    if po.scope_type != ScopeType.PROJECT.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artefact not found")
    await owned_project_or_404(session, po.scope_uuid, account_uuid)
    return po


async def _rebuild_docx_for_po(*, session: DbSession, po: ProvenanceObject) -> tuple[bytes, str]:
    """Rebuild DOCX bytes from an EXPORT_EVENT-PO + return them with
    the canonical filename stem (no extension)."""
    payload = po.payload or {}
    snapshot = payload.get("revision_snapshot") or []
    if not isinstance(snapshot, list):
        snapshot = []
    rev_uuids = [_uuid.UUID(s) for s in snapshot if isinstance(s, str)]

    project_title = str(payload.get("project_title") or "Waraq Export")
    docx_config = docx_config_from_export_payload(payload)
    artefact = await build_translation_docx_from_snapshot(
        session=session,
        project_uuid=po.scope_uuid,
        project_title=project_title,
        revision_uuids=rev_uuids,
        config=docx_config,
    )
    raw_filename = str(payload.get("filename") or f"export_{po.po_uuid}.docx")
    stem = raw_filename.rsplit(".", 1)[0]
    return artefact.bytes_, stem


class ExportRunRequest(BaseModel):
    project_uuid: _uuid.UUID
    project_title: str = Field(min_length=1, max_length=512)
    preflight_run_uuid: _uuid.UUID


class ExportRunResponse(BaseModel):
    job_uuid: _uuid.UUID
    job_state: str
    export_event_po_uuid: _uuid.UUID
    artefact_uuid: _uuid.UUID
    artefact_sha256: str
    artefact_size_bytes: int
    gate_mode: str
    n_segments_exported: int


@router.post(
    "/projects/{project_uuid}/exports",
    response_model=ExportRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_translation_export(
    project_uuid: _uuid.UUID,
    req: ExportRunRequest,
    session: DbSession,
    current: CurrentAccount,
) -> ExportRunResponse:
    """Trigger one translation-export attempt synchronously.

    Re-checks preflight at job start (per Sprint 5 §2 R-S5-04). Builds
    the DOCX, then atomically commits artefact + EXPORT_EVENT-PO + job
    completion. Returns the new PO UUID — the UI then GETs
    `/exports/artefacts/{po_uuid}` (DOCX) or `/pdf` for download.
    """
    if req.project_uuid != project_uuid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_uuid in path and body must match",
        )
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    preflight_job: Job | None = await session.get(Job, req.preflight_run_uuid)
    if (
        preflight_job is None
        or preflight_job.job_type != PREFLIGHT_JOB_TYPE
        or preflight_job.project_uuid != project_uuid
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preflight run not found")

    cfg = ExportConfig(
        project_uuid=project_uuid,
        account_uuid=current.account_uuid,
        project_title=req.project_title,
        current_export_attempt_id=str(new_uuid()),
        preflight_run=preflight_job,
        actor_uuid=current.account_uuid,
    )
    try:
        result = await run_export_job(session=session, config=cfg)
    except (ExportNotInExportableState, PreflightStateChanged) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CanonRuleViolationsDetected as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "reason": "canon_rule_violations",
                "message": str(exc),
                "violations": [
                    {"satz_uuid": str(v.satz_uuid), "kind": v.kind.value} for v in exc.violations
                ],
            },
        ) from exc

    return ExportRunResponse(
        job_uuid=result.job.job_uuid,
        job_state=result.job.state,
        export_event_po_uuid=result.export_event_po.po_uuid,
        artefact_uuid=result.artefact_uuid,
        artefact_sha256=result.artefact_sha256,
        artefact_size_bytes=result.artefact_size_bytes,
        gate_mode=result.gate_mode.value,
        n_segments_exported=len(result.revision_snapshot),
    )


@router.get("/exports/artefacts/{po_uuid}")
async def download_translation_artefact(
    po_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> StreamingResponse:
    """Stream the DOCX bytes of an EXPORT_EVENT-PO."""
    po = await _resolve_export_event_po(session, po_uuid, current.account_uuid)
    docx_bytes, stem = await _rebuild_docx_for_po(session=session, po=po)
    filename = f"{stem}.docx"
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type=("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/exports/artefacts/{po_uuid}/pdf")
async def download_translation_artefact_pdf(
    po_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
    format: PdfFormatChoice | None = None,
) -> StreamingResponse:
    """Stream a PDF artefact for the EXPORT_EVENT-PO.

    Per §4.7.2 there are two canonical PDF format choices:

      - `print_pdf_x_1a` (default): DOCX → LibreOffice → Ghostscript
        PDF/X-1a (CMYK, prepress, best-effort) → veraPDF validate.
      - `digital_rgb`:              DOCX → LibreOffice. RGB output,
        no Ghostscript pass, no veraPDF (digital distribution path).

    Returns 503 if LibreOffice is not installed on the host.

    The X-Waraq headers expose pipeline-stage outcomes:
    - `X-Waraq-PDF-Format: digital_rgb|print_pdf_x_1a` — chosen format.
    - `X-Waraq-PDF-X-1a: true|false` — whether the Ghostscript pass succeeded.
      Always `false` for `digital_rgb`.
    - `X-Waraq-veraPDF-Valid: true|false|skipped` — veraPDF result.
      `skipped` for `digital_rgb`.
    """
    po = await _resolve_export_event_po(session, po_uuid, current.account_uuid)
    docx_bytes, stem = await _rebuild_docx_for_po(session=session, po=po)

    payload = po.payload or {}
    export_config = payload.get("export_config") if isinstance(payload, dict) else None
    stored_choice = None
    if isinstance(export_config, dict):
        raw_choice = export_config.get("pdf_format_choice")
        if isinstance(raw_choice, str):
            try:
                stored_choice = PdfFormatChoice(raw_choice)
            except ValueError:
                stored_choice = None
    effective_format = format or stored_choice or PdfFormatChoice.PRINT_PDF_X_1A
    is_digital = effective_format == PdfFormatChoice.DIGITAL_RGB
    try:
        result = await docx_to_pdf_print(
            docx_bytes=docx_bytes,
            enable_pdf_x_1a=not is_digital,
            enable_verapdf=not is_digital,
        )
    except PdfPrintError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"PDF pipeline unavailable: {exc}",
        ) from exc

    headers = {
        "Content-Disposition": f'attachment; filename="{stem}.pdf"',
        "X-Waraq-PDF-Format": effective_format.value,
        "X-Waraq-PDF-X-1a": "true" if result.is_pdf_x_1a else "false",
        "X-Waraq-veraPDF-Valid": (
            ("true" if result.verapdf_validation["valid"] else "false")
            if result.verapdf_validation is not None
            else "skipped"
        ),
    }
    return StreamingResponse(
        io.BytesIO(result.bytes_),
        media_type="application/pdf",
        headers=headers,
    )
