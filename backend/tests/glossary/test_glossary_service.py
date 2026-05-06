"""T-5.2.1 — GLOSSARY service tests.

Mandatory tests from Sprint 1 §4:
- T-KE-01 — `lookup` returns explicit Konzept-ID or `NO_ENTRY`, never null.
- Glossar-Lookup-Explicit-No-Entry-Test
- Glossar-Eintrag-Aenderung-Decision-Event-Test (project + account)
- Glossar-Kein-Auto-Erzeugung-Test (no bypass entrypoints)

Glossar-Kein-Auto-Ueberschreiben-Gesperrt-Test belongs in T-5.1.2 (it
exercises detect_conflict on a glossary apply against a locked Segment).
That coverage lands with the conflict_instance work; this file confirms
the glossary side of the contract (lookup/CRUD).
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.glossary import (
    NO_ENTRY,
    BindingLevel,
    InvalidBindingScope,
    NoEntrySentinel,
    SurfaceFormAlreadyExists,
    create_entry,
    get_entry,
    lookup,
    update_entry,
)
from waraq.identity import new_uuid
from waraq.schemas import DecisionEvent, Project
from waraq.schemas.enums import DecisionSource, ScopeType


async def _seed_account(session: AsyncSession):  # type: ignore[no-untyped-def]
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)
    return account_uuid


async def _seed_project(session: AsyncSession):  # type: ignore[no-untyped-def]
    account_uuid = await _seed_account(session)
    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="glossary-test")
    session.add(project)
    await session.flush()
    return project, account_uuid


# --- Layer 1: surface contract -------------------------------------------


class TestT_5_2_1_NoAutoCreationSurface:
    """Glossar-Kein-Auto-Erzeugung-Test.

    The module exposes only the canonical CRUD + lookup entrypoints. No
    bulk/seed/auto creation surface is permitted (Sprint 1 §2)."""

    def test_module_exposes_only_canonical_glossary_entrypoints(self) -> None:
        import inspect as _inspect
        import types

        import waraq.glossary as glossary_module

        functions = {
            name
            for name, obj in vars(glossary_module).items()
            if not name.startswith("_")
            and callable(obj)
            and not isinstance(obj, type)
            and not isinstance(obj, types.ModuleType)
            and _inspect.getmodule(obj) is not None
            and _inspect.getmodule(obj).__name__.startswith("waraq.glossary")  # type: ignore[union-attr]
        }
        assert functions == {"lookup", "get_entry", "create_entry", "update_entry"}, (
            f"waraq.glossary exposes unexpected operations: {functions}"
        )

    def test_no_bulk_or_auto_kwarg_in_create_signature(self) -> None:
        # No `bulk=`, `auto=`, `from_corpus=`, `from_ocr=` kwargs.
        params = set(inspect.signature(create_entry).parameters)
        suspicious = {p for p in params if any(t in p.lower() for t in ("bulk", "auto"))}
        assert suspicious == set()


# --- Layer 2: lookup return contract (T-KE-01) ---------------------------


@pytest.mark.asyncio
class TestT_5_2_1_LookupExplicitReturnContract:
    """T-KE-01 + Glossar-Lookup-Explicit-No-Entry-Test."""

    async def test_miss_returns_no_entry_sentinel(self, db_session: AsyncSession) -> None:
        project, _ = await _seed_project(db_session)

        result = await lookup(
            session=db_session,
            surface_form="never-existed",
            project_uuid=project.project_uuid,
        )
        assert result is NO_ENTRY
        # Defense in depth — the sentinel is its own type, not None.
        assert result is not None
        assert isinstance(result, NoEntrySentinel)

    async def test_no_entry_is_a_singleton(self) -> None:
        # The sentinel pattern relies on `is NO_ENTRY` checks; constructing
        # NoEntrySentinel() must always return the same instance.
        from waraq.glossary import NO_ENTRY as NO_ENTRY_RECHECK

        assert NO_ENTRY is NO_ENTRY_RECHECK
        assert NoEntrySentinel() is NO_ENTRY

    async def test_hit_returns_concept_id_uuid(self, db_session: AsyncSession) -> None:
        project, _ = await _seed_project(db_session)
        concept, _ = await create_entry(
            session=db_session,
            canonical_label="al-Tirmidhi",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )

        result = await lookup(
            session=db_session,
            surface_form="al-Tirmidhi",
            project_uuid=project.project_uuid,
        )
        assert result == concept.concept_id

    async def test_lookup_is_case_insensitive(self, db_session: AsyncSession) -> None:
        project, _ = await _seed_project(db_session)
        concept, _ = await create_entry(
            session=db_session,
            canonical_label="al-Bukhari",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )

        for variant in ("AL-BUKHARI", "al-bukhari", " Al-Bukhari "):
            result = await lookup(
                session=db_session,
                surface_form=variant,
                project_uuid=project.project_uuid,
            )
            assert result == concept.concept_id

    async def test_lookup_requires_at_least_one_scope(self, db_session: AsyncSession) -> None:
        with pytest.raises(InvalidBindingScope):
            await lookup(session=db_session, surface_form="anything")


@pytest.mark.asyncio
class TestT_5_2_1_LookupScopeOverride:
    """Project-bound entries override account-bound entries with the same
    surface form. Confirms the scope cascade documented in `lookup`."""

    async def test_project_entry_shadows_account_entry(self, db_session: AsyncSession) -> None:
        project, account_uuid = await _seed_project(db_session)

        account_concept, _ = await create_entry(
            session=db_session,
            canonical_label="iʿtibār",
            language="ar",
            binding_level=BindingLevel.ACCOUNT,
            account_uuid=account_uuid,
        )
        project_concept, _ = await create_entry(
            session=db_session,
            canonical_label="iʿtibār",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )

        result = await lookup(
            session=db_session,
            surface_form="iʿtibār",
            project_uuid=project.project_uuid,
            account_uuid=account_uuid,
        )
        # Project entry wins.
        assert result == project_concept.concept_id
        assert result != account_concept.concept_id

    async def test_account_only_lookup_finds_account_entry(self, db_session: AsyncSession) -> None:
        _, account_uuid = await _seed_project(db_session)
        concept, _ = await create_entry(
            session=db_session,
            canonical_label="ḥadīth",
            language="ar",
            binding_level=BindingLevel.ACCOUNT,
            account_uuid=account_uuid,
        )

        result = await lookup(session=db_session, surface_form="ḥadīth", account_uuid=account_uuid)
        assert result == concept.concept_id


# --- Layer 2: create / update Decision-Event coverage --------------------


@pytest.mark.asyncio
class TestT_5_2_1_CreateAndUpdateDecisionEvents:
    """Glossar-Eintrag-Aenderung-Decision-Event-Test (project + account)."""

    async def test_create_project_bound_writes_decision_event_with_scope_project(
        self, db_session: AsyncSession
    ) -> None:
        project, _ = await _seed_project(db_session)
        actor = new_uuid()
        from tests.conftest import seed_account_uuid

        await seed_account_uuid(db_session, actor)

        concept, de = await create_entry(
            session=db_session,
            canonical_label="muḥaddith",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
            actor_uuid=actor,
        )

        assert str(de.scope_type) == ScopeType.PROJECT.value
        assert de.scope_uuid == project.project_uuid
        assert str(de.decision_source) == DecisionSource.GLOSSARY_MANAGEMENT.value
        assert de.decision_type == "glossary_create"
        assert de.actor_uuid == actor
        assert de.content["concept_id"] == str(concept.concept_id)
        assert de.content["binding_level"] == BindingLevel.PROJECT.value

    async def test_create_account_bound_writes_decision_event_with_scope_account(
        self, db_session: AsyncSession
    ) -> None:
        _, account_uuid = await _seed_project(db_session)

        _concept, de = await create_entry(
            session=db_session,
            canonical_label="riwāya",
            language="ar",
            binding_level=BindingLevel.ACCOUNT,
            account_uuid=account_uuid,
        )

        assert str(de.scope_type) == ScopeType.ACCOUNT.value
        assert de.scope_uuid == account_uuid
        assert de.content["binding_level"] == BindingLevel.ACCOUNT.value

    async def test_update_writes_decision_event_with_prior_and_new_values(
        self, db_session: AsyncSession
    ) -> None:
        project, _ = await _seed_project(db_session)
        concept, _ = await create_entry(
            session=db_session,
            canonical_label="sanad",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
            gloss="chain of authorities",
        )

        de = await update_entry(
            session=db_session,
            concept=concept,
            gloss="Überlieferungskette",
        )

        assert de.decision_type == "glossary_update"
        assert str(de.scope_type) == ScopeType.PROJECT.value
        assert de.scope_uuid == project.project_uuid
        assert de.content["prior_gloss"] == "chain of authorities"
        assert de.content["new_gloss"] == "Überlieferungskette"
        assert de.content["new_canonical_label"] == "sanad"  # unchanged

    async def test_update_with_no_changes_raises(self, db_session: AsyncSession) -> None:
        project, _ = await _seed_project(db_session)
        concept, _ = await create_entry(
            session=db_session,
            canonical_label="x",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )

        with pytest.raises(ValueError, match="no mutable field changes"):
            await update_entry(session=db_session, concept=concept)

    async def test_create_refuses_invalid_binding_scope(self, db_session: AsyncSession) -> None:
        # binding_level=PROJECT but no project_uuid set.
        with pytest.raises(InvalidBindingScope):
            await create_entry(
                session=db_session,
                canonical_label="x",
                language="ar",
                binding_level=BindingLevel.PROJECT,
            )

        # binding_level=ACCOUNT but project_uuid set.
        project, _ = await _seed_project(db_session)
        with pytest.raises(InvalidBindingScope):
            await create_entry(
                session=db_session,
                canonical_label="x",
                language="ar",
                binding_level=BindingLevel.ACCOUNT,
                project_uuid=project.project_uuid,
            )

    async def test_create_refuses_duplicate_surface_form_in_same_scope(
        self, db_session: AsyncSession
    ) -> None:
        project, _ = await _seed_project(db_session)
        await create_entry(
            session=db_session,
            canonical_label="ʿadāla",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )

        with pytest.raises(SurfaceFormAlreadyExists):
            await create_entry(
                session=db_session,
                canonical_label="ʿadāla",
                language="ar",
                binding_level=BindingLevel.PROJECT,
                project_uuid=project.project_uuid,
            )


# --- Layer 2: get_entry --------------------------------------------------


@pytest.mark.asyncio
class TestT_5_2_1_GetEntry:
    async def test_get_entry_returns_concept_row(self, db_session: AsyncSession) -> None:
        project, _ = await _seed_project(db_session)
        concept, _ = await create_entry(
            session=db_session,
            canonical_label="ʿillah",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )

        loaded = await get_entry(session=db_session, concept_id=concept.concept_id)
        assert loaded is not None
        assert loaded.concept_id == concept.concept_id
        assert loaded.canonical_label == "ʿillah"

    async def test_get_entry_returns_none_for_unknown(self, db_session: AsyncSession) -> None:
        loaded = await get_entry(session=db_session, concept_id=new_uuid())
        assert loaded is None


# --- Layer 3: cross-table discipline -------------------------------------


@pytest.mark.asyncio
class TestT_5_2_1_CrossTableDiscipline:
    async def test_lookup_writes_no_decision_event(self, db_session: AsyncSession) -> None:
        project, _ = await _seed_project(db_session)
        before = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()

        await lookup(session=db_session, surface_form="x", project_uuid=project.project_uuid)

        after = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        assert after == before
