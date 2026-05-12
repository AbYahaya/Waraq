"""Phase 4 sub-batch G — production OCR-side AI validators.

These tests cover the parser + factory error paths. They DO NOT make
live API calls — the SDK clients are stubbed at the module-attribute
level, mirroring the cloud_vision adapter test pattern.
"""

from __future__ import annotations

import pytest

from waraq.ocr.stage3_ai_production import (
    Stage3AiValidatorUnconfigured,
    _parse_response,
    make_gemini_ocr_validator,
    make_openai_ocr_validator,
)


class TestParseResponse:
    def test_clean_json_parses(self) -> None:
        parsed = _parse_response('{"confidence": 0.92, "issue": null}')
        assert parsed.confidence == pytest.approx(0.92)
        assert parsed.issue is None
        assert parsed.parse_error is None

    def test_issue_string_passes_through(self) -> None:
        parsed = _parse_response('{"confidence": 0.55, "issue": "diacritic mismatch on word 2"}')
        assert parsed.issue == "diacritic mismatch on word 2"

    def test_fenced_json_is_unwrapped(self) -> None:
        # GPT and Gemini sometimes wrap output in ```json fences.
        wrapped = '```json\n{"confidence": 0.88, "issue": null}\n```'
        parsed = _parse_response(wrapped)
        assert parsed.confidence == pytest.approx(0.88)
        assert parsed.parse_error is None

    def test_invalid_json_yields_neutral_with_error_note(self) -> None:
        parsed = _parse_response("this is not JSON at all")
        assert parsed.confidence == 0.50  # NEUTRAL
        assert parsed.parse_error is not None
        assert "json_decode_error" in parsed.parse_error

    def test_non_numeric_confidence_yields_neutral(self) -> None:
        parsed = _parse_response('{"confidence": "high", "issue": null}')
        assert parsed.confidence == 0.50
        assert parsed.parse_error is not None

    def test_confidence_clamped_above_one(self) -> None:
        parsed = _parse_response('{"confidence": 1.5, "issue": null}')
        assert parsed.confidence == 1.0

    def test_confidence_clamped_below_zero(self) -> None:
        parsed = _parse_response('{"confidence": -0.3, "issue": null}')
        assert parsed.confidence == 0.0


class TestFactoryErrors:
    def test_openai_validator_raises_when_key_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(Stage3AiValidatorUnconfigured):
            make_openai_ocr_validator()

    def test_gemini_validator_raises_when_key_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
        with pytest.raises(Stage3AiValidatorUnconfigured):
            make_gemini_ocr_validator()
