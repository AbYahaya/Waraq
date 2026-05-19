"""Phase 4 sub-batch D — Stage-3 three-track aggregator + OCR-PO
payload integration."""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment
from waraq.ocr.openai_ocr import OpenAiOcrResult
from waraq.ocr.consensus import (
    AGREEMENT_DIVERGENT,
    AGREEMENT_EXACT_MATCH,
    AGREEMENT_SINGLE_ENGINE,
    EngineResult,
    run_engines,
)
from waraq.ocr.routing import OcrEngine
from waraq.ocr.stage3 import (
    DIVERGENCE_COLLAPSE,
    W_AI,
    W_RULES,
    W_STAGE2,
    W_STATISTICAL,
    Stage3Result,
    aggregate_stage3,
)
from waraq.ocr.stage3_ai import AiEngineVerdict
from waraq.schemas.enums import BlockClass


def _gemini_returns(text: str):
    async def _fn(_image: bytes, _mime: str) -> str:
        return text

    return _fn


def _cv_returns(text: str, confidence: float | None):
    async def _fn(_image: bytes, _mime: str) -> OpenAiOcrResult:
        return OpenAiOcrResult(text=text, confidence=confidence)

    return _fn


def _morph_all(words: set[str]):
    def _fn(word: str) -> bool:
        return word in words

    return _fn


def _diac_zero(text: str) -> str:
    return text


def _ai_verdict(confidence: float):
    async def _fn(_text: str, _ctx: dict[str, str]) -> AiEngineVerdict:
        return AiEngineVerdict(engine="stub", confidence=confidence)

    return _fn


class TestWeightsSum:
    def test_track_weights_sum_to_one(self) -> None:
        # Phase 7 gold-corpus recalibration target — guard the
        # invariant.
        total = W_STAGE2 + W_RULES + W_STATISTICAL + W_AI
        assert abs(total - 1.0) < 1e-9


@pytest.mark.asyncio
class TestAggregateStage3:
    async def test_all_tracks_high_yields_high_confidence(self, db_session: AsyncSession) -> None:
        # Stage-2 exact_match → 1.0 contribution.
        consensus = await run_engines(
            image_bytes=b"x",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=_gemini_returns("بسم الله"),
            openai_ocr_fn=_cv_returns("بسم الله", 0.92),
        )
        assert consensus.agreement == AGREEMENT_EXACT_MATCH

        result = await aggregate_stage3(
            session=db_session,
            candidate_text="بسم الله",
            block_class=BlockClass.MAIN_TEXT,
            stage2=consensus,
            morphology_fn=_morph_all({"بسم", "الله"}),
            diacritizer_fn=_diac_zero,
            openai_validator=_ai_verdict(0.95),
            gemini_validator=_ai_verdict(0.95),
        )
        assert isinstance(result, Stage3Result)
        # Stage2 1.0 + rules ≥ 0.6 + stat 0.5 (no Shamela seeded) +
        # AI 0.95 — all in the high band.
        assert result.confidence > 0.7
        assert result.divergence_penalty_applied is False

    async def test_divergent_with_low_track_triggers_collapse(
        self, db_session: AsyncSession
    ) -> None:
        consensus = await run_engines(
            image_bytes=b"x",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=_gemini_returns("بسم الله الرحمن"),
            openai_ocr_fn=_cv_returns("سمع غير لذلك", 0.5),
        )
        assert consensus.agreement == AGREEMENT_DIVERGENT

        # AI returns very low confidence — triggers the divergence
        # collapse on top of the divergent Stage-2.
        result = await aggregate_stage3(
            session=db_session,
            candidate_text="بسم الله الرحمن",
            block_class=BlockClass.MAIN_TEXT,
            stage2=consensus,
            morphology_fn=_morph_all(set()),
            diacritizer_fn=_diac_zero,
            openai_validator=_ai_verdict(0.20),
            gemini_validator=_ai_verdict(0.20),
        )
        assert result.divergence_penalty_applied is True
        # The collapsed score must be lower than what the same inputs
        # would produce without the penalty (just a sanity bound).
        assert (
            result.confidence
            <= (W_STAGE2 * 0.40 + W_RULES * 0.50 + W_STATISTICAL * 0.50 + W_AI * 0.20)
            * DIVERGENCE_COLLAPSE
            + 1e-9
        )

    async def test_divergent_without_low_track_no_collapse(self, db_session: AsyncSession) -> None:
        # Stage-2 divergent, but rules + AI are both ≥ 0.5 → no
        # collapse fires.
        consensus = await run_engines(
            image_bytes=b"x",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=_gemini_returns("بسم الله الرحمن"),
            openai_ocr_fn=_cv_returns("سمع غير لذلك", 0.85),
        )
        assert consensus.agreement == AGREEMENT_DIVERGENT
        result = await aggregate_stage3(
            session=db_session,
            candidate_text="بسم الله الرحمن",
            block_class=BlockClass.MAIN_TEXT,
            stage2=consensus,
            morphology_fn=_morph_all({"بسم", "الله", "الرحمن"}),
            diacritizer_fn=_diac_zero,
            openai_validator=_ai_verdict(0.85),
            gemini_validator=_ai_verdict(0.85),
        )
        assert result.divergence_penalty_applied is False

    async def test_quran_single_engine_path(self, db_session: AsyncSession) -> None:
        consensus = await run_engines(
            image_bytes=b"x",
            mime_type="image/png",
            block_class=BlockClass.QURAN,
            gemini_fn=_gemini_returns("بسم الله"),
            openai_ocr_fn=_cv_returns("never-runs", 0.99),
        )
        assert consensus.agreement == AGREEMENT_SINGLE_ENGINE

        result = await aggregate_stage3(
            session=db_session,
            candidate_text="بسم الله",
            block_class=BlockClass.QURAN,
            stage2=consensus,
            morphology_fn=_morph_all({"بسم", "الله"}),
            diacritizer_fn=_diac_zero,
            openai_validator=_ai_verdict(0.85),
            gemini_validator=_ai_verdict(0.85),
        )
        # Stage-2 single_engine → 0.65 contribution; everything else
        # is high → final lands above neutral but below all-agreement.
        assert 0.50 < result.confidence < 0.95
        assert result.stage2_score == 0.65


@pytest.mark.asyncio
class TestPageRunnerStage3Wiring:
    """End-to-end: `run_ocr_for_page` calls aggregate_stage3 and the
    resulting payload lands on the OCR-PO."""

    async def test_stage3_payload_persisted_on_ocr_po(self, db_session: AsyncSession) -> None:
        """Run the same flow as `run_ocr_job` directly with a Stage-3
        payload — easier to assert in isolation than going through
        the rasterize-and-render path."""
        from waraq.ocr.consensus import EngineResult as _EngineResult
        from waraq.ocr.service import run_ocr_job, start_ocr_job
        from waraq.schemas import Block, Page, ProvenanceObject
        from waraq.schemas.enums import POType

        project = await seed_project(db_session)
        segment = await seed_segment(db_session, project=project, text="")

        block_q = await db_session.execute(
            select(Block).where(Block.block_uuid == segment.block_uuid)
        )
        block = block_q.scalar_one()
        page_q = await db_session.execute(select(Page).where(Page.page_uuid == block.page_uuid))
        page = page_q.scalar_one()

        async def _stub(_image: bytes, _mime: str) -> str:
            return "بسم الله"

        engine_breakdown = [
            _EngineResult(engine=OcrEngine.GEMINI, text="بسم الله", confidence=None),
            _EngineResult(engine=OcrEngine.OPENAI, text="بسم الله", confidence=0.92),
        ]
        stage3_payload = {
            "confidence": 0.91,
            "stage2_score": 1.0,
            "divergence_penalty_applied": False,
            "rules": {
                "score": 0.85,
                "morphology_score": 1.0,
                "morphology_available": True,
                "diacritization_score": 0.6,
                "diacritization_available": True,
                "word_count": 2,
            },
            "statistical": {
                "score": 0.85,
                "hit_count": 3,
                "scoped_to_kutub_as_sitta": False,
                "sample_titles": ["Sahih al-Bukhari"],
            },
            "ai": {
                "score": 0.92,
                "agreement": "agree",
                "verdicts": [
                    {
                        "engine": "openai/gpt-4o",
                        "confidence": 0.92,
                        "correction_note": None,
                        "error_class": None,
                    },
                    {
                        "engine": "google/gemini-2.5-pro",
                        "confidence": 0.92,
                        "correction_note": None,
                        "error_class": None,
                    },
                ],
            },
        }

        job = await start_ocr_job(session=db_session, page=page)
        await run_ocr_job(
            session=db_session,
            ocr_job=job,
            image_bytes=b"",
            mime_type="image/png",
            extractor=_stub,
            target_segment=segment,
            confidence_score=0.91,
            engine_breakdown=engine_breakdown,
            engine_agreement=AGREEMENT_EXACT_MATCH,
            stage3_payload=stage3_payload,
        )

        po_q = await db_session.execute(
            select(ProvenanceObject)
            .where(ProvenanceObject.po_type == POType.OCR.value)
            .where(ProvenanceObject.scope_uuid == segment.satz_uuid)
        )
        pos: Sequence[ProvenanceObject] = list(po_q.scalars())
        assert len(pos) == 1
        payload = pos[0].payload
        assert payload["stage3"] is not None
        assert payload["stage3"]["confidence"] == pytest.approx(0.91)
        assert payload["stage3"]["rules"]["morphology_available"] is True
        assert payload["stage3"]["statistical"]["hit_count"] == 3
        assert payload["stage3"]["ai"]["agreement"] == "agree"
        # Reference unused imports for ruff; they're imported above for
        # completeness but the test asserts via payload only.
        _ = (EngineResult, run_engines)
