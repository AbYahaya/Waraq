"""Tests for §3.6 chunk-context resolver + prompt injection."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.schemas import Account, Concept, Entity, Project
from waraq.translation.chunk_context import (
    ChunkBrief,
    ChunkContextResolver,
    EntityHit,
    GlossaryHit,
)
from waraq.translation.service import TranslationContext


async def _seed_project(session: AsyncSession) -> tuple[Project, Account]:
    account = Account(
        account_uuid=new_uuid(),
        email=f"chunk-{new_uuid()}@waraq.test",
        password_hash="x",
        active=True,
    )
    session.add(account)
    await session.flush()
    project = Project(
        project_uuid=new_uuid(),
        account_uuid=account.account_uuid,
        name="Chunk-context test",
    )
    session.add(project)
    await session.flush()
    return project, account


@pytest.mark.asyncio
class TestResolverFromProject:
    async def test_loads_project_glossary_and_entities(self, db_session: AsyncSession) -> None:
        project, account = await _seed_project(db_session)
        db_session.add(
            Concept(
                concept_id=new_uuid(),
                canonical_label="إجماع",
                language="ar",
                gloss="Konsens",
                binding_level="project",
                project_uuid=project.project_uuid,
            )
        )
        db_session.add(
            Entity(
                entity_id=new_uuid(),
                category="scholar_or_person",
                canonical_label="البخاري",
                language="ar",
                short_bio="Hadith compiler",
                binding_level="project",
                project_uuid=project.project_uuid,
            )
        )
        await db_session.flush()

        resolver = await ChunkContextResolver.for_project(
            db_session,
            project_uuid=project.project_uuid,
            account_uuid=account.account_uuid,
        )
        # Source text contains both terms
        brief = resolver.resolve("روى البخاري عن إجماع الأمة على هذا.")
        assert len(brief.glossary_hits) == 1
        assert brief.glossary_hits[0].surface_form == "إجماع"
        assert brief.glossary_hits[0].gloss == "Konsens"
        assert brief.glossary_hits[0].binding_level == "project"
        assert len(brief.entity_hits) == 1
        assert brief.entity_hits[0].surface_form == "البخاري"
        assert brief.entity_hits[0].category == "scholar_or_person"

    async def test_loads_account_scoped_entries(self, db_session: AsyncSession) -> None:
        project, account = await _seed_project(db_session)
        db_session.add(
            Concept(
                concept_id=new_uuid(),
                canonical_label="فقه",
                language="ar",
                gloss="Fiqh",
                binding_level="account",
                account_uuid=account.account_uuid,
            )
        )
        await db_session.flush()
        resolver = await ChunkContextResolver.for_project(
            db_session,
            project_uuid=project.project_uuid,
            account_uuid=account.account_uuid,
        )
        brief = resolver.resolve("علم الفقه واسع")
        assert len(brief.glossary_hits) == 1
        assert brief.glossary_hits[0].binding_level == "account"

    async def test_skips_inactive_entries(self, db_session: AsyncSession) -> None:
        project, account = await _seed_project(db_session)
        c = Concept(
            concept_id=new_uuid(),
            canonical_label="إجماع",
            language="ar",
            gloss="Konsens",
            binding_level="project",
            project_uuid=project.project_uuid,
        )
        c.active = False
        db_session.add(c)
        await db_session.flush()
        resolver = await ChunkContextResolver.for_project(
            db_session,
            project_uuid=project.project_uuid,
            account_uuid=account.account_uuid,
        )
        brief = resolver.resolve("ذكر الإجماع")
        assert brief.is_empty

    async def test_no_match_returns_empty_brief(self, db_session: AsyncSession) -> None:
        project, account = await _seed_project(db_session)
        db_session.add(
            Concept(
                concept_id=new_uuid(),
                canonical_label="إجماع",
                language="ar",
                gloss="Konsens",
                binding_level="project",
                project_uuid=project.project_uuid,
            )
        )
        await db_session.flush()
        resolver = await ChunkContextResolver.for_project(
            db_session,
            project_uuid=project.project_uuid,
            account_uuid=account.account_uuid,
        )
        brief = resolver.resolve("هذا نص بدون مصطلحات معجمية.")
        assert brief.is_empty

    async def test_skips_entries_without_gloss(self, db_session: AsyncSession) -> None:
        project, account = await _seed_project(db_session)
        db_session.add(
            Concept(
                concept_id=new_uuid(),
                canonical_label="إجماع",
                language="ar",
                gloss=None,  # No translation set
                binding_level="project",
                project_uuid=project.project_uuid,
            )
        )
        await db_session.flush()
        resolver = await ChunkContextResolver.for_project(
            db_session,
            project_uuid=project.project_uuid,
            account_uuid=account.account_uuid,
        )
        brief = resolver.resolve("ذكر إجماع")
        # No gloss = no enforceable rendering = no hit
        assert not brief.glossary_hits


class TestResolverInProcess:
    """Pure-Python tests of `ChunkContextResolver.resolve` without DB."""

    def test_longer_match_preferred_over_shorter(self) -> None:
        # Both labels match the source; resolver should prefer the longer
        # canonical_label (sorted-by-length descending).
        long_concept = Concept(
            concept_id=new_uuid(),
            canonical_label="إجماع الأمة",
            language="ar",
            gloss="Konsens der Gemeinschaft",
            binding_level="project",
        )
        short_concept = Concept(
            concept_id=new_uuid(),
            canonical_label="إجماع",
            language="ar",
            gloss="Konsens",
            binding_level="project",
        )
        resolver = ChunkContextResolver(glossary=[short_concept, long_concept], entities=[])
        brief = resolver.resolve("ذكر إجماع الأمة في هذا الباب")
        # Both hit (the short label is a substring of the long one), but
        # the long label appears first in the result list.
        labels = [h.surface_form for h in brief.glossary_hits]
        assert labels[0] == "إجماع الأمة"

    def test_empty_source_returns_empty_brief(self) -> None:
        resolver = ChunkContextResolver(glossary=[], entities=[])
        assert resolver.resolve("").is_empty
        assert resolver.resolve("anything").is_empty


# --- Translation context wiring ----------------------------------------


class TestTranslationContextChunkBrief:
    def test_with_chunk_brief_attaches_transiently(self) -> None:
        ctx = TranslationContext()
        assert ctx.chunk_brief is None
        brief = ChunkBrief(
            glossary_hits=[
                GlossaryHit(
                    concept_id=new_uuid(),
                    surface_form="إجماع",
                    gloss="Konsens",
                    binding_level="project",
                )
            ]
        )
        new_ctx = ctx.with_chunk_brief(brief)
        assert new_ctx.chunk_brief is brief
        # Original context unchanged (frozen dataclass)
        assert ctx.chunk_brief is None

    def test_to_dict_excludes_chunk_brief(self) -> None:
        brief = ChunkBrief(glossary_hits=[])
        ctx = TranslationContext().with_chunk_brief(brief)
        serialized = ctx.to_dict()
        assert "chunk_brief" not in serialized

    def test_with_translated_drops_chunk_brief(self) -> None:
        # Forwarding the context to the next chunk must drop the previous
        # chunk's brief (it would be wrong to reuse it for a different
        # source segment).
        brief = ChunkBrief(glossary_hits=[])
        ctx = TranslationContext().with_chunk_brief(brief)
        next_ctx = ctx.with_translated("German output")
        assert next_ctx.chunk_brief is None


# --- Prompt injection (translator integration) -------------------------


@pytest.mark.asyncio
class TestPromptInjection:
    async def test_glossary_hits_appear_in_system_prompt(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from waraq.translation import openai_translator

        captured_messages: list[Any] = []

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
                    captured_messages.append(kw["messages"])
                    return _StubResponse("translated")

        class _StubClient:
            chat = _StubChat()

        monkeypatch.setenv("OPENAI_API_KEY", "stub")
        import openai

        monkeypatch.setattr(openai, "AsyncOpenAI", lambda **_: _StubClient())

        translator = openai_translator.make_openai_translator()
        brief = ChunkBrief(
            glossary_hits=[
                GlossaryHit(
                    concept_id=new_uuid(),
                    surface_form="إجماع",
                    gloss="Konsens",
                    binding_level="project",
                )
            ],
            entity_hits=[
                EntityHit(
                    entity_id=new_uuid(),
                    category="scholar_or_person",
                    surface_form="البخاري",
                    canonical_label="البخاري",
                    short_bio="Hadith compiler",
                    binding_level="project",
                )
            ],
        )
        ctx = TranslationContext().with_chunk_brief(brief)
        await translator("dummy source", ctx)

        assert len(captured_messages) == 1
        system_msg = captured_messages[0][0]["content"]
        assert "إجماع" in system_msg
        assert "Konsens" in system_msg
        assert "Tier 1" in system_msg  # the glossary precedence note
        assert "البخاري" in system_msg
        assert "scholar_or_person" in system_msg

    async def test_empty_brief_omits_terminology_block(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from waraq.translation import openai_translator

        captured_messages: list[Any] = []

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
                    captured_messages.append(kw["messages"])
                    return _StubResponse("translated")

        class _StubClient:
            chat = _StubChat()

        monkeypatch.setenv("OPENAI_API_KEY", "stub")
        import openai

        monkeypatch.setattr(openai, "AsyncOpenAI", lambda **_: _StubClient())

        translator = openai_translator.make_openai_translator()
        await translator("dummy", TranslationContext())

        system_msg = captured_messages[0][0]["content"]
        assert "TERMINOLOGY" not in system_msg
        assert "NAMED ENTITIES" not in system_msg
