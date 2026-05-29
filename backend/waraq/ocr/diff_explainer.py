"""OpenAI-backed OCR difference explanation.

This is intentionally a reviewer aid, not the source of truth for OCR
edits. The UI already shows a deterministic inline diff; this layer adds a
language-aware explanation for Arabic character differences so a reviewer can
understand why two OCR engines disagree.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

_TIMEOUT_S = 20.0


class OcrDifferenceExplainerUnconfigured(RuntimeError):
    """Raised when the OpenAI-backed explainer is requested without a key."""


class OcrDifferenceExplainerError(RuntimeError):
    """Raised when the model call or response normalization fails."""


_SYSTEM_PROMPT = (
    "You are an expert Arabic OCR reviewer. Gemini is the primary OCR "
    "reading and OpenAI is the comparison reading. Compare OpenAI against "
    "Gemini line by line, preserving line order. Explain how OpenAI differs "
    "from Gemini, including Arabic letter shape, dot, hamza, alif/ya/ta "
    "marbuta, diacritic, whitespace, joining, and punctuation issues when "
    "relevant. Output STRICT JSON only with these keys: summary (string), "
    "recommended_reading (string), confidence (number 0..1), "
    "normalization_notes (array of strings), line_differences (array of "
    "objects with line_number, gemini_line, openai_line, differences), "
    "character_differences (array of objects with gemini, openai, "
    "explanation, severity). Do not invent manuscript context; say when "
    "the evidence is insufficient."
)


def _extract_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last > first:
            text = text[first : last + 1]
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OcrDifferenceExplainerError(f"OpenAI returned non-JSON output: {exc}") from exc
    if not isinstance(obj, dict):
        raise OcrDifferenceExplainerError("OpenAI returned JSON, but not an object.")
    return obj


def _coerce_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _coerce_character_differences(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, str]] = []
    for raw in value[:12]:
        if not isinstance(raw, dict):
            continue
        items.append(
            {
                "gemini": str(raw.get("gemini") or raw.get("current") or ""),
                "openai": str(raw.get("openai") or raw.get("alternative") or ""),
                "explanation": str(raw.get("explanation") or ""),
                "severity": str(raw.get("severity") or "note"),
            }
        )
    return items


def _coerce_line_differences(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, Any]] = []
    for raw in value[:24]:
        if not isinstance(raw, dict):
            continue
        try:
            line_number = int(raw.get("line_number", len(items) + 1))
        except (TypeError, ValueError):
            line_number = len(items) + 1
        items.append(
            {
                "line_number": line_number,
                "gemini_line": str(raw.get("gemini_line") or ""),
                "openai_line": str(raw.get("openai_line") or ""),
                "differences": _coerce_string_list(raw.get("differences")),
            }
        )
    return items


async def explain_ocr_difference_with_openai(
    *,
    gemini_text: str,
    openai_text: str,
    model: str | None = None,
) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise OcrDifferenceExplainerUnconfigured(
            "OPENAI_API_KEY not set; cannot explain OCR differences."
        )

    chosen_model = model or os.environ.get("OPENAI_OCR_DIFF_MODEL", "gpt-4o")
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=api_key,
        timeout=_TIMEOUT_S,
        max_retries=int(os.environ.get("OPENAI_MAX_RETRIES", "1")),
    )
    payload = {
        "primary_engine": "gemini",
        "primary_text": gemini_text,
        "comparison_engine": "openai",
        "comparison_text": openai_text,
    }
    try:
        resp = await asyncio.wait_for(
            client.chat.completions.create(
                model=chosen_model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    },
                ],
                temperature=0,
            ),
            timeout=_TIMEOUT_S,
        )
    except Exception as exc:  # pragma: no cover - network/provider path
        raise OcrDifferenceExplainerError(str(exc)) from exc

    raw = (resp.choices[0].message.content or "").strip()
    obj = _extract_json(raw)
    try:
        confidence = float(obj.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5

    return {
        "provider": "openai",
        "model": chosen_model,
        "summary": str(obj.get("summary") or "No summary returned."),
        "recommended_reading": str(obj.get("recommended_reading") or ""),
        "confidence": max(0.0, min(1.0, confidence)),
        "normalization_notes": _coerce_string_list(obj.get("normalization_notes")),
        "line_differences": _coerce_line_differences(obj.get("line_differences")),
        "character_differences": _coerce_character_differences(
            obj.get("character_differences")
        ),
    }
