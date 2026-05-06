"""T-4.2.1 — LINEAGE service: 1→1 and 1→0.

Three layers:

1. Architectural — the lineage service exposes only `record_one_to_one` and
   `inactivate_segment`; the signatures carry no decision-shaped kwargs and
   no text-change kwargs. Lineage-as-decision-event (DBB Abkürzung 8) is
   refused at the signature.

2. Integration — both operations write the LINEAGE_EVENT-PO with the
   canonical payload shape (`match_kind`, `automatisch=True`, `herkunft_uuid`,
   `ziel_uuid`) plus a Log-Eintrag. 1→0 flips `active = false` while keeping
   the row queryable (H-5).

3. Cross-table discipline — neither operation creates a Decision Event.
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.lineage import inactivate_segment, record_one_to_one
from waraq.schemas import Block, DecisionEvent, LogEntry, Page, Project, ProvenanceObject, Segment
from waraq.schemas.enums import POType, ScopeType

# --- Layer 1: signature-level architectural tests -------------------------


class TestT_4_2_1_Signatures:
    """Sprint 1 R-S1-01 / DBB Abkürzung 8: lineage matching is a system event,
    not a decision. The service surface itself must refuse decision-shaped
    kwargs so callers cannot trigger the failure mode."""

    FORBIDDEN_KWARGS = frozenset(
        {
            "decision_type",
            "decision_source",
            "before_text",
            "after_text",
            "change_source",
            "rev_uuid",
        }
    )

    def test_record_one_to_one_signature_has_no_decision_kwargs(self) -> None:
        params = set(inspect.signature(record_one_to_one).parameters)
        leaked = self.FORBIDDEN_KWARGS & params
        assert leaked == set(), f"record_one_to_one leaked decision/text kwargs: {leaked}"

    def test_inactivate_segment_signature_has_no_decision_kwargs(self) -> None:
        params = set(inspect.signature(inactivate_segment).parameters)
        leaked = self.FORBIDDEN_KWARGS & params
        assert leaked == set(), f"inactivate_segment leaked decision/text kwargs: {leaked}"

    def test_module_exposes_only_canonical_lineage_entrypoints(self) -> None:
        import inspect as _inspect
        import types

        import waraq.lineage as lineage_module

        # Lock in the full Sprint 1 lineage surface across T-4.2.1 (1→1, 1→0)
        # and T-4.2.2 (1→n, n→1, reactivation + plausibility helper). Any new
        # operation must be added here deliberately so the no-decision-event
        # discipline can be re-checked for it.
        functions = {
            name
            for name, obj in vars(lineage_module).items()
            if not name.startswith("_")
            and callable(obj)
            and not isinstance(obj, type)
            and not isinstance(obj, types.ModuleType)
            and _inspect.getmodule(obj) is not None
            and _inspect.getmodule(obj).__name__.startswith("waraq.lineage")  # type: ignore[union-attr]
        }
        assert functions == {
            "record_one_to_one",
            "inactivate_segment",
            "record_split",
            "record_merge",
            "reactivate_segment",
            "find_reactivation_candidate",
        }, f"waraq.lineage exposes unexpected operations: {functions}"


# --- Layer 2 + 3: integration + cross-table discipline --------------------


async def _seed_segment(session: AsyncSession) -> Segment:
    """Insert a project + page + block + segment chain. Returns the segment."""
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="lineage-test")
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
        text_content="surviving content",
    )
    session.add(segment)
    await session.flush()
    return segment


@pytest.mark.asyncio
class TestT_4_2_1_OneToOne:
    """LINEAGE-1zu1-Test: existing satz_uuid preserved on re-segmentation."""

    async def test_writes_lineage_event_po_with_canonical_payload(
        self, db_session: AsyncSession
    ) -> None:
        segment = await _seed_segment(db_session)

        po = await record_one_to_one(session=db_session, satz_uuid=segment.satz_uuid)

        loaded = (
            await db_session.execute(
                select(ProvenanceObject).where(ProvenanceObject.po_uuid == po.po_uuid)
            )
        ).scalar_one()
        assert str(loaded.po_type) == POType.LINEAGE_EVENT.value
        assert str(loaded.scope_type) == ScopeType.SEGMENT.value
        assert loaded.scope_uuid == segment.satz_uuid
        assert loaded.payload["match_kind"] == "1to1"
        assert loaded.payload["automatisch"] is True
        assert loaded.payload["herkunft_uuid"] == [str(segment.satz_uuid)]
        assert loaded.payload["ziel_uuid"] == [str(segment.satz_uuid)]

    async def test_lineage_event_po_is_system_authored(self, db_session: AsyncSession) -> None:
        # CLAUDE.md §5.5: LINEAGE_EVENT-POs are canonically system-authored.
        # No human actor goes on them — this protects the user-decision audit
        # trail from being polluted by automatic matching.
        segment = await _seed_segment(db_session)
        po = await record_one_to_one(session=db_session, satz_uuid=segment.satz_uuid)
        assert po.author_uuid is None

    async def test_writes_log_eintrag_for_one_to_one(self, db_session: AsyncSession) -> None:
        segment = await _seed_segment(db_session)
        await record_one_to_one(session=db_session, satz_uuid=segment.satz_uuid)

        result = await db_session.execute(
            select(LogEntry)
            .where(LogEntry.scope_uuid == segment.satz_uuid)
            .where(LogEntry.operation_type == "lineage_match_1to1")
        )
        entry = result.scalar_one()
        assert entry.result["match_kind"] == "1to1"
        assert str(entry.scope_type) == ScopeType.SEGMENT.value

    async def test_does_not_mutate_segment_state(self, db_session: AsyncSession) -> None:
        segment = await _seed_segment(db_session)
        original_text = segment.text_content
        original_active = segment.active

        await record_one_to_one(session=db_session, satz_uuid=segment.satz_uuid)
        await db_session.refresh(segment)

        assert segment.text_content == original_text
        assert segment.active == original_active

    async def test_creates_no_decision_event(self, db_session: AsyncSession) -> None:
        # Sprint 1 R-S1-01 / DBB Abkürzung 8.
        segment = await _seed_segment(db_session)
        before = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()

        await record_one_to_one(session=db_session, satz_uuid=segment.satz_uuid)

        after = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        assert after == before


@pytest.mark.asyncio
class TestT_4_2_1_OneToZero:
    """LINEAGE-1zu0-Inaktivierungs-Test: disappearing Segment marked
    `active = false`, UUID retained, queryable post-inactivation."""

    async def test_inactivation_flips_active_flag(self, db_session: AsyncSession) -> None:
        segment = await _seed_segment(db_session)
        assert segment.active is True

        await inactivate_segment(session=db_session, segment=segment)
        await db_session.refresh(segment)

        assert segment.active is False

    async def test_inactivation_preserves_satz_uuid_and_row(self, db_session: AsyncSession) -> None:
        # H-5: inactive UUID stays queryable; the row is never deleted.
        segment = await _seed_segment(db_session)
        original_satz_uuid = segment.satz_uuid

        await inactivate_segment(session=db_session, segment=segment)

        loaded = (
            await db_session.execute(select(Segment).where(Segment.satz_uuid == original_satz_uuid))
        ).scalar_one()
        assert loaded.satz_uuid == original_satz_uuid
        assert loaded.active is False
        # Text content and FK chain are untouched — only the active flag changes.
        assert loaded.text_content == "surviving content"
        assert loaded.block_uuid == segment.block_uuid

    async def test_writes_lineage_event_po_with_empty_ziel(self, db_session: AsyncSession) -> None:
        segment = await _seed_segment(db_session)
        po = await inactivate_segment(session=db_session, segment=segment)

        loaded = (
            await db_session.execute(
                select(ProvenanceObject).where(ProvenanceObject.po_uuid == po.po_uuid)
            )
        ).scalar_one()
        assert str(loaded.po_type) == POType.LINEAGE_EVENT.value
        assert str(loaded.scope_type) == ScopeType.SEGMENT.value
        assert loaded.scope_uuid == segment.satz_uuid
        assert loaded.payload["match_kind"] == "1to0"
        assert loaded.payload["automatisch"] is True
        assert loaded.payload["herkunft_uuid"] == [str(segment.satz_uuid)]
        assert loaded.payload["ziel_uuid"] == []

    async def test_writes_log_eintrag_for_one_to_zero(self, db_session: AsyncSession) -> None:
        segment = await _seed_segment(db_session)
        await inactivate_segment(session=db_session, segment=segment)

        result = await db_session.execute(
            select(LogEntry)
            .where(LogEntry.scope_uuid == segment.satz_uuid)
            .where(LogEntry.operation_type == "lineage_inactivate_1to0")
        )
        entry = result.scalar_one()
        assert entry.result["match_kind"] == "1to0"

    async def test_creates_no_decision_event(self, db_session: AsyncSession) -> None:
        segment = await _seed_segment(db_session)
        before = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()

        await inactivate_segment(session=db_session, segment=segment)

        after = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        assert after == before


@pytest.mark.asyncio
class TestT_4_2_1_KeinDecisionEventAutomatisch:
    """LINEAGE-Kein-Decision-Event-Automatisch-Test (T-4.2.1 portion).

    DBB Abkürzung 8 names this exact failure mode. Run BOTH 1→1 and 1→0
    operations and assert the decision_events table delta is zero. (T-4.2.2
    extends this test family to cover 1→n / n→1 / reactivation.)"""

    async def test_combined_1to1_and_1to0_produce_no_decision_events(
        self, db_session: AsyncSession
    ) -> None:
        seg_keep = await _seed_segment(db_session)
        seg_drop = await _seed_segment(db_session)
        before = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()

        await record_one_to_one(session=db_session, satz_uuid=seg_keep.satz_uuid)
        await inactivate_segment(session=db_session, segment=seg_drop)

        after = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        assert after == before
