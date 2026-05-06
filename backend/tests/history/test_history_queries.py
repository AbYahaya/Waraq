"""M2 closeout — lightweight history-query tests.

Coverage:
- Segment history aggregates Revisions + DEs + POs + Log Entries +
  Conflict Instances anchored at the segment.
- Page history rolls up segment histories + page-scoped events + OCR
  errors.
- Project history rolls up page histories + project-scoped events +
  Konsistenz-Befunde.
- LINEAGE_EVENT-POs surface under provenance_objects (not Decision
  Events) — Sprint 6 R-S6-09 / DBB §B Abkürzung 8 invariant.
- Empty histories return empty containers (not None).
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.conflicts import ConflictType, RuleSource, detect_conflict
from waraq.consistency import (
    KConsistencyFinding,
    KRuleId,
    Verstossklasse,
    register_k_rule,
    register_stub_k_rules,
    run_consistency_check,
)
from waraq.decisions import create_decision_event
from waraq.history import (
    PageHistory,
    ProjectHistory,
    SegmentHistory,
    get_page_history,
    get_project_history,
    get_segment_history,
)
from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag, OperationMode
from waraq.lineage import inactivate_segment, record_one_to_one
from waraq.lock import set_lock
from waraq.ocr.error_classes import OcrErrorClass
from waraq.ocr.review import record_ocr_error_instance
from waraq.revision import create_revision
from waraq.schemas import Block, Page, Project, Segment
from waraq.schemas.enums import ChangeSource, DecisionSource, POType, ScopeType


async def _seed_chain(
    session: AsyncSession,
) -> tuple[Project, Page, Block, Segment]:
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="history-test")
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
    return project, page, block, segment


# --- Empty histories return populated containers ------------------------


@pytest.mark.asyncio
class TestEmptyHistories:
    async def test_segment_with_no_events_returns_empty_lists(
        self, db_session: AsyncSession
    ) -> None:
        _, _, _, segment = await _seed_chain(db_session)
        h = await get_segment_history(session=db_session, satz_uuid=segment.satz_uuid)
        assert isinstance(h, SegmentHistory)
        assert h.satz_uuid == segment.satz_uuid
        assert h.revisions == []
        assert h.decision_events == []
        assert h.provenance_objects == []
        assert h.log_entries == []
        assert h.conflict_instances == []

    async def test_page_with_no_events_returns_segments_list(
        self, db_session: AsyncSession
    ) -> None:
        _, page, _, _ = await _seed_chain(db_session)
        h = await get_page_history(session=db_session, page_uuid=page.page_uuid)
        assert isinstance(h, PageHistory)
        assert h.page_uuid == page.page_uuid
        assert len(h.segments) == 1
        assert h.page_decision_events == []
        assert h.ocr_error_instances == []

    async def test_project_with_no_events_returns_pages_list(
        self, db_session: AsyncSession
    ) -> None:
        project, _, _, _ = await _seed_chain(db_session)
        h = await get_project_history(session=db_session, project_uuid=project.project_uuid)
        assert isinstance(h, ProjectHistory)
        assert h.project_uuid == project.project_uuid
        assert len(h.pages) == 1
        assert h.project_decision_events == []
        assert h.konsistenz_befunde == []


# --- Segment history aggregates everything anchored at segment ----------


@pytest.mark.asyncio
class TestSegmentHistoryAggregation:
    async def test_revision_lock_change_and_conflict_all_appear(
        self, db_session: AsyncSession
    ) -> None:
        _, _, _, segment = await _seed_chain(db_session)

        # Drive multiple events anchored at this segment.
        await create_revision(
            session=db_session,
            segment=segment,
            after_text="first revision",
            change_source=ChangeSource.OCR,
            operation_mode=OperationMode.AUTOMATIC,
        )
        await set_lock(session=db_session, segment=segment, level=LockFlag.MANUAL_LOCAL)
        await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )
        await record_one_to_one(session=db_session, satz_uuid=segment.satz_uuid)

        h = await get_segment_history(session=db_session, satz_uuid=segment.satz_uuid)

        # Revisions: from create_revision.
        assert len(h.revisions) == 1
        assert h.revisions[0].after_text == "first revision"

        # Decision Events: lock_set DE (lock_management).
        de_sources = {str(de.decision_source) for de in h.decision_events}
        assert DecisionSource.LOCK_MANAGEMENT.value in de_sources

        # Provenance Objects: MANUAL_-PO (lock change) + LINEAGE_EVENT-PO
        # (1→1 record). create_revision alone does not write an OCR-PO —
        # that comes from run_ocr_job, which we don't drive here.
        po_types = {str(po.po_type) for po in h.provenance_objects}
        assert POType.MANUAL_.value in po_types
        assert POType.LINEAGE_EVENT.value in po_types

        # Log Entries: lineage_match_1to1 etc.
        log_ops = {entry.operation_type for entry in h.log_entries}
        assert "lineage_match_1to1" in log_ops

        # Conflict Instances: the open glossary-vs-lock collision.
        assert len(h.conflict_instances) == 1
        assert h.conflict_instances[0].state == "offen"

    async def test_lineage_event_pos_do_not_surface_as_decision_events(
        self, db_session: AsyncSession
    ) -> None:
        # Sprint 6 R-S6-09 / DBB §B Abkürzung 8: lineage matching events
        # MUST NOT appear in decision_events (they're system-events, not
        # user decisions). Verify the segment history keeps them strictly
        # under provenance_objects.
        _, _, _, segment = await _seed_chain(db_session)
        await record_one_to_one(session=db_session, satz_uuid=segment.satz_uuid)
        await inactivate_segment(session=db_session, segment=segment)

        h = await get_segment_history(session=db_session, satz_uuid=segment.satz_uuid)

        # Two LINEAGE_EVENT-POs in provenance_objects.
        lineage_pos = [
            po for po in h.provenance_objects if str(po.po_type) == POType.LINEAGE_EVENT.value
        ]
        assert len(lineage_pos) == 2

        # Zero "lineage" decision_types in decision_events.
        for de in h.decision_events:
            assert "lineage" not in de.decision_type.lower()


# --- Page history rolls up segments + page-scoped events ----------------


@pytest.mark.asyncio
class TestPageHistoryRollup:
    async def test_page_history_includes_segment_history_and_ocr_errors(
        self, db_session: AsyncSession
    ) -> None:
        _, page, _, segment = await _seed_chain(db_session)
        # Page-scoped event: an OCR error on this page.
        await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_01,
        )
        # Segment-scoped event: a Revision.
        await create_revision(
            session=db_session,
            segment=segment,
            after_text="page-history-test",
            change_source=ChangeSource.OCR,
            operation_mode=OperationMode.AUTOMATIC,
        )

        h = await get_page_history(session=db_session, page_uuid=page.page_uuid)

        assert h.page_uuid == page.page_uuid
        assert len(h.segments) == 1
        assert h.segments[0].satz_uuid == segment.satz_uuid
        assert len(h.segments[0].revisions) == 1
        assert len(h.ocr_error_instances) == 1
        assert h.ocr_error_instances[0].error_code == OcrErrorClass.F_01.value

    async def test_page_history_includes_page_scoped_decision_events(
        self, db_session: AsyncSession
    ) -> None:
        _, page, _, _ = await _seed_chain(db_session)
        await create_decision_event(
            session=db_session,
            scope_type=ScopeType.PAGE,
            scope_uuid=page.page_uuid,
            decision_type="ocr_review_no_go_to_go",
            decision_source=DecisionSource.OCR_REVIEW,
        )

        h = await get_page_history(session=db_session, page_uuid=page.page_uuid)
        assert len(h.page_decision_events) == 1
        assert h.page_decision_events[0].decision_type == "ocr_review_no_go_to_go"


# --- Project history rolls up pages + project-scoped events -------------


@pytest.mark.asyncio
class TestProjectHistoryRollup:
    async def test_project_history_includes_konsistenz_befunde_from_consistency_run(
        self, db_session: AsyncSession
    ) -> None:
        project, _, _, _ = await _seed_chain(db_session)

        # Register a synthetic K-rule that emits one finding so we have
        # something to surface in history.
        async def _emit(*, session: AsyncSession, project_uuid):  # type: ignore[no-untyped-def]
            return [
                KConsistencyFinding(
                    k_rule=KRuleId.K_01,
                    subject_key=str(new_uuid()),
                    verstossklasse=Verstossklasse.MITTEL,
                )
            ]

        register_stub_k_rules()
        register_k_rule(KRuleId.K_01, _emit)
        try:
            await run_consistency_check(session=db_session, project_uuid=project.project_uuid)
        finally:
            register_stub_k_rules()

        h = await get_project_history(session=db_session, project_uuid=project.project_uuid)
        assert len(h.konsistenz_befunde) == 1
        assert h.konsistenz_befunde[0].k_rule == KRuleId.K_01.value

    async def test_project_history_includes_project_scoped_decision_events(
        self, db_session: AsyncSession
    ) -> None:
        project, _, _, _ = await _seed_chain(db_session)
        await create_decision_event(
            session=db_session,
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            decision_type="glossary_create",
            decision_source=DecisionSource.GLOSSARY_MANAGEMENT,
        )

        h = await get_project_history(session=db_session, project_uuid=project.project_uuid)
        assert len(h.project_decision_events) == 1
        assert h.project_decision_events[0].decision_type == "glossary_create"

    async def test_project_history_includes_export_event_pos(
        self, db_session: AsyncSession
    ) -> None:
        # EXPORT_EVENT-POs are project-scoped per CLAUDE.md §5.4.
        from waraq.provenance import create_po

        project, _, _, _ = await _seed_chain(db_session)
        await create_po(
            session=db_session,
            po_type=POType.EXPORT_EVENT,
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            payload={"filename": "x.docx", "format": "docx"},
        )

        h = await get_project_history(session=db_session, project_uuid=project.project_uuid)
        export_pos = [
            po
            for po in h.project_provenance_objects
            if str(po.po_type) == POType.EXPORT_EVENT.value
        ]
        assert len(export_pos) == 1


# --- Cross-history isolation --------------------------------------------


@pytest.mark.asyncio
class TestHistoryIsolation:
    async def test_segment_history_does_not_leak_other_segment_events(
        self, db_session: AsyncSession
    ) -> None:
        _, _, _, segment_a = await _seed_chain(db_session)
        _, _, _, segment_b = await _seed_chain(db_session)

        await create_revision(
            session=db_session,
            segment=segment_a,
            after_text="A only",
            change_source=ChangeSource.OCR,
            operation_mode=OperationMode.AUTOMATIC,
        )

        h_a = await get_segment_history(session=db_session, satz_uuid=segment_a.satz_uuid)
        h_b = await get_segment_history(session=db_session, satz_uuid=segment_b.satz_uuid)

        assert len(h_a.revisions) == 1
        assert h_b.revisions == []
