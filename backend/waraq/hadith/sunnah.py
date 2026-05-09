"""§4.16.1 P-1 — sunnah.com client (mandatory hadith verification source).

Per Dokument 1 §4.16.1: P-1 = sunnah.com (API). Mandatory set, fully
searched on every hadith verification run. Free non-commercial API
key registration at sunnah.com/developers; sent as `X-API-Key` header.

This module provides direct hadith lookup and collection-scoped
fetch. The actual consensus + multi-dimensional comparison logic
that consumes these results lives in Phase 2F. v1.0 ship: client +
parse + Model U retry/timeout/Class-B mapping.

Public surface:
    fetch_hadith(collection, hadith_number, *, api_key, profile, fetcher)
        → SunnahHadith | None  (None when collection+number doesn't exist)

Endpoints (per public sunnah.com developer docs):
    GET https://api.sunnah.com/v1/hadiths/{collection}/{hadithNumber}
    GET https://api.sunnah.com/v1/collections                  (list)
    GET https://api.sunnah.com/v1/collections/{name}/books     (list)

The v1.0 client implements the direct-lookup endpoint only — that's
what the §4.16 verification flow needs given an author-supplied
citation like "Bukhari, Nr. 1907". Search-by-text is Phase 2F.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from waraq.external import (
    DEFAULT_MODEL_U_PROFILE,
    JsonFetcher,
    ModelUClassA,
    ModelURequestProfile,
    model_u_fetch,
)

DEFAULT_SUNNAH_BASE_URL = "https://api.sunnah.com/v1"


class SunnahApiKeyMissing(ModelUClassA):
    """`SUNNAH_COM_API_KEY` not set. Class A — caller fixes."""


@dataclass(frozen=True, slots=True)
class SunnahHadith:
    """One hadith from sunnah.com.

    Field naming reflects the canonical §4.16 semantics: `matn_arabic`
    is the matn (Arabic body), `matn_english` the parallel English
    rendering (per §4.16.8 — comparison/provenance, not derivation
    source). `grades` carries the authenticity-grade list verbatim
    from the upstream payload (consensus engine reads these per
    §4.16.3 "authenticity signals").
    """

    collection: str
    hadith_number: int
    matn_arabic: str
    matn_english: str
    book_number: int | None
    chapter_id: int | None
    grades: list[dict[str, Any]]
    raw_payload: dict[str, Any]


async def fetch_hadith(
    *,
    collection: str,
    hadith_number: int,
    api_key: str,
    base_url: str = DEFAULT_SUNNAH_BASE_URL,
    profile: ModelURequestProfile = DEFAULT_MODEL_U_PROFILE,
    fetcher: JsonFetcher | None = None,
) -> SunnahHadith:
    """Direct lookup of one hadith by collection + number.

    Raises:
        SunnahApiKeyMissing: empty `api_key`. Class A — set the env
            slot `SUNNAH_COM_API_KEY` and retry.
        ModelUClassA: 401/403 from upstream (key invalid).
        ModelUClassB: 429/5xx/network — retried inside Model U.
        ExternalSourceError: parse failure / shape change.
        ValueError: caller passed an empty collection.
    """
    if not api_key:
        raise SunnahApiKeyMissing(
            "SUNNAH_COM_API_KEY not set; cannot call sunnah.com. "
            "Free registration at sunnah.com/developers."
        )
    if not collection:
        raise ValueError("collection name required")

    url = f"{base_url}/hadiths/{collection}/{hadith_number}"
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    payload = await model_u_fetch(
        url,
        headers=headers,
        profile=profile,
        fetcher=fetcher,
    )
    return _parse_hadith_payload(payload, expected_collection=collection)


def _parse_hadith_payload(payload: dict[str, object], *, expected_collection: str) -> SunnahHadith:
    """Parse the sunnah.com `/hadiths/{collection}/{hadithNumber}` payload."""
    coll = payload.get("collection")
    number_raw = payload.get("hadithNumber")
    if not isinstance(coll, str) or coll != expected_collection:
        raise ValueError(
            f"sunnah.com response collection={coll!r} doesn't match "
            f"expected {expected_collection!r}"
        )
    number = _coerce_int(number_raw, "hadithNumber")

    arabic = _coerce_str(payload, "hadithArabic")
    english = _coerce_str(payload, "hadithEnglish")
    book_number = _coerce_optional_int(payload, "bookNumber")
    chapter_id = _coerce_optional_int(payload, "chapterId")
    grades_raw = payload.get("grades", [])
    if not isinstance(grades_raw, list):
        raise ValueError(f"grades field is not a list: {type(grades_raw).__name__}")
    grades = [g for g in grades_raw if isinstance(g, dict)]

    return SunnahHadith(
        collection=coll,
        hadith_number=number,
        matn_arabic=arabic,
        matn_english=english,
        book_number=book_number,
        chapter_id=chapter_id,
        grades=grades,
        raw_payload=payload,
    )


def _coerce_str(payload: dict[str, object], key: str) -> str:
    raw = payload.get(key, "")
    if not isinstance(raw, str):
        raise ValueError(f"field {key} not a string: {type(raw).__name__}")
    return raw


def _coerce_int(raw: object, key: str) -> int:
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        try:
            return int(raw)
        except ValueError as exc:
            raise ValueError(f"field {key}={raw!r} not parseable as int") from exc
    raise ValueError(f"field {key} missing or wrong type: {raw!r}")


def _coerce_optional_int(payload: dict[str, object], key: str) -> int | None:
    raw = payload.get(key)
    if raw is None or raw == "":
        return None
    return _coerce_int(raw, key)


__all__ = [
    "DEFAULT_SUNNAH_BASE_URL",
    "SunnahApiKeyMissing",
    "SunnahHadith",
    "fetch_hadith",
]
