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
from waraq.ocr.exceptions import OcrError
from waraq.ocr.gemini import extract_text
from waraq.ocr.profiling import profile_exception
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
            ocr_po_payload: dict[str, Any] = {
                "model": settings.gemini_ocr_model,
                "text_chars": len(text),
                "text_changed": text_changed,
                "rev_uuid": str(revision.rev_uuid) if revision is not None else None,
                "ocr_job_uuid": str(ocr_job.job_uuid),
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
