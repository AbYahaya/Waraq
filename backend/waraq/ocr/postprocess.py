"""Small OCR-output cleanup helpers.

These helpers are deliberately conservative: they remove obviously
non-OCR assistant commentary while preserving the model's line and
paragraph structure as much as possible.
"""

from __future__ import annotations

import re

_COMMENTARY_PATTERNS = [
    re.compile(r"^\s*sorry\b", re.IGNORECASE),
    re.compile(r"\bi[' ]?m sorry\b", re.IGNORECASE),
    re.compile(r"\bi[' ]?m unable to perform ocr\b", re.IGNORECASE),
    re.compile(r"\bi cannot perform ocr\b", re.IGNORECASE),
    re.compile(r"\bi can't perform ocr\b", re.IGNORECASE),
    re.compile(r"\bi cannot help with (?:that|this)\b", re.IGNORECASE),
    re.compile(r"\bi can't help with (?:that|this)\b", re.IGNORECASE),
    re.compile(r"\bi cannot assist with (?:that|this)\b", re.IGNORECASE),
    re.compile(r"\bi can't assist with (?:that|this)\b", re.IGNORECASE),
    re.compile(r"\bif you have any other questions\b", re.IGNORECASE),
    re.compile(r"\bfeel free to ask\b", re.IGNORECASE),
    re.compile(r"\bneed assistance\b", re.IGNORECASE),
    re.compile(r"\bhow else can i help\b", re.IGNORECASE),
    re.compile(r"\breturn only the extracted text\b", re.IGNORECASE),
]

_ARABIC_CHARS = re.compile(r"[\u0600-\u06FF]")
_LATIN_WORDS = re.compile(r"[A-Za-z]{3,}")


def _is_commentary_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if any(pattern.search(stripped) for pattern in _COMMENTARY_PATTERNS):
        return True
    # Defensive fallback: OCR output for Arabic pages should not suddenly
    # switch to an all-English assistant sentence. We only trigger this
    # when the line has clear Latin words and no Arabic characters.
    if _LATIN_WORDS.search(stripped) and not _ARABIC_CHARS.search(stripped):
        lowered = stripped.casefold()
        if any(
            token in lowered
            for token in (
                "sorry",
                "unable",
                "cannot",
                "can't",
                "assist",
                "help",
                "questions",
            )
        ):
            return True
    return False


def sanitize_ocr_output(text: str) -> str:
    """Strip obvious assistant commentary/refusal text from OCR output."""
    text = text.strip()
    if not text:
        return ""

    lines = text.splitlines()
    kept: list[str] = []
    for line in lines:
        if _is_commentary_line(line):
            continue
        kept.append(line.rstrip())

    while kept and not kept[0].strip():
        kept.pop(0)
    while kept and not kept[-1].strip():
        kept.pop()

    return "\n".join(kept).strip()


__all__ = ["sanitize_ocr_output"]
