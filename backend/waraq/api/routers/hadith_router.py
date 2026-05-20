"""§4.16 Hadith verification HTTP route — sub-batch J.

Wires the canonical `run_full_hadith_verification` helper into a
public endpoint so the UI can drive Hadith verification per segment
without operator-side bridging.

Per §4.16.1 the mandatory source set is P-1 (sunnah.com) + P-2
(Shamela / Kutub-as-Sitta) + P-3 (dorar.net). The v1.0 path:

  - **P-2 (Shamela)** is always exercised — Bukhari is locally
    ingested (Phase 4 sub-batch B'), so skeleton lookup against the
    Kutub-as-Sitta corpus produces real hits. This is the canonical
    primary path that always works without external network or API
    keys.
  - **P-1 (sunnah.com)** is exercised iff `SUNNAH_API_KEY` is in env
    AND the segment carries a `(collection, book, hadith_number)`
    triple via the optional request body. Without those the P-1
    fetcher's signature can't be satisfied (sunnah.com requires
    canonical addressing, no free-text search), so the path is
    skipped — canon-honest.
  - **P-3 (dorar.net)** API path is exercised when reachable;
    `ModelUClassB(retryable=False)` exceptions from the scraping
    fallback are swallowed per §3.5 (no retry).

The endpoint passes the gathered mandatory hits through
`run_full_hadith_verification`, which sequences `run_two_tier_verification`
+ `run_verification_round` in one transaction.
"""

from __future__ import annotations

import logging
import os
import uuid as _uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.api._ownership import owned_segment_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.db.session import get_settings
from waraq.external.model_u import ModelUClassA, ModelUClassB
from waraq.hadith import (
    HadithCandidateHit,
    Quellenrolle,
    run_full_hadith_verification,
)
from waraq.hadith.dorar import DorarHadith
from waraq.hadith.dorar import search_via_api as dorar_search_via_api
from waraq.hadith.sunnah import (
    SunnahApiKeyMissing,
    SunnahHadith,
)
from waraq.hadith.sunnah import (
    fetch_hadith as sunnah_fetch_hadith,
)
from waraq.schemas import Block, Page
from waraq.shamela import find_by_skeleton, shamela_hits_to_consensus_candidates
from waraq.text_state import resolve_segment_source_text

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/segments/{satz_uuid}/hadith", tags=["hadith"])


class _SunnahLookupRef(BaseModel):
    """Optional canonical sunnah.com address (collection + hadith number).
    Without it the P-1 path is skipped — sunnah.com requires canonical
    addressing, no free-text search."""

    collection: str
    hadith_number: int


class HadithVerifyRequest(BaseModel):
    """Optional request body for a hadith-verify call.

    All fields default to None — the simplest call is
    `POST /segments/{u}/hadith/verify` with no body.
    """

    sunnah_lookup: _SunnahLookupRef | None = None
    dorar_query: str | None = None
    manually_trigger_extended: bool = False


class _SourceCitation(BaseModel):
    source_name: str
    quellen_rolle: str
    matn_excerpt: str


class _RunSummary(BaseModel):
    aggregate_uuid: _uuid.UUID
    single_source_uuids: list[_uuid.UUID]
    superseded_aggregate_uuid: _uuid.UUID | None


class HadithVerifyResponse(BaseModel):
    satz_uuid: _uuid.UUID
    extended_set_triggered: bool
    extended_trigger_reason: str | None
    extended_sources_invoked: list[str]
    mandatory_count: int
    extended_count: int
    sources_skipped: list[str]  # e.g. ["sunnah_api_key_missing"]
    citations: list[_SourceCitation]
    run: _RunSummary | None  # None when no candidates were gathered


async def _gather_p2_shamela(session: AsyncSession, query_text: str) -> list[HadithCandidateHit]:
    """P-2 (Shamela) skeleton lookup, scoped to Kutub-as-Sitta."""
    if not query_text.strip():
        return []
    hits = await find_by_skeleton(
        session,
        candidate_text=query_text,
        only_kutub_as_sitta=True,
        limit=20,
    )
    return shamela_hits_to_consensus_candidates(hits)


def _sunnah_to_candidate(hadith: SunnahHadith) -> HadithCandidateHit:
    """Adapt a `SunnahHadith` to a `HadithCandidateHit` for consensus.
    Lives in the router since the canonical sunnah-side model
    deliberately doesn't depend on the consensus types."""
    # `hadith.grades` is `list[dict[str, Any]]` (sunnah.com returns one
    # row per grader). Collapse to a comma-separated string of grade
    # values for the authenticity-grade slot the consensus engine reads.
    grade_values: list[str] = []
    for g in hadith.grades:
        v = g.get("grade") if isinstance(g, dict) else None
        if isinstance(v, str) and v:
            grade_values.append(v)
    return HadithCandidateHit(
        source_name="sunnah.com",
        quellen_rolle=Quellenrolle.PFLICHT,
        matn_arabic=hadith.matn_arabic,
        matn_vocalized=None,
        isnad_chain=[],
        collection_label=hadith.collection,
        authenticity_grade=", ".join(grade_values) if grade_values else None,
        raw_payload=dict(hadith.raw_payload),
    )


def _dorar_to_candidate(hadith: DorarHadith) -> HadithCandidateHit:
    """Adapt a `DorarHadith` to a `HadithCandidateHit` for consensus."""
    return HadithCandidateHit(
        source_name="dorar.net",
        quellen_rolle=Quellenrolle.PFLICHT,
        matn_arabic=hadith.matn,
        matn_vocalized=None,
        isnad_chain=[hadith.rawi] if hadith.rawi else [],
        collection_label=hadith.book or "",
        authenticity_grade=hadith.grade,
        raw_payload=dict(hadith.raw_payload),
    )


async def _gather_p1_sunnah(
    sunnah_lookup: _SunnahLookupRef,
) -> tuple[list[HadithCandidateHit], list[str]]:
    """P-1 (sunnah.com) direct lookup. Returns (candidates, skip_reasons)."""
    skips: list[str] = []
    api_key = os.environ.get("SUNNAH_COM_API_KEY", "")
    try:
        hadith = await sunnah_fetch_hadith(
            collection=sunnah_lookup.collection,
            hadith_number=sunnah_lookup.hadith_number,
            api_key=api_key,
        )
    except SunnahApiKeyMissing:
        skips.append("sunnah_api_key_missing")
        return [], skips
    except (ModelUClassA, ModelUClassB) as exc:
        logger.info("hadith.sunnah_skipped: %r", exc)
        skips.append(f"sunnah_unreachable:{type(exc).__name__}")
        return [], skips
    return [_sunnah_to_candidate(hadith)], skips


async def _gather_p3_dorar(
    dorar_query: str,
) -> tuple[list[HadithCandidateHit], list[str]]:
    """P-3 (dorar.net) API search. Returns (candidates, skip_reasons)."""
    skips: list[str] = []
    if not dorar_query.strip():
        return [], skips
    settings = get_settings()
    try:
        results = await dorar_search_via_api(
            query=dorar_query,
            base_url=settings.dorar_net_base_url,
            api_key=settings.dorar_net_api_key or None,
        )
    except (ModelUClassA, ModelUClassB) as exc:
        logger.info("hadith.dorar_skipped: %r", exc)
        skips.append(f"dorar_unreachable:{type(exc).__name__}")
        return [], skips
    return [_dorar_to_candidate(r) for r in results], skips


def _excerpt(text: str, *, n: int = 80) -> str:
    text = text.strip()
    if len(text) <= n:
        return text
    return text[: n - 1] + "…"


@router.post("/verify", response_model=HadithVerifyResponse, status_code=status.HTTP_200_OK)
async def verify_hadith(
    satz_uuid: _uuid.UUID,
    req: HadithVerifyRequest,
    session: DbSession,
    current: CurrentAccount,
) -> HadithVerifyResponse:
    """Run §4.16 two-tier hadith verification on `satz_uuid`.

    Gathers mandatory P-1/P-2/P-3 hits per the rules in the module
    docstring, then sequences `run_two_tier_verification` →
    `run_verification_round` via `run_full_hadith_verification`.

    Returns the full outcome (consensus + Level-2 + Level-3 row UUIDs)
    when at least one candidate was gathered; returns the empty
    summary when none were (no DB write — canonical no-write path).
    """
    segment = await owned_segment_or_404(session, satz_uuid, current.account_uuid)
    block = await session.get(Block, segment.block_uuid)
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment block missing")
    page = await session.get(Page, block.page_uuid)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment page missing")

    query_text = (await resolve_segment_source_text(session=session, segment=segment)).strip()

    skips: list[str] = []
    mandatory: list[HadithCandidateHit] = []

    p2 = await _gather_p2_shamela(session, query_text)
    mandatory.extend(p2)

    if req.sunnah_lookup is not None:
        p1, p1_skips = await _gather_p1_sunnah(req.sunnah_lookup)
        mandatory.extend(p1)
        skips.extend(p1_skips)
    else:
        skips.append("sunnah_no_lookup_address")

    dorar_q = req.dorar_query or query_text
    p3, p3_skips = await _gather_p3_dorar(dorar_q)
    mandatory.extend(p3)
    skips.extend(p3_skips)

    outcome = await run_full_hadith_verification(
        session=session,
        project_uuid=page.project_uuid,
        satz_uuid=segment.satz_uuid,
        block_uuid=segment.block_uuid,
        ocr_rev_uuid=segment.current_rev_uuid,
        mandatory_hits=mandatory,
        query=query_text,
        manually_trigger_extended=req.manually_trigger_extended,
    )

    citations = [
        _SourceCitation(
            source_name=hit.source_name,
            quellen_rolle=hit.quellen_rolle.value,
            matn_excerpt=_excerpt(hit.matn_arabic),
        )
        for hit in (list(outcome.two_tier.mandatory_hits) + list(outcome.two_tier.extended_hits))
    ]

    run_summary: _RunSummary | None = None
    if outcome.run is not None:
        run_summary = _RunSummary(
            aggregate_uuid=outcome.run.aggregate_uuid,
            single_source_uuids=list(outcome.run.single_source_uuids),
            superseded_aggregate_uuid=outcome.run.superseded_aggregate_uuid,
        )

    return HadithVerifyResponse(
        satz_uuid=segment.satz_uuid,
        extended_set_triggered=outcome.two_tier.extended_set_triggered,
        extended_trigger_reason=outcome.two_tier.extended_trigger_reason,
        extended_sources_invoked=list(outcome.two_tier.extended_sources_invoked),
        mandatory_count=len(outcome.two_tier.mandatory_hits),
        extended_count=len(outcome.two_tier.extended_hits),
        sources_skipped=skips,
        citations=citations,
        run=run_summary,
    )
