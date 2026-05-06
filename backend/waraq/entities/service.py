"""§4.19 — Reference / Entity service.

Per Dokument 1 §4.19: 5-value canonical category taxonomy. Schema shape is
not canonized — only the categories are. This service ships the CRUD +
lookup framework that K-03 (Sprint 4 / T-8.2.1) consumes for entity-
consistency checking.

Decision-source convention: entity CRUD writes Decision Events with
`decision_source=glossary_management`. The 10-value `decision_source` enum
is unveränderlich (Dokument 1 §4.10 / CLAUDE.md §5.9) and there is no
`entity_management` slot. Glossary management is the closest semantic fit —
both are "user maintains a controlled vocabulary of named things". The DE
content carries `subsystem: "entity"` so audit-readers can disambiguate
glossary CRUD from entity CRUD downstream.

`lookup_entity` is the canonical surface-form-to-entity_id resolver and
follows the same NEVER-NULL discipline as `glossary.lookup`: returns the
entity_id UUID on hit, the `NO_ENTITY` singleton sentinel on miss.
"""

from __future__ import annotations

import uuid as _uuid
from enum import StrEnum
from typing import Any, Final, final

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.decisions import create_decision_event
from waraq.entities.exceptions import (
    EntityLabelAlreadyExists,
    InvalidEntityCategory,
    InvalidEntityScope,
)
from waraq.glossary.service import BindingLevel
from waraq.identity.service import new_uuid
from waraq.schemas import DecisionEvent, Entity
from waraq.schemas.enums import DecisionSource, ScopeType


class EntityCategory(StrEnum):
    """Per Dokument 1 §4.19 — 5 canonical categories."""

    SCHOLAR_OR_PERSON = "scholar_or_person"
    HISTORICAL_PLACE = "historical_place"
    UNIT_OF_MEASUREMENT = "unit_of_measurement"
    ARABIC_BOOK = "arabic_book"
    DYNASTY_OR_EPOCH = "dynasty_or_epoch"


@final
class EntityNotFoundSentinel:
    """Explicit "no entity" return value for `lookup_entity`. Same singleton
    pattern as `glossary.NO_ENTRY`."""

    _instance: EntityNotFoundSentinel | None = None

    def __new__(cls) -> EntityNotFoundSentinel:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "NO_ENTITY"

    def __bool__(self) -> bool:
        return False


NO_ENTITY: Final[EntityNotFoundSentinel] = EntityNotFoundSentinel()
LookupEntityResult = _uuid.UUID | EntityNotFoundSentinel


# --- internal helpers -----------------------------------------------------


def _scope_type_for_binding(binding: BindingLevel) -> ScopeType:
    return ScopeType.PROJECT if binding == BindingLevel.PROJECT else ScopeType.ACCOUNT


def _validate_scope(
    *,
    binding_level: BindingLevel,
    project_uuid: _uuid.UUID | None,
    account_uuid: _uuid.UUID | None,
) -> None:
    if binding_level == BindingLevel.PROJECT:
        if project_uuid is None or account_uuid is not None:
            raise InvalidEntityScope(
                "binding_level='project' requires project_uuid set and account_uuid unset"
            )
    else:
        if account_uuid is None or project_uuid is not None:
            raise InvalidEntityScope(
                "binding_level='account' requires account_uuid set and project_uuid unset"
            )


def _normalize_label(label: str) -> str:
    return label.strip().casefold()


# --- public API -----------------------------------------------------------


async def lookup_entity(
    *,
    session: AsyncSession,
    surface_form: str,
    project_uuid: _uuid.UUID | None = None,
    account_uuid: _uuid.UUID | None = None,
    category: EntityCategory | None = None,
) -> LookupEntityResult:
    """Resolve a surface form to an `entity_id` within the given scope.

    Same project-shadows-account cascade as `glossary.lookup`. Optional
    `category` narrows the search to a single taxonomy slot.
    """
    if project_uuid is None and account_uuid is None:
        raise InvalidEntityScope(
            "lookup_entity requires at least one of project_uuid or account_uuid"
        )

    needle = _normalize_label(surface_form)

    scope_filters = []
    if project_uuid is not None:
        scope_filters.append(
            and_(
                Entity.binding_level == BindingLevel.PROJECT.value,
                Entity.project_uuid == project_uuid,
            )
        )
    if account_uuid is not None:
        scope_filters.append(
            and_(
                Entity.binding_level == BindingLevel.ACCOUNT.value,
                Entity.account_uuid == account_uuid,
            )
        )

    stmt = select(Entity).where(Entity.active.is_(True)).where(or_(*scope_filters))
    if category is not None:
        stmt = stmt.where(Entity.category == category.value)
    rows = list((await session.execute(stmt)).scalars())

    project_hit = next(
        (
            r
            for r in rows
            if r.binding_level == BindingLevel.PROJECT.value
            and _normalize_label(r.canonical_label) == needle
        ),
        None,
    )
    if project_hit is not None:
        return project_hit.entity_id

    account_hit = next(
        (
            r
            for r in rows
            if r.binding_level == BindingLevel.ACCOUNT.value
            and _normalize_label(r.canonical_label) == needle
        ),
        None,
    )
    if account_hit is not None:
        return account_hit.entity_id

    return NO_ENTITY


async def get_entity(
    *,
    session: AsyncSession,
    entity_id: _uuid.UUID,
) -> Entity | None:
    result = await session.execute(select(Entity).where(Entity.entity_id == entity_id))
    row: Entity | None = result.scalar_one_or_none()
    return row


async def create_entity(
    *,
    session: AsyncSession,
    category: EntityCategory,
    canonical_label: str,
    language: str,
    binding_level: BindingLevel,
    project_uuid: _uuid.UUID | None = None,
    account_uuid: _uuid.UUID | None = None,
    short_bio: str | None = None,
    metadata_json: dict[str, Any] | None = None,
    source_refs: list[dict[str, Any]] | None = None,
    actor_uuid: _uuid.UUID | None = None,
) -> tuple[Entity, DecisionEvent]:
    """Create a new entity. Writes a Decision Event scoped to the binding-
    level scope.

    Per Sprint 1 §2 lineage: just like glossary, entities are **never**
    auto-created from external sources — every entity lands here with a
    Decision Event for the audit trail. No `bulk_create_*` /
    `seed_from_corpus` / `auto_*` surface.
    """
    if not isinstance(category, EntityCategory):
        raise InvalidEntityCategory(
            f"category must be an EntityCategory; got {type(category).__name__}"
        )

    _validate_scope(
        binding_level=binding_level,
        project_uuid=project_uuid,
        account_uuid=account_uuid,
    )

    # Per-(category, scope) uniqueness check.
    needle = _normalize_label(canonical_label)
    existing = await session.execute(
        select(Entity).where(
            Entity.category == category.value,
            Entity.binding_level == binding_level.value,
            Entity.project_uuid == project_uuid,
            Entity.account_uuid == account_uuid,
            Entity.active.is_(True),
        )
    )
    for row in existing.scalars():
        if _normalize_label(row.canonical_label) == needle:
            raise EntityLabelAlreadyExists(
                f"entity with category={category.value} and label={canonical_label!r} "
                f"already exists in this scope (entity_id={row.entity_id})"
            )

    entity = Entity(
        entity_id=new_uuid(),
        category=category.value,
        canonical_label=canonical_label,
        language=language,
        short_bio=short_bio,
        metadata_json=metadata_json if metadata_json is not None else {},
        source_refs=source_refs if source_refs is not None else [],
        binding_level=binding_level.value,
        project_uuid=project_uuid,
        account_uuid=account_uuid,
    )
    session.add(entity)
    await session.flush()

    scope_type = _scope_type_for_binding(binding_level)
    scope_uuid = project_uuid if binding_level == BindingLevel.PROJECT else account_uuid
    assert scope_uuid is not None

    de = await create_decision_event(
        session=session,
        scope_type=scope_type,
        scope_uuid=scope_uuid,
        decision_type="entity_create",
        decision_source=DecisionSource.GLOSSARY_MANAGEMENT,
        actor_uuid=actor_uuid,
        content={
            "subsystem": "entity",
            "entity_id": str(entity.entity_id),
            "category": category.value,
            "canonical_label": canonical_label,
            "language": language,
            "binding_level": binding_level.value,
        },
    )

    return entity, de


async def update_entity(
    *,
    session: AsyncSession,
    entity: Entity,
    canonical_label: str | None = None,
    short_bio: str | None = None,
    metadata_json: dict[str, Any] | None = None,
    source_refs: list[dict[str, Any]] | None = None,
    actor_uuid: _uuid.UUID | None = None,
    extra_content: dict[str, Any] | None = None,
) -> DecisionEvent:
    """Update mutable fields on an entity. Identity (entity_id, category,
    binding_level, scope) is immutable per H-5; to re-bind, inactivate the
    old entity and create a new one."""
    if all(v is None for v in (canonical_label, short_bio, metadata_json, source_refs)):
        raise ValueError(
            "update_entity called with no mutable field changes; "
            "no-op updates would pollute the Decision-Event audit trail"
        )

    binding_level = BindingLevel(entity.binding_level)
    scope_type = _scope_type_for_binding(binding_level)
    scope_uuid = (
        entity.project_uuid if binding_level == BindingLevel.PROJECT else entity.account_uuid
    )
    assert scope_uuid is not None

    prior_label = entity.canonical_label
    prior_bio = entity.short_bio

    if canonical_label is not None:
        entity.canonical_label = canonical_label
    if short_bio is not None:
        entity.short_bio = short_bio
    if metadata_json is not None:
        entity.metadata_json = metadata_json
    if source_refs is not None:
        entity.source_refs = source_refs
    await session.flush()

    content: dict[str, Any] = {
        "subsystem": "entity",
        "entity_id": str(entity.entity_id),
        "category": entity.category,
        "binding_level": binding_level.value,
        "prior_canonical_label": prior_label,
        "prior_short_bio": prior_bio,
        "new_canonical_label": entity.canonical_label,
        "new_short_bio": entity.short_bio,
    }
    if extra_content:
        content.update(extra_content)

    de = await create_decision_event(
        session=session,
        scope_type=scope_type,
        scope_uuid=scope_uuid,
        decision_type="entity_update",
        decision_source=DecisionSource.GLOSSARY_MANAGEMENT,
        actor_uuid=actor_uuid,
        content=content,
    )
    return de
