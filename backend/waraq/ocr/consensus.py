"""§3.4 / §3.6 — two-engine OCR driver (sub-batch C).

Runs the engines selected by Stage-2 `routing.engines_for(block_class)`
in parallel via `asyncio.gather`, captures both texts + confidences,
and emits a coarse `engine_agreement` classification.

Agreement classes (the v1.0 vocabulary; sub-batch D's full Stage-3
three-track consensus replaces this with a richer label set):

  - `single_engine`   only one engine ran (e.g. QURAN routing).
  - `exact_match`     both engines returned identical text after
                      whitespace-collapse (NFC + collapse runs of
                      whitespace).
  - `skeleton_equal`  texts differ at the diacritic / Tatweel /
                      Alif-variant level only — the OCR-stage
                      `to_skeleton` reduction (§4.15.2) is equal.
  - `divergent`       texts differ at the skeletal-letter level.
  - `engine_error`    at least one engine raised; the surviving
                      engine's text becomes the primary.

Confidence aggregation (the v1.0 rule; sub-batch D refines):

  - Single engine → engine's reported confidence (often None: Gemini
    does not surface one).
  - Multi engine + agreement (exact / skeleton) → arithmetic mean of
    the engines that DID report a confidence (None when all are None).
  - Multi engine + divergent → the lower of the two reported
    confidences (or None when neither does). Divergence is by
    construction less trustworthy than either engine alone.
  - engine_error → confidence of the surviving engine (or None).

The driver is engine-injectable: tests pass stub callables, production
uses `gemini.extract_text` and `openai_ocr.extract_with_confidence`.
"""

from __future__ import annotations

import asyncio
import re
import unicodedata
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from waraq.arabic import to_skeleton
from waraq.ocr.routing import OcrEngine, engines_for, primary_engine
from waraq.schemas.enums import BlockClass

# Engine callable types matching the existing `gemini.extract_text` and
# `openai_ocr.extract_with_confidence` signatures.
GeminiExtractor = Callable[[bytes, str], Awaitable[str]]
# OpenAI OCR returns an `OpenAiOcrResult` with text + confidence;
# we accept the broader Awaitable[Any] in test injection so a fake can
# return a small dataclass-shaped namespace without importing the real
# OpenAiOcrResult.
from waraq.ocr.openai_ocr import OpenAiOcrResult  # noqa: E402

OpenAiOcrExtractor = Callable[[bytes, str], Awaitable[OpenAiOcrResult]]


# Agreement-class string constants — wire-stable, persisted on OCR-PO.
AGREEMENT_SINGLE_ENGINE = "single_engine"
AGREEMENT_EXACT_MATCH = "exact_match"
AGREEMENT_SKELETON_EQUAL = "skeleton_equal"
AGREEMENT_DIVERGENT = "divergent"
AGREEMENT_ENGINE_ERROR = "engine_error"


_WHITESPACE_RUN = re.compile(r"\s+")


def _normalize_for_exact(text: str) -> str:
    """NFC + whitespace-collapse. The exact_match check is *near*-exact
    rather than byte-exact because OCR engines disagree harmlessly on
    line-break placement — collapsing runs of whitespace lets us catch
    the agreement that actually matters semantically."""
    return _WHITESPACE_RUN.sub(" ", unicodedata.normalize("NFC", text)).strip()


@dataclass(frozen=True, kw_only=True, slots=True)
class EngineResult:
    """Result of running one engine on one block image. Persisted on
    the OCR-PO `engines[*]` payload field — JSON-serializable."""

    engine: OcrEngine
    text: str
    confidence: float | None
    error_class: str | None = None  # `type(exc).__name__` when engine raised


@dataclass(frozen=True, kw_only=True, slots=True)
class ConsensusResult:
    """Output of the two-engine driver. The page-runner picks
    `primary_text` for the `run_ocr_job` extractor and forwards
    `engines` + `agreement` + `aggregated_confidence` onto the
    OCR-PO payload."""

    primary_text: str
    primary_engine_used: OcrEngine
    engines: tuple[EngineResult, ...]
    agreement: str
    aggregated_confidence: float | None


async def _run_one_gemini(fn: GeminiExtractor, image_bytes: bytes, mime_type: str) -> EngineResult:
    try:
        text = await fn(image_bytes, mime_type)
        return EngineResult(engine=OcrEngine.GEMINI, text=text, confidence=None)
    except Exception as exc:
        return EngineResult(
            engine=OcrEngine.GEMINI,
            text="",
            confidence=None,
            error_class=type(exc).__name__,
        )


async def _run_one_openai(
    fn: OpenAiOcrExtractor, image_bytes: bytes, mime_type: str
) -> EngineResult:
    try:
        result = await fn(image_bytes, mime_type)
        return EngineResult(
            engine=OcrEngine.OPENAI,
            text=result.text,
            confidence=result.confidence,
        )
    except Exception as exc:
        return EngineResult(
            engine=OcrEngine.OPENAI,
            text="",
            confidence=None,
            error_class=type(exc).__name__,
        )


def _classify_agreement(results: tuple[EngineResult, ...]) -> str:
    """Compute the agreement label across all engines that ran (and
    didn't error)."""
    successful = tuple(r for r in results if r.error_class is None)
    if len(successful) == 0:
        # Every engine failed — surface as engine_error; primary text
        # will be empty.
        return AGREEMENT_ENGINE_ERROR
    if len(successful) == 1:
        if any(r.error_class is not None for r in results):
            return AGREEMENT_ENGINE_ERROR
        return AGREEMENT_SINGLE_ENGINE
    # Multi-engine path (currently 2): pairwise compare the first two.
    a, b = successful[0], successful[1]
    if _normalize_for_exact(a.text) == _normalize_for_exact(b.text):
        return AGREEMENT_EXACT_MATCH
    if to_skeleton(a.text) == to_skeleton(b.text):
        return AGREEMENT_SKELETON_EQUAL
    return AGREEMENT_DIVERGENT


def _aggregate_confidence(results: tuple[EngineResult, ...], agreement: str) -> float | None:
    """Apply the v1.0 aggregation rule documented in the module
    docstring."""
    successful = [r for r in results if r.error_class is None]
    confidences = [r.confidence for r in successful if r.confidence is not None]
    if not confidences:
        return None
    if agreement in (AGREEMENT_SINGLE_ENGINE, AGREEMENT_ENGINE_ERROR):
        # The surviving engine's value (or single value when one ran).
        return confidences[0] if len(confidences) == 1 else sum(confidences) / len(confidences)
    if agreement in (AGREEMENT_EXACT_MATCH, AGREEMENT_SKELETON_EQUAL):
        return sum(confidences) / len(confidences)
    # Divergent: pessimistic — take the lower confidence.
    if len(confidences) == 1:
        return confidences[0]
    return min(confidences)


def _pick_primary_text(results: tuple[EngineResult, ...], agreement: str) -> tuple[str, OcrEngine]:
    """Pick which engine's text becomes the canonical `text` field.

    Rule: primary engine (Gemini per §3.3) wins when its result is
    successful. If primary failed, fall back to the first surviving
    engine. If all failed, return ("", primary).
    """
    primary = primary_engine()
    primary_result = next(
        (r for r in results if r.engine == primary and r.error_class is None), None
    )
    if primary_result is not None:
        _ = agreement  # reserved for sub-batch D consensus tie-breaks
        return primary_result.text, primary

    fallback = next((r for r in results if r.error_class is None), None)
    if fallback is not None:
        return fallback.text, fallback.engine
    return "", primary


async def run_engines(
    *,
    image_bytes: bytes,
    mime_type: str,
    block_class: BlockClass,
    gemini_fn: GeminiExtractor,
    openai_ocr_fn: OpenAiOcrExtractor,
) -> ConsensusResult:
    """Run the engines Stage-2 routes for `block_class` in parallel and
    return the consensus result.

    Engine callables are required (no implicit defaults) — the
    page-runner injects production extractors, tests inject stubs.
    Forcing explicit injection keeps this module decoupled from the
    Gemini / OpenAI OCR import surface and makes the test boundary
    obvious.
    """
    eligible = engines_for(block_class)

    awaitables: list[Awaitable[EngineResult]] = []
    if OcrEngine.GEMINI in eligible:
        awaitables.append(_run_one_gemini(gemini_fn, image_bytes, mime_type))
    if OcrEngine.OPENAI in eligible:
        awaitables.append(_run_one_openai(openai_ocr_fn, image_bytes, mime_type))

    results_list = await asyncio.gather(*awaitables)
    results = tuple(results_list)

    agreement = _classify_agreement(results)
    primary_text, used = _pick_primary_text(results, agreement)
    aggregated = _aggregate_confidence(results, agreement)

    return ConsensusResult(
        primary_text=primary_text,
        primary_engine_used=used,
        engines=results,
        agreement=agreement,
        aggregated_confidence=aggregated,
    )


__all__ = [
    "AGREEMENT_DIVERGENT",
    "AGREEMENT_ENGINE_ERROR",
    "AGREEMENT_EXACT_MATCH",
    "AGREEMENT_SINGLE_ENGINE",
    "AGREEMENT_SKELETON_EQUAL",
    "ConsensusResult",
    "EngineResult",
    "run_engines",
]
