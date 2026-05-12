"""§3.4 Stage-3 statistical track — Shamela Mode-A plausibility consumer.

Per §3.5 Mode A: "system-triggered in OCR Stage 3 as plausibility check
of recognized text fragments". Sub-batch B' shipped the data substrate
(Bukhari + the canonical-floor lexicons live in the `shamela_*`
tables); this module shipped 2026-05-10 wires that into Stage-3.

Signal semantics
----------------
A Mode-A skeleton hit means: "this OCR fragment matches a verbatim
section in a known classical text". That is **strong** evidence the
OCR is correct — classical Arabic books quote each other, so a hit
doesn't prove the SOURCE document, but it does prove the *reading*.

Block-class scoping
-------------------
HADITH-class blocks scope the lookup to Kutub-as-Sitta (per §4.16.3 P-2
candidate construction). Other classes use the full corpus so a
quotation from a lexicon, a fiqh manual, etc. still surfaces.

Score rule (v1.0):
  - 0 hits   → 0.50 (neutral; no information either way)
  - 1+ hits  → 0.85 (ACCEPTED-band per §4.4 confidence taxonomy)

We deliberately do not boost beyond 0.85 — multi-hit doesn't prove a
better match than single-hit (the candidate could be a common-cited
phrase). 0.50 vs 0.85 is the canonical split: "no signal" vs "match".
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.schemas.enums import BlockClass
from waraq.shamela.lookup import ShamelaHit, find_by_skeleton

# v1.0 score band — see module docstring rationale.
NEUTRAL_SCORE: float = 0.50
HIT_SCORE: float = 0.85

# Block classes that route to Kutub-as-Sitta only. HADITH is the
# canonical case per §4.16.3; other classes use the full corpus.
_KUTUB_SCOPED: frozenset[BlockClass] = frozenset({BlockClass.HADITH})


@dataclass(frozen=True, kw_only=True, slots=True)
class Stage3StatisticalResult:
    """Output of one Stage-3 statistical pass over a candidate text.

    Attributes:
        score: [0, 1] plausibility score. The Stage-3 aggregator
            (`waraq.ocr.stage3`) folds it into the multi-track vote.
        hit_count: How many Shamela sections matched the candidate's
            skeleton. Recorded on the OCR-PO for audit so a reviewer
            can drill into which texts hit.
        scoped_to_kutub_as_sitta: True when the lookup was constrained
            to the 6 Kutub collections (HADITH-class blocks).
        sample_titles: First N matching text titles, for human-readable
            audit. Empty when `hit_count == 0`.
    """

    score: float
    hit_count: int
    scoped_to_kutub_as_sitta: bool
    sample_titles: tuple[str, ...]


async def statistical_score(
    *,
    session: AsyncSession,
    candidate_text: str,
    block_class: BlockClass,
    sample_limit: int = 5,
) -> Stage3StatisticalResult:
    """Run the Mode-A skeleton lookup and convert to a [0, 1] score.

    Args:
        session: Active async session — same scope as the OCR job.
        candidate_text: The Stage-2-consensus text being validated.
        block_class: Drives Kutub-as-Sitta scoping (HADITH only).
        sample_limit: How many matching titles to record on the result
            for audit. The `find_by_skeleton` lookup itself uses a
            larger internal limit (50) to count hits reliably.

    Empty / pure-whitespace candidates are neutral by construction —
    the skeleton is empty, so no meaningful lookup is possible.
    """
    text = candidate_text.strip()
    if not text:
        return Stage3StatisticalResult(
            score=NEUTRAL_SCORE,
            hit_count=0,
            scoped_to_kutub_as_sitta=False,
            sample_titles=(),
        )

    scope_kutub = block_class in _KUTUB_SCOPED
    hits: list[ShamelaHit] = await find_by_skeleton(
        session,
        candidate_text=text,
        only_kutub_as_sitta=scope_kutub,
        limit=50,
    )
    score = HIT_SCORE if hits else NEUTRAL_SCORE
    sample_titles = tuple(dict.fromkeys(h.title for h in hits[:sample_limit]))
    return Stage3StatisticalResult(
        score=score,
        hit_count=len(hits),
        scoped_to_kutub_as_sitta=scope_kutub,
        sample_titles=sample_titles,
    )


__all__ = [
    "HIT_SCORE",
    "NEUTRAL_SCORE",
    "Stage3StatisticalResult",
    "statistical_score",
]
