"""T-4.1.1 — OCR baseline tests.

Three layers:
1. Architectural — service signature, JOB_TYPE, no foreign-table writes.
2. Integration with stub extractor — no Gemini quota burned. Job lifecycle,
   result/error payloads, exception propagation.
3. Live-API smoke (`@pytest.mark.live_api`) — opt-in only. Skipped unless
   GOOGLE_AI_API_KEY is set in the environment AND `--run-live-api` is
   passed to pytest. Lets you sanity-check the SDK wiring without burning
   quota on every CI run.
"""

from __future__ import annotations

import inspect
import os

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.ocr import (
    GeminiApiError,
    MissingGeminiApiKey,
    extract_text,
    run_ocr_job,
    start_ocr_job,
)
from waraq.schemas import (
    DecisionEvent,
    Page,
    Project,
    ProvenanceObject,
    Revision,
)
from waraq.schemas.enums import JobState

# --- Helpers ---------------------------------------------------------------


async def _seed_page(session: AsyncSession) -> Page:
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="ocr-baseline-test")
    session.add(project)
    await session.flush()

    page = Page(page_uuid=new_uuid(), project_uuid=project.project_uuid, page_index=1)
    session.add(page)
    await session.flush()
    return page


# --- Layer 1: architectural ------------------------------------------------


class TestT_4_1_1_ServiceSurface:
    def test_run_ocr_job_signature_is_keyword_only(self) -> None:
        sig = inspect.signature(run_ocr_job)
        for name, param in sig.parameters.items():
            assert param.kind == inspect.Parameter.KEYWORD_ONLY, f"{name} must be keyword-only"

    def test_run_ocr_job_accepts_injectable_extractor(self) -> None:
        sig = inspect.signature(run_ocr_job)
        assert "extractor" in sig.parameters
        # Default is None so the real extractor wires in at call time.
        assert sig.parameters["extractor"].default is None

    # The T-4.1.1 boundary AST guard that forbade `create_po` / `create_revision`
    # imports has been removed — T-4.1.2 legitimately crosses that boundary.
    # Module bypass discipline (no direct ProvenanceObject/Revision schema
    # imports) is still enforced by the cross-table tests below.


# --- Layer 2: integration with stub extractor -----------------------------


class _StubExtractor:
    """Captures call args and returns a configurable text. Async-callable
    so it matches the canonical `TextExtractor` shape."""

    def __init__(self, return_text: str = "stubbed text") -> None:
        self.return_text = return_text
        self.calls: list[tuple[bytes, str]] = []

    async def __call__(self, image_bytes: bytes, mime_type: str) -> str:
        self.calls.append((image_bytes, mime_type))
        return self.return_text


@pytest.mark.asyncio
class TestT_4_1_1_HappyPath:
    async def test_start_ocr_job_creates_pending_job(self, db_session: AsyncSession) -> None:
        page = await _seed_page(db_session)

        job = await start_ocr_job(session=db_session, page=page)

        assert job.state == JobState.PENDING.value
        assert job.job_type == "ocr_baseline"
        assert job.project_uuid == page.project_uuid
        assert job.payload == {"page_uuid": str(page.page_uuid)}

    async def test_run_ocr_job_completes_and_returns_text(self, db_session: AsyncSession) -> None:
        page = await _seed_page(db_session)
        job = await start_ocr_job(session=db_session, page=page)
        stub = _StubExtractor(return_text="بسم الله الرحمن الرحيم")

        text = await run_ocr_job(
            session=db_session,
            ocr_job=job,
            image_bytes=b"<png-bytes>",
            mime_type="image/png",
            extractor=stub,
        )

        assert text == "بسم الله الرحمن الرحيم"
        assert job.state == JobState.COMPLETED.value
        assert job.result is not None
        assert job.result["text_chars"] == len("بسم الله الرحمن الرحيم")
        assert "model" in job.result

    async def test_extractor_receives_image_bytes_and_mime_type(
        self, db_session: AsyncSession
    ) -> None:
        page = await _seed_page(db_session)
        job = await start_ocr_job(session=db_session, page=page)
        stub = _StubExtractor()

        await run_ocr_job(
            session=db_session,
            ocr_job=job,
            image_bytes=b"raw-image",
            mime_type="image/jpeg",
            extractor=stub,
        )
        assert stub.calls == [(b"raw-image", "image/jpeg")]

    async def test_state_transitions_pending_running_completed(
        self, db_session: AsyncSession
    ) -> None:
        page = await _seed_page(db_session)
        job = await start_ocr_job(session=db_session, page=page)
        assert job.state == JobState.PENDING.value

        # Custom extractor that observes the state mid-call.
        states_seen: list[str] = []

        async def _observing_extractor(_b: bytes, _m: str) -> str:
            states_seen.append(job.state)
            return "ok"

        await run_ocr_job(
            session=db_session,
            ocr_job=job,
            image_bytes=b"x",
            extractor=_observing_extractor,
        )

        assert states_seen == [JobState.RUNNING.value]
        assert job.state == JobState.COMPLETED.value


# --- Layer 2b: failure handling -------------------------------------------


class _ExplodingExtractor:
    def __init__(self, exc: BaseException) -> None:
        self.exc = exc

    async def __call__(self, _b: bytes, _m: str) -> str:
        raise self.exc


@pytest.mark.asyncio
class TestT_4_1_1_FailureHandling:
    async def test_extractor_failure_transitions_job_to_failed(
        self, db_session: AsyncSession
    ) -> None:
        page = await _seed_page(db_session)
        job = await start_ocr_job(session=db_session, page=page)

        underlying = GeminiApiError(model="gemini-2.5-pro", cause=RuntimeError("429"))
        with pytest.raises(GeminiApiError):
            await run_ocr_job(
                session=db_session,
                ocr_job=job,
                image_bytes=b"x",
                extractor=_ExplodingExtractor(underlying),
            )

        assert job.state == JobState.FAILED.value
        assert job.error is not None
        assert job.error["error_class"] == "GeminiApiError"
        assert job.error["is_ocr_error"] is True
        assert "429" in job.error["repr"]

    async def test_unexpected_exception_still_marks_failed_and_propagates(
        self, db_session: AsyncSession
    ) -> None:
        page = await _seed_page(db_session)
        job = await start_ocr_job(session=db_session, page=page)

        with pytest.raises(ValueError, match="boom"):
            await run_ocr_job(
                session=db_session,
                ocr_job=job,
                image_bytes=b"x",
                extractor=_ExplodingExtractor(ValueError("boom")),
            )

        assert job.state == JobState.FAILED.value
        assert job.error is not None
        assert job.error["error_class"] == "ValueError"
        assert job.error["is_ocr_error"] is False


# --- Layer 2c: cross-table discipline (T-4.1.1 boundary) -----------------


@pytest.mark.asyncio
class TestT_4_1_1_BaselineModeWritesNoEventsOrPos:
    """When `run_ocr_job` is called WITHOUT `target_segment`, it behaves as
    the T-4.1.1 baseline: returns text, completes the Job, and writes nothing
    else. The Revision + OCR-PO writes only happen when target_segment is
    provided (T-4.1.2 layer). This test pins that contract."""

    async def test_baseline_run_does_not_create_revision_decision_event_or_po(
        self, db_session: AsyncSession
    ) -> None:
        page = await _seed_page(db_session)
        job = await start_ocr_job(session=db_session, page=page)

        before_rev = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()
        before_de = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        before_po = (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one()

        await run_ocr_job(
            session=db_session,
            ocr_job=job,
            image_bytes=b"x",
            extractor=_StubExtractor("hello"),
        )

        assert (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one() == before_rev
        assert (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one() == before_de
        assert (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one() == before_po


# --- Layer 3: missing-key path (no live API) -----------------------------


@pytest.mark.asyncio
class TestT_4_1_1_MissingApiKey:
    async def test_real_extractor_raises_when_key_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from waraq.db import session as db_session_module

        # Force an empty key regardless of what's in backend/.env.
        monkeypatch.setenv("GOOGLE_AI_API_KEY", "")
        db_session_module.get_settings.cache_clear()
        try:
            with pytest.raises(MissingGeminiApiKey):
                await extract_text(b"image-bytes", "image/png")
        finally:
            db_session_module.get_settings.cache_clear()


# --- Layer 4: optional live-API smoke test -------------------------------


def _live_api_enabled() -> bool:
    return bool(os.environ.get("GOOGLE_AI_API_KEY")) and (
        os.environ.get("WARAQ_RUN_LIVE_API") == "1"
    )


@pytest_asyncio.fixture
async def live_api_clear_settings_cache() -> None:
    from waraq.db import session as db_session_module

    db_session_module.get_settings.cache_clear()


@pytest.mark.live_api
@pytest.mark.skipif(
    not _live_api_enabled(),
    reason="Set GOOGLE_AI_API_KEY and WARAQ_RUN_LIVE_API=1 to exercise the real Gemini API",
)
@pytest.mark.asyncio
async def test_live_gemini_smoke(live_api_clear_settings_cache: None) -> None:
    """Smoke test: tiny PNG → Gemini → some string. Skipped by default to
    avoid burning the free-tier quota on routine test runs.

    To run it manually:
        WARAQ_RUN_LIVE_API=1 .venv/bin/pytest tests/ocr -k live_gemini
    """
    # 1x1 transparent PNG — won't have OCRable text, but proves the call path.
    tiny_png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000d49444154789c63000100000005000196f4d8c40000000049454e44"
        "ae426082"
    )
    text = await extract_text(tiny_png, "image/png")
    # Don't assert content — Gemini may return an empty string or descriptor.
    # The proof is "we got a string back without an exception."
    assert isinstance(text, str)
