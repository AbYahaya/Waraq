"""Morphology endpoints — Arabic click-word → analysis (CAMeL Tools).

- `GET  /morphology/availability` — probe: does the server have CAMeL?
- `POST /morphology/analyze`      — return analyses for a word.

CAMeL Tools is an optional install. When the package is absent (or its
morphology database isn't downloaded) both endpoints return a clear
diagnostic instead of crashing — `availability` returns `available:
false`, `analyze` returns 503 with a configuration message.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from waraq.api.dependencies import CurrentAccount
from waraq.morphology import (
    MorphologicalAnalysis,
    MorphologyDataMissing,
    MorphologyNotInstalled,
    analyze_word,
    is_available,
)

router = APIRouter(prefix="/morphology", tags=["morphology"])


class MorphologyAnalyzeRequest(BaseModel):
    word: str = Field(min_length=1, max_length=128)


class MorphologyAnalysisOut(BaseModel):
    diac: str
    lex: str
    root: str
    pos: str
    gloss: str | None
    gen: str | None
    num: str | None
    per: str | None


class MorphologyAnalyzeResponse(BaseModel):
    word: str
    analyses: list[MorphologyAnalysisOut]


class MorphologyAvailabilityResponse(BaseModel):
    available: bool
    reason: str | None = None


@router.get("/availability", response_model=MorphologyAvailabilityResponse)
async def availability(current: CurrentAccount) -> MorphologyAvailabilityResponse:
    _ = current
    if is_available():
        return MorphologyAvailabilityResponse(available=True, reason=None)
    return MorphologyAvailabilityResponse(
        available=False,
        reason=(
            "CAMeL Tools is not installed or the morphology DB is missing. "
            "Install with `pip install camel-tools` and download the DB "
            "via `camel_data -i morphology-db-msa-r13`."
        ),
    )


@router.post("/analyze", response_model=MorphologyAnalyzeResponse)
async def analyze(
    req: MorphologyAnalyzeRequest, current: CurrentAccount
) -> MorphologyAnalyzeResponse:
    _ = current
    try:
        analyses = analyze_word(req.word)
    except (MorphologyNotInstalled, MorphologyDataMissing) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    def _to_out(a: MorphologicalAnalysis) -> MorphologyAnalysisOut:
        return MorphologyAnalysisOut(
            diac=a.diac,
            lex=a.lex,
            root=a.root,
            pos=a.pos,
            gloss=a.gloss,
            gen=a.gen,
            num=a.num,
            per=a.per,
        )

    return MorphologyAnalyzeResponse(word=req.word, analyses=[_to_out(a) for a in analyses])
