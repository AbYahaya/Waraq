"""Phase 4 sub-batch I — religious-formula verifier integration."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment
from waraq.canon_rules import (
    CanonRuleViolationKind,
    apply_all,
    verify_canon_rules_for_export,
)
from waraq.canon_rules.religious_formulas import has_religious_formula_violations


class TestHasReligiousFormulaViolations:
    def test_clean_glyph_text_passes(self) -> None:
        assert has_religious_formula_violations("der Prophet ﷺ sagte") is False

    def test_empty_string_no_violation(self) -> None:
        assert has_religious_formula_violations("") is False

    def test_text_without_any_formula_passes(self) -> None:
        assert has_religious_formula_violations("ordinary text 123") is False

    def test_spelled_out_saw_bare_detected(self) -> None:
        # "صلى الله عليه وسلم" is a spelled-out form of ﷺ.
        assert has_religious_formula_violations("قال صلى الله عليه وسلم") is True

    def test_spelled_out_saw_vocalized_detected(self) -> None:
        assert has_religious_formula_violations("قال صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ") is True

    def test_spelled_out_jj_detected(self) -> None:
        # "جل جلاله" is a spelled-out form of ﷻ.
        assert has_religious_formula_violations("الله جل جلاله") is True

    def test_apply_all_output_passes_predicate(self) -> None:
        # Defense-in-depth invariant: anything that survives `apply_all`
        # MUST NOT trigger the verifier.
        original = "قال صلى الله عليه وسلم وذكر جل جلاله"
        normalized = apply_all(original)
        assert has_religious_formula_violations(normalized) is False


@pytest.mark.asyncio
class TestVerifierIntegration:
    async def test_clean_segment_no_finding(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await seed_segment(
            db_session,
            project=project,
            text="der Prophet ﷺ sagte\n---\nclean translation",
        )
        result = await verify_canon_rules_for_export(
            session=db_session, project_uuid=project.project_uuid
        )
        assert all(v.kind != CanonRuleViolationKind.RELIGIOUS_FORMULA_NOT_GLYPH for v in result)

    async def test_spelled_out_saw_yields_finding(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(
            db_session,
            project=project,
            text="قال صلى الله عليه وسلم\n---\nsagte salla allahu alayhi wa sallam",
        )
        result = await verify_canon_rules_for_export(
            session=db_session, project_uuid=project.project_uuid
        )
        relig = [v for v in result if v.kind == CanonRuleViolationKind.RELIGIOUS_FORMULA_NOT_GLYPH]
        assert len(relig) == 1
        assert relig[0].satz_uuid == seg.satz_uuid

    async def test_spelled_out_jj_yields_finding(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await seed_segment(
            db_session,
            project=project,
            text="الله جل جلاله\n---\nGott in Seiner Erhabenheit",
        )
        result = await verify_canon_rules_for_export(
            session=db_session, project_uuid=project.project_uuid
        )
        relig = [v for v in result if v.kind == CanonRuleViolationKind.RELIGIOUS_FORMULA_NOT_GLYPH]
        assert len(relig) == 1

    async def test_canonical_glyph_no_finding(self, db_session: AsyncSession) -> None:
        # Already in canonical glyph form — verifier must not flag.
        project = await seed_project(db_session)
        await seed_segment(
            db_session,
            project=project,
            text="ذكر ﷻ عبده ﷺ\n---\nGott ﷻ erwähnte Seinen Diener ﷺ",
        )
        result = await verify_canon_rules_for_export(
            session=db_session, project_uuid=project.project_uuid
        )
        assert all(v.kind != CanonRuleViolationKind.RELIGIOUS_FORMULA_NOT_GLYPH for v in result)
