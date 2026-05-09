"""§4.16.1 P-3 — dorar.net client (mandatory hadith verification source).

Per Dokument 1 §4.16.1: P-3 = dorar.net (= الدُّرَرُ السَّنِيَّة). Mandatory
set, fully searched on every hadith verification run.

Per §3.5 (scraping secondary-path rule):
  "For dorar.net: API path primary, scraping only as fallback when
  the API does not cover the required functionality. A DOM break is
  treated as a §4.18 Class B failure without retry; no silent
  self-healing at runtime."

This module ships **two paths** structurally:

1. `search_via_api(...)` — primary path. Uses the dorar.net
   `dorar_api.json` JSON endpoint with the `q` query parameter.
   Subject to Model U retry/timeout/Class-B mapping like every other
   API.

2. `search_via_scraping_fallback(...)` — secondary path per §3.5.
   v1.0 ship: this raises `ModelUClassB(retryable=False)` immediately
   ("DOM break is treated as a Class B failure without retry"). The
   actual DOM selectors are calibration territory — they require
   real-DOM analysis on dorar.net's current markup, which is exactly
   the kind of fragile coupling §3.5 anticipates. Configuring the
   selectors when the API doesn't cover the required functionality
   is a follow-up; the canonical no-retry-on-break rule is enforced
   today by structural construction (any access fails Class-B-no-retry).

Endpoint default per §3.5: "fully unspecified – active work front".
The base URL is configurable via the `dorar_net_base_url` setting.
Real endpoint discovery + signature is a deployment-time concern.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from waraq.external import (
    DEFAULT_MODEL_U_PROFILE,
    JsonFetcher,
    ModelUClassB,
    ModelURequestProfile,
    model_u_fetch,
)


@dataclass(frozen=True, slots=True)
class DorarHadith:
    """One hadith hit from dorar.net.

    Field naming reflects the upstream payload shape (Arabic-only
    source — dorar.net publishes the Arabic matn + grading
    metadata). The consensus engine in Phase 2F maps these to the
    `HadithSingleSourceResult` rows under `quellen_rolle="pflicht"`.
    """

    matn: str
    rawi: str
    mohaddith: str
    book: str
    page_or_number: str | None
    grade: str
    raw_payload: dict[str, Any]


async def search_via_api(
    *,
    query: str,
    base_url: str,
    api_key: str | None = None,
    profile: ModelURequestProfile = DEFAULT_MODEL_U_PROFILE,
    fetcher: JsonFetcher | None = None,
) -> list[DorarHadith]:
    """Primary path — dorar.net API search.

    Returns matched hits. dorar.net's public path is keyless; the
    `api_key` parameter is supplied for future authenticated rollout
    or local-test override (sent as `X-API-Key` header when present).
    """
    if not query:
        raise ValueError("query must not be empty")

    headers: dict[str, str] = {"Accept": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    # The exact query-parameter name + response shape is upstream-
    # specific and deployment-configurable. v1.0 wires the most common
    # convention (`q` query param); deployments override `base_url`
    # to point at whatever signature dorar.net's stable endpoint uses.
    url = f"{base_url}?q={_url_quote(query)}"
    payload = await model_u_fetch(url, headers=headers, profile=profile, fetcher=fetcher)
    return _parse_search_payload(payload)


async def search_via_scraping_fallback(
    *,
    query: str,
) -> list[DorarHadith]:
    """Secondary path per §3.5 — scraping fallback when the API does
    not cover the required functionality.

    v1.0 raises `ModelUClassB(retryable=False)` immediately:
      - DOM selectors are not configured (the secondary path is
        structurally present but inert until real DOM analysis lands).
      - DOM break = Class B without retry per §3.5 — every fallback
        invocation today is structurally a "DOM break" since no
        selectors exist; the no-retry contract is preserved.

    Once selectors are configured (Phase 4+ calibration work), this
    function will try the scraping path and raise the same
    `ModelUClassB(retryable=False)` only on actual DOM mismatch.
    """
    if not query:
        raise ValueError("query must not be empty")
    raise ModelUClassB(
        "dorar.net scraping fallback: DOM selectors not configured "
        "(§3.5 secondary path inert in v1.0). Class B without retry.",
        retryable=False,
    )


def _parse_search_payload(payload: dict[str, object]) -> list[DorarHadith]:
    """Parse dorar.net's JSON search payload.

    The shape is upstream-specific; this v1.0 parser handles the
    common `{"data": [{...}, ...]}` / `{"ahadith": [{...}]}` shapes
    by checking both keys. Real shape is configurable when the
    canonical signature is fixed.
    """
    raw = _extract_results_array(payload)
    out: list[DorarHadith] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        out.append(
            DorarHadith(
                matn=_str_or_empty(entry, "matn", "hadith", "text"),
                rawi=_str_or_empty(entry, "rawi", "narrator"),
                mohaddith=_str_or_empty(entry, "mohaddith", "muhaddith"),
                book=_str_or_empty(entry, "book", "kitab"),
                page_or_number=_str_or_none(entry, "page", "number", "rakm"),
                grade=_str_or_empty(entry, "grade", "hokm", "judgment"),
                raw_payload=entry,
            )
        )
    return out


def _extract_results_array(payload: dict[str, object]) -> list[object]:
    for key in ("data", "ahadith", "results", "items"):
        raw = payload.get(key)
        if isinstance(raw, list):
            return raw
    # No recognized array → empty result set rather than crash;
    # callers treat that as "no hits". Real shape changes surface
    # via empty results in dev, prompting the consensus engine to
    # log Class B aggregation.
    return []


def _str_or_empty(entry: dict[str, object], *keys: str) -> str:
    for k in keys:
        raw = entry.get(k)
        if isinstance(raw, str) and raw:
            return raw
    return ""


def _str_or_none(entry: dict[str, object], *keys: str) -> str | None:
    for k in keys:
        raw = entry.get(k)
        if isinstance(raw, str) and raw:
            return raw
        if isinstance(raw, int):
            return str(raw)
    return None


def _url_quote(value: str) -> str:
    from urllib.parse import quote_plus

    return quote_plus(value)


__all__ = [
    "DorarHadith",
    "search_via_api",
    "search_via_scraping_fallback",
]
