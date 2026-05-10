"""§4.16.3 — Multi-dimensional Hadith consensus engine.

Per Dokument 1 §4.16.3:

  Hadith verification works with a multidimensional comparison and
  consensus logic across all active sources. Comparison is by:
    - Wording proximity
    - Carriage by multiple sources
    - Proximity to the source named by the author
    - Isnād/collection reference
    - Vocalization consistency
    - Authenticity signals

  The linear confidence ranking (§3.5) acts as tie-breaker when the
  consensus logic does not yield a clear winner.

  Kutub as-Sitta: strong weighting factor in conflicts, no absolute
  precedence. With equally strong hits, Kutub-as-Sitta sources are
  preferred. A more wording-faithful, robust hit outside the Kutub
  as-Sitta can break precedence; the deviation is made visible in
  review.

This module is the **pure compute layer** — given a list of
`HadithCandidateHit` objects from various sources, it computes the
6-dimensional score, applies the Kutub-as-Sitta tiebreak, then the
§3.5 linear tiebreak, and returns the winning reference matn +
reference vocalization plus the full ranking.

Persistence (writing the chosen winner + losers as
`HadithSingleSourceResult` + `HadithAggregateResult` rows) lives in
`waraq.hadith.aggregation` so this module stays independently
testable without a DB.

**Calibration boundary**: the per-dimension weights, the tie
epsilon, and the authenticity-grade-to-score map are v1.0
implementation choices. §3.5 explicitly leaves these calibration-
deferred ("Concrete rates, pauses, upper limits, and resumption
times remain open and will be set after real measurement"). Tune
when real test data exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from waraq.arabic import to_skeleton
from waraq.hadith.enums import Quellenrolle, Vokalisierungsklasse
from waraq.hadith.vocalization import (
    aggregate_vocalization_class,
    classify_vocalization_class,
)

# §3.5 linear confidence ranking: quranenc > sunnah > Shamela > dorar
# > islamweb > others. Lower rank = stronger; used as the §4.16.3 tie-
# breaker after Kutub-as-Sitta preference is applied.
LINEAR_SOURCE_RANK: dict[str, int] = {
    "quranenc.com": 1,
    "sunnah.com": 2,
    "shamela": 3,
    "dorar.net": 4,
    "islamweb.net": 5,
    # Everything else gets rank 6 — the bucket for E-2/E-3/E-4 (currently
    # canonically suspended) and any future canonical source not yet ranked.
}
_DEFAULT_LINEAR_RANK = 6


# Kutub as-Sitta — six canonical Sunni hadith collections per §4.16.3.
# Match against `collection_label` after light normalization (lowercase,
# strip punctuation, collapse whitespace). Common transliteration
# variants are listed so callers don't have to normalize upstream
# differently.
KUTUB_AS_SITTA_LABELS: frozenset[str] = frozenset(
    {
        # Bukhari
        "sahih al-bukhari",
        "sahih bukhari",
        "bukhari",
        # Muslim
        "sahih muslim",
        "muslim",
        # Abu Dawud
        "sunan abi dawud",
        "sunan abu dawud",
        "abu dawud",
        "abi dawud",
        # Tirmidhi
        "jami at-tirmidhi",
        "jami` at-tirmidhi",
        "tirmidhi",
        "at-tirmidhi",
        # Nasa'i
        "sunan an-nasa'i",
        "sunan an-nasai",
        "nasa'i",
        "nasai",
        "an-nasai",
        # Ibn Majah
        "sunan ibn majah",
        "ibn majah",
    }
)


# Authenticity grade → score (calibration-deferred). Maps common
# grading terms to a 0..1 score; unknown grades fall to 0.5 (neutral).
_AUTHENTICITY_SCORES: dict[str, float] = {
    # Strong (Sahih variants).
    "sahih": 1.0,
    "صحيح": 1.0,
    "sahih li-ghayrihi": 0.9,
    # Acceptable (Hasan variants).
    "hasan": 0.75,
    "حسن": 0.75,
    "hasan li-ghayrihi": 0.65,
    # Weak.
    "daif": 0.3,
    "ضعيف": 0.3,
    # Fabricated.
    "mawdu": 0.0,
    "موضوع": 0.0,
}

# v1.0 weights. Equal across the 6 §4.16.3 dimensions — calibration
# territory. These are the implementation choice that should change
# when real corpus tests refine.
_DIM_WEIGHTS: dict[str, float] = {
    "wording_proximity": 1.0,
    "carriage": 1.0,
    "author_named_match": 1.0,
    "isnad_collection_quality": 1.0,
    "vocalization_consistency": 1.0,
    "authenticity": 1.0,
}

# Tie threshold — composite scores within `_TIE_EPSILON` are treated
# as ties for the Kutub-as-Sitta + linear tiebreak rules. v1.0
# default; tune in calibration.
_TIE_EPSILON = 0.05

# Wording-similarity threshold for "carriage by multiple sources" —
# two hits are considered to "carry the same matn" when their
# skeleton-stripped Levenshtein ratio is at least this value.
_CARRIAGE_THRESHOLD = 0.85


@dataclass(frozen=True, slots=True)
class HadithCandidateHit:
    """One candidate hit from a hadith source. Construction-time data;
    the consensus engine treats these as pure inputs."""

    source_name: str
    quellen_rolle: Quellenrolle
    matn_arabic: str
    matn_vocalized: str | None = None
    isnad_chain: list[str] = field(default_factory=list)
    collection_label: str = ""
    hadith_number: int | str | None = None
    authenticity_grade: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
    # Set True when this hit's source matches the source the author
    # named in their citation. Boosts the §4.16.3 "Proximity to
    # source named by author" dimension. Caller is responsible for
    # determining the match (via citation parsing / source mapping).
    matched_author_named_source: bool = False


@dataclass(frozen=True, slots=True)
class DimensionScores:
    """Per-hit score across the 6 §4.16.3 comparison dimensions."""

    wording_proximity: float
    carriage_count: int  # raw count of OTHER hits with skeleton similarity ≥ threshold
    author_named_match: float  # 0.0 or 1.0
    isnad_collection_quality: float  # 0..1
    vocalization_consistency: float  # 0..1
    authenticity_score: float  # 0..1


@dataclass(frozen=True, slots=True)
class HitScore:
    hit: HadithCandidateHit
    hit_index: int  # index into the original hits list
    dimensions: DimensionScores
    is_kutub_as_sitta: bool
    linear_rank: int  # §3.5 rank (lower = stronger)
    composite_score: float


@dataclass(frozen=True, slots=True)
class ConsensusResult:
    reference_matn: str
    reference_matn_source_index: int
    reference_vocalization: str | None
    reference_vocalization_source_index: int | None
    vokalisierungsklasse: Vokalisierungsklasse
    vokalisierungs_konflikt: bool
    ranking: list[HitScore]  # descending by composite_score
    consensus_summary: dict[str, Any]
    kutub_preference_applied: bool
    linear_tie_break_applied: bool


# --- Public API -----------------------------------------------------


def compute_consensus(
    candidates: list[HadithCandidateHit],
) -> ConsensusResult:
    """Compute the §4.16.3 consensus across `candidates`.

    Algorithm:
      1. For each candidate, compute the 6-dimensional score.
      2. Combine via weighted sum into a composite score.
      3. Sort hits by composite score (desc).
      4. If top-2 are within `_TIE_EPSILON`: prefer Kutub-as-Sitta.
      5. If still tied after Kutub preference: §3.5 linear ranking.
      6. Reference vocalization: hit with the best vocalization
         agreement (may differ from the matn winner per §4.16.7
         "with hadith there is deliberately no sole text carrier").

    Empty candidate list → raises ValueError.
    """
    if not candidates:
        raise ValueError("compute_consensus requires at least one candidate hit")

    skeletons = [to_skeleton(c.matn_arabic) for c in candidates]
    scores: list[HitScore] = []
    for idx, candidate in enumerate(candidates):
        dims = _score_dimensions(idx, candidates, skeletons)
        composite = _composite(dims)
        kutub = _is_kutub_as_sitta(candidate.collection_label)
        linear_rank = LINEAR_SOURCE_RANK.get(candidate.source_name, _DEFAULT_LINEAR_RANK)
        scores.append(
            HitScore(
                hit=candidate,
                hit_index=idx,
                dimensions=dims,
                is_kutub_as_sitta=kutub,
                linear_rank=linear_rank,
                composite_score=composite,
            )
        )

    # Step 3: sort by composite descending.
    ranking = sorted(scores, key=lambda s: -s.composite_score)

    kutub_applied, linear_applied = False, False
    if (
        len(ranking) > 1
        and abs(ranking[0].composite_score - ranking[1].composite_score) <= _TIE_EPSILON
    ):
        # Step 4: Kutub-as-Sitta preference among the top-tied group.
        tied_top = [
            s
            for s in ranking
            if abs(s.composite_score - ranking[0].composite_score) <= _TIE_EPSILON
        ]
        if any(s.is_kutub_as_sitta for s in tied_top):
            kutub_winners = [s for s in tied_top if s.is_kutub_as_sitta]
            if len(kutub_winners) == 1:
                # Exactly one Kutub-as-Sitta in tied top → it wins.
                kutub_winner = kutub_winners[0]
                if ranking[0].hit_index != kutub_winner.hit_index:
                    kutub_applied = True
                    ranking = [kutub_winner] + [
                        s for s in ranking if s.hit_index != kutub_winner.hit_index
                    ]
            else:
                # Multiple Kutub-as-Sitta tied → linear tiebreak among them.
                kutub_winner = min(kutub_winners, key=lambda s: s.linear_rank)
                if ranking[0].hit_index != kutub_winner.hit_index:
                    kutub_applied = True
                    linear_applied = True
                    ranking = [kutub_winner] + [
                        s for s in ranking if s.hit_index != kutub_winner.hit_index
                    ]
        else:
            # Step 5: no Kutub-as-Sitta in tied top → §3.5 linear tiebreak.
            linear_winner = min(tied_top, key=lambda s: s.linear_rank)
            if ranking[0].hit_index != linear_winner.hit_index:
                linear_applied = True
                ranking = [linear_winner] + [
                    s for s in ranking if s.hit_index != linear_winner.hit_index
                ]

    # Step 6: vocalization winner — separately determined per §4.16.7
    # ("when another source delivers the vocalization better, the
    # vocalization source can be determined and logged separately").
    voc_idx, voc_text, voc_klasse, voc_conflict = _pick_vocalization(candidates)

    matn_winner = ranking[0]
    consensus_summary = _build_summary(
        ranking=ranking,
        kutub_applied=kutub_applied,
        linear_applied=linear_applied,
        candidates=candidates,
        skeletons=skeletons,
    )

    return ConsensusResult(
        reference_matn=matn_winner.hit.matn_arabic,
        reference_matn_source_index=matn_winner.hit_index,
        reference_vocalization=voc_text,
        reference_vocalization_source_index=voc_idx,
        vokalisierungsklasse=voc_klasse,
        vokalisierungs_konflikt=voc_conflict,
        ranking=ranking,
        consensus_summary=consensus_summary,
        kutub_preference_applied=kutub_applied,
        linear_tie_break_applied=linear_applied,
    )


# --- Per-dimension scoring -----------------------------------------


def _score_dimensions(
    idx: int,
    candidates: list[HadithCandidateHit],
    skeletons: list[str],
) -> DimensionScores:
    candidate = candidates[idx]

    # Wording proximity: average skeleton similarity against all OTHER
    # hits. Single-hit run = 1.0 (no comparison context = neutral high).
    others_indices = [i for i in range(len(candidates)) if i != idx]
    if others_indices:
        sims = [_skeleton_similarity(skeletons[idx], skeletons[i]) for i in others_indices]
        wording = sum(sims) / len(sims)
    else:
        wording = 1.0

    # Carriage: count of OTHER hits with skeleton-similarity ≥ threshold.
    carriage = sum(
        1
        for i in others_indices
        if _skeleton_similarity(skeletons[idx], skeletons[i]) >= _CARRIAGE_THRESHOLD
    )

    # Author-named source proximity: 1.0 when matched, else 0.0.
    author_match = 1.0 if candidate.matched_author_named_source else 0.0

    # Isnād/collection quality: presence of isnād chain + collection label.
    isnad_present = bool(candidate.isnad_chain)
    coll_present = bool(candidate.collection_label)
    if isnad_present and coll_present:
        isnad_q = 1.0
    elif isnad_present or coll_present:
        isnad_q = 0.5
    else:
        isnad_q = 0.0

    # Vocalization consistency: when this hit has vocalization,
    # average §4.16.7 V-0=1.0 / V-1=0.6 / V-2=0.0 against other hits'
    # vocalizations. When this hit has none, score 0.5 (neutral —
    # missing vocalization isn't a vocalization conflict).
    if not candidate.matn_vocalized:
        voc_score = 0.5
    else:
        comparisons: list[float] = []
        for i in others_indices:
            other = candidates[i]
            if not other.matn_vocalized:
                continue
            klasse = classify_vocalization_class(candidate.matn_vocalized, other.matn_vocalized)
            if klasse == Vokalisierungsklasse.V_0:
                comparisons.append(1.0)
            elif klasse == Vokalisierungsklasse.V_1:
                comparisons.append(0.6)
            else:
                comparisons.append(0.0)
        voc_score = sum(comparisons) / len(comparisons) if comparisons else 0.5

    # Authenticity: lookup in the canonical map; unknown → 0.5.
    grade = (candidate.authenticity_grade or "").strip().casefold()
    auth_score = _AUTHENTICITY_SCORES.get(grade, 0.5)

    return DimensionScores(
        wording_proximity=wording,
        carriage_count=carriage,
        author_named_match=author_match,
        isnad_collection_quality=isnad_q,
        vocalization_consistency=voc_score,
        authenticity_score=auth_score,
    )


def _composite(dims: DimensionScores) -> float:
    # Carriage normalized: a hit carried by zero others contributes 0
    # to this dimension; carried by one or more contributes 1.0. The
    # canonical "more sources carrying the matn = stronger" without
    # an explicit upper bound (canon §4.16.3 doesn't quantify).
    carriage_norm = 1.0 if dims.carriage_count >= 1 else 0.0
    weighted = (
        _DIM_WEIGHTS["wording_proximity"] * dims.wording_proximity
        + _DIM_WEIGHTS["carriage"] * carriage_norm
        + _DIM_WEIGHTS["author_named_match"] * dims.author_named_match
        + _DIM_WEIGHTS["isnad_collection_quality"] * dims.isnad_collection_quality
        + _DIM_WEIGHTS["vocalization_consistency"] * dims.vocalization_consistency
        + _DIM_WEIGHTS["authenticity"] * dims.authenticity_score
    )
    total_weight = sum(_DIM_WEIGHTS.values())
    return weighted / total_weight


# --- Vocalization winner -------------------------------------------


def _pick_vocalization(
    candidates: list[HadithCandidateHit],
) -> tuple[int | None, str | None, Vokalisierungsklasse, bool]:
    """§4.16.7 — pick the best vocalization source.

    Returns:
        (source_index, vocalization_text, vokalisierungsklasse, vokalisierungs_konflikt)

    The winner is the candidate whose vocalization most agrees with
    others (highest avg V-0 score across pairwise comparisons). If no
    candidate has vocalization, returns (None, None, V_0, False).
    """
    voc_candidates = [(i, c.matn_vocalized) for i, c in enumerate(candidates) if c.matn_vocalized]
    if not voc_candidates:
        return (None, None, Vokalisierungsklasse.V_0, False)

    if len(voc_candidates) == 1:
        return (voc_candidates[0][0], voc_candidates[0][1], Vokalisierungsklasse.V_0, False)

    # Score each vocalized hit by avg agreement with others.
    best_idx = voc_candidates[0][0]
    best_score = -1.0
    pairwise_classes: list[Vokalisierungsklasse] = []
    for i, voc_i in voc_candidates:
        score = 0.0
        n = 0
        for j, voc_j in voc_candidates:
            if i == j:
                continue
            klasse = classify_vocalization_class(voc_i, voc_j)
            pairwise_classes.append(klasse)
            if klasse == Vokalisierungsklasse.V_0:
                score += 1.0
            elif klasse == Vokalisierungsklasse.V_1:
                score += 0.6
            n += 1
        avg = score / n if n else 0.0
        if avg > best_score:
            best_score = avg
            best_idx = i

    # Aggregate vocalization class across all pairs (§4.16.7 max rule).
    voc_klasse = aggregate_vocalization_class(pairwise_classes)
    voc_conflict = voc_klasse != Vokalisierungsklasse.V_0
    voc_text = next(c.matn_vocalized for i, c in enumerate(candidates) if i == best_idx)
    return (best_idx, voc_text, voc_klasse, voc_conflict)


# --- Helpers --------------------------------------------------------


def _is_kutub_as_sitta(collection_label: str) -> bool:
    norm = " ".join(collection_label.casefold().split())
    return norm in KUTUB_AS_SITTA_LABELS


def _skeleton_similarity(a: str, b: str) -> float:
    """Levenshtein-ratio similarity between two skeleton-stripped strings."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _build_summary(
    *,
    ranking: list[HitScore],
    kutub_applied: bool,
    linear_applied: bool,
    candidates: list[HadithCandidateHit],
    skeletons: list[str],
) -> dict[str, Any]:
    return {
        "winner": {
            "source_name": ranking[0].hit.source_name,
            "collection_label": ranking[0].hit.collection_label,
            "composite_score": ranking[0].composite_score,
            "is_kutub_as_sitta": ranking[0].is_kutub_as_sitta,
            "dimensions": {
                "wording_proximity": ranking[0].dimensions.wording_proximity,
                "carriage_count": ranking[0].dimensions.carriage_count,
                "author_named_match": ranking[0].dimensions.author_named_match,
                "isnad_collection_quality": ranking[0].dimensions.isnad_collection_quality,
                "vocalization_consistency": ranking[0].dimensions.vocalization_consistency,
                "authenticity_score": ranking[0].dimensions.authenticity_score,
            },
        },
        "tiebreak": {
            "kutub_as_sitta_preference_applied": kutub_applied,
            "linear_rank_applied": linear_applied,
        },
        "ranking": [
            {
                "source_name": s.hit.source_name,
                "collection_label": s.hit.collection_label,
                "composite_score": s.composite_score,
                "linear_rank": s.linear_rank,
                "is_kutub_as_sitta": s.is_kutub_as_sitta,
            }
            for s in ranking
        ],
        "candidate_count": len(candidates),
        "vocalized_candidate_count": sum(1 for c in candidates if c.matn_vocalized),
        "skeleton_pairwise_min_similarity": (
            min(
                (
                    _skeleton_similarity(skeletons[i], skeletons[j])
                    for i in range(len(skeletons))
                    for j in range(i + 1, len(skeletons))
                ),
                default=1.0,
            )
        ),
    }


__all__ = [
    "KUTUB_AS_SITTA_LABELS",
    "LINEAR_SOURCE_RANK",
    "ConsensusResult",
    "DimensionScores",
    "HadithCandidateHit",
    "HitScore",
    "compute_consensus",
]
