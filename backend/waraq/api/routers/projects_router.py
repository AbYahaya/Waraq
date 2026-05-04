"""Project endpoints."""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import ProjectCreateRequest, ProjectResponse
from waraq.identity.service import new_uuid
from waraq.schemas import Project

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    req: ProjectCreateRequest,
    session: DbSession,
    current: CurrentAccount,
) -> ProjectResponse:
    project = Project(
        project_uuid=new_uuid(),
        account_uuid=current.account_uuid,
        name=req.name,
    )
    session.add(project)
    await session.flush()
    return ProjectResponse.model_validate(project)


@router.get("", response_model=list[ProjectResponse])
async def list_my_projects(session: DbSession, current: CurrentAccount) -> list[ProjectResponse]:
    result = await session.execute(
        select(Project)
        .where(Project.account_uuid == current.account_uuid, Project.active.is_(True))
        .order_by(Project.created_at)
    )
    return [ProjectResponse.model_validate(p) for p in result.scalars().all()]


@router.get("/{project_uuid}", response_model=ProjectResponse)
async def get_project(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> ProjectResponse:
    project: Project | None = await session.get(Project, project_uuid)
    if project is None or project.account_uuid != current.account_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return ProjectResponse.model_validate(project)
