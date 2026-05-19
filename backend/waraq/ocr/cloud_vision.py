"""§3.4 Stage-2 — Google Cloud Vision OCR adapter.

Sister to `waraq.ocr.gemini`. Wraps the `document_text_detection`
endpoint and surfaces both the extracted text AND a per-page confidence
signal (Cloud Vision's `pages[*].confidence`).

The two-engine driver in `waraq.ocr.consensus` calls both Gemini and
Cloud Vision in parallel via `asyncio.gather` and feeds the §4.4
confidence taxonomy + §3.4 disagreement signal off the result.

Authentication
--------------
Uses Application Default Credentials (`GOOGLE_APPLICATION_CREDENTIALS`
env var pointing at a service-account JSON). Lazy import keeps
host environments without `google-cloud-vision` from failing at module
import time (mirrors the gemini wrapper pattern). Tests inject stub
extractors via the consensus driver and never reach this code.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from waraq.ocr.exceptions import OcrError


class CloudVisionApiError(OcrError):
    """Wraps any google-cloud-vision SDK exception with the cause attached
    so `profile_exception` can route into F-01..F-09 the same way it
    already does for Gemini errors."""

    def __init__(self, *, cause: BaseException) -> None:
        super().__init__(f"Cloud Vision call failed: {cause!r}")
        self.cause = cause


class MissingCloudVisionCredentials(OcrError):
    """Raised when the SDK cannot locate Application Default Credentials.
    The user fixes this by exporting `GOOGLE_APPLICATION_CREDENTIALS` to
    a service-account JSON path."""

    def __init__(self) -> None:
        super().__init__(
            "Cloud Vision credentials not found. "
            "Set GOOGLE_APPLICATION_CREDENTIALS to a service-account JSON path "
            "or pass an explicit cloud_vision_fn for tests."
        )


@dataclass(frozen=True, kw_only=True, slots=True)
class CloudVisionResult:
    """Per-call output of the Cloud Vision adapter.

    `confidence` is the arithmetic mean of `pages[*].confidence` returned
    by the API, or None when the API surfaced no confidence signal. The
    consensus driver passes this through as the engine's per-block score.
    """

    text: str
    confidence: float | None


def _detected_break_name(symbol: Any) -> str | None:
    """Best-effort extraction of Cloud Vision's break-type label.

    The SDK exposes this through protobuf-backed objects; tests use
    light fakes. Keep the reader tolerant of either shape.
    """
    prop = getattr(symbol, "property", None)
    if prop is None:
        return None
    detected_break = getattr(prop, "detected_break", None)
    if detected_break is None:
        return None
    raw = getattr(detected_break, "type_", None)
    if raw is None:
        raw = getattr(detected_break, "type", None)
    if raw is None:
        return None
    name = getattr(raw, "name", None)
    if isinstance(name, str):
        return name
    if isinstance(raw, str):
        return raw
    return str(raw)


def _reconstruct_structured_text(full: Any) -> str:
    """Rebuild text from Cloud Vision's document structure.

    `full.text` is sometimes too eager to flatten visual structure. For
    Arabic book pages we want paragraph boundaries, line endings, page
    numbers, and short running headers preserved as faithfully as the
    OCR tree allows.
    """
    pages = getattr(full, "pages", None)
    if not pages:
        return (getattr(full, "text", "") or "").strip()

    out: list[str] = []
    wrote_anything = False

    def _append(text: str) -> None:
        nonlocal wrote_anything
        if not text:
            return
        out.append(text)
        if any(not ch.isspace() for ch in text):
            wrote_anything = True

    for page in pages:
        blocks = getattr(page, "blocks", None) or []
        for block in blocks:
            paragraphs = getattr(block, "paragraphs", None) or []
            for paragraph in paragraphs:
                words = getattr(paragraph, "words", None) or []
                paragraph_start_len = len(out)
                for word in words:
                    symbols = getattr(word, "symbols", None) or []
                    if not symbols:
                        continue
                    for symbol in symbols:
                        _append(getattr(symbol, "text", "") or "")
                        break_name = _detected_break_name(symbol)
                        if break_name in {"SPACE", "SURE_SPACE", "UNKNOWN"}:
                            _append(" ")
                        elif break_name in {"EOL_SURE_SPACE", "LINE_BREAK"}:
                            _append("\n")
                        elif break_name == "HYPHEN":
                            # Soft line-wrap hyphen; don't force an extra space.
                            continue
                if len(out) > paragraph_start_len and not "".join(out).endswith("\n"):
                    _append("\n")
                if len(out) > paragraph_start_len:
                    _append("\n")

    structured = "".join(out).strip()
    if structured:
        return structured
    if wrote_anything:
        return "".join(out).strip()
    return (getattr(full, "text", "") or "").strip()


async def extract_with_confidence(
    image_bytes: bytes, mime_type: str = "image/png"
) -> CloudVisionResult:
    """Send `image_bytes` to Cloud Vision document_text_detection and
    return text + averaged page confidence.

    Args:
        image_bytes: Raw bytes of the page image (PNG/JPEG/WEBP).
        mime_type: Currently advisory; Cloud Vision auto-detects from
            bytes. Accepted to match the `TextExtractor` shape.

    Raises:
        MissingCloudVisionCredentials: when ADC cannot be resolved.
        CloudVisionApiError: wraps any other SDK exception.
    """
    _ = mime_type  # Cloud Vision sniffs the format from the bytes.

    # Lazy imports — keep tests / hosts without the SDK importable.
    from google.api_core import exceptions as gcp_exceptions
    from google.auth.exceptions import DefaultCredentialsError
    from google.cloud import vision

    def _call_sync() -> CloudVisionResult:
        try:
            client = vision.ImageAnnotatorClient()
        except DefaultCredentialsError as exc:
            raise MissingCloudVisionCredentials() from exc

        image = vision.Image(content=image_bytes)
        try:
            response = client.document_text_detection(image=image, timeout=20.0)
        except gcp_exceptions.PermissionDenied as exc:
            raise MissingCloudVisionCredentials() from exc
        except Exception as exc:
            raise CloudVisionApiError(cause=exc) from exc

        if response.error.message:
            raise CloudVisionApiError(cause=RuntimeError(response.error.message))

        full = response.full_text_annotation
        text = _reconstruct_structured_text(full) if full else ""
        confidences = [
            float(page.confidence)
            for page in (full.pages if full else [])
            if page.confidence is not None
        ]
        confidence = sum(confidences) / len(confidences) if confidences else None
        return CloudVisionResult(text=text, confidence=confidence)

    return await asyncio.to_thread(_call_sync)


async def extract_text(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """`TextExtractor`-shaped wrapper that drops the confidence signal.

    Useful when a caller wants to use Cloud Vision through the same
    interface as `gemini.extract_text` (e.g. as a one-engine fallback
    for a class that's normally Gemini-only)."""
    result = await extract_with_confidence(image_bytes, mime_type)
    return result.text


__all__ = [
    "CloudVisionApiError",
    "CloudVisionResult",
    "MissingCloudVisionCredentials",
    "extract_text",
    "extract_with_confidence",
]
