"""§4.7.2 — Canonical 4 Pflichtfragen with validated answer schemas.

Per Dokument 1 §4.7.2 the four mandatory questions are:

  1. Which heading level should be displayed in the header?
  2. Which heading level marks chapter breaks?
  3. Position of the TOC (front / back)?
  4. Display Arabic chapter headings in the body text (yes / no)?

§4.7.2 also specifies the PDF export choice as a separate decision in
the same configuration layer:

  PDF export: Digital (RGB) or Print (PDF/X-1a, CMYK, 3 mm bleed).

The PDF choice is NOT one of the 4 Pflichtfragen — the canon labels
the four explicitly. It is handled separately (see
`waraq.preflight.pdf_choice`).

This module supplies the canonical schemas + validation. The four
Pflichtfragen are content-canonical: the 4-count is unveränderlich
(§4.7.2 + Sprint 4 §2), and the question content is named in §4.7.2.
The `frage_key` strings are stable identifiers used in API contracts;
the answer shapes are the validated payloads UI clients must submit.

Heading-level range — §7.1 + §7.2 of Formatvorlagen-Baseline v1.1
references Heading 1..6 (the §7.2 Heading-4/5/6 gap was closed in
Schluss-Audit Paket 7 with TOC depth raised to `\\o "1-6"`). We accept
1..6 here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from waraq.preflight.exceptions import PreflightError

# Canonical heading-level range per Formatvorlagen-Baseline v1.1 §7.1/§7.2
# (post Schluss-Audit Paket 7 — TOC depth = 1..6).
HEADING_LEVEL_MIN = 1
HEADING_LEVEL_MAX = 6


# --- Per-question Pydantic schemas ---------------------------------------


class HeaderHeadingLevelAnswer(BaseModel):
    """Frage 1 — Which heading level should be displayed in the header?"""

    heading_level: int = Field(ge=HEADING_LEVEL_MIN, le=HEADING_LEVEL_MAX)


class ChapterBreakHeadingLevelAnswer(BaseModel):
    """Frage 2 — Which heading level marks chapter breaks?"""

    heading_level: int = Field(ge=HEADING_LEVEL_MIN, le=HEADING_LEVEL_MAX)


class TocPositionAnswer(BaseModel):
    """Frage 3 — Position of the TOC (front / back)?"""

    position: Literal["front", "back"]


class DisplayArabicHeadingsAnswer(BaseModel):
    """Frage 4 — Display Arabic chapter headings in the body text (yes/no)?"""

    display: bool


# --- Canonical question definitions --------------------------------------


@dataclass(frozen=True, slots=True)
class PflichtfrageDefinition:
    """One of the four canonical Pflichtfragen per §4.7.2.

    The frage_key is the stable wire identifier; the schema is the
    Pydantic model that validates the answer payload.
    """

    frage_index: int  # 1..4 per §4.7.2 + PFLICHTFRAGE_COUNT
    frage_key: str
    prompt_de: str
    prompt_en: str
    schema: type[BaseModel]


PFLICHTFRAGEN: tuple[PflichtfrageDefinition, ...] = (
    PflichtfrageDefinition(
        frage_index=1,
        frage_key="header_heading_level",
        prompt_de="Welche Überschriftenebene soll im Kopfzeilenbereich angezeigt werden?",
        prompt_en="Which heading level should be displayed in the header?",
        schema=HeaderHeadingLevelAnswer,
    ),
    PflichtfrageDefinition(
        frage_index=2,
        frage_key="chapter_break_heading_level",
        prompt_de="Welche Überschriftenebene markiert Kapitelumbrüche?",
        prompt_en="Which heading level marks chapter breaks?",
        schema=ChapterBreakHeadingLevelAnswer,
    ),
    PflichtfrageDefinition(
        frage_index=3,
        frage_key="toc_position",
        prompt_de="Position des Inhaltsverzeichnisses (vorne / hinten)?",
        prompt_en="Position of the TOC (front / back)?",
        schema=TocPositionAnswer,
    ),
    PflichtfrageDefinition(
        frage_index=4,
        frage_key="display_arabic_chapter_headings",
        prompt_de="Arabische Kapitelüberschriften im Fliesstext anzeigen (ja/nein)?",
        prompt_en="Display Arabic chapter headings in the body text (yes/no)?",
        schema=DisplayArabicHeadingsAnswer,
    ),
)


_BY_INDEX: dict[int, PflichtfrageDefinition] = {p.frage_index: p for p in PFLICHTFRAGEN}
_BY_KEY: dict[str, PflichtfrageDefinition] = {p.frage_key: p for p in PFLICHTFRAGEN}


def get_pflichtfrage_by_index(frage_index: int) -> PflichtfrageDefinition:
    """Look up by 1-indexed canonical position. Raises KeyError on miss."""
    if frage_index not in _BY_INDEX:
        raise KeyError(f"frage_index {frage_index!r} is not canonical; valid: {sorted(_BY_INDEX)}")
    return _BY_INDEX[frage_index]


def get_pflichtfrage_by_key(frage_key: str) -> PflichtfrageDefinition:
    """Look up by stable wire key. Raises KeyError on miss."""
    if frage_key not in _BY_KEY:
        raise KeyError(f"frage_key {frage_key!r} is not canonical; valid: {sorted(_BY_KEY)}")
    return _BY_KEY[frage_key]


# --- Validation ----------------------------------------------------------


def validate_pflichtfrage_answer(
    *,
    frage_index: int,
    frage_key: str,
    answer: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate an answer payload against the canonical Pflichtfrage schema.

    Raises `PreflightError` on validation failure (covers: unknown
    frage_index, mismatched frage_key, malformed answer payload). On
    success returns the cleaned/validated dict (ready to persist on
    the Decision Event content).

    The (frage_index, frage_key) MUST match — the index is canonical,
    the key is the wire identifier; mixing them across rows is the
    failure mode (e.g., index=3 + key="display_arabic_chapter_headings"
    would mean a UI bug).
    """
    try:
        spec = get_pflichtfrage_by_index(frage_index)
    except KeyError as exc:
        raise PreflightError(str(exc)) from exc

    if spec.frage_key != frage_key:
        raise PreflightError(
            f"frage_key mismatch for frage_index={frage_index}: expected "
            f"{spec.frage_key!r}, got {frage_key!r}"
        )

    try:
        validated = spec.schema.model_validate(dict(answer))
    except ValidationError as exc:
        raise PreflightError(
            f"Pflichtfrage {frage_index} ({frage_key!r}) answer invalid: {exc}"
        ) from exc

    return validated.model_dump()


__all__ = [
    "HEADING_LEVEL_MAX",
    "HEADING_LEVEL_MIN",
    "PFLICHTFRAGEN",
    "ChapterBreakHeadingLevelAnswer",
    "DisplayArabicHeadingsAnswer",
    "HeaderHeadingLevelAnswer",
    "PflichtfrageDefinition",
    "TocPositionAnswer",
    "get_pflichtfrage_by_index",
    "get_pflichtfrage_by_key",
    "validate_pflichtfrage_answer",
]
