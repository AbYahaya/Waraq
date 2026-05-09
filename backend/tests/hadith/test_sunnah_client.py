"""Phase 2C — sunnah.com client tests (no network)."""

from __future__ import annotations

import pytest

from waraq.external import ModelUClassA, ModelURequestProfile
from waraq.hadith import SunnahApiKeyMissing, fetch_hadith
from waraq.hadith.sunnah import _parse_hadith_payload

_FAST_PROFILE = ModelURequestProfile(
    timeout_seconds=1.0,
    max_retries=2,
    retry_delay_seconds=0.0,
    inter_request_pause_seconds=0.0,
)


def _bukhari_1_payload() -> dict[str, object]:
    return {
        "collection": "bukhari",
        "bookNumber": "1",
        "chapterId": "1",
        "hadithNumber": "1",
        "hadithEnglish": "Actions are by intentions...",
        "hadithArabic": "إنما الأعمال بالنيات",
        "grades": [
            {"grade": "Sahih", "graded_by": "Bukhari"},
            {"grade": "Sahih", "graded_by": "Muslim"},
        ],
    }


@pytest.mark.asyncio
class TestFetchHadith:
    async def test_happy_path(self) -> None:
        captured: list[tuple[str, dict[str, str] | None]] = []

        async def stub(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            captured.append((url, headers))
            return _bukhari_1_payload()

        h = await fetch_hadith(
            collection="bukhari",
            hadith_number=1,
            api_key="test-key",
            profile=_FAST_PROFILE,
            fetcher=stub,
        )
        assert h.collection == "bukhari"
        assert h.hadith_number == 1
        assert h.matn_arabic.startswith("إنما الأعمال")
        assert h.matn_english.startswith("Actions are by intentions")
        assert h.book_number == 1
        assert h.chapter_id == 1
        assert len(h.grades) == 2
        assert h.grades[0]["grade"] == "Sahih"
        # URL canonical + auth header passed.
        url, headers = captured[0]
        assert url.endswith("/hadiths/bukhari/1")
        assert headers is not None
        assert headers.get("X-API-Key") == "test-key"

    async def test_missing_api_key_raises(self) -> None:
        async def stub(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            raise AssertionError("must not call upstream when key is missing")

        with pytest.raises(SunnahApiKeyMissing, match="SUNNAH_COM_API_KEY not set"):
            await fetch_hadith(
                collection="bukhari",
                hadith_number=1,
                api_key="",
                profile=_FAST_PROFILE,
                fetcher=stub,
            )

    async def test_missing_collection_rejected(self) -> None:
        async def stub(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            raise AssertionError("must not call upstream")

        with pytest.raises(ValueError, match="collection name required"):
            await fetch_hadith(
                collection="",
                hadith_number=1,
                api_key="key",
                profile=_FAST_PROFILE,
                fetcher=stub,
            )

    async def test_response_collection_mismatch_rejected(self) -> None:
        async def wrong_coll(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            payload = _bukhari_1_payload()
            payload["collection"] = "muslim"
            return payload

        with pytest.raises(ValueError, match="doesn't match"):
            await fetch_hadith(
                collection="bukhari",
                hadith_number=1,
                api_key="key",
                profile=_FAST_PROFILE,
                fetcher=wrong_coll,
            )

    async def test_class_a_propagates_no_retry(self) -> None:
        """SUNNAH_COM_API_KEY invalid → 401 → ModelUClassA → no retry."""
        calls = {"n": 0}

        async def auth_fail(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            calls["n"] += 1
            raise ModelUClassA("auth failure 401")

        with pytest.raises(ModelUClassA, match="401"):
            await fetch_hadith(
                collection="bukhari",
                hadith_number=1,
                api_key="bad-key",
                profile=_FAST_PROFILE,
                fetcher=auth_fail,
            )
        assert calls["n"] == 1


class TestParser:
    def test_grades_filtered_to_dicts(self) -> None:
        payload = _bukhari_1_payload()
        # Sneak a non-dict in.
        payload["grades"] = [
            {"grade": "Sahih", "graded_by": "Bukhari"},
            "string-not-a-dict",
            42,
            {"grade": "Hasan", "graded_by": "Tirmidhi"},
        ]
        h = _parse_hadith_payload(payload, expected_collection="bukhari")
        assert len(h.grades) == 2  # only the two dicts survive

    def test_optional_book_chapter_handled(self) -> None:
        payload = _bukhari_1_payload()
        payload["bookNumber"] = ""
        payload["chapterId"] = None
        h = _parse_hadith_payload(payload, expected_collection="bukhari")
        assert h.book_number is None
        assert h.chapter_id is None
