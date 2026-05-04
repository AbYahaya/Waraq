"""T-1.4.1 — create_revision service tests.

Two layers:
1. Guard discipline tests — pure unit, no DB. Confirm that the service
   refuses Guard-violating call sites before any write attempt.
2. Integration tests — against the live Postgres from docker-compose. A
   per-test transaction is rolled back, so nothing leaks between tests.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag, OperationMode
from waraq.invariant.exceptions import H1H2Violation
from waraq.revision import create_revision
from waraq.schemas import Block, Page, Project, Revision, Segment
from waraq.schemas.enums import ChangeSource

# --- Layer 1: Guard discipline (no DB) ------------------------------------


class _SegmentStub:
    """In-memory stand-in that satisfies the Segment surface the Guard reads.

    We use a stub instead of an unpersisted ORM Segment so that Guard tests
    do not depend on the database fixture or sessionmaker."""

    def __init__(self, lock_flag: LockFlag) -> None:
        self.satz_uuid = new_uuid()
        self.lock_flag = lock_flag
        self.text_content: str | None = None
        self.current_rev_uuid: _uuid.UUID | None = None


class _SessionStub:
    """Captures `add(...)` and provides a no-op `flush()`. Guard tests should
    raise before either is called; if the stub is touched, the test fails."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.flushed = False

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushed = True


class TestT_1_4_1_GuardEnforcement:
    @pytest.mark.h1
    @pytest.mark.asyncio
    async def test_refuses_automatic_write_to_manual_local(self) -> None:
        seg = _SegmentStub(LockFlag.MANUAL_LOCAL)
        sess = _SessionStub()
        with pytest.raises(H1H2Violation):
            await create_revision(
                session=sess,  # type: ignore[arg-type]
                segment=seg,  # type: ignore[arg-type]
                after_text="x",
                change_source=ChangeSource.OCR,
                operation_mode=OperationMode.AUTOMATIC,
            )
        assert sess.added == []
        assert sess.flushed is False

    @pytest.mark.h2
    @pytest.mark.asyncio
    async def test_refuses_automatic_write_to_manual_editorial(self) -> None:
        seg = _SegmentStub(LockFlag.MANUAL_EDITORIAL)
        sess = _SessionStub()
        with pytest.raises(H1H2Violation):
            await create_revision(
                session=sess,  # type: ignore[arg-type]
                segment=seg,  # type: ignore[arg-type]
                after_text="x",
                change_source=ChangeSource.OCR,
                operation_mode=OperationMode.AUTOMATIC,
            )
        assert sess.added == []


# --- Layer 2: integration against live Postgres ---------------------------


async def _seed_segment(
    session: AsyncSession,
    *,
    initial_text: str | None = None,
    lock_flag: LockFlag = LockFlag.NONE,
) -> Segment:
    """Insert a project + page + block + segment chain. Returns the segment.

    Caller's session is the per-test rollback session, so this seed data
    disappears at end-of-test.
    """
    # Explicit per-stage flushes: SQLAlchemy's topological sort relies on
    # ORM relationships; we have FK columns only, so we sequence by hand.
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="test-project")
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
    return segment


@pytest.mark.asyncio
class TestT_1_4_1_Integration:
    async def test_first_revision_has_null_before_text(self, db_session: AsyncSession) -> None:
        segment = await _seed_segment(db_session, initial_text=None)

        revision = await create_revision(
            session=db_session,
            segment=segment,
            after_text="erste fassung",
            change_source=ChangeSource.OCR,
            operation_mode=OperationMode.AUTOMATIC,
        )

        assert revision.before_text is None
        assert revision.after_text == "erste fassung"
        assert revision.satz_uuid == segment.satz_uuid

    async def test_subsequent_revision_carries_prior_text_as_before(
        self, db_session: AsyncSession
    ) -> None:
        segment = await _seed_segment(db_session, initial_text="alt")
        rev = await create_revision(
            session=db_session,
            segment=segment,
            after_text="neu",
            change_source=ChangeSource.MANUAL,
            operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
        )
        assert rev.before_text == "alt"
        assert rev.after_text == "neu"

    async def test_segment_current_rev_uuid_advances_to_new_revision(
        self, db_session: AsyncSession
    ) -> None:
        segment = await _seed_segment(db_session)
        rev = await create_revision(
            session=db_session,
            segment=segment,
            after_text="x",
            change_source=ChangeSource.OCR,
            operation_mode=OperationMode.AUTOMATIC,
        )
        assert segment.current_rev_uuid == rev.rev_uuid

    async def test_segment_text_content_is_updated_to_after_text(
        self, db_session: AsyncSession
    ) -> None:
        segment = await _seed_segment(db_session, initial_text="alt")
        await create_revision(
            session=db_session,
            segment=segment,
            after_text="neu",
            change_source=ChangeSource.MANUAL,
            operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
        )
        assert segment.text_content == "neu"

    async def test_revision_row_persisted_with_canonical_columns(
        self, db_session: AsyncSession
    ) -> None:
        segment = await _seed_segment(db_session)
        rev = await create_revision(
            session=db_session,
            segment=segment,
            after_text="content",
            change_source=ChangeSource.OCR,
            operation_mode=OperationMode.AUTOMATIC,
        )
        # Round-trip from the DB to confirm the row really landed and that
        # the satz_uuid FK is the bridge.
        result = await db_session.execute(select(Revision).where(Revision.rev_uuid == rev.rev_uuid))
        loaded = result.scalar_one()
        assert loaded.satz_uuid == segment.satz_uuid
        assert loaded.change_source == ChangeSource.OCR.value
        assert loaded.author_uuid is None  # OCR-driven, no human actor

    async def test_manual_with_confirmation_unblocks_locked_segment(
        self, db_session: AsyncSession
    ) -> None:
        from tests.conftest import seed_account_uuid

        segment = await _seed_segment(
            db_session, lock_flag=LockFlag.MANUAL_EDITORIAL, initial_text="locked"
        )
        author_uuid = new_uuid()
        await seed_account_uuid(db_session, author_uuid)
        rev = await create_revision(
            session=db_session,
            segment=segment,
            after_text="edited",
            change_source=ChangeSource.MANUAL,
            operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
            author_uuid=author_uuid,
        )
        assert rev.after_text == "edited"

    async def test_two_revisions_form_a_chain_via_before_text(
        self, db_session: AsyncSession
    ) -> None:
        segment = await _seed_segment(db_session, initial_text="v0")
        rev1 = await create_revision(
            session=db_session,
            segment=segment,
            after_text="v1",
            change_source=ChangeSource.MANUAL,
            operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
        )
        rev2 = await create_revision(
            session=db_session,
            segment=segment,
            after_text="v2",
            change_source=ChangeSource.MANUAL,
            operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
        )
        assert rev1.before_text == "v0"
        assert rev1.after_text == "v1"
        assert rev2.before_text == "v1"
        assert rev2.after_text == "v2"
        assert segment.current_rev_uuid == rev2.rev_uuid
