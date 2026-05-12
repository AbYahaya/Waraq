"""Phase 4 sub-batch E — §3.4 Stage-4 homoglyph + Stage-5 quality.

Three layers covered:

1. Pure Stage-5 check functions (completeness, symmetry, char-count,
   known-passage neutral) — boundary semantics + clamp behavior.
2. `compute_quality_score` aggregator — weighted average correctness,
   override on `known_passage` argument, no-expected-chars handling.
3. Stage-4 homoglyph harness — taxonomy invariants + default no-op +
   custom adapter wiring.
4. OCR-PO payload integration — `quality_breakdown` + `homoglyph_*`
   fields land via `run_ocr_job` and confidence is derived from quality.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment
from waraq.ocr.confidence import OcrConfidenceClass
from waraq.ocr.homoglyph import (
    ALTERNATES,
    HOMOGLYPH_PAIRS,
    HomoglyphSuggestion,
    find_homoglyph_candidates,
    is_homoglyph_candidate,
    separate_syllables,
)
from waraq.ocr.quality import (
    KnownPassageSignal,
    check_char_count,
    check_completeness,
    check_known_passage_neutral,
    check_structural_symmetry,
    compute_quality_score,
)
from waraq.ocr.service import run_ocr_job, start_ocr_job
from waraq.schemas import ProvenanceObject
from waraq.schemas.enums import POType

# -----------------------------------------------------------------------
# Stage-5 — pure checks
# -----------------------------------------------------------------------


class TestCompletenessCheck:
    def test_clean_arabic_period_is_full_score(self) -> None:
        sig = check_completeness("هذا نص كامل.")
        assert sig.score == 1.0
        assert sig.ends_with == "."

    def test_arabic_question_mark_is_full_score(self) -> None:
        sig = check_completeness("أين الكتاب؟")
        assert sig.score == 1.0
        assert sig.ends_with == "؟"

    def test_mid_word_truncation_is_zero(self) -> None:
        # Last char is a letter, not punctuation.
        sig = check_completeness("هذا نص مقطو")
        assert sig.score == 0.0

    def test_empty_text_is_zero(self) -> None:
        sig = check_completeness("")
        assert sig.score == 0.0
        assert sig.ends_with is None

    def test_closing_bracket_is_neutral(self) -> None:
        # Ending with `)` isn't sentence-end but isn't mid-word either.
        sig = check_completeness("متن (متخصصة)")
        assert sig.score == 0.5


class TestStructuralSymmetry:
    def test_balanced_parens_is_full_score(self) -> None:
        sig = check_structural_symmetry("text (one) and (two) [three]")
        assert sig.score == 1.0
        assert sig.imbalanced == []

    def test_unbalanced_parens_drops_score(self) -> None:
        sig = check_structural_symmetry("text (one and (two without close")
        assert sig.score < 1.0
        assert ("(", ")", 2, 0) in sig.imbalanced

    def test_arabic_quran_brackets(self) -> None:
        # Balanced: ﴾ ﴿
        sig = check_structural_symmetry("قال ﴾إنا أنزلناه﴿ في ليلة")
        assert sig.score == 1.0

    def test_unbalanced_quran_brackets(self) -> None:
        sig = check_structural_symmetry("قال ﴾إنا أنزلناه")  # missing close
        assert ("﴾", "﴿", 1, 0) in sig.imbalanced


class TestCharCount:
    def test_in_band_is_full_score(self) -> None:
        sig = check_char_count(actual_chars=1000, expected_chars=1000)
        assert sig.score == 1.0

    def test_at_lower_band_edge(self) -> None:
        # ratio = 0.85 — exactly the in-band lower edge.
        sig = check_char_count(actual_chars=850, expected_chars=1000)
        assert sig.score == pytest.approx(1.0)

    def test_at_upper_band_edge(self) -> None:
        sig = check_char_count(actual_chars=1150, expected_chars=1000)
        assert sig.score == pytest.approx(1.0)

    def test_below_lower_band_fades(self) -> None:
        # ratio = 0.6 — below lower band; should fade toward 0.
        sig = check_char_count(actual_chars=600, expected_chars=1000)
        assert 0.0 < sig.score < 1.0

    def test_far_below_band_is_zero(self) -> None:
        sig = check_char_count(actual_chars=100, expected_chars=1000)
        assert sig.score == 0.0

    def test_no_expectation_is_neutral(self) -> None:
        # expected=0 → caller has no estimate; neutral signal so
        # char-count doesn't punish the overall.
        sig = check_char_count(actual_chars=500, expected_chars=0)
        assert sig.score == 0.5


class TestKnownPassage:
    def test_neutral_default(self) -> None:
        sig = check_known_passage_neutral()
        assert sig.score == 0.5
        assert sig.matched_count == 0


# -----------------------------------------------------------------------
# Stage-5 — aggregator
# -----------------------------------------------------------------------


class TestComputeQualityScore:
    def test_overall_in_unit_interval(self) -> None:
        score = compute_quality_score("نص كامل.")
        assert 0.0 <= score.overall <= 1.0

    def test_components_attached(self) -> None:
        score = compute_quality_score("نص كامل.")
        # All four signals present and have a score.
        assert score.completeness.score >= 0.0
        assert score.structural_symmetry.score >= 0.0
        assert score.char_count.score >= 0.0
        assert score.known_passage.score >= 0.0

    def test_known_passage_override(self) -> None:
        # When the caller has a real positive corpus match, the
        # overall lifts.
        baseline = compute_quality_score("نص كامل.")
        with_match = compute_quality_score(
            "نص كامل.",
            known_passage=KnownPassageSignal(score=1.0, matched_count=3),
        )
        assert with_match.overall > baseline.overall

    def test_clean_short_text_lands_in_accepted_range(self) -> None:
        # No expected_chars → char_count neutral 0.5.
        # Completeness 1.0 + symmetry 1.0 + char_count 0.5 + known_passage 0.5
        # = 0.30 + 0.20 + 0.15 + 0.10 = 0.75 — DEFICIENT band.
        score = compute_quality_score("نص قصير.")
        # Deficient under canonical thresholds.
        assert 0.60 <= score.overall < 0.85

    def test_truncated_text_drops_overall(self) -> None:
        truncated = compute_quality_score("نص مقطو")  # mid-word
        clean = compute_quality_score("نص كامل.")
        assert truncated.overall < clean.overall


# -----------------------------------------------------------------------
# Stage-4 — homoglyph harness
# -----------------------------------------------------------------------


class TestHomoglyphTaxonomy:
    def test_canonical_pairs_count(self) -> None:
        # The canonical pair list shouldn't shrink without canon shaping.
        assert len(HOMOGLYPH_PAIRS) >= 14

    def test_alternates_round_trip(self) -> None:
        # If `(a, b)` is a pair, both `a → {b, …}` and `b → {a, …}`
        # appear in ALTERNATES.
        for left, right in HOMOGLYPH_PAIRS:
            assert right in ALTERNATES[left]
            assert left in ALTERNATES[right]

    def test_is_homoglyph_candidate(self) -> None:
        assert is_homoglyph_candidate("ر")
        assert is_homoglyph_candidate("ز")
        assert not is_homoglyph_candidate("X")
        assert not is_homoglyph_candidate("0")


class TestHomoglyphCorrector:
    def test_default_returns_no_suggestions(self) -> None:
        # v1.0 ships no auto-correction; default is identity.
        out = find_homoglyph_candidates("كتاب رد")
        assert out == []

    def test_custom_corrector_invoked(self) -> None:
        captured: list[str] = []

        def fake(text: str) -> list[HomoglyphSuggestion]:
            captured.append(text)
            return [
                HomoglyphSuggestion(
                    position=4,
                    original="ر",
                    replacement="ز",
                    confidence=0.9,
                    rationale="dict-hit on alternate",
                ),
            ]

        out = find_homoglyph_candidates("كتاب ردا", corrector=fake)
        assert captured == ["كتاب ردا"]
        assert len(out) == 1
        assert out[0].position == 4
        assert out[0].replacement == "ز"

    def test_suggestions_sorted_by_position(self) -> None:
        def fake(_t: str) -> list[HomoglyphSuggestion]:
            return [
                HomoglyphSuggestion(position=10, original="د", replacement="ذ", confidence=0.5),
                HomoglyphSuggestion(position=2, original="ر", replacement="ز", confidence=0.5),
                HomoglyphSuggestion(position=2, original="ر", replacement="ا", confidence=0.5),
            ]

        out = find_homoglyph_candidates("x", corrector=fake)
        positions = [s.position for s in out]
        assert positions == [2, 2, 10]
        # Same-position suggestions tie-break on `replacement` (alphabetical).
        assert out[0].replacement == "ا"
        assert out[1].replacement == "ز"


class TestSyllableSeparator:
    def test_default_is_identity(self) -> None:
        result = separate_syllables("text")
        assert result.text == "text"
        assert result.insertions == []


# -----------------------------------------------------------------------
# Integration — OCR-PO payload reflects Stage 4 + 5
# -----------------------------------------------------------------------


@pytest.mark.asyncio
class TestOcrPoQualityIntegration:
    async def test_quality_breakdown_lands_on_payload(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        segment = await seed_segment(db_session, project=project, text="")
        from waraq.schemas import Block, Page

        block = (
            await db_session.execute(select(Block).where(Block.block_uuid == segment.block_uuid))
        ).scalar_one()
        page = (
            await db_session.execute(select(Page).where(Page.page_uuid == block.page_uuid))
        ).scalar_one()

        async def _stub(_image: bytes, _mime: str) -> str:
            # Clean Arabic text — completeness + symmetry both full.
            return "بسم الله الرحمن الرحيم."

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
        pos: Sequence[ProvenanceObject] = list(po_q.scalars())
        assert len(pos) == 1
        payload = pos[0].payload
        # Quality breakdown stamped.
        assert payload["quality_breakdown"] is not None
        assert payload["quality_breakdown"]["completeness"] == 1.0
        assert payload["quality_breakdown"]["structural_symmetry"] == 1.0
        # Confidence_score derived from quality (no caller value).
        assert payload["confidence_score"] is not None
        assert 0.6 <= payload["confidence_score"] <= 1.0
        # Default homoglyph corrector emits no suggestions.
        assert payload["homoglyph_suggestion_count"] == 0
        assert payload["homoglyph_suggestions"] == []

    async def test_caller_confidence_takes_precedence_over_quality(
        self, db_session: AsyncSession
    ) -> None:
        """When the caller supplies an explicit `confidence_score`
        (e.g. from a future Stage-3 consensus run), it overrides the
        Stage-5 quality score — consensus is the stronger signal."""
        project = await seed_project(db_session)
        segment = await seed_segment(db_session, project=project, text="")
        from waraq.schemas import Block, Page

        block = (
            await db_session.execute(select(Block).where(Block.block_uuid == segment.block_uuid))
        ).scalar_one()
        page = (
            await db_session.execute(select(Page).where(Page.page_uuid == block.page_uuid))
        ).scalar_one()

        async def _stub(_image: bytes, _mime: str) -> str:
            return "نص كامل."

        job = await start_ocr_job(session=db_session, page=page)
        await run_ocr_job(
            session=db_session,
            ocr_job=job,
            image_bytes=b"",
            mime_type="image/png",
            extractor=_stub,
            target_segment=segment,
            confidence_score=0.92,  # caller-supplied
        )
        po = (
            await db_session.execute(
                select(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.OCR.value)
                .where(ProvenanceObject.scope_uuid == segment.satz_uuid)
            )
        ).scalar_one()
        # Caller's 0.92 wins, not the quality-derived value.
        assert po.payload["confidence_score"] == 0.92
        assert po.payload["confidence_class"] == OcrConfidenceClass.ACCEPTED.value
        # Quality breakdown still attached for audit.
        assert po.payload["quality_breakdown"] is not None

    async def test_quality_check_disabled(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        segment = await seed_segment(db_session, project=project, text="")
        from waraq.schemas import Block, Page

        block = (
            await db_session.execute(select(Block).where(Block.block_uuid == segment.block_uuid))
        ).scalar_one()
        page = (
            await db_session.execute(select(Page).where(Page.page_uuid == block.page_uuid))
        ).scalar_one()

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
        po = (
            await db_session.execute(
                select(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.OCR.value)
                .where(ProvenanceObject.scope_uuid == segment.satz_uuid)
            )
        ).scalar_one()
        # No quality check ran.
        assert po.payload["quality_breakdown"] is None
        # No caller-supplied score either → confidence is None.
        assert po.payload["confidence_score"] is None
        assert po.payload["confidence_class"] is None
