"""Shared seed helpers for export (T-9.2.1) tests."""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag, OperationMode
from waraq.preflight import (
    PFLICHTFRAGE_COUNT,
    PreflightState,
    confirm_pflichtfrage,
    evaluate_preflight,
    start_preflight_run,
)
from waraq.preflight.enums import WarningSlot
from waraq.preflight.service import accept_warning_gate
from waraq.revision import create_revision
from waraq.schemas import Block, Job, Page, Project, Segment
from waraq.schemas.enums import ChangeSource, OcrStatus


async def seed_account(session: AsyncSession) -> _uuid.UUID:
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)
    return account_uuid


async def seed_project_with_account(
    session: AsyncSession, *, name: str = "export-test"
) -> tuple[Project, _uuid.UUID]:
    account_uuid = await seed_account(session)
    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name=name)
    session.add(project)
    await session.flush()
    return project, account_uuid


async def seed_segment_with_revision(
    session: AsyncSession,
    *,
    project: Project,
    text: str,
    page_index: int = 1,
    block_index: int = 0,
    satz_index: int = 0,
    create_initial_revision: bool = True,
) -> Segment:
    """Seed a segment + its first revision so `current_rev_uuid` is set.

    The export snapshot reads `segments.current_rev_uuid`; tests need
    this populated to verify Revision-Snapshot-Vollstaendigkeit-Test.
    """
    page = Page(
        page_uuid=new_uuid(),
        project_uuid=project.project_uuid,
        page_index=page_index,
        ocr_status=OcrStatus.GO,
    )
    session.add(page)
    await session.flush()
    block = Block(
        block_uuid=new_uuid(),
        page_uuid=page.page_uuid,
        block_type="main_text",
        block_index=block_index,
    )
    session.add(block)
    await session.flush()
    seg = Segment(
        satz_uuid=new_uuid(),
        block_uuid=block.block_uuid,
        satz_index=satz_index,
        lock_flag=LockFlag.NONE,
        text_content=text,
    )
    session.add(seg)
    await session.flush()
    if create_initial_revision:
        await create_revision(
            session=session,
            segment=seg,
            after_text=text,
            change_source=ChangeSource.MANUAL,
            operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
        )
    return seg


async def confirm_all_pflichtfragen(
    session: AsyncSession,
    *,
    project_uuid: _uuid.UUID,
    preflight_run: Job,
) -> None:
    for i in range(1, PFLICHTFRAGE_COUNT + 1):
        await confirm_pflichtfrage(
            session=session,
            project_uuid=project_uuid,
            preflight_run_uuid=preflight_run.job_uuid,
            frage_index=i,
            frage_key=f"frage_{i}",
            answer={"value": "yes"},
        )


async def reach_exportierbar(
    session: AsyncSession, *, project: Project
) -> tuple[Job, PreflightState]:
    """Run preflight to `exportierbar` for a clean project + return the
    preflight run handle (caller passes it to `run_export_job`)."""
    run = await start_preflight_run(session=session, project_uuid=project.project_uuid)
    await confirm_all_pflichtfragen(
        session=session, project_uuid=project.project_uuid, preflight_run=run
    )
    ev = await evaluate_preflight(
        session=session, project_uuid=project.project_uuid, preflight_run=run
    )
    return run, ev.state


async def accept_warnings(
    session: AsyncSession,
    *,
    project_uuid: _uuid.UUID,
    preflight_run: Job,
    warning_slots: list[WarningSlot],
) -> None:
    for slot in warning_slots:
        await accept_warning_gate(
            session=session,
            project_uuid=project_uuid,
            preflight_run=preflight_run,
            warning_slot=slot,
        )
