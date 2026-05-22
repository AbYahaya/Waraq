"""Current-account profile, security, and usage endpoints."""

from __future__ import annotations

import uuid as _uuid
from collections import Counter, defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from waraq.admission import is_admin_email
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.auth.passwords import hash_password, verify_password
from waraq.schemas import Account, Block, Job, Page, Project, ProvenanceObject, Segment
from waraq.schemas.enums import JobState, OcrStatus, POType, ScopeType

router = APIRouter(prefix="/me", tags=["account"])


class AccountProfileResponse(BaseModel):
    account_uuid: _uuid.UUID
    email: str
    display_name: str | None
    active: bool
    approval_status: str
    is_admin: bool


class AccountProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=8, max_length=512)


class GeneralUsageResponse(BaseModel):
    projects: int
    active_projects: int
    uploaded_books: int
    pages: int
    ocr_pages: int
    translated_pages: int
    segments: int
    translated_segments: int
    storage_bytes: int


class ProviderUsageResponse(BaseModel):
    provider_calls: dict[str, int]
    jobs_by_type: dict[str, int]
    jobs_by_state: dict[str, int]
    ocr_provenance_objects: int
    translation_provenance_objects: int
    token_usage_available: bool
    total_input_tokens: int | None
    total_output_tokens: int | None
    estimated_cost_usd: float | None
    note: str


class AccountUsageResponse(BaseModel):
    general: GeneralUsageResponse
    api: ProviderUsageResponse


def _profile_response(account: Account) -> AccountProfileResponse:
    return AccountProfileResponse(
        account_uuid=account.account_uuid,
        email=account.email,
        display_name=account.display_name,
        active=account.active,
        approval_status=account.approval_status.value,
        is_admin=is_admin_email(account.email),
    )


@router.get("/profile", response_model=AccountProfileResponse)
async def get_my_profile(current: CurrentAccount) -> AccountProfileResponse:
    return _profile_response(current)


@router.put("/profile", response_model=AccountProfileResponse)
async def update_my_profile(
    req: AccountProfileUpdateRequest,
    session: DbSession,
    current: CurrentAccount,
) -> AccountProfileResponse:
    account = await session.get(Account, current.account_uuid)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    display_name = req.display_name.strip() if req.display_name is not None else None
    account.display_name = display_name or None
    await session.flush()
    return _profile_response(account)


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    req: PasswordChangeRequest,
    session: DbSession,
    current: CurrentAccount,
) -> None:
    account = await session.get(Account, current.account_uuid)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if not verify_password(req.current_password, account.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    account.password_hash = hash_password(req.new_password)
    await session.flush()


@router.get("/usage", response_model=AccountUsageResponse)
async def get_my_usage(
    session: DbSession,
    current: CurrentAccount,
) -> AccountUsageResponse:
    project_rows = await session.execute(
        select(Project.project_uuid, Project.active).where(
            Project.account_uuid == current.account_uuid
        )
    )
    projects = list(project_rows.all())
    project_uuids = [row.project_uuid for row in projects]
    if not project_uuids:
        empty_general = GeneralUsageResponse(
            projects=0,
            active_projects=0,
            uploaded_books=0,
            pages=0,
            ocr_pages=0,
            translated_pages=0,
            segments=0,
            translated_segments=0,
            storage_bytes=0,
        )
        return AccountUsageResponse(general=empty_general, api=_empty_provider_usage())

    page_count = await _count_pages(session, project_uuids)
    ocr_page_count = await _count_ocr_pages(session, project_uuids)
    segment_count = await _count_segments(session, project_uuids)
    translated_segments, translated_pages = await _count_translation_coverage(
        session, project_uuids
    )
    uploaded_books, storage_bytes = await _upload_usage(session, project_uuids)
    api_usage = await _provider_usage(session, project_uuids)

    return AccountUsageResponse(
        general=GeneralUsageResponse(
            projects=len(projects),
            active_projects=sum(1 for row in projects if row.active),
            uploaded_books=uploaded_books,
            pages=page_count,
            ocr_pages=ocr_page_count,
            translated_pages=translated_pages,
            segments=segment_count,
            translated_segments=translated_segments,
            storage_bytes=storage_bytes,
        ),
        api=api_usage,
    )


async def _count_pages(session: DbSession, project_uuids: list[_uuid.UUID]) -> int:
    result = await session.execute(
        select(func.count()).select_from(Page).where(Page.project_uuid.in_(project_uuids))
    )
    return int(result.scalar_one())


async def _count_ocr_pages(session: DbSession, project_uuids: list[_uuid.UUID]) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(Page)
        .where(Page.project_uuid.in_(project_uuids))
        .where(Page.ocr_status != OcrStatus.AUSSTEHEND)
    )
    return int(result.scalar_one())


async def _count_segments(session: DbSession, project_uuids: list[_uuid.UUID]) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(Segment)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Page.project_uuid.in_(project_uuids))
        .where(Segment.active.is_(True))
    )
    return int(result.scalar_one())


async def _count_translation_coverage(
    session: DbSession, project_uuids: list[_uuid.UUID]
) -> tuple[int, int]:
    result = await session.execute(
        select(Segment.satz_uuid, Page.page_uuid)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .join(
            ProvenanceObject,
            (ProvenanceObject.scope_uuid == Segment.satz_uuid)
            & (ProvenanceObject.scope_type == ScopeType.SEGMENT.value)
            & (ProvenanceObject.po_type == POType.TRANSLATION.value),
        )
        .where(Page.project_uuid.in_(project_uuids))
        .where(Segment.active.is_(True))
    )
    rows = list(result.all())
    return len({row.satz_uuid for row in rows}), len({row.page_uuid for row in rows})


async def _upload_usage(session: DbSession, project_uuids: list[_uuid.UUID]) -> tuple[int, int]:
    result = await session.execute(
        select(Job.result)
        .where(Job.project_uuid.in_(project_uuids))
        .where(Job.job_type == "upload")
        .where(Job.state == JobState.COMPLETED.value)
    )
    uploaded_books = 0
    storage_bytes = 0
    for (job_result,) in result.all():
        if not isinstance(job_result, dict):
            continue
        uploaded_books += 1
        size = job_result.get("size_bytes")
        if isinstance(size, int):
            storage_bytes += size
    return uploaded_books, storage_bytes


async def _provider_usage(
    session: DbSession, project_uuids: list[_uuid.UUID]
) -> ProviderUsageResponse:
    jobs_result = await session.execute(
        select(Job.job_type, Job.state, func.count())
        .where(Job.project_uuid.in_(project_uuids))
        .group_by(Job.job_type, Job.state)
    )
    jobs_by_type: Counter[str] = Counter()
    jobs_by_state: Counter[str] = Counter()
    for job_type, state, count in jobs_result.all():
        jobs_by_type[str(job_type)] += int(count)
        jobs_by_state[str(state)] += int(count)

    provenance_rows = await _ocr_translation_provenance(session, project_uuids)
    provider_calls: defaultdict[str, int] = defaultdict(int)
    ocr_po_count = 0
    translation_po_count = 0
    input_tokens = 0
    output_tokens = 0
    has_tokens = False

    for po_type, payload in provenance_rows:
        if po_type == POType.OCR.value:
            ocr_po_count += 1
            _add_ocr_provider_counts(provider_calls, payload)
        elif po_type == POType.TRANSLATION.value:
            translation_po_count += 1
            _add_translation_provider_counts(provider_calls, payload)
        token_usage = payload.get("token_usage") if isinstance(payload, dict) else None
        if isinstance(token_usage, dict):
            in_tokens = token_usage.get("input_tokens")
            out_tokens = token_usage.get("output_tokens")
            if isinstance(in_tokens, int) or isinstance(out_tokens, int):
                has_tokens = True
                input_tokens += int(in_tokens or 0)
                output_tokens += int(out_tokens or 0)

    return ProviderUsageResponse(
        provider_calls=dict(sorted(provider_calls.items())),
        jobs_by_type=dict(sorted(jobs_by_type.items())),
        jobs_by_state=dict(sorted(jobs_by_state.items())),
        ocr_provenance_objects=ocr_po_count,
        translation_provenance_objects=translation_po_count,
        token_usage_available=has_tokens,
        total_input_tokens=input_tokens if has_tokens else None,
        total_output_tokens=output_tokens if has_tokens else None,
        estimated_cost_usd=None,
        note=(
            "Provider call counts are based on stored jobs/provenance. "
            "Token usage and cost are unavailable until provider responses are persisted."
        ),
    )


async def _ocr_translation_provenance(
    session: DbSession, project_uuids: list[_uuid.UUID]
) -> list[tuple[str, dict[str, Any]]]:
    result = await session.execute(
        select(ProvenanceObject.po_type, ProvenanceObject.payload)
        .join(Segment, Segment.satz_uuid == ProvenanceObject.scope_uuid)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Page.project_uuid.in_(project_uuids))
        .where(ProvenanceObject.scope_type == ScopeType.SEGMENT.value)
        .where(ProvenanceObject.po_type.in_([POType.OCR.value, POType.TRANSLATION.value]))
    )
    return [
        (str(po_type), payload if isinstance(payload, dict) else {})
        for po_type, payload in result.all()
    ]


def _add_ocr_provider_counts(provider_calls: defaultdict[str, int], payload: dict[str, Any]) -> None:
    engines = payload.get("engines")
    if isinstance(engines, list) and engines:
        for engine in engines:
            if isinstance(engine, dict):
                _increment_provider(provider_calls, engine.get("engine"))
        return
    _increment_provider(provider_calls, payload.get("model") or "gemini")


def _add_translation_provider_counts(
    provider_calls: defaultdict[str, int], payload: dict[str, Any]
) -> None:
    for key in ("engine", "primary_engine", "check_engine"):
        _increment_provider(provider_calls, payload.get(key))
    cross_check = payload.get("cross_check")
    if isinstance(cross_check, dict):
        for key in ("primary_engine", "check_engine"):
            _increment_provider(provider_calls, cross_check.get(key))


def _increment_provider(provider_calls: defaultdict[str, int], raw: Any) -> None:
    if not isinstance(raw, str) or not raw:
        return
    lowered = raw.lower()
    if "openai" in lowered or "gpt" in lowered:
        provider_calls["openai"] += 1
    elif "gemini" in lowered or "google" in lowered:
        provider_calls["gemini"] += 1
    elif "vision" in lowered or "cloud" in lowered:
        provider_calls["cloud_vision"] += 1
    else:
        provider_calls[raw] += 1


def _empty_provider_usage() -> ProviderUsageResponse:
    return ProviderUsageResponse(
        provider_calls={},
        jobs_by_type={},
        jobs_by_state={},
        ocr_provenance_objects=0,
        translation_provenance_objects=0,
        token_usage_available=False,
        total_input_tokens=None,
        total_output_tokens=None,
        estimated_cost_usd=None,
        note=(
            "Provider call counts are based on stored jobs/provenance. "
            "Token usage and cost are unavailable until provider responses are persisted."
        ),
    )
