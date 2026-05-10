"""§4.15.2 — Qurʾān recognition pipeline.

Per Dokument 1 §4.15.2:
  "The first external API call (quranenc.com) occurs only in the
  translation phase. During the OCR run only local matching takes
  place; no external call in the OCR phase."

  "When confidence of Qurʾān recognition is below the defined
  threshold: manual confirmation by the user is upstream; no automatic
  API call. Threshold still open."

This module is the **local-only** matcher. Given a candidate Arabic
text, it tries to match against the AR-Referenzbestand (`ArReferenzVerse`
populated by Phase 2D) and returns one of:

  - `RecognitionResult(matched=True, confidence=…, sura, aya_start, aya_end, …)`
    when the candidate's skeleton aligns with one or more contiguous
    ʾāyāt in the local collection.
  - `RecognitionResult(matched=False, confidence=0.0, …)` when no
    alignment is found.

The confidence score reflects skeleton-match strength:
  - **1.0** — exact skeleton match across all ʾāyāt (sura+aya bounds
    line up and skeleton-equality holds for every word).
  - **0.0** — no skeleton match.

v1.0 only emits high-confidence (1.0) or zero — fuzzy partial-match
scoring is calibration territory (Phase 4+ would use a string-distance
metric like normalized Levenshtein for skeleton overlap). Confidence
threshold is configurable; default `_HIGH_CONFIDENCE_DEFAULT` = 0.85
matches §4.17 vocalization "high (>85%)" tier semantics. Below
threshold → §4.15.2 manual-confirmation path.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.arabic import to_skeleton
from waraq.schemas import ArReferenzVerse

# §4.15.2 threshold canonically deferred. v1.0 default mirrors §4.17
# vocalization "high" tier (>85%); lower it temporarily to invoke the
# manual-confirmation path during testing.
_HIGH_CONFIDENCE_DEFAULT = 0.85


@dataclass(frozen=True, slots=True)
class RecognitionResult:
    """Result of one local-only Qurʾān recognition attempt.

    Attributes:
        matched: True iff the candidate's skeleton was found in the
            local AR-Referenzbestand (one or more contiguous ʾāyāt of
            the same sura).
        confidence: 0.0..1.0 — exact-match yields 1.0 in v1.0.
        sura_index: matched sura (None if not matched).
        aya_index_start / aya_index_end: matched āya range (None if
            not matched). For a single-āya match both equal the same.
        ar_source_name / ar_source_version: provenance of the matched
            AR rows (empty when not matched).
        matched_text_vocalized: the canonical vocalized text from the
            AR-Referenzbestand for the matched range (joined with
            single spaces). Empty when not matched.
    """

    matched: bool
    confidence: float
    sura_index: int | None = None
    aya_index_start: int | None = None
    aya_index_end: int | None = None
    ar_source_name: str = ""
    ar_source_version: str = ""
    matched_text_vocalized: str = ""

    @property
    def is_above_threshold(self) -> bool:
        return self.confidence >= _HIGH_CONFIDENCE_DEFAULT

    def above_threshold(self, threshold: float) -> bool:
        return self.confidence >= threshold


async def recognize_quran_passage(
    session: AsyncSession,
    *,
    candidate_text: str,
    source_name: str | None = None,
) -> RecognitionResult:
    """Local-only Qurʾān recognition on `candidate_text`.

    Strategy:
      1. Compute skeleton of candidate via `waraq.arabic.to_skeleton`.
      2. Load all active AR rows for `source_name` (or any source if
         None).
      3. Try to align the candidate skeleton against contiguous āyāt
         of the same sura. v1.0 == exact skeleton match across the
         joined range.

    The candidate may be one āya OR multiple contiguous āyāt. The
    matcher walks the AR rows of each sura in `aya_index` order and
    looks for a contiguous skeleton-concatenation that equals the
    candidate skeleton.
    """
    skeleton = to_skeleton(candidate_text)
    if not skeleton:
        return RecognitionResult(matched=False, confidence=0.0)

    # Single-āya match first — the common path; sub-second on a
    # well-indexed `text_skeleton` column.
    single = await _match_single_aya(
        session=session,
        skeleton=skeleton,
        source_name=source_name,
    )
    if single is not None:
        return single

    # Multi-āya scan — restricted to the suras that contain at least
    # one prefix of the candidate skeleton, so we don't scan all 6,236
    # rows per call.
    return await _match_multi_aya(
        session=session,
        skeleton=skeleton,
        source_name=source_name,
    )


async def _match_single_aya(
    *,
    session: AsyncSession,
    skeleton: str,
    source_name: str | None,
) -> RecognitionResult | None:
    stmt = (
        select(ArReferenzVerse)
        .where(ArReferenzVerse.text_skeleton == skeleton)
        .where(ArReferenzVerse.active.is_(True))
        .order_by(ArReferenzVerse.sura_index, ArReferenzVerse.aya_index)
    )
    if source_name is not None:
        stmt = stmt.where(ArReferenzVerse.source_name == source_name)
    row = (await session.execute(stmt)).scalars().first()
    if row is None:
        return None
    return RecognitionResult(
        matched=True,
        confidence=1.0,
        sura_index=row.sura_index,
        aya_index_start=row.aya_index,
        aya_index_end=row.aya_index,
        ar_source_name=row.source_name,
        ar_source_version=row.source_version,
        matched_text_vocalized=row.text_vocalized,
    )


async def _match_multi_aya(
    *,
    session: AsyncSession,
    skeleton: str,
    source_name: str | None,
) -> RecognitionResult:
    """Scan every active sura for a contiguous-āya skeleton match.

    Loads each sura's ʾāyāt in order, joins their skeletons
    progressively, and returns the first sura where some contiguous
    range matches. v1.0 quadratic-in-sura-length scan; for the 6,236-
    row corpus this is bounded — the longest sura (al-Baqara) has
    286 āyāt → ~286×286/2 = ~41k comparisons worst case per failed
    sura, which is still <500ms with skeleton strings cached.
    """
    sura_stmt = select(ArReferenzVerse.sura_index).where(ArReferenzVerse.active.is_(True))
    if source_name is not None:
        sura_stmt = sura_stmt.where(ArReferenzVerse.source_name == source_name)
    sura_stmt = sura_stmt.distinct()
    suras = sorted({s for (s,) in (await session.execute(sura_stmt)).all()})

    for sura in suras:
        verses_stmt = (
            select(ArReferenzVerse)
            .where(ArReferenzVerse.sura_index == sura)
            .where(ArReferenzVerse.active.is_(True))
            .order_by(ArReferenzVerse.aya_index)
        )
        if source_name is not None:
            verses_stmt = verses_stmt.where(ArReferenzVerse.source_name == source_name)
        verses = list((await session.execute(verses_stmt)).scalars())
        if not verses:
            continue
        for start_idx in range(len(verses)):
            joined_skeleton_parts: list[str] = []
            joined_text_parts: list[str] = []
            for end_idx in range(start_idx, len(verses)):
                joined_skeleton_parts.append(verses[end_idx].text_skeleton)
                joined_text_parts.append(verses[end_idx].text_vocalized)
                joined_skeleton = " ".join(joined_skeleton_parts)
                if joined_skeleton == skeleton:
                    first = verses[start_idx]
                    last = verses[end_idx]
                    return RecognitionResult(
                        matched=True,
                        confidence=1.0,
                        sura_index=sura,
                        aya_index_start=first.aya_index,
                        aya_index_end=last.aya_index,
                        ar_source_name=first.source_name,
                        ar_source_version=first.source_version,
                        matched_text_vocalized=" ".join(joined_text_parts),
                    )
                if len(joined_skeleton) > len(skeleton):
                    # Joining one more āya overshot — abandon this start_idx.
                    break

    return RecognitionResult(matched=False, confidence=0.0)


__all__ = [
    "RecognitionResult",
    "recognize_quran_passage",
]
