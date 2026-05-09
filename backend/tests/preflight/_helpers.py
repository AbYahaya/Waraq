"""Shared seed helpers for preflight tests."""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.audit.service import RuleFinding, record_befund
from waraq.audit.severity import default_severity_table
from waraq.identity import new_uuid
from waraq.preflight.enums import HadithStellenTyp
from waraq.preflight.hadith import record_hadith_status
from waraq.schemas import Job, KonsistenzBefund, OcrErrorInstance, Project, Segment
from waraq.schemas.enums import JobState


async def seed_audit_job(session: AsyncSession, *, project: Project) -> Job:
    job = Job(
        job_uuid=new_uuid(),
        project_uuid=project.project_uuid,
        job_type="audit",
        state=JobState.COMPLETED.value,
    )
    session.add(job)
    await session.flush()
    return job


async def seed_befund(
    session: AsyncSession,
    *,
    project: Project,
    segment: Segment,
    audit_job: Job,
    regelkennung: str,
):
    return await record_befund(
        session=session,
        finding=RuleFinding(
            regelkennung=regelkennung,
            satz_uuid=segment.satz_uuid,
            detection_context={"marker": "test"},
        ),
        project_uuid=project.project_uuid,
        audit_run_job_uuid=audit_job.job_uuid,
        severity_table=default_severity_table(),
    )


async def seed_konsistenz_befund(
    session: AsyncSession,
    *,
    project: Project,
    k_rule: str,
    subject_type: str,
    subject_key: str,
    verstossklasse: str = "mittel",
) -> KonsistenzBefund:
    row = KonsistenzBefund(
        konsistenz_befund_uuid=new_uuid(),
        project_uuid=project.project_uuid,
        k_rule=k_rule,
        subject_type=subject_type,
        subject_key=subject_key,
        verstossklasse=verstossklasse,
        betroffene_segment_uuids=[],
        vorschlag={},
    )
    session.add(row)
    await session.flush()
    return row


async def seed_hadith(
    session: AsyncSession,
    *,
    project: Project,
    segment: Segment,
    stellen_typ: HadithStellenTyp,
):
    return await record_hadith_status(
        session=session,
        satz_uuid=segment.satz_uuid,
        project_uuid=project.project_uuid,
        stellen_typ=stellen_typ,
    )


async def seed_ocr_error(
    session: AsyncSession,
    *,
    page_uuid: _uuid.UUID,
    error_code: str,
    state: str = "offen",
) -> OcrErrorInstance:
    row = OcrErrorInstance(
        ocr_error_instance_uuid=new_uuid(),
        page_uuid=page_uuid,
        error_code=error_code,
        state=state,
    )
    session.add(row)
    await session.flush()
    return row
