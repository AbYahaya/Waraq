"""Tests for §4.17 technical-term first-occurrence handling."""

from __future__ import annotations

import pytest

from waraq.identity import new_uuid
from waraq.schemas import Concept
from waraq.translation.chunk_context import ChunkContextResolver


def _concept(label: str, gloss: str = "Konsens") -> Concept:
    return Concept(
        concept_id=new_uuid(),
        canonical_label=label,
        language="ar",
        gloss=gloss,
        binding_level="project",
    )


# --- In-process: tracking within a single resolver --------------------


class TestFirstOccurrenceWithinRun:
    def test_first_chunk_all_hits_are_first_occurrence(self) -> None:
        c1 = _concept("إجماع", "Konsens")
        c2 = _concept("فقه", "Fiqh")
        resolver = ChunkContextResolver(glossary=[c1, c2], entities=[])
        brief = resolver.resolve("ذكر إجماع و فقه")
        assert len(brief.glossary_hits) == 2
        assert all(h.is_first_occurrence for h in brief.glossary_hits)

    def test_second_chunk_same_concept_subsequent_occurrence(self) -> None:
        c = _concept("إجماع", "Konsens")
        resolver = ChunkContextResolver(glossary=[c], entities=[])
        first = resolver.resolve("ذكر إجماع")
        second = resolver.resolve("إجماع آخر")
        assert first.glossary_hits[0].is_first_occurrence is True
        assert second.glossary_hits[0].is_first_occurrence is False

    def test_concept_first_seen_in_chunk_n_subsequent_in_chunk_n_plus_1(self) -> None:
        c1 = _concept("إجماع", "Konsens")
        c2 = _concept("فقه", "Fiqh")
        resolver = ChunkContextResolver(glossary=[c1, c2], entities=[])
        # Chunk 1: only إجماع
        b1 = resolver.resolve("ذكر إجماع الأمة")
        # Chunk 2: both — إجماع subsequent, فقه first
        b2 = resolver.resolve("في الفقه نجد الإجماع")
        assert b1.glossary_hits[0].is_first_occurrence is True
        # In b2: gather both hits and assert per-concept
        first_flags = {h.surface_form: h.is_first_occurrence for h in b2.glossary_hits}
        assert first_flags["إجماع"] is False
        assert first_flags["فقه"] is True

    def test_previously_used_seeds_subsequent_occurrence(self) -> None:
        """When the resolver is built with `previously_used_concept_ids`
        seeded (e.g., from prior TRANSLATION-PO rows), those concepts
        are NEVER first-occurrence even on the very first chunk."""
        c = _concept("إجماع", "Konsens")
        resolver = ChunkContextResolver(
            glossary=[c],
            entities=[],
            previously_used_concept_ids={c.concept_id},
        )
        brief = resolver.resolve("ذكر إجماع")
        assert brief.glossary_hits[0].is_first_occurrence is False


# --- Across runs (DB-backed) ------------------------------------------


@pytest.mark.asyncio
class TestFirstOccurrenceAcrossRuns:
    async def test_re_run_marks_subsequent_for_already_used_concepts(
        self,
    ) -> None:
        """First translation run records `concept_ids_used` on the
        TRANSLATION-PO. A second resolver built via `for_project`
        reads those rows and seeds `previously_used`, so the SECOND
        run's first chunk treats matched concepts as
        already-introduced."""
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.api._m4_fixtures import make_page_block_segment
        from tests.conftest import _test_database_url, seed_account_uuid
        from waraq.release_gate import start_translation
        from waraq.schemas import Project
        from waraq.translation import (
            make_translation_persistence_hook,
            run_translation_job,
            start_translation_job,
        )
        from waraq.translation.service import TranslationContext

        async def _stub_translator(_text: str, _ctx: TranslationContext) -> str:
            return "Konsens der Gemeinschaft"

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
                        name="first-occurrence-test",
                    )
                )
                await session.flush()
                # One glossary entry — the test concept.
                concept = _concept("إجماع", "Konsens")
                # `_concept` builds Concept without project binding — set it here:
                concept.project_uuid = project_uuid
                session.add(concept)

            seeded = await make_page_block_segment(str(project_uuid), text="ذكر إجماع الأمة")

            # First run: persistence hook records concept_ids_used.
            async with sm() as session, session.begin():
                await start_translation(session=session, project_uuid=project_uuid)
                job1 = await start_translation_job(
                    session=session,
                    project_uuid=project_uuid,
                    segment_uuids=[seeded.satz_uuid],
                )
                hook = make_translation_persistence_hook(engine_identifier="stub-test")
                await run_translation_job(
                    session=session,
                    job=job1,
                    translator=_stub_translator,
                    on_segment_translated=hook,
                )

            # Second run via `for_project`: should pre-seed the concept
            # as previously_used.
            async with sm() as session:
                resolver = await ChunkContextResolver.for_project(
                    session,
                    project_uuid=project_uuid,
                    account_uuid=account_uuid,
                )
                brief = resolver.resolve("ذكر إجماع")
                assert len(brief.glossary_hits) == 1
                # SECOND run sees concept as already-used → not first.
                assert brief.glossary_hits[0].is_first_occurrence is False
        finally:
            await engine.dispose()


# --- Prompt injection -------------------------------------------------


@pytest.mark.asyncio
class TestPromptInjectionFirstOccurrence:
    async def test_first_occurrence_directive_in_prompt(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When a hit is first-occurrence, the system prompt carries a
        `[FIRST OCCURRENCE — ...]` directive. When subsequent, the
        directive is `[subsequent occurrence ...]`."""
        from waraq.translation import openai_translator
        from waraq.translation.chunk_context import ChunkBrief, GlossaryHit
        from waraq.translation.service import TranslationContext

        captured: list[str] = []

        class _StubChoice:
            def __init__(self, content: str) -> None:
                self.message = type("M", (), {"content": content})()

        class _StubResponse:
            def __init__(self, content: str) -> None:
                self.choices = [_StubChoice(content)]

        class _StubChat:
            class completions:
                @staticmethod
                async def create(**kw: object) -> _StubResponse:
                    captured.append(kw["messages"][0]["content"])  # type: ignore[index]
                    return _StubResponse("[[L0001]] translated")

        class _StubClient:
            chat = _StubChat()

        monkeypatch.setenv("OPENAI_API_KEY", "stub")
        import openai

        monkeypatch.setattr(openai, "AsyncOpenAI", lambda **_: _StubClient())

        translator = openai_translator.make_openai_translator()

        # First-occurrence hit
        brief_first = ChunkBrief(
            glossary_hits=[
                GlossaryHit(
                    concept_id=new_uuid(),
                    surface_form="إجماع",
                    gloss="Konsens",
                    binding_level="project",
                    is_first_occurrence=True,
                )
            ]
        )
        await translator("dummy", TranslationContext().with_chunk_brief(brief_first))
        assert "FIRST OCCURRENCE" in captured[-1]
        assert "إجماع" in captured[-1]
        assert "Konsens" in captured[-1]
        assert "Anm.:" in captured[-1]

        # Subsequent hit
        brief_subsequent = ChunkBrief(
            glossary_hits=[
                GlossaryHit(
                    concept_id=new_uuid(),
                    surface_form="إجماع",
                    gloss="Konsens",
                    binding_level="project",
                    is_first_occurrence=False,
                )
            ]
        )
        await translator("dummy", TranslationContext().with_chunk_brief(brief_subsequent))
        assert "subsequent occurrence" in captured[-1]
        assert "FIRST OCCURRENCE" not in captured[-1]


# --- TRANSLATION-PO records concept_ids_used --------------------------


@pytest.mark.asyncio
class TestPersistenceRecordsConceptIds:
    async def test_concept_ids_used_recorded_on_po(self) -> None:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.api._m4_fixtures import make_page_block_segment
        from tests.conftest import _test_database_url, seed_account_uuid
        from waraq.release_gate import start_translation
        from waraq.schemas import Project, ProvenanceObject
        from waraq.schemas.enums import POType
        from waraq.translation import (
            make_translation_persistence_hook,
            run_translation_job,
            start_translation_job,
        )
        from waraq.translation.service import TranslationContext

        async def _stub_translator(_text: str, _ctx: TranslationContext) -> str:
            return "Konsens und Fiqh"

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        try:
            account_uuid = new_uuid()
            project_uuid = new_uuid()
            c1 = _concept("إجماع", "Konsens")
            c2 = _concept("فقه", "Fiqh")
            async with sm() as session, session.begin():
                await seed_account_uuid(session, account_uuid)
                session.add(
                    Project(
                        project_uuid=project_uuid,
                        account_uuid=account_uuid,
                        name="concept-ids-test",
                    )
                )
                await session.flush()
                c1.project_uuid = project_uuid
                c2.project_uuid = project_uuid
                session.add_all([c1, c2])

            seeded = await make_page_block_segment(str(project_uuid), text="ذكر إجماع و فقه")

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
                    translator=_stub_translator,
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
                assert "concept_ids_used" in payload
                ids = set(payload["concept_ids_used"])
                assert str(c1.concept_id) in ids
                assert str(c2.concept_id) in ids
        finally:
            await engine.dispose()
