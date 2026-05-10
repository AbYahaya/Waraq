"""Phase 3 sub-batch B — §2.2 pre-export verifier + EI2 predicate tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment
from waraq.canon_rules import (
    CanonRuleViolationKind,
    apply_all,
    has_ei2_violations,
    verify_canon_rules_for_export,
)


class TestEI2ViolationPredicate:
    def test_clean_text_passes(self) -> None:
        assert has_ei2_violations("Quran, Jihad, ordinary text") is False

    def test_capital_k_dot_below_detected(self) -> None:
        assert has_ei2_violations("the word Ḳur'an") is True

    def test_lowercase_k_dot_below_detected(self) -> None:
        assert has_ei2_violations("ḳur'an") is True

    def test_dj_capital_detected(self) -> None:
        assert has_ei2_violations("Djinn lore") is True

    def test_dj_uppercase_detected(self) -> None:
        assert has_ei2_violations("DJINNI") is True

    def test_dj_lowercase_detected(self) -> None:
        assert has_ei2_violations("hadj") is True

    def test_empty_string(self) -> None:
        assert has_ei2_violations("") is False

    def test_normalized_text_passes(self) -> None:
        # `apply_all` output is by construction violation-free.
        assert has_ei2_violations(apply_all("Ḳur'an, Djinn, ḳadi, dj")) is False


@pytest.mark.asyncio
class TestVerifierEmpty:
    async def test_clean_project_no_violations(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await seed_segment(db_session, project=project, text="Western 42 Quran")
        result = await verify_canon_rules_for_export(
            session=db_session, project_uuid=project.project_uuid
        )
        assert result == []

    async def test_no_segments_no_violations(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        result = await verify_canon_rules_for_export(
            session=db_session, project_uuid=project.project_uuid
        )
        assert result == []


@pytest.mark.asyncio
class TestVerifierFindings:
    async def test_arabic_indic_digit_caught(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="Page ٤٢")
        result = await verify_canon_rules_for_export(
            session=db_session, project_uuid=project.project_uuid
        )
        assert len(result) == 1
        assert result[0].satz_uuid == seg.satz_uuid
        assert result[0].kind == CanonRuleViolationKind.ARABIC_INDIC_DIGITS

    async def test_ei2_violation_caught(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="Ḳur'an study")
        result = await verify_canon_rules_for_export(
            session=db_session, project_uuid=project.project_uuid
        )
        assert len(result) == 1
        assert result[0].satz_uuid == seg.satz_uuid
        assert result[0].kind == CanonRuleViolationKind.EI2_TRANSLITERATION

    async def test_both_kinds_on_one_segment_two_rows(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="Ḳur'an page ٤٢")
        result = await verify_canon_rules_for_export(
            session=db_session, project_uuid=project.project_uuid
        )
        assert len(result) == 2
        assert {v.kind for v in result} == {
            CanonRuleViolationKind.ARABIC_INDIC_DIGITS,
            CanonRuleViolationKind.EI2_TRANSLITERATION,
        }
        assert all(v.satz_uuid == seg.satz_uuid for v in result)

    async def test_only_active_segments_scanned(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="bad ٧")
        seg.active = False
        await db_session.flush()
        result = await verify_canon_rules_for_export(
            session=db_session, project_uuid=project.project_uuid
        )
        assert result == []

    async def test_other_project_segments_excluded(self, db_session: AsyncSession) -> None:
        project_a = await seed_project(db_session, name="A")
        project_b = await seed_project(db_session, name="B")
        await seed_segment(db_session, project=project_a, text="Ḳur'an")
        await seed_segment(db_session, project=project_b, text="clean")
        result = await verify_canon_rules_for_export(
            session=db_session, project_uuid=project_b.project_uuid
        )
        assert result == []
