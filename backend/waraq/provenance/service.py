"""T-1.6.1 — PROVENANCE-Kern `create_po` service.

CAB §5.3 / CLAUDE.md §5.3: PROVENANCE-Kern is the **sole writer** to the
`provenance_objects` table. All seven canonical PO types — SCAN, OCR,
MANUAL_, RULE_BINDING, TRANSLATION, LINEAGE_EVENT, EXPORT_EVENT — go through
this single function.

DBB §B Abkürzung 7: "Upload-Handler writes SCAN-PO directly instead of through
PROVENANCE-Kern" is the named structural failure mode. Every PO insert in the
codebase MUST go through `create_po`. Bypass is a discipline violation.

DBB §B Abkürzung 4 / CLAUDE.md §5.4: EXPORT_EVENT atomicity is unverhandelbar.
EXPORT_EVENT is created **only after** the artefact is fully produced.
Implementation pattern (caller-side, not enforced here):

    async with session.begin():
        # 1. Move artefact to persistent location
        await move_artefact(temp_path, persistent_path)
        # 2. Create the EXPORT_EVENT-PO
        await create_po(
            session=session,
            po_type=POType.EXPORT_EVENT,
            scope_type=ScopeType.PROJECT,
            scope_uuid=project_uuid,
            payload={
                "filename": "...", "format": "docx",
                "sha256": "...", "size_bytes": ...,
            },
        )
        # 3. Mark the export job complete
        await mark_job_complete(session, job_uuid)

If any step fails, the transaction rolls back and no EXPORT_EVENT row exists.

This service does **not** carry a `satz_uuid` parameter (Abkürzung 2). All
addressing is via `scope_type` + `scope_uuid`, polymorphic across the five
canonical scope values. For segment-scoped POs (OCR, MANUAL_, RULE_BINDING,
TRANSLATION, LINEAGE_EVENT) callers pass `scope_type=ScopeType.SEGMENT` and
`scope_uuid=segment.satz_uuid`.

Atomicity: caller owns the transaction. The service flushes; commit/rollback
is the caller's responsibility.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity.service import new_uuid
from waraq.schemas import ProvenanceObject
from waraq.schemas.enums import POType, ScopeType


async def create_po(
    *,
    session: AsyncSession,
    po_type: POType,
    scope_type: ScopeType,
    scope_uuid: _uuid.UUID,
    payload: dict[str, Any] | None = None,
    author_uuid: _uuid.UUID | None = None,
) -> ProvenanceObject:
    """Stage a Provenance Object row.

    Args:
        session: Active async session. Caller manages commit/rollback.
            For EXPORT_EVENT the caller MUST wrap this call in a transaction
            that also performs the artefact-move and job-completion steps;
            partial commit violates §5.4 atomicity.
        po_type: One of the seven canonical POType values.
        scope_type: Canonical scope value (segment | page | block | account |
            project). For EXPORT_EVENT use ScopeType.PROJECT (the "work").
        scope_uuid: Identifier of the scoped object. Polymorphic — meaning
            depends on `scope_type`. Not FK-constrained at the schema level.
            For EXPORT_EVENT this is the project_uuid.
        payload: PO-specific JSONB data. Defaults to `{}`. For EXPORT_EVENT
            the canonical shape is `{"filename": str, "format": str,
            "sha256": str, "size_bytes": int}`; T-1.6.1 does not validate
            payload shape — that's per-type service responsibility.
        author_uuid: Identity of the actor that produced the PO. None for
            system-authored POs (LINEAGE_EVENT-PO, automatic SCAN-PO
            finalization).

    Returns:
        The ProvenanceObject instance with `po_uuid` populated.
    """
    po = ProvenanceObject(
        po_uuid=new_uuid(),
        po_type=po_type,
        scope_type=scope_type,
        scope_uuid=scope_uuid,
        payload=payload if payload is not None else {},
        author_uuid=author_uuid,
    )
    session.add(po)
    await session.flush()
    return po
