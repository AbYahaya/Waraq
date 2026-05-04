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

from waraq.db.session import get_settings
from waraq.ocr.exceptions import GeminiApiError, MissingGeminiApiKey

_OCR_PROMPT = (
    "You are an OCR engine for classical Arabic Islamic texts. "
    "Extract every visible character of the main text from this page image, "
    "preserving line breaks. "
    "Return only the extracted text — no descriptions, no commentary, no markdown."
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
        try:
            response = client.models.generate_content(
                model=settings.gemini_ocr_model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    _OCR_PROMPT,
                ],
            )
        except Exception as exc:
            raise GeminiApiError(model=settings.gemini_ocr_model, cause=exc) from exc
        return (response.text or "").strip()

    # google-genai's sync client; offload to a worker thread so we don't
    # block the event loop. The SDK has an async client too; if rate-limit
    # backoff or streaming becomes a concern, swap to client.aio later.
    return await asyncio.to_thread(_call_sync)
