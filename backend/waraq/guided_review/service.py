"""Guided-review queue service — see module docstring for canonical scope."""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.ocr.error_classes import OcrErrorClass
from waraq.ocr.review import make_default_severity_weights
from waraq.preflight.enums import HadithKlasse, HadithStellenTyp
from waraq.preflight.hadith import derive_hadith_klasse
from waraq.schemas import (
    Befund,
    HadithPassageStatus,
    KonsistenzBefund,
    OcrErrorInstance,
    Page,
)
from waraq.schemas.enums import OcrSeverity


class GuidedReviewTier(StrEnum):
    """Priority tier — drives queue ordering."""

    P_03_BLOCKING = "p_03_blocking"
    P_04_BLOCKING = "p_04_blocking"
    WARNING = "warning"


class GuidedReviewItemKind(StrEnum):
    """The finding class an item represents — drives the resolver UI route."""

    AUDIT_BEFUND = "audit_befund"
    KONSISTENZ_BEFUND = "konsistenz_befund"
    OCR_ERROR = "ocr_error"
    HADITH = "hadith"


@dataclass(frozen=True, slots=True)
class GuidedReviewItem:
    """One finding to walk through.

    `finding_uuid` is the canonical row UUID the resolver UI dispatches on
    (audit_befund_uuid / konsistenz_befund_uuid / ocr_error_instance_uuid /
    hadith_status_uuid). `satz_uuid` and `page_uuid` may be None — only
    segment-anchored item kinds carry them — and the UI uses them to
    deep-link the user to the offending location.
    """

    kind: GuidedReviewItemKind
    finding_uuid: _uuid.UUID
    tier: GuidedReviewTier
    severity: str  # canonical severity / class string
    detected_at: datetime
    satz_uuid: _uuid.UUID | None = None
    page_uuid: _uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class GuidedReviewQueue:
    """Ordered list of unresolved findings + summary counts.

    `items` is the canonical priority-ordered queue (P-03 → P-04 → warning,
    `detected_at` ascending within tier). `total` is the queue length;
    `by_tier` lets the UI render summary chips ("3 P-03, 2 P-04, 5 W").
    """

    items: list[GuidedReviewItem]
    total: int
    by_tier: dict[str, int]


_KRITISCH = "kritisch"
_HOCH = "hoch"
_MITTEL = "mittel"


async def _select_open_audit_befunde(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> list[Befund]:
    result = await session.execute(
        select(Befund)
        .where(Befund.project_uuid == project_uuid)
        .where(Befund.aufloesungsstatus == "offen")
    )
    return list(result.scalars())


async def _select_open_konsistenz(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> list[KonsistenzBefund]:
    result = await session.execute(
        select(KonsistenzBefund)
        .where(KonsistenzBefund.project_uuid == project_uuid)
        .where(KonsistenzBefund.aufloesungsstatus == "offen")
    )
    return list(result.scalars())


async def _select_open_ocr_errors(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> list[OcrErrorInstance]:
    result = await session.execute(
        select(OcrErrorInstance)
        .join(Page, Page.page_uuid == OcrErrorInstance.page_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(OcrErrorInstance.state == "offen")
    )
    return list(result.scalars())


async def _select_open_hadith(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> list[HadithPassageStatus]:
    result = await session.execute(
        select(HadithPassageStatus)
        .where(HadithPassageStatus.project_uuid == project_uuid)
        .where(HadithPassageStatus.state == "offen")
    )
    return list(result.scalars())


def _audit_tier(schweregrad: str) -> GuidedReviewTier:
    if schweregrad == _KRITISCH:
        return GuidedReviewTier.P_03_BLOCKING
    if schweregrad == _HOCH:
        return GuidedReviewTier.P_04_BLOCKING
    return GuidedReviewTier.WARNING


def _ocr_tier(severity: OcrSeverity | None) -> GuidedReviewTier:
    if severity == OcrSeverity.KRITISCH:
        return GuidedReviewTier.P_03_BLOCKING
    if severity == OcrSeverity.HOCH:
        return GuidedReviewTier.P_04_BLOCKING
    return GuidedReviewTier.WARNING


def _hadith_tier(klasse: HadithKlasse | None) -> GuidedReviewTier | None:
    if klasse == HadithKlasse.H_2:
        return GuidedReviewTier.P_03_BLOCKING
    if klasse == HadithKlasse.H_1:
        return GuidedReviewTier.WARNING
    return None  # H-0 silently excluded.


def _konsistenz_tier(verstossklasse: str) -> GuidedReviewTier:
    if verstossklasse == _KRITISCH:
        return GuidedReviewTier.P_03_BLOCKING
    return GuidedReviewTier.WARNING


_TIER_ORDER = {
    GuidedReviewTier.P_03_BLOCKING: 0,
    GuidedReviewTier.P_04_BLOCKING: 1,
    GuidedReviewTier.WARNING: 2,
}


async def build_review_queue(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> GuidedReviewQueue:
    """Read all unresolved findings + return them in canonical priority
    order. Caller (frontend) walks this list one-at-a-time."""

    befunde = await _select_open_audit_befunde(session=session, project_uuid=project_uuid)
    konsistenz = await _select_open_konsistenz(session=session, project_uuid=project_uuid)
    ocr_errors = await _select_open_ocr_errors(session=session, project_uuid=project_uuid)
    hadith_rows = await _select_open_hadith(session=session, project_uuid=project_uuid)

    weights = make_default_severity_weights()
    items: list[GuidedReviewItem] = []

    for b in befunde:
        items.append(
            GuidedReviewItem(
                kind=GuidedReviewItemKind.AUDIT_BEFUND,
                finding_uuid=b.befund_uuid,
                tier=_audit_tier(b.schweregrad),
                severity=b.schweregrad,
                detected_at=b.detected_at,
                satz_uuid=b.satz_uuid,
                page_uuid=None,
            )
        )

    for k in konsistenz:
        items.append(
            GuidedReviewItem(
                kind=GuidedReviewItemKind.KONSISTENZ_BEFUND,
                finding_uuid=k.konsistenz_befund_uuid,
                tier=_konsistenz_tier(k.verstossklasse),
                severity=k.verstossklasse,
                detected_at=k.created_at,
                satz_uuid=None,
                page_uuid=None,
            )
        )

    for e in ocr_errors:
        try:
            cls = OcrErrorClass(e.error_code)
        except ValueError:
            continue
        sev = weights.weights.get(cls)
        items.append(
            GuidedReviewItem(
                kind=GuidedReviewItemKind.OCR_ERROR,
                finding_uuid=e.ocr_error_instance_uuid,
                tier=_ocr_tier(sev),
                severity=sev.value if sev is not None else "unknown",
                detected_at=e.detected_at,
                satz_uuid=None,
                page_uuid=e.page_uuid,
            )
        )

    for h in hadith_rows:
        try:
            stellen_typ = HadithStellenTyp(h.hadith_stellen_typ)
        except ValueError:
            continue
        klasse = derive_hadith_klasse(stellen_typ)
        tier = _hadith_tier(klasse)
        if tier is None:
            continue
        items.append(
            GuidedReviewItem(
                kind=GuidedReviewItemKind.HADITH,
                finding_uuid=h.hadith_status_uuid,
                tier=tier,
                severity=klasse.value,
                detected_at=h.created_at,
                satz_uuid=h.satz_uuid,
                page_uuid=None,
            )
        )

    items.sort(key=lambda it: (_TIER_ORDER[it.tier], it.detected_at, str(it.finding_uuid)))

    by_tier: dict[str, int] = {}
    for it in items:
        by_tier[it.tier.value] = by_tier.get(it.tier.value, 0) + 1

    return GuidedReviewQueue(items=items, total=len(items), by_tier=by_tier)


__all__ = [
    "GuidedReviewItem",
    "GuidedReviewItemKind",
    "GuidedReviewQueue",
    "GuidedReviewTier",
    "build_review_queue",
]
