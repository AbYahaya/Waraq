"""Phase 4 sub-batch A — §4.4 OCR confidence taxonomy + §3.3 preprocessing harness.

Three orthogonal layers covered:

1. `classify_confidence` boundary semantics + clamp behavior.
2. `preprocess_if_needed` gate + adapter wiring (default is no-op).
3. OCR-PO payload shape: `confidence_score`, `confidence_class`,
   `was_preprocessed`, `source_dpi` are recorded by `run_ocr_job`.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Sequence

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment
from waraq.ocr.confidence import (
    ACCEPTED_MIN,
    DEFICIENT_MIN,
    OcrConfidenceClass,
    classify_confidence,
)
from waraq.ocr.preprocessing import (
    LOW_DPI_THRESHOLD,
    preprocess_if_needed,
    should_preprocess,
)
from waraq.ocr.service import run_ocr_job, start_ocr_job
from waraq.schemas import ProvenanceObject
from waraq.schemas.enums import POType


class TestClassifyConfidence:
    """§4.4 — three classes, two thresholds. Boundary behavior matters
    (a misclassification at 0.85 is canon noncompliance)."""

    def test_well_above_accepted_min_is_accepted(self) -> None:
        assert classify_confidence(0.95) == OcrConfidenceClass.ACCEPTED

    def test_exact_accepted_min_is_accepted(self) -> None:
        # 0.85 belongs to ACCEPTED, not DEFICIENT.
        assert classify_confidence(ACCEPTED_MIN) == OcrConfidenceClass.ACCEPTED

    def test_just_below_accepted_min_is_deficient(self) -> None:
        assert classify_confidence(ACCEPTED_MIN - 0.001) == OcrConfidenceClass.DEFICIENT

    def test_exact_deficient_min_is_deficient(self) -> None:
        # 0.60 belongs to DEFICIENT, not CRITICAL.
        assert classify_confidence(DEFICIENT_MIN) == OcrConfidenceClass.DEFICIENT

    def test_just_below_deficient_min_is_critical(self) -> None:
        assert classify_confidence(DEFICIENT_MIN - 0.001) == OcrConfidenceClass.CRITICAL

    def test_zero_is_critical(self) -> None:
        assert classify_confidence(0.0) == OcrConfidenceClass.CRITICAL

    def test_one_is_accepted(self) -> None:
        assert classify_confidence(1.0) == OcrConfidenceClass.ACCEPTED

    def test_negative_clamps_to_zero(self) -> None:
        assert classify_confidence(-0.5) == OcrConfidenceClass.CRITICAL

    def test_above_one_clamps_to_one(self) -> None:
        assert classify_confidence(1.5) == OcrConfidenceClass.ACCEPTED


class TestPreprocessingGate:
    """§3.3 — should_preprocess + preprocess_if_needed."""

    def test_above_threshold_returns_false(self) -> None:
        assert should_preprocess(LOW_DPI_THRESHOLD + 1) is False

    def test_at_threshold_returns_false(self) -> None:
        # `< LOW_DPI_THRESHOLD` strict — exactly-at-threshold scans are
        # canonically not "low-DPI".
        assert should_preprocess(LOW_DPI_THRESHOLD) is False

    def test_below_threshold_returns_true(self) -> None:
        assert should_preprocess(LOW_DPI_THRESHOLD - 1) is True

    def test_zero_dpi_returns_true(self) -> None:
        # Caller passes 0 to mean "unknown" — conservative trigger.
        assert should_preprocess(0) is True


class TestPreprocessIfNeeded:
    def test_no_op_when_above_threshold(self) -> None:
        out, was_preprocessed = preprocess_if_needed(b"raw-bytes", LOW_DPI_THRESHOLD + 50)
        assert out == b"raw-bytes"
        assert was_preprocessed is False

    def test_default_no_op_below_threshold_returns_unchanged_bytes(self) -> None:
        # Default preprocessor is the identity, so even when the gate
        # fires the bytes are unchanged. The `was_preprocessed` flag
        # still flips to True so audit can tell the gate triggered.
        out, was_preprocessed = preprocess_if_needed(b"raw-bytes", 100)
        assert out == b"raw-bytes"
        assert was_preprocessed is True

    def test_custom_preprocessor_invoked_below_threshold(self) -> None:
        captured: list[int] = []

        def fake_preprocessor(b: bytes, dpi: int) -> bytes:
            captured.append(dpi)
            return b + b"::preprocessed"

        out, was_preprocessed = preprocess_if_needed(b"raw", 100, preprocessor=fake_preprocessor)
        assert out == b"raw::preprocessed"
        assert was_preprocessed is True
        assert captured == [100]

    def test_custom_preprocessor_skipped_above_threshold(self) -> None:
        called = False

        def fake_preprocessor(b: bytes, dpi: int) -> bytes:
            nonlocal called
            called = True
            return b

        out, was_preprocessed = preprocess_if_needed(
            b"raw", LOW_DPI_THRESHOLD + 50, preprocessor=fake_preprocessor
        )
        assert out == b"raw"
        assert was_preprocessed is False
        assert called is False


@pytest.mark.asyncio
class TestOcrPoPayloadShape:
    """OCR-PO payload includes the new fields after `run_ocr_job` lands."""

    async def test_payload_has_all_phase4a_fields(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        segment = await seed_segment(db_session, project=project, text="")
        # `seed_segment` returns a Segment; we need the Page for start_ocr_job.
        from waraq.schemas import Block, Page

        block_q = await db_session.execute(
            select(Block).where(Block.block_uuid == segment.block_uuid)
        )
        block = block_q.scalar_one()
        page_q = await db_session.execute(select(Page).where(Page.page_uuid == block.page_uuid))
        page = page_q.scalar_one()

        async def _stub(_image: bytes, _mime: str) -> str:
            return "بسم الله"

        job = await start_ocr_job(session=db_session, page=page)
        await run_ocr_job(
            session=db_session,
            ocr_job=job,
            image_bytes=b"",
            mime_type="image/png",
            extractor=_stub,
            target_segment=segment,
            confidence_score=0.92,
            was_preprocessed=True,
            source_dpi=150,
        )

        po_q = await db_session.execute(
            select(ProvenanceObject)
            .where(ProvenanceObject.po_type == POType.OCR.value)
            .where(ProvenanceObject.scope_uuid == segment.satz_uuid)
        )
        pos: Sequence[ProvenanceObject] = list(po_q.scalars())
        assert len(pos) == 1
        payload = pos[0].payload
        assert payload["confidence_score"] == 0.92
        assert payload["confidence_class"] == OcrConfidenceClass.ACCEPTED.value
        assert payload["was_preprocessed"] is True
        assert payload["source_dpi"] == 150

    async def test_payload_records_none_when_no_signal(self, db_session: AsyncSession) -> None:
        """When neither a caller-supplied score nor Stage-5 quality
        scoring is available, OCR-PO must record None — never a
        fake-1.0. (Sub-batch E added quality scoring as the v1.0
        signal source; this test still covers the explicit-opt-out
        path that downstream consensus callers will use.)"""
        project = await seed_project(db_session)
        segment = await seed_segment(db_session, project=project, text="")
        from waraq.schemas import Block, Page

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
            run_quality_check=False,
        )

        po_q = await db_session.execute(
            select(ProvenanceObject)
            .where(ProvenanceObject.po_type == POType.OCR.value)
            .where(ProvenanceObject.scope_uuid == segment.satz_uuid)
        )
        po = po_q.scalar_one()
        assert po.payload["confidence_score"] is None
        assert po.payload["confidence_class"] is None
        assert po.payload["was_preprocessed"] is False
        assert po.payload["source_dpi"] is None


_ = _uuid  # Silence unused import; available for ad-hoc test extensions.
