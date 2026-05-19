"""Lean read-only diagnostic endpoints for verifying Phase 1–4 wiring.

Sub-batch J ships an end-to-end-testable pipeline. This router gives
the human tester a single, no-nonsense surface to verify that every
backend signal actually lands and the data we ingested is reachable.
NOT meant as production UI — kept under `/diagnostics/*` so a future
production gate can hide it.

Endpoints (all GET unless noted, all auth-gated):

  - `GET  /diagnostics/segments/{satz_uuid}/ocr-po`
        Return the latest OCR-PO payload JSON for the segment so the
        tester can see Stage-2 engines, agreement, Stage-3 breakdown,
        quality scores, homoglyph candidates — exactly what `run_ocr_job`
        wrote.

  - `GET  /diagnostics/quran/verse?sura=N&aya=M`
        Tanzil-Hafs lookup against the local AR-Referenzbestand
        (operator step 1 — populated 2026-05-10).

  - `GET  /diagnostics/quran/translation?sura=N&aya=M&key=german_rwwad`
        quranenc.com Mode-A lookup (local fallback) — operator step 2
        populated 2026-05-10.

  - `GET  /diagnostics/shamela/search?query=...&mode=skeleton|keyword`
        Mode-A skeleton lookup (used by §3.4 Stage-3 statistical) or
        Mode-B keyword search.

  - `GET  /diagnostics/morphology/analyze?word=...`
        CAMeL Tools morphology analyses (operator step 3 — DB
        installed 2026-05-10).

Each endpoint returns plain JSON; errors return structured
`{detail, ...}` 4xx/5xx so the tester can read the failure mode at a
glance.
"""

from __future__ import annotations

import logging
import os
import uuid as _uuid
from typing import Any, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import desc, select

from waraq.api._ownership import owned_segment_or_404
from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.morphology import (
    MorphologyDataMissing,
    MorphologyNotInstalled,
    analyze_word,
)
from waraq.morphology import (
    is_available as morphology_is_available,
)
from waraq.quran import lookup_aya, lookup_translation_aya
from waraq.schemas import ProvenanceObject
from waraq.schemas.enums import POType
from waraq.shamela import find_by_skeleton, search_by_keyword

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


# ---------------------------------------------------------------------
# OCR-PO payload — see Stage-2 + Stage-3 + Stage-4/5 in one place.
# ---------------------------------------------------------------------


class OcrPoDiagnostic(BaseModel):
    satz_uuid: _uuid.UUID
    po_uuid: _uuid.UUID | None
    payload: dict[str, Any] | None


@router.get("/segments/{satz_uuid}/ocr-po", response_model=OcrPoDiagnostic)
async def get_ocr_po(
    satz_uuid: _uuid.UUID,
    session: DbSession,
    current: CurrentAccount,
) -> OcrPoDiagnostic:
    """Return the most recent OCR-PO payload for the segment.

    Useful for verifying that:
      - Stage-2 multi-engine consensus ran (`engines`, `engine_agreement`)
      - Stage-3 three-track aggregator ran (`stage3.{rules,statistical,ai}`)
      - Stage-4 homoglyph candidates surfaced (`homoglyph_suggestions[]`)
      - Stage-5 quality breakdown landed (`quality_breakdown`)
      - Confidence + class are wired (`confidence_score`, `confidence_class`)
    """
    segment = await owned_segment_or_404(session, satz_uuid, current.account_uuid)
    result = await session.execute(
        select(ProvenanceObject)
        .where(ProvenanceObject.po_type == POType.OCR.value)
        .where(ProvenanceObject.scope_uuid == segment.satz_uuid)
        .order_by(desc(ProvenanceObject.created_at))
        .limit(1)
    )
    po: ProvenanceObject | None = result.scalar_one_or_none()
    if po is None:
        return OcrPoDiagnostic(satz_uuid=segment.satz_uuid, po_uuid=None, payload=None)
    return OcrPoDiagnostic(
        satz_uuid=segment.satz_uuid,
        po_uuid=po.po_uuid,
        payload=po.payload,
    )


# ---------------------------------------------------------------------
# Tanzil-Hafs verse lookup — verifies operator step 1 ingest.
# ---------------------------------------------------------------------


class QuranVerseDiagnostic(BaseModel):
    sura: int
    aya: int
    text_arabic: str | None
    source_name: str | None
    source_version: str | None
    found: bool


@router.get("/quran/verse", response_model=QuranVerseDiagnostic)
async def get_quran_verse(
    session: DbSession,
    current: CurrentAccount,
    sura: int = Query(..., ge=1, le=114),
    aya: int = Query(..., ge=1),
) -> QuranVerseDiagnostic:
    _ = current
    verse = await lookup_aya(session, sura_index=sura, aya_index=aya)
    if verse is None:
        return QuranVerseDiagnostic(
            sura=sura,
            aya=aya,
            text_arabic=None,
            source_name=None,
            source_version=None,
            found=False,
        )
    return QuranVerseDiagnostic(
        sura=sura,
        aya=aya,
        text_arabic=verse.text_vocalized,
        source_name=verse.source_name,
        source_version=verse.source_version,
        found=True,
    )


# ---------------------------------------------------------------------
# quranenc translation lookup — verifies operator step 2 sync.
# ---------------------------------------------------------------------


class QuranTranslationDiagnostic(BaseModel):
    sura: int
    aya: int
    translation_key: str
    translation: str | None
    source_version: str | None
    found: bool


@router.get("/quran/translation", response_model=QuranTranslationDiagnostic)
async def get_quran_translation(
    session: DbSession,
    current: CurrentAccount,
    sura: int = Query(..., ge=1, le=114),
    aya: int = Query(..., ge=1),
    key: str = Query("german_rwwad"),
) -> QuranTranslationDiagnostic:
    _ = current
    # `phase="ocr"` skips any API fallback so we exercise the local
    # quranenc cache exclusively (canon §4.15.2 OCR-phase rule).
    verse = await lookup_translation_aya(
        session,
        sura_index=sura,
        aya_index=aya,
        translation_key=key,
        phase="ocr",
    )
    if verse is None or verse.text is None:
        return QuranTranslationDiagnostic(
            sura=sura,
            aya=aya,
            translation_key=key,
            translation=None,
            source_version=None,
            found=False,
        )
    return QuranTranslationDiagnostic(
        sura=sura,
        aya=aya,
        translation_key=key,
        translation=verse.text,
        # `TranslationLookupResult` doesn't carry version directly — that
        # lives on the registry/row and isn't exposed by the lookup helper.
        # Surface the source enum as a stable identifier instead.
        source_version=verse.source.value,
        found=True,
    )


# ---------------------------------------------------------------------
# Shamela search — verifies Bukhari ingest + Mode A/B.
# ---------------------------------------------------------------------


class ShamelaHitDiagnostic(BaseModel):
    text_slug: str
    title: str
    is_kutub_as_sitta: bool
    text_type: str
    section_index: int
    section_path: str
    matn_excerpt: str


class ShamelaSearchDiagnostic(BaseModel):
    mode: Literal["skeleton", "keyword"]
    query: str
    only_kutub_as_sitta: bool
    hit_count: int
    hits: list[ShamelaHitDiagnostic]


@router.get("/shamela/search", response_model=ShamelaSearchDiagnostic)
async def shamela_search(
    session: DbSession,
    current: CurrentAccount,
    query: str = Query(..., min_length=2),
    mode: Literal["skeleton", "keyword"] = Query("skeleton"),
    only_kutub_as_sitta: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
) -> ShamelaSearchDiagnostic:
    _ = current
    if mode == "skeleton":
        hits = await find_by_skeleton(
            session,
            candidate_text=query,
            only_kutub_as_sitta=only_kutub_as_sitta,
            limit=limit,
        )
    else:
        hits = await search_by_keyword(
            session,
            keyword=query,
            limit=limit,
        )
    return ShamelaSearchDiagnostic(
        mode=mode,
        query=query,
        only_kutub_as_sitta=only_kutub_as_sitta,
        hit_count=len(hits),
        hits=[
            ShamelaHitDiagnostic(
                text_slug=h.text_slug,
                title=h.title,
                is_kutub_as_sitta=h.is_kutub_as_sitta,
                text_type=h.text_type,
                section_index=h.section_index,
                section_path=h.section_path,
                matn_excerpt=(h.text_arabic[:160] + "…")
                if len(h.text_arabic) > 160
                else h.text_arabic,
            )
            for h in hits
        ],
    )


# ---------------------------------------------------------------------
# CAMeL morphology — verifies operator step 3 DB install.
# ---------------------------------------------------------------------


class MorphologyAnalysisDiagnostic(BaseModel):
    diac: str
    lex: str
    root: str
    pos: str
    gloss: str | None
    gen: str | None
    num: str | None
    per: str | None


class MorphologyDiagnostic(BaseModel):
    word: str
    available: bool
    analyses: list[MorphologyAnalysisDiagnostic]
    error: str | None = None


@router.get("/morphology/analyze", response_model=MorphologyDiagnostic)
async def morphology_analyze(
    current: CurrentAccount,
    word: str = Query(..., min_length=1),
) -> MorphologyDiagnostic:
    _ = current
    if not morphology_is_available():
        return MorphologyDiagnostic(
            word=word,
            available=False,
            analyses=[],
            error=(
                "CAMeL Tools morphology DB not installed. Run "
                "`camel_data -i morphology-db-msa-r13` to enable."
            ),
        )
    try:
        rows = analyze_word(word)
    except (MorphologyNotInstalled, MorphologyDataMissing) as exc:
        return MorphologyDiagnostic(
            word=word,
            available=False,
            analyses=[],
            error=f"{type(exc).__name__}: {exc}",
        )
    return MorphologyDiagnostic(
        word=word,
        available=True,
        analyses=[
            MorphologyAnalysisDiagnostic(
                diac=r.diac,
                lex=r.lex,
                root=r.root,
                pos=r.pos,
                gloss=r.gloss,
                gen=r.gen,
                num=r.num,
                per=r.per,
            )
            for r in rows
        ],
    )


# ---------------------------------------------------------------------
# Environment status — confirms which API keys / data are loaded.
# ---------------------------------------------------------------------


class EnvironmentDiagnostic(BaseModel):
    openai_key_present: bool
    google_ai_key_present: bool
    google_application_credentials_set: bool
    sunnah_com_api_key_present: bool
    morphology_db_available: bool


@router.get("/environment", response_model=EnvironmentDiagnostic)
async def environment_diagnostic(
    current: CurrentAccount,
) -> EnvironmentDiagnostic:
    """Verify which Phase 4 keys / installs are configured on this host.
    No secrets returned — just presence flags so the UI can show
    coloured indicators."""
    _ = current
    return EnvironmentDiagnostic(
        openai_key_present=bool(os.environ.get("OPENAI_API_KEY")),
        google_ai_key_present=bool(os.environ.get("GOOGLE_AI_API_KEY")),
        google_application_credentials_set=bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")),
        sunnah_com_api_key_present=bool(os.environ.get("SUNNAH_COM_API_KEY")),
        morphology_db_available=morphology_is_available(),
    )


__all__ = ["router"]
