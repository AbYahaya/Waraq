"""§3.5 Model U — uniform conservative request profile for external sources.

Per Dokument 1 §3.5:
  "External HTTP-based sources (APIs and scraping paths) follow a
  uniform conservative request profile. Local sources are excluded;
  Shamela as a local collection is an explicit exception. Concrete
  rates, pauses, upper limits, and resumption times remain open and
  will be set after real measurement."

This module provides the **structural** Model U mechanism: a
configurable request profile + retry helper + Class A/B/C error
mapping per §4.18. The **concrete values** (rates, pauses, upper
limits) are calibration-deferred; the v1.0 defaults below are
documented implementation choices, replaceable when canon catches up.

§4.18 error class mapping:
  - **Class A** (user/data error): missing API key, malformed request,
    401/403 (caller-side fix). Surfaces as `ModelUClassA`.
  - **Class B** (external error): 429 rate-limited, 5xx server error,
    network timeout, DOM-break in scraping. Surfaces as `ModelUClassB`.
    DOM-break in the scraping fallback is **Class B without retry**
    per §3.5 ("DOM break is treated as a §4.18 Class B failure
    without retry; no silent self-healing at runtime").
  - **Class C** (system-fixable): upstream shape changed, parse
    failure. Surfaces as plain `ExternalSourceError`.

Class B is retry-eligible at the Model-U layer (linear backoff up to
`max_retries`); Class A and Class C raise immediately.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx


@dataclass(frozen=True, slots=True)
class ModelURequestProfile:
    """Configurable Model U knobs.

    All values are calibration-deferred per §3.5 ("remain open and
    will be set after real measurement"). The defaults below are v1.0
    implementation choices, not canon.
    """

    timeout_seconds: float = 15.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    inter_request_pause_seconds: float = 0.0


DEFAULT_MODEL_U_PROFILE = ModelURequestProfile()


class ExternalSourceError(RuntimeError):
    """External-source fetch failed (catch-all)."""


class ModelUClassA(ExternalSourceError):
    """§4.18 Class A — user/data error (missing API key, bad request,
    401/403). Caller fixes; never retried by Model U."""


class ModelUClassB(ExternalSourceError):
    """§4.18 Class B — external error (429, 5xx, network, DOM-break).

    The `retryable` flag follows §3.5: API-path Class B IS retried
    inside Model U; scraping-path DOM-break is Class B WITHOUT retry
    ("no silent self-healing at runtime") — callers raise
    `ModelUClassB(retryable=False, ...)` to opt out of retry.
    """

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


JsonFetcher = Callable[[str, dict[str, str] | None], Awaitable[dict[str, object]]]


async def _httpx_fetcher(
    url: str, headers: dict[str, str] | None, *, timeout_seconds: float
) -> dict[str, object]:
    """Default JSON fetcher backed by httpx.AsyncClient.

    Maps HTTP status to the canonical error class:
        401, 403           → ModelUClassA (auth/key problem)
        429, 5xx           → ModelUClassB (retryable)
        network / timeout  → ModelUClassB (retryable)
    """
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(url, headers=headers or {})
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        raise ModelUClassB(f"network failure for {url}: {exc}") from exc
    if response.status_code in (401, 403):
        raise ModelUClassA(f"auth failure {response.status_code} for {url}: {response.text[:200]}")
    if response.status_code == 429 or 500 <= response.status_code < 600:
        raise ModelUClassB(f"upstream {response.status_code} for {url}: {response.text[:200]}")
    if not response.is_success:
        raise ExternalSourceError(
            f"unexpected {response.status_code} for {url}: {response.text[:200]}"
        )
    try:
        return response.json()  # type: ignore[no-any-return]
    except ValueError as exc:
        raise ExternalSourceError(f"non-JSON body from {url}: {exc}") from exc


async def model_u_fetch(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    profile: ModelURequestProfile = DEFAULT_MODEL_U_PROFILE,
    fetcher: JsonFetcher | None = None,
) -> dict[str, object]:
    """Fetch JSON from `url` honoring Model U.

    Class B exceptions trigger up to `profile.max_retries` retries
    with `profile.retry_delay_seconds` linear backoff between attempts;
    Class A and other exceptions raise immediately. After `profile.
    inter_request_pause_seconds` is honored before each attempt to
    avoid hammering small upstream services.
    """

    async def _default(u: str, h: dict[str, str] | None) -> dict[str, object]:
        return await _httpx_fetcher(u, h, timeout_seconds=profile.timeout_seconds)

    fetch = fetcher or _default
    last_class_b: ModelUClassB | None = None
    for attempt in range(profile.max_retries):
        if profile.inter_request_pause_seconds > 0:
            await asyncio.sleep(profile.inter_request_pause_seconds)
        try:
            return await fetch(url, headers)
        except ModelUClassB as exc:
            last_class_b = exc
            if not exc.retryable or attempt + 1 >= profile.max_retries:
                raise
            await asyncio.sleep(profile.retry_delay_seconds)
            continue
        except ModelUClassA:
            raise
        except ExternalSourceError:
            raise
    # Defensive — the loop above always either returns or raises.
    assert last_class_b is not None
    raise last_class_b
