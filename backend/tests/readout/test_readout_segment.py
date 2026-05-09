"""T-10.1.1 mandatory tests — Sprint 6 §4 (segment-scoped readout).

Test ID coverage:
- Get-Pos-For-Segment-Scope-Filter-Test
- Get-Pos-For-Segment-Page-Scoped-Excluded-Test
- Get-Pos-For-Segment-Read-Only-Test
- Get-Export-Events-For-Segment-Via-Snapshot-Test
- Get-Export-Events-For-Segment-Lineage-Aware-Test
- Get-Export-Events-Werkweite-Referenz-Marker-Test
- Get-Export-Events-No-Direct-FK-Shortcut-Test
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.readout._helpers import (
    seed_export_event,
    seed_po,
    seed_project_with_account,
    seed_segment_export,
    seed_segment_with_revision,
)
from waraq.invariant.enums import OperationMode
from waraq.readout import (
    SegmentExportEventRef,
    get_export_events_for_segment,
    get_pos_for_segment,
)
from waraq.revision import create_revision
from waraq.schemas import Block, DecisionEvent, ProvenanceObject, Revision
from waraq.schemas.enums import ChangeSource, POType, ScopeType

# --- Get-Pos-For-Segment-Scope-Filter-Test ---------------------------


@pytest.mark.asyncio
class TestGetPosForSegmentScopeFilter:
    async def test_only_returns_segment_scoped_pos_with_matching_uuid(
        self, db_session: AsyncSession
    ) -> None:
        project, _ = await seed_project_with_account(db_session)
        seg_a = await seed_segment_with_revision(db_session, project=project, text="src\n---\ntgt")
        seg_b = await seed_segment_with_revision(
            db_session, project=project, text="x", page_index=2, satz_index=1
        )
        # Segment-scoped POs on seg_a (matches) and seg_b (no match).
        po_a = await seed_po(
            db_session,
            po_type=POType.OCR,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg_a.satz_uuid,
            payload={"label": "ocr_a"},
        )
        await seed_po(
            db_session,
            po_type=POType.OCR,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg_b.satz_uuid,
            payload={"label": "ocr_b"},
        )
        # Project-scoped PO (must be excluded).
        await seed_po(
            db_session,
            po_type=POType.EXPORT_EVENT,
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            payload={"revision_snapshot": []},
        )

        result = await get_pos_for_segment(session=db_session, satz_uuid=seg_a.satz_uuid)
        assert len(result) == 1
        assert result[0].po_uuid == po_a.po_uuid


# --- Get-Pos-For-Segment-Page-Scoped-Excluded-Test --------------------


@pytest.mark.asyncio
class TestGetPosForSegmentPageScopedExcluded:
    async def test_page_scoped_scan_po_excluded(self, db_session: AsyncSession) -> None:
        project, _ = await seed_project_with_account(db_session)
        seg = await seed_segment_with_revision(db_session, project=project, text="x")
        block = await db_session.get(Block, seg.block_uuid)
        # Page-scoped SCAN-PO (T-3.1.2) — must NOT appear in the segment query.
        await seed_po(
            db_session,
            po_type=POType.SCAN,
            scope_type=ScopeType.PAGE,
            scope_uuid=block.page_uuid,
            payload={"sha256": "abc"},
        )
        result = await get_pos_for_segment(session=db_session, satz_uuid=seg.satz_uuid)
        assert result == []


# --- Get-Pos-For-Segment-Read-Only-Test -------------------------------


@pytest.mark.asyncio
class TestGetPosForSegmentReadOnly:
    async def test_query_writes_nothing(self, db_session: AsyncSession) -> None:
        project, _ = await seed_project_with_account(db_session)
        seg = await seed_segment_with_revision(db_session, project=project, text="x")
        rev_count_before = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()
        de_count_before = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        po_count_before = (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one()

        await get_pos_for_segment(session=db_session, satz_uuid=seg.satz_uuid)

        assert (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one() == rev_count_before
        assert (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one() == de_count_before
        assert (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one() == po_count_before


# --- Get-Export-Events-For-Segment-Via-Snapshot-Test ------------------


class TestGetExportEventsViaSnapshot:
    """Sprint 6 §A HG-S6-1: lookup is strictly via revision_snapshot[],
    NEVER via a segment-FK on the EXPORT_EVENT row.

    Three structural assertions:
    1. The EXPORT_EVENT-PO row schema (provenance_objects) carries no
       segment FK.
    2. The implementation references `revision_snapshot` and reads from
       payload, not from any FK on the row itself.
    3. No `satz_uuid` column / FK is added to provenance_objects.
    """

    def test_provenance_table_has_no_segment_fk(self) -> None:
        col_names = {c.name for c in ProvenanceObject.__table__.columns}
        # The Provenance row has scope_type + scope_uuid (generic) and a
        # JSONB payload. No `satz_uuid` column exists.
        assert "satz_uuid" not in col_names
        # No FK on provenance to segments.
        fk_targets = {fk.column.table.name for fk in ProvenanceObject.__table__.foreign_keys}
        assert "segments" not in fk_targets

    def test_implementation_reads_revision_snapshot(self) -> None:
        from waraq.readout import service as svc

        src = inspect.getsource(svc.get_export_events_for_segment)
        assert "revision_snapshot" in src
        # Must NOT join to segments via a direct FK.
        assert "Segment.satz_uuid" not in src
        assert "satz_uuid ==" not in src


@pytest.mark.asyncio
class TestGetExportEventsFromRealRunExportJob:
    async def test_real_export_event_surfaces_via_snapshot(self, db_session: AsyncSession) -> None:
        project, account_uuid = await seed_project_with_account(db_session)
        seg = await seed_segment_with_revision(db_session, project=project, text="src\n---\ntgt")
        po = await seed_segment_export(
            db_session, project=project, account_uuid=account_uuid, segment=seg
        )
        refs = await get_export_events_for_segment(session=db_session, satz_uuid=seg.satz_uuid)
        assert len(refs) == 1
        assert refs[0].po.po_uuid == po.po_uuid
        assert refs[0].als_werkweite_referenz is True


# --- Get-Export-Events-For-Segment-Lineage-Aware-Test (HG-S6-2) -------


@pytest.mark.asyncio
class TestGetExportEventsLineageAware:
    async def test_export_events_across_inactivation_reactivation_cycle(
        self, db_session: AsyncSession
    ) -> None:
        """Per Sprint 6 §A HG-S6-2: a Segment that was exported, then
        inactivated, then reactivated, then exported again — both
        EXPORT_EVENTs surface in the lookup, in chronological order.

        We synthesize this with two distinct rev_uuid snapshots: one
        pre-cycle, one post-cycle. The export-events query enumerates
        all Revisions FK'd to the segment regardless of `active`
        flags, so the pre-cycle EXPORT_EVENT remains visible.
        """
        project, _ = await seed_project_with_account(db_session)
        seg = await seed_segment_with_revision(db_session, project=project, text="v1")
        rev_v1 = seg.current_rev_uuid
        # Pre-cycle EXPORT_EVENT containing v1's rev_uuid.
        export_pre = await seed_export_event(
            db_session,
            project_uuid=project.project_uuid,
            revision_snapshot=[rev_v1],
        )

        # Simulate post-reactivation re-translation: a new Revision
        # appears on the same segment.
        await create_revision(
            session=db_session,
            segment=seg,
            after_text="v2",
            change_source=ChangeSource.MANUAL,
            operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
        )
        await db_session.refresh(seg)
        rev_v2 = seg.current_rev_uuid
        assert rev_v2 != rev_v1

        # Post-cycle EXPORT_EVENT containing v2's rev_uuid.
        export_post = await seed_export_event(
            db_session,
            project_uuid=project.project_uuid,
            revision_snapshot=[rev_v2],
        )

        refs = await get_export_events_for_segment(session=db_session, satz_uuid=seg.satz_uuid)
        assert len(refs) == 2
        po_uuids = [r.po.po_uuid for r in refs]
        # Chronological order.
        assert po_uuids == [export_pre.po_uuid, export_post.po_uuid]


# --- Get-Export-Events-Werkweite-Referenz-Marker-Test ------------------


@pytest.mark.asyncio
class TestWerkweiteReferenzMarker:
    async def test_each_returned_export_event_carries_marker(
        self, db_session: AsyncSession
    ) -> None:
        project, _ = await seed_project_with_account(db_session)
        seg = await seed_segment_with_revision(db_session, project=project, text="x")
        rev = seg.current_rev_uuid
        await seed_export_event(
            db_session,
            project_uuid=project.project_uuid,
            revision_snapshot=[rev],
        )
        refs = await get_export_events_for_segment(session=db_session, satz_uuid=seg.satz_uuid)
        assert len(refs) == 1
        # Type and value invariant — marker is True on every entry.
        assert isinstance(refs[0], SegmentExportEventRef)
        assert refs[0].als_werkweite_referenz is True


# --- Segment readout aggregator ---------------------------------------


@pytest.mark.asyncio
class TestGetSegmentReadout:
    async def test_aggregates_revisions_des_pos_export_refs(self, db_session: AsyncSession) -> None:
        from tests.readout._helpers import seed_de
        from waraq.readout import get_segment_readout
        from waraq.schemas.enums import DecisionSource

        project, _ = await seed_project_with_account(db_session)
        seg = await seed_segment_with_revision(db_session, project=project, text="v1")
        rev = seg.current_rev_uuid
        # Segment-scoped DE.
        de = await seed_de(
            db_session,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
            decision_source=DecisionSource.LOCK_MANAGEMENT,
        )
        # Segment-scoped PO.
        po = await seed_po(
            db_session,
            po_type=POType.OCR,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
        )
        # EXPORT_EVENT containing the rev.
        export_po = await seed_export_event(
            db_session,
            project_uuid=project.project_uuid,
            revision_snapshot=[rev],
        )

        readout = await get_segment_readout(session=db_session, satz_uuid=seg.satz_uuid)
        assert readout.satz_uuid == seg.satz_uuid
        assert any(r.rev_uuid == rev for r in readout.revisions)
        assert any(d.decision_event_uuid == de.decision_event_uuid for d in readout.decision_events)
        assert any(p.po_uuid == po.po_uuid for p in readout.provenance_objects)
        # EXPORT_EVENT NOT in `provenance_objects` (it's project-scoped, not segment-scoped).
        assert all(p.po_uuid != export_po.po_uuid for p in readout.provenance_objects)
        # But IS in `export_event_refs` with werkweite marker.
        assert any(r.po.po_uuid == export_po.po_uuid for r in readout.export_event_refs)
        for ref in readout.export_event_refs:
            assert ref.als_werkweite_referenz is True
