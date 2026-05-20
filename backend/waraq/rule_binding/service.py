"""T-7.2.1 — RULE_BINDING service.

Per Sprint 2 §2: every Segment translation pass invokes the GLOSSARY
service (`lookup`, `get_entry`) to resolve terminology. The bindings are
recorded as RULE_BINDING-POs via PROVENANCE-Kern. When a glossary entry
would apply to a locked Segment, the conflict_instance pathway from
T-5.1.2 is invoked instead — translation never silently overwrites a
locked Segment (DBB §B Abkürzung 6).

Surface-form matching: this v1.0 implementation does substring matching
(case-insensitive) of `Concept.canonical_label` against
`Segment.text_content`. The Sprint 2 §B "Calibration values" line covers
this — match precision is configurable / refinable, not pre-set.

`lookup` discipline (R-S2-08, RULE-BINDING-Lookup-Sole-Entrypoint-Test):
this module imports only the public glossary entrypoints (`lookup`,
`get_entry`, `BindingLevel`). It does NOT touch the `Concept` ORM class
directly — surface-form-to-concept resolution flows exclusively through
`waraq.glossary.lookup` so the `NO_ENTRY` sentinel discipline is upheld.

Two integration paths with the translation pipeline:

1. **Locked-segment hook** — `make_locked_segment_glossary_conflict_hook`
   builds a hook for T-7.1.1's `on_locked_segment_skip`. Each glossary
   match against a locked Segment writes a `conflict_instance` row via
   `detect_conflict` (T-5.1.2).

2. **Unlocked-segment hook** — `make_translation_with_rule_binding_hook`
   wraps T-7.1.2's persistence hook and additionally writes a
   RULE_BINDING-PO per glossary match. When the Segment was previously
   resolved as `lokale_ausnahme` for the same concept_id, the PO carries
   `ausnahme_flag=True` plus the original resolution's
   `decision_event_uuid`.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.conflicts import (
    ConflictType,
    ResolutionType,
    RuleSource,
    detect_conflict,
)
from waraq.glossary import get_entry, lookup
from waraq.glossary.service import NoEntrySentinel
from waraq.provenance import create_po
from waraq.schemas import ConflictInstance, ProvenanceObject, Segment
from waraq.schemas.enums import POType, ScopeType
from waraq.text_state import resolve_segment_source_text
from waraq.translation.persistence import make_translation_persistence_hook
from waraq.translation.service import (
    LockedSegmentSkipHook,
    SegmentTranslatedHook,
    TranslationContext,
)


@dataclass(frozen=True, kw_only=True, slots=True)
class GlossaryMatch:
    """A surface-form match found in a Segment's text. The
    `concept_id` was resolved via `glossary.lookup` (the canonical
    entrypoint)."""

    surface_form: str
    concept_id: _uuid.UUID


@dataclass(frozen=True, kw_only=True, slots=True)
class RuleBindingApplied:
    """RULE_BINDING-PO write for an unlocked Segment."""

    surface_form: str
    concept_id: _uuid.UUID
    po_uuid: _uuid.UUID
    ausnahme_flag: bool
    decision_event_uuid: _uuid.UUID | None


@dataclass(frozen=True, kw_only=True, slots=True)
class RuleBindingConflict:
    """conflict_instance row created for a glossary match against a locked
    Segment."""

    surface_form: str
    concept_id: _uuid.UUID
    conflict_uuid: _uuid.UUID


@dataclass(frozen=True, kw_only=True, slots=True)
class RuleBindingResult:
    applied: list[RuleBindingApplied]
    conflicts: list[RuleBindingConflict]


# --- surface-form match (lookup-only) ---------------------------------


async def find_glossary_matches_in_segment(
    *,
    session: AsyncSession,
    segment: Segment,
    project_uuid: _uuid.UUID,
    account_uuid: _uuid.UUID | None = None,
    candidate_surface_forms: Iterable[str] | None = None,
) -> list[GlossaryMatch]:
    """Identify glossary surface forms present in `segment.text_content`.

    By default, callers must supply `candidate_surface_forms` — the list
    of surface strings to test for presence in the segment text. The
    canonical reason for that requirement is the lookup-discipline rule:
    we never SELECT the concepts table directly to enumerate labels.
    Instead, callers (the translation pipeline) provide the candidate
    set from their own context, and this function only calls
    `glossary.lookup` to resolve each candidate to a `concept_id`.

    Returns one `GlossaryMatch` per surface form that (a) appears in the
    segment text (case-insensitive substring) AND (b) resolves via
    `lookup` to a non-`NO_ENTRY` concept_id.
    """
    if candidate_surface_forms is None:
        return []

    haystack = (await resolve_segment_source_text(session=session, segment=segment)).casefold()
    matches: list[GlossaryMatch] = []
    seen: set[_uuid.UUID] = set()
    for surface in candidate_surface_forms:
        needle = surface.strip().casefold()
        if not needle or needle not in haystack:
            continue
        result = await lookup(
            session=session,
            surface_form=surface,
            project_uuid=project_uuid,
            account_uuid=account_uuid,
        )
        if isinstance(result, NoEntrySentinel):
            continue
        if result in seen:
            continue
        seen.add(result)
        matches.append(GlossaryMatch(surface_form=surface, concept_id=result))
    return matches


# --- ausnahme tracking ----------------------------------------------


async def _find_lokale_ausnahme_de_uuid(
    *,
    session: AsyncSession,
    satz_uuid: _uuid.UUID,
    concept_id: _uuid.UUID,
) -> _uuid.UUID | None:
    """Return the decision_event_uuid of an aufgeloest conflict_instance
    for this (segment, concept_id) pair with resolution_type=lokale_ausnahme,
    if any. Used to set `ausnahme_flag` on the RULE_BINDING-PO and to
    reference the original user resolution event."""
    result = await session.execute(
        select(ConflictInstance)
        .where(ConflictInstance.satz_uuid == satz_uuid)
        .where(ConflictInstance.resolution_type == ResolutionType.LOKALE_AUSNAHME.value)
        .where(ConflictInstance.state == "aufgeloest")
        .order_by(ConflictInstance.resolved_at.desc())
    )
    for row in result.scalars():
        ctx = row.context or {}
        if ctx.get("concept_id") == str(concept_id):
            return row.decision_event_uuid
    return None


# --- bind / write paths --------------------------------------------


async def bind_glossary_to_segment(
    *,
    session: AsyncSession,
    segment: Segment,
    project_uuid: _uuid.UUID,
    account_uuid: _uuid.UUID | None = None,
    candidate_surface_forms: Iterable[str],
    application_context: dict[str, Any] | None = None,
) -> RuleBindingResult:
    """Run the full glossary-bind step for one Segment.

    For each surface-form match:
    - If `segment.lock_flag != NONE` → `detect_conflict` (T-5.1.2). The
      conflict_instance row carries the concept_id in its `context` JSONB.
    - Else → `create_po` (T-1.6.1) with `po_type=RULE_BINDING`, payload
      including the surface form, concept_id, application context, and
      (when applicable) `ausnahme_flag` + the resolution
      `decision_event_uuid`.

    Returns a `RuleBindingResult` enumerating applied bindings and any
    conflicts that were created.
    """
    from waraq.invariant.enums import LockFlag

    matches = await find_glossary_matches_in_segment(
        session=session,
        segment=segment,
        project_uuid=project_uuid,
        account_uuid=account_uuid,
        candidate_surface_forms=candidate_surface_forms,
    )

    applied: list[RuleBindingApplied] = []
    conflicts: list[RuleBindingConflict] = []

    is_locked = segment.lock_flag != LockFlag.NONE

    for match in matches:
        if is_locked:
            conflict = await detect_conflict(
                session=session,
                segment=segment,
                rule_source=RuleSource.GLOSSARY,
                conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
                context={
                    "concept_id": str(match.concept_id),
                    "surface_form": match.surface_form,
                    **(application_context or {}),
                },
            )
            conflicts.append(
                RuleBindingConflict(
                    surface_form=match.surface_form,
                    concept_id=match.concept_id,
                    conflict_uuid=conflict.conflict_uuid,
                )
            )
            continue

        # Unlocked segment — write RULE_BINDING-PO.
        ausnahme_de_uuid = await _find_lokale_ausnahme_de_uuid(
            session=session,
            satz_uuid=segment.satz_uuid,
            concept_id=match.concept_id,
        )
        ausnahme_flag = ausnahme_de_uuid is not None

        # Confirm the concept still exists / is active. We use the public
        # get_entry, never a direct ORM query.
        concept = await get_entry(session=session, concept_id=match.concept_id)
        if concept is None:
            # Glossary entry vanished between lookup and get_entry — skip.
            continue

        po_payload: dict[str, Any] = {
            "concept_id": str(match.concept_id),
            "surface_form": match.surface_form,
            "binding_level": concept.binding_level,
            "ausnahme_flag": ausnahme_flag,
            "decision_event_uuid": str(ausnahme_de_uuid) if ausnahme_de_uuid else None,
        }
        if application_context:
            po_payload["application_context"] = dict(application_context)

        po = await create_po(
            session=session,
            po_type=POType.RULE_BINDING,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=segment.satz_uuid,
            payload=po_payload,
        )
        applied.append(
            RuleBindingApplied(
                surface_form=match.surface_form,
                concept_id=match.concept_id,
                po_uuid=po.po_uuid,
                ausnahme_flag=ausnahme_flag,
                decision_event_uuid=ausnahme_de_uuid,
            )
        )

    return RuleBindingResult(applied=applied, conflicts=conflicts)


# --- translation-pipeline integration hooks --------------------------


def make_locked_segment_glossary_conflict_hook(
    *,
    project_uuid: _uuid.UUID,
    candidate_surface_forms: Iterable[str],
    account_uuid: _uuid.UUID | None = None,
    application_context: dict[str, Any] | None = None,
) -> LockedSegmentSkipHook:
    """Build a `LockedSegmentSkipHook` for T-7.1.1.

    For each glossary surface form that matches the locked Segment's
    text, the hook invokes `detect_conflict` (T-5.1.2). No translation
    happens (T-7.1.1 already skips locked segments) but the conflict
    pathway is canonical.
    """
    surface_forms = list(candidate_surface_forms)

    async def _hook(
        session: AsyncSession,
        segment: Segment,
        context: TranslationContext,
    ) -> None:
        await bind_glossary_to_segment(
            session=session,
            segment=segment,
            project_uuid=project_uuid,
            account_uuid=account_uuid,
            candidate_surface_forms=surface_forms,
            application_context=application_context,
        )

    return _hook


def make_translation_with_rule_binding_hook(
    *,
    engine_identifier: str,
    project_uuid: _uuid.UUID,
    candidate_surface_forms: Iterable[str],
    account_uuid: _uuid.UUID | None = None,
    application_context: dict[str, Any] | None = None,
) -> SegmentTranslatedHook:
    """Composite hook = T-7.1.2 persistence (Revision + TRANSLATION-PO) +
    T-7.2.1 RULE_BINDING-PO writes for any glossary matches.

    Per Sprint 2 §2: "Resolved entries are applied to the Segment output
    before TRANSLATION-PO is written." Order in this hook:

    1. Run the persistence hook (writes Revision-on-change +
       TRANSLATION-PO).
    2. Run `bind_glossary_to_segment` for unlocked-segment matches —
       writes RULE_BINDING-POs.

    Note on ordering: the spec phrasing "applied to the Segment output
    before TRANSLATION-PO" suggests the binding application would
    influence the OUTPUT TEXT itself. In v1.0 the LLM-side translator
    consumes terminology bindings via `TranslationContext.terminology_bindings`
    BEFORE producing output, so the OUTPUT already reflects the
    binding. This hook records the binding fact in provenance — the
    rendering is already done.
    """
    persistence_hook = make_translation_persistence_hook(engine_identifier=engine_identifier)
    surface_forms = list(candidate_surface_forms)

    async def _hook(
        session: AsyncSession,
        segment: Segment,
        output_text: str,
        context: TranslationContext,
    ) -> None:
        # T-7.1.2 first.
        await persistence_hook(session, segment, output_text, context)
        # Then T-7.2.1 binding writes.
        await bind_glossary_to_segment(
            session=session,
            segment=segment,
            project_uuid=project_uuid,
            account_uuid=account_uuid,
            candidate_surface_forms=surface_forms,
            application_context=application_context,
        )

    return _hook


# silence unused-import warnings in __init__.py re-exports
_ = ProvenanceObject
