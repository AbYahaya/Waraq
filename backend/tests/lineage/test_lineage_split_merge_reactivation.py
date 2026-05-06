"""T-4.2.2 — Lineage 1→n split, n→1 merge, reactivation.

Tests follow the layer pattern: signature/architectural, integration, then
cross-table discipline (decision_events delta = 0 across all four lineage
operations exercised here together with T-4.2.1's two).

Reactivation is the highest-risk piece (R-S1-02): missing reactivation breaks
revision history at re-segmentation boundaries. The plausibility heuristic
must be configurable, never hard-coded (R-S1-04).
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.lineage import (
    ReactivationConfig,
    find_reactivation_candidate,
    inactivate_segment,
    reactivate_segment,
    record_merge,
    record_one_to_one,
    record_split,
)
from waraq.schemas import Block, DecisionEvent, LogEntry, Page, Project, ProvenanceObject, Segment
from waraq.schemas.enums import POType, ScopeType


async def _seed_block(session: AsyncSession) -> Block:
    """Build a project + page + block; return the block. Caller adds segments."""
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="lineage-t422")
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
    return block


def _segment(
    block: Block,
    *,
    text: str | None,
    satz_index: int,
    active: bool = True,
) -> Segment:
    seg = Segment(
        satz_uuid=new_uuid(),
        block_uuid=block.block_uuid,
        satz_index=satz_index,
        lock_flag=LockFlag.NONE,
        text_content=text,
    )
    seg.active = active
    return seg


# --- Layer 1: signatures ---------------------------------------------------


class TestT_4_2_2_Signatures:
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

    @pytest.mark.parametrize(
        "func_obj",
        [record_split, record_merge, find_reactivation_candidate, reactivate_segment],
    )
    def test_no_decision_or_text_kwargs(self, func_obj: object) -> None:
        params = set(inspect.signature(func_obj).parameters)  # type: ignore[arg-type]
        leaked = self.FORBIDDEN_KWARGS & params
        assert leaked == set(), f"{getattr(func_obj, '__name__', func_obj)} leaked: {leaked}"

    def test_reactivation_config_thresholds_validated(self) -> None:
        # R-S1-04: thresholds are config-time values; out-of-range raises early.
        with pytest.raises(ValueError):
            ReactivationConfig(text_overlap_min=1.5, position_window=2)
        with pytest.raises(ValueError):
            ReactivationConfig(text_overlap_min=-0.1, position_window=2)
        with pytest.raises(ValueError):
            ReactivationConfig(text_overlap_min=0.7, position_window=-1)


# --- Layer 2: integration --------------------------------------------------


@pytest.mark.asyncio
class TestT_4_2_2_Split_OneToN:
    """LINEAGE-1zun-Aufspaltungs-Test."""

    async def test_split_inactivates_source_and_records_daughter_uuids(
        self, db_session: AsyncSession
    ) -> None:
        block = await _seed_block(db_session)
        source = _segment(block, text="Originaltext", satz_index=1)
        d1 = _segment(block, text="Originaltext Teil 1", satz_index=1)
        d2 = _segment(block, text="Teil 2", satz_index=2)
        db_session.add_all([source, d1, d2])
        await db_session.flush()

        po = await record_split(session=db_session, source=source, daughters=[d1, d2])
        await db_session.refresh(source)

        assert source.active is False
        assert d1.active is True
        assert d2.active is True
        assert po.payload["match_kind"] == "1ton"
        assert po.payload["automatisch"] is True
        assert po.payload["herkunft_uuid"] == [str(source.satz_uuid)]
        assert set(po.payload["ziel_uuid"]) == {str(d1.satz_uuid), str(d2.satz_uuid)}
        # PO is anchored at the source — that's the surviving identity-trail anchor.
        assert po.scope_uuid == source.satz_uuid
        assert str(po.scope_type) == ScopeType.SEGMENT.value

    async def test_split_writes_log_eintrag(self, db_session: AsyncSession) -> None:
        block = await _seed_block(db_session)
        source = _segment(block, text="A B C D", satz_index=1)
        d1 = _segment(block, text="A B", satz_index=1)
        d2 = _segment(block, text="C D", satz_index=2)
        db_session.add_all([source, d1, d2])
        await db_session.flush()

        await record_split(session=db_session, source=source, daughters=[d1, d2])

        entry = (
            await db_session.execute(
                select(LogEntry)
                .where(LogEntry.scope_uuid == source.satz_uuid)
                .where(LogEntry.operation_type == "lineage_split_1ton")
            )
        ).scalar_one()
        assert entry.result["match_kind"] == "1ton"
        assert entry.result["n_daughters"] == 2

    async def test_split_with_fewer_than_two_daughters_raises(
        self, db_session: AsyncSession
    ) -> None:
        block = await _seed_block(db_session)
        source = _segment(block, text="x", satz_index=1)
        d1 = _segment(block, text="x", satz_index=1)
        db_session.add_all([source, d1])
        await db_session.flush()

        with pytest.raises(ValueError, match="at least 2 daughters"):
            await record_split(session=db_session, source=source, daughters=[d1])


@pytest.mark.asyncio
class TestT_4_2_2_Merge_NToOne:
    """LINEAGE-nzu1-Zusammenfuehrungs-Test."""

    async def test_merge_inactivates_all_sources_and_records_target(
        self, db_session: AsyncSession
    ) -> None:
        block = await _seed_block(db_session)
        s1 = _segment(block, text="Erster Teil", satz_index=1)
        s2 = _segment(block, text="Zweiter Teil", satz_index=2)
        target = _segment(block, text="Erster Teil Zweiter Teil", satz_index=1)
        db_session.add_all([s1, s2, target])
        await db_session.flush()

        po = await record_merge(session=db_session, sources=[s1, s2], target=target)
        await db_session.refresh(s1)
        await db_session.refresh(s2)

        assert s1.active is False
        assert s2.active is False
        assert target.active is True
        assert po.payload["match_kind"] == "nto1"
        assert set(po.payload["herkunft_uuid"]) == {str(s1.satz_uuid), str(s2.satz_uuid)}
        assert po.payload["ziel_uuid"] == [str(target.satz_uuid)]
        # PO is anchored at the target — that's the surviving Segment.
        assert po.scope_uuid == target.satz_uuid

    async def test_merge_with_fewer_than_two_sources_raises(self, db_session: AsyncSession) -> None:
        block = await _seed_block(db_session)
        s1 = _segment(block, text="x", satz_index=1)
        target = _segment(block, text="x", satz_index=1)
        db_session.add_all([s1, target])
        await db_session.flush()

        with pytest.raises(ValueError, match="at least 2 sources"):
            await record_merge(session=db_session, sources=[s1], target=target)


@pytest.mark.asyncio
class TestT_4_2_2_Reactivation:
    """LINEAGE-Reaktivierungs-Test + R-S1-04 (config thresholds)."""

    async def test_finds_inactive_match_when_text_and_position_align(
        self, db_session: AsyncSession
    ) -> None:
        block = await _seed_block(db_session)
        # An old Segment that disappeared in a previous re-segmentation pass.
        inactive = _segment(block, text="alpha beta gamma delta", satz_index=3, active=False)
        # Distractor: same block but very different text.
        distractor = _segment(block, text="zeta eta theta", satz_index=10, active=False)
        db_session.add_all([inactive, distractor])
        await db_session.flush()

        candidate = await find_reactivation_candidate(
            session=db_session,
            block_uuid=block.block_uuid,
            candidate_text="alpha beta gamma",
            candidate_satz_index=3,
            config=ReactivationConfig(text_overlap_min=0.5, position_window=1),
        )

        assert candidate is not None
        assert candidate.satz_uuid == inactive.satz_uuid

    async def test_returns_none_when_no_inactive_above_threshold(
        self, db_session: AsyncSession
    ) -> None:
        block = await _seed_block(db_session)
        inactive = _segment(block, text="alpha beta gamma", satz_index=3, active=False)
        db_session.add(inactive)
        await db_session.flush()

        # Threshold so high (1.0 = identical sets) that "alpha beta gamma" vs
        # "completely unrelated" cannot match.
        candidate = await find_reactivation_candidate(
            session=db_session,
            block_uuid=block.block_uuid,
            candidate_text="completely unrelated text",
            candidate_satz_index=3,
            config=ReactivationConfig(text_overlap_min=0.7, position_window=2),
        )

        assert candidate is None

    async def test_returns_none_when_position_outside_window(
        self, db_session: AsyncSession
    ) -> None:
        block = await _seed_block(db_session)
        inactive = _segment(block, text="alpha beta gamma", satz_index=3, active=False)
        db_session.add(inactive)
        await db_session.flush()

        # Same text but candidate is far away — position guard kicks in.
        candidate = await find_reactivation_candidate(
            session=db_session,
            block_uuid=block.block_uuid,
            candidate_text="alpha beta gamma",
            candidate_satz_index=20,
            config=ReactivationConfig(text_overlap_min=0.5, position_window=1),
        )

        assert candidate is None

    async def test_threshold_is_config_driven_not_hard_coded(
        self, db_session: AsyncSession
    ) -> None:
        # R-S1-04: same DB state; flipping the config flips the matching outcome.
        # If the threshold were hard-coded, this couldn't work.
        block = await _seed_block(db_session)
        inactive = _segment(block, text="alpha beta", satz_index=1, active=False)
        db_session.add(inactive)
        await db_session.flush()

        loose = await find_reactivation_candidate(
            session=db_session,
            block_uuid=block.block_uuid,
            candidate_text="alpha gamma",  # Jaccard = 1/3 ≈ 0.33
            candidate_satz_index=1,
            config=ReactivationConfig(text_overlap_min=0.3, position_window=2),
        )
        strict = await find_reactivation_candidate(
            session=db_session,
            block_uuid=block.block_uuid,
            candidate_text="alpha gamma",
            candidate_satz_index=1,
            config=ReactivationConfig(text_overlap_min=0.9, position_window=2),
        )

        assert loose is not None
        assert loose.satz_uuid == inactive.satz_uuid
        assert strict is None

    async def test_reactivate_flips_active_and_writes_lineage_event(
        self, db_session: AsyncSession
    ) -> None:
        block = await _seed_block(db_session)
        inactive = _segment(block, text="alpha beta", satz_index=1, active=False)
        db_session.add(inactive)
        await db_session.flush()

        po = await reactivate_segment(session=db_session, segment=inactive)
        await db_session.refresh(inactive)

        assert inactive.active is True
        assert po.payload["match_kind"] == "reactivation"
        assert po.payload["automatisch"] is True
        # Both arrays carry the reactivated UUID — continuity across the gap.
        assert po.payload["herkunft_uuid"] == [str(inactive.satz_uuid)]
        assert po.payload["ziel_uuid"] == [str(inactive.satz_uuid)]
        assert po.scope_uuid == inactive.satz_uuid

    async def test_reactivate_writes_log_eintrag(self, db_session: AsyncSession) -> None:
        block = await _seed_block(db_session)
        inactive = _segment(block, text="x", satz_index=1, active=False)
        db_session.add(inactive)
        await db_session.flush()

        await reactivate_segment(session=db_session, segment=inactive)

        entry = (
            await db_session.execute(
                select(LogEntry)
                .where(LogEntry.scope_uuid == inactive.satz_uuid)
                .where(LogEntry.operation_type == "lineage_reactivation")
            )
        ).scalar_one()
        assert entry.result["match_kind"] == "reactivation"

    async def test_reactivate_refuses_already_active_segment(
        self, db_session: AsyncSession
    ) -> None:
        block = await _seed_block(db_session)
        active_seg = _segment(block, text="x", satz_index=1, active=True)
        db_session.add(active_seg)
        await db_session.flush()

        with pytest.raises(ValueError, match="already active"):
            await reactivate_segment(session=db_session, segment=active_seg)

    async def test_round_trip_inactivate_then_reactivate_preserves_uuid(
        self, db_session: AsyncSession
    ) -> None:
        # R-S1-03: Inactive Segment treated as "new" on next layout pass.
        # Round-trip exercises 1→0 followed by reactivation; same UUID.
        block = await _seed_block(db_session)
        seg = _segment(block, text="alpha beta gamma", satz_index=2)
        db_session.add(seg)
        await db_session.flush()
        original_uuid = seg.satz_uuid

        await inactivate_segment(session=db_session, segment=seg)
        await db_session.refresh(seg)
        assert seg.active is False

        candidate = await find_reactivation_candidate(
            session=db_session,
            block_uuid=block.block_uuid,
            candidate_text="alpha beta gamma",
            candidate_satz_index=2,
            config=ReactivationConfig(text_overlap_min=0.5, position_window=1),
        )
        assert candidate is not None
        assert candidate.satz_uuid == original_uuid

        await reactivate_segment(session=db_session, segment=candidate)
        await db_session.refresh(seg)

        # Same UUID survives the whole cycle.
        assert seg.satz_uuid == original_uuid
        assert seg.active is True


# --- Layer 3: cross-table discipline (combined T-4.2.1 + T-4.2.2) ---------


@pytest.mark.asyncio
class TestT_4_2_KeinDecisionEventAcrossAllFourTransitions:
    """LINEAGE-Kein-Decision-Event-Automatisch-Test (canonical wording).

    Run all four canonical lineage operations (1→1, 1→0, 1→n, n→1) plus
    reactivation and assert decision_events delta = 0.
    """

    async def test_no_decision_event_for_any_lineage_path(self, db_session: AsyncSession) -> None:
        block = await _seed_block(db_session)

        # 1→1 candidate
        keep = _segment(block, text="keep", satz_index=1)
        # 1→0 candidate
        drop = _segment(block, text="drop", satz_index=2)
        # 1→n source + daughters
        src_split = _segment(block, text="parent", satz_index=3)
        d1 = _segment(block, text="parent first", satz_index=3)
        d2 = _segment(block, text="last", satz_index=4)
        # n→1 sources + target
        m1 = _segment(block, text="merge a", satz_index=5)
        m2 = _segment(block, text="merge b", satz_index=6)
        merged = _segment(block, text="merge a merge b", satz_index=5)
        # reactivation candidate
        ghost = _segment(block, text="ghost token", satz_index=10, active=False)
        db_session.add_all([keep, drop, src_split, d1, d2, m1, m2, merged, ghost])
        await db_session.flush()

        before = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()

        await record_one_to_one(session=db_session, satz_uuid=keep.satz_uuid)
        await inactivate_segment(session=db_session, segment=drop)
        await record_split(session=db_session, source=src_split, daughters=[d1, d2])
        await record_merge(session=db_session, sources=[m1, m2], target=merged)
        await reactivate_segment(session=db_session, segment=ghost)

        after = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        assert after == before

        # Sanity: the lineage operations *did* land — five LINEAGE_EVENT-POs.
        po_count = (
            await db_session.execute(
                select(func.count())
                .select_from(ProvenanceObject)
                .where(
                    ProvenanceObject.po_type == POType.LINEAGE_EVENT.value,
                )
            )
        ).scalar_one()
        assert po_count == 5
