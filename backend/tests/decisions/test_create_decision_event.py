"""T-1.4.2 — create_decision_event service tests.

Three layers:
1. Architectural — the service signature itself enforces three-tables
   separation (no text-change kwargs at all).
2. Integration — round-trip writes against live Postgres for every canonical
   scope_type and every canonical decision_source.
3. Cross-table discipline — writing a Decision Event must not mutate any
   Segment field, must not produce a Revision row, must not produce a
   Log-Eintrag row.
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.decisions import create_decision_event
from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag, OperationMode
from waraq.revision import create_revision
from waraq.schemas import (
    Block,
    DecisionEvent,
    LogEntry,
    Page,
    Project,
    Revision,
    Segment,
)
from waraq.schemas.enums import ChangeSource, DecisionSource, ScopeType

# --- Layer 1: signature-level architectural test --------------------------


class TestT_1_4_2_SignatureForbidsTextChangeKwargs:
    """Three-tables separation (DBB Abkürzung 3) starts at the function
    signature: there is no way to ask `create_decision_event` to also do a
    text change. If someone tries to add `before_text` or `after_text` here
    later, this test fails first."""

    FORBIDDEN_KWARGS = frozenset(
        {"before_text", "after_text", "change_source", "rev_uuid", "current_rev_uuid"}
    )

    def test_no_text_change_kwargs_in_signature(self) -> None:
        params = set(inspect.signature(create_decision_event).parameters)
        leaked = self.FORBIDDEN_KWARGS & params
        assert leaked == set(), f"create_decision_event leaked text-change kwargs: {leaked}"

    def test_required_canonical_kwargs_present(self) -> None:
        params = set(inspect.signature(create_decision_event).parameters)
        # The canonical Decision Event surface from CAB §5.2.
        required = {"scope_type", "scope_uuid", "decision_type", "decision_source"}
        assert required <= params


# --- Layer 2: integration ---------------------------------------------------


@pytest.mark.asyncio
class TestT_1_4_2_Integration:
    async def test_writes_a_row_with_canonical_fields(self, db_session: AsyncSession) -> None:
        from tests.conftest import seed_account_uuid

        scope_uuid = new_uuid()
        actor_uuid = new_uuid()
        await seed_account_uuid(db_session, actor_uuid)

        de = await create_decision_event(
            session=db_session,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=scope_uuid,
            decision_type="ocr_accept",
            decision_source=DecisionSource.OCR_REVIEW,
            content={"reason": "high confidence"},
            actor_uuid=actor_uuid,
        )

        result = await db_session.execute(
            select(DecisionEvent).where(DecisionEvent.decision_event_uuid == de.decision_event_uuid)
        )
        loaded = result.scalar_one()
        assert str(loaded.scope_type) == ScopeType.SEGMENT.value
        assert loaded.scope_uuid == scope_uuid
        assert loaded.decision_type == "ocr_accept"
        assert str(loaded.decision_source) == DecisionSource.OCR_REVIEW.value
        assert loaded.content == {"reason": "high confidence"}

    async def test_content_defaults_to_empty_dict_when_omitted(
        self, db_session: AsyncSession
    ) -> None:
        de = await create_decision_event(
            session=db_session,
            scope_type=ScopeType.PROJECT,
            scope_uuid=new_uuid(),
            decision_type="export_confirm",
            decision_source=DecisionSource.EXPORT_CONFIRMATION,
        )
        assert de.content == {}

    async def test_actor_uuid_optional(self, db_session: AsyncSession) -> None:
        de = await create_decision_event(
            session=db_session,
            scope_type=ScopeType.PROJECT,
            scope_uuid=new_uuid(),
            decision_type="system_decision",
            decision_source=DecisionSource.STYLE_MANAGEMENT,
        )
        assert de.actor_uuid is None

    @pytest.mark.parametrize("scope", list(ScopeType))
    async def test_all_five_scope_types_round_trip(
        self, db_session: AsyncSession, scope: ScopeType
    ) -> None:
        de = await create_decision_event(
            session=db_session,
            scope_type=scope,
            scope_uuid=new_uuid(),
            decision_type=f"test_{scope.value}",
            decision_source=DecisionSource.LOCK_MANAGEMENT,
        )
        assert str(de.scope_type) == scope.value

    @pytest.mark.parametrize("source", list(DecisionSource))
    async def test_all_ten_decision_sources_round_trip(
        self, db_session: AsyncSession, source: DecisionSource
    ) -> None:
        de = await create_decision_event(
            session=db_session,
            scope_type=ScopeType.PROJECT,
            scope_uuid=new_uuid(),
            decision_type="t",
            decision_source=source,
        )
        assert str(de.decision_source) == source.value

    async def test_decision_event_uuid_is_unique_per_call(self, db_session: AsyncSession) -> None:
        scope_uuid = new_uuid()
        de1 = await create_decision_event(
            session=db_session,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=scope_uuid,
            decision_type="ocr_accept",
            decision_source=DecisionSource.OCR_REVIEW,
        )
        de2 = await create_decision_event(
            session=db_session,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=scope_uuid,
            decision_type="ocr_accept",
            decision_source=DecisionSource.OCR_REVIEW,
        )
        assert de1.decision_event_uuid != de2.decision_event_uuid


# --- Layer 3: cross-table discipline ---------------------------------------


async def _seed_segment(session: AsyncSession) -> Segment:
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="cross-table-test")
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
        lock_flag=LockFlag.NONE,
        text_content="initial",
    )
    session.add(segment)
    await session.flush()
    return segment


@pytest.mark.asyncio
class TestT_1_4_2_CrossTableDiscipline:
    async def test_does_not_create_revision_or_log_entry(self, db_session: AsyncSession) -> None:
        segment = await _seed_segment(db_session)
        before_revisions = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()
        before_logs = (
            await db_session.execute(select(func.count()).select_from(LogEntry))
        ).scalar_one()

        await create_decision_event(
            session=db_session,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=segment.satz_uuid,
            decision_type="lock_set",
            decision_source=DecisionSource.LOCK_MANAGEMENT,
            content={"new_flag": "manual_local"},
        )

        after_revisions = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()
        after_logs = (
            await db_session.execute(select(func.count()).select_from(LogEntry))
        ).scalar_one()

        assert after_revisions == before_revisions
        assert after_logs == before_logs

    async def test_does_not_mutate_segment_state(self, db_session: AsyncSession) -> None:
        segment = await _seed_segment(db_session)
        # Establish a real Revision so current_rev_uuid is non-null and we
        # can detect any unintended mutation.
        rev = await create_revision(
            session=db_session,
            segment=segment,
            after_text="seeded",
            change_source=ChangeSource.OCR,
            operation_mode=OperationMode.AUTOMATIC,
        )
        original_lock = segment.lock_flag
        original_text = segment.text_content
        original_rev_uuid = segment.current_rev_uuid
        assert original_rev_uuid == rev.rev_uuid

        await create_decision_event(
            session=db_session,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=segment.satz_uuid,
            decision_type="ocr_accept",
            decision_source=DecisionSource.OCR_REVIEW,
            content={"verdict": "accepted"},
        )

        # Refresh from DB to be sure the DB itself agrees with us.
        await db_session.refresh(segment)
        assert segment.lock_flag == original_lock
        assert segment.text_content == original_text
        assert segment.current_rev_uuid == original_rev_uuid
