"""§4.16.6 four-level data model — schema integration tests.

Coverage:
- Aggregate row round-trips with all required fields.
- Single-source row FK to aggregate, source_role enum constraint.
- Vokalisierungsklasse CHECK constraint rejects garbage.
- Quellenrolle CHECK constraint rejects garbage.
- Multiple Single-source rows per (source, run) permitted ("hit variants").
- Immutability: a new verification round writes a new aggregate row;
  the old one survives with is_aktiv=false and superseded_by_uuid set.
- Level 1 anchor (block_uuid + satz_uuid + ocr_rev_uuid) round-trips.
"""

from __future__ import annotations

import uuid as _uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_segment
from waraq.hadith.enums import Quellenrolle, Vokalisierungsklasse
from waraq.identity import new_uuid
from waraq.schemas import HadithAggregateResult, HadithSingleSourceResult, Project


async def _seed_project(session: AsyncSession) -> Project:
    from tests.audit._helpers import seed_project

    return await seed_project(session)


def _make_aggregate(
    *,
    project_uuid: _uuid.UUID,
    satz_uuid: _uuid.UUID,
    block_uuid: _uuid.UUID,
    run_uuid: str | None = None,
    voc_klasse: Vokalisierungsklasse = Vokalisierungsklasse.V_0,
    voc_konflikt: bool = False,
    is_aktiv: bool = True,
    superseded_by_uuid: _uuid.UUID | None = None,
) -> HadithAggregateResult:
    return HadithAggregateResult(
        aggregate_uuid=new_uuid(),
        satz_uuid=satz_uuid,
        block_uuid=block_uuid,
        ocr_rev_uuid=None,
        project_uuid=project_uuid,
        run_uuid=run_uuid or str(new_uuid()),
        reference_matn="بسم الله الرحمن الرحيم",
        reference_matn_source_uuid=None,
        reference_vocalization="بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
        reference_vocalization_source_uuid=None,
        vokalisierungsklasse=voc_klasse.value,
        vokalisierungs_konflikt=voc_konflikt,
        consensus_summary={"wording_proximity": 0.92},
        is_aktiv=is_aktiv,
        superseded_by_uuid=superseded_by_uuid,
    )


@pytest.mark.asyncio
class TestAggregateRoundTrip:
    async def test_aggregate_round_trip(self, db_session: AsyncSession) -> None:
        project = await _seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        agg = _make_aggregate(
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
        )
        db_session.add(agg)
        await db_session.flush()

        loaded = (
            await db_session.execute(
                select(HadithAggregateResult).where(
                    HadithAggregateResult.aggregate_uuid == agg.aggregate_uuid
                )
            )
        ).scalar_one()
        assert loaded.run_uuid == agg.run_uuid
        assert loaded.vokalisierungsklasse == "V-0"
        assert loaded.vokalisierungs_konflikt is False
        assert loaded.is_aktiv is True
        assert loaded.consensus_summary == {"wording_proximity": 0.92}

    async def test_vokalisierungsklasse_check_rejects_garbage(
        self, db_session: AsyncSession
    ) -> None:
        project = await _seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        agg = HadithAggregateResult(
            aggregate_uuid=new_uuid(),
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
            ocr_rev_uuid=None,
            project_uuid=project.project_uuid,
            run_uuid=str(new_uuid()),
            vokalisierungsklasse="V-X",  # invalid
            vokalisierungs_konflikt=False,
        )
        db_session.add(agg)
        with pytest.raises(IntegrityError):
            await db_session.flush()


@pytest.mark.asyncio
class TestSingleSourceFkAndRole:
    async def test_single_source_fk_to_aggregate(self, db_session: AsyncSession) -> None:
        project = await _seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        agg = _make_aggregate(
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
        )
        db_session.add(agg)
        await db_session.flush()

        ss = HadithSingleSourceResult(
            single_source_uuid=new_uuid(),
            aggregate_uuid=agg.aggregate_uuid,
            source_name="sunnah.com",
            quellen_rolle=Quellenrolle.PFLICHT.value,
            matn_text="...",
            matn_vocalized="...",
            raw_payload={"hadith_no": 1},
            website_uebersetzung=[{"lang": "en", "text": "By the name of..."}],
        )
        db_session.add(ss)
        await db_session.flush()

        loaded = (
            await db_session.execute(
                select(HadithSingleSourceResult).where(
                    HadithSingleSourceResult.single_source_uuid == ss.single_source_uuid
                )
            )
        ).scalar_one()
        assert loaded.aggregate_uuid == agg.aggregate_uuid
        assert loaded.quellen_rolle == "pflicht"
        assert loaded.website_uebersetzung == [{"lang": "en", "text": "By the name of..."}]

    async def test_quellen_rolle_check_rejects_garbage(self, db_session: AsyncSession) -> None:
        project = await _seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        agg = _make_aggregate(
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
        )
        db_session.add(agg)
        await db_session.flush()

        ss = HadithSingleSourceResult(
            single_source_uuid=new_uuid(),
            aggregate_uuid=agg.aggregate_uuid,
            source_name="sunnah.com",
            quellen_rolle="bogus",  # invalid
        )
        db_session.add(ss)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_multiple_single_source_rows_per_run_permitted(
        self, db_session: AsyncSession
    ) -> None:
        """§4.16.6 — multiple Single-source objects of the same source
        in the same run are permitted (hit variants)."""
        project = await _seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")
        agg = _make_aggregate(
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
        )
        db_session.add(agg)
        await db_session.flush()

        for variant_no in range(3):
            db_session.add(
                HadithSingleSourceResult(
                    single_source_uuid=new_uuid(),
                    aggregate_uuid=agg.aggregate_uuid,
                    source_name="sunnah.com",
                    quellen_rolle=Quellenrolle.PFLICHT.value,
                    matn_text=f"variant {variant_no}",
                )
            )
        await db_session.flush()

        rows = list(
            (
                await db_session.execute(
                    select(HadithSingleSourceResult).where(
                        HadithSingleSourceResult.aggregate_uuid == agg.aggregate_uuid
                    )
                )
            ).scalars()
        )
        assert len(rows) == 3
        assert all(r.source_name == "sunnah.com" for r in rows)


@pytest.mark.asyncio
class TestImmutabilityAndSupersession:
    async def test_new_run_writes_new_aggregate_old_remains(self, db_session: AsyncSession) -> None:
        """§4.16.6 — new verification round generates a new aggregate
        with its own UUID; old one preserved as provenance with
        is_aktiv=false and superseded_by_uuid pointing forward."""
        project = await _seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x")

        old = _make_aggregate(
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
            run_uuid="run-1",
        )
        db_session.add(old)
        await db_session.flush()

        # Second verification round.
        new = _make_aggregate(
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
            run_uuid="run-2",
            voc_klasse=Vokalisierungsklasse.V_1,
            voc_konflikt=True,
        )
        db_session.add(new)
        await db_session.flush()

        # Mark old as superseded.
        old.is_aktiv = False
        old.superseded_by_uuid = new.aggregate_uuid
        await db_session.flush()

        # Both rows still present; old preserved as provenance.
        rows = list(
            (
                await db_session.execute(
                    select(HadithAggregateResult).where(
                        HadithAggregateResult.satz_uuid == seg.satz_uuid
                    )
                )
            ).scalars()
        )
        assert len(rows) == 2
        active = [r for r in rows if r.is_aktiv]
        inactive = [r for r in rows if not r.is_aktiv]
        assert len(active) == 1
        assert len(inactive) == 1
        assert active[0].aggregate_uuid == new.aggregate_uuid
        assert inactive[0].superseded_by_uuid == new.aggregate_uuid


@pytest.mark.asyncio
class TestLevel1Anchor:
    async def test_block_uuid_satz_uuid_ocr_rev_uuid_anchor(self, db_session: AsyncSession) -> None:
        """§4.16.6 Level 1 — passage anchor via Block-UUID + Sentence-UUID
        + OCR Revision-UUID. Test confirms all three columns persist
        when ocr_rev_uuid is provided."""
        from waraq.invariant.enums import OperationMode
        from waraq.revision import create_revision
        from waraq.schemas.enums import ChangeSource

        project = await _seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="initial")
        rev = await create_revision(
            session=db_session,
            segment=seg,
            after_text="updated",
            change_source=ChangeSource.OCR,
            operation_mode=OperationMode.AUTOMATIC,
        )

        agg = HadithAggregateResult(
            aggregate_uuid=new_uuid(),
            satz_uuid=seg.satz_uuid,
            block_uuid=seg.block_uuid,
            ocr_rev_uuid=rev.rev_uuid,
            project_uuid=project.project_uuid,
            run_uuid=str(new_uuid()),
            vokalisierungsklasse=Vokalisierungsklasse.V_0.value,
            vokalisierungs_konflikt=False,
        )
        db_session.add(agg)
        await db_session.flush()

        loaded = (
            await db_session.execute(
                select(HadithAggregateResult).where(
                    HadithAggregateResult.aggregate_uuid == agg.aggregate_uuid
                )
            )
        ).scalar_one()
        assert loaded.satz_uuid == seg.satz_uuid
        assert loaded.block_uuid == seg.block_uuid
        assert loaded.ocr_rev_uuid == rev.rev_uuid
