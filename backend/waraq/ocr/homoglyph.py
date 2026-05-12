"""§3.4 Stage 4 — homoglyph correction + syllable separation harness.

Canon §3.4 Stage 4 names two concrete operations:

  1. **Homoglyph correction** for Arabic letter pairs OCR engines
     routinely confuse — `ر`/`ز`, `د`/`ذ`, and a handful of others
     where the only difference is a single dot.
  2. **Syllable separation** — collapsing accidental letter
     concatenations introduced by tight kerning at OCR time.

Same pattern as the Stage-1 layout harness (sub-batch B): the
**taxonomy + Protocol + persistence** ship in code; the *correction
implementation* is a pluggable adapter. The default adapter is a
**no-op identity** so deployments without a calibrated corrector see
no functional change — the canonical mechanism is wired and the
hook is in place for a real corrector (CAMeL morphology lookup,
dictionary check against the Shamela / AR-Referenzbestand corpora,
custom rules) to slot in.

Why no auto-correct in v1.0:
    A homoglyph swap is a content-changing edit. Per H-1/H-2 and the
    §2.2 "no silent winners" rule, automatic OCR-stage corrections
    that change the text without an audit trail violate canon. The
    canonical path is: detect candidate corrections → surface them
    as `HomoglyphSuggestion`s → caller (user or §3.4 Stage-3
    consensus) decides. The default adapter therefore returns no
    suggestions. A real corrector returns suggestions; the consumer
    routes them per the canonical Decision-Event flow.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

# --- Canonical Arabic homoglyph pairs ------------------------------

# Letter pairs OCR engines confuse. Each entry is `(left, right)`
# where the only typographic difference is dot count / placement.
# Canon-stable identifiers; renaming or removing is canon-shaped.
HOMOGLYPH_PAIRS: tuple[tuple[str, str], ...] = (
    ("ر", "ز"),  # raa vs zay (single dot above)
    ("د", "ذ"),  # daal vs dhaal (single dot above)
    ("ح", "خ"),  # haa vs khaa (single dot above)
    ("ج", "خ"),  # jeem vs khaa (dot moved)
    ("ح", "ج"),  # haa vs jeem (dot below vs above)
    ("ص", "ض"),  # saad vs daad (single dot above)
    ("ط", "ظ"),  # taa vs zaa (single dot above)
    ("ع", "غ"),  # ayn vs ghayn (single dot above)
    ("ف", "ق"),  # faa (1 dot) vs qaaf (2 dots)
    ("ب", "ت"),  # baa (1 dot below) vs taa (2 dots above)
    ("ت", "ث"),  # taa (2 dots) vs thaa (3 dots)
    ("ن", "ت"),  # nuun vs taa (dot count varies)
    ("ن", "ث"),  # nuun vs thaa
    ("ن", "ب"),  # nuun vs baa
)


# Quick lookup for "is `c` a homoglyph candidate, and what alternates?"
_ALTERNATES_BUILDER: dict[str, set[str]] = {}
for _a, _b in HOMOGLYPH_PAIRS:
    _ALTERNATES_BUILDER.setdefault(_a, set()).add(_b)
    _ALTERNATES_BUILDER.setdefault(_b, set()).add(_a)
ALTERNATES: dict[str, frozenset[str]] = {k: frozenset(v) for k, v in _ALTERNATES_BUILDER.items()}


@dataclass(frozen=True, kw_only=True, slots=True)
class HomoglyphSuggestion:
    """One candidate substitution at a specific position.

    Fields:
        position: 0-indexed character offset into the text where the
            substitution applies.
        original: the character actually emitted by OCR at `position`.
        replacement: the proposed alternate character.
        confidence: corrector-supplied score in [0, 1]. 1.0 means "I
            am confident this swap is correct"; 0.5 is a coin flip.
            The default adapter never emits suggestions, so this
            field is purely a contract for real adapters.
        rationale: free-form explanation surfaced in audit (e.g.
            "candidate 'كتاب' present in Shamela; OCR'd 'كناب' is
            not a Shamela token"). May be empty.
    """

    position: int
    original: str
    replacement: str
    confidence: float
    rationale: str = ""


HomoglyphCorrector = Callable[[str], list[HomoglyphSuggestion]]


def _default_homoglyph_corrector(text: str) -> list[HomoglyphSuggestion]:
    """v1.0 fallback: no suggestions. Preserves OCR output unchanged.

    Real adapters (CAMeL morphology lookup; Shamela / AR-Reference
    dictionary check; rule-based grammar validator) plug in via the
    `corrector` parameter on `find_homoglyph_candidates`.
    """
    _ = text
    return []


def find_homoglyph_candidates(
    text: str,
    *,
    corrector: HomoglyphCorrector | None = None,
) -> list[HomoglyphSuggestion]:
    """Run the configured corrector over `text`. Returns suggestions
    sorted by `(position, replacement)` for stable iteration order.

    Default behaviour is no suggestions — see module docstring on
    why v1.0 doesn't auto-correct.
    """
    fn = corrector if corrector is not None else _default_homoglyph_corrector
    suggestions = fn(text)
    return sorted(suggestions, key=lambda s: (s.position, s.replacement))


def is_homoglyph_candidate(char: str) -> bool:
    """Pure: would `char` participate in any canonical homoglyph
    pair? Useful for highlighting suspicious positions in the UI
    even when no corrector is configured."""
    return char in ALTERNATES


# ---------------------------------------------------------------------
# Sub-batch H — real corrector backed by an analyzability oracle
# ---------------------------------------------------------------------


# Word-analyzability oracle — returns True if `word` is a recognized
# Arabic word (e.g., morphologically analyzable, in a dictionary,
# or attested in a known corpus).
WordAnalyzableFn = Callable[[str], bool]


def make_dictionary_homoglyph_corrector(
    is_known_word: WordAnalyzableFn,
    *,
    min_word_skeleton_len: int = 3,
    confidence_known_unknown: float = 0.85,
) -> HomoglyphCorrector:
    """Build a `HomoglyphCorrector` backed by an analyzability oracle.

    Algorithm: for each Arabic word ≥ `min_word_skeleton_len`
    characters in the input that fails the oracle, generate every
    single-character homoglyph swap (one per position with a
    canonical alternate). For each swap that succeeds the oracle,
    emit a `HomoglyphSuggestion` with confidence
    `confidence_known_unknown`. Words the oracle already recognizes
    are passed through with no suggestions (no spurious flagging).

    The oracle is the pluggable knob: production wires
    `make_camel_homoglyph_corrector()` (CAMeL Tools morphology,
    when the DB is installed) or a Shamela-skeleton-frequency
    callable; tests inject a deterministic stub.

    Returns a sync `HomoglyphCorrector`. Per H-1/H-2 + §2.2 the
    corrector NEVER mutates the text — it surfaces candidates only;
    the user / Stage-3 consensus decides.
    """
    import re as _re

    arabic_word_re = _re.compile(r"[؀-ۿ]+")

    def _corrector(text: str) -> list[HomoglyphSuggestion]:
        suggestions: list[HomoglyphSuggestion] = []
        # Skeleton-strip uses the same canonicalization the rest of
        # the OCR pipeline uses so cross-stage signals align.
        for m in arabic_word_re.finditer(text):
            word = m.group(0)
            if len(word) < min_word_skeleton_len:
                continue
            try:
                if is_known_word(word):
                    continue
            except Exception:
                # Defensive: oracle quirks shouldn't kill the corrector.
                continue
            word_start = m.start()
            for local_i, char in enumerate(word):
                alts = ALTERNATES.get(char)
                if not alts:
                    continue
                for replacement in alts:
                    swapped = word[:local_i] + replacement + word[local_i + 1 :]
                    try:
                        if not is_known_word(swapped):
                            continue
                    except Exception:
                        continue
                    suggestions.append(
                        HomoglyphSuggestion(
                            position=word_start + local_i,
                            original=char,
                            replacement=replacement,
                            confidence=confidence_known_unknown,
                            rationale=(
                                f"swap '{char}'→'{replacement}' yields a "
                                f"recognized form '{swapped}'"
                            ),
                        )
                    )
        return suggestions

    return _corrector


def make_camel_homoglyph_corrector(*, confidence_known_unknown: float = 0.85) -> HomoglyphCorrector:
    """Build a CAMeL-Tools-backed `HomoglyphCorrector`.

    Uses CAMeL morphology analyzability as the oracle: a word is
    "known" iff `analyze_word(word)` returns at least one analysis.
    When the morphology DB isn't installed (`MorphologyDataMissing`)
    or CAMeL itself is absent, the oracle returns True for every
    word — which collapses the corrector to no suggestions, the
    canonical neutral fallback.

    Production wiring path. Tests inject the simpler
    `make_dictionary_homoglyph_corrector` with a deterministic
    word-set oracle.
    """
    from waraq.morphology.exceptions import MorphologyDataMissing, MorphologyNotInstalled

    def _is_known(word: str) -> bool:
        try:
            from waraq.morphology.service import analyze_word

            return len(analyze_word(word)) > 0
        except (MorphologyNotInstalled, MorphologyDataMissing):
            # CAMeL DB missing → treat every word as known so the
            # corrector emits zero suggestions (canon-honest no-op).
            return True
        except Exception:
            # Defensive: any other CAMeL quirk → no-op.
            return True

    return make_dictionary_homoglyph_corrector(
        _is_known,
        confidence_known_unknown=confidence_known_unknown,
    )


@dataclass(frozen=True, kw_only=True, slots=True)
class SyllableSeparationResult:
    """Output of `separate_syllables` — both the (possibly modified)
    text and the list of insertion points the separator chose.

    `insertions` is `[(position, inserted_char)]` keyed against the
    ORIGINAL text (before insertion); audit consumers use it to align
    the corrected output with the OCR raw output.
    """

    text: str
    insertions: list[tuple[int, str]] = field(default_factory=list)


SyllableSeparator = Callable[[str], SyllableSeparationResult]


def _default_syllable_separator(text: str) -> SyllableSeparationResult:
    """v1.0 identity. Real adapters compute syllable boundaries from
    morphology + tight-kerning heuristics."""
    return SyllableSeparationResult(text=text, insertions=[])


def separate_syllables(
    text: str,
    *,
    separator: SyllableSeparator | None = None,
) -> SyllableSeparationResult:
    """Run the configured syllable separator. Default is identity."""
    fn = separator if separator is not None else _default_syllable_separator
    return fn(text)


__all__ = [
    "ALTERNATES",
    "HOMOGLYPH_PAIRS",
    "HomoglyphCorrector",
    "HomoglyphSuggestion",
    "SyllableSeparationResult",
    "SyllableSeparator",
    "WordAnalyzableFn",
    "find_homoglyph_candidates",
    "is_homoglyph_candidate",
    "make_camel_homoglyph_corrector",
    "make_dictionary_homoglyph_corrector",
    "separate_syllables",
]
