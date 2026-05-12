"""§3.3 — kraken OCR adapter for manuscripts / calligraphy.

Sister to `waraq.ocr.cloud_vision` and `waraq.ocr.gemini`. Wraps the
kraken OCR engine — the canonical v1.0 reading line for **handwritten /
historical / calligraphic** Arabic scripts that Gemini-Vision and
Cloud Vision DOCUMENT_TEXT_DETECTION reliably fail on.

Routing
-------
Per §3.3 canon row "kraken + eScriptorium … Lower priority if no
manuscript material" and the Phase 4 row "gate behind project-flag",
kraken does NOT run by default. The routing layer (`waraq.ocr.routing`)
accepts a `use_kraken` flag — when True, kraken is added to the
eligible engine set for MAIN_TEXT / HEADING / FOOTNOTE / HADITH /
MARGINALIA. QURAN is excluded: Qurʾān script is canonically printed,
and a manuscript-oriented model would degrade rather than help.

eScriptorium (the Django web frontend over kraken) is deliberately
out of scope per the project owner. v1.0 uses kraken's Python API
directly; the human-correction loop is the existing OCR-Review UI.

Authentication / installation
-----------------------------
Two requirements before kraken produces signal:

  1. `pip install kraken` in the active venv. Lazy-imported here so
     hosts without the package stay importable.
  2. A recognition model on disk. Path comes from the
     `KRAKEN_MODEL_PATH` env var (defaults to `arabic_best.mlmodel`
     in the CWD, the OpenITI convention).

When either is missing, `extract_with_confidence` raises
`KrakenUnavailable` — the consensus driver's `_safe` wrapper converts
to a graceful `error_class` verdict, and the OCR pass continues with
whatever other engines ran. This mirrors the CAMeL / cv2 / openai
graceful-degradation pattern used throughout the codebase.

Confidence
----------
kraken returns per-character confidences on each prediction. We
return the arithmetic mean as the page-level confidence, mirroring
the Cloud Vision aggregation convention. None when the model
surfaces no confidence signal.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from waraq.ocr.exceptions import OcrError


class KrakenUnavailable(OcrError):
    """Raised when kraken cannot run on this host. Three reasons:

      - The `kraken` Python package isn't installed in this venv.
      - The recognition model file isn't reachable on disk.
      - The kraken SDK raised during model load.

    Surface the cause via `__cause__` so the diagnostics endpoint can
    show the user exactly what to fix (install package vs. download
    model vs. fix path)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class KrakenRecognitionError(OcrError):
    """Raised when the kraken SDK is installed and the model loaded,
    but the recognition pass itself raised. Wraps any kraken-internal
    exception with the cause attached so `profile_exception` can
    route into F-01..F-09 the same way it does for Gemini errors."""

    def __init__(self, *, cause: BaseException) -> None:
        super().__init__(f"kraken recognition failed: {cause!r}")
        self.cause = cause


@dataclass(frozen=True, kw_only=True, slots=True)
class KrakenResult:
    """Per-call output of the kraken adapter.

    `confidence` is the arithmetic mean of per-character confidences
    across all predicted lines, or None when kraken surfaced no
    confidence signal. The consensus driver passes this through as
    the engine's per-block score."""

    text: str
    confidence: float | None


def _resolve_model_path() -> str:
    """Resolve which kraken recognition model to load.

    Source order:
      1. `KRAKEN_MODEL_PATH` env var — explicit override.
      2. `arabic_best.mlmodel` in the current working directory —
         the OpenITI / kraken-doc convention.

    The path may or may not exist on disk; existence is checked in
    `extract_with_confidence` so the error message can be specific.
    """
    return os.environ.get("KRAKEN_MODEL_PATH", "arabic_best.mlmodel")


def is_available() -> bool:
    """Lightweight presence check — used by `/diagnostics/environment`
    to colour a UI pill. Returns True iff the kraken package imports
    AND the configured model file exists on disk.

    Does NOT load the model (which is the expensive part of a real
    recognition run) — just verifies the two preconditions.
    """
    try:
        import kraken  # noqa: F401
    except ImportError:
        return False
    model_path = _resolve_model_path()
    return os.path.isfile(model_path)


async def extract_with_confidence(
    image_bytes: bytes, mime_type: str = "image/png"
) -> KrakenResult:
    """Run kraken segmentation + recognition on `image_bytes` and return
    text + averaged confidence.

    Args:
        image_bytes: Raw bytes of the page image (PNG/JPEG/TIFF).
        mime_type: Advisory; PIL sniffs the format from the bytes.

    Raises:
        KrakenUnavailable: when the kraken package or model is missing.
        KrakenRecognitionError: wraps any other SDK exception.
    """
    _ = mime_type  # PIL sniffs the format from the bytes.

    def _call_sync() -> KrakenResult:
        # Lazy imports — keep hosts without kraken (and tests that
        # never reach the adapter) importable.
        try:
            from io import BytesIO

            from PIL import Image
        except ImportError as exc:
            raise KrakenUnavailable(
                "Pillow (PIL) not installed — kraken adapter needs it for image I/O. "
                "Install via `pip install Pillow`."
            ) from exc

        try:
            from kraken import binarization, pageseg, rpred
            from kraken.lib import models
        except ImportError as exc:
            raise KrakenUnavailable(
                "kraken not installed in this venv. "
                "Install via `pip install kraken` and download a recognition "
                "model (e.g. `kraken get arabic_best`)."
            ) from exc

        model_path = _resolve_model_path()
        if not os.path.isfile(model_path):
            raise KrakenUnavailable(
                f"kraken recognition model not found at {model_path!r}. "
                "Set KRAKEN_MODEL_PATH to the model file, or download "
                "`kraken get arabic_best` into the working directory."
            )

        try:
            model = models.load_any(model_path)
        except Exception as exc:
            raise KrakenUnavailable(
                f"kraken model load failed for {model_path!r}: {exc!r}"
            ) from exc

        try:
            im = Image.open(BytesIO(image_bytes))
            im.load()  # force decode before passing on
        except Exception as exc:
            raise KrakenRecognitionError(cause=exc) from exc

        try:
            # Modern kraken expects a binarized PIL image for the
            # legacy segmenter; nlbin returns a binarized PIL.Image.
            bw = binarization.nlbin(im)
            segmentation = pageseg.segment(bw)
            predictions = list(rpred.rpred(model, im, segmentation))
        except Exception as exc:
            raise KrakenRecognitionError(cause=exc) from exc

        # Stitch line predictions in reading order. kraken emits one
        # `ocr_record`-shaped object per line; the `.prediction` field
        # (string) is the recognised text. Older kraken versions used
        # `.prediction` as a property; very old ones used `str(p)`.
        line_texts: list[str] = []
        all_confidences: list[float] = []
        for p in predictions:
            text_attr = getattr(p, "prediction", None)
            line_text = text_attr if isinstance(text_attr, str) else str(p)
            line_texts.append(line_text)
            conf_attr = getattr(p, "confidences", None)
            if conf_attr:
                for c in conf_attr:
                    try:
                        all_confidences.append(float(c))
                    except (TypeError, ValueError):
                        continue

        text = "\n".join(t for t in line_texts if t).strip()
        confidence = (
            sum(all_confidences) / len(all_confidences) if all_confidences else None
        )
        return KrakenResult(text=text, confidence=confidence)

    return await asyncio.to_thread(_call_sync)


async def extract_text(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """`TextExtractor`-shaped wrapper that drops the confidence signal.

    Useful when a caller wants to drive kraken through the same
    interface as `gemini.extract_text` (e.g. for a one-engine pass on
    a manuscript-only project flag).
    """
    result = await extract_with_confidence(image_bytes, mime_type)
    return result.text


__all__ = [
    "KrakenRecognitionError",
    "KrakenResult",
    "KrakenUnavailable",
    "extract_text",
    "extract_with_confidence",
    "is_available",
]
