"""LINEAGE service — covers all five lineage transitions across T-4.2.1 and T-4.2.2.

Per Sprint 1 §2 / DBB §B Abkürzung 8 / CLAUDE.md §5.5: lineage matching is a
**system event**, not a user decision. Lineage operations write:

- LINEAGE_EVENT-POs through PROVENANCE-Kern (`scope_type=segment`,
  `automatisch=True`, system-authored: `author_uuid=None`)
- Log-Einträge through EVENTING

Lineage operations **never** write Decision Events. Modeling lineage as a user
decision floods the decision-event table and makes the user-decision history
unreadable (Sprint 1 R-S1-01).

H-5 discipline: any "disappearance" inactivates via the IDENTITY service
`mark_inactive`. The satz_uuid is preserved; the row is never deleted, never
recycled.

Coverage:

- T-4.2.1 — 1→1 (preserve UUID), 1→0 (inactivation).
- T-4.2.2 — 1→n (split), n→1 (merge), reactivation (in `reactivation.py`).

Atomicity: caller owns the transaction. Each entrypoint flushes (so the
LINEAGE_EVENT-PO and Log-Eintrag rows land in the open transaction); commit
or rollback is the caller's responsibility.
"""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.eventing import log_event
from waraq.identity import mark_inactive
from waraq.provenance import create_po
from waraq.schemas import ProvenanceObject, Segment
from waraq.schemas.enums import POType, ScopeType


def _lineage_payload(
    *,
    match_kind: str,
    herkunft_uuids: list[_uuid.UUID],
    ziel_uuids: list[_uuid.UUID],
) -> dict[str, object]:
    """Canonical LINEAGE_EVENT-PO payload shape.

    `automatisch=True` is verbatim per Sprint 1 §2 — system-matching events
    are flagged so downstream history queries can distinguish them from user
    decisions even at the readout layer (Sprint 6 R-S6-09).
    """
    return {
        "match_kind": match_kind,
        "automatisch": True,
        "herkunft_uuid": [str(u) for u in herkunft_uuids],
        "ziel_uuid": [str(u) for u in ziel_uuids],
    }


async def record_one_to_one(
    *,
    session: AsyncSession,
    satz_uuid: _uuid.UUID,
) -> ProvenanceObject:
    """T-4.2.1: 1→1 lineage transition.

    On re-segmentation, an existing satz_uuid survives because the
    surrounding text content was preserved. The Segment row is **not**
    mutated here — its identity is preserved by the simple act of not
    issuing a new UUID. We record the survival as a LINEAGE_EVENT-PO
    (provenance) plus a Log-Eintrag (operational trail).

    Args:
        session: Active async session. Caller manages commit/rollback.
        satz_uuid: The preserved Segment identity. Both `herkunft_uuid` and
            `ziel_uuid` carry this single value, per the canonical
            LINEAGE_EVENT-PO payload shape (Sprint 1 §2).

    Returns:
        The LINEAGE_EVENT-PO. The Log-Eintrag is also staged but not returned
        — callers needing it can query by `scope_uuid`.
    """
    po = await create_po(
        session=session,
        po_type=POType.LINEAGE_EVENT,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=satz_uuid,
        payload=_lineage_payload(
            match_kind="1to1",
            herkunft_uuids=[satz_uuid],
            ziel_uuids=[satz_uuid],
        ),
        author_uuid=None,
    )
    await log_event(
        session=session,
        operation_type="lineage_match_1to1",
        scope_type=ScopeType.SEGMENT,
        scope_uuid=satz_uuid,
        result={"po_uuid": str(po.po_uuid), "match_kind": "1to1"},
    )
    return po


async def inactivate_segment(
    *,
    session: AsyncSession,
    segment: Segment,
) -> ProvenanceObject:
    """T-4.2.1: 1→0 lineage transition.

    A Segment that disappears from the new layout is inactivated via H-5:
    `active = true → false`. The UUID is retained — the row remains queryable
    so downstream provenance/history paths can still reach it (Sprint 6
    history endpoints).

    Args:
        session: Active async session. Caller manages commit/rollback.
        segment: The disappearing Segment. Must currently be `active`. Its
            `active` field is flipped here via the IDENTITY service.

    Returns:
        The LINEAGE_EVENT-PO. `ziel_uuid[]` is empty (the canonical 1→0
        payload shape).
    """
    mark_inactive(segment)
    # Force the active flag through to the database row. In-test the flush is
    # what materializes the change inside the open transaction; production
    # callers benefit from the same explicitness.
    await session.flush()

    po = await create_po(
        session=session,
        po_type=POType.LINEAGE_EVENT,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=segment.satz_uuid,
        payload=_lineage_payload(
            match_kind="1to0",
            herkunft_uuids=[segment.satz_uuid],
            ziel_uuids=[],
        ),
        author_uuid=None,
    )
    await log_event(
        session=session,
        operation_type="lineage_inactivate_1to0",
        scope_type=ScopeType.SEGMENT,
        scope_uuid=segment.satz_uuid,
        result={"po_uuid": str(po.po_uuid), "match_kind": "1to0"},
    )
    return po


async def record_split(
    *,
    session: AsyncSession,
    source: Segment,
    daughters: list[Segment],
) -> ProvenanceObject:
    """T-4.2.2: 1→n Aufspaltung (split).

    A single Segment is replaced by `n` daughter Segments. The source UUID
    is referenced in `herkunft_uuid[]`; daughter UUIDs go in `ziel_uuid[]`.
    Source is inactivated. Daughters are assumed to already exist with
    issued UUIDs — caller is responsible for creating them with `new_uuid()`
    and inserting them. The LINEAGE service exists to record the matching,
    not to manage Segment creation.

    Args:
        session: Active async session. Caller manages commit/rollback.
        source: The original Segment to inactivate. Must currently be active.
        daughters: At least 2 daughter Segments produced by re-segmentation.
            Caller is responsible for FK chain coherence (same Block scope
            is conventional but not enforced here — the LINEAGE_EVENT-PO is
            anchored at `scope_type=segment` on the source).

    Returns:
        The LINEAGE_EVENT-PO recording the split.
    """
    if len(daughters) < 2:
        raise ValueError(
            f"record_split requires at least 2 daughters; got {len(daughters)}. "
            "For 1→1 use record_one_to_one; for 1→0 use inactivate_segment."
        )

    mark_inactive(source)
    await session.flush()

    daughter_uuids = [d.satz_uuid for d in daughters]
    po = await create_po(
        session=session,
        po_type=POType.LINEAGE_EVENT,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=source.satz_uuid,
        payload=_lineage_payload(
            match_kind="1ton",
            herkunft_uuids=[source.satz_uuid],
            ziel_uuids=daughter_uuids,
        ),
        author_uuid=None,
    )
    await log_event(
        session=session,
        operation_type="lineage_split_1ton",
        scope_type=ScopeType.SEGMENT,
        scope_uuid=source.satz_uuid,
        result={
            "po_uuid": str(po.po_uuid),
            "match_kind": "1ton",
            "n_daughters": len(daughters),
        },
    )
    return po


async def record_merge(
    *,
    session: AsyncSession,
    sources: list[Segment],
    target: Segment,
) -> ProvenanceObject:
    """T-4.2.2: n→1 Zusammenführung (merge).

    Multiple source Segments are replaced by a single target Segment. All
    source UUIDs go in `herkunft_uuid[]`; the target UUID goes in
    `ziel_uuid[]`. Each source is inactivated. The target is assumed to
    already exist with an issued UUID.

    Args:
        session: Active async session. Caller manages commit/rollback.
        sources: At least 2 source Segments to inactivate.
        target: The single Segment that consumed the merged content.

    Returns:
        The LINEAGE_EVENT-PO recording the merge. Anchored at the target's
        UUID — that's the surviving Segment whose history continues.
    """
    if len(sources) < 2:
        raise ValueError(
            f"record_merge requires at least 2 sources; got {len(sources)}. "
            "For 1→1 use record_one_to_one; for 1→0 use inactivate_segment."
        )

    for source in sources:
        mark_inactive(source)
    await session.flush()

    source_uuids = [s.satz_uuid for s in sources]
    po = await create_po(
        session=session,
        po_type=POType.LINEAGE_EVENT,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=target.satz_uuid,
        payload=_lineage_payload(
            match_kind="nto1",
            herkunft_uuids=source_uuids,
            ziel_uuids=[target.satz_uuid],
        ),
        author_uuid=None,
    )
    await log_event(
        session=session,
        operation_type="lineage_merge_nto1",
        scope_type=ScopeType.SEGMENT,
        scope_uuid=target.satz_uuid,
        result={
            "po_uuid": str(po.po_uuid),
            "match_kind": "nto1",
            "n_sources": len(sources),
        },
    )
    return po
