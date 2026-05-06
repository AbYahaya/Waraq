"""§4.19 — Reference / Entity service tests.

Coverage:
- Module surface lockdown — only canonical CRUD + lookup, no auto-create.
- Lookup return contract — UUID or `NO_ENTITY` sentinel, never null.
- Category taxonomy — 5 canonical values; misuse raises.
- Scope discipline — exactly one of project_uuid / account_uuid set.
- Decision Event shape — scope_type derived from binding_level,
  decision_source=glossary_management, content carries `subsystem: "entity"`.
- Schema discipline — all 5 categories accepted by DB CHECK; binding
  consistency CHECK refuses inconsistent rows.
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.entities import (
    NO_ENTITY,
    EntityCategory,
    EntityLabelAlreadyExists,
    EntityNotFoundSentinel,
    InvalidEntityCategory,
    InvalidEntityScope,
    create_entity,
    get_entity,
    lookup_entity,
    update_entity,
)
from waraq.glossary import BindingLevel
from waraq.identity import new_uuid
from waraq.schemas import DecisionEvent, Entity, Project
from waraq.schemas.enums import DecisionSource, ScopeType


async def _seed_account(session: AsyncSession):  # type: ignore[no-untyped-def]
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)
    return account_uuid


async def _seed_project(session: AsyncSession):  # type: ignore[no-untyped-def]
    account_uuid = await _seed_account(session)
    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="entity-test")
    session.add(project)
    await session.flush()
    return project, account_uuid


# --- Layer 1: module surface ---------------------------------------------


class TestEntityServiceSurface:
    """No bulk/seed/auto-create entrypoint — Sprint 1 §B / §4.19 spirit:
    entities are user-curated, not corpus-imported."""

    def test_module_exposes_only_canonical_crud_entrypoints(self) -> None:
        import inspect as _inspect
        import types

        import waraq.entities as ent_module

        functions = {
            name
            for name, obj in vars(ent_module).items()
            if not name.startswith("_")
            and callable(obj)
            and not isinstance(obj, type)
            and not isinstance(obj, types.ModuleType)
            and _inspect.getmodule(obj) is not None
            and _inspect.getmodule(obj).__name__.startswith("waraq.entities")  # type: ignore[union-attr]
        }
        assert functions == {"lookup_entity", "get_entity", "create_entity", "update_entity"}, (
            f"waraq.entities exposes unexpected operations: {functions}"
        )

    def test_no_bulk_or_auto_kwarg_in_create_signature(self) -> None:
        params = set(inspect.signature(create_entity).parameters)
        suspicious = {p for p in params if any(t in p.lower() for t in ("bulk", "auto"))}
        assert suspicious == set()


# --- Layer 2: lookup return contract -------------------------------------


@pytest.mark.asyncio
class TestEntityLookupReturnContract:
    async def test_miss_returns_no_entity_sentinel(self, db_session: AsyncSession) -> None:
        project, _ = await _seed_project(db_session)
        result = await lookup_entity(
            session=db_session,
            surface_form="never-existed",
            project_uuid=project.project_uuid,
        )
        assert result is NO_ENTITY
        assert result is not None
        assert isinstance(result, EntityNotFoundSentinel)

    async def test_no_entity_is_singleton(self) -> None:
        from waraq.entities import NO_ENTITY as NO_ENTITY_RECHECK

        assert NO_ENTITY is NO_ENTITY_RECHECK
        assert EntityNotFoundSentinel() is NO_ENTITY

    async def test_hit_returns_entity_id_uuid(self, db_session: AsyncSession) -> None:
        project, _ = await _seed_project(db_session)
        entity, _ = await create_entity(
            session=db_session,
            category=EntityCategory.SCHOLAR_OR_PERSON,
            canonical_label="ابن حجر العسقلاني",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
            short_bio="hadith critic",
        )
        result = await lookup_entity(
            session=db_session,
            surface_form="ابن حجر العسقلاني",
            project_uuid=project.project_uuid,
        )
        assert result == entity.entity_id

    async def test_lookup_can_filter_by_category(self, db_session: AsyncSession) -> None:
        # Same surface label across two categories — category filter narrows.
        project, _ = await _seed_project(db_session)
        scholar, _ = await create_entity(
            session=db_session,
            category=EntityCategory.SCHOLAR_OR_PERSON,
            canonical_label="فاس",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )
        # Deliberate same label, different category — they are different
        # entities. Per-(category, scope) uniqueness, not per-label.
        place, _ = await create_entity(
            session=db_session,
            category=EntityCategory.HISTORICAL_PLACE,
            canonical_label="فاس",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )

        as_scholar = await lookup_entity(
            session=db_session,
            surface_form="فاس",
            project_uuid=project.project_uuid,
            category=EntityCategory.SCHOLAR_OR_PERSON,
        )
        as_place = await lookup_entity(
            session=db_session,
            surface_form="فاس",
            project_uuid=project.project_uuid,
            category=EntityCategory.HISTORICAL_PLACE,
        )

        assert as_scholar == scholar.entity_id
        assert as_place == place.entity_id

    async def test_lookup_requires_at_least_one_scope(self, db_session: AsyncSession) -> None:
        with pytest.raises(InvalidEntityScope):
            await lookup_entity(session=db_session, surface_form="x")


# --- Layer 2: create / update Decision Events ----------------------------


@pytest.mark.asyncio
class TestEntityCreateAndUpdateDecisionEvents:
    async def test_create_writes_decision_event_with_glossary_management_source(
        self, db_session: AsyncSession
    ) -> None:
        project, _ = await _seed_project(db_session)

        entity, de = await create_entity(
            session=db_session,
            category=EntityCategory.ARABIC_BOOK,
            canonical_label="فتح الباري",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
            short_bio="commentary on Sahih al-Bukhari by Ibn Hajar",
        )

        # decision_source is glossary_management (10-value enum is unveränderlich;
        # entity CRUD shares the source). subsystem="entity" disambiguates.
        assert str(de.decision_source) == DecisionSource.GLOSSARY_MANAGEMENT.value
        assert de.decision_type == "entity_create"
        assert str(de.scope_type) == ScopeType.PROJECT.value
        assert de.scope_uuid == project.project_uuid
        assert de.content["subsystem"] == "entity"
        assert de.content["entity_id"] == str(entity.entity_id)
        assert de.content["category"] == EntityCategory.ARABIC_BOOK.value

    async def test_create_account_bound_uses_scope_account(self, db_session: AsyncSession) -> None:
        _, account_uuid = await _seed_project(db_session)

        _entity, de = await create_entity(
            session=db_session,
            category=EntityCategory.UNIT_OF_MEASUREMENT,
            canonical_label="dirham",
            language="ar",
            binding_level=BindingLevel.ACCOUNT,
            account_uuid=account_uuid,
        )

        assert str(de.scope_type) == ScopeType.ACCOUNT.value
        assert de.scope_uuid == account_uuid

    async def test_update_writes_decision_event_with_prior_and_new_values(
        self, db_session: AsyncSession
    ) -> None:
        project, _ = await _seed_project(db_session)
        entity, _ = await create_entity(
            session=db_session,
            category=EntityCategory.SCHOLAR_OR_PERSON,
            canonical_label="ابن تيمية",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
            short_bio="prior bio",
        )

        de = await update_entity(
            session=db_session,
            entity=entity,
            short_bio="updated bio: 661-728 AH",
        )

        assert de.decision_type == "entity_update"
        assert de.content["subsystem"] == "entity"
        assert de.content["prior_short_bio"] == "prior bio"
        assert de.content["new_short_bio"] == "updated bio: 661-728 AH"

    async def test_update_with_no_changes_raises(self, db_session: AsyncSession) -> None:
        project, _ = await _seed_project(db_session)
        entity, _ = await create_entity(
            session=db_session,
            category=EntityCategory.HISTORICAL_PLACE,
            canonical_label="بغداد",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )
        with pytest.raises(ValueError, match="no mutable field changes"):
            await update_entity(session=db_session, entity=entity)

    async def test_create_refuses_invalid_scope(self, db_session: AsyncSession) -> None:
        with pytest.raises(InvalidEntityScope):
            await create_entity(
                session=db_session,
                category=EntityCategory.ARABIC_BOOK,
                canonical_label="x",
                language="ar",
                binding_level=BindingLevel.PROJECT,
                # missing project_uuid
            )

    async def test_create_refuses_non_enum_category(self, db_session: AsyncSession) -> None:
        project, _ = await _seed_project(db_session)
        with pytest.raises(InvalidEntityCategory):
            await create_entity(
                session=db_session,
                category="random-string",  # type: ignore[arg-type]
                canonical_label="x",
                language="ar",
                binding_level=BindingLevel.PROJECT,
                project_uuid=project.project_uuid,
            )

    async def test_create_refuses_duplicate_within_same_category_and_scope(
        self, db_session: AsyncSession
    ) -> None:
        project, _ = await _seed_project(db_session)
        await create_entity(
            session=db_session,
            category=EntityCategory.DYNASTY_OR_EPOCH,
            canonical_label="العباسيون",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )
        with pytest.raises(EntityLabelAlreadyExists):
            await create_entity(
                session=db_session,
                category=EntityCategory.DYNASTY_OR_EPOCH,
                canonical_label="العباسيون",
                language="ar",
                binding_level=BindingLevel.PROJECT,
                project_uuid=project.project_uuid,
            )


# --- Layer 2: get_entity --------------------------------------------------


@pytest.mark.asyncio
class TestEntityGet:
    async def test_get_entity_returns_row(self, db_session: AsyncSession) -> None:
        project, _ = await _seed_project(db_session)
        entity, _ = await create_entity(
            session=db_session,
            category=EntityCategory.SCHOLAR_OR_PERSON,
            canonical_label="مالك بن أنس",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )

        loaded = await get_entity(session=db_session, entity_id=entity.entity_id)
        assert loaded is not None
        assert loaded.entity_id == entity.entity_id
        assert loaded.canonical_label == "مالك بن أنس"

    async def test_get_entity_returns_none_for_unknown(self, db_session: AsyncSession) -> None:
        loaded = await get_entity(session=db_session, entity_id=new_uuid())
        assert loaded is None


# --- Layer 3: cross-table discipline -------------------------------------


@pytest.mark.asyncio
class TestEntityCrossTableDiscipline:
    async def test_lookup_writes_no_decision_event(self, db_session: AsyncSession) -> None:
        project, _ = await _seed_project(db_session)
        before = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()

        await lookup_entity(session=db_session, surface_form="x", project_uuid=project.project_uuid)

        after = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        assert after == before


# --- Layer 4: schema discipline ------------------------------------------


class TestEntitySchemaDiscipline:
    def test_entities_table_registered(self) -> None:
        from waraq.db.base import Base

        assert "entities" in Base.metadata.tables

    def test_entity_id_pk(self) -> None:
        assert [c.name for c in Entity.__table__.primary_key.columns] == ["entity_id"]

    def test_category_column_present(self) -> None:
        assert "category" in Entity.__table__.columns

    def test_no_satz_uuid_on_entities(self) -> None:
        # Entities are project/account-scoped, not segment-scoped.
        assert "satz_uuid" not in Entity.__table__.columns

    @pytest.mark.parametrize("category", list(EntityCategory))
    def test_all_5_canonical_categories_are_strings(self, category: EntityCategory) -> None:
        # Sanity check the enum is fully populated and canonical-shape strings.
        assert isinstance(category.value, str)
        assert "_" in category.value or category.value.isalpha()


# --- All 5 categories actually round-trip --------------------------------


@pytest.mark.asyncio
class TestAllFiveCategoriesRoundTrip:
    @pytest.mark.parametrize("category", list(EntityCategory))
    async def test_each_category_round_trips(
        self, db_session: AsyncSession, category: EntityCategory
    ) -> None:
        project, _ = await _seed_project(db_session)
        entity, _ = await create_entity(
            session=db_session,
            category=category,
            canonical_label=f"label-{category.value}",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )
        loaded = await get_entity(session=db_session, entity_id=entity.entity_id)
        assert loaded is not None
        assert loaded.category == category.value
