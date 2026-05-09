"""Arabic morphological analysis via CAMeL Tools (optional dependency).

CAMeL Tools is the chosen Arabic NLP stack for the click-word →
analysis feature in M4. It is **not** required for the rest of Waraq
to run, so this module:

- Imports `camel_tools` lazily on first call
- Raises a typed `MorphologyNotInstalled` when the package is absent
- Raises a typed `MorphologyDataMissing` when the morphology DB file
  has not been downloaded (`camel_data -i morphology-db-msa-r13`)

The HTTP layer maps both to 503 with a clear message so the frontend
can render a "morphology not configured" placeholder. Tests stub the
heavyweight Analyzer at the module-attribute level (no need to install
~500 MB of ML deps in CI).

`MorphologicalAnalysis` is the canonical result shape used by the API.
It carries the small subset of CAMeL fields the UI consumes — root,
lemma, POS, gloss, vocalized form, gender/number/person — and any extra
analyzer fields land in `extras` as a free-form dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from waraq.morphology.exceptions import MorphologyDataMissing, MorphologyNotInstalled

# Module-level singleton. Lazily initialized in `_get_analyzer()`. Tests
# that want to stub the analyzer can monkeypatch this binding.
_analyzer: Any = None


@dataclass(frozen=True, kw_only=True, slots=True)
class MorphologicalAnalysis:
    """One CAMeL-Tools analysis row, narrowed to the UI-relevant fields.

    Attributes:
        diac: vocalized (diacritized) form.
        lex: lexeme key.
        root: tri-/quadri-literal root.
        pos: part-of-speech tag.
        gloss: short English gloss (when available).
        gen: grammatical gender ("m", "f", "na").
        num: number ("s", "d", "p", "na").
        per: person ("1", "2", "3", "na").
        extras: any other CAMeL fields, raw.
    """

    diac: str
    lex: str
    root: str
    pos: str
    gloss: str | None
    gen: str | None
    num: str | None
    per: str | None
    extras: dict[str, Any] = field(default_factory=dict)


def _get_analyzer() -> Any:
    """Resolve the singleton CAMeL analyzer, raising the typed exceptions
    on either missing package or missing DB file."""
    global _analyzer
    if _analyzer is not None:
        return _analyzer
    try:
        from camel_tools.morphology.analyzer import Analyzer
        from camel_tools.morphology.database import MorphologyDB
    except ImportError as exc:
        raise MorphologyNotInstalled(
            "camel-tools is not installed in this environment. "
            "Run `pip install camel-tools` and download the morphology "
            "database with `camel_data -i morphology-db-msa-r13`."
        ) from exc
    try:
        db = MorphologyDB.builtin_db()
    except Exception as exc:
        raise MorphologyDataMissing(
            "camel-tools is installed but the morphology database is not "
            "available. Run `camel_data -i morphology-db-msa-r13` to "
            "download it."
        ) from exc
    _analyzer = Analyzer(db)
    return _analyzer


def is_available() -> bool:
    """Cheap check — True if the analyzer can be constructed without
    raising. Used by the HTTP layer for a probe endpoint that the UI
    can call to decide whether to enable the click-word affordance."""
    try:
        _get_analyzer()
        return True
    except (MorphologyNotInstalled, MorphologyDataMissing):
        return False


def analyze_word(word: str) -> list[MorphologicalAnalysis]:
    """Return all CAMeL morphological analyses for `word`.

    Args:
        word: surface form (Arabic). Must be non-empty after strip.

    Returns:
        List of `MorphologicalAnalysis`. Empty list when CAMeL has no
        analyses for the word (typical for misspellings / non-Arabic
        input).

    Raises:
        MorphologyNotInstalled: package absent.
        MorphologyDataMissing: package present but DB absent.
    """
    if not word.strip():
        return []
    analyzer = _get_analyzer()
    raw = analyzer.analyze(word)
    out: list[MorphologicalAnalysis] = []
    for r in raw:
        # CAMeL returns dict-like rows. Slice the canonical UI fields and
        # park the rest in extras.
        canonical = {"diac", "lex", "root", "pos", "gloss", "gen", "num", "per"}
        extras = {k: v for k, v in r.items() if k not in canonical}
        out.append(
            MorphologicalAnalysis(
                diac=str(r.get("diac", "")),
                lex=str(r.get("lex", "")),
                root=str(r.get("root", "")),
                pos=str(r.get("pos", "")),
                gloss=str(r["gloss"]) if r.get("gloss") else None,
                gen=str(r["gen"]) if r.get("gen") else None,
                num=str(r["num"]) if r.get("num") else None,
                per=str(r["per"]) if r.get("per") else None,
                extras=extras,
            )
        )
    return out
