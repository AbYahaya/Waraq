"""Admin endpoints (M4 scope only — accounts list + project list).

The admin role is gated by the `WARAQ_ADMIN_EMAILS` env allowlist (see
`require_admin` in `dependencies.py`). No `is_admin` column, no schema
migration — admin is a deployment concern at v1.0.

Out-of-scope for v1.0 (parked for M5+): the §4.18.3 Admin-Optimierungs-
Eingabekanal — that's canon backend work, not a UI listing.
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from waraq.admission import is_admin_email
from waraq.api.dependencies import CurrentAdmin, DbSession
from waraq.schemas import Account, Project

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_uuid: _uuid.UUID
    email: str
    display_name: str | None
    active: bool
    approval_status: str
    is_admin: bool = False


class AdminProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_uuid: _uuid.UUID
    account_uuid: _uuid.UUID
    name: str
    active: bool


@router.get("/accounts", response_model=list[AdminAccountResponse])
async def list_all_accounts(
    session: DbSession,
    current: CurrentAdmin,
    include_inactive: bool = Query(default=False),
) -> list[AdminAccountResponse]:
    _ = current
    stmt = select(Account).order_by(Account.email.asc())
    if not include_inactive:
        stmt = stmt.where(Account.active.is_(True))
    result = await session.execute(stmt)
    return [
        AdminAccountResponse(
            account_uuid=a.account_uuid,
            email=a.email,
            display_name=a.display_name,
            active=a.active,
            approval_status=a.approval_status.value
            if hasattr(a.approval_status, "value")
            else str(a.approval_status),
            is_admin=is_admin_email(a.email),
        )
        for a in result.scalars()
    ]


@router.get("/projects", response_model=list[AdminProjectResponse])
async def list_all_projects(
    session: DbSession,
    current: CurrentAdmin,
    account_uuid: _uuid.UUID | None = Query(default=None),
    include_inactive: bool = Query(default=False),
) -> list[AdminProjectResponse]:
    _ = current
    stmt = select(Project).order_by(Project.created_at.desc())
    if not include_inactive:
        stmt = stmt.where(Project.active.is_(True))
    if account_uuid is not None:
        stmt = stmt.where(Project.account_uuid == account_uuid)
    result = await session.execute(stmt)
    return [AdminProjectResponse.model_validate(p) for p in result.scalars()]
