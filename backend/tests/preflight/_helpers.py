"""Shared seed helpers for preflight tests."""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.audit.service import RuleFinding, record_befund
from waraq.audit.severity import default_severity_table
from waraq.identity import new_uuid
from waraq.preflight.enums import HadithStellenTyp
from waraq.preflight.hadith import record_hadith_status
from waraq.schemas import Job, KonsistenzBefund, OcrErrorInstance, Project, Segment
from waraq.schemas.enums import JobState


def canonical_pflichtfrage_payload(frage_index: int) -> tuple[str, dict[str, Any]]:
    """Return (frage_key, valid_answer) for the canonical §4.7.2 Pflichtfrage
    at `frage_index` ∈ {1,2,3,4}.

    Used by tests that need to confirm Pflichtfragen end-to-end with
    payloads that satisfy the §4.7.2 answer-schema validation.
    """
    if frage_index == 1:
        return "header_heading_level", {"heading_level": 1}
    if frage_index == 2:
        return "chapter_break_heading_level", {"heading_level": 2}
    if frage_index == 3:
        return "toc_position", {"position": "front"}
    if frage_index == 4:
        return "display_arabic_chapter_headings", {"display": True}
    raise AssertionError(f"frage_index {frage_index!r} out of canonical 1..4 range")


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
