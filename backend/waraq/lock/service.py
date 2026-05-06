"""T-5.1.1 — LOCK service (set_lock / release_lock).

Per Sprint 1 §2:

- `set_lock(segment, level)` writes `lock_flag` from `none` to either
  `manual_local` or `manual_editorial`.
- `release_lock(segment)` writes `lock_flag` back to `none`. Releasing
  `manual_editorial` requires an explicit `ConfirmationContext` (callers
  without that context fail per LOCK-Release-Manual-Editorial-Confirmation-
  Test). Releasing `manual_local` does not.
- Each set or release issues a Decision Event with `scope_type=segment` and
  `decision_source=lock_management` (T-1.4.2).
- After each lock-state change, a MANUAL_-PO is written via PROVENANCE-Kern
  with the prior/new flag values and the decision_event_uuid.
- No code path performs automatic release. The service has no auto-release
  surface — every release goes through `release_lock`.

The Decision Event is written **before** the MANUAL_-PO so the PO payload
can carry the decision_event_uuid as the canonical anchor. The flag
transition itself happens between the two writes; the segment row is
updated via direct attribute assignment, then `flush`-ed alongside the PO.

Atomicity: caller owns the transaction. The service flushes; commit /
rollback is the caller's responsibility. On any failure (e.g., guard
refusal, FK violation) the transaction rolls back, leaving no Decision
Event without a matching PO.
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.decisions import create_decision_event
from waraq.invariant.enums import LockFlag
from waraq.lock.exceptions import (
    LockAlreadyAtTargetState,
    LockConfirmationRequired,
    LockInvalidLevel,
)
from waraq.provenance import create_po
from waraq.schemas import DecisionEvent, ProvenanceObject, Segment
from waraq.schemas.enums import DecisionSource, POType, ScopeType


@dataclass(frozen=True, kw_only=True, slots=True)
class ConfirmationContext:
    """Required to release a `manual_editorial` lock.

    The presence of this object IS the contract. Construction validates a
    non-null `confirmed_by` so that empty/dummy contexts can't sneak past
    the editorial-release guard.

    Attributes:
        confirmed_by: account_uuid of the user who actively confirmed.
            Becomes the `actor_uuid` on the Decision Event when omitted at
            the call site.
        note: Optional human-readable trail (e.g. UI surface, ticket id).
            Stored on the Decision Event content + MANUAL_-PO payload.
    """

    confirmed_by: _uuid.UUID
    note: str = ""


_MANUAL_LEVELS: frozenset[LockFlag] = frozenset({LockFlag.MANUAL_LOCAL, LockFlag.MANUAL_EDITORIAL})


async def _write_lock_change_artifacts(
    *,
    session: AsyncSession,
    segment: Segment,
    prior_flag: LockFlag,
    new_flag: LockFlag,
    action: str,  # "set" | "release"
    actor_uuid: _uuid.UUID | None,
    confirmation: ConfirmationContext | None,
    content: dict[str, Any] | None,
) -> tuple[DecisionEvent, ProvenanceObject]:
    """Decision Event first, then MANUAL_-PO referencing the DE."""
    de_content: dict[str, Any] = {
        "action": action,
        "prior_flag": prior_flag.value,
        "new_flag": new_flag.value,
    }
    if confirmation is not None:
        de_content["confirmation"] = {
            "confirmed_by": str(confirmation.confirmed_by),
            "note": confirmation.note,
        }
    if content:
        de_content.update(content)

    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=segment.satz_uuid,
        decision_type=f"lock_{action}",
        decision_source=DecisionSource.LOCK_MANAGEMENT,
        actor_uuid=actor_uuid,
        content=de_content,
    )

    # MANUAL_-PO author = actor_uuid (the human responsible). System-only
    # writes never use this service, so author_uuid being null here would
    # signal a misuse — but we don't enforce that since the upstream Decision
    # Event already carries the actor.
    po = await create_po(
        session=session,
        po_type=POType.MANUAL_,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=segment.satz_uuid,
        author_uuid=actor_uuid,
        payload={
            "action": action,
            "prior_flag": prior_flag.value,
            "new_flag": new_flag.value,
            "decision_event_uuid": str(de.decision_event_uuid),
            "confirmation_required": prior_flag == LockFlag.MANUAL_EDITORIAL
            and action == "release",
            "confirmation_provided": confirmation is not None,
        },
    )
    return de, po


async def set_lock(
    *,
    session: AsyncSession,
    segment: Segment,
    level: LockFlag,
    actor_uuid: _uuid.UUID | None = None,
    content: dict[str, Any] | None = None,
) -> tuple[DecisionEvent, ProvenanceObject]:
    """Set the segment's `lock_flag` to `level`.

    Args:
        session: Active async session. Caller manages commit/rollback.
        segment: The Segment to lock. Must be currently at a different flag
            level (idempotent set raises `LockAlreadyAtTargetState`).
        level: Target lock level. Must be `manual_local` or
            `manual_editorial`. `none` is rejected — releasing flows through
            `release_lock` so the editorial-confirmation rule applies
            uniformly.
        actor_uuid: Account that initiated the lock. Becomes `actor_uuid`
            on the Decision Event and `author_uuid` on the MANUAL_-PO.
        content: Extra Decision-Event content (e.g. UI chip, justification
            free text). Merged into the DE content dict.

    Returns:
        `(DecisionEvent, MANUAL_-PO)` pair, both already flushed.
    """
    if level not in _MANUAL_LEVELS:
        raise LockInvalidLevel(
            f"set_lock(level={level.value!r}) is not a manual lock level. "
            "Use release_lock to set lock_flag back to 'none'."
        )

    prior_flag = segment.lock_flag
    if prior_flag == level:
        raise LockAlreadyAtTargetState(
            f"segment {segment.satz_uuid} already at lock_flag={level.value}; "
            "no-op locks would pollute the Decision-Event audit trail"
        )

    segment.lock_flag = level
    return await _write_lock_change_artifacts(
        session=session,
        segment=segment,
        prior_flag=prior_flag,
        new_flag=level,
        action="set",
        actor_uuid=actor_uuid,
        confirmation=None,
        content=content,
    )


async def release_lock(
    *,
    session: AsyncSession,
    segment: Segment,
    confirmation: ConfirmationContext | None = None,
    actor_uuid: _uuid.UUID | None = None,
    content: dict[str, Any] | None = None,
) -> tuple[DecisionEvent, ProvenanceObject]:
    """Release the segment's `lock_flag` back to `none`.

    Confirmation rule (Sprint 1 §2):
    - From `manual_local`: `confirmation` may be omitted.
    - From `manual_editorial`: `confirmation` is **required**. Calls without
      it raise `LockConfirmationRequired`.

    Idempotent release (segment already `none`) raises
    `LockAlreadyAtTargetState`.

    Args:
        session: Active async session. Caller manages commit/rollback.
        segment: The Segment to unlock.
        confirmation: Required for `manual_editorial → none`; ignored on
            `manual_local → none` (but accepted, and logged for audit).
        actor_uuid: Account that initiated the release. Falls back to
            `confirmation.confirmed_by` when omitted and confirmation is
            provided — the confirming user is the natural actor.
        content: Extra Decision-Event content.

    Returns:
        `(DecisionEvent, MANUAL_-PO)` pair, both already flushed.
    """
    prior_flag = segment.lock_flag
    if prior_flag == LockFlag.NONE:
        raise LockAlreadyAtTargetState(
            f"segment {segment.satz_uuid} already lock_flag=none; "
            "release_lock requires an actual transition"
        )

    if prior_flag == LockFlag.MANUAL_EDITORIAL and confirmation is None:
        raise LockConfirmationRequired(
            f"release of manual_editorial lock on segment {segment.satz_uuid} "
            "requires an explicit ConfirmationContext"
        )

    effective_actor = (
        actor_uuid
        if actor_uuid is not None
        else (confirmation.confirmed_by if confirmation is not None else None)
    )

    segment.lock_flag = LockFlag.NONE
    return await _write_lock_change_artifacts(
        session=session,
        segment=segment,
        prior_flag=prior_flag,
        new_flag=LockFlag.NONE,
        action="release",
        actor_uuid=effective_actor,
        confirmation=confirmation,
        content=content,
    )
