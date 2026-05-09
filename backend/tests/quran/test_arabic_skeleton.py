"""Shared waraq.arabic helpers — skeleton-strip + normalize-for-compare."""

from __future__ import annotations

import unicodedata

from waraq.arabic import (
    TATWEEL,
    normalize_for_compare,
    strip_arabic_diacritics,
    to_skeleton,
)


class TestStripArabicDiacritics:
    def test_strips_basic_harakat(self) -> None:
        s = "بِسْمِ اللَّهِ"
        # Sukun, Kasra, Shadda, Fatha all stripped.
        assert strip_arabic_diacritics(s) == "بسم الله"

    def test_strips_tatweel(self) -> None:
        s = f"محمد{TATWEEL}محمد"
        assert TATWEEL not in strip_arabic_diacritics(s)

    def test_idempotent(self) -> None:
        s = "بِسْمِ اللَّهِ"
        once = strip_arabic_diacritics(s)
        twice = strip_arabic_diacritics(once)
        assert once == twice

    def test_empty_string(self) -> None:
        assert strip_arabic_diacritics("") == ""

    def test_preserves_non_arabic(self) -> None:
        s = "Hello بِسْمِ World"
        out = strip_arabic_diacritics(s)
        assert "Hello" in out and "World" in out
        assert "بسم" in out


class TestNormalizeForCompare:
    def test_nfc_idempotent(self) -> None:
        s = "بِسْم"
        assert normalize_for_compare(s) == normalize_for_compare(unicodedata.normalize("NFD", s))

    def test_strips_tatweel(self) -> None:
        s = f"محمد{TATWEEL}"
        assert TATWEEL not in normalize_for_compare(s)

    def test_preserves_diacritics(self) -> None:
        s = "بِسْمِ"
        out = normalize_for_compare(s)
        assert "ِ" in out  # Kasra preserved


class TestToSkeleton:
    def test_full_pipeline(self) -> None:
        # NFC + Tatweel + diacritics all collapsed.
        vocalized = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"
        skeleton = to_skeleton(vocalized)
        # No diacritics, no Tatweel.
        for ch in skeleton:
            cp = ord(ch)
            assert ch != TATWEEL
            assert not (0x064B <= cp <= 0x065F)

    def test_collapses_whitespace(self) -> None:
        s = "بسم   الله"
        assert to_skeleton(s) == "بسم الله"

    def test_idempotent(self) -> None:
        s = "بِسْمِ اللَّهِ"
        once = to_skeleton(s)
        twice = to_skeleton(once)
        assert once == twice
