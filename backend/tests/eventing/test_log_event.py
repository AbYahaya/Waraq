"""T-1.5.1 — log_event service tests.

Three layers:
1. Architectural — signature blocks both Decision-Event-shaped kwargs
   (Abkürzung 3 surface) and text-change kwargs (H-4 surface).
2. Integration — round-trip writes against live Postgres.
3. Cross-table discipline — writing a Log-Eintrag must not produce a
   Decision Event row (the §5.5 lineage-as-decision failure mode).
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.eventing import log_event
from waraq.identity import new_uuid
from waraq.schemas import DecisionEvent, LogEntry, Revision
from waraq.schemas.enums import ScopeType

# --- Layer 1: signature-level architectural test --------------------------


class TestT_1_5_1_SignatureForbidsForeignKwargs:
    """Three-tables separation starts at the function signature.

    `log_event` must not accept Decision-Event-shaped kwargs (otherwise
    lineage matching could be smuggled into decision_events) and must not
    accept text-change kwargs (otherwise H-4 could be bypassed)."""

    DECISION_KWARGS = frozenset({"decision_type", "decision_source"})
    TEXT_CHANGE_KWARGS = frozenset(
        {"before_text", "after_text", "change_source", "rev_uuid", "current_rev_uuid"}
    )

    def test_no_decision_event_kwargs(self) -> None:
        params = set(inspect.signature(log_event).parameters)
        leaked = self.DECISION_KWARGS & params
        assert leaked == set(), f"log_event leaked decision-event kwargs: {leaked}"

    def test_no_text_change_kwargs(self) -> None:
        params = set(inspect.signature(log_event).parameters)
        leaked = self.TEXT_CHANGE_KWARGS & params
        assert leaked == set(), f"log_event leaked text-change kwargs: {leaked}"

    def test_required_canonical_kwarg_present(self) -> None:
        # CAB §5.2: a Log-Eintrag has at minimum operation_type and result.
        params = set(inspect.signature(log_event).parameters)
        assert "operation_type" in params


# --- Layer 2: integration ---------------------------------------------------


@pytest.mark.asyncio
class TestT_1_5_1_Integration:
    async def test_writes_a_row_with_canonical_fields(self, db_session: AsyncSession) -> None:
        scope_uuid = new_uuid()
        entry = await log_event(
            session=db_session,
            operation_type="ocr_run_started",
            result={"job_uuid": str(new_uuid())},
            scope_type=ScopeType.PAGE,
            scope_uuid=scope_uuid,
        )

        loaded = (
            await db_session.execute(select(LogEntry).where(LogEntry.log_id == entry.log_id))
        ).scalar_one()
        assert loaded.operation_type == "ocr_run_started"
        assert loaded.scope_type == ScopeType.PAGE.value
        assert loaded.scope_uuid == scope_uuid
        assert "job_uuid" in loaded.result

    async def test_result_defaults_to_empty_dict(self, db_session: AsyncSession) -> None:
        entry = await log_event(
            session=db_session,
            operation_type="checkpoint_written",
        )
        assert entry.result == {}

    async def test_scope_fields_optional(self, db_session: AsyncSession) -> None:
        entry = await log_event(
            session=db_session,
            operation_type="system_event",
        )
        assert entry.scope_type is None
        assert entry.scope_uuid is None

    async def test_log_id_is_unique_per_call(self, db_session: AsyncSession) -> None:
        e1 = await log_event(session=db_session, operation_type="x")
        e2 = await log_event(session=db_session, operation_type="x")
        assert e1.log_id != e2.log_id

    async def test_lineage_event_use_case(self, db_session: AsyncSession) -> None:
        """Per CLAUDE.md §5.5, lineage events are written here, not to
        decision_events. Verify the canonical lineage shape round-trips."""
        segment_uuid = new_uuid()
        entry = await log_event(
            session=db_session,
            operation_type="lineage_match_1to1",
            result={
                "predecessor_satz_uuid": str(new_uuid()),
                "successor_satz_uuid": str(segment_uuid),
                "match_kind": "1to1",
            },
            scope_type=ScopeType.SEGMENT,
            scope_uuid=segment_uuid,
        )
        loaded = (
            await db_session.execute(select(LogEntry).where(LogEntry.log_id == entry.log_id))
        ).scalar_one()
        assert loaded.operation_type == "lineage_match_1to1"
        assert loaded.result["match_kind"] == "1to1"


# --- Layer 3: cross-table discipline ---------------------------------------


@pytest.mark.asyncio
class TestT_1_5_1_CrossTableDiscipline:
    async def test_does_not_create_decision_event_or_revision(
        self, db_session: AsyncSession
    ) -> None:
        before_decisions = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        before_revisions = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()

        await log_event(
            session=db_session,
            operation_type="lineage_match_1to0",
            result={"predecessor_satz_uuid": str(new_uuid())},
            scope_type=ScopeType.SEGMENT,
            scope_uuid=new_uuid(),
        )

        after_decisions = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        after_revisions = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()

        assert after_decisions == before_decisions
        assert after_revisions == before_revisions
