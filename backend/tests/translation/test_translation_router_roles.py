from __future__ import annotations

import pytest
from fastapi import HTTPException

from waraq.translation.service import TranslationContext


def _translator(output: str):
    async def _run(_text: str, _ctx: TranslationContext) -> str:
        return output

    return _run


@pytest.mark.asyncio
async def test_translation_route_uses_gemini_as_primary(monkeypatch: pytest.MonkeyPatch) -> None:
    from waraq.api.routers import translation_router

    monkeypatch.setattr(
        translation_router,
        "make_gemini_translator",
        lambda: _translator("Gemini primary"),
    )
    monkeypatch.setattr(
        translation_router,
        "make_openai_translator",
        lambda: _translator("OpenAI check"),
    )

    translator, label = translation_router._build_translator_and_label()
    ctx = TranslationContext()
    output = await translator("source", ctx)  # type: ignore[operator]

    assert output == "Gemini primary"
    assert label == "google/gemini-2.5-pro+openai/gpt-4o"
    assert ctx.cross_check.primary_engine == "google/gemini-2.5-pro"
    assert ctx.cross_check.check_engine == "openai/gpt-4o"
    assert ctx.cross_check.primary_output == "Gemini primary"
    assert ctx.cross_check.check_output == "OpenAI check"


@pytest.mark.asyncio
async def test_translation_route_runs_gemini_only_without_openai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from waraq.api.routers import translation_router
    from waraq.translation.openai_translator import OpenAITranslatorUnconfigured

    monkeypatch.setattr(
        translation_router,
        "make_gemini_translator",
        lambda: _translator("Gemini only"),
    )

    def _missing_openai() -> object:
        raise OpenAITranslatorUnconfigured("OPENAI_API_KEY not set")

    monkeypatch.setattr(translation_router, "make_openai_translator", _missing_openai)

    translator, label = translation_router._build_translator_and_label()
    ctx = TranslationContext()
    output = await translator("source", ctx)  # type: ignore[operator]

    assert output == "Gemini only"
    assert label == "google/gemini-2.5-pro"
    assert ctx.cross_check is None


def test_translation_route_requires_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    from waraq.api.routers import translation_router
    from waraq.translation.gemini_translator import GeminiTranslatorUnconfigured

    def _missing_gemini() -> object:
        raise GeminiTranslatorUnconfigured("GOOGLE_AI_API_KEY not set")

    monkeypatch.setattr(translation_router, "make_gemini_translator", _missing_gemini)

    with pytest.raises(HTTPException) as exc:
        translation_router._build_translator_and_label()

    assert exc.value.status_code == 503
    assert "GOOGLE_AI_API_KEY" in str(exc.value.detail)
