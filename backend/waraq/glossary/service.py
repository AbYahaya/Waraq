"""T-5.2.1 — GLOSSARY service.

Per Sprint 1 §2:

- `lookup(surface_form, scope)` returns either a `concept_id` or the
  explicit sentinel `NO_ENTRY`. **Never null. Never silent.** Callers can't
  conflate "no entry" with "lookup failure" — a hit returns a UUID; a miss
  returns the named sentinel.
- `get_entry(concept_id)` returns the full Concept ORM row.
- `create_entry()` and `update_entry()` write Decision Events with
  `decision_source=glossary_management`. The `scope_type` is derived from
  the Concept's `binding_level`: `project` → `ScopeType.PROJECT`,
  `account` → `ScopeType.ACCOUNT`.
- `lookup()` is the **sole entrypoint** for surface-form-to-concept
  resolution. No code path may bypass it via direct SELECT against the
  concepts table; downstream services must import `lookup`.
- Glossary entries are never auto-created from external sources, OCR runs,
  or AI suggestions. The service exposes no `bulk_create_from_*`,
  `seed_from_corpus`, or `auto_*` entrypoint.

Application of a glossary entry against a locked Segment routes through
T-5.1.2 conflict detection (Sprint 1's other half). That's not in this
module — this module just persists the entry. The application layer lives
in T-7.2.1 (Sprint 2/3) and is responsible for calling `detect_conflict`
before applying.
"""

from __future__ import annotations

import uuid as _uuid
from enum import StrEnum
from typing import Any, Final, final

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.decisions import create_decision_event
from waraq.glossary.exceptions import InvalidBindingScope, SurfaceFormAlreadyExists
from waraq.identity.service import new_uuid
from waraq.schemas import Concept, DecisionEvent
from waraq.schemas.enums import DecisionSource, ScopeType


class BindingLevel(StrEnum):
    """Per CLAUDE.md §2.4 — verbatim canonical column value set."""

    PROJECT = "project"
    ACCOUNT = "account"


@final
class NoEntrySentinel:
    """The explicit "no entry" return value for `lookup`.

    Per Sprint 1 §2 / R-S1-08: a glossary miss must return a named sentinel,
    never null. The sentinel's `__bool__` is False so common idioms like
    `if (result := await lookup(...)):` keep working, but identity checks
    (`result is NO_ENTRY`) remain the discipline-bearing form.
    """

    _instance: NoEntrySentinel | None = None

    def __new__(cls) -> NoEntrySentinel:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "NO_ENTRY"

    def __bool__(self) -> bool:
        return False


NO_ENTRY: Final[NoEntrySentinel] = NoEntrySentinel()
LookupResult = _uuid.UUID | NoEntrySentinel


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
            raise InvalidBindingScope(
                "binding_level='project' requires project_uuid set and account_uuid unset"
            )
    else:
        if account_uuid is None or project_uuid is not None:
            raise InvalidBindingScope(
                "binding_level='account' requires account_uuid set and project_uuid unset"
            )


def _normalize_surface_form(surface_form: str) -> str:
    """Case-fold + strip whitespace. Glossary lookup is case-insensitive
    matching against the canonical_label."""
    return surface_form.strip().casefold()


# --- public API -----------------------------------------------------------


async def lookup(
    *,
    session: AsyncSession,
    surface_form: str,
    project_uuid: _uuid.UUID | None = None,
    account_uuid: _uuid.UUID | None = None,
) -> LookupResult:
    """Resolve a surface form to a `concept_id` within the given scope.

    At least one of `project_uuid` / `account_uuid` must be supplied. When
    both are given, the search prefers project-bound entries (a project
    glossary can override the account-wide one) and falls back to account-
    bound matches.

    Args:
        session: Active async session.
        surface_form: The text to look up. Case-insensitively compared with
            `Concept.canonical_label` after whitespace strip + casefold.
        project_uuid: Restrict project-bound search to this project.
        account_uuid: Restrict account-bound search to this account.

    Returns:
        The matching `concept_id` UUID, or `NO_ENTRY` if no active Concept
        matches in the given scope.
    """
    if project_uuid is None and account_uuid is None:
        raise InvalidBindingScope("lookup requires at least one of project_uuid or account_uuid")

    needle = _normalize_surface_form(surface_form)

    # Build the scope filter: project-bound OR account-bound (when given).
    scope_filters = []
    if project_uuid is not None:
        scope_filters.append(
            and_(
                Concept.binding_level == BindingLevel.PROJECT.value,
                Concept.project_uuid == project_uuid,
            )
        )
    if account_uuid is not None:
        scope_filters.append(
            and_(
                Concept.binding_level == BindingLevel.ACCOUNT.value,
                Concept.account_uuid == account_uuid,
            )
        )

    stmt = select(Concept).where(Concept.active.is_(True)).where(or_(*scope_filters))
    result = await session.execute(stmt)
    rows = list(result.scalars())

    # Project-scope wins when both are present (project overrides account).
    project_hit = next(
        (
            r
            for r in rows
            if r.binding_level == BindingLevel.PROJECT.value
            and _normalize_surface_form(r.canonical_label) == needle
        ),
        None,
    )
    if project_hit is not None:
        return project_hit.concept_id

    account_hit = next(
        (
            r
            for r in rows
            if r.binding_level == BindingLevel.ACCOUNT.value
            and _normalize_surface_form(r.canonical_label) == needle
        ),
        None,
    )
    if account_hit is not None:
        return account_hit.concept_id

    return NO_ENTRY


async def get_entry(
    *,
    session: AsyncSession,
    concept_id: _uuid.UUID,
) -> Concept | None:
    """Return the full Concept row, or None when not present."""
    result = await session.execute(select(Concept).where(Concept.concept_id == concept_id))
    row: Concept | None = result.scalar_one_or_none()
    return row


async def create_entry(
    *,
    session: AsyncSession,
    canonical_label: str,
    language: str,
    binding_level: BindingLevel,
    project_uuid: _uuid.UUID | None = None,
    account_uuid: _uuid.UUID | None = None,
    gloss: str | None = None,
    actor_uuid: _uuid.UUID | None = None,
) -> tuple[Concept, DecisionEvent]:
    """Create a new glossary entry. Writes a Decision Event scoped to the
    binding-level scope.

    Per Sprint 1 §2: glossary entries are **never** auto-created from
    external sources. This service has no `bulk_create_from_*` surface;
    every Concept lands here via this single entrypoint with a Decision
    Event attached, so `glossary_management` events on `decision_events`
    are an exhaustive audit of glossary growth.

    Args:
        session: Active async session.
        canonical_label: The surface form / canonical label.
        language: ISO language tag for canonical_label.
        binding_level: PROJECT or ACCOUNT.
        project_uuid: Required when binding_level=PROJECT.
        account_uuid: Required when binding_level=ACCOUNT.
        gloss: Optional human-readable gloss.
        actor_uuid: Account that created the entry (Decision Event actor).

    Returns:
        `(Concept, DecisionEvent)` pair, both already flushed.
    """
    _validate_scope(
        binding_level=binding_level,
        project_uuid=project_uuid,
        account_uuid=account_uuid,
    )

    # Per-scope uniqueness check: refuse duplicate (surface_form, scope).
    needle = _normalize_surface_form(canonical_label)
    existing = await session.execute(
        select(Concept).where(
            Concept.binding_level == binding_level.value,
            Concept.project_uuid == project_uuid,
            Concept.account_uuid == account_uuid,
            Concept.active.is_(True),
        )
    )
    for row in existing.scalars():
        if _normalize_surface_form(row.canonical_label) == needle:
            raise SurfaceFormAlreadyExists(
                f"surface_form={canonical_label!r} already has an active Concept "
                f"in this scope (concept_id={row.concept_id})"
            )

    concept = Concept(
        concept_id=new_uuid(),
        canonical_label=canonical_label,
        language=language,
        gloss=gloss,
        binding_level=binding_level.value,
        project_uuid=project_uuid,
        account_uuid=account_uuid,
    )
    session.add(concept)
    await session.flush()

    scope_type = _scope_type_for_binding(binding_level)
    scope_uuid = project_uuid if binding_level == BindingLevel.PROJECT else account_uuid
    assert scope_uuid is not None  # _validate_scope guarantees this

    de = await create_decision_event(
        session=session,
        scope_type=scope_type,
        scope_uuid=scope_uuid,
        decision_type="glossary_create",
        decision_source=DecisionSource.GLOSSARY_MANAGEMENT,
        actor_uuid=actor_uuid,
        content={
            "concept_id": str(concept.concept_id),
            "canonical_label": canonical_label,
            "language": language,
            "binding_level": binding_level.value,
        },
    )

    return concept, de


async def update_entry(
    *,
    session: AsyncSession,
    concept: Concept,
    canonical_label: str | None = None,
    gloss: str | None = None,
    actor_uuid: _uuid.UUID | None = None,
    extra_content: dict[str, Any] | None = None,
) -> DecisionEvent:
    """Update a glossary entry's mutable fields. Writes a Decision Event
    scoped to the entry's binding-level scope.

    Identity (concept_id, binding_level, scope) is immutable per H-5 — only
    `canonical_label` and `gloss` can change. To re-bind to a different
    scope, inactivate the old entry and `create_entry` a new one.
    """
    if canonical_label is None and gloss is None:
        raise ValueError(
            "update_entry called with no mutable field changes; "
            "no-op updates would pollute the Decision-Event audit trail"
        )

    binding_level = BindingLevel(concept.binding_level)
    scope_type = _scope_type_for_binding(binding_level)
    scope_uuid = (
        concept.project_uuid if binding_level == BindingLevel.PROJECT else concept.account_uuid
    )
    assert scope_uuid is not None  # CHECK constraint guarantees this

    prior_label = concept.canonical_label
    prior_gloss = concept.gloss

    if canonical_label is not None:
        concept.canonical_label = canonical_label
    if gloss is not None:
        concept.gloss = gloss
    await session.flush()

    content: dict[str, Any] = {
        "concept_id": str(concept.concept_id),
        "binding_level": binding_level.value,
        "prior_canonical_label": prior_label,
        "prior_gloss": prior_gloss,
        "new_canonical_label": concept.canonical_label,
        "new_gloss": concept.gloss,
    }
    if extra_content:
        content.update(extra_content)

    de = await create_decision_event(
        session=session,
        scope_type=scope_type,
        scope_uuid=scope_uuid,
        decision_type="glossary_update",
        decision_source=DecisionSource.GLOSSARY_MANAGEMENT,
        actor_uuid=actor_uuid,
        content=content,
    )
    return de
