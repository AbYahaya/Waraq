"""Phase 3 sub-batch D — guided review queue tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment
from tests.preflight._helpers import (
    seed_audit_job,
    seed_befund,
    seed_hadith,
    seed_konsistenz_befund,
    seed_ocr_error,
)
from waraq.guided_review import (
    GuidedReviewItemKind,
    GuidedReviewTier,
    build_review_queue,
)
from waraq.preflight.enums import HadithStellenTyp
from waraq.schemas import Block


@pytest.mark.asyncio
class TestQueueOrdering:
    async def test_empty_project_empty_queue(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        q = await build_review_queue(session=db_session, project_uuid=project.project_uuid)
        assert q.total == 0
        assert q.items == []

    async def test_kritisch_audit_before_hoch(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg1 = await seed_segment(db_session, project=project, text="a")
        seg2 = await seed_segment(db_session, project=project, text="b", satz_index=1)
        audit_job = await seed_audit_job(db_session, project=project)
        # Hoch (A-01) seeded BEFORE kritisch — but kritisch must still come first.
        await seed_befund(
            db_session, project=project, segment=seg1, audit_job=audit_job, regelkennung="A-01"
        )
        await seed_befund(
            db_session, project=project, segment=seg2, audit_job=audit_job, regelkennung="C-01"
        )
        q = await build_review_queue(session=db_session, project_uuid=project.project_uuid)
        assert q.total == 2
        assert q.items[0].tier == GuidedReviewTier.P_03_BLOCKING  # kritisch first
        assert q.items[1].tier == GuidedReviewTier.P_04_BLOCKING

    async def test_warning_tier_lowest(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        audit_job = await seed_audit_job(db_session, project=project)
        # D-01 = mittel (warning)
        await seed_befund(
            db_session, project=project, segment=seg, audit_job=audit_job, regelkennung="D-01"
        )
        # C-01 = kritisch
        seg2 = await seed_segment(db_session, project=project, text="y", satz_index=1)
        await seed_befund(
            db_session, project=project, segment=seg2, audit_job=audit_job, regelkennung="C-01"
        )
        q = await build_review_queue(session=db_session, project_uuid=project.project_uuid)
        assert q.items[0].tier == GuidedReviewTier.P_03_BLOCKING
        assert q.items[-1].tier == GuidedReviewTier.WARNING

    async def test_resolved_befunde_excluded(self, db_session: AsyncSession) -> None:
        from waraq.audit.service import quittiere_befund

        project = await seed_project(db_session)
        # D-01 = mittel — quittierbar (kritisch can't be quittiert).
        seg = await seed_segment(db_session, project=project, text="x")
        audit_job = await seed_audit_job(db_session, project=project)
        b = await seed_befund(
            db_session, project=project, segment=seg, audit_job=audit_job, regelkennung="D-01"
        )
        await quittiere_befund(session=db_session, befund=b)
        q = await build_review_queue(session=db_session, project_uuid=project.project_uuid)
        # Quittierte rows have aufloesungsstatus != offen → excluded.
        assert all(it.finding_uuid != b.befund_uuid for it in q.items)


@pytest.mark.asyncio
class TestKindCoverage:
    async def test_all_four_kinds_appear(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        block = await db_session.get(Block, seg.block_uuid)
        assert block is not None
        audit_job = await seed_audit_job(db_session, project=project)
        # 1. audit befund
        await seed_befund(
            db_session, project=project, segment=seg, audit_job=audit_job, regelkennung="C-01"
        )
        # 2. konsistenz
        await seed_konsistenz_befund(
            db_session,
            project=project,
            k_rule="K-01",
            subject_type="concept_id",
            subject_key="y",
            verstossklasse="mittel",
        )
        # 3. ocr error
        await seed_ocr_error(db_session, page_uuid=block.page_uuid, error_code="F-01")
        # 4. hadith H-2
        seg2 = await seed_segment(db_session, project=project, text="z", satz_index=1)
        await seed_hadith(
            db_session, project=project, segment=seg2, stellen_typ=HadithStellenTyp.N_5
        )
        q = await build_review_queue(session=db_session, project_uuid=project.project_uuid)
        kinds = {it.kind for it in q.items}
        assert kinds == {
            GuidedReviewItemKind.AUDIT_BEFUND,
            GuidedReviewItemKind.KONSISTENZ_BEFUND,
            GuidedReviewItemKind.OCR_ERROR,
            GuidedReviewItemKind.HADITH,
        }
        # by_tier accounting matches.
        assert sum(q.by_tier.values()) == q.total

    async def test_h0_hadith_excluded(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        # N-1 derives to HadithKlasse.H_0 — must be excluded.
        await seed_hadith(
            db_session, project=project, segment=seg, stellen_typ=HadithStellenTyp.N_1
        )
        q = await build_review_queue(session=db_session, project_uuid=project.project_uuid)
        # H-0 is silent per §4.16.4 — must not show in the guided-review queue.
        assert not any(it.kind == GuidedReviewItemKind.HADITH for it in q.items)
