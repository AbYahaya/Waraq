"""Phase 3 sub-batch D — difficulty report tests."""

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
from waraq.difficulty import (
    DEFAULT_DIFFICULTY_WEIGHTS,
    compute_page_difficulty,
    compute_project_difficulty,
)
from waraq.preflight.enums import HadithStellenTyp
from waraq.schemas import Block


@pytest.mark.asyncio
class TestEmptyProject:
    async def test_empty_project_score_zero(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        rep = await compute_project_difficulty(
            session=db_session, project_uuid=project.project_uuid
        )
        assert rep.score == 0.0
        assert rep.segment_count == 0
        assert rep.scope == "project"

    async def test_clean_page_score_zero(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        block = await db_session.get(Block, seg.block_uuid)
        assert block is not None
        rep = await compute_page_difficulty(session=db_session, page_uuid=block.page_uuid)
        assert rep.score == 0.0
        assert rep.segment_count == 1
        assert rep.scope == "page"


@pytest.mark.asyncio
class TestProjectScoring:
    async def test_kritisch_audit_befund_contributes_4(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        audit_job = await seed_audit_job(db_session, project=project)
        await seed_befund(
            db_session,
            project=project,
            segment=seg,
            audit_job=audit_job,
            regelkennung="C-01",  # kritisch
        )
        rep = await compute_project_difficulty(
            session=db_session, project_uuid=project.project_uuid
        )
        assert rep.breakdown.audit_kritisch == 1
        assert rep.score == DEFAULT_DIFFICULTY_WEIGHTS.audit_kritisch

    async def test_konsistenz_kritisch_routes_to_kritisch_bucket(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        await seed_konsistenz_befund(
            db_session,
            project=project,
            k_rule="K-01",
            subject_type="concept_id",
            subject_key="x",
            verstossklasse="kritisch",
        )
        rep = await compute_project_difficulty(
            session=db_session, project_uuid=project.project_uuid
        )
        assert rep.breakdown.konsistenz_kritisch == 1
        assert rep.breakdown.konsistenz_other == 0
        assert rep.score == DEFAULT_DIFFICULTY_WEIGHTS.konsistenz_kritisch

    async def test_konsistenz_non_kritisch_routes_to_other_bucket(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        await seed_konsistenz_befund(
            db_session,
            project=project,
            k_rule="K-01",
            subject_type="concept_id",
            subject_key="x",
            verstossklasse="mittel",
        )
        rep = await compute_project_difficulty(
            session=db_session, project_uuid=project.project_uuid
        )
        assert rep.breakdown.konsistenz_kritisch == 0
        assert rep.breakdown.konsistenz_other == 1

    async def test_hadith_h2_contributes_4(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        await seed_hadith(
            db_session, project=project, segment=seg, stellen_typ=HadithStellenTyp.N_5
        )
        rep = await compute_project_difficulty(
            session=db_session, project_uuid=project.project_uuid
        )
        assert rep.breakdown.hadith_h_2 == 1
        assert rep.score == DEFAULT_DIFFICULTY_WEIGHTS.hadith_h_2

    async def test_ocr_kritisch_contributes(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        block = await db_session.get(Block, seg.block_uuid)
        assert block is not None
        await seed_ocr_error(db_session, page_uuid=block.page_uuid, error_code="F-01")
        rep = await compute_project_difficulty(
            session=db_session, project_uuid=project.project_uuid
        )
        assert rep.breakdown.ocr_error_kritisch >= 1


@pytest.mark.asyncio
class TestPageScoping:
    async def test_other_page_findings_excluded(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        # Page A has a kritisch befund.
        seg_a = await seed_segment(db_session, project=project, text="a", page_index=1)
        block_a = await db_session.get(Block, seg_a.block_uuid)
        assert block_a is not None
        audit_job = await seed_audit_job(db_session, project=project)
        await seed_befund(
            db_session,
            project=project,
            segment=seg_a,
            audit_job=audit_job,
            regelkennung="C-01",
        )
        # Page B has nothing.
        seg_b = await seed_segment(db_session, project=project, text="b", page_index=2)
        block_b = await db_session.get(Block, seg_b.block_uuid)
        assert block_b is not None

        page_a_rep = await compute_page_difficulty(session=db_session, page_uuid=block_a.page_uuid)
        page_b_rep = await compute_page_difficulty(session=db_session, page_uuid=block_b.page_uuid)
        assert page_a_rep.score > 0
        assert page_b_rep.score == 0
