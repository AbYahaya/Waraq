"""Sub-batch N — project audit dashboard service tests.

Covers:
- `summarize_project` distributions across OCR-PO confidence,
  engine_agreement, cross-check, page ocr_status, open Befunde.
- `list_attention_segments` per-filter semantics.
- Empty project = zero counts everywhere, empty attention list.
- Per-project scoping (no leakage from other projects).
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment
from waraq.audit_dashboard import (
    AttentionFilter,
    list_attention_segments,
    segment_audit_detail,
    summarize_project,
)
from waraq.identity import new_uuid
from waraq.provenance import create_po
from waraq.schemas import Befund, Job
from waraq.schemas.enums import JobState, POType, ScopeType


async def _seed_audit_job(session: AsyncSession) -> Job:
    """Create an audit-type Job so a Befund's FK constraint passes."""
    job = Job(job_uuid=new_uuid(), job_type="audit", state=JobState.PENDING.value)
    session.add(job)
    await session.flush()
    return job

# ---------------------------------------------------------------------
# summarize_project
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestSummarizeProject:
    async def test_empty_project_zero_counts(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        summary = await summarize_project(
            session=db_session, project_uuid=project.project_uuid
        )
        assert summary.total_pages == 0
        assert summary.total_segments == 0
        # All distribution buckets default to 0.
        assert summary.ocr_confidence.accepted == 0
        assert summary.ocr_confidence.no_ocr == 0
        assert summary.cross_check.not_translated == 0
        assert summary.open_befunde.kritisch == 0
        assert summary.open_konsistenz_befunde == 0
        assert summary.open_conflicts == 0

    async def test_segments_without_ocr_po_count_as_no_ocr(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        seg1 = await seed_segment(db_session, project=project, text="a", page_index=1)
        seg2 = await seed_segment(db_session, project=project, text="b", page_index=2)
        summary = await summarize_project(
            session=db_session, project_uuid=project.project_uuid
        )
        assert summary.total_segments == 2
        assert summary.ocr_confidence.no_ocr == 2
        assert summary.ocr_confidence.accepted == 0
        _ = seg1, seg2

    async def test_confidence_class_distribution(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        seg_a = await seed_segment(db_session, project=project, text="a", page_index=1)
        seg_b = await seed_segment(db_session, project=project, text="b", page_index=2)
        seg_c = await seed_segment(db_session, project=project, text="c", page_index=3)
        # Each segment gets one OCR-PO with a different confidence class.
        for seg, klass in [
            (seg_a, "accepted"),
            (seg_b, "deficient"),
            (seg_c, "critical"),
        ]:
            await create_po(
                session=db_session,
                po_type=POType.OCR,
                scope_type=ScopeType.SEGMENT,
                scope_uuid=seg.satz_uuid,
                payload={"confidence_class": klass, "confidence_score": 0.5},
            )
        summary = await summarize_project(
            session=db_session, project_uuid=project.project_uuid
        )
        assert summary.ocr_confidence.accepted == 1
        assert summary.ocr_confidence.deficient == 1
        assert summary.ocr_confidence.critical == 1
        assert summary.ocr_confidence.no_ocr == 0

    async def test_engine_agreement_distribution(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        a = await seed_segment(db_session, project=project, text="a", page_index=1)
        b = await seed_segment(db_session, project=project, text="b", page_index=2)
        for seg, agreement in [(a, "exact_match"), (b, "divergent")]:
            await create_po(
                session=db_session,
                po_type=POType.OCR,
                scope_type=ScopeType.SEGMENT,
                scope_uuid=seg.satz_uuid,
                payload={"engine_agreement": agreement},
            )
        summary = await summarize_project(
            session=db_session, project_uuid=project.project_uuid
        )
        assert summary.engine_agreement.exact_match == 1
        assert summary.engine_agreement.divergent == 1

    async def test_cross_check_distribution(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        a = await seed_segment(db_session, project=project, text="a", page_index=1)
        b = await seed_segment(db_session, project=project, text="b", page_index=2)
        for seg, situation in [
            (a, "agreement"),
            (b, "substantive_deviation"),
        ]:
            await create_po(
                session=db_session,
                po_type=POType.TRANSLATION,
                scope_type=ScopeType.SEGMENT,
                scope_uuid=seg.satz_uuid,
                payload={"cross_check": {"situation": situation}},
            )
        summary = await summarize_project(
            session=db_session, project_uuid=project.project_uuid
        )
        assert summary.cross_check.agreement == 1
        assert summary.cross_check.substantive_deviation == 1
        assert summary.cross_check.not_translated == 0

    async def test_open_befunde_distribution(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x", page_index=1)
        job = await _seed_audit_job(db_session)
        befund = Befund(
            befund_uuid=new_uuid(),
            satz_uuid=seg.satz_uuid,
            project_uuid=project.project_uuid,
            audit_run_job_uuid=job.job_uuid,
            regelkennung="C-01",
            verstossklasse="blockierend",
            schweregrad="kritisch",
            detection_context={},
        )
        db_session.add(befund)
        await db_session.flush()
        summary = await summarize_project(
            session=db_session, project_uuid=project.project_uuid
        )
        assert summary.open_befunde.kritisch == 1
        assert summary.open_befunde.hoch == 0

    async def test_per_project_scope_no_leakage(self, db_session: AsyncSession) -> None:
        project_a = await seed_project(db_session)
        project_b = await seed_project(db_session)
        # Seed activity in project_a only.
        await seed_segment(db_session, project=project_a, text="a", page_index=1)
        summary_b = await summarize_project(
            session=db_session, project_uuid=project_b.project_uuid
        )
        assert summary_b.total_segments == 0
        assert summary_b.total_pages == 0


# ---------------------------------------------------------------------
# list_attention_segments
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestAttentionList:
    async def test_empty_project_empty_list(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        items = await list_attention_segments(
            session=db_session, project_uuid=project.project_uuid
        )
        assert items == []

    async def test_low_confidence_filter(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        accepted = await seed_segment(
            db_session, project=project, text="a", page_index=1
        )
        deficient = await seed_segment(
            db_session, project=project, text="b", page_index=2
        )
        critical = await seed_segment(
            db_session, project=project, text="c", page_index=3
        )
        for seg, klass in [
            (accepted, "accepted"),
            (deficient, "deficient"),
            (critical, "critical"),
        ]:
            await create_po(
                session=db_session,
                po_type=POType.OCR,
                scope_type=ScopeType.SEGMENT,
                scope_uuid=seg.satz_uuid,
                payload={"confidence_class": klass, "confidence_score": 0.4},
            )
        items = await list_attention_segments(
            session=db_session,
            project_uuid=project.project_uuid,
            filters=[AttentionFilter.LOW_CONFIDENCE],
        )
        # Accepted is NOT surfaced; deficient + critical are.
        surfaced = {it.satz_uuid for it in items}
        assert deficient.satz_uuid in surfaced
        assert critical.satz_uuid in surfaced
        assert accepted.satz_uuid not in surfaced
        for it in items:
            assert it.filter_matched == AttentionFilter.LOW_CONFIDENCE
            assert it.detail["confidence_class"] in ("deficient", "critical")

    async def test_divergent_ocr_filter(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        agree = await seed_segment(
            db_session, project=project, text="a", page_index=1
        )
        diverge = await seed_segment(
            db_session, project=project, text="b", page_index=2
        )
        await create_po(
            session=db_session,
            po_type=POType.OCR,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=agree.satz_uuid,
            payload={"engine_agreement": "exact_match"},
        )
        await create_po(
            session=db_session,
            po_type=POType.OCR,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=diverge.satz_uuid,
            payload={"engine_agreement": "divergent"},
        )
        items = await list_attention_segments(
            session=db_session,
            project_uuid=project.project_uuid,
            filters=[AttentionFilter.DIVERGENT_OCR],
        )
        assert len(items) == 1
        assert items[0].satz_uuid == diverge.satz_uuid

    async def test_cross_check_substantive_filter(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        agree = await seed_segment(
            db_session, project=project, text="a", page_index=1
        )
        flagged = await seed_segment(
            db_session, project=project, text="b", page_index=2
        )
        for seg, situation in [
            (agree, "agreement"),
            (flagged, "substantive_deviation"),
        ]:
            await create_po(
                session=db_session,
                po_type=POType.TRANSLATION,
                scope_type=ScopeType.SEGMENT,
                scope_uuid=seg.satz_uuid,
                payload={"cross_check": {"situation": situation}},
            )
        items = await list_attention_segments(
            session=db_session,
            project_uuid=project.project_uuid,
            filters=[AttentionFilter.CROSS_CHECK_SUBSTANTIVE],
        )
        assert len(items) == 1
        assert items[0].satz_uuid == flagged.satz_uuid
        assert items[0].detail["situation"] == "substantive_deviation"

    async def test_open_audit_finding_filter(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="x", page_index=1)
        job = await _seed_audit_job(db_session)
        befund = Befund(
            befund_uuid=new_uuid(),
            satz_uuid=seg.satz_uuid,
            project_uuid=project.project_uuid,
            audit_run_job_uuid=job.job_uuid,
            regelkennung="A-02",
            verstossklasse="pflichthinweis",
            schweregrad="hoch",
            detection_context={"sample": "x"},
        )
        db_session.add(befund)
        await db_session.flush()
        items = await list_attention_segments(
            session=db_session,
            project_uuid=project.project_uuid,
            filters=[AttentionFilter.OPEN_AUDIT_FINDING],
        )
        assert len(items) == 1
        assert items[0].satz_uuid == seg.satz_uuid
        assert items[0].detail["regelkennung"] == "A-02"
        assert items[0].detail["schweregrad"] == "hoch"

    async def test_no_filters_returns_union_of_all_filters(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        critical_seg = await seed_segment(
            db_session, project=project, text="a", page_index=1
        )
        divergent_seg = await seed_segment(
            db_session, project=project, text="b", page_index=2
        )
        # Critical confidence on seg_a; divergent on seg_b.
        await create_po(
            session=db_session,
            po_type=POType.OCR,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=critical_seg.satz_uuid,
            payload={"confidence_class": "critical"},
        )
        await create_po(
            session=db_session,
            po_type=POType.OCR,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=divergent_seg.satz_uuid,
            payload={"engine_agreement": "divergent"},
        )
        items = await list_attention_segments(
            session=db_session,
            project_uuid=project.project_uuid,
            filters=None,
        )
        surfaced = {it.satz_uuid for it in items}
        assert critical_seg.satz_uuid in surfaced
        assert divergent_seg.satz_uuid in surfaced

    async def test_limit_caps_results(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        for i in range(5):
            seg = await seed_segment(
                db_session, project=project, text=str(i), page_index=i + 1
            )
            await create_po(
                session=db_session,
                po_type=POType.OCR,
                scope_type=ScopeType.SEGMENT,
                scope_uuid=seg.satz_uuid,
                payload={"confidence_class": "critical"},
            )
        items = await list_attention_segments(
            session=db_session,
            project_uuid=project.project_uuid,
            filters=[AttentionFilter.LOW_CONFIDENCE],
            limit=3,
        )
        assert len(items) == 3


# ---------------------------------------------------------------------
# N-2 — block_index in AttentionItem + segment_audit_detail
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestAttentionItemBlockIndex:
    async def test_block_index_populated_from_block_row(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        # Seed two segments on different pages so we see distinct
        # block_index values when the seed helper writes them.
        seg_a = await seed_segment(
            db_session,
            project=project,
            text="a",
            page_index=1,
            block_index=0,
        )
        seg_b = await seed_segment(
            db_session,
            project=project,
            text="b",
            page_index=2,
            block_index=7,  # non-zero so we can verify it's surfaced
        )
        for seg in (seg_a, seg_b):
            await create_po(
                session=db_session,
                po_type=POType.OCR,
                scope_type=ScopeType.SEGMENT,
                scope_uuid=seg.satz_uuid,
                payload={"confidence_class": "critical"},
            )
        items = await list_attention_segments(
            session=db_session,
            project_uuid=project.project_uuid,
            filters=[AttentionFilter.LOW_CONFIDENCE],
        )
        by_uuid = {it.satz_uuid: it for it in items}
        assert by_uuid[seg_a.satz_uuid].block_index == 0
        assert by_uuid[seg_b.satz_uuid].block_index == 7


@pytest.mark.asyncio
class TestSegmentAuditDetail:
    async def test_returns_none_for_segment_outside_project(
        self, db_session: AsyncSession
    ) -> None:
        project_a = await seed_project(db_session)
        project_b = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project_a, text="a", page_index=1)
        # Looking up seg under project_b → None (no cross-project leak).
        detail = await segment_audit_detail(
            session=db_session,
            project_uuid=project_b.project_uuid,
            satz_uuid=seg.satz_uuid,
        )
        assert detail is None

    async def test_returns_engine_readings_with_text_when_persisted(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="a", page_index=1)
        # Persist an OCR-PO with full engine text (N-2 forward-only).
        await create_po(
            session=db_session,
            po_type=POType.OCR,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
            payload={
                "engine_agreement": "divergent",
                "confidence_class": "deficient",
                "confidence_score": 0.62,
                "engines": [
                    {
                        "engine": "gemini",
                        "text": "بسم الله",
                        "text_chars": 8,
                        "confidence": None,
                        "error_class": None,
                    },
                    {
                        "engine": "cloud_vision",
                        "text": "سمع غير",
                        "text_chars": 7,
                        "confidence": 0.55,
                        "error_class": None,
                    },
                ],
            },
        )
        detail = await segment_audit_detail(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
        )
        assert detail is not None
        assert detail.ocr_engine_agreement == "divergent"
        assert detail.ocr_confidence_class == "deficient"
        assert detail.ocr_confidence_score == pytest.approx(0.62)
        assert detail.ocr_engines_have_text is True
        assert len(detail.ocr_engines) == 2
        gem = next(e for e in detail.ocr_engines if e.engine == "gemini")
        cv = next(e for e in detail.ocr_engines if e.engine == "cloud_vision")
        assert gem.text == "بسم الله"
        assert cv.text == "سمع غير"

    async def test_legacy_ocr_po_without_per_engine_text(
        self, db_session: AsyncSession
    ) -> None:
        # Simulate a pre-N-2 OCR-PO that only has `text_chars`, no `text`.
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="a", page_index=1)
        await create_po(
            session=db_session,
            po_type=POType.OCR,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
            payload={
                "engines": [
                    {
                        "engine": "gemini",
                        "text_chars": 5,
                        "confidence": None,
                        "error_class": None,
                    }
                ],
                "engine_agreement": "single_engine",
            },
        )
        detail = await segment_audit_detail(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
        )
        assert detail is not None
        # Engine row surfaced with text=None and text_chars correct.
        assert detail.ocr_engines_have_text is False
        assert len(detail.ocr_engines) == 1
        assert detail.ocr_engines[0].text is None
        assert detail.ocr_engines[0].text_chars == 5

    async def test_includes_translation_situation(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="a", page_index=1)
        await create_po(
            session=db_session,
            po_type=POType.TRANSLATION,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
            payload={
                "cross_check": {"situation": "substantive_deviation"},
                "translation_text": "Im Namen Gottes",
            },
        )
        detail = await segment_audit_detail(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
        )
        assert detail is not None
        assert detail.translation_situation == "substantive_deviation"
        assert detail.translation_target_text == "Im Namen Gottes"

    async def test_includes_open_befunde(
        self, db_session: AsyncSession
    ) -> None:
        project = await seed_project(db_session)
        seg = await seed_segment(db_session, project=project, text="a", page_index=1)
        job = await _seed_audit_job(db_session)
        b = Befund(
            befund_uuid=new_uuid(),
            satz_uuid=seg.satz_uuid,
            project_uuid=project.project_uuid,
            audit_run_job_uuid=job.job_uuid,
            regelkennung="C-01",
            verstossklasse="blockierend",
            schweregrad="kritisch",
            detection_context={"match": "glossary_lookup"},
        )
        db_session.add(b)
        await db_session.flush()
        detail = await segment_audit_detail(
            session=db_session,
            project_uuid=project.project_uuid,
            satz_uuid=seg.satz_uuid,
        )
        assert detail is not None
        assert len(detail.open_befunde) == 1
        assert detail.open_befunde[0].regelkennung == "C-01"
        assert detail.open_befunde[0].schweregrad == "kritisch"
        assert detail.open_befunde[0].detection_context == {"match": "glossary_lookup"}
