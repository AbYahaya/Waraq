"""Phase 4 sub-batch G — C-01 audit-rule glossary lookup body upgrade."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment
from waraq.audit import (
    GlossaryEntry,
    RuleContext,
    build_default_rule_context,
    run_audit_for_project,
)
from waraq.audit.rules import rule_c_01
from waraq.identity import new_uuid
from waraq.schemas import Befund, Concept


def _ctx(*entries: GlossaryEntry) -> RuleContext:
    return RuleContext(glossary=tuple(entries))


def _entry(canonical: str, gloss: str) -> GlossaryEntry:
    return GlossaryEntry(
        concept_id=new_uuid(),
        canonical_label=canonical,
        gloss=gloss,
        binding_level="project",
    )


# ---------------------------------------------------------------------
# Direct rule invocation
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestRuleC01Direct:
    async def test_marker_only_path_preserved(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        segment = await seed_segment(
            db_session,
            project=project,
            text="مثل ذلك\n---\nfalsche [TERM-VIOLATION]",
        )
        # No ctx supplied → legacy behaviour: just the marker check.
        findings = rule_c_01(segment)
        assert len(findings) == 1
        assert findings[0].regelkennung == "C-01"
        assert findings[0].detection_context.get("match", "marker") in (
            "terminology_violation_marker",
            "marker",
        )

    async def test_glossary_hit_with_correct_gloss_no_finding(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        segment = await seed_segment(
            db_session,
            project=project,
            text="بسم الله\n---\nim Namen Gottes",
        )
        ctx = _ctx(_entry("الله", "Gottes"))
        findings = rule_c_01(segment, ctx)
        assert findings == []

    async def test_glossary_hit_missing_gloss_yields_finding(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        segment = await seed_segment(
            db_session,
            project=project,
            text="بسم الله\n---\nim Namen des Höchsten",  # gloss "Gottes" missing
        )
        ctx = _ctx(_entry("الله", "Gottes"))
        findings = rule_c_01(segment, ctx)
        assert len(findings) == 1
        ctx_dict = findings[0].detection_context
        assert ctx_dict["match"] == "glossary_lookup"
        assert ctx_dict["canonical_label"] == "الله"
        assert ctx_dict["expected_gloss"] == "Gottes"
        assert "concept_id" in ctx_dict

    async def test_canonical_label_not_in_source_no_finding(self, db_session: AsyncSession) -> None:
        # Glossary entry whose canonical_label doesn't appear in source —
        # the rule has nothing to flag against.
        project = await seed_project(db_session)
        segment = await seed_segment(
            db_session,
            project=project,
            text="نص آخر\n---\nirgendein anderer Text",
        )
        ctx = _ctx(_entry("الله", "Gottes"))
        findings = rule_c_01(segment, ctx)
        assert findings == []

    async def test_marker_and_glossary_findings_both_fire(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        segment = await seed_segment(
            db_session,
            project=project,
            text="بسم الله\n---\netwas anderes [TERM-VIOLATION]",
        )
        ctx = _ctx(_entry("الله", "Gottes"))
        findings = rule_c_01(segment, ctx)
        # One for the marker + one for the missing gloss.
        assert len(findings) == 2
        kinds = sorted(f.detection_context.get("match", "marker") for f in findings)
        assert "glossary_lookup" in kinds


# ---------------------------------------------------------------------
# build_default_rule_context + dispatcher integration
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestBuildDefaultRuleContext:
    async def test_pulls_active_concepts_only(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        active = Concept(
            concept_id=new_uuid(),
            canonical_label="الله",
            language="ar",
            gloss="Gottes",
            binding_level="project",
            project_uuid=project.project_uuid,
        )
        inactive = Concept(
            concept_id=new_uuid(),
            canonical_label="رسول",
            language="ar",
            gloss="Gesandter",
            binding_level="project",
            project_uuid=project.project_uuid,
            active=False,
        )
        no_gloss = Concept(
            concept_id=new_uuid(),
            canonical_label="نبي",
            language="ar",
            gloss=None,
            binding_level="project",
            project_uuid=project.project_uuid,
        )
        db_session.add_all([active, inactive, no_gloss])
        await db_session.flush()

        ctx = await build_default_rule_context(db_session, project.project_uuid)
        labels = sorted(e.canonical_label for e in ctx.glossary)
        # Inactive + no-gloss rows excluded.
        assert labels == ["الله"]


@pytest.mark.asyncio
class TestRunAuditWithGlossaryContext:
    async def test_findings_include_glossary_lookup_match(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await seed_segment(
            db_session,
            project=project,
            text="بسم الله\n---\nim Namen des Höchsten",
        )
        # Seed a glossary row + run the audit with the auto-built ctx.
        db_session.add(
            Concept(
                concept_id=new_uuid(),
                canonical_label="الله",
                language="ar",
                gloss="Gottes",
                binding_level="project",
                project_uuid=project.project_uuid,
            )
        )
        await db_session.flush()
        ctx = await build_default_rule_context(db_session, project.project_uuid)
        result = await run_audit_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            rules=[rule_c_01],
            rule_context=ctx,
        )
        assert result.befund_count >= 1
        from sqlalchemy import select

        rows = (
            await db_session.execute(select(Befund).where(Befund.regelkennung == "C-01"))
        ).scalars()
        assert any(r.detection_context.get("match") == "glossary_lookup" for r in rows)

    async def test_legacy_no_context_path_unchanged(self, db_session: AsyncSession) -> None:
        # Legacy callers (no ctx) get the marker-only behaviour. Sanity:
        # the same audit run with no ctx + a non-marker target doesn't
        # produce a C-01 finding.
        project = await seed_project(db_session)
        await seed_segment(
            db_session,
            project=project,
            text="بسم الله\n---\nim Namen des Höchsten",
        )
        db_session.add(
            Concept(
                concept_id=new_uuid(),
                canonical_label="الله",
                language="ar",
                gloss="Gottes",
                binding_level="project",
                project_uuid=project.project_uuid,
            )
        )
        await db_session.flush()
        result = await run_audit_for_project(
            session=db_session,
            project_uuid=project.project_uuid,
            rules=[rule_c_01],
            # Deliberately omit rule_context.
        )
        # Marker not present → no findings, even though glossary is mismatched.
        assert result.befund_count == 0


# Sanity: keep `uuid` reference live (used implicitly by helpers).
_ = uuid
