"""T-4.1.1 — Gemini Vision OCR wrapper.

Thin async wrapper around the google-genai SDK. Single entrypoint:
`extract_text(image_bytes, mime_type)`.

The OCR prompt is intentionally narrow ("return only the extracted text, no
commentary, no descriptions") so callers get back a string they can hand
straight to `create_revision` (T-4.1.2). Anything richer — error-class
profiling, confidence scores, multi-engine consensus — belongs in T-4.1.3
or later in the OCR pipeline (Sprint-OCR).

Per Dokument 1 §3.3, Gemini is the OCR main reading line; the model name is
configurable via Settings.gemini_ocr_model. Free-tier rate limits matter
during development — the OCR service exposes an injectable extractor so
tests don't burn quota.
"""

from __future__ import annotations

import asyncio
import os

from waraq.db.session import get_settings
from waraq.ocr.exceptions import GeminiApiError, MissingGeminiApiKey
from waraq.ocr.postprocess import sanitize_ocr_output

_OCR_PROMPT = (
    "You are an OCR engine for classical Arabic Islamic texts. "
    "Extract every visible character from this page image exactly as laid out on the page. "
    "Preserve the visible reading structure: keep each printed line on its own output line, "
    "preserve paragraph breaks, preserve intentionally blank separator lines, "
    "and keep page numbers and running headers exactly as they appear instead of explaining them. "
    "Preserve the numeral glyph system exactly as printed: never convert Western digits to Arabic-Indic digits or vice versa. "
    "Do not reflow, justify, summarize, normalize, or complete lines to the page width. "
    "Return only the extracted text — no descriptions, no commentary, no markdown."
)


def _is_rate_limit_error(exc: BaseException) -> bool:
    haystack = f"{exc!s} {exc!r} {type(exc).__name__}".lower()
    return any(
        token in haystack
        for token in ("429", "rate limit", "resourceexhausted", "resource_exhausted", "quota")
    )


async def extract_text(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """Send an image to Gemini Vision and return the extracted text.

    Args:
        image_bytes: Raw bytes of the page image (PNG, JPEG, WEBP supported).
        mime_type: Content type hint for the API.

    Returns:
        The extracted text, stripped of leading/trailing whitespace.

    Raises:
        MissingGeminiApiKey: if GOOGLE_AI_API_KEY isn't configured.
        GeminiApiError: wraps any underlying API exception with the model
            name and cause attached.
    """
    settings = get_settings()
    if not settings.google_ai_api_key:
        raise MissingGeminiApiKey()

    # Lazy import so the SDK isn't loaded for tests that pass an injected
    # extractor (most of them) and so import-time errors don't break the
    # whole module if the SDK is missing in some environment.
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.google_ai_api_key)

    def _call_sync() -> str:
        response = client.models.generate_content(
            model=settings.gemini_ocr_model,
            contents=[  # type: ignore[arg-type]
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                _OCR_PROMPT,
            ],
        )
        return sanitize_ocr_output((response.text or "").strip())

    max_attempts = max(1, int(os.environ.get("GEMINI_OCR_MAX_ATTEMPTS", "3")))
    backoff_s = float(os.environ.get("GEMINI_OCR_RETRY_BACKOFF_SECONDS", "2"))
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await asyncio.to_thread(_call_sync)
        except Exception as exc:
            last_exc = exc
            if attempt >= max_attempts or not _is_rate_limit_error(exc):
                raise GeminiApiError(model=settings.gemini_ocr_model, cause=exc) from exc
            await asyncio.sleep(backoff_s * attempt)

    assert last_exc is not None
    raise GeminiApiError(model=settings.gemini_ocr_model, cause=last_exc)
