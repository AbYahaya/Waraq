"""Rule-binding endpoint — apply glossary to a segment.

Caller supplies candidate surface forms. The service resolves each via
`glossary.lookup`, then either writes a RULE_BINDING-PO (unlocked) or
detects a conflict (locked).
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter
from sqlalchemy import select

from waraq.api._ownership import owned_segment_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import RuleBindingApplyRequest, RuleBindingResponse
from waraq.rule_binding import bind_glossary_to_segment
from waraq.schemas import Block, Page

router = APIRouter(prefix="/segments/{satz_uuid}/rule-binding", tags=["rule-binding"])


@router.post("", response_model=RuleBindingResponse)
async def apply_rule_binding(
    satz_uuid: _uuid.UUID,
    req: RuleBindingApplyRequest,
    session: DbSession,
    current: CurrentAccount,
) -> RuleBindingResponse:
    segment = await owned_segment_or_404(session, satz_uuid, current.account_uuid)
    # Resolve project_uuid via segment → block → page → project
    block = await session.get(Block, segment.block_uuid)
    assert block is not None  # ownership guard already verified the chain
    page = await session.get(Page, block.page_uuid)
    assert page is not None
    project_uuid = page.project_uuid

    result = await bind_glossary_to_segment(
        session=session,
        segment=segment,
        project_uuid=project_uuid,
        account_uuid=current.account_uuid,
        candidate_surface_forms=list(req.candidate_surface_forms),
        application_context=req.application_context,
    )

    matched_concepts = list(
        {a.concept_id for a in result.applied} | {c.concept_id for c in result.conflicts}
    )

    if result.conflicts:
        return RuleBindingResponse(
            outcome="conflict_detected",
            matched_concept_ids=matched_concepts,
            conflict_uuid=result.conflicts[0].conflict_uuid,
            rule_binding_po_uuid=None,
        )
    return RuleBindingResponse(
        outcome="applied",
        matched_concept_ids=matched_concepts,
        conflict_uuid=None,
        rule_binding_po_uuid=(result.applied[0].po_uuid if result.applied else None),
    )


_ = select  # silence unused
