"""§3.4 Stage 5 — OCR quality check.

Canon §3.4 Stage 5 names four checks the post-extract pass runs over
the OCR text:

  1. **Completeness** — does the text terminate cleanly (sentence-end
     punctuation, paragraph break) or mid-word? Mid-word truncation
     is a strong signal of a clipped scan or a failed page boundary.
  2. **Char count** — actual character count vs. the count expected
     for the page area. Very-short output on a normal-sized page
     suggests the OCR engine missed most of the content.
  3. **Structural symmetry** — paired delimiters (parentheses,
     brackets, French quotes, Arabic quotation marks) must balance.
     An unbalanced state typically means OCR misread one of a pair.
  4. **Known-passage matching** — does any segment of the text match
     a known Qurʾān āya or a Shamela section by skeleton? An exact
     match against canonical text is a strong positive signal.

Each check produces a signal in [0, 1]. The aggregator returns one
overall `QualityScore` per OCR pass; the score feeds the §4.4
confidence taxonomy via `classify_confidence` (sub-batch A).

Pluggability: each check is a pure function; the aggregator is a
plain weighted-average wrapper. Calibration of weights is Phase-7
work — v1.0 ships a defensible balanced default.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

# --- Sentence-end punctuation set (Latin + Arabic) ---------------------

# Characters that legitimately end a sentence in either Latin or
# Arabic script. `.` and `؟` (Arabic question mark) are the canonical
# anchors; the others are common terminators encountered in mixed
# scripts.
_SENTENCE_END_CHARS: Final[frozenset[str]] = frozenset(
    {
        ".",
        "!",
        "?",
        "؟",  # Arabic question mark
        "؛",  # Arabic semicolon
        "۔",  # Urdu full stop (sometimes appears in mixed corpus)
        ":",
        "\n",  # paragraph break
    }
)


# Paired delimiters whose counts must balance for `text` to be
# structurally well-formed. Add canon-stable; do not silently extend.
_BALANCED_PAIRS: Final[tuple[tuple[str, str], ...]] = (
    ("(", ")"),
    ("[", "]"),
    ("{", "}"),
    ("«", "»"),  # French / Arabic typographic quotes
    ("﴾", "﴿"),  # Qurʾān ornamental brackets
    ("“", "”"),  # English curly quotes
    ("‘", "’"),
)


# A whole-word boundary in Arabic text — Arabic letters + Latin
# alphanumerics. Used by completeness check to detect mid-word cut-off.
_WORD_RE = re.compile(r"[؀-ۿݐ-ݿA-Za-z0-9]+")


# --- Per-check signals -------------------------------------------------


@dataclass(frozen=True, kw_only=True, slots=True)
class CompletenessSignal:
    """Did `text` end cleanly?

    `score`: 1.0 if the trimmed last character is in
    `_SENTENCE_END_CHARS`; 0.5 if last char is whitespace adjacent to
    a word; 0.0 if last char is a letter mid-word.
    """

    score: float
    ends_with: str | None  # last non-whitespace character, for audit


@dataclass(frozen=True, kw_only=True, slots=True)
class StructuralSymmetrySignal:
    """Are paired delimiters balanced?

    `score`: 1.0 when every pair balances; otherwise the proportion
    of pairs that DO balance.
    `imbalanced`: list of `(open, close, open_count, close_count)`
    for the pairs that don't match — auditable.
    """

    score: float
    imbalanced: list[tuple[str, str, int, int]]


@dataclass(frozen=True, kw_only=True, slots=True)
class CharCountSignal:
    """Char count vs an expected count for the page.

    `ratio`: actual/expected, clamped to [0, 1.5]. `score` is the
    reward shape — peaks at ratio=1.0 and decays as ratio drifts.
    """

    score: float
    actual_chars: int
    expected_chars: int
    ratio: float


@dataclass(frozen=True, kw_only=True, slots=True)
class KnownPassageSignal:
    """Optional Stage-5 anchor: did any subsequence match a known
    canonical passage (Qurʾān āya, Shamela section)?

    Filled in by callers that have a session + corpus available; the
    pure-function check defaults to "no matches found, neutral
    contribution" (`score=0.5` — neither positive nor negative
    evidence).
    """

    score: float
    matched_count: int


@dataclass(frozen=True, kw_only=True, slots=True)
class QualityScore:
    """Aggregate Stage-5 quality signal.

    `overall` is a weighted average in [0, 1] suitable for feeding
    `classify_confidence` (sub-batch A): ≥0.85 → ACCEPTED,
    ≥0.60 → DEFICIENT, else CRITICAL.

    The constituent signals stay attached so audit / UI can show
    "why" the overall score is what it is.
    """

    overall: float
    completeness: CompletenessSignal
    structural_symmetry: StructuralSymmetrySignal
    char_count: CharCountSignal
    known_passage: KnownPassageSignal


# --- Pure check functions ----------------------------------------------


def check_completeness(text: str) -> CompletenessSignal:
    stripped = text.rstrip()
    if not stripped:
        return CompletenessSignal(score=0.0, ends_with=None)
    last = stripped[-1]
    if last in _SENTENCE_END_CHARS:
        return CompletenessSignal(score=1.0, ends_with=last)
    # Mid-word truncation: last char is a word character.
    if _WORD_RE.fullmatch(last):
        return CompletenessSignal(score=0.0, ends_with=last)
    # Closing delimiter / dash / etc. — neutral.
    return CompletenessSignal(score=0.5, ends_with=last)


def check_structural_symmetry(text: str) -> StructuralSymmetrySignal:
    imbalanced: list[tuple[str, str, int, int]] = []
    for open_c, close_c in _BALANCED_PAIRS:
        oc = text.count(open_c)
        cc = text.count(close_c)
        if oc != cc:
            imbalanced.append((open_c, close_c, oc, cc))
    score = 1.0 - (len(imbalanced) / len(_BALANCED_PAIRS))
    return StructuralSymmetrySignal(score=score, imbalanced=imbalanced)


def check_char_count(*, actual_chars: int, expected_chars: int) -> CharCountSignal:
    """`expected_chars` is the calibration parameter — derived per
    page from area + DPI + script density. v1.0 callers pass an
    estimate; Phase-7 calibration tightens it.

    Reward shape (intentionally simple, defensibly canon-aligned):
      ratio in [0.85, 1.15] → score 1.0
      ratio in [0.50, 0.85) or (1.15, 1.50] → linearly fades to 0.0
      ratio outside [0.5, 1.5] → score 0.0
    """
    if expected_chars <= 0:
        # No expectation supplied — neutral.
        return CharCountSignal(
            score=0.5, actual_chars=actual_chars, expected_chars=expected_chars, ratio=0.0
        )
    ratio = actual_chars / expected_chars
    clamped_ratio = max(0.0, min(1.5, ratio))
    if 0.85 <= clamped_ratio <= 1.15:
        score = 1.0
    elif 0.5 <= clamped_ratio < 0.85:
        # Linear ramp 0.5 → 0.85 maps to 0.0 → 1.0.
        score = (clamped_ratio - 0.5) / (0.85 - 0.5)
    elif 1.15 < clamped_ratio <= 1.5:
        # Linear ramp 1.15 → 1.5 maps to 1.0 → 0.0.
        score = 1.0 - (clamped_ratio - 1.15) / (1.5 - 1.15)
    else:
        score = 0.0
    return CharCountSignal(
        score=score,
        actual_chars=actual_chars,
        expected_chars=expected_chars,
        ratio=clamped_ratio,
    )


def check_known_passage_neutral() -> KnownPassageSignal:
    """v1.0 default when caller cannot run a corpus lookup. Returns
    a neutral 0.5 — neither positive nor negative evidence."""
    return KnownPassageSignal(score=0.5, matched_count=0)


# --- Aggregator --------------------------------------------------------


# Weights chosen so the aggregate sums to 1.0 and each signal carries
# at least 15% — a single mediocre signal cannot drag overall to
# CRITICAL on its own. Phase-7 calibration may re-tune these.
_DEFAULT_WEIGHTS: Final[dict[str, float]] = {
    "completeness": 0.30,
    "structural_symmetry": 0.20,
    "char_count": 0.30,
    "known_passage": 0.20,
}


def compute_quality_score(
    text: str,
    *,
    expected_chars: int = 0,
    known_passage: KnownPassageSignal | None = None,
) -> QualityScore:
    """Run every Stage-5 check + aggregate.

    `expected_chars=0` means "caller has no per-page estimate" — the
    char-count check returns the neutral 0.5 score in that case so it
    doesn't unfairly punish the overall.

    `known_passage`: optional signal from a corpus lookup. Pass
    `KnownPassageSignal(score=1.0, matched_count=N)` when at least
    one segment exact-matches a known passage; default
    `check_known_passage_neutral()` otherwise.
    """
    completeness = check_completeness(text)
    symmetry = check_structural_symmetry(text)
    char_count = check_char_count(actual_chars=len(text), expected_chars=expected_chars)
    kp = known_passage if known_passage is not None else check_known_passage_neutral()

    overall = (
        _DEFAULT_WEIGHTS["completeness"] * completeness.score
        + _DEFAULT_WEIGHTS["structural_symmetry"] * symmetry.score
        + _DEFAULT_WEIGHTS["char_count"] * char_count.score
        + _DEFAULT_WEIGHTS["known_passage"] * kp.score
    )
    # Clamp defensively in case of float drift.
    overall = max(0.0, min(1.0, overall))
    return QualityScore(
        overall=overall,
        completeness=completeness,
        structural_symmetry=symmetry,
        char_count=char_count,
        known_passage=kp,
    )


__all__ = [
    "CharCountSignal",
    "CompletenessSignal",
    "KnownPassageSignal",
    "QualityScore",
    "StructuralSymmetrySignal",
    "check_char_count",
    "check_completeness",
    "check_known_passage_neutral",
    "check_structural_symmetry",
    "compute_quality_score",
]
