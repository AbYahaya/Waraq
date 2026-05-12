"""Phase 4 sub-batch C — §3.4 Stage-2 block-typed routing + §3.6
two-engine consensus driver.

Three orthogonal layers covered:

1. `waraq.ocr.routing` — Stage-2 routing table semantics: QURAN
   Gemini-only, others both engines, unknown class falls back to
   MAIN_TEXT routing.
2. `waraq.ocr.consensus.run_engines` — single-engine vs two-engine
   paths, agreement classification (exact / skeleton / divergent),
   confidence aggregation rules, engine-error fallback.
3. OCR-PO payload contract — the engine breakdown + agreement label
   are persisted by `run_ocr_job` when supplied.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment
from waraq.ocr.cloud_vision import CloudVisionResult
from waraq.ocr.consensus import (
    AGREEMENT_DIVERGENT,
    AGREEMENT_ENGINE_ERROR,
    AGREEMENT_EXACT_MATCH,
    AGREEMENT_SINGLE_ENGINE,
    AGREEMENT_SKELETON_EQUAL,
    EngineResult,
    run_engines,
)
from waraq.ocr.routing import OcrEngine, engines_for, primary_engine
from waraq.ocr.service import run_ocr_job, start_ocr_job
from waraq.schemas import ProvenanceObject
from waraq.schemas.enums import BlockClass, POType

# ---------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------


class TestRoutingTable:
    """Stage-2 routing: which engines are eligible for which block class."""

    def test_quran_is_gemini_only(self) -> None:
        # Cloud Vision systematically misreads Qurʾān script per
        # the §3.4 Stage-2 routing rationale.
        eligible = engines_for(BlockClass.QURAN)
        assert eligible == frozenset({OcrEngine.GEMINI})

    def test_main_text_uses_both_engines(self) -> None:
        eligible = engines_for(BlockClass.MAIN_TEXT)
        assert eligible == frozenset({OcrEngine.GEMINI, OcrEngine.CLOUD_VISION})

    def test_heading_footnote_hadith_marginalia_use_both(self) -> None:
        for cls in (
            BlockClass.HEADING,
            BlockClass.FOOTNOTE,
            BlockClass.HADITH,
            BlockClass.MARGINALIA,
        ):
            assert engines_for(cls) == frozenset({OcrEngine.GEMINI, OcrEngine.CLOUD_VISION}), cls

    def test_primary_engine_is_gemini(self) -> None:
        # §3.3 names Gemini the canonical main reading line. The
        # primary-engine pick anchors which engine's text becomes
        # the OCR-PO `text` field when both agreed.
        assert primary_engine() == OcrEngine.GEMINI

    def test_routing_table_returns_immutable_frozenset(self) -> None:
        # Defensive: callers must not be able to mutate the routing
        # table by accident.
        eligible = engines_for(BlockClass.MAIN_TEXT)
        assert isinstance(eligible, frozenset)


class TestOcrEngineEnum:
    def test_canonical_three_values(self) -> None:
        # Sub-batch kraken: KRAKEN added as the §3.3 manuscript-line
        # engine, project-flag gated (see test_kraken_adapter.py).
        assert {e.value for e in OcrEngine} == {"gemini", "cloud_vision", "kraken"}


# ---------------------------------------------------------------------
# Consensus driver
# ---------------------------------------------------------------------


def _gemini_returns(text: str):
    async def _fn(_image: bytes, _mime: str) -> str:
        return text

    return _fn


def _gemini_raises(exc: Exception):
    async def _fn(_image: bytes, _mime: str) -> str:
        raise exc

    return _fn


def _cv_returns(text: str, confidence: float | None):
    async def _fn(_image: bytes, _mime: str) -> CloudVisionResult:
        return CloudVisionResult(text=text, confidence=confidence)

    return _fn


def _cv_raises(exc: Exception):
    async def _fn(_image: bytes, _mime: str) -> CloudVisionResult:
        raise exc

    return _fn


@pytest.mark.asyncio
class TestConsensusSingleEngine:
    """QURAN routing → only Gemini runs. Cloud Vision callable is
    supplied (the API requires it) but never invoked."""

    async def test_quran_runs_gemini_only(self) -> None:
        cv_invoked = False

        async def cv_fn(_image: bytes, _mime: str) -> CloudVisionResult:
            nonlocal cv_invoked
            cv_invoked = True
            return CloudVisionResult(text="should-not-run", confidence=0.99)

        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.QURAN,
            gemini_fn=_gemini_returns("بسم الله"),
            cloud_vision_fn=cv_fn,
        )

        assert cv_invoked is False
        assert result.agreement == AGREEMENT_SINGLE_ENGINE
        assert result.primary_text == "بسم الله"
        assert result.primary_engine_used == OcrEngine.GEMINI
        assert len(result.engines) == 1
        assert result.engines[0].engine == OcrEngine.GEMINI
        # Gemini doesn't surface a confidence — None is honest.
        assert result.aggregated_confidence is None

    async def test_quran_propagates_gemini_error_as_engine_error(self) -> None:
        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.QURAN,
            gemini_fn=_gemini_raises(RuntimeError("boom")),
            cloud_vision_fn=_cv_returns("never", 0.9),
        )
        assert result.agreement == AGREEMENT_ENGINE_ERROR
        assert result.primary_text == ""
        assert len(result.engines) == 1
        assert result.engines[0].error_class == "RuntimeError"


@pytest.mark.asyncio
class TestConsensusBothEngines:
    """MAIN_TEXT / HEADING / etc. — both engines run in parallel; the
    agreement label classifies their outputs."""

    async def test_exact_match_aggregates_confidences(self) -> None:
        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=_gemini_returns("بسم الله"),
            cloud_vision_fn=_cv_returns("بسم الله", 0.92),
        )
        assert result.agreement == AGREEMENT_EXACT_MATCH
        assert result.primary_engine_used == OcrEngine.GEMINI
        assert result.primary_text == "بسم الله"
        # Mean of [0.92] (Gemini reports None and is skipped) = 0.92.
        assert result.aggregated_confidence == pytest.approx(0.92)

    async def test_exact_match_collapses_whitespace(self) -> None:
        # Engines disagreeing harmlessly on line-break placement
        # should still register as exact_match.
        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=_gemini_returns("بسم   الله\nالرحمن"),
            cloud_vision_fn=_cv_returns("بسم الله الرحمن", 0.85),
        )
        assert result.agreement == AGREEMENT_EXACT_MATCH

    async def test_skeleton_equal_when_diacritics_differ(self) -> None:
        # Same skeletal letters, different vocalization.
        # `to_skeleton` collapses both to the same key.
        gemini_text = "بِسْمِ اللَّهِ"  # fully vocalized
        cv_text = "بسم الله"  # bare
        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=_gemini_returns(gemini_text),
            cloud_vision_fn=_cv_returns(cv_text, 0.80),
        )
        assert result.agreement == AGREEMENT_SKELETON_EQUAL

    async def test_divergent_picks_lower_confidence(self) -> None:
        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=_gemini_returns("بسم الله الرحمن"),
            cloud_vision_fn=_cv_returns("سمع غير لذلك", 0.75),
        )
        assert result.agreement == AGREEMENT_DIVERGENT
        # Only Cloud Vision reported a confidence — that single value
        # is the aggregate (the divergent rule's `min` over a single
        # value is itself).
        assert result.aggregated_confidence == pytest.approx(0.75)

    async def test_primary_text_from_gemini_when_both_succeed(self) -> None:
        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=_gemini_returns("gemini-text"),
            cloud_vision_fn=_cv_returns("cv-text", 0.5),
        )
        # §3.3 Gemini is canonical primary even when the texts diverge.
        assert result.primary_engine_used == OcrEngine.GEMINI
        assert result.primary_text == "gemini-text"

    async def test_primary_falls_back_to_cv_when_gemini_errors(self) -> None:
        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=_gemini_raises(RuntimeError("rate-limit")),
            cloud_vision_fn=_cv_returns("survivor", 0.8),
        )
        assert result.agreement == AGREEMENT_ENGINE_ERROR
        assert result.primary_engine_used == OcrEngine.CLOUD_VISION
        assert result.primary_text == "survivor"
        # Aggregator returns the surviving engine's confidence.
        assert result.aggregated_confidence == pytest.approx(0.8)

    async def test_both_engines_fail_returns_empty_text(self) -> None:
        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=_gemini_raises(RuntimeError("g")),
            cloud_vision_fn=_cv_raises(RuntimeError("v")),
        )
        assert result.agreement == AGREEMENT_ENGINE_ERROR
        assert result.primary_text == ""
        assert result.aggregated_confidence is None
        assert all(r.error_class is not None for r in result.engines)


# ---------------------------------------------------------------------
# OCR-PO payload — engines + engine_agreement persisted by run_ocr_job
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestOcrPoEnginesPayload:
    async def test_engines_and_agreement_persisted_when_supplied(
        self, db_session: AsyncSession
    ) -> None:
        from waraq.schemas import Block, Page

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
            EngineResult(engine=OcrEngine.GEMINI, text="بسم الله", confidence=None),
            EngineResult(engine=OcrEngine.CLOUD_VISION, text="بسم الله", confidence=0.92),
        ]

        job = await start_ocr_job(session=db_session, page=page)
        await run_ocr_job(
            session=db_session,
            ocr_job=job,
            image_bytes=b"",
            mime_type="image/png",
            extractor=_stub,
            target_segment=segment,
            engine_breakdown=engine_breakdown,
            engine_agreement=AGREEMENT_EXACT_MATCH,
        )

        po_q = await db_session.execute(
            select(ProvenanceObject)
            .where(ProvenanceObject.po_type == POType.OCR.value)
            .where(ProvenanceObject.scope_uuid == segment.satz_uuid)
        )
        pos: Sequence[ProvenanceObject] = list(po_q.scalars())
        assert len(pos) == 1
        payload = pos[0].payload
        assert payload["engine_agreement"] == AGREEMENT_EXACT_MATCH
        engines_payload = payload["engines"]
        assert engines_payload is not None
        assert len(engines_payload) == 2
        assert {e["engine"] for e in engines_payload} == {"gemini", "cloud_vision"}
        cv_entry = next(e for e in engines_payload if e["engine"] == "cloud_vision")
        assert cv_entry["confidence"] == pytest.approx(0.92)
        assert cv_entry["text_chars"] == len("بسم الله")
        assert cv_entry["error_class"] is None

    async def test_engines_none_for_legacy_callers(self, db_session: AsyncSession) -> None:
        """Pre-sub-batch-C callers (no engine_breakdown supplied) still
        get a None entry on the OCR-PO so the payload contract is
        stable."""
        from waraq.schemas import Block, Page

        project = await seed_project(db_session)
        segment = await seed_segment(db_session, project=project, text="")

        block_q = await db_session.execute(
            select(Block).where(Block.block_uuid == segment.block_uuid)
        )
        block = block_q.scalar_one()
        page_q = await db_session.execute(select(Page).where(Page.page_uuid == block.page_uuid))
        page = page_q.scalar_one()

        async def _stub(_image: bytes, _mime: str) -> str:
            return "x"

        job = await start_ocr_job(session=db_session, page=page)
        await run_ocr_job(
            session=db_session,
            ocr_job=job,
            image_bytes=b"",
            mime_type="image/png",
            extractor=_stub,
            target_segment=segment,
        )
        po_q = await db_session.execute(
            select(ProvenanceObject)
            .where(ProvenanceObject.po_type == POType.OCR.value)
            .where(ProvenanceObject.scope_uuid == segment.satz_uuid)
        )
        po = po_q.scalar_one()
        assert po.payload["engines"] is None
        assert po.payload["engine_agreement"] is None
