"""Phase 4 — kraken manuscript/calligraphy OCR adapter.

Three orthogonal layers covered:

1. `waraq.ocr.routing` — the `use_kraken` flag adds KRAKEN to the
   eligible set for every non-QURAN class.
2. `waraq.ocr.consensus.run_engines` — kraken is invoked when the
   flag is set AND the callable is supplied; gracefully no-ops
   otherwise; error branch records `error_class`.
3. `waraq.ocr.kraken` — `is_available()` reflects package + model
   presence; `extract_with_confidence` raises `KrakenUnavailable`
   when the package isn't installed (the test host case).
"""

from __future__ import annotations

import builtins
import os
from collections.abc import Iterator
from typing import Any

import pytest

from waraq.ocr.openai_ocr import OpenAiOcrResult
from waraq.ocr.consensus import (
    AGREEMENT_DIVERGENT,
    AGREEMENT_ENGINE_ERROR,
    AGREEMENT_EXACT_MATCH,
    run_engines,
)
from waraq.ocr.kraken import (
    KrakenResult,
    KrakenUnavailable,
    extract_with_confidence,
    is_available,
)
from waraq.ocr.routing import OcrEngine, engines_for
from waraq.schemas.enums import BlockClass

# ---------------------------------------------------------------------
# Routing — `use_kraken` extension
# ---------------------------------------------------------------------


class TestRoutingWithKrakenFlag:
    """The `use_kraken` flag adds KRAKEN to the eligible set for every
    non-QURAN class. The base routing (Gemini + OpenAI OCR) is
    preserved — kraken is additive, not replacement."""

    def test_kraken_off_default(self) -> None:
        assert OcrEngine.KRAKEN not in engines_for(BlockClass.MAIN_TEXT)
        assert OcrEngine.KRAKEN not in engines_for(BlockClass.HEADING)

    def test_kraken_added_to_main_text_when_flag_set(self) -> None:
        eligible = engines_for(BlockClass.MAIN_TEXT, use_kraken=True)
        assert OcrEngine.KRAKEN in eligible
        # Other engines preserved — kraken is additive.
        assert OcrEngine.GEMINI in eligible
        assert OcrEngine.OPENAI in eligible

    def test_kraken_added_to_all_non_quran_classes(self) -> None:
        for cls in (
            BlockClass.MAIN_TEXT,
            BlockClass.HEADING,
            BlockClass.FOOTNOTE,
            BlockClass.HADITH,
            BlockClass.MARGINALIA,
        ):
            assert OcrEngine.KRAKEN in engines_for(cls, use_kraken=True), cls

    def test_kraken_excluded_from_quran_even_with_flag(self) -> None:
        # Qurʾān script is canonically printed — kraken's manuscript
        # orientation would degrade rather than help.
        eligible = engines_for(BlockClass.QURAN, use_kraken=True)
        assert OcrEngine.KRAKEN not in eligible
        assert eligible == frozenset({OcrEngine.GEMINI})

    def test_kraken_enum_canonical_value(self) -> None:
        assert OcrEngine.KRAKEN.value == "kraken"


# ---------------------------------------------------------------------
# Consensus driver — kraken eligibility + error branch
# ---------------------------------------------------------------------


def _gemini_returns(text: str):
    async def _fn(_image: bytes, _mime: str) -> str:
        return text

    return _fn


def _cv_returns(text: str, confidence: float | None):
    async def _fn(_image: bytes, _mime: str) -> OpenAiOcrResult:
        return OpenAiOcrResult(text=text, confidence=confidence)

    return _fn


def _kraken_returns(text: str, confidence: float | None):
    async def _fn(_image: bytes, _mime: str) -> KrakenResult:
        return KrakenResult(text=text, confidence=confidence)

    return _fn


def _kraken_raises(exc: Exception):
    async def _fn(_image: bytes, _mime: str) -> KrakenResult:
        raise exc

    return _fn


@pytest.mark.asyncio
class TestConsensusKrakenInvocation:
    async def test_kraken_not_invoked_when_flag_false(self) -> None:
        kraken_invoked = False

        async def kraken_fn(_image: bytes, _mime: str) -> KrakenResult:
            nonlocal kraken_invoked
            kraken_invoked = True
            return KrakenResult(text="should-not-run", confidence=0.99)

        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=_gemini_returns("بسم الله"),
            openai_ocr_fn=_cv_returns("بسم الله", 0.9),
            kraken_fn=kraken_fn,
            use_kraken=False,
        )

        assert kraken_invoked is False
        # Default 2-engine behaviour preserved.
        assert result.agreement == AGREEMENT_EXACT_MATCH
        assert len(result.engines) == 2
        assert {r.engine for r in result.engines} == {
            OcrEngine.GEMINI,
            OcrEngine.OPENAI,
        }

    async def test_kraken_runs_when_flag_set_and_fn_supplied(self) -> None:
        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=_gemini_returns("بسم الله"),
            openai_ocr_fn=_cv_returns("بسم الله", 0.9),
            kraken_fn=_kraken_returns("بسم الله", 0.85),
            use_kraken=True,
        )

        assert len(result.engines) == 3
        assert {r.engine for r in result.engines} == {
            OcrEngine.GEMINI,
            OcrEngine.OPENAI,
            OcrEngine.KRAKEN,
        }
        kraken_result = next(r for r in result.engines if r.engine == OcrEngine.KRAKEN)
        assert kraken_result.text == "بسم الله"
        assert kraken_result.confidence == pytest.approx(0.85)
        assert kraken_result.error_class is None

    async def test_kraken_skipped_when_flag_set_but_fn_missing(self) -> None:
        # Partial wiring (use_kraken=True without kraken_fn) is a
        # programmer error but should degrade gracefully — fall back
        # to 2-engine behaviour, no runtime crash.
        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=_gemini_returns("بسم الله"),
            openai_ocr_fn=_cv_returns("بسم الله", 0.9),
            kraken_fn=None,
            use_kraken=True,
        )

        assert len(result.engines) == 2
        assert {r.engine for r in result.engines} == {
            OcrEngine.GEMINI,
            OcrEngine.OPENAI,
        }

    async def test_kraken_skipped_on_quran_class_even_with_flag(self) -> None:
        kraken_invoked = False

        async def kraken_fn(_image: bytes, _mime: str) -> KrakenResult:
            nonlocal kraken_invoked
            kraken_invoked = True
            return KrakenResult(text="should-not-run", confidence=0.99)

        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.QURAN,
            gemini_fn=_gemini_returns("بسم الله"),
            openai_ocr_fn=_cv_returns("never", 0.9),
            kraken_fn=kraken_fn,
            use_kraken=True,
        )

        assert kraken_invoked is False
        assert len(result.engines) == 1
        assert result.engines[0].engine == OcrEngine.GEMINI

    async def test_kraken_error_recorded_as_engine_error_class(self) -> None:
        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=_gemini_returns("بسم الله"),
            openai_ocr_fn=_cv_returns("بسم الله", 0.9),
            kraken_fn=_kraken_raises(KrakenUnavailable("model missing")),
            use_kraken=True,
        )

        # Surviving 2 engines agreed → not propagated as overall
        # engine_error (the agreement classifier only looks at
        # successful results). Gemini + OpenAI OCR exact-match.
        assert result.agreement == AGREEMENT_EXACT_MATCH
        kraken_result = next(r for r in result.engines if r.engine == OcrEngine.KRAKEN)
        assert kraken_result.text == ""
        assert kraken_result.confidence is None
        assert kraken_result.error_class == "KrakenUnavailable"

    async def test_three_engine_divergent_aggregates_min_confidence(self) -> None:
        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=_gemini_returns("بسم الله الرحمن"),
            openai_ocr_fn=_cv_returns("سمع غير لذلك", 0.75),
            kraken_fn=_kraken_returns("نص مختلف تماما", 0.6),
            use_kraken=True,
        )

        assert result.agreement == AGREEMENT_DIVERGENT
        # Divergent rule: min of reported confidences.
        assert result.aggregated_confidence == pytest.approx(0.6)


# ---------------------------------------------------------------------
# Adapter — graceful unavailability on a host without kraken installed
# ---------------------------------------------------------------------


@pytest.fixture
def hide_kraken_import(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Force `import kraken` to raise ImportError so the adapter's
    "not installed" branch fires deterministically regardless of
    whether the host venv has the package. Mirrors the cv2/PIL
    hide-import pattern used elsewhere in the OCR test suite."""
    real_import = builtins.__import__

    def _fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "kraken" or name.startswith("kraken."):
            raise ImportError(f"hidden kraken import: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    yield


@pytest.fixture
def clear_kraken_model_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("KRAKEN_MODEL_PATH", raising=False)
    yield


class TestKrakenAvailability:
    def test_is_available_false_when_package_missing(
        self, hide_kraken_import: None
    ) -> None:
        assert is_available() is False

    def test_is_available_false_when_model_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        # Point at a non-existent file. Even if kraken is installed in
        # the venv, `is_available` should return False because the
        # model file isn't on disk.
        monkeypatch.setenv("KRAKEN_MODEL_PATH", str(tmp_path / "no_such_model.mlmodel"))
        assert is_available() is False


@pytest.mark.asyncio
class TestKrakenAdapterUnavailable:
    async def test_raises_when_package_missing(
        self, hide_kraken_import: None
    ) -> None:
        with pytest.raises(KrakenUnavailable) as info:
            await extract_with_confidence(b"png-bytes", "image/png")
        # Should hit either the PIL or kraken ImportError branch with
        # a helpful install hint in the message.
        msg = str(info.value).lower()
        assert "install" in msg or "pillow" in msg or "kraken" in msg

    async def test_raises_when_model_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
    ) -> None:
        # If kraken isn't importable on this host, the package-missing
        # branch fires first — skip then. We're testing the model-path
        # branch specifically.
        try:
            import kraken  # noqa: F401
        except ImportError:
            pytest.skip("kraken package not installed; model-missing branch unreachable")

        monkeypatch.setenv(
            "KRAKEN_MODEL_PATH", str(tmp_path / "definitely_not_a_real_model.mlmodel")
        )
        with pytest.raises(KrakenUnavailable) as info:
            await extract_with_confidence(b"png-bytes", "image/png")
        assert "model" in str(info.value).lower()


class TestKrakenModelPathResolution:
    def test_env_var_overrides_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from waraq.ocr.kraken import _resolve_model_path

        monkeypatch.setenv("KRAKEN_MODEL_PATH", "/some/custom/path.mlmodel")
        assert _resolve_model_path() == "/some/custom/path.mlmodel"

    def test_default_is_arabic_best_in_cwd(
        self,
        monkeypatch: pytest.MonkeyPatch,
        clear_kraken_model_env: None,
    ) -> None:
        from waraq.ocr.kraken import _resolve_model_path

        assert _resolve_model_path() == "arabic_best.mlmodel"


# ---------------------------------------------------------------------
# Three-engine error path — every engine fails
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestThreeEngineAllFail:
    async def test_all_three_failures_register_engine_error(self) -> None:
        async def gemini_raises(_image: bytes, _mime: str) -> str:
            raise RuntimeError("gemini boom")

        async def cv_raises(_image: bytes, _mime: str) -> OpenAiOcrResult:
            raise RuntimeError("cv boom")

        async def kraken_raises(_image: bytes, _mime: str) -> KrakenResult:
            raise KrakenUnavailable("kraken boom")

        result = await run_engines(
            image_bytes=b"img",
            mime_type="image/png",
            block_class=BlockClass.MAIN_TEXT,
            gemini_fn=gemini_raises,
            openai_ocr_fn=cv_raises,
            kraken_fn=kraken_raises,
            use_kraken=True,
        )

        assert result.agreement == AGREEMENT_ENGINE_ERROR
        assert result.primary_text == ""
        assert result.aggregated_confidence is None
        assert len(result.engines) == 3
        assert all(r.error_class is not None for r in result.engines)


# Used in module scope to silence unused-import lint; the symbol
# re-exports the public `os` shadow some test environments need.
_ = os
