"""Phase 3 sub-batch A — §4.7.2 Pflichtfragen canonical-schema tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project
from tests.preflight._helpers import canonical_pflichtfrage_payload
from waraq.preflight import (
    PFLICHTFRAGE_COUNT,
    PFLICHTFRAGEN,
    PreflightError,
    confirm_pflichtfrage,
    get_pflichtfrage_by_index,
    get_pflichtfrage_by_key,
    save_export_profile_prefill,
    start_preflight_run,
    validate_pflichtfrage_answer,
)


class TestCanonicalRegistry:
    def test_count_is_canonical_4(self) -> None:
        assert len(PFLICHTFRAGEN) == PFLICHTFRAGE_COUNT == 4

    def test_indexes_are_1_through_4(self) -> None:
        assert sorted(p.frage_index for p in PFLICHTFRAGEN) == [1, 2, 3, 4]

    def test_keys_are_canonical(self) -> None:
        # Per §4.7.2 — these stable wire identifiers must not drift.
        assert {p.frage_key for p in PFLICHTFRAGEN} == {
            "header_heading_level",
            "chapter_break_heading_level",
            "toc_position",
            "display_arabic_chapter_headings",
        }

    def test_lookup_by_index_round_trip(self) -> None:
        for spec in PFLICHTFRAGEN:
            assert get_pflichtfrage_by_index(spec.frage_index) is spec
            assert get_pflichtfrage_by_key(spec.frage_key) is spec

    def test_lookup_unknown_raises(self) -> None:
        with pytest.raises(KeyError):
            get_pflichtfrage_by_index(99)
        with pytest.raises(KeyError):
            get_pflichtfrage_by_key("not_a_real_frage")


class TestAnswerValidation:
    def test_canonical_payloads_round_trip(self) -> None:
        for i in (1, 2, 3, 4):
            key, ans = canonical_pflichtfrage_payload(i)
            validated = validate_pflichtfrage_answer(frage_index=i, frage_key=key, answer=ans)
            # Round-tripped payload retains the canonical fields.
            assert validated == ans

    def test_heading_level_out_of_range_rejected(self) -> None:
        for i in (1, 2):
            key, _ = canonical_pflichtfrage_payload(i)
            with pytest.raises(PreflightError):
                validate_pflichtfrage_answer(
                    frage_index=i, frage_key=key, answer={"heading_level": 7}
                )
            with pytest.raises(PreflightError):
                validate_pflichtfrage_answer(
                    frage_index=i, frage_key=key, answer={"heading_level": 0}
                )

    def test_toc_position_must_be_front_or_back(self) -> None:
        with pytest.raises(PreflightError):
            validate_pflichtfrage_answer(
                frage_index=3, frage_key="toc_position", answer={"position": "side"}
            )

    def test_display_must_be_bool(self) -> None:
        # Pydantic's strict bool-coercion still rejects an arbitrary string.
        with pytest.raises(PreflightError):
            validate_pflichtfrage_answer(
                frage_index=4,
                frage_key="display_arabic_chapter_headings",
                answer={"display": "maybe"},
            )

    def test_frage_key_mismatch_rejected(self) -> None:
        # Index says 1 (header_heading_level), key says 3 (toc_position) — bug!
        with pytest.raises(PreflightError):
            validate_pflichtfrage_answer(
                frage_index=1,
                frage_key="toc_position",
                answer={"heading_level": 1},
            )

    def test_unknown_frage_index_rejected(self) -> None:
        with pytest.raises(PreflightError):
            validate_pflichtfrage_answer(
                frage_index=99, frage_key="header_heading_level", answer={"heading_level": 1}
            )


@pytest.mark.asyncio
class TestConfirmPflichtfrageValidates:
    async def test_canonical_payload_persisted(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        key, ans = canonical_pflichtfrage_payload(3)
        de = await confirm_pflichtfrage(
            session=db_session,
            project_uuid=project.project_uuid,
            preflight_run_uuid=run.job_uuid,
            frage_index=3,
            frage_key=key,
            answer=ans,
        )
        # Validated answer is what's persisted on the DE.
        assert de.content["answer"] == ans
        assert de.content["frage_key"] == key

    async def test_invalid_payload_refused(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        run = await start_preflight_run(session=db_session, project_uuid=project.project_uuid)
        with pytest.raises(PreflightError):
            await confirm_pflichtfrage(
                session=db_session,
                project_uuid=project.project_uuid,
                preflight_run_uuid=run.job_uuid,
                frage_index=1,
                frage_key="header_heading_level",
                answer={"heading_level": 99},  # out of canonical range
            )


@pytest.mark.asyncio
class TestProfilePrefillValidates:
    async def test_profile_prefill_canonical(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        key, ans = canonical_pflichtfrage_payload(2)
        row = await save_export_profile_prefill(
            session=db_session,
            project_uuid=project.project_uuid,
            frage_index=2,
            frage_key=key,
            prefilled_answer=ans,
        )
        assert row.prefilled_answer == ans

    async def test_profile_prefill_invalid_refused(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        with pytest.raises(PreflightError):
            await save_export_profile_prefill(
                session=db_session,
                project_uuid=project.project_uuid,
                frage_index=4,
                frage_key="display_arabic_chapter_headings",
                prefilled_answer={"display": "ja"},  # not bool
            )
