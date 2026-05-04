"""T-4.1.3 — F-01..F-09 OCR error-class profiling tests.

Two layers:
1. Pure profile_exception unit tests — every F-XX class has at least one
   positive mapping. Heuristic keyword sets are tested by the kinds of
   exceptions they're meant to catch.
2. Integration — Job.error after a failed extract phase carries the
   canonical F-XX code in `error_code` (extract phase only) plus the
   Python exception class name in `error_class`.

Note on canon-pending: the SPECIFIC class descriptions and the keyword
mappings are draft until CAB §B is consulted. The tests below verify the
infrastructure is correctly wired — they DON'T attempt to spec the
canonical mapping. If CAB §B says "F-04 means foo not bar", update the
mapping in `waraq.ocr.profiling._Keywords` and adjust the tests.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.ocr import (
    GeminiApiError,
    OcrErrorClass,
    profile_exception,
    run_ocr_job,
    start_ocr_job,
)
from waraq.ocr.error_classes import F_DESCRIPTIONS
from waraq.schemas import Page, Project
from waraq.schemas.enums import JobState

# --- Layer 1: pure profile_exception ------------------------------------


class TestT_4_1_3_EnumShape:
    def test_all_nine_codes_present(self) -> None:
        codes = {e.value for e in OcrErrorClass}
        assert codes == {f"F-0{i}" for i in range(1, 10)}

    def test_each_code_has_a_shell_description(self) -> None:
        for cls in OcrErrorClass:
            assert cls in F_DESCRIPTIONS
            assert isinstance(F_DESCRIPTIONS[cls], str)
            assert F_DESCRIPTIONS[cls]


class TestT_4_1_3_NetworkAndTimeout_F04:
    def test_bare_timeout_error_maps_to_f04(self) -> None:
        assert profile_exception(TimeoutError("read timed out")) == OcrErrorClass.F_04

    def test_bare_connection_error_maps_to_f04(self) -> None:
        assert profile_exception(ConnectionError("refused")) == OcrErrorClass.F_04

    def test_gemini_wrapping_timeout_cause_maps_to_f04(self) -> None:
        wrapped = GeminiApiError(model="g", cause=TimeoutError("x"))
        assert profile_exception(wrapped) == OcrErrorClass.F_04

    def test_gemini_with_network_keyword_in_cause_maps_to_f04(self) -> None:
        wrapped = GeminiApiError(model="g", cause=RuntimeError("connection reset"))
        assert profile_exception(wrapped) == OcrErrorClass.F_04


class TestT_4_1_3_AuthenticationAndRate:
    def test_401_maps_to_f01(self) -> None:
        wrapped = GeminiApiError(model="g", cause=RuntimeError("HTTP 401 Unauthorized"))
        assert profile_exception(wrapped) == OcrErrorClass.F_01

    def test_403_permission_maps_to_f01(self) -> None:
        wrapped = GeminiApiError(model="g", cause=PermissionError("forbidden: insufficient scope"))
        assert profile_exception(wrapped) == OcrErrorClass.F_01

    def test_429_maps_to_f02(self) -> None:
        wrapped = GeminiApiError(model="g", cause=RuntimeError("HTTP 429 Too Many Requests"))
        assert profile_exception(wrapped) == OcrErrorClass.F_02

    def test_resource_exhausted_maps_to_f02(self) -> None:
        wrapped = GeminiApiError(model="g", cause=RuntimeError("ResourceExhausted: quota"))
        assert profile_exception(wrapped) == OcrErrorClass.F_02


class TestT_4_1_3_ServerError_F03:
    def test_500_maps_to_f03(self) -> None:
        wrapped = GeminiApiError(model="g", cause=RuntimeError("HTTP 500 Internal Server Error"))
        assert profile_exception(wrapped) == OcrErrorClass.F_03

    def test_503_unavailable_maps_to_f03(self) -> None:
        wrapped = GeminiApiError(model="g", cause=RuntimeError("503 Service Unavailable"))
        assert profile_exception(wrapped) == OcrErrorClass.F_03


class TestT_4_1_3_MalformedInput_F05:
    def test_value_error_maps_to_f05(self) -> None:
        assert profile_exception(ValueError("not a valid PNG")) == OcrErrorClass.F_05

    def test_type_error_maps_to_f05(self) -> None:
        assert profile_exception(TypeError("expected bytes, got str")) == OcrErrorClass.F_05


class TestT_4_1_3_ContentFiltered_F07:
    def test_safety_block_maps_to_f07(self) -> None:
        wrapped = GeminiApiError(
            model="g", cause=RuntimeError("response blocked: SAFETY harm_category")
        )
        assert profile_exception(wrapped) == OcrErrorClass.F_07

    def test_recitation_block_maps_to_f07(self) -> None:
        wrapped = GeminiApiError(model="g", cause=RuntimeError("blocked: RECITATION"))
        assert profile_exception(wrapped) == OcrErrorClass.F_07


class TestT_4_1_3_TokenLimit_F08:
    def test_context_length_maps_to_f08(self) -> None:
        wrapped = GeminiApiError(model="g", cause=RuntimeError("context length exceeded"))
        assert profile_exception(wrapped) == OcrErrorClass.F_08

    def test_image_too_large_maps_to_f08(self) -> None:
        wrapped = GeminiApiError(model="g", cause=RuntimeError("image too large for input"))
        assert profile_exception(wrapped) == OcrErrorClass.F_08


class TestT_4_1_3_Unknown_F09:
    def test_unrecognized_runtime_error_maps_to_f09(self) -> None:
        assert profile_exception(RuntimeError("totally unexpected")) == OcrErrorClass.F_09

    def test_unrecognized_gemini_cause_maps_to_f09(self) -> None:
        wrapped = GeminiApiError(model="g", cause=RuntimeError("plot twist"))
        assert profile_exception(wrapped) == OcrErrorClass.F_09

    def test_arbitrary_exception_class_maps_to_f09(self) -> None:
        class WeirdError(Exception):
            pass

        assert profile_exception(WeirdError("???")) == OcrErrorClass.F_09


# --- Layer 2: integration on Job.error -----------------------------------


class _ExplodingExtractor:
    def __init__(self, exc: BaseException) -> None:
        self.exc = exc

    async def __call__(self, _b: bytes, _m: str) -> str:
        raise self.exc


async def _seed_page(session: AsyncSession) -> Page:
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="ocr-profile-test")
    session.add(project)
    await session.flush()
    page = Page(page_uuid=new_uuid(), project_uuid=project.project_uuid, page_index=1)
    session.add(page)
    await session.flush()
    return page


@pytest.mark.asyncio
class TestT_4_1_3_JobErrorCarriesFXX:
    async def test_extract_phase_failure_records_error_code(self, db_session: AsyncSession) -> None:
        page = await _seed_page(db_session)
        job = await start_ocr_job(session=db_session, page=page)

        # 429 should classify as F-02 (rate_limit).
        wrapped = GeminiApiError(model="gemini-2.5-pro", cause=RuntimeError("HTTP 429"))
        with pytest.raises(GeminiApiError):
            await run_ocr_job(
                session=db_session,
                ocr_job=job,
                image_bytes=b"x",
                extractor=_ExplodingExtractor(wrapped),
            )

        assert job.state == JobState.FAILED.value
        assert job.error is not None
        # T-4.1.1 fields preserved.
        assert job.error["error_class"] == "GeminiApiError"
        assert job.error["is_ocr_error"] is True
        assert job.error["phase"] == "extract"
        # T-4.1.3 addition.
        assert job.error["error_code"] == OcrErrorClass.F_02.value

    async def test_unknown_exception_records_f09(self, db_session: AsyncSession) -> None:
        page = await _seed_page(db_session)
        job = await start_ocr_job(session=db_session, page=page)

        with pytest.raises(RuntimeError):
            await run_ocr_job(
                session=db_session,
                ocr_job=job,
                image_bytes=b"x",
                extractor=_ExplodingExtractor(RuntimeError("plot twist")),
            )

        assert job.error is not None
        assert job.error["error_code"] == OcrErrorClass.F_09.value

    async def test_value_error_records_f05(self, db_session: AsyncSession) -> None:
        page = await _seed_page(db_session)
        job = await start_ocr_job(session=db_session, page=page)

        with pytest.raises(ValueError):
            await run_ocr_job(
                session=db_session,
                ocr_job=job,
                image_bytes=b"x",
                extractor=_ExplodingExtractor(ValueError("bad bytes")),
            )

        assert job.error is not None
        assert job.error["error_code"] == OcrErrorClass.F_05.value
        assert job.error["error_class"] == "ValueError"
