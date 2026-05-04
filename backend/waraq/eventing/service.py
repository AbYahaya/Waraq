"""T-1.5.1 — EVENTING `log_event` service.

Per CAB §5.2 / CLAUDE.md §5.2, a Log-Eintrag is an operational/system event:
`log_id` (UUID), `operation_type`, `result` JSONB.

Per CLAUDE.md §5.5, **lineage matching is a system event, not a user
decision**. Lineage-related operations (1→1, 1→0, 1→n, n→1, reactivation)
write Log-Einträge here (and LINEAGE_EVENT-POs in Provenance). They never
write Decision Events — modeling lineage as a decision floods the
decision-event table and makes the user-decision history unreadable.

Discipline contract for this service:

- **Three-tables separation (DBB Abkürzung 3).** This service writes only to
  `log_entries`. The signature exposes no decision-shaped kwargs
  (`decision_type`, `decision_source`) and no text-change kwargs
  (`before_text`, `after_text`, `change_source`). It cannot be misused for
  the §5.5 lineage-as-decision-event failure mode.

- **H-4 separation.** No revision-UUID is generated here. A Log-Eintrag
  describes that something happened; it is not a text change.

Atomicity: caller owns the transaction. The service flushes; commit/rollback
is the caller's responsibility.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity.service import new_uuid
from waraq.schemas import LogEntry
from waraq.schemas.enums import ScopeType


async def log_event(
    *,
    session: AsyncSession,
    operation_type: str,
    result: dict[str, Any] | None = None,
    scope_type: ScopeType | None = None,
    scope_uuid: _uuid.UUID | None = None,
) -> LogEntry:
    """Stage a Log-Eintrag row.

    Args:
        session: Active async session. Caller manages commit/rollback.
        operation_type: Free-text label for the *kind* of operation (e.g.,
            "lineage_match_1to1", "ocr_run_started", "checkpoint_written").
            The vocabulary is owned by the calling service, not by this
            generic writer.
        result: JSONB payload describing the operation outcome — match
            details, error info, counts, references to other UUIDs.
            Defaults to `{}` when omitted.
        scope_type: Optional canonical scope value for filtered reads (e.g.,
            tag a lineage log entry as `ScopeType.SEGMENT`). When set,
            `scope_uuid` should be set too; the service does not enforce that
            relationship — it is a read-side convenience.
        scope_uuid: Optional scoped object identifier. Polymorphic per
            `scope_type`. Not FK-constrained at the schema level (would
            require five different FK targets).

    Returns:
        The LogEntry instance with `log_id` populated.
    """
    log_entry = LogEntry(
        log_id=new_uuid(),
        operation_type=operation_type,
        result=result if result is not None else {},
        scope_type=scope_type.value if scope_type is not None else None,
        scope_uuid=scope_uuid,
    )
    session.add(log_entry)
    await session.flush()
    return log_entry
