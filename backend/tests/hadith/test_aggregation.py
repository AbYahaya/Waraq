"""Phase 2F-B — `run_verification_round` persistence integration tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment
from waraq.hadith import (
    HadithCandidateHit,
    Quellenrolle,
    run_verification_round,
)
from waraq.schemas import HadithAggregateResult, HadithSingleSourceResult


def _hit(*, source: str, matn: str, **kwargs: object) -> HadithCandidateHit:
    return HadithCandidateHit(
        source_name=source,
        quellen_rolle=kwargs.get("role", Quellenrolle.PFLICHT),  # type: ignore[arg-type]
        matn_arabic=matn,
        matn_vocalized=kwargs.get("voc"),  # type: ignore[arg-type]
        isnad_chain=kwargs.get("isnad", []),  # type: ignore[arg-type]
        collection_label=kwargs.get("collection", ""),  # type: ignore[arg-type]
        authenticity_grade=kwargs.get("grade"),  # type: ignore[arg-type]
        raw_payload=kwargs.get("raw", {}),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
class TestSingleRound:
    async def test_writes_aggregate_and_single_source_rows(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session, name="hadith-agg-1")
        seg = await seed_segment(db_session, project=project, text="x")

        candidates = [
            _hit(
                source="sunnah.com",
                matn="إنما الأعمال بالنيات",
                voc="إنَّمَا الأَعْمَالُ بِالنِّيَّاتِ",
                isnad=["عمر"],
                collection="Sahih al-Bukhari",
                grade="Sahih",
                raw={"hadithEnglish": "Actions are by intentions"},
            ),
            _hit(
                source="dorar.net",
                matn="إنما الأعمال بالنيات",
                collection="some other collection",
                grade="Sahih",
            ),
        ]
        outcome = await run_verification_round(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
            ocr_rev_uuid=None,
            candidates=candidates,
        )
        assert outcome.superseded_aggregate_uuid is None
        assert len(outcome.single_source_uuids) == 2

        # Aggregate row landed.
        aggregate = (
            await db_session.execute(
                select(HadithAggregateResult).where(
                    HadithAggregateResult.aggregate_uuid == outcome.aggregate_uuid
                )
            )
        ).scalar_one()
        assert aggregate.is_aktiv is True
        assert aggregate.satz_uuid == seg.satz_uuid
        assert aggregate.block_uuid == seg.block_uuid
        assert aggregate.reference_matn == "إنما الأعمال بالنيات"
        # Reference matn source is one of our two single-source rows.
        assert aggregate.reference_matn_source_uuid in outcome.single_source_uuids
        # Reference vocalization came from sunnah.com (only voc'd hit).
        assert aggregate.reference_vocalization is not None
        assert aggregate.reference_vocalization_source_uuid is not None

        # Two Single-source rows attached.
        ss_rows = list(
            (
                await db_session.execute(
                    select(HadithSingleSourceResult).where(
                        HadithSingleSourceResult.aggregate_uuid == outcome.aggregate_uuid
                    )
                )
            ).scalars()
        )
        assert len(ss_rows) == 2
        sources = {r.source_name for r in ss_rows}
        assert sources == {"sunnah.com", "dorar.net"}

        # §4.16.8 — sunnah.com's hadithEnglish goes into website_uebersetzung.
        sunnah_row = next(r for r in ss_rows if r.source_name == "sunnah.com")
        assert sunnah_row.website_uebersetzung == [
            {"lang": "en", "text": "Actions are by intentions"}
        ]


@pytest.mark.asyncio
class TestRerunSupersession:
    async def test_second_round_supersedes_first(self, db_session: AsyncSession) -> None:
        """§4.16.6 — new verification round writes a new aggregate;
        old goes is_aktiv=false + superseded_by_uuid points forward."""
        project = await seed_project(db_session, name="hadith-rerun")
        seg = await seed_segment(db_session, project=project, text="x")

        first = await run_verification_round(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
            ocr_rev_uuid=None,
            candidates=[
                _hit(
                    source="sunnah.com",
                    matn="إنما الأعمال بالنيات",
                    collection="Sahih al-Bukhari",
                )
            ],
        )

        second = await run_verification_round(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
            ocr_rev_uuid=None,
            candidates=[
                _hit(
                    source="sunnah.com",
                    matn="إنما الأعمال بالنيات",
                    collection="Sahih al-Bukhari",
                ),
                _hit(
                    source="dorar.net",
                    matn="إنما الأعمال بالنيات",
                    collection="other",
                ),
            ],
        )
        assert second.superseded_aggregate_uuid == first.aggregate_uuid
        assert second.aggregate_uuid != first.aggregate_uuid

        # Both aggregates exist; check by UUID rather than detected_at
        # ordering (which is non-deterministic when both timestamps
        # land in the same flush).
        aggregates = list(
            (
                await db_session.execute(
                    select(HadithAggregateResult).where(
                        HadithAggregateResult.satz_uuid == seg.satz_uuid
                    )
                )
            ).scalars()
        )
        assert len(aggregates) == 2
        by_uuid = {a.aggregate_uuid: a for a in aggregates}
        first_agg = by_uuid[first.aggregate_uuid]
        second_agg = by_uuid[second.aggregate_uuid]
        assert first_agg.is_aktiv is False
        assert first_agg.superseded_by_uuid == second.aggregate_uuid
        assert second_agg.is_aktiv is True
        assert second_agg.superseded_by_uuid is None

    async def test_old_single_source_rows_immutable_after_rerun(
        self, db_session: AsyncSession
    ) -> None:
        """§4.16.6 / §4.9 E-10 — old Single-source rows stay attached
        to their original aggregate after a re-run."""
        project = await seed_project(db_session, name="hadith-immut")
        seg = await seed_segment(db_session, project=project, text="x")

        first = await run_verification_round(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
            ocr_rev_uuid=None,
            candidates=[_hit(source="sunnah.com", matn="x", collection="Sahih al-Bukhari")],
        )

        await run_verification_round(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
            ocr_rev_uuid=None,
            candidates=[_hit(source="dorar.net", matn="y", collection="other")],
        )

        # Old aggregate's Single-source row(s) still tagged with the
        # FIRST aggregate's UUID — not migrated.
        first_agg_ss = list(
            (
                await db_session.execute(
                    select(HadithSingleSourceResult).where(
                        HadithSingleSourceResult.aggregate_uuid == first.aggregate_uuid
                    )
                )
            ).scalars()
        )
        assert len(first_agg_ss) == 1
        assert first_agg_ss[0].source_name == "sunnah.com"


@pytest.mark.asyncio
class TestPropagatesConsensusToSummary:
    async def test_consensus_summary_lands_on_aggregate(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session, name="hadith-summary")
        seg = await seed_segment(db_session, project=project, text="x")

        outcome = await run_verification_round(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
            ocr_rev_uuid=None,
            candidates=[
                _hit(
                    source="sunnah.com",
                    matn="إنما الأعمال بالنيات",
                    collection="Sahih al-Bukhari",
                    grade="Sahih",
                ),
                _hit(
                    source="dorar.net",
                    matn="إنما الأعمال بالنيات",
                    collection="other",
                ),
            ],
        )

        aggregate = (
            await db_session.execute(
                select(HadithAggregateResult).where(
                    HadithAggregateResult.aggregate_uuid == outcome.aggregate_uuid
                )
            )
        ).scalar_one()
        # Per-dimension breakdown landed in the consensus_summary JSONB.
        assert "winner" in aggregate.consensus_summary
        assert "ranking" in aggregate.consensus_summary
        assert aggregate.consensus_summary["candidate_count"] == 2
