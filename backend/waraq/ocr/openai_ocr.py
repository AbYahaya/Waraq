"""OpenAI-backed OCR adapter for Stage-2 OCR consensus.

Acts as the second OCR engine alongside Gemini in the page runner.
Returns extracted text plus an optional confidence signal. OpenAI's
vision OCR path does not currently expose a calibrated confidence the way
Cloud Vision did, so `confidence` is `None` for now; the rest of the
consensus + Stage-3 pipeline remains intact.
"""

from __future__ import annotations

import asyncio
import base64
import os
from dataclasses import dataclass

from waraq.ocr.exceptions import OcrError
from waraq.ocr.postprocess import sanitize_ocr_output


class OpenAiOcrApiError(OcrError):
    """Wrap OpenAI SDK errors in the canonical OCR error family."""

    def __init__(self, *, cause: BaseException) -> None:
        super().__init__(f"OpenAI OCR call failed: {cause!r}")
        self.cause = cause


class MissingOpenAiOcrApiKey(OcrError):
    """Raised when `OPENAI_API_KEY` is absent."""

    def __init__(self) -> None:
        super().__init__(
            "OpenAI OCR API key not found. Set OPENAI_API_KEY to enable "
            "OpenAI OCR as the secondary OCR engine."
        )


@dataclass(frozen=True, kw_only=True, slots=True)
class OpenAiOcrResult:
    text: str
    confidence: float | None


_OCR_PROMPT = (
    "You are an OCR engine for classical Arabic Islamic texts. "
    "Extract every visible character from this page image exactly as laid out on the page. "
    "Preserve the visible reading structure: keep each printed line on its own output line, "
    "preserve paragraph breaks, preserve intentionally blank separator lines, "
    "and keep page numbers and running headers exactly as they appear instead of explaining them. "
    "Preserve the numeral glyph system exactly as printed: never convert Western digits to Arabic-Indic digits or vice versa. "
    "Do not reflow, justify, summarize, normalize, or complete lines to the page width. "
    "Return only the extracted text, with no commentary and no markdown."
)


def _mime_to_data_url(image_bytes: bytes, mime_type: str) -> str:
    payload = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{payload}"


async def extract_with_confidence(
    image_bytes: bytes, mime_type: str = "image/png"
) -> OpenAiOcrResult:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise MissingOpenAiOcrApiKey()

    from openai import AsyncOpenAI

    timeout_s = float(os.environ.get("OPENAI_HTTP_TIMEOUT", "30"))
    max_retries = int(os.environ.get("OPENAI_MAX_RETRIES", "1"))
    model = os.environ.get("OPENAI_OCR_MODEL", "gpt-4o")
    client = AsyncOpenAI(api_key=api_key, timeout=timeout_s, max_retries=max_retries)

    data_url = _mime_to_data_url(image_bytes, mime_type)

    try:
        resp = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _OCR_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Perform OCR on this page image."},
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            },
                        ],
                    },
                ],
                temperature=0,
            ),
            timeout=timeout_s,
        )
    except Exception as exc:
        raise OpenAiOcrApiError(cause=exc) from exc

    text = sanitize_ocr_output((resp.choices[0].message.content or "").strip())
    return OpenAiOcrResult(text=text, confidence=None)


async def extract_text(image_bytes: bytes, mime_type: str = "image/png") -> str:
    result = await extract_with_confidence(image_bytes, mime_type)
    return result.text


__all__ = [
    "MissingOpenAiOcrApiKey",
    "OpenAiOcrApiError",
    "OpenAiOcrResult",
    "extract_text",
    "extract_with_confidence",
]
