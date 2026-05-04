"""T-4.1.3 — Map OCR-pipeline exceptions to canonical F-XX error classes.

The mapping is heuristic (string-pattern matching on the wrapped exception's
representation). It's fragile by nature — when the SDK exposes structured
error types we should switch to those. Adopted as canonical 2026-05-04.

Heuristic precedence (first match wins):
1. TimeoutError / ConnectionError → F-04 (network_timeout)
2. GeminiApiError → inspect cause for keywords (auth, rate, server, network,
   safety, token), default F-09
3. ValueError / TypeError → F-05 (malformed_input)
4. anything else → F-09 (unknown)

The function is pure (no side effects, no IO). Tests cover each F-XX class.
"""

from __future__ import annotations

from typing import ClassVar

from waraq.ocr.error_classes import OcrErrorClass
from waraq.ocr.exceptions import GeminiApiError


class _Keywords:
    """Lowercase keyword groups matched against the underlying cause's string
    representation. Order in profile_exception matters; this is just storage."""

    AUTH: ClassVar[tuple[str, ...]] = (
        "401",
        "403",
        "unauthenticated",
        "permission",
        "forbidden",
        "invalid api key",
        "api_key_invalid",
    )
    RATE: ClassVar[tuple[str, ...]] = (
        "429",
        "rate limit",
        "quota",
        "resourceexhausted",
        "resource_exhausted",
        "too many requests",
    )
    SERVER: ClassVar[tuple[str, ...]] = (
        "500",
        "502",
        "503",
        "504",
        "internal error",
        "internal server error",
        "service unavailable",
        "bad gateway",
    )
    NETWORK: ClassVar[tuple[str, ...]] = (
        "timeout",
        "timed out",
        "connection",
        "dns",
        "network",
        "unreachable",
    )
    SAFETY: ClassVar[tuple[str, ...]] = (
        "safety",
        "recitation",
        "blocked",
        "block_reason",
        "harm_category",
        "prohibited",
    )
    TOKEN: ClassVar[tuple[str, ...]] = (
        "token limit",
        "context length",
        "context window",
        "max_tokens",
        "input too large",
        "image too large",
    )


def profile_exception(exc: BaseException) -> OcrErrorClass:
    """Classify an exception into one of the F-01..F-09 canonical classes.

    Pure function; never raises. Anything it can't recognize maps to F_09."""
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return OcrErrorClass.F_04

    if isinstance(exc, GeminiApiError):
        return _profile_gemini_cause(exc.cause)

    if isinstance(exc, (ValueError, TypeError)):
        return OcrErrorClass.F_05

    return OcrErrorClass.F_09


def _profile_gemini_cause(cause: BaseException) -> OcrErrorClass:
    """Map the underlying cause of a GeminiApiError to F-XX.

    Inspects both `str(cause)` and `repr(cause)` since some SDK errors carry
    informative content in only one of them."""
    if isinstance(cause, (TimeoutError, ConnectionError)):
        return OcrErrorClass.F_04

    haystack = f"{cause!s} {cause!r} {type(cause).__name__}".lower()

    if any(kw in haystack for kw in _Keywords.AUTH):
        return OcrErrorClass.F_01
    if any(kw in haystack for kw in _Keywords.RATE):
        return OcrErrorClass.F_02
    if any(kw in haystack for kw in _Keywords.SERVER):
        return OcrErrorClass.F_03
    if any(kw in haystack for kw in _Keywords.NETWORK):
        return OcrErrorClass.F_04
    if any(kw in haystack for kw in _Keywords.SAFETY):
        return OcrErrorClass.F_07
    if any(kw in haystack for kw in _Keywords.TOKEN):
        return OcrErrorClass.F_08
    return OcrErrorClass.F_09
