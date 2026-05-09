"""§3.5 Model U + §4.18 Class A/B/C error mapping tests (no network)."""

from __future__ import annotations

import pytest

from waraq.external import (
    ExternalSourceError,
    ModelUClassA,
    ModelUClassB,
    ModelURequestProfile,
    model_u_fetch,
)

# Profile with no inter-request pause + zero retry delay so the test
# loop is deterministic and instant.
_FAST_PROFILE = ModelURequestProfile(
    timeout_seconds=1.0,
    max_retries=3,
    retry_delay_seconds=0.0,
    inter_request_pause_seconds=0.0,
)


@pytest.mark.asyncio
class TestRetryAndClassMapping:
    async def test_happy_path_single_call(self) -> None:
        calls = {"n": 0}

        async def stub(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            calls["n"] += 1
            return {"ok": True}

        result = await model_u_fetch("https://x", profile=_FAST_PROFILE, fetcher=stub)
        assert result == {"ok": True}
        assert calls["n"] == 1

    async def test_class_b_retried_then_succeed(self) -> None:
        calls = {"n": 0}

        async def flaky(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            calls["n"] += 1
            if calls["n"] < 2:
                raise ModelUClassB("upstream 503")
            return {"ok": True}

        result = await model_u_fetch("https://x", profile=_FAST_PROFILE, fetcher=flaky)
        assert result == {"ok": True}
        assert calls["n"] == 2

    async def test_class_b_exhausts_retries_raises(self) -> None:
        calls = {"n": 0}

        async def always_fail(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            calls["n"] += 1
            raise ModelUClassB("permanent 500")

        with pytest.raises(ModelUClassB, match="permanent 500"):
            await model_u_fetch("https://x", profile=_FAST_PROFILE, fetcher=always_fail)
        # max_retries=3 → exactly 3 attempts.
        assert calls["n"] == 3

    async def test_class_a_raises_immediately_no_retry(self) -> None:
        calls = {"n": 0}

        async def auth_fail(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            calls["n"] += 1
            raise ModelUClassA("auth failure 401")

        with pytest.raises(ModelUClassA, match="401"):
            await model_u_fetch("https://x", profile=_FAST_PROFILE, fetcher=auth_fail)
        # Class A is NOT retried.
        assert calls["n"] == 1

    async def test_class_b_non_retryable_raises_immediately(self) -> None:
        """The DOM-break = Class B no-retry rule (§3.5)."""
        calls = {"n": 0}

        async def dom_break(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            calls["n"] += 1
            raise ModelUClassB("DOM break", retryable=False)

        with pytest.raises(ModelUClassB, match="DOM break"):
            await model_u_fetch("https://x", profile=_FAST_PROFILE, fetcher=dom_break)
        # retryable=False → exactly 1 attempt.
        assert calls["n"] == 1

    async def test_class_c_raises_immediately_no_retry(self) -> None:
        calls = {"n": 0}

        async def parse_fail(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            calls["n"] += 1
            raise ExternalSourceError("non-JSON body")

        with pytest.raises(ExternalSourceError, match="non-JSON"):
            await model_u_fetch("https://x", profile=_FAST_PROFILE, fetcher=parse_fail)
        # Class C is NOT retried.
        assert calls["n"] == 1


@pytest.mark.asyncio
class TestHeaders:
    async def test_headers_passed_through(self) -> None:
        captured: dict[str, dict[str, str] | None] = {"hdr": None}

        async def echo(url: str, headers: dict[str, str] | None) -> dict[str, object]:
            captured["hdr"] = headers
            return {"ok": True}

        await model_u_fetch(
            "https://x",
            headers={"X-API-Key": "secret"},
            profile=_FAST_PROFILE,
            fetcher=echo,
        )
        assert captured["hdr"] == {"X-API-Key": "secret"}
