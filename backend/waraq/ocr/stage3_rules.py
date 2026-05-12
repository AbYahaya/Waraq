"""§3.4 Stage-3 rule-based track — CAMeL Tools morphology + Mishkal
diacritization plausibility.

Per §3.4 the rule-based reading-line validates that the Stage-2
consensus output is *grammatically Arabic*. Two independent signals:

1. **Morphological analyzability** (CAMeL Tools)
   For each Arabic word in the candidate, ask CAMeL's MSA morphology
   analyzer for at least one analysis. The fraction of words that
   are analyzable is the morphological-plausibility score.

2. **Diacritization viability** (Mishkal)
   Mishkal's `tashkeel` engine attempts to vocalize bare Arabic. A
   high diacritization rate is consistent with valid input; gibberish
   is largely passed through unchanged.

Both signals are pluggable: callers can inject stub callables for
testing without invoking either heavyweight engine. Production wires
the real adapters through `morphology_default()` + `mishkal_default()`.

Graceful degradation
--------------------
Per the existing `waraq.morphology` lazy-import pattern (M4 click-word
feature), CAMeL is OPTIONAL: when the morphology DB isn't installed
on the host (`camel_data -i morphology-db-msa-r13` not run), the
analyzer returns a `MorphologyDataMissing` exception. We treat that
as **neutral** (0.5) rather than failing the whole Stage-3 pass.
Mishkal is similarly wrapped — any import / runtime error degrades
to neutral.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Arabic letter range U+0600..U+06FF — used to identify words to score.
_ARABIC_WORD_RE = re.compile(r"[؀-ۿ]+")

# Neutral signal when an engine is unavailable. Same convention as the
# §3.3 preprocessing harness in sub-batch A.
NEUTRAL_SCORE: float = 0.50


# ---------------------------------------------------------------------
# Adapter signatures — pluggable at the function boundary
# ---------------------------------------------------------------------

# `(word) -> bool` — True iff CAMeL has at least one morphology row.
MorphologyAnalyzableFn = Callable[[str], bool]

# `(text) -> str` — Mishkal-tashkeel-style call returning a vocalized
# variant of the input. The score is the ratio of added diacritic
# characters to total characters; high ratios mean the engine
# recognized lots of valid forms.
DiacritizerFn = Callable[[str], str]


@dataclass(frozen=True, kw_only=True, slots=True)
class Stage3RuleResult:
    """Output of the rule-based pass.

    Attributes:
        score: Weighted [0, 1] aggregate.
        morphology_score: Fraction of Arabic words CAMeL analyzes.
            Neutral (0.5) when the engine is unavailable.
        morphology_available: True iff CAMeL produced at least one
            real analyzability decision (i.e. the DB was present).
        diacritization_score: Mishkal diacritic-density ratio.
            Neutral (0.5) when Mishkal raises.
        diacritization_available: True iff Mishkal returned without
            raising.
        word_count: Number of Arabic-script words seen in the input.
    """

    score: float
    morphology_score: float
    morphology_available: bool
    diacritization_score: float
    diacritization_available: bool
    word_count: int


def _morphology_analyzable_default(word: str) -> bool:
    """Default morphology adapter — uses `waraq.morphology.service`.

    Lazy-imports + suppresses `MorphologyNotInstalled` /
    `MorphologyDataMissing` by returning False (treated as a neutral
    signal at the aggregate level when ALL words fail this way).
    """
    from waraq.morphology.exceptions import MorphologyDataMissing, MorphologyNotInstalled
    from waraq.morphology.service import analyze_word

    try:
        analyses = analyze_word(word)
    except (MorphologyNotInstalled, MorphologyDataMissing):
        # Sentinel: re-raise so the wrapper can flip to neutral.
        raise
    except Exception:
        # Defensive: any runtime quirk → not analyzable.
        return False
    return len(analyses) > 0


def _diacritizer_default(text: str) -> str:
    """Default Mishkal adapter. Lazy-imports the package on first call
    and constructs the singleton tashkeel engine."""
    import mishkal.tashkeel  # type: ignore[import-untyped]

    engine = mishkal.tashkeel.TashkeelClass()
    return str(engine.tashkeel(text))


# Diacritic codepoints we count — same range as `waraq.arabic`.
_DIACRITIC_CHARS = frozenset(
    {chr(cp) for start, end in [(0x064B, 0x065F), (0x0670, 0x0670)] for cp in range(start, end + 1)}
)


def _diacritization_density(original: str, vocalized: str) -> float:
    """Score = ratio of diacritic chars in `vocalized` minus those
    already in `original`, normalized by the count of Arabic letters
    in `original`. Clamped to [0, 1]."""
    arabic_letters = sum(1 for c in original if "؀" <= c <= "ۿ" and c not in _DIACRITIC_CHARS)
    if arabic_letters == 0:
        return NEUTRAL_SCORE
    voc_diacritics = sum(1 for c in vocalized if c in _DIACRITIC_CHARS)
    orig_diacritics = sum(1 for c in original if c in _DIACRITIC_CHARS)
    added = max(voc_diacritics - orig_diacritics, 0)
    return max(0.0, min(1.0, added / arabic_letters))


def rule_based_score(
    candidate_text: str,
    *,
    morphology_fn: MorphologyAnalyzableFn | None = None,
    diacritizer_fn: DiacritizerFn | None = None,
    morphology_weight: float = 0.6,
    diacritization_weight: float = 0.4,
) -> Stage3RuleResult:
    """Compute the rule-based Stage-3 score over `candidate_text`.

    Args:
        candidate_text: Arabic text to validate.
        morphology_fn: Optional adapter — defaults to CAMeL Tools.
            Test stubs return deterministic per-word verdicts.
        diacritizer_fn: Optional adapter — defaults to Mishkal.
        morphology_weight, diacritization_weight: Sum to 1.0; v1.0
            weights morphology slightly higher because diacritic
            density is noisier on lexicon-style abbreviated text.
    """
    morphology = morphology_fn if morphology_fn is not None else _morphology_analyzable_default
    diacritizer = diacritizer_fn if diacritizer_fn is not None else _diacritizer_default

    words = _ARABIC_WORD_RE.findall(candidate_text)
    word_count = len(words)

    # --- Morphology track --------------------------------------------
    morph_score: float
    morph_available: bool
    if word_count == 0:
        morph_score = NEUTRAL_SCORE
        morph_available = False
    else:
        analyzable = 0
        morph_available = True
        for w in words:
            try:
                if morphology(w):
                    analyzable += 1
            except Exception:
                # Engine unavailable for the whole pass — treat as
                # neutral and stop trying.
                morph_available = False
                break
        morph_score = (analyzable / word_count) if morph_available else NEUTRAL_SCORE

    # --- Diacritization track ----------------------------------------
    diac_score: float
    diac_available: bool
    try:
        vocalized = diacritizer(candidate_text)
        diac_score = _diacritization_density(candidate_text, vocalized)
        diac_available = True
    except Exception:
        diac_score = NEUTRAL_SCORE
        diac_available = False

    # --- Aggregate ----------------------------------------------------
    # Re-weight on availability: when only one signal is real, give it
    # full weight rather than diluting with the unavailable neutral.
    if morph_available and diac_available:
        score = morph_score * morphology_weight + diac_score * diacritization_weight
    elif morph_available:
        score = morph_score
    elif diac_available:
        score = diac_score
    else:
        score = NEUTRAL_SCORE

    return Stage3RuleResult(
        score=score,
        morphology_score=morph_score,
        morphology_available=morph_available,
        diacritization_score=diac_score,
        diacritization_available=diac_available,
        word_count=word_count,
    )


def is_morphology_available() -> bool:
    """Cheap probe — True iff the CAMeL DB is installed.

    Mirrors `waraq.morphology.service.is_available` so the OCR runner
    can record `morphology_available` without forcing a real
    `analyze_word` call on a random word."""
    from waraq.morphology import is_available as _morph_available

    try:
        return bool(_morph_available())
    except Exception:
        return False


def _unused_typing_anchor() -> Any:
    """Reserved for future re-exports of CAMeL-typed adapter shims."""
    return None


__all__ = [
    "NEUTRAL_SCORE",
    "DiacritizerFn",
    "MorphologyAnalyzableFn",
    "Stage3RuleResult",
    "is_morphology_available",
    "rule_based_score",
]
