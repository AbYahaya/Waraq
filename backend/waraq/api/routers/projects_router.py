"""Project endpoints."""

from __future__ import annotations

import uuid as _uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from waraq.api._ownership import owned_project_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectTranslationAvailabilityResponse,
    TrashedProjectResponse,
)
from waraq.identity.service import new_uuid
from waraq.projects import delete_project as delete_project_service
from waraq.schemas import Block, Page, Project, Revision, Segment
from waraq.schemas.enums import ChangeSource

router = APIRouter(prefix="/projects", tags=["projects"])

TRASH_RETENTION_DAYS = 10


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


@router.get("/trash", response_model=list[TrashedProjectResponse])
async def list_trashed_projects(
    session: DbSession,
    current: CurrentAccount,
) -> list[TrashedProjectResponse]:
    result = await session.execute(
        select(Project)
        .where(Project.account_uuid == current.account_uuid, Project.active.is_(False))
        .order_by(Project.updated_at.desc())
    )
    return [_trashed_project_response(p) for p in result.scalars().all()]


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


@router.post("/{project_uuid}/restore", response_model=ProjectResponse)
async def restore_project(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> ProjectResponse:
    result = await session.execute(
        select(Project).where(
            Project.project_uuid == project_uuid,
            Project.account_uuid == current.account_uuid,
            Project.active.is_(False),
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not _is_restorable(project):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project restore window expired after {TRASH_RETENTION_DAYS} days.",
        )

    project.active = True
    await session.flush()
    return ProjectResponse.model_validate(project)


@router.get(
    "/{project_uuid}/translation-availability",
    response_model=ProjectTranslationAvailabilityResponse,
)
async def get_project_translation_availability(
    project_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> ProjectTranslationAvailabilityResponse:
    await owned_project_or_404(session, project_uuid, current.account_uuid)

    segment_rows = (
        await session.execute(
            select(Segment.satz_uuid)
            .select_from(Segment)
            .join(Block, Block.block_uuid == Segment.block_uuid)
            .join(Page, Page.page_uuid == Block.page_uuid)
            .where(Page.project_uuid == project_uuid)
            .where(Segment.active.is_(True))
        )
    ).all()
    segment_uuids = [row[0] for row in segment_rows]
    total_segments = len(segment_uuids)

    translated_segments = 0
    fresh_translated_segments = 0
    stale_translated_segments = 0

    if segment_uuids:
        revision_rows = (
            await session.execute(
                select(Revision.satz_uuid, Revision.change_source, Revision.created_at)
                .where(Revision.satz_uuid.in_(segment_uuids))
                .order_by(Revision.satz_uuid.asc(), Revision.created_at.asc())
            )
        ).all()

        revision_summary: dict[_uuid.UUID, dict[str, datetime | None]] = {
            satz_uuid: {"source_at": None, "target_at": None} for satz_uuid in segment_uuids
        }
        for satz_uuid, change_source, created_at in revision_rows:
            summary = revision_summary[satz_uuid]
            if change_source == ChangeSource.RE_TRANSLATE.value:
                summary["target_at"] = created_at
            else:
                summary["source_at"] = created_at

        for satz_uuid in segment_uuids:
            summary = revision_summary[satz_uuid]
            source_at = summary["source_at"]
            target_at = summary["target_at"]
            if target_at is None:
                continue
            translated_segments += 1
            if source_at is None or target_at >= source_at:
                fresh_translated_segments += 1
            else:
                stale_translated_segments += 1

    untranslated_segments = total_segments - translated_segments

    return ProjectTranslationAvailabilityResponse(
        project_uuid=project_uuid,
        total_segments=total_segments,
        translated_segments=translated_segments,
        fresh_translated_segments=fresh_translated_segments,
        stale_translated_segments=stale_translated_segments,
        untranslated_segments=untranslated_segments,
        has_translation=translated_segments > 0,
        has_full_translation=total_segments > 0 and translated_segments == total_segments,
        has_fresh_translation=fresh_translated_segments > 0,
        has_full_fresh_translation=(
            total_segments > 0 and fresh_translated_segments == total_segments
        ),
    )


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


def _deleted_at(project: Project) -> datetime | None:
    return project.updated_at or project.created_at


def _as_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _restore_until(project: Project) -> datetime | None:
    deleted_at = _as_aware(_deleted_at(project))
    if deleted_at is None:
        return None
    return deleted_at + timedelta(days=TRASH_RETENTION_DAYS)


def _is_restorable(project: Project) -> bool:
    restore_until = _restore_until(project)
    return restore_until is not None and datetime.now(UTC) <= restore_until


def _trashed_project_response(project: Project) -> TrashedProjectResponse:
    deleted_at = _as_aware(_deleted_at(project))
    restore_until = _restore_until(project)
    remaining = 0
    if restore_until is not None:
        seconds = (restore_until - datetime.now(UTC)).total_seconds()
        remaining = max(0, int((seconds + 86_399) // 86_400))
    return TrashedProjectResponse(
        project_uuid=project.project_uuid,
        account_uuid=project.account_uuid,
        name=project.name,
        active=project.active,
        deleted_at=deleted_at.isoformat() if deleted_at else None,
        restore_until=restore_until.isoformat() if restore_until else None,
        days_remaining=remaining,
        restorable=_is_restorable(project),
    )
