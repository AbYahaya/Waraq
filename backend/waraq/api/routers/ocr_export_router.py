"""OCR-text export endpoints.

Flow:
1. POST /projects/{project_uuid}/ocr-export/gate  — pure check, no log/DE
2. POST /projects/{project_uuid}/ocr-export/confirm — Pflichtfragen DE
3. POST /projects/{project_uuid}/ocr-export/run    — gate-recheck → Job → DOCX → OCR_EXPORT_EVENT
4. GET  /ocr-export/artefacts/{po_uuid}            — download DOCX bytes
"""

from __future__ import annotations

import io
import uuid as _uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from waraq.api._ownership import owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import (
    OcrExportConfirmRequest,
    OcrExportGateResponse,
    OcrExportPflichtfragenInput,
    OcrExportRunResponse,
)
from waraq.notifications.events import notify_project_event, project_workspace_url
from waraq.ocr_export import (
    DocxArtefactFailed,
    GateMode,
    OcrExportBlocked,
    OcrExportConfig,
    OcrExportPflichtfragenMissing,
    Pflichtfragen,
    check_ocr_export_gate,
    confirm_pflichtfragen,
    run_ocr_export,
)
from waraq.schemas import ProvenanceObject
from waraq.schemas.enums import POType, ScopeType

router = APIRouter(tags=["ocr-export"])


def _config_from_input(
    *,
    project_uuid: _uuid.UUID,
    actor_uuid: _uuid.UUID,
    pflichtfragen_in: OcrExportPflichtfragenInput,
    export_attempt_id: str = "",
) -> OcrExportConfig:
    return OcrExportConfig(
        project_uuid=project_uuid,
        pflichtfragen=Pflichtfragen(
            page_range=list(pflichtfragen_in.page_range),
            block_types_enabled=list(pflichtfragen_in.block_types_enabled),
            markings_enabled=pflichtfragen_in.markings_enabled,
            mode=GateMode(pflichtfragen_in.mode),
        ),
        actor_uuid=actor_uuid,
        export_attempt_id=export_attempt_id,
    )


@router.post("/projects/{project_uuid}/ocr-export/gate", response_model=OcrExportGateResponse)
async def gate(
    project_uuid: _uuid.UUID,
    pflichtfragen_in: OcrExportPflichtfragenInput,
    session: DbSession,
    current: CurrentAccount,
) -> OcrExportGateResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    config = _config_from_input(
        project_uuid=project_uuid,
        actor_uuid=current.account_uuid,
        pflichtfragen_in=pflichtfragen_in,
    )
    result = await check_ocr_export_gate(session=session, config=config)
    return OcrExportGateResponse(
        state=result.state.value,
        blocking_reasons=list(result.blocking_reasons),
        warnings=list(result.warnings),
    )


@router.post(
    "/projects/{project_uuid}/ocr-export/confirm",
    status_code=status.HTTP_201_CREATED,
)
async def confirm(
    project_uuid: _uuid.UUID,
    req: OcrExportConfirmRequest,
    session: DbSession,
    current: CurrentAccount,
) -> dict[str, str]:
    await owned_project_or_404(session, project_uuid, current.account_uuid)
    config = _config_from_input(
        project_uuid=project_uuid,
        actor_uuid=current.account_uuid,
        pflichtfragen_in=req.pflichtfragen,
        export_attempt_id=req.export_attempt_id,
    )
    try:
        de = await confirm_pflichtfragen(session=session, config=config)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"decision_event_uuid": str(de.decision_event_uuid)}


@router.post(
    "/projects/{project_uuid}/ocr-export/run",
    response_model=OcrExportRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run(
    project_uuid: _uuid.UUID,
    req: OcrExportConfirmRequest,
    session: DbSession,
    current: CurrentAccount,
) -> OcrExportRunResponse:
    project = await owned_project_or_404(session, project_uuid, current.account_uuid)
    config = _config_from_input(
        project_uuid=project_uuid,
        actor_uuid=current.account_uuid,
        pflichtfragen_in=req.pflichtfragen,
        export_attempt_id=req.export_attempt_id,
    )
    try:
        job, artefact, po = await run_ocr_export(session=session, config=config)
    except OcrExportBlocked as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OcrExportPflichtfragenMissing as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DocxArtefactFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DOCX build failed: {exc!s}",
        ) from exc
    await notify_project_event(
        session=session,
        project=project,
        kind="ocr_export_completed",
        severity="success",
        title=f"OCR export ready — {project.name}",
        body=f"Exported {artefact.n_pages_exported} page(s) and {artefact.n_segments_exported} segment(s).",
        target_url=project_workspace_url(project.project_uuid),
        action_label="Open project",
    )
    return OcrExportRunResponse(
        job_uuid=job.job_uuid,
        job_state=job.state,
        artefact_uuid=artefact.artefact_uuid,
        sha256=artefact.sha256,
        size_bytes=artefact.size_bytes,
        ocr_export_event_po_uuid=po.po_uuid,
        n_segments_exported=artefact.n_segments_exported,
        n_pages_exported=artefact.n_pages_exported,
    )


@router.get("/ocr-export/artefacts/{po_uuid}")
async def download_artefact(
    po_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> StreamingResponse:
    """Stream the DOCX bytes of an OCR_EXPORT_EVENT-PO.

    Note: the artefact bytes themselves are not stored on the PO row in
    v1.0 — only the sha256/identity are. For M4 we re-build the DOCX
    on demand from the PO payload (page_range etc.) so the UI can
    download. This is a deliberate v1.0 simplification; M5 will move
    bytes to durable storage with a content-addressed file path.
    """
    po: ProvenanceObject | None = await session.get(ProvenanceObject, po_uuid)
    if po is None or po.po_type != POType.OCR_EXPORT_EVENT.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artefact not found")
    if po.scope_type != ScopeType.PROJECT.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artefact not found")
    await owned_project_or_404(session, po.scope_uuid, current.account_uuid)

    # Re-build DOCX on demand from the original Pflichtfragen captured
    # in the PO payload.
    from waraq.ocr_export import build_ocr_docx

    payload = po.payload or {}
    page_range = list(payload.get("page_range", []))
    block_types_enabled = list(
        payload.get("block_types_enabled", payload.get("block_types_present", []))
    )
    markings_enabled = bool(payload.get("markings_enabled", False))
    mode = str(payload.get("mode", "arbeitsstand"))
    artefact = await build_ocr_docx(
        session=session,
        project_uuid=po.scope_uuid,
        page_range=page_range,
        block_types_enabled=block_types_enabled,
        markings_enabled=markings_enabled,
        mode=mode,
        warnings=list(payload.get("export_warnings", [])),
    )
    filename = str(payload.get("filename") or f"ocr_export_{po_uuid}.docx")
    return StreamingResponse(
        io.BytesIO(artefact.bytes_),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
