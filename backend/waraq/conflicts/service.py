"""T-5.1.2 — CONFLICT-Erkennung service.

THE CRITICAL Sprint 1 piece. Per CLAUDE.md §5.6 / DBB Abkürzung 11: open
`conflict_instance` rows MUST survive process restarts. Every detection
writes the row to the database immediately; the service holds nothing in
memory.

Public surface (HG-S1: exactly three resolution paths, no fourth):

- `detect_conflict(...)` — writer. Persists `conflict_instance` with
  `state=offen`, `decision_event_uuid=NULL`. **No Decision Event is
  written at detection time** (Conflict-Instance-Kein-Decision-Event-Bei-
  Erkennung-Test).
- `resolve_with_local_exception(...)` — path 1: rule does not apply here.
- `resolve_with_glossary_change(...)` — path 2: glossary entry adjusted.
- `resolve_with_lock_release(...)` — path 3: lock released via T-5.1.1
  (subject to the editorial-confirmation rule there).

Each resolution path:
1. Performs path-specific side effects (e.g., release the lock for path 3).
2. Writes a Decision Event via T-1.4.2 with `scope_type=segment` and
   `decision_source=conflict_resolution`.
3. Atomically transitions the conflict row: `state=aufgeloest`,
   `resolution_type=...`, `decision_event_uuid=<DE.uuid>`,
   `resolved_at=now()`. The CHECK constraint
   `ck_conflict_resolution_consistency` makes a half-resolved row
   impossible at the DB level.

`conflict_instance` is **not** a PO. HG-S1-6: the service must never call
`create_po` with `po_type=...CONFLICT_INSTANCE`. The Decision Event is the
provenance anchor.

Atomicity: caller owns the transaction. The service flushes; commit /
rollback is the caller's responsibility. The restart-survival contract
requires the caller to commit promptly after detection.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.conflicts.enums import (
    ConflictState,
    ConflictType,
    ResolutionType,
    RuleSource,
)
from waraq.conflicts.exceptions import (
    ConflictAlreadyResolved,
    ConflictResolutionPathInvalid,
)
from waraq.decisions import create_decision_event
from waraq.identity.service import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.lock import ConfirmationContext, release_lock
from waraq.schemas import (
    Block,
    ConflictInstance,
    DecisionEvent,
    Page,
    Segment,
)
from waraq.schemas.enums import DecisionSource, ScopeType

# --- detection ------------------------------------------------------------


async def detect_conflict(
    *,
    session: AsyncSession,
    segment: Segment,
    rule_source: RuleSource,
    conflict_type: ConflictType,
    context: dict[str, Any] | None = None,
) -> ConflictInstance:
    """Persist a new `conflict_instance` row with `state=offen`.

    No Decision Event at this point — the canonical detection-vs-resolution
    distinction (Sprint 1 §2 / Conflict-Instance-Decision-Event-Bei-
    Aufloesung-Test) means decision_event_uuid stays NULL until a resolve_*
    call happens.

    Args:
        session: Active async session. Caller MUST commit promptly to
            satisfy the restart-survival contract.
        segment: The Segment the conflict is anchored to. The conflict's
            `satz_uuid` FK is set from `segment.satz_uuid`.
        rule_source: Which kind of automatic rule attempted to act
            (glossary / terminology / style_profile).
        conflict_type: Taxonomy of the conflict shape.
        context: Free-form JSONB for downstream resolution context — e.g.
            the rule entry's UUID, the attempted text, the prior text.

    Returns:
        The freshly inserted ConflictInstance (state=offen).
    """
    conflict = ConflictInstance(
        conflict_uuid=new_uuid(),
        satz_uuid=segment.satz_uuid,
        rule_source=rule_source.value,
        conflict_type=conflict_type.value,
        state=ConflictState.OFFEN.value,
        context=context if context is not None else {},
    )
    session.add(conflict)
    await session.flush()
    return conflict


# --- query helpers --------------------------------------------------------


async def get_open_conflicts_for_segment(
    *,
    session: AsyncSession,
    satz_uuid: _uuid.UUID,
) -> list[ConflictInstance]:
    """All open conflicts for a Segment, ordered by detected_at ascending."""
    result = await session.execute(
        select(ConflictInstance)
        .where(ConflictInstance.satz_uuid == satz_uuid)
        .where(ConflictInstance.state == ConflictState.OFFEN.value)
        .order_by(ConflictInstance.detected_at.asc())
    )
    return list(result.scalars())


async def get_open_conflicts_for_page(
    *,
    session: AsyncSession,
    page_uuid: _uuid.UUID,
) -> list[ConflictInstance]:
    """All open conflicts for a Page (any block, any segment)."""
    result = await session.execute(
        select(ConflictInstance)
        .join(Segment, Segment.satz_uuid == ConflictInstance.satz_uuid)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .where(Block.page_uuid == page_uuid)
        .where(ConflictInstance.state == ConflictState.OFFEN.value)
        .order_by(ConflictInstance.detected_at.asc())
    )
    return list(result.scalars())


async def get_open_conflicts_for_project(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> list[ConflictInstance]:
    """All open conflicts within a Project."""
    result = await session.execute(
        select(ConflictInstance)
        .join(Segment, Segment.satz_uuid == ConflictInstance.satz_uuid)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(ConflictInstance.state == ConflictState.OFFEN.value)
        .order_by(ConflictInstance.detected_at.asc())
    )
    return list(result.scalars())


# --- resolution paths -----------------------------------------------------


def _ensure_open(conflict: ConflictInstance) -> None:
    if conflict.state != ConflictState.OFFEN.value:
        raise ConflictAlreadyResolved(
            f"conflict {conflict.conflict_uuid} already in state "
            f"{conflict.state!r}; pre-resolution rows are immutable"
        )


async def _stamp_resolution(
    *,
    conflict: ConflictInstance,
    resolution_type: ResolutionType,
    decision_event_uuid: _uuid.UUID,
) -> None:
    """Apply the offen → aufgeloest transition. Atomic at the DB level via
    `ck_conflict_resolution_consistency`."""
    conflict.state = ConflictState.AUFGELOEST.value
    conflict.resolution_type = resolution_type.value
    conflict.decision_event_uuid = decision_event_uuid
    conflict.resolved_at = datetime.now(UTC)


async def resolve_with_local_exception(
    *,
    session: AsyncSession,
    conflict: ConflictInstance,
    actor_uuid: _uuid.UUID | None = None,
    content: dict[str, Any] | None = None,
) -> DecisionEvent:
    """Path 1 — `lokale_ausnahme`.

    The rule does not apply to this Segment. The rule itself is unchanged,
    so no glossary mutation or lock release happens — only the conflict row
    is resolved with a Decision Event recording the user's local-exception
    decision.
    """
    _ensure_open(conflict)
    de_content: dict[str, Any] = {
        "conflict_uuid": str(conflict.conflict_uuid),
        "resolution_type": ResolutionType.LOKALE_AUSNAHME.value,
        "rule_source": conflict.rule_source,
        "conflict_type": conflict.conflict_type,
    }
    if content:
        de_content.update(content)
    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=conflict.satz_uuid,
        decision_type="conflict_resolve_local_exception",
        decision_source=DecisionSource.CONFLICT_RESOLUTION,
        actor_uuid=actor_uuid,
        content=de_content,
    )
    await _stamp_resolution(
        conflict=conflict,
        resolution_type=ResolutionType.LOKALE_AUSNAHME,
        decision_event_uuid=de.decision_event_uuid,
    )
    await session.flush()
    return de


async def resolve_with_glossary_change(
    *,
    session: AsyncSession,
    conflict: ConflictInstance,
    new_concept_id: _uuid.UUID,
    actor_uuid: _uuid.UUID | None = None,
    content: dict[str, Any] | None = None,
) -> DecisionEvent:
    """Path 2 — `glossar_anpassen`.

    The glossary entry was adjusted (caller is responsible for invoking
    `glossary.update_entry` or `glossary.create_entry` first); the new
    entry's concept_id is recorded here as evidence of the resolution. The
    new entry version applies to all Segments — this conflict_instance row
    captures the user's "adjust glossary" decision, the glossary side
    captures the actual entry change.
    """
    _ensure_open(conflict)
    de_content: dict[str, Any] = {
        "conflict_uuid": str(conflict.conflict_uuid),
        "resolution_type": ResolutionType.GLOSSAR_ANPASSEN.value,
        "rule_source": conflict.rule_source,
        "conflict_type": conflict.conflict_type,
        "new_concept_id": str(new_concept_id),
    }
    if content:
        de_content.update(content)
    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=conflict.satz_uuid,
        decision_type="conflict_resolve_glossary_change",
        decision_source=DecisionSource.CONFLICT_RESOLUTION,
        actor_uuid=actor_uuid,
        content=de_content,
    )
    await _stamp_resolution(
        conflict=conflict,
        resolution_type=ResolutionType.GLOSSAR_ANPASSEN,
        decision_event_uuid=de.decision_event_uuid,
    )
    await session.flush()
    return de


async def resolve_with_lock_release(
    *,
    session: AsyncSession,
    conflict: ConflictInstance,
    segment: Segment,
    confirmation: ConfirmationContext | None = None,
    actor_uuid: _uuid.UUID | None = None,
    content: dict[str, Any] | None = None,
) -> tuple[DecisionEvent, DecisionEvent]:
    """Path 3 — `sperrflag_aufheben`.

    Releases the segment's `lock_flag` via T-5.1.1 (which itself writes a
    Decision Event + a MANUAL_-PO and enforces the editorial-confirmation
    rule), then writes the conflict-resolution Decision Event.

    Args:
        segment: The same Segment the conflict points to. Caller passes it
            explicitly so the lock release uses the live ORM row.
        confirmation: Forwarded to `release_lock`. Required when the segment
            is currently `manual_editorial`. `release_lock` raises
            `LockConfirmationRequired` otherwise.

    Returns:
        `(conflict_resolution_DE, lock_release_DE)`. Two distinct Decision
        Events: one for the conflict resolution (decision_source=
        `conflict_resolution`) and one for the lock change (decision_source=
        `lock_management`). The audit trail captures both moments.

    Raises:
        ConflictResolutionPathInvalid: if the segment is currently
            `lock_flag = none` (nothing to release — wrong path).
    """
    _ensure_open(conflict)
    if segment.lock_flag == LockFlag.NONE:
        raise ConflictResolutionPathInvalid(
            f"resolve_with_lock_release on segment {segment.satz_uuid} "
            f"that is not locked (lock_flag=none); use a different path"
        )
    if segment.satz_uuid != conflict.satz_uuid:
        raise ConflictResolutionPathInvalid(
            f"segment {segment.satz_uuid} does not match conflict.satz_uuid={conflict.satz_uuid}"
        )

    # Release the lock first. release_lock writes its own DE +
    # MANUAL_-PO and enforces the editorial-confirmation rule.
    lock_de, _lock_po = await release_lock(
        session=session,
        segment=segment,
        confirmation=confirmation,
        actor_uuid=actor_uuid,
    )

    de_content: dict[str, Any] = {
        "conflict_uuid": str(conflict.conflict_uuid),
        "resolution_type": ResolutionType.SPERRFLAG_AUFHEBEN.value,
        "rule_source": conflict.rule_source,
        "conflict_type": conflict.conflict_type,
        "lock_release_decision_event_uuid": str(lock_de.decision_event_uuid),
    }
    if content:
        de_content.update(content)
    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=conflict.satz_uuid,
        decision_type="conflict_resolve_lock_release",
        decision_source=DecisionSource.CONFLICT_RESOLUTION,
        actor_uuid=actor_uuid,
        content=de_content,
    )
    await _stamp_resolution(
        conflict=conflict,
        resolution_type=ResolutionType.SPERRFLAG_AUFHEBEN,
        decision_event_uuid=de.decision_event_uuid,
    )
    await session.flush()
    return de, lock_de
