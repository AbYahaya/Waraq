"""Project endpoints."""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, Response, status
from sqlalchemy import select

from waraq.api._ownership import owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import ProjectCreateRequest, ProjectResponse
from waraq.identity.service import new_uuid
from waraq.projects import delete_project as delete_project_service
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
    # Sub-batch P (2026-05-13): defer to the centralized ownership helper
    # so deleted (active=False) projects 404 here too, matching the rest
    # of the routes that already use it.
    project = await owned_project_or_404(session, project_uuid, current.account_uuid)
    return ProjectResponse.model_validate(project)


@router.delete(
    "/{project_uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_project(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> Response:
    """Sub-batch P (out-of-phase, 2026-05-13) — soft-delete a project.

    Per H-5 this is inactivation (`active=false`), not a hard delete —
    the Project row + all child UUIDs survive in the DB forever.
    Children remain `active=true` but are unreachable because every
    ownership helper now refuses chains rooted at an inactive project.

    Any in-flight `ocr_auto_run` / `translation` Job for the project
    gets `payload.cancel_requested=True` set in the same transaction
    (user-chosen "auto-cancel then delete" behaviour). The runner
    cooperatively bails on its next iteration.
    """
    project = await owned_project_or_404(session, project_uuid, current.account_uuid)
    await delete_project_service(session=session, project=project)
    # Session.commit() happens via the DbSession dependency.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
