"""T-4.1.1 + T-4.1.2 — OCR job baseline + OCR-PO + revision-on-change.

Layered design:

T-4.1.1 (already in place):
- start_ocr_job: create a PENDING Job for a Page.
- run_ocr_job (no target_segment): execute the Gemini call wrapped in the
  canonical Job lifecycle (PENDING → RUNNING → COMPLETED). Returns text.

T-4.1.2 (this layer):
- run_ocr_job (with target_segment): same lifecycle, plus:
  * Write a Revision via create_revision when the OCR text differs from the
    Segment's current text_content. **No Revision-UUID is issued when the
    text is unchanged** — that's H-4 by construction.
  * Write an OCR-PO via PROVENANCE-Kern (create_po) for every successful
    OCR pass, regardless of whether text changed. The PO records what
    happened; the Revision records the change (and only when there was one).
  * The Guard inside create_revision refuses automatic writes to locked
    segments (H-1, H-2). When that raise happens, the OCR Job is marked
    FAILED with the H-violation in `Job.error`, and **no OCR-PO is written**
    — the canonical contract is "OCR-PO follows a successful Revision (or
    a successful no-change pass), never a Guard refusal."

Atomicity: caller owns the transaction. On the happy path, the OCR-PO and
the optional Revision land in the same transaction as the Job state
transition. On Guard refusal, the Job is FAILED, no Revision and no OCR-PO
are staged, and the original H1H2Violation re-raises.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.db.session import get_settings
from waraq.identity.service import new_uuid
from waraq.invariant.enums import OperationMode
from waraq.invariant.exceptions import GuardViolation
from waraq.jobs import complete_job, fail_job, start_job
from waraq.ocr.confidence import classify_confidence
from waraq.ocr.consensus import EngineResult
from waraq.ocr.exceptions import OcrError
from waraq.ocr.gemini import extract_text
from waraq.ocr.homoglyph import HomoglyphCorrector, find_homoglyph_candidates
from waraq.ocr.profiling import profile_exception
from waraq.ocr.quality import QualityScore, compute_quality_score
from waraq.provenance import create_po
from waraq.revision import create_revision
from waraq.schemas import Job, Page, Revision, Segment
from waraq.schemas.enums import ChangeSource, JobState, POType, ScopeType

JOB_TYPE = "ocr_baseline"

# Type alias for the injectable extractor — keeps signatures tidy and lets
# tests substitute a stub without monkeypatching module globals.
TextExtractor = Callable[[bytes, str], Awaitable[str]]


async def start_ocr_job(*, session: AsyncSession, page: Page) -> Job:
    """Create a PENDING OCR Job for `page`. project_uuid is copied so
    project-scoped queries find OCR jobs alongside upload jobs."""
    job = Job(
        job_uuid=new_uuid(),
        job_type=JOB_TYPE,
        state=JobState.PENDING.value,
        project_uuid=page.project_uuid,
        payload={"page_uuid": str(page.page_uuid)},
    )
    session.add(job)
    await session.flush()
    return job


async def run_ocr_job(
    *,
    session: AsyncSession,
    ocr_job: Job,
    image_bytes: bytes,
    mime_type: str = "image/png",
    extractor: TextExtractor | None = None,
    target_segment: Segment | None = None,
    confidence_score: float | None = None,
    was_preprocessed: bool = False,
    source_dpi: int | None = None,
    expected_chars: int = 0,
    homoglyph_corrector: HomoglyphCorrector | None = None,
    run_quality_check: bool = True,
    engine_breakdown: list[EngineResult] | None = None,
    engine_agreement: str | None = None,
    stage3_payload: dict[str, Any] | None = None,
) -> str:
    """Execute the OCR Job and (if `target_segment` is provided) write the
    canonical Revision + OCR-PO pair.

    Args:
        session: Active async session. Caller manages commit/rollback.
        ocr_job: The Job to execute. Must be in PENDING state.
        image_bytes: Raw bytes of the page image.
        mime_type: Content-type hint for Gemini.
        extractor: Optional async callable. Defaults to the real Gemini wrapper.
        target_segment: When provided, the OCR text is written into this
            Segment via create_revision (only on text change), and an
            OCR-PO is written for the segment via PROVENANCE-Kern.
            When None, the function behaves as the T-4.1.1 baseline: it
            returns text and no events/POs are written.

    Returns:
        The extracted text.

    Raises:
        Re-raises any extractor exception (after marking the Job FAILED).
        Re-raises any Guard violation from create_revision (after marking
        the Job FAILED). In both failure cases, no OCR-PO is written.
    """
    extract = extractor if extractor is not None else extract_text
    settings = get_settings()

    await start_job(session=session, job=ocr_job)

    # --- Phase 1: extract text ---------------------------------------------
    try:
        text = await extract(image_bytes, mime_type)
    except Exception as exc:
        # T-4.1.3: also classify into F-01..F-09 (canonical OCR error codes).
        # Job.error field semantics (stable across phases):
        #   error_class    — Python exception class name (diagnostic, always)
        #   error_code     — canonical F-XX code (extract phase only;
        #                    Guard-phase failures aren't OCR errors per F-XX)
        #   repr           — full exception repr (diagnostic)
        #   is_ocr_error   — True when isinstance(exc, OcrError)
        #   phase          — "extract" | "guard"
        await fail_job(
            session=session,
            job=ocr_job,
            error={
                "error_class": type(exc).__name__,
                "error_code": profile_exception(exc).value,
                "repr": repr(exc),
                "is_ocr_error": isinstance(exc, OcrError),
                "phase": "extract",
            },
        )
        raise

    # --- Phase 2 (T-4.1.2 only): Revision + OCR-PO when target_segment set -
    revision: Revision | None = None
    if target_segment is not None:
        text_changed = text != target_segment.text_content
        try:
            if text_changed:
                # H-1/H-2 enforced inside create_revision. If the segment is
                # manual_local / manual_editorial, this raises and we mark
                # FAILED — no OCR-PO is written.
                revision = await create_revision(
                    session=session,
                    segment=target_segment,
                    after_text=text,
                    change_source=ChangeSource.OCR,
                    operation_mode=OperationMode.AUTOMATIC,
                )

            # OCR-PO is written on every successful OCR pass — change or
            # no-change. The PO records that OCR happened; the Revision
            # records the change.
            # §3.4 Stage-5 quality score + Stage-4 homoglyph candidates.
            # Quality score feeds confidence_score when no caller-supplied
            # value exists; explicit caller value (e.g. Stage-3 consensus
            # in sub-batch D) takes precedence — the consensus signal
            # subsumes single-engine quality heuristics.
            quality: QualityScore | None = None
            if run_quality_check:
                quality = compute_quality_score(text, expected_chars=expected_chars)
                if confidence_score is None:
                    confidence_score = quality.overall

            # Stage-4 homoglyph candidate detection — read-only
            # suggestion list, never auto-applied (§2.2 "no silent
            # winners" / H-1/H-2). Default corrector emits no
            # suggestions; real adapters surface candidates the user
            # or Stage-3 consensus reviews.
            homoglyph_suggestions = find_homoglyph_candidates(text, corrector=homoglyph_corrector)

            # Phase 4 sub-batch A — §4.4 confidence taxonomy + §3.3
            # preprocessing audit. Confidence may now come from Stage-5
            # quality scoring (when run_quality_check=True) or from a
            # Stage-3 consensus pass (sub-batch D); either way the
            # taxonomy classifier is the same.
            confidence_class = (
                classify_confidence(confidence_score).value
                if confidence_score is not None
                else None
            )
            ocr_po_payload: dict[str, Any] = {
                "model": settings.gemini_ocr_model,
                "text_chars": len(text),
                "text_changed": text_changed,
                "rev_uuid": str(revision.rev_uuid) if revision is not None else None,
                "ocr_job_uuid": str(ocr_job.job_uuid),
                "confidence_score": confidence_score,
                "confidence_class": confidence_class,
                "was_preprocessed": was_preprocessed,
                "source_dpi": source_dpi,
                # Stage-5 quality breakdown — None when run_quality_check=False.
                "quality_breakdown": (
                    {
                        "overall": quality.overall,
                        "completeness": quality.completeness.score,
                        "structural_symmetry": quality.structural_symmetry.score,
                        "char_count": quality.char_count.score,
                        "known_passage": quality.known_passage.score,
                    }
                    if quality is not None
                    else None
                ),
                # Stage-4 homoglyph candidate count + first-N
                # serialization. Empty when default corrector is in use.
                "homoglyph_suggestion_count": len(homoglyph_suggestions),
                "homoglyph_suggestions": [
                    {
                        "position": s.position,
                        "original": s.original,
                        "replacement": s.replacement,
                        "confidence": s.confidence,
                        "rationale": s.rationale,
                    }
                    for s in homoglyph_suggestions[:32]
                ],
                # Sub-batch C — Stage-2 multi-engine breakdown.
                # `engines` is None for legacy single-engine callers (the
                # extractor-driven path); when set, the §3.6-symmetric
                # two-engine driver populated it. `engine_agreement` is
                # the coarse v1.0 agreement label; sub-batch D refines.
                #
                # Sub-batch N-2 (2026-05-12): each engine's `text` is
                # persisted alongside `text_chars` so the audit-dashboard
                # divergent-case can show a side-by-side reading
                # comparison. Additive payload extension; legacy OCR-POs
                # written before N-2 lack `text` per engine — the audit
                # UI shows a "(re-run OCR to populate)" notice for them.
                "engines": (
                    [
                        {
                            "engine": r.engine.value,
                            "text": r.text,
                            "text_chars": len(r.text),
                            "confidence": r.confidence,
                            "error_class": r.error_class,
                        }
                        for r in engine_breakdown
                    ]
                    if engine_breakdown is not None
                    else None
                ),
                "engine_agreement": engine_agreement,
                # Sub-batch D — §3.4 Stage-3 three-track consensus
                # breakdown. None for callers that don't run Stage-3
                # (e.g. existing T-4.1.2 unit tests). When set, the
                # caller-aggregated final confidence has typically
                # overridden `confidence_score` already.
                "stage3": stage3_payload,
            }
            await create_po(
                session=session,
                po_type=POType.OCR,
                scope_type=ScopeType.SEGMENT,
                scope_uuid=target_segment.satz_uuid,
                payload=ocr_po_payload,
            )
        except GuardViolation as exc:
            await fail_job(
                session=session,
                job=ocr_job,
                error={
                    "error_class": type(exc).__name__,
                    "repr": repr(exc),
                    "is_ocr_error": False,
                    "phase": "guard",
                },
            )
            raise

    # --- Phase 3: complete the job ----------------------------------------
    await complete_job(
        session=session,
        job=ocr_job,
        result={
            "text_chars": len(text),
            "model": settings.gemini_ocr_model,
            "rev_uuid": str(revision.rev_uuid) if revision is not None else None,
            "text_changed": revision is not None,
        },
    )
    return text
