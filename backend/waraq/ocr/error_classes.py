"""T-4.1.3 — OCR error classes F-01 through F-09.

The codes (F-01..F-09) are canonical per CAB §B reference in CLAUDE.md §4.6.
The descriptions and the heuristic mapping in `waraq.ocr.profiling` were
adopted as canonical on 2026-05-04 (decision logged in WORKLOG):

    F-01 api_authentication   401 / 403 / bad-key / wrong scope
    F-02 rate_limit           429 / quota / RPM exhausted
    F-03 api_server_error     5xx / provider-side failure
    F-04 network_timeout      connection / DNS / wall-clock timeout
    F-05 malformed_input      bad image, unsupported MIME, oversized
    F-06 empty_extraction     API returned empty / whitespace text
    F-07 content_filtered     SAFETY / RECITATION / blocked content
    F-08 token_limit          context / token / image-size limit
    F-09 unknown              unclassified — investigate and re-profile
"""

from __future__ import annotations

from enum import StrEnum


class OcrErrorClass(StrEnum):
    """Canonical OCR error class codes per CAB §B.

    Values are the wire/DB form ("F-01" .. "F-09"). See module docstring for
    the canon-pending caveat on per-code descriptions.

    `F_06_QR` is a Qurʾān-recognition class read by the T-6.1.1 release
    gate (Sprint 2 §2). It is distinct from `F_06` (empty_extraction) — the
    `-QR` suffix marks it as a §4.15 Qurʾān-Stage-3 detection class. The
    detection writer for F-06-QR ships in M5 alongside Qurʾān-recognition;
    the gate that reads for unresolved F-06-QR rows ships in Sprint 2.
    """

    F_01 = "F-01"
    F_02 = "F-02"
    F_03 = "F-03"
    F_04 = "F-04"
    F_05 = "F-05"
    F_06 = "F-06"
    F_07 = "F-07"
    F_08 = "F-08"
    F_09 = "F-09"
    F_06_QR = "F-06-QR"


# Canonical descriptions for each F-XX code (decision 2026-05-04).
F_DESCRIPTIONS: dict[OcrErrorClass, str] = {
    OcrErrorClass.F_01: "api_authentication",  # 401, 403, bad/expired/wrong-scope key
    OcrErrorClass.F_02: "rate_limit",  # 429, quota exceeded, RPM exceeded
    OcrErrorClass.F_03: "api_server_error",  # 5xx — provider-side failure
    OcrErrorClass.F_04: "network_timeout",  # connection timeouts, DNS failures
    OcrErrorClass.F_05: "malformed_input",  # corrupt image, unsupported MIME, oversized
    OcrErrorClass.F_06: "empty_extraction",  # API returned empty/whitespace text
    OcrErrorClass.F_07: "content_filtered",  # safety / recitation / blocked-content
    OcrErrorClass.F_08: "token_limit",  # context/token limit exceeded
    OcrErrorClass.F_09: "unknown",  # unclassified — investigate
    OcrErrorClass.F_06_QR: "qurʾan_recognition",  # §4.15 Qurʾān-Stage-3 detection class
}
