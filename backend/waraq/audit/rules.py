"""T-8.1.2 — Audit rule check functions A-01..D-03 (13 rules per ITB §4).

Each rule is a `RuleCheck` callable: takes a Segment, returns a list of
`RuleFinding`. The rule's `regelkennung` is set as a function attribute
so the run summary can enumerate which rules executed.

Detection logic in v1.0 is **first-pass structural matching** —
substring detection, regex patterns, glossary lookups. Per
Sprint 3 §B "Calibration values: ... configurable, never pre-set"; the
matchers err on the side of catching obvious violations and leaving
finer linguistic precision to post-Gold-Corpus refinement.

A Segment's `text_content` represents the CURRENT segment state. After
OCR it's Arabic source; after a translation pass it's German target.
For audit purposes, rule families A/B operate on Arabic source → target
pairings (so they need access to the originating revision); rule
families C/D often need both. To keep the v1.0 surface small, every
rule reads:

  source = first revision's `after_text` (OCR baseline)
  target = latest `re_translate` revision's `after_text`, or `None`

via the `RuleContext` injected by the audit-run. Rules that need only
the source (e.g. C-02 first-occurrence, D-02 sajʿ in source) operate
on `source` alone; rules that compare source vs target read both. When
target is None the rule yields no findings (translation hasn't run yet).

For rule bodies the rule_id → severity mapping is NOT encoded here.
The audit run's SeverityTable is the only source of truth — swap the
table to reclassify without touching rule code (R-S3-04).
"""

from __future__ import annotations

import re
import uuid as _uuid
from collections.abc import Callable

from waraq.audit.service import RuleCheck, RuleContext, RuleFinding
from waraq.schemas import Segment

# Broad Arabic-block letter class. Covers the full U+0600..U+06FF range
# so diacritic marks (U+064B..U+0652) inside vocalized words don't break
# multi-letter `+` matches. The narrower `[ء-ي]` class is U+0621..U+064A
# only and silently drops to zero on text like `كتابُهُ` after the first
# diacritic mark.
_ARLETTER = r"[؀-ۿ]"


def _decorator_for(regelkennung: str) -> Callable[[RuleCheck], RuleCheck]:
    """Stamp `regelkennung` on the rule function so the audit-run can
    enumerate the active rule set without inspecting source."""

    def deco(fn: RuleCheck) -> RuleCheck:
        fn.regelkennung = regelkennung  # type: ignore[attr-defined]
        return fn

    return deco


# ---------------------------------------------------------------------
# A-class — discourse particles
#
# Detection in v1.0 is purely token-presence: the rule fires iff the
# canonical Arabic particle appears in the source text but the target
# carries no equivalent rendering. The "equivalent rendering" set is a
# small per-rule list; the matcher is intentionally coarse so it's
# explainable. Calibration is post-Gold-Corpus.
# ---------------------------------------------------------------------

# Vowelized + bare forms of `inna` / `anna` (A-01).
_INNA_FORMS = ("إنّ", "إنّ", "إن", "أنّ", "أنّ", "أن")
_INNA_RENDERINGS = ("wahrlich", "fürwahr", "dass", "daß")

_LAM_EMPHASIS_RENDERINGS = ("wahrlich", "fürwahr", "ja")

_FA_FORMS = ("فَ", "فَ", "ف")
_FA_RENDERINGS = ("so", "dann", "und so")


@_decorator_for("A-01")
def rule_a_01(segment: Segment) -> list[RuleFinding]:
    """`إِنَّ` / `أَنَّ` not translated.

    Source carries one of the inna/anna forms but target carries no
    canonical rendering token.
    """
    src, tgt = _source_target(segment)
    if tgt is None:
        return []
    if not _contains_any(src, _INNA_FORMS):
        return []
    if _contains_any_ci(tgt, _INNA_RENDERINGS):
        return []
    return [_finding(segment.satz_uuid, "A-01", "inna_or_anna_present_no_rendering")]


@_decorator_for("A-02")
def rule_a_02(segment: Segment) -> list[RuleFinding]:
    """Emphatic `لَ` not rendered as emphasis.

    Heuristic: a fatha-marked lām followed by Arabic letter at the start
    of a word indicates emphasis; if no canonical emphasis token in target.
    """
    src, tgt = _source_target(segment)
    if tgt is None:
        return []
    # Emphatic la pattern: ل with fatha followed by an Arabic letter.
    if not re.search(rf"(?:^|\s)لَ{_ARLETTER}", src):
        return []
    if _contains_any_ci(tgt, _LAM_EMPHASIS_RENDERINGS):
        return []
    return [_finding(segment.satz_uuid, "A-02", "emphatic_lam_no_rendering")]


@_decorator_for("A-03")
def rule_a_03(segment: Segment) -> list[RuleFinding]:
    """`فَ` not context-sensitively translated.

    Source carries a fa-prefix; target carries none of the canonical
    sequencing/conjunction tokens.
    """
    src, tgt = _source_target(segment)
    if tgt is None:
        return []
    if not _contains_any(src, _FA_FORMS):
        return []
    if _contains_any_ci(tgt, _FA_RENDERINGS):
        return []
    return [_finding(segment.satz_uuid, "A-03", "fa_prefix_no_rendering")]


# ---------------------------------------------------------------------
# B-class — morpho-syntactic structure
# ---------------------------------------------------------------------


@_decorator_for("B-01")
def rule_b_01(segment: Segment) -> list[RuleFinding]:
    """Idāfa zu frei aufgelöst.

    Heuristic for v1.0: the source has 2+ Arabic-script tokens with a
    suffix-pronoun pattern (-hu / -hā / -him / -hum / -hunna) and the
    target uses 'des' / 'der' / 'genitive' indicators less than expected.
    Crude — flagged with a low-confidence note.
    """
    src, tgt = _source_target(segment)
    if tgt is None:
        return []
    has_idafa = re.search(rf"{_ARLETTER}+(ه|ها|هم|هن|نا)\b", src) is not None
    if not has_idafa:
        return []
    if re.search(r"\b(des|der|sein|ihr|unser)\b", tgt, re.IGNORECASE):
        return []
    return [_finding(segment.satz_uuid, "B-01", "idafa_present_no_genitive")]


@_decorator_for("B-02")
def rule_b_02(segment: Segment) -> list[RuleFinding]:
    """Dual nicht sichtbar.

    Heuristic: a -ān / -ayn suffix on an Arabic noun in source, with no
    "beide" / "zwei" / dual-marker word in target.
    """
    src, tgt = _source_target(segment)
    if tgt is None:
        return []
    if not re.search(rf"{_ARLETTER}+(ان|ين)\b", src):
        return []
    if re.search(r"\b(beide|zwei|paar)\b", tgt, re.IGNORECASE):
        return []
    return [_finding(segment.satz_uuid, "B-02", "dual_present_no_marker")]


@_decorator_for("B-03")
def rule_b_03(segment: Segment) -> list[RuleFinding]:
    """Genusunterschied nicht übertragen.

    Marker-of-marker heuristic: source uses a feminine ending (-a) on a
    noun + verb agreement, target uses a generic gender. Crude in v1.0.
    """
    src, tgt = _source_target(segment)
    if tgt is None:
        return []
    if not re.search(rf"{_ARLETTER}+ة\b", src):
        return []
    # If target has any feminine-marked word ending (-in -e -es), accept.
    if re.search(r"\b\w+(in|innen)\b", tgt, re.IGNORECASE):
        return []
    return [_finding(segment.satz_uuid, "B-03", "feminine_marker_lost")]


@_decorator_for("B-04")
def rule_b_04(segment: Segment) -> list[RuleFinding]:
    """Konditionalsatz nicht textnah.

    Heuristic: source contains an Arabic conditional particle
    (إذا / إن / لو) but target lacks 'wenn' / 'falls' / 'sollte'.
    """
    src, tgt = _source_target(segment)
    if tgt is None:
        return []
    if not re.search(r"\b(إذا|إن|لو)\b", src):
        return []
    if re.search(r"\b(wenn|falls|sollte)\b", tgt, re.IGNORECASE):
        return []
    return [_finding(segment.satz_uuid, "B-04", "conditional_present_no_marker")]


# ---------------------------------------------------------------------
# C-class — content-integrity
# ---------------------------------------------------------------------


@_decorator_for("C-01")
def rule_c_01(segment: Segment, ctx: RuleContext | None = None) -> list[RuleFinding]:
    """Terminologieeintrag verletzt.

    Phase 4 sub-batch G upgrade: when the audit-run pre-loaded the
    project glossary into `ctx.glossary`, the rule actually compares
    every glossary entry whose canonical_label appears in the source
    against the target — flagging entries whose canonical gloss is
    NOT present in the target.

    Both signals are kept:

      - The legacy `[TERM-VIOLATION]` marker still fires (deterministic
        path used by tests + manual reviewer flagging).
      - When `ctx.glossary` is non-empty, every missing-gloss case
        produces an additional C-01 finding with detection_context
        carrying `concept_id`, `canonical_label`, `expected_gloss`.

    Per the pure-by-design contract: this rule still does NO DB access
    of its own; the audit-runner builds the context once and passes it
    in. When `ctx is None` (legacy callers / tests without context)
    the marker-only behaviour is preserved exactly.
    """
    src, tgt = _source_target(segment)
    if tgt is None:
        return []

    findings: list[RuleFinding] = []
    if "[TERM-VIOLATION]" in tgt:
        findings.append(_finding(segment.satz_uuid, "C-01", "terminology_violation_marker"))

    if ctx is not None and ctx.glossary:
        for entry in ctx.glossary:
            label = entry.canonical_label
            if not label or label not in src:
                continue
            if entry.gloss in tgt:
                continue
            findings.append(
                RuleFinding(
                    regelkennung="C-01",
                    satz_uuid=segment.satz_uuid,
                    detection_context={
                        "match": "glossary_lookup",
                        "concept_id": str(entry.concept_id),
                        "canonical_label": entry.canonical_label,
                        "expected_gloss": entry.gloss,
                        "binding_level": entry.binding_level,
                    },
                )
            )
    return findings


@_decorator_for("C-02")
def rule_c_02(segment: Segment) -> list[RuleFinding]:
    """Islamischer Fachbegriff ohne Erstauftreten-Behandlung.

    Heuristic: target contains an Islamic-term token (e.g., 'Hadith',
    'Sunna', 'Salat') without a parenthesized Arabic original or a
    footnote marker.
    """
    _, tgt = _source_target(segment)
    if tgt is None:
        return []
    islamic_terms = (
        "hadith",
        "sunna",
        "salat",
        "schari'a",
        "scharia",
        "fiqh",
        "tafsir",
        "ijma",
        "qiyas",
    )
    has_term = any(t in tgt.lower() for t in islamic_terms)
    if not has_term:
        return []
    if "(" in tgt and ")" in tgt:
        return []
    if "[Ü.]" in tgt or re.search(r"\[\d+\]", tgt):
        return []
    return [_finding(segment.satz_uuid, "C-02", "islamic_term_no_first_occurrence_treatment")]


@_decorator_for("C-03")
def rule_c_03(segment: Segment) -> list[RuleFinding]:
    """Translatorische Ergänzung nicht markiert.

    Heuristic: target's word-count is significantly larger than the
    source's (>= 2x) but no `[Ü.]` footnote marker is present.
    """
    src, tgt = _source_target(segment)
    if tgt is None:
        return []
    src_words = len(src.split())
    tgt_words = len(tgt.split())
    if src_words == 0 or tgt_words < src_words * 2:
        return []
    if "[Ü.]" in tgt:
        return []
    return [_finding(segment.satz_uuid, "C-03", "translator_addition_unmarked")]


# ---------------------------------------------------------------------
# D-class — style and formatting
# ---------------------------------------------------------------------


@_decorator_for("D-01")
def rule_d_01(segment: Segment) -> list[RuleFinding]:
    """Metapher / Redewendung nicht wörtlich mit Fussnote.

    Heuristic detection_context marker `[METAPHER]` in target, with no
    `[Ü.]` footnote nearby.
    """
    _, tgt = _source_target(segment)
    if tgt is None:
        return []
    if "[METAPHER]" in tgt and "[Ü.]" not in tgt:
        return [_finding(segment.satz_uuid, "D-01", "metaphor_no_footnote")]
    return []


@_decorator_for("D-02")
def rule_d_02(segment: Segment) -> list[RuleFinding]:
    """Sajʿ ohne Hinweis in Fussnote.

    Heuristic: source carries the Sajʿ marker (a deliberate test/
    detection signal `[SAJʿ]`) but target lacks the Sajʿ-Reimprosa
    footnote text.
    """
    src, tgt = _source_target(segment)
    if tgt is None:
        return []
    if "[SAJʿ]" not in src:
        return []
    if "Sajʿ" in tgt or "Reimprosa" in tgt:
        return []
    return [_finding(segment.satz_uuid, "D-02", "sajʿ_no_footnote")]


@_decorator_for("D-03")
def rule_d_03(segment: Segment) -> list[RuleFinding]:
    """Religiöse Formel nicht nach Verzeichnis.

    Heuristic: target contains an Islamic religious-formula English
    pseudo-rendering (e.g. 'pbuh', 'a.s.', 'r.a.') instead of the
    canonical German Verzeichnis form. Real implementation reads the
    Verzeichnis from the project; v1.0 catches the obvious English
    abbreviations.
    """
    _, tgt = _source_target(segment)
    if tgt is None:
        return []
    pseudo = ("pbuh", "(a.s.)", "(r.a.)", "saw")
    if any(p in tgt.lower() for p in pseudo):
        return [_finding(segment.satz_uuid, "D-03", "religious_formula_pseudo_rendering")]
    return []


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _source_target(segment: Segment) -> tuple[str, str | None]:
    """Read the segment's source + target directly from `text_content`.

    Per the v1.0 simplification documented in the module header: the
    audit-run rules operate on the segment's CURRENT text + the most
    recent re_translate revision via the run-context. To keep rule
    bodies pure and DB-free, we encode source/target in `text_content`
    using a simple `\n---\n` separator marker. The audit-run wires this
    via SegmentSnapshot in service.py — but for the v1.0 first-pass we
    treat the raw `text_content` as both, splitting on the marker when
    present.

    Production refinement (M5+): rules read from a `RuleContext` object
    that pre-loads the original source revision and the latest
    re_translate revision via a SQL join, eliminating the marker
    convention. Until then this convention keeps tests deterministic.
    """
    raw = segment.text_content or ""
    if "\n---\n" in raw:
        src, tgt = raw.split("\n---\n", 1)
        return src, tgt
    return raw, None


def _contains_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(n in haystack for n in needles)


def _contains_any_ci(haystack: str, needles: tuple[str, ...]) -> bool:
    h = haystack.lower()
    return any(n.lower() in h for n in needles)


def _finding(satz_uuid: _uuid.UUID, regelkennung: str, marker: str) -> RuleFinding:
    return RuleFinding(
        regelkennung=regelkennung,
        satz_uuid=satz_uuid,
        detection_context={"marker": marker},
    )


# Convenient registry of all 13 rules (default rule set).
ALL_RULES: tuple[RuleCheck, ...] = (
    rule_a_01,
    rule_a_02,
    rule_a_03,
    rule_b_01,
    rule_b_02,
    rule_b_03,
    rule_b_04,
    rule_c_01,
    rule_c_02,
    rule_c_03,
    rule_d_01,
    rule_d_02,
    rule_d_03,
)
