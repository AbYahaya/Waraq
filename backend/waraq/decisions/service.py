"""T-1.4.2 — `create_decision_event` service.

Per CAB §5.2 / CLAUDE.md §5.2: a Decision Event is a user decision. It carries
`scope_type` + `scope_uuid` (polymorphic across the five canonical scope
values), a `decision_type` label, one of the ten canonical `decision_source`
values per Dokument 1 §4.10, and a JSONB `content` payload.

Discipline contract for this service:

- **Three-tables separation (DBB Abkürzung 3).** This service writes only to
  `decision_events`. It does not insert into `revisions` or `log_entries`,
  and it does not update any Segment field. The signature deliberately
  exposes no `before_text`/`after_text`/`change_source` kwargs — there is no
  way to confuse this code path with `create_revision`.

- **H-4 separation.** No revision-UUID is generated here. Decision events
  describe a *decision*, not a *text change*; even when the decision is
  "accept this OCR text," the actual text write goes through
  `create_revision` in a different call.

- **Lineage matching produces no Decision Events** (CLAUDE.md §5.5).
  This service must not be called from lineage matching code paths;
  lineage events go through `log_event` (T-1.5.1) and Provenance.

Atomicity: caller owns the transaction. The service flushes; commit/rollback
is the caller's responsibility.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity.service import new_uuid
from waraq.schemas.enums import DecisionSource, ScopeType
from waraq.schemas.events import DecisionEvent


async def create_decision_event(
    *,
    session: AsyncSession,
    scope_type: ScopeType,
    scope_uuid: _uuid.UUID,
    decision_type: str,
    decision_source: DecisionSource,
    content: dict[str, Any] | None = None,
    actor_uuid: _uuid.UUID | None = None,
    related_export_attempt_id: str | None = None,
) -> DecisionEvent:
    """Stage a Decision Event row.

    Args:
        session: Active async session. Caller manages commit/rollback.
        scope_type: One of the five canonical ScopeType values
            (segment | page | block | account | project).
        scope_uuid: Identifier of the scoped object. Polymorphic — interpretation
            depends on `scope_type`. Not FK-constrained at the schema level
            (would require five different FK targets); the writing service is
            responsible for ensuring `scope_uuid` actually points at a row of
            the matching kind.
        decision_type: Free-text label for the *kind* of decision (e.g.,
            "ocr_accept", "lock_set"). Format conventions per scope live in
            the calling service, not in this generic writer.
        decision_source: One of the ten canonical DecisionSource values
            (Dokument 1 §4.10). DB CHECK constraint rejects everything else.
        content: JSONB payload for decision-specific data. Defaults to an
            empty dict if omitted.
        actor_uuid: Identity of the user who made the decision. None for
            system-promoted decisions where the canon allows it.

    Returns:
        The DecisionEvent instance with `decision_event_uuid` populated.
    """
    decision_event = DecisionEvent(
        decision_event_uuid=new_uuid(),
        scope_type=scope_type,
        scope_uuid=scope_uuid,
        decision_type=decision_type,
        decision_source=decision_source,
        content=content if content is not None else {},
        actor_uuid=actor_uuid,
        related_export_attempt_id=related_export_attempt_id,
    )
    session.add(decision_event)
    await session.flush()
    return decision_event
