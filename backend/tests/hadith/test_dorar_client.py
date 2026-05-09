"""Phase 2C — dorar.net client tests (no network).

Covers the §3.5 scraping secondary-path rule: API primary, scraping
fallback raises Class B WITHOUT retry on every invocation in v1.0
(DOM selectors not configured).
"""

from __future__ import annotations

import pytest

from waraq.external import ModelUClassB, ModelURequestProfile
from waraq.hadith import (
    DorarHadith,
    search_via_api,
    search_via_scraping_fallback,
)

_FAST_PROFILE = ModelURequestProfile(
    timeout_seconds=1.0,
    max_retries=2,
    retry_delay_seconds=0.0,
    inter_request_pause_seconds=0.0,
)


def _three_hits_payload() -> dict[str, object]:
    return {
        "data": [
            {
                "matn": "إنما الأعمال بالنيات",
                "rawi": "عمر بن الخطاب",
                "mohaddith": "البخاري",
                "book": "صحيح البخاري",
                "rakm": "1",
                "grade": "صحيح",
            },
            {
                "matn": "حديث آخر",
                "narrator": "أبو هريرة",
                "muhaddith": "مسلم",
                "kitab": "صحيح مسلم",
                "number": 7,
                "judgment": "حسن",
            },
            "this-string-should-be-skipped",
        ]
    }


# --- search_via_api -------------------------------------------------


@pytest.mark.asyncio
class TestSearchViaApi:
    async def test_happy_path_three_hits_skips_non_dict(self) -> None:
        captured: list[tuple[str, dict[str, str] | None]] = []

        async def stub(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            captured.append((url, headers))
            return _three_hits_payload()

        hits = await search_via_api(
            query="إنما الأعمال",
            base_url="https://dorar.net/dorar_api.json",
            profile=_FAST_PROFILE,
            fetcher=stub,
        )
        assert len(hits) == 2  # third entry was a non-dict, filtered
        assert isinstance(hits[0], DorarHadith)
        assert hits[0].matn.startswith("إنما الأعمال")
        assert hits[0].rawi == "عمر بن الخطاب"
        assert hits[0].grade == "صحيح"
        # Second hit uses alternate field names — parser handles both.
        assert hits[1].matn == "حديث آخر"
        assert hits[1].rawi == "أبو هريرة"
        assert hits[1].mohaddith == "مسلم"
        assert hits[1].book == "صحيح مسلم"
        assert hits[1].page_or_number == "7"
        assert hits[1].grade == "حسن"

    async def test_url_carries_query_param(self) -> None:
        captured: list[str] = []

        async def stub(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            captured.append(url)
            return {"data": []}

        await search_via_api(
            query="إنما",
            base_url="https://dorar.net/dorar_api.json",
            profile=_FAST_PROFILE,
            fetcher=stub,
        )
        # Query param appears, URL-encoded.
        assert "?q=" in captured[0]
        # Arabic survives encoding (utf-8 percent-encoded)
        assert "%D8%A5%D9%86%D9%85%D8%A7" in captured[0]  # "إنما"

    async def test_api_key_when_present_passes_header(self) -> None:
        captured: list[dict[str, str] | None] = []

        async def stub(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            captured.append(headers)
            return {"data": []}

        await search_via_api(
            query="x",
            base_url="https://x",
            api_key="optional-key",
            profile=_FAST_PROFILE,
            fetcher=stub,
        )
        assert captured[0] is not None
        assert captured[0].get("X-API-Key") == "optional-key"

    async def test_api_key_absent_no_header(self) -> None:
        captured: list[dict[str, str] | None] = []

        async def stub(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            captured.append(headers)
            return {"data": []}

        await search_via_api(
            query="x",
            base_url="https://x",
            profile=_FAST_PROFILE,
            fetcher=stub,
        )
        # No X-API-Key header when the env slot is empty.
        assert captured[0] is not None
        assert "X-API-Key" not in captured[0]

    async def test_empty_query_rejected(self) -> None:
        async def stub(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            raise AssertionError("must not call")

        with pytest.raises(ValueError, match="query must not be empty"):
            await search_via_api(
                query="",
                base_url="https://x",
                profile=_FAST_PROFILE,
                fetcher=stub,
            )

    async def test_unknown_payload_shape_returns_empty(self) -> None:
        """An unrecognized response shape returns []. The consensus
        engine logs Class B aggregation downstream rather than crashing
        the whole verification run."""

        async def stub(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            return {"oops": "no recognized array key"}

        hits = await search_via_api(
            query="x",
            base_url="https://x",
            profile=_FAST_PROFILE,
            fetcher=stub,
        )
        assert hits == []

    async def test_alternate_payload_shape_ahadith(self) -> None:
        async def stub(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            return {
                "ahadith": [
                    {
                        "hadith": "نص آخر",
                        "rawi": "X",
                        "mohaddith": "Y",
                        "book": "Z",
                    }
                ]
            }

        hits = await search_via_api(
            query="x",
            base_url="https://x",
            profile=_FAST_PROFILE,
            fetcher=stub,
        )
        assert len(hits) == 1
        assert hits[0].matn == "نص آخر"


# --- search_via_scraping_fallback (DOM-break = Class B no-retry) ----


@pytest.mark.asyncio
class TestScrapingFallback:
    async def test_always_raises_class_b_no_retry(self) -> None:
        """§3.5 secondary-path rule: every invocation today is Class B
        without retry (DOM selectors not configured)."""
        with pytest.raises(ModelUClassB) as excinfo:
            await search_via_scraping_fallback(query="إنما")
        assert excinfo.value.retryable is False
        assert "scraping fallback" in str(excinfo.value)
        assert "Class B without retry" in str(excinfo.value)

    async def test_empty_query_rejected_before_class_b(self) -> None:
        """Empty query is a caller bug (Class A), not a DOM break.
        Surfaces as plain ValueError, not ModelUClassB."""
        with pytest.raises(ValueError, match="query must not be empty"):
            await search_via_scraping_fallback(query="")
