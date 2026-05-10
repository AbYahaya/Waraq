"""Difficulty scoring service — see module docstring in
`waraq.difficulty.__init__` for the canonical scope statement."""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, field
from typing import Final

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.invariant.enums import LockFlag
from waraq.ocr.error_classes import OcrErrorClass
from waraq.ocr.review import make_default_severity_weights
from waraq.schemas import (
    Befund,
    Block,
    HadithPassageStatus,
    KonsistenzBefund,
    OcrErrorInstance,
    Page,
    Segment,
)
from waraq.schemas.enums import OcrSeverity


@dataclass(frozen=True, slots=True)
class DifficultyWeights:
    """Per-dimension weight applied to the unresolved-count of that
    finding class. v1.0 implementation choice; canon-deferred per §3.5
    calibration policy."""

    audit_kritisch: float = 4.0
    audit_hoch: float = 3.0
    audit_mittel: float = 2.0
    konsistenz_kritisch: float = 4.0
    konsistenz_other: float = 2.0
    hadith_h_2: float = 4.0
    hadith_h_1: float = 2.0
    ocr_error_kritisch: float = 4.0
    ocr_error_hoch: float = 3.0
    ocr_error_mittel: float = 2.0
    locked_segment_manual_local: float = 1.0
    locked_segment_manual_editorial: float = 2.0


DEFAULT_DIFFICULTY_WEIGHTS: Final[DifficultyWeights] = DifficultyWeights()


@dataclass(frozen=True, slots=True)
class DifficultyBreakdown:
    """Counts that fed the score — surfaced for UI explainability."""

    audit_kritisch: int = 0
    audit_hoch: int = 0
    audit_mittel: int = 0
    konsistenz_kritisch: int = 0
    konsistenz_other: int = 0
    hadith_h_2: int = 0
    hadith_h_1: int = 0
    ocr_error_kritisch: int = 0
    ocr_error_hoch: int = 0
    ocr_error_mittel: int = 0
    locked_segment_manual_local: int = 0
    locked_segment_manual_editorial: int = 0


@dataclass(frozen=True, slots=True)
class DifficultyReport:
    """One difficulty rollup — page-scoped or project-aggregate.

    `score` is the weighted sum of the breakdown counts, computed at
    construction time so callers don't have to re-multiply.
    `segment_count` carries the project- / page-segment count for
    optional normalization (score / segments) — surfaced to the UI but
    NOT divided into the score automatically (page-level work has
    different shape than project-level)."""

    scope: str  # "page" | "project"
    scope_uuid: _uuid.UUID
    breakdown: DifficultyBreakdown
    score: float
    segment_count: int
    weights: DifficultyWeights = field(default_factory=lambda: DEFAULT_DIFFICULTY_WEIGHTS)


def _score_breakdown(b: DifficultyBreakdown, w: DifficultyWeights) -> float:
    return (
        b.audit_kritisch * w.audit_kritisch
        + b.audit_hoch * w.audit_hoch
        + b.audit_mittel * w.audit_mittel
        + b.konsistenz_kritisch * w.konsistenz_kritisch
        + b.konsistenz_other * w.konsistenz_other
        + b.hadith_h_2 * w.hadith_h_2
        + b.hadith_h_1 * w.hadith_h_1
        + b.ocr_error_kritisch * w.ocr_error_kritisch
        + b.ocr_error_hoch * w.ocr_error_hoch
        + b.ocr_error_mittel * w.ocr_error_mittel
        + b.locked_segment_manual_local * w.locked_segment_manual_local
        + b.locked_segment_manual_editorial * w.locked_segment_manual_editorial
    )


# --- Page-scoped query helpers ----------------------------------------


async def _count_open_befunde_by_severity_for_page(
    *, session: AsyncSession, page_uuid: _uuid.UUID
) -> dict[str, int]:
    """Return {schweregrad: count} for open Befunde whose Segment lives on
    `page_uuid`. Befunde reference Segments via `satz_uuid`; Segments
    reference Pages via Block."""
    result = await session.execute(
        select(Befund.schweregrad, func.count())
        .join(Segment, Segment.satz_uuid == Befund.satz_uuid)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .where(Block.page_uuid == page_uuid)
        .where(Befund.aufloesungsstatus == "offen")
        .group_by(Befund.schweregrad)
    )
    return {row[0]: row[1] for row in result.all()}


async def _count_locked_segments_for_page(
    *, session: AsyncSession, page_uuid: _uuid.UUID
) -> dict[str, int]:
    result = await session.execute(
        select(Segment.lock_flag, func.count())
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .where(Block.page_uuid == page_uuid)
        .where(Segment.active.is_(True))
        .group_by(Segment.lock_flag)
    )
    return {str(flag): cnt for flag, cnt in result.all()}


async def _count_segments_for_page(*, session: AsyncSession, page_uuid: _uuid.UUID) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(Segment)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .where(Block.page_uuid == page_uuid)
        .where(Segment.active.is_(True))
    )
    return int(result.scalar_one())


async def _count_open_ocr_errors_by_severity_for_page(
    *, session: AsyncSession, page_uuid: _uuid.UUID
) -> dict[OcrSeverity, int]:
    """Read OCR error instances scoped to the page; map error_code →
    canonical severity via `make_default_severity_weights`."""
    weights = make_default_severity_weights()
    result = await session.execute(
        select(OcrErrorInstance.error_code, func.count())
        .where(OcrErrorInstance.page_uuid == page_uuid)
        .where(OcrErrorInstance.state == "offen")
        .group_by(OcrErrorInstance.error_code)
    )
    counts: dict[OcrSeverity, int] = {}
    for code, cnt in result.all():
        try:
            cls = OcrErrorClass(code)
        except ValueError:
            continue
        sev = weights.weights.get(cls)
        if sev is None:
            continue
        counts[sev] = counts.get(sev, 0) + cnt
    return counts


async def _count_open_hadith_for_page(
    *, session: AsyncSession, page_uuid: _uuid.UUID
) -> dict[str, int]:
    """Count open hadith status rows for segments on `page_uuid`,
    grouped by H-2 / H-1 derivation. H-2 covers stellen_typ
    contributing to `HadithKlasse.H_2`; H-1 covers H-1.

    We avoid importing the derivation logic here to keep this module's
    dep tree small — instead read the canonical mapping list from
    `waraq.preflight.hadith`."""
    from waraq.preflight.enums import HadithKlasse, HadithStellenTyp
    from waraq.preflight.hadith import derive_hadith_klasse

    result = await session.execute(
        select(HadithPassageStatus.hadith_stellen_typ)
        .join(Segment, Segment.satz_uuid == HadithPassageStatus.satz_uuid)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .where(Block.page_uuid == page_uuid)
        .where(HadithPassageStatus.state == "offen")
    )
    h_2 = 0
    h_1 = 0
    for (raw,) in result.all():
        try:
            stellen_typ = HadithStellenTyp(raw)
        except ValueError:
            continue
        klasse = derive_hadith_klasse(stellen_typ)
        if klasse == HadithKlasse.H_2:
            h_2 += 1
        elif klasse == HadithKlasse.H_1:
            h_1 += 1
    return {"h_2": h_2, "h_1": h_1}


# --- Project-scoped query helpers -------------------------------------


async def _count_open_befunde_by_severity_for_project(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> dict[str, int]:
    result = await session.execute(
        select(Befund.schweregrad, func.count())
        .where(Befund.project_uuid == project_uuid)
        .where(Befund.aufloesungsstatus == "offen")
        .group_by(Befund.schweregrad)
    )
    return {row[0]: row[1] for row in result.all()}


async def _count_open_konsistenz_by_class_for_project(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> dict[str, int]:
    result = await session.execute(
        select(KonsistenzBefund.verstossklasse, func.count())
        .where(KonsistenzBefund.project_uuid == project_uuid)
        .where(KonsistenzBefund.aufloesungsstatus == "offen")
        .group_by(KonsistenzBefund.verstossklasse)
    )
    return {row[0]: row[1] for row in result.all()}


async def _count_open_hadith_for_project(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> dict[str, int]:
    from waraq.preflight.enums import HadithKlasse, HadithStellenTyp
    from waraq.preflight.hadith import derive_hadith_klasse

    result = await session.execute(
        select(HadithPassageStatus.hadith_stellen_typ)
        .where(HadithPassageStatus.project_uuid == project_uuid)
        .where(HadithPassageStatus.state == "offen")
    )
    h_2 = 0
    h_1 = 0
    for (raw,) in result.all():
        try:
            stellen_typ = HadithStellenTyp(raw)
        except ValueError:
            continue
        klasse = derive_hadith_klasse(stellen_typ)
        if klasse == HadithKlasse.H_2:
            h_2 += 1
        elif klasse == HadithKlasse.H_1:
            h_1 += 1
    return {"h_2": h_2, "h_1": h_1}


async def _count_open_ocr_errors_by_severity_for_project(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> dict[OcrSeverity, int]:
    weights = make_default_severity_weights()
    result = await session.execute(
        select(OcrErrorInstance.error_code, func.count())
        .join(Page, Page.page_uuid == OcrErrorInstance.page_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(OcrErrorInstance.state == "offen")
        .group_by(OcrErrorInstance.error_code)
    )
    counts: dict[OcrSeverity, int] = {}
    for code, cnt in result.all():
        try:
            cls = OcrErrorClass(code)
        except ValueError:
            continue
        sev = weights.weights.get(cls)
        if sev is None:
            continue
        counts[sev] = counts.get(sev, 0) + cnt
    return counts


async def _count_locked_segments_for_project(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> dict[str, int]:
    result = await session.execute(
        select(Segment.lock_flag, func.count())
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(Segment.active.is_(True))
        .group_by(Segment.lock_flag)
    )
    return {str(flag): cnt for flag, cnt in result.all()}


async def _count_segments_for_project(*, session: AsyncSession, project_uuid: _uuid.UUID) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(Segment)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(Segment.active.is_(True))
    )
    return int(result.scalar_one())


# --- Public entry points ----------------------------------------------


async def compute_page_difficulty(
    *,
    session: AsyncSession,
    page_uuid: _uuid.UUID,
    weights: DifficultyWeights = DEFAULT_DIFFICULTY_WEIGHTS,
) -> DifficultyReport:
    befunde = await _count_open_befunde_by_severity_for_page(session=session, page_uuid=page_uuid)
    locked = await _count_locked_segments_for_page(session=session, page_uuid=page_uuid)
    seg_count = await _count_segments_for_page(session=session, page_uuid=page_uuid)
    ocr_sev = await _count_open_ocr_errors_by_severity_for_page(
        session=session, page_uuid=page_uuid
    )
    hadith = await _count_open_hadith_for_page(session=session, page_uuid=page_uuid)

    breakdown = DifficultyBreakdown(
        audit_kritisch=befunde.get("kritisch", 0),
        audit_hoch=befunde.get("hoch", 0),
        audit_mittel=befunde.get("mittel", 0),
        konsistenz_kritisch=0,  # konsistenz is project-scoped only.
        konsistenz_other=0,
        hadith_h_2=hadith.get("h_2", 0),
        hadith_h_1=hadith.get("h_1", 0),
        ocr_error_kritisch=ocr_sev.get(OcrSeverity.KRITISCH, 0),
        ocr_error_hoch=ocr_sev.get(OcrSeverity.HOCH, 0),
        ocr_error_mittel=ocr_sev.get(OcrSeverity.MITTEL, 0),
        locked_segment_manual_local=locked.get(LockFlag.MANUAL_LOCAL.value, 0),
        locked_segment_manual_editorial=locked.get(LockFlag.MANUAL_EDITORIAL.value, 0),
    )
    return DifficultyReport(
        scope="page",
        scope_uuid=page_uuid,
        breakdown=breakdown,
        score=_score_breakdown(breakdown, weights),
        segment_count=seg_count,
        weights=weights,
    )


async def compute_project_difficulty(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    weights: DifficultyWeights = DEFAULT_DIFFICULTY_WEIGHTS,
) -> DifficultyReport:
    befunde = await _count_open_befunde_by_severity_for_project(
        session=session, project_uuid=project_uuid
    )
    konsistenz = await _count_open_konsistenz_by_class_for_project(
        session=session, project_uuid=project_uuid
    )
    locked = await _count_locked_segments_for_project(session=session, project_uuid=project_uuid)
    seg_count = await _count_segments_for_project(session=session, project_uuid=project_uuid)
    ocr_sev = await _count_open_ocr_errors_by_severity_for_project(
        session=session, project_uuid=project_uuid
    )
    hadith = await _count_open_hadith_for_project(session=session, project_uuid=project_uuid)

    konsistenz_kritisch = konsistenz.get("kritisch", 0)
    konsistenz_other = sum(v for k, v in konsistenz.items() if k != "kritisch")

    breakdown = DifficultyBreakdown(
        audit_kritisch=befunde.get("kritisch", 0),
        audit_hoch=befunde.get("hoch", 0),
        audit_mittel=befunde.get("mittel", 0),
        konsistenz_kritisch=konsistenz_kritisch,
        konsistenz_other=konsistenz_other,
        hadith_h_2=hadith.get("h_2", 0),
        hadith_h_1=hadith.get("h_1", 0),
        ocr_error_kritisch=ocr_sev.get(OcrSeverity.KRITISCH, 0),
        ocr_error_hoch=ocr_sev.get(OcrSeverity.HOCH, 0),
        ocr_error_mittel=ocr_sev.get(OcrSeverity.MITTEL, 0),
        locked_segment_manual_local=locked.get(LockFlag.MANUAL_LOCAL.value, 0),
        locked_segment_manual_editorial=locked.get(LockFlag.MANUAL_EDITORIAL.value, 0),
    )
    return DifficultyReport(
        scope="project",
        scope_uuid=project_uuid,
        breakdown=breakdown,
        score=_score_breakdown(breakdown, weights),
        segment_count=seg_count,
        weights=weights,
    )


__all__ = [
    "DEFAULT_DIFFICULTY_WEIGHTS",
    "DifficultyBreakdown",
    "DifficultyReport",
    "DifficultyWeights",
    "compute_page_difficulty",
    "compute_project_difficulty",
]
