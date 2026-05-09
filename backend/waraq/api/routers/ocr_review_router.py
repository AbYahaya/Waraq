"""OCR Review endpoints.

State machine per Sprint 1 §2 / T-4.3.1:
    ausstehend → in_review → go | go_with_warning | no_go

Endpoints:
- POST /pages/{page_uuid}/ocr-review/enter      — enter in_review
- POST /pages/{page_uuid}/ocr-review/findings   — record + apply findings
- POST /pages/{page_uuid}/ocr-review/resolve-no-go — explicit no_go → go
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from waraq.api._ownership import owned_page_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import (
    OcrApplyFindingsRequest,
    OcrPageStatusResponse,
    OcrResolveNoGoRequest,
)
from waraq.ocr.error_classes import OcrErrorClass
from waraq.ocr.review import (
    apply_findings_to_status,
    enter_in_review,
    make_default_severity_weights,
    record_ocr_error_instance,
    resolve_no_go_to_go,
)
from waraq.schemas import OcrErrorInstance
from waraq.schemas.enums import OcrErrorState

router = APIRouter(prefix="/pages/{page_uuid}/ocr-review", tags=["ocr-review"])


async def _open_codes(session, page_uuid: _uuid.UUID) -> list[str]:  # type: ignore[no-untyped-def]
    result = await session.execute(
        select(OcrErrorInstance.error_code)
        .where(OcrErrorInstance.page_uuid == page_uuid)
        .where(OcrErrorInstance.state == OcrErrorState.OFFEN.value)
    )
    return list(result.scalars())


@router.post("/enter", response_model=OcrPageStatusResponse, status_code=status.HTTP_200_OK)
async def enter(
    page_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> OcrPageStatusResponse:
    page = await owned_page_or_404(session, page_uuid, current.account_uuid)
    await enter_in_review(session=session, page=page)
    return OcrPageStatusResponse(
        page_uuid=page.page_uuid,
        ocr_status=page.ocr_status.value,
        error_codes_open=await _open_codes(session, page_uuid),
    )


@router.post("/findings", response_model=OcrPageStatusResponse)
async def post_findings(
    page_uuid: _uuid.UUID,
    req: OcrApplyFindingsRequest,
    session: DbSession,
    current: CurrentAccount,
) -> OcrPageStatusResponse:
    """Record `ocr_error_instance` rows and apply the aggregator. Page must
    already be `in_review`; call `/enter` first."""
    page = await owned_page_or_404(session, page_uuid, current.account_uuid)
    for f in req.findings:
        await record_ocr_error_instance(
            session=session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass(f.error_code),
            block_uuid=f.block_uuid,
            details=f.details,
        )
    try:
        await apply_findings_to_status(
            session=session,
            page=page,
            weights=make_default_severity_weights(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return OcrPageStatusResponse(
        page_uuid=page.page_uuid,
        ocr_status=page.ocr_status.value,
        error_codes_open=await _open_codes(session, page_uuid),
    )


@router.post("/resolve-no-go", response_model=OcrPageStatusResponse)
async def resolve_no_go(
    page_uuid: _uuid.UUID,
    req: OcrResolveNoGoRequest,
    session: DbSession,
    current: CurrentAccount,
) -> OcrPageStatusResponse:
    page = await owned_page_or_404(session, page_uuid, current.account_uuid)
    try:
        await resolve_no_go_to_go(
            session=session,
            page=page,
            actor_uuid=current.account_uuid,
            content={"note": req.note} if req.note else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return OcrPageStatusResponse(
        page_uuid=page.page_uuid,
        ocr_status=page.ocr_status.value,
        error_codes_open=await _open_codes(session, page_uuid),
    )
