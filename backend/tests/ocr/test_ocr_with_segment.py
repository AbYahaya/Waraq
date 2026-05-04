"""T-4.1.2 — OCR-PO + revision-UUID on text change.

The contract:
- When `run_ocr_job(..., target_segment=segment)` succeeds and the OCR text
  differs from the segment's current text_content → write a Revision via
  `create_revision` AND an OCR-PO via `create_po`.
- When the OCR text matches the segment's current text → write the OCR-PO
  but NOT a Revision (H-4: no revision-UUID for non-changes).
- When the segment is locked (manual_local / manual_editorial) and OCR is
  AUTOMATIC → create_revision raises H1H2Violation, the job is marked
  FAILED, and NO OCR-PO is written.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.invariant.exceptions import H1H2Violation
from waraq.ocr import run_ocr_job, start_ocr_job
from waraq.schemas import (
    Block,
    Page,
    Project,
    ProvenanceObject,
    Revision,
    Segment,
)
from waraq.schemas.enums import ChangeSource, JobState, POType, ScopeType

# --- Helpers ---------------------------------------------------------------


async def _seed_segment(
    session: AsyncSession,
    *,
    initial_text: str | None = None,
    lock_flag: LockFlag = LockFlag.NONE,
) -> tuple[Page, Segment]:
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(
        project_uuid=new_uuid(),
        account_uuid=account_uuid,
        name="ocr-revision-test",
    )
    session.add(project)
    await session.flush()

    page = Page(page_uuid=new_uuid(), project_uuid=project.project_uuid, page_index=1)
    session.add(page)
    await session.flush()

    block = Block(
        block_uuid=new_uuid(),
        page_uuid=page.page_uuid,
        block_type="main_text",
        block_index=1,
    )
    session.add(block)
    await session.flush()

    segment = Segment(
        satz_uuid=new_uuid(),
        block_uuid=block.block_uuid,
        satz_index=1,
        lock_flag=lock_flag,
        text_content=initial_text,
    )
    session.add(segment)
    await session.flush()
    return page, segment


class _StubExtractor:
    def __init__(self, return_text: str) -> None:
        self.return_text = return_text

    async def __call__(self, _b: bytes, _m: str) -> str:
        return self.return_text


# --- Layer 1: H-4 — Revision only on text change -------------------------


@pytest.mark.asyncio
class TestT_4_1_2_RevisionOnlyOnTextChange:
    async def test_first_ocr_writes_a_revision(self, db_session: AsyncSession) -> None:
        page, segment = await _seed_segment(db_session, initial_text=None)
        job = await start_ocr_job(session=db_session, page=page)

        ocr_text = "بسم الله الرحمن الرحيم"
        await run_ocr_job(
            session=db_session,
            ocr_job=job,
            image_bytes=b"<png>",
            extractor=_StubExtractor(ocr_text),
            target_segment=segment,
        )

        revs = (
            (
                await db_session.execute(
                    select(Revision).where(Revision.satz_uuid == segment.satz_uuid)
                )
            )
            .scalars()
            .all()
        )
        assert len(revs) == 1
        assert revs[0].after_text == ocr_text
        assert revs[0].before_text is None
        assert revs[0].change_source == ChangeSource.OCR.value
        # Segment now points at the new revision and carries the new text.
        assert segment.current_rev_uuid == revs[0].rev_uuid
        assert segment.text_content == ocr_text

    async def test_second_ocr_with_changed_text_writes_a_new_revision(
        self, db_session: AsyncSession
    ) -> None:
        page, segment = await _seed_segment(db_session, initial_text="alt")
        job1 = await start_ocr_job(session=db_session, page=page)
        await run_ocr_job(
            session=db_session,
            ocr_job=job1,
            image_bytes=b"x",
            extractor=_StubExtractor("alt"),  # matches existing — no rev
            target_segment=segment,
        )
        # Confirm no revision yet (matches existing text).
        revs = (
            (
                await db_session.execute(
                    select(Revision).where(Revision.satz_uuid == segment.satz_uuid)
                )
            )
            .scalars()
            .all()
        )
        assert revs == []

        # Second OCR returns different text → revision written.
        job2 = await start_ocr_job(session=db_session, page=page)
        await run_ocr_job(
            session=db_session,
            ocr_job=job2,
            image_bytes=b"x",
            extractor=_StubExtractor("neu"),
            target_segment=segment,
        )
        revs = (
            (
                await db_session.execute(
                    select(Revision).where(Revision.satz_uuid == segment.satz_uuid)
                )
            )
            .scalars()
            .all()
        )
        assert len(revs) == 1
        assert revs[0].before_text == "alt"
        assert revs[0].after_text == "neu"

    async def test_unchanged_text_writes_no_revision(self, db_session: AsyncSession) -> None:
        """H-4: no revision-UUID is issued for non-changes."""
        page, segment = await _seed_segment(db_session, initial_text="same")
        job = await start_ocr_job(session=db_session, page=page)

        before_count = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()

        await run_ocr_job(
            session=db_session,
            ocr_job=job,
            image_bytes=b"x",
            extractor=_StubExtractor("same"),
            target_segment=segment,
        )

        after_count = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()
        assert after_count == before_count
        # Job result reports no change.
        assert job.result is not None
        assert job.result["text_changed"] is False
        assert job.result["rev_uuid"] is None


# --- Layer 2: OCR-PO is written on every successful pass -----------------


@pytest.mark.asyncio
class TestT_4_1_2_OcrPoOnEverySuccessfulPass:
    async def test_ocr_po_written_when_text_changes(self, db_session: AsyncSession) -> None:
        page, segment = await _seed_segment(db_session, initial_text=None)
        job = await start_ocr_job(session=db_session, page=page)

        await run_ocr_job(
            session=db_session,
            ocr_job=job,
            image_bytes=b"x",
            extractor=_StubExtractor("hello"),
            target_segment=segment,
        )

        po = (
            await db_session.execute(
                select(ProvenanceObject).where(
                    ProvenanceObject.scope_type == ScopeType.SEGMENT.value,
                    ProvenanceObject.scope_uuid == segment.satz_uuid,
                    ProvenanceObject.po_type == POType.OCR.value,
                )
            )
        ).scalar_one()
        assert po.payload["text_changed"] is True
        assert po.payload["rev_uuid"] is not None
        assert po.payload["text_chars"] == len("hello")
        assert po.payload["model"]  # model name present
        assert po.payload["ocr_job_uuid"] == str(job.job_uuid)

    async def test_ocr_po_written_when_text_unchanged_with_null_rev_uuid(
        self, db_session: AsyncSession
    ) -> None:
        """OCR-PO records that the OCR pass happened, even when no Revision
        was issued. rev_uuid in the payload is None."""
        page, segment = await _seed_segment(db_session, initial_text="same")
        job = await start_ocr_job(session=db_session, page=page)

        await run_ocr_job(
            session=db_session,
            ocr_job=job,
            image_bytes=b"x",
            extractor=_StubExtractor("same"),
            target_segment=segment,
        )

        po = (
            await db_session.execute(
                select(ProvenanceObject).where(
                    ProvenanceObject.scope_uuid == segment.satz_uuid,
                    ProvenanceObject.po_type == POType.OCR.value,
                )
            )
        ).scalar_one()
        assert po.payload["text_changed"] is False
        assert po.payload["rev_uuid"] is None


# --- Layer 3: H-1/H-2 — locked segment refused, no OCR-PO written --------


@pytest.mark.asyncio
class TestT_4_1_2_LockedSegmentRefusal:
    async def test_manual_local_segment_refuses_ocr(self, db_session: AsyncSession) -> None:
        """OCR is AUTOMATIC. create_revision's Guard raises H1H2Violation
        on a manual_local segment. The OCR job is marked FAILED with the
        violation in Job.error, and **no OCR-PO is written**."""
        page, segment = await _seed_segment(
            db_session, initial_text="locked", lock_flag=LockFlag.MANUAL_LOCAL
        )
        job = await start_ocr_job(session=db_session, page=page)

        po_count_before = (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one()

        with pytest.raises(H1H2Violation):
            await run_ocr_job(
                session=db_session,
                ocr_job=job,
                image_bytes=b"x",
                extractor=_StubExtractor("new text"),
                target_segment=segment,
            )

        # Job FAILED with phase=guard.
        assert job.state == JobState.FAILED.value
        assert job.error is not None
        assert job.error["error_class"] == "H1H2Violation"
        assert job.error["phase"] == "guard"

        # No OCR-PO written for a Guard refusal — contract per service docstring.
        po_count_after = (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one()
        assert po_count_after == po_count_before

        # Segment text unchanged.
        await db_session.refresh(segment)
        assert segment.text_content == "locked"
        assert segment.lock_flag == LockFlag.MANUAL_LOCAL

    async def test_manual_editorial_segment_refuses_ocr(self, db_session: AsyncSession) -> None:
        page, segment = await _seed_segment(
            db_session, initial_text="locked", lock_flag=LockFlag.MANUAL_EDITORIAL
        )
        job = await start_ocr_job(session=db_session, page=page)

        with pytest.raises(H1H2Violation):
            await run_ocr_job(
                session=db_session,
                ocr_job=job,
                image_bytes=b"x",
                extractor=_StubExtractor("new"),
                target_segment=segment,
            )

        assert job.state == JobState.FAILED.value
        # No revision was written.
        revs = (
            (
                await db_session.execute(
                    select(Revision).where(Revision.satz_uuid == segment.satz_uuid)
                )
            )
            .scalars()
            .all()
        )
        assert revs == []


# --- Layer 4: backwards compat — baseline mode unchanged ----------------


@pytest.mark.asyncio
class TestT_4_1_2_BaselineModeStillWorks:
    """When called without target_segment, run_ocr_job still behaves as the
    T-4.1.1 baseline: just returns text, no events/POs. (The T-4.1.1 tests
    cover this exhaustively; this is one paranoid double-check that the
    T-4.1.2 changes didn't accidentally regress baseline behavior.)"""

    async def test_no_target_segment_still_returns_text(self, db_session: AsyncSession) -> None:
        page, _ = await _seed_segment(db_session)
        job = await start_ocr_job(session=db_session, page=page)
        text = await run_ocr_job(
            session=db_session,
            ocr_job=job,
            image_bytes=b"x",
            extractor=_StubExtractor("hello"),
            # target_segment intentionally omitted
        )
        assert text == "hello"
        assert job.state == JobState.COMPLETED.value
        # No revision, no PO.
        assert job.result is not None
        assert job.result.get("rev_uuid") is None
        assert job.result.get("text_changed") is False
