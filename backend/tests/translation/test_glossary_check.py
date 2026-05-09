"""Tests for §2.2 / §4.12.1 Tier 1 glossary precedence verifier."""

from __future__ import annotations

import pytest

from waraq.identity import new_uuid
from waraq.translation.chunk_context import ChunkBrief, GlossaryHit
from waraq.translation.glossary_check import (
    GlossaryViolation,
    verify_glossary_precedence,
)


def _hit(surface: str, gloss: str, binding: str = "project") -> GlossaryHit:
    return GlossaryHit(
        concept_id=new_uuid(),
        surface_form=surface,
        gloss=gloss,
        binding_level=binding,
    )


class TestVerifyGlossaryPrecedence:
    def test_empty_brief_returns_no_violations(self) -> None:
        assert verify_glossary_precedence(brief=None, output_text="x") == []
        assert verify_glossary_precedence(brief=ChunkBrief(), output_text="x") == []

    def test_gloss_present_no_violation(self) -> None:
        brief = ChunkBrief(glossary_hits=[_hit("إجماع", "Konsens")])
        out = "Es gab den Konsens der Gemeinschaft."
        assert verify_glossary_precedence(brief=brief, output_text=out) == []

    def test_gloss_missing_one_violation(self) -> None:
        brief = ChunkBrief(glossary_hits=[_hit("إجماع", "Konsens")])
        # The translator used "Übereinstimmung" instead of the canonical
        # "Konsens" — a violation per §2.2 Tier 1.
        out = "Es gab Übereinstimmung der Gemeinschaft."
        violations = verify_glossary_precedence(brief=brief, output_text=out)
        assert len(violations) == 1
        assert violations[0].surface_form == "إجماع"
        assert violations[0].expected_gloss == "Konsens"
        assert violations[0].binding_level == "project"

    def test_case_insensitive_match_no_violation(self) -> None:
        # Mixed case should still match.
        brief = ChunkBrief(glossary_hits=[_hit("فقه", "Fiqh")])
        out = "Das ist ein Beispiel für FIQH."
        assert verify_glossary_precedence(brief=brief, output_text=out) == []

    def test_substring_match_handles_morphology(self) -> None:
        # German inflection: "Konsenses" (genitive) contains "Konsens".
        brief = ChunkBrief(glossary_hits=[_hit("إجماع", "Konsens")])
        out = "Die Konsenses Bedeutung ist klar."
        assert verify_glossary_precedence(brief=brief, output_text=out) == []

    def test_multiple_hits_some_missing(self) -> None:
        brief = ChunkBrief(
            glossary_hits=[
                _hit("إجماع", "Konsens"),
                _hit("فقه", "Fiqh"),
                _hit("سنة", "Sunna"),
            ]
        )
        # Output uses Konsens and Fiqh, but uses "Tradition" instead of Sunna.
        out = "Konsens und Fiqh, aber Tradition."
        violations = verify_glossary_precedence(brief=brief, output_text=out)
        assert len(violations) == 1
        assert violations[0].surface_form == "سنة"
        assert violations[0].expected_gloss == "Sunna"

    def test_empty_output_all_hits_become_violations(self) -> None:
        brief = ChunkBrief(
            glossary_hits=[
                _hit("إجماع", "Konsens"),
                _hit("فقه", "Fiqh"),
            ]
        )
        violations = verify_glossary_precedence(brief=brief, output_text="")
        assert len(violations) == 2

    def test_skips_entries_without_gloss(self) -> None:
        # Defensive: even if a hit slipped through with empty gloss,
        # we don't flag it (nothing enforceable).
        brief = ChunkBrief(glossary_hits=[_hit("إجماع", "")])
        violations = verify_glossary_precedence(brief=brief, output_text="x")
        assert violations == []

    def test_violation_payload_shape(self) -> None:
        v = GlossaryViolation(
            surface_form="إجماع",
            expected_gloss="Konsens",
            binding_level="account",
            concept_id="abc-123",
        )
        payload = v.to_payload()
        assert payload == {
            "surface_form": "إجماع",
            "expected_gloss": "Konsens",
            "binding_level": "account",
            "concept_id": "abc-123",
        }


# --- Persistence-hook integration --------------------------------------


@pytest.mark.asyncio
class TestGlossaryViolationOnTranslationPo:
    """Full end-to-end: a translation chunk with a glossary hit + an LLM
    output that doesn't honor it should produce a TRANSLATION-PO with a
    `glossary_precedence_violations` block."""

    async def test_violation_recorded_in_translation_po(self) -> None:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.api._m4_fixtures import make_page_block_segment
        from tests.conftest import _test_database_url, seed_account_uuid
        from waraq.release_gate import start_translation
        from waraq.schemas import Concept, Project, ProvenanceObject
        from waraq.schemas.enums import POType
        from waraq.translation import (
            make_translation_persistence_hook,
            run_translation_job,
            start_translation_job,
        )
        from waraq.translation.service import TranslationContext

        # Stub translator that ignores the chunk_brief and emits a
        # German rendering that violates the glossary.
        async def _ignoring_translator(_text: str, _ctx: TranslationContext) -> str:
            # Emits "Übereinstimmung" instead of "Konsens".
            return "Es gab Übereinstimmung der Gemeinschaft."

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        try:
            account_uuid = new_uuid()
            project_uuid = new_uuid()
            async with sm() as session, session.begin():
                await seed_account_uuid(session, account_uuid)
                session.add(
                    Project(
                        project_uuid=project_uuid,
                        account_uuid=account_uuid,
                        name="glossary-violation",
                    )
                )
                await session.flush()
                # Glossary entry: "إجماع" → "Konsens"
                session.add(
                    Concept(
                        concept_id=new_uuid(),
                        canonical_label="إجماع",
                        language="ar",
                        gloss="Konsens",
                        binding_level="project",
                        project_uuid=project_uuid,
                    )
                )

            seeded = await make_page_block_segment(
                str(project_uuid), text="ذكر إجماع الأمة على هذا"
            )

            async with sm() as session, session.begin():
                await start_translation(session=session, project_uuid=project_uuid)
                job = await start_translation_job(
                    session=session,
                    project_uuid=project_uuid,
                    segment_uuids=[seeded.satz_uuid],
                )
                hook = make_translation_persistence_hook(engine_identifier="stub-test")
                await run_translation_job(
                    session=session,
                    job=job,
                    translator=_ignoring_translator,
                    on_segment_translated=hook,
                )

            async with sm() as session:
                pos = list(
                    (
                        await session.execute(
                            select(ProvenanceObject)
                            .where(ProvenanceObject.scope_uuid == seeded.satz_uuid)
                            .where(ProvenanceObject.po_type == POType.TRANSLATION.value)
                        )
                    ).scalars()
                )
                assert len(pos) == 1
                payload = pos[0].payload or {}
                assert "glossary_precedence_violations" in payload
                vlist = payload["glossary_precedence_violations"]
                assert len(vlist) == 1
                assert vlist[0]["surface_form"] == "إجماع"
                assert vlist[0]["expected_gloss"] == "Konsens"
        finally:
            await engine.dispose()

    async def test_no_violation_block_when_compliant(self) -> None:
        """When the translator honors the glossary, the TRANSLATION-PO
        must NOT carry a violations block."""
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.api._m4_fixtures import make_page_block_segment
        from tests.conftest import _test_database_url, seed_account_uuid
        from waraq.release_gate import start_translation
        from waraq.schemas import Concept, Project, ProvenanceObject
        from waraq.schemas.enums import POType
        from waraq.translation import (
            make_translation_persistence_hook,
            run_translation_job,
            start_translation_job,
        )
        from waraq.translation.service import TranslationContext

        async def _compliant_translator(_text: str, _ctx: TranslationContext) -> str:
            return "Konsens der Gemeinschaft auf diesem Punkt."

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        try:
            account_uuid = new_uuid()
            project_uuid = new_uuid()
            async with sm() as session, session.begin():
                await seed_account_uuid(session, account_uuid)
                session.add(
                    Project(
                        project_uuid=project_uuid,
                        account_uuid=account_uuid,
                        name="glossary-compliant",
                    )
                )
                await session.flush()
                session.add(
                    Concept(
                        concept_id=new_uuid(),
                        canonical_label="إجماع",
                        language="ar",
                        gloss="Konsens",
                        binding_level="project",
                        project_uuid=project_uuid,
                    )
                )

            seeded = await make_page_block_segment(
                str(project_uuid), text="ذكر إجماع الأمة على هذا"
            )

            async with sm() as session, session.begin():
                await start_translation(session=session, project_uuid=project_uuid)
                job = await start_translation_job(
                    session=session,
                    project_uuid=project_uuid,
                    segment_uuids=[seeded.satz_uuid],
                )
                hook = make_translation_persistence_hook(engine_identifier="stub-test")
                await run_translation_job(
                    session=session,
                    job=job,
                    translator=_compliant_translator,
                    on_segment_translated=hook,
                )

            async with sm() as session:
                pos = list(
                    (
                        await session.execute(
                            select(ProvenanceObject)
                            .where(ProvenanceObject.scope_uuid == seeded.satz_uuid)
                            .where(ProvenanceObject.po_type == POType.TRANSLATION.value)
                        )
                    ).scalars()
                )
                assert len(pos) == 1
                payload = pos[0].payload or {}
                assert "glossary_precedence_violations" not in payload
        finally:
            await engine.dispose()
