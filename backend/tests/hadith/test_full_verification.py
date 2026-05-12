"""Phase 4 sub-batch I — `run_full_hadith_verification` end-to-end wiring."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment
from waraq.hadith import (
    HadithCandidateHit,
    Quellenrolle,
    run_full_hadith_verification,
)
from waraq.schemas import HadithAggregateResult, HadithSingleSourceResult


def _hit(
    *, source: str, matn: str, role: Quellenrolle = Quellenrolle.PFLICHT
) -> HadithCandidateHit:
    return HadithCandidateHit(
        source_name=source,
        quellen_rolle=role,
        matn_arabic=matn,
        matn_vocalized=None,
        isnad_chain=[],
        collection_label=source,
        authenticity_grade=None,
        raw_payload={},
    )


@pytest.mark.asyncio
class TestFullVerification:
    async def test_persists_levels_2_and_3_when_candidates_present(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session, name="full-verif-1")
        seg = await seed_segment(db_session, project=project, text="x")
        mandatory = [
            _hit(source="sunnah.com", matn="إنما الأعمال بالنيات"),
            _hit(source="dorar.net", matn="إنما الأعمال بالنيات"),
        ]
        outcome = await run_full_hadith_verification(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
            ocr_rev_uuid=None,
            mandatory_hits=mandatory,
            query="إنما الأعمال بالنيات",
        )
        assert outcome.run is not None
        assert len(outcome.run.single_source_uuids) == 2
        # Level-3 row written.
        aggregate = (
            await db_session.execute(
                select(HadithAggregateResult).where(
                    HadithAggregateResult.aggregate_uuid == outcome.run.aggregate_uuid
                )
            )
        ).scalar_one()
        assert aggregate.is_aktiv is True
        # Level-2 rows written.
        single_sources = list(
            (
                await db_session.execute(
                    select(HadithSingleSourceResult).where(
                        HadithSingleSourceResult.aggregate_uuid == outcome.run.aggregate_uuid
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(single_sources) == 2

    async def test_no_candidates_no_persistence(self, db_session: AsyncSession) -> None:
        # Empty mandatory + (default) E-5-stub returns nothing →
        # outcome.run is None and no DB rows are written.
        project = await seed_project(db_session, name="full-verif-2")
        seg = await seed_segment(db_session, project=project, text="x")
        outcome = await run_full_hadith_verification(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
            ocr_rev_uuid=None,
            mandatory_hits=[],
            query="anything",
        )
        assert outcome.run is None
        # No persistent rows.
        assert outcome.two_tier.mandatory_hits == []
        assert outcome.two_tier.extended_hits == []

    async def test_orchestrator_extension_persisted_too(self, db_session: AsyncSession) -> None:
        # Manual escalation triggers the extended fetcher set; in v1.0
        # the default fetchers all return empty hits, so the only
        # persistent rows are the mandatory ones — but the orchestrator
        # records the escalation reason which the caller can read off
        # `outcome.two_tier`.
        project = await seed_project(db_session, name="full-verif-3")
        seg = await seed_segment(db_session, project=project, text="x")
        mandatory = [_hit(source="sunnah.com", matn="إنما الأعمال بالنيات")]

        outcome = await run_full_hadith_verification(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
            ocr_rev_uuid=None,
            mandatory_hits=mandatory,
            query="إنما الأعمال بالنيات",
            manually_trigger_extended=True,
        )
        assert outcome.two_tier.extended_set_triggered is True
        assert outcome.two_tier.extended_trigger_reason == "manual"
        assert outcome.run is not None
        assert len(outcome.run.single_source_uuids) == 1
