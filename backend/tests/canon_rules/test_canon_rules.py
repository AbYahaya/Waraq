"""Unit tests for the §2.2 mandatory product-logic enforcers."""

from __future__ import annotations

import pytest

from waraq.canon_rules import (
    apply_all,
    enforce_ei2_transliteration,
    has_arabic_indic_digits,
    normalize_religious_formulas,
    to_western_digits,
)
from waraq.canon_rules.religious_formulas import (
    JALLA_JALALUHU,
    SALLA_ALLAHU_ALAYHI_WA_SALLAM,
)

# --- Western digits ------------------------------------------------------


class TestDigitGuard:
    def test_arabic_indic_digits_converted(self) -> None:
        assert to_western_digits("سنة ١٤٤٦") == "سنة 1446"

    def test_eastern_arabic_indic_digits_converted(self) -> None:
        # U+06F0..U+06F9 are Persian/Urdu digits
        assert to_western_digits("سال ۱۴۴۶") == "سال 1446"

    def test_mixed_digit_ranges(self) -> None:
        assert to_western_digits("١٢٣۴۵۶") == "123456"

    def test_no_digits_passthrough(self) -> None:
        assert to_western_digits("بسم الله") == "بسم الله"

    def test_already_western_passthrough(self) -> None:
        assert to_western_digits("page 42") == "page 42"

    def test_idempotent(self) -> None:
        text = "Verse ١:٧"
        once = to_western_digits(text)
        twice = to_western_digits(once)
        assert once == twice == "Verse 1:7"

    def test_empty_string(self) -> None:
        assert to_western_digits("") == ""

    def test_has_arabic_indic_digits_positive(self) -> None:
        assert has_arabic_indic_digits("page ١") is True
        assert has_arabic_indic_digits("page ۱") is True

    def test_has_arabic_indic_digits_negative(self) -> None:
        assert has_arabic_indic_digits("page 42") is False
        assert has_arabic_indic_digits("بسم الله") is False
        assert has_arabic_indic_digits("") is False


# --- EI2 transliteration -------------------------------------------------


class TestEi2Transliteration:
    def test_capital_k_dot_below_to_q(self) -> None:
        assert enforce_ei2_transliteration("Ḳurʾān") == "Qurʾān"

    def test_lowercase_k_dot_below_to_q(self) -> None:
        assert enforce_ei2_transliteration("muḳaddima") == "muqaddima"

    def test_dj_uppercase(self) -> None:
        assert enforce_ei2_transliteration("Djinni") == "Jinni"

    def test_dj_lowercase(self) -> None:
        assert enforce_ei2_transliteration("madjlis") == "majlis"

    def test_dj_all_caps(self) -> None:
        assert enforce_ei2_transliteration("DJINNI") == "JINNI"

    def test_combined_substitutions(self) -> None:
        assert enforce_ei2_transliteration("Ḳāḍī al-Djurdjānī") == "Qāḍī al-Jurjānī"

    def test_idempotent(self) -> None:
        text = "Ḳurʾān, Djinn"
        once = enforce_ei2_transliteration(text)
        assert enforce_ei2_transliteration(once) == once

    def test_no_substitutions_passthrough(self) -> None:
        assert enforce_ei2_transliteration("Bismillah") == "Bismillah"


# --- Religious formulas --------------------------------------------------


class TestReligiousFormulas:
    def test_bare_consonantal_saw_to_glyph(self) -> None:
        out = normalize_religious_formulas("الرسول صلى الله عليه وسلم قال")
        assert SALLA_ALLAHU_ALAYHI_WA_SALLAM in out
        assert "صلى الله عليه وسلم" not in out

    def test_vocalized_saw_to_glyph(self) -> None:
        out = normalize_religious_formulas("النبي صَلَّى اللهُ عَلَيْهِ وَسَلَّمَ")
        assert SALLA_ALLAHU_ALAYHI_WA_SALLAM in out

    def test_jalla_jalaluhu_to_glyph(self) -> None:
        out = normalize_religious_formulas("الله جل جلاله")
        assert JALLA_JALALUHU in out
        assert "جل جلاله" not in out

    def test_glyph_passthrough_idempotent(self) -> None:
        text = f"الرسول {SALLA_ALLAHU_ALAYHI_WA_SALLAM} قال"
        assert normalize_religious_formulas(text) == text

    def test_no_formulas_passthrough(self) -> None:
        assert normalize_religious_formulas("بسم الله الرحمن الرحيم") == "بسم الله الرحمن الرحيم"

    def test_idempotent(self) -> None:
        text = "صلى الله عليه وسلم"
        once = normalize_religious_formulas(text)
        twice = normalize_religious_formulas(once)
        assert once == twice


# --- apply_all integration -----------------------------------------------


class TestApplyAll:
    def test_combined_rules_applied(self) -> None:
        text = "صلى الله عليه وسلم — Year ١٤٤٦ — Ḳurʾān"
        out = apply_all(text)
        assert SALLA_ALLAHU_ALAYHI_WA_SALLAM in out
        assert "1446" in out
        assert "Qurʾān" in out
        # And no Arabic-Indic digits remain.
        assert not has_arabic_indic_digits(out)

    def test_idempotent(self) -> None:
        text = "Page ١, Djinni, صلى الله عليه وسلم"
        once = apply_all(text)
        twice = apply_all(once)
        assert once == twice

    def test_empty(self) -> None:
        assert apply_all("") == ""


# --- Translator integration ---------------------------------------------


@pytest.mark.asyncio
class TestTranslatorIntegration:
    async def test_translator_post_processes_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The OpenAI translator factory must apply canon rules to output.
        We monkeypatch the OpenAI client so no real API call is made."""
        from waraq.translation import openai_translator
        from waraq.translation.service import TranslationContext

        class _StubChoice:
            def __init__(self, content: str) -> None:
                self.message = type("M", (), {"content": content})()

        class _StubResponse:
            def __init__(self, content: str) -> None:
                self.choices = [_StubChoice(content)]

        class _StubChat:
            class completions:
                @staticmethod
                async def create(**_kw: object) -> _StubResponse:
                    # Return text containing every canon-rule violation.
                    return _StubResponse("[[L0001]] Sure ١٤٤٦ Ḳurʾān صلى الله عليه وسلم")

        class _StubClient:
            chat = _StubChat()

        monkeypatch.setenv("OPENAI_API_KEY", "stub")
        monkeypatch.setattr(
            openai_translator, "AsyncOpenAI", lambda **_: _StubClient(), raising=False
        )
        # The factory imports AsyncOpenAI lazily; patch the module attr too.
        import openai

        monkeypatch.setattr(openai, "AsyncOpenAI", lambda **_: _StubClient())

        translator = openai_translator.make_openai_translator()
        out = await translator("dummy source", TranslationContext())
        # Western digits applied
        assert "1446" in out
        assert not has_arabic_indic_digits(out)
        # EI2 transliteration applied
        assert "Qurʾān" in out
        assert "Ḳ" not in out
        # Religious formula normalized
        assert SALLA_ALLAHU_ALAYHI_WA_SALLAM in out
