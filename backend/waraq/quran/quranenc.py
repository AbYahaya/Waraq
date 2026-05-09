"""§4.15.1 quranenc.com translation client.

Public REST API (no key, no auth):
    GET https://quranenc.com/api/v1/translation/sura/<key>/<sura_num>
    GET https://quranenc.com/api/v1/translation/aya/<key>/<sura_num>/<aya_num>

`<key>` is the canonical translation identifier — per §4.15.1 the v1.0
keys are `german_rwwad` (German Rwwad) and `english_rwwad` (English
Rwwad).

Response shape (sura endpoint):
    {
        "result": [
            {"sura": "1", "aya": "1", "arabic_text": "...",
             "translation": "...", "footnotes": "..."},
            ...
        ]
    }

This module only fetches + parses. It does NOT write to the DB and
does NOT implement primary-fallback semantics — those live in
`translation_lookup` / `translation_sync`. Keeping fetch isolated
makes it cheap to mock in tests + cheap to swap the HTTP backend.

**Model U** (§3.5 conservative request profile): for v1.0 the client
exposes a default per-request timeout (15s) and a per-sura connect
backoff (1s, max 3 retries). The concrete rates / pauses / upper
limits are calibration-deferred per canon ("remain open and will be
set after real measurement"); this client's defaults are documented
implementation choices, replaceable when the values get canonized.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

DEFAULT_BASE_URL = "https://quranenc.com/api/v1"
GERMAN_RWWAD_KEY = "german_rwwad"
ENGLISH_RWWAD_KEY = "english_rwwad"

# Canonical translation_key → ISO 639-1 language code mapping.
TRANSLATION_KEY_TO_LANGUAGE: dict[str, str] = {
    GERMAN_RWWAD_KEY: "de",
    ENGLISH_RWWAD_KEY: "en",
}


class QuranEncError(RuntimeError):
    """quranenc.com fetch failed (network / HTTP / parse)."""


@dataclass(frozen=True, slots=True)
class QuranEncVerse:
    """One verse from a quranenc.com translation response."""

    sura_index: int
    aya_index: int
    arabic_text: str
    translation: str
    footnotes: str | None


# Type alias for an injectable HTTP fetcher: (url) -> json dict.
JsonFetcher = Callable[[str], Awaitable[dict[str, object]]]


async def _default_fetcher(url: str) -> dict[str, object]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]


async def fetch_sura(
    *,
    translation_key: str,
    sura_index: int,
    base_url: str = DEFAULT_BASE_URL,
    fetcher: JsonFetcher | None = None,
    max_retries: int = 3,
    retry_delay_seconds: float = 1.0,
) -> list[QuranEncVerse]:
    """Fetch all verses of a sura under the given translation key.

    Retries up to `max_retries` times on httpx exceptions / non-2xx;
    raises `QuranEncError` after exhausting retries. The retry delay
    is a simple linear backoff — Model U's exponential profile is
    canonically deferred to calibration.
    """
    if not 1 <= sura_index <= 114:
        raise ValueError(f"sura_index {sura_index} out of canonical range 1..114")
    if translation_key not in TRANSLATION_KEY_TO_LANGUAGE:
        raise ValueError(
            f"unknown translation_key {translation_key!r}; "
            f"canonical keys: {sorted(TRANSLATION_KEY_TO_LANGUAGE)}"
        )

    fetch = fetcher or _default_fetcher
    url = f"{base_url}/translation/sura/{translation_key}/{sura_index}"
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            payload = await fetch(url)
            return _parse_sura_payload(payload, expected_sura=sura_index)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            last_error = exc
            if attempt + 1 < max_retries:
                await asyncio.sleep(retry_delay_seconds)
            continue
    raise QuranEncError(
        f"quranenc.com fetch failed for sura {sura_index} ({translation_key}): "
        f"{type(last_error).__name__}: {last_error}"
    ) from last_error


def _parse_sura_payload(payload: dict[str, object], *, expected_sura: int) -> list[QuranEncVerse]:
    raw = payload.get("result")
    if not isinstance(raw, list):
        raise ValueError(f"quranenc.com response missing 'result' array (got {type(raw).__name__})")
    verses: list[QuranEncVerse] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError(f"non-dict entry in result: {entry!r}")
        sura = _coerce_int(entry, "sura")
        aya = _coerce_int(entry, "aya")
        if sura != expected_sura:
            raise ValueError(f"verse reports sura {sura} but request was for {expected_sura}")
        translation_value = entry.get("translation", "")
        if not isinstance(translation_value, str):
            raise ValueError(f"sura {sura} aya {aya}: translation field not a string")
        arabic_value = entry.get("arabic_text", "")
        if not isinstance(arabic_value, str):
            raise ValueError(f"sura {sura} aya {aya}: arabic_text field not a string")
        footnotes_value = entry.get("footnotes")
        footnotes = (
            footnotes_value if isinstance(footnotes_value, str) and footnotes_value else None
        )
        verses.append(
            QuranEncVerse(
                sura_index=sura,
                aya_index=aya,
                arabic_text=arabic_value,
                translation=translation_value,
                footnotes=footnotes,
            )
        )
    if not verses:
        raise ValueError(f"empty verse list returned for sura {expected_sura}")
    return verses


def _coerce_int(entry: dict[str, object], key: str) -> int:
    raw = entry.get(key)
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        try:
            return int(raw)
        except ValueError as exc:
            raise ValueError(f"field {key}={raw!r} is not an integer") from exc
    raise ValueError(f"field {key} missing or wrong type: {raw!r}")


__all__ = [
    "DEFAULT_BASE_URL",
    "ENGLISH_RWWAD_KEY",
    "GERMAN_RWWAD_KEY",
    "TRANSLATION_KEY_TO_LANGUAGE",
    "JsonFetcher",
    "QuranEncError",
    "QuranEncVerse",
    "fetch_sura",
]
