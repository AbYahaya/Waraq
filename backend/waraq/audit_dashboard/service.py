"""Sub-batch N — project audit dashboard aggregation service.

Read-only. Three operations:

- `summarize_project(session, project_uuid)` — counts/distributions
  across pages, OCR-PO confidence, cross-check situations, open Befunde,
  open consistency findings, open conflicts. One call → all the data
  the summary card needs.

- `list_attention_segments(session, project_uuid, filter)` — filterable
  per-segment list. Each item carries the minimal data the UI needs
  to render a row + link to the existing per-segment review surfaces.

- `segment_audit_detail(session, project_uuid, satz_uuid)` (N-2) —
  expandable-row detail: latest OCR-PO engines (with per-engine text
  when persisted; `text_chars`-only for legacy POs pre-N-2), Stage-3
  breakdown, latest TRANSLATION-PO cross-check, open Befunde for this
  segment, open conflicts. Powers the inline expansion of attention
  rows so the user can compare engine readings without leaving the
  audit page.

Pure aggregation: no writes, no decisions, no new domain concepts.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.schemas import (
    Befund,
    Block,
    ConflictInstance,
    Page,
    ProvenanceObject,
    Segment,
)
from waraq.schemas.consistency import KonsistenzBefund
from waraq.schemas.enums import OcrStatus, POType, ScopeType

# ---------------------------------------------------------------------
# Summary models
# ---------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True, slots=True)
class OcrStatusDistribution:
    """Page-level OCR review state counts. Empty buckets are 0, not omitted,
    so the UI can render a stable layout."""

    ausstehend: int = 0
    in_review: int = 0
    go: int = 0
    go_with_warning: int = 0
    no_go: int = 0


@dataclass(frozen=True, kw_only=True, slots=True)
class ConfidenceDistribution:
    """OCR-PO confidence_class counts over segments with an OCR-PO.

    `unknown_or_unscored` is the count of segments with an OCR-PO but
    no confidence_score (single-engine OCR pre-Stage-3 lands here —
    Gemini doesn't surface a confidence). `no_ocr` is the count of
    segments without any OCR-PO at all (uploaded but not OCR'd yet,
    or direct-text-extracted segments that skip OCR).
    """

    accepted: int = 0
    deficient: int = 0
    critical: int = 0
    unknown_or_unscored: int = 0
    no_ocr: int = 0


@dataclass(frozen=True, kw_only=True, slots=True)
class EngineAgreementDistribution:
    """OCR-PO engine_agreement counts over segments with multi-engine
    consensus data. `none_recorded` covers segments where only a
    single engine ran or pre-Stage-2 data."""

    exact_match: int = 0
    skeleton_equal: int = 0
    divergent: int = 0
    single_engine: int = 0
    engine_error: int = 0
    none_recorded: int = 0


@dataclass(frozen=True, kw_only=True, slots=True)
class CrossCheckDistribution:
    """TRANSLATION-PO cross_check.situation counts over translated
    segments. `not_translated` is the count of segments without a
    TRANSLATION-PO yet."""

    agreement: int = 0
    auto_correction: int = 0
    substantive_deviation: int = 0
    ambiguity: int = 0
    check_failed: int = 0
    not_translated: int = 0


@dataclass(frozen=True, kw_only=True, slots=True)
class BefundDistribution:
    """Open audit-Befund counts by severity. Resolved Befunde are not
    surfaced in the dashboard — the surface is "what needs attention",
    and resolved items are by definition not needing attention."""

    kritisch: int = 0
    hoch: int = 0
    mittel: int = 0


@dataclass(frozen=True, kw_only=True, slots=True)
class ProjectAuditSummary:
    """One-shot aggregation for the audit dashboard summary card."""

    project_uuid: _uuid.UUID
    total_pages: int
    total_segments: int
    page_ocr_status: OcrStatusDistribution
    ocr_confidence: ConfidenceDistribution
    engine_agreement: EngineAgreementDistribution
    cross_check: CrossCheckDistribution
    open_befunde: BefundDistribution
    open_konsistenz_befunde: int
    open_conflicts: int


# ---------------------------------------------------------------------
# Attention list models
# ---------------------------------------------------------------------


class AttentionFilter(StrEnum):
    """Why a segment is surfaced on the attention list. One per row;
    a segment matching multiple filters appears once per matched
    filter (the UI groups by filter)."""

    LOW_CONFIDENCE = "low_confidence"  # OCR confidence_class ∈ {deficient, critical}
    DIVERGENT_OCR = "divergent_ocr"  # engine_agreement = divergent
    CROSS_CHECK_SUBSTANTIVE = "cross_check_substantive"  # translation flagged
    CROSS_CHECK_AMBIGUITY = "cross_check_ambiguity"
    CROSS_CHECK_FAILED = "cross_check_failed"
    OPEN_AUDIT_FINDING = "open_audit_finding"  # has open Befund
    OPEN_CONFLICT = "open_conflict"


@dataclass(frozen=True, kw_only=True, slots=True)
class AttentionItem:
    """One row of the attention list. Carries the minimum the UI needs
    to render + link to the canonical per-segment review surface.

    `block_index` and `satz_index` together with `page_index` form the
    canonical address for a segment. Today the pipeline always emits
    `satz_index = 0` (one Segment per Block), so the discriminating
    coordinate is actually (page_index, block_index); the response
    carries both so the UI can render the full `page #X · block #Y ·
    seg #Z` label and stay correct when future sub-batches split
    multi-Segment Blocks.

    `detail` is filter-specific: confidence value for LOW_CONFIDENCE,
    rule code (regelkennung) for OPEN_AUDIT_FINDING, etc.
    """

    project_uuid: _uuid.UUID
    page_uuid: _uuid.UUID
    page_index: int
    block_uuid: _uuid.UUID
    block_index: int
    satz_uuid: _uuid.UUID
    satz_index: int
    filter_matched: AttentionFilter
    detail: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------
# summarize_project
# ---------------------------------------------------------------------


async def summarize_project(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> ProjectAuditSummary:
    """Build the one-shot summary used by the audit-dashboard summary card."""
    pages = await _project_pages(session, project_uuid)
    segments = await _project_segments(session, project_uuid)

    page_status = OcrStatusDistribution(
        ausstehend=sum(1 for p in pages if p.ocr_status == OcrStatus.AUSSTEHEND),
        in_review=sum(1 for p in pages if p.ocr_status == OcrStatus.IN_REVIEW),
        go=sum(1 for p in pages if p.ocr_status == OcrStatus.GO),
        go_with_warning=sum(1 for p in pages if p.ocr_status == OcrStatus.GO_WITH_WARNING),
        no_go=sum(1 for p in pages if p.ocr_status == OcrStatus.NO_GO),
    )

    # OCR-POs + TRANSLATION-POs scoped to segments in this project.
    segment_uuids = {s.satz_uuid for s in segments}
    ocr_pos_by_segment = await _latest_pos_for_segments(session, segment_uuids, POType.OCR)
    trans_pos_by_segment = await _latest_pos_for_segments(
        session, segment_uuids, POType.TRANSLATION
    )

    conf = _confidence_distribution(segments, ocr_pos_by_segment)
    agreement = _agreement_distribution(segments, ocr_pos_by_segment)
    cross = _cross_check_distribution(segments, trans_pos_by_segment)

    open_befunde = await _open_befund_distribution(session, project_uuid)
    open_konsistenz = await _open_konsistenz_count(session, project_uuid)
    open_conflicts = await _open_conflicts_count(session, segment_uuids)

    return ProjectAuditSummary(
        project_uuid=project_uuid,
        total_pages=len(pages),
        total_segments=len(segments),
        page_ocr_status=page_status,
        ocr_confidence=conf,
        engine_agreement=agreement,
        cross_check=cross,
        open_befunde=open_befunde,
        open_konsistenz_befunde=open_konsistenz,
        open_conflicts=open_conflicts,
    )


# ---------------------------------------------------------------------
# list_attention_segments
# ---------------------------------------------------------------------


async def list_attention_segments(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    filters: Sequence[AttentionFilter] | None = None,
    limit: int = 200,
) -> list[AttentionItem]:
    """Return per-segment rows matching `filters`. When `filters` is
    None or empty, returns all matching rows across every filter
    category. `limit` caps the result — first-match-wins ordering by
    (page_index, block_index, satz_index).
    """
    segments = await _project_segments(session, project_uuid)
    seg_by_uuid = {s.satz_uuid: s for s in segments}
    segment_uuids = set(seg_by_uuid.keys())
    if not segments:
        return []

    # Build a (segment → page) lookup so the per-row UI can render the
    # page_index without an extra round-trip.
    pages = await _project_pages(session, project_uuid)
    pages_by_uuid = {p.page_uuid: p for p in pages}
    blocks = await _project_blocks(session, project_uuid)
    blocks_by_uuid = {b.block_uuid: b for b in blocks}

    active_filters = set(filters or list(AttentionFilter))

    items: list[AttentionItem] = []

    if AttentionFilter.LOW_CONFIDENCE in active_filters or (
        AttentionFilter.DIVERGENT_OCR in active_filters
    ):
        ocr_pos = await _latest_pos_for_segments(session, segment_uuids, POType.OCR)
        for satz_uuid, po in ocr_pos.items():
            payload: dict[str, Any] = po.payload or {}
            if AttentionFilter.LOW_CONFIDENCE in active_filters:
                klass = payload.get("confidence_class")
                if klass in ("deficient", "critical"):
                    items.append(
                        _build_item(
                            seg_by_uuid,
                            blocks_by_uuid,
                            pages_by_uuid,
                            project_uuid,
                            satz_uuid,
                            AttentionFilter.LOW_CONFIDENCE,
                            {
                                "confidence_class": klass,
                                "confidence_score": payload.get("confidence_score"),
                            },
                        )
                    )
            if (
                AttentionFilter.DIVERGENT_OCR in active_filters
                and payload.get("engine_agreement") == "divergent"
            ):
                items.append(
                    _build_item(
                        seg_by_uuid,
                        blocks_by_uuid,
                        pages_by_uuid,
                        project_uuid,
                        satz_uuid,
                        AttentionFilter.DIVERGENT_OCR,
                        {"engine_agreement": "divergent"},
                    )
                )

    cross_filters = {
        AttentionFilter.CROSS_CHECK_SUBSTANTIVE,
        AttentionFilter.CROSS_CHECK_AMBIGUITY,
        AttentionFilter.CROSS_CHECK_FAILED,
    } & active_filters
    if cross_filters:
        trans_pos = await _latest_pos_for_segments(session, segment_uuids, POType.TRANSLATION)
        for satz_uuid, po in trans_pos.items():
            payload = po.payload or {}
            cross_check = payload.get("cross_check") or {}
            situation = cross_check.get("situation")
            mapping = {
                "substantive_deviation": AttentionFilter.CROSS_CHECK_SUBSTANTIVE,
                "ambiguity": AttentionFilter.CROSS_CHECK_AMBIGUITY,
                "check_failed": AttentionFilter.CROSS_CHECK_FAILED,
            }
            matched = mapping.get(situation) if isinstance(situation, str) else None
            if matched is not None and matched in cross_filters:
                items.append(
                    _build_item(
                        seg_by_uuid,
                        blocks_by_uuid,
                        pages_by_uuid,
                        project_uuid,
                        satz_uuid,
                        matched,
                        {"situation": situation},
                    )
                )

    if AttentionFilter.OPEN_AUDIT_FINDING in active_filters:
        befunde = await _open_befunde_for_project(session, project_uuid)
        for b in befunde:
            if b.satz_uuid not in seg_by_uuid:
                continue
            items.append(
                _build_item(
                    seg_by_uuid,
                    blocks_by_uuid,
                    pages_by_uuid,
                    project_uuid,
                    b.satz_uuid,
                    AttentionFilter.OPEN_AUDIT_FINDING,
                    {
                        "regelkennung": b.regelkennung,
                        "schweregrad": b.schweregrad,
                        "verstossklasse": b.verstossklasse,
                    },
                )
            )

    if AttentionFilter.OPEN_CONFLICT in active_filters:
        conflicts = await _open_conflicts_for_segments(session, segment_uuids)
        for c in conflicts:
            items.append(
                _build_item(
                    seg_by_uuid,
                    blocks_by_uuid,
                    pages_by_uuid,
                    project_uuid,
                    c.satz_uuid,
                    AttentionFilter.OPEN_CONFLICT,
                    {"conflict_type": c.conflict_type, "rule_source": c.rule_source},
                )
            )

    # Stable ordering: page, block, segment ascending.
    items.sort(key=lambda it: (it.page_index, it.satz_index))
    return items[:limit]


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------


async def _project_pages(session: AsyncSession, project_uuid: _uuid.UUID) -> list[Page]:
    result = await session.execute(
        select(Page)
        .where(Page.project_uuid == project_uuid)
        .where(Page.active.is_(True))
        .order_by(Page.page_index.asc())
    )
    return list(result.scalars())


async def _project_blocks(session: AsyncSession, project_uuid: _uuid.UUID) -> list[Block]:
    result = await session.execute(
        select(Block)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(Block.active.is_(True))
        .where(Page.active.is_(True))
    )
    return list(result.scalars())


async def _project_segments(session: AsyncSession, project_uuid: _uuid.UUID) -> list[Segment]:
    result = await session.execute(
        select(Segment)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(Segment.active.is_(True))
        .where(Block.active.is_(True))
        .where(Page.active.is_(True))
        .order_by(Page.page_index.asc(), Block.block_index.asc(), Segment.satz_index.asc())
    )
    return list(result.scalars())


async def _latest_pos_for_segments(
    session: AsyncSession,
    segment_uuids: set[_uuid.UUID],
    po_type: POType,
) -> dict[_uuid.UUID, ProvenanceObject]:
    """Return the most-recent PO of `po_type` for each segment in
    `segment_uuids`. Walks all SEGMENT-scoped POs and keeps the latest
    per scope_uuid — matches the per-segment readout pattern.
    """
    if not segment_uuids:
        return {}
    result = await session.execute(
        select(ProvenanceObject)
        .where(ProvenanceObject.po_type == po_type.value)
        .where(ProvenanceObject.scope_type == ScopeType.SEGMENT.value)
        .where(ProvenanceObject.scope_uuid.in_(segment_uuids))
        .order_by(ProvenanceObject.created_at.desc())
    )
    latest: dict[_uuid.UUID, ProvenanceObject] = {}
    for po in result.scalars():
        if po.scope_uuid in latest:
            continue
        latest[po.scope_uuid] = po
    return latest


def _confidence_distribution(
    segments: list[Segment],
    ocr_pos: dict[_uuid.UUID, ProvenanceObject],
) -> ConfidenceDistribution:
    accepted = deficient = critical = unknown = no_ocr = 0
    for seg in segments:
        po = ocr_pos.get(seg.satz_uuid)
        if po is None:
            no_ocr += 1
            continue
        klass = (po.payload or {}).get("confidence_class")
        if klass == "accepted":
            accepted += 1
        elif klass == "deficient":
            deficient += 1
        elif klass == "critical":
            critical += 1
        else:
            unknown += 1
    return ConfidenceDistribution(
        accepted=accepted,
        deficient=deficient,
        critical=critical,
        unknown_or_unscored=unknown,
        no_ocr=no_ocr,
    )


def _agreement_distribution(
    segments: list[Segment],
    ocr_pos: dict[_uuid.UUID, ProvenanceObject],
) -> EngineAgreementDistribution:
    counts = {
        "exact_match": 0,
        "skeleton_equal": 0,
        "divergent": 0,
        "single_engine": 0,
        "engine_error": 0,
        "none_recorded": 0,
    }
    for seg in segments:
        po = ocr_pos.get(seg.satz_uuid)
        if po is None:
            counts["none_recorded"] += 1
            continue
        agreement = (po.payload or {}).get("engine_agreement")
        if isinstance(agreement, str) and agreement in counts:
            counts[agreement] += 1
        else:
            counts["none_recorded"] += 1
    return EngineAgreementDistribution(**counts)


def _cross_check_distribution(
    segments: list[Segment],
    trans_pos: dict[_uuid.UUID, ProvenanceObject],
) -> CrossCheckDistribution:
    counts = {
        "agreement": 0,
        "auto_correction": 0,
        "substantive_deviation": 0,
        "ambiguity": 0,
        "check_failed": 0,
        "not_translated": 0,
    }
    for seg in segments:
        po = trans_pos.get(seg.satz_uuid)
        if po is None:
            counts["not_translated"] += 1
            continue
        payload = po.payload or {}
        cross_check = payload.get("cross_check") or {}
        situation = cross_check.get("situation")
        if isinstance(situation, str) and situation in counts:
            counts[situation] += 1
        else:
            counts["not_translated"] += 1
    return CrossCheckDistribution(**counts)


async def _open_befund_distribution(
    session: AsyncSession, project_uuid: _uuid.UUID
) -> BefundDistribution:
    result = await session.execute(
        select(Befund)
        .where(Befund.project_uuid == project_uuid)
        .where(Befund.aufloesungsstatus == "offen")
    )
    counts = {"kritisch": 0, "hoch": 0, "mittel": 0}
    for b in result.scalars():
        if b.schweregrad in counts:
            counts[b.schweregrad] += 1
    return BefundDistribution(**counts)


async def _open_befunde_for_project(
    session: AsyncSession, project_uuid: _uuid.UUID
) -> list[Befund]:
    result = await session.execute(
        select(Befund)
        .where(Befund.project_uuid == project_uuid)
        .where(Befund.aufloesungsstatus == "offen")
    )
    return list(result.scalars())


async def _open_konsistenz_count(session: AsyncSession, project_uuid: _uuid.UUID) -> int:
    result = await session.execute(
        select(KonsistenzBefund)
        .where(KonsistenzBefund.project_uuid == project_uuid)
        .where(KonsistenzBefund.aufloesungsstatus == "offen")
    )
    return len(list(result.scalars()))


async def _open_conflicts_count(session: AsyncSession, segment_uuids: set[_uuid.UUID]) -> int:
    if not segment_uuids:
        return 0
    result = await session.execute(
        select(ConflictInstance)
        .where(ConflictInstance.satz_uuid.in_(segment_uuids))
        .where(ConflictInstance.state == "offen")
    )
    return len(list(result.scalars()))


async def _open_conflicts_for_segments(
    session: AsyncSession, segment_uuids: set[_uuid.UUID]
) -> list[ConflictInstance]:
    if not segment_uuids:
        return []
    result = await session.execute(
        select(ConflictInstance)
        .where(ConflictInstance.satz_uuid.in_(segment_uuids))
        .where(ConflictInstance.state == "offen")
    )
    return list(result.scalars())


# ---------------------------------------------------------------------
# segment_audit_detail (N-2)
# ---------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True, slots=True)
class EngineReading:
    """One engine's reading of the segment for the divergent-comparison UI."""

    engine: str  # OcrEngine.value
    text: str | None  # None for legacy OCR-POs that only stored text_chars
    text_chars: int
    confidence: float | None
    error_class: str | None


@dataclass(frozen=True, kw_only=True, slots=True)
class BefundDetail:
    """One open Befund row for the segment-detail panel."""

    befund_uuid: _uuid.UUID
    regelkennung: str
    schweregrad: str
    verstossklasse: str
    detection_context: dict[str, Any]


@dataclass(frozen=True, kw_only=True, slots=True)
class SegmentAuditDetail:
    """Per-segment expandable-row payload. All fields nullable so a
    segment with only partial state (e.g. OCR done, no translation yet)
    renders cleanly."""

    satz_uuid: _uuid.UUID
    page_index: int
    block_index: int
    satz_index: int
    current_text: str | None
    # OCR side
    ocr_engine_agreement: str | None
    ocr_confidence_score: float | None
    ocr_confidence_class: str | None
    ocr_engines: tuple[EngineReading, ...]
    ocr_engines_have_text: bool  # True iff at least one engine has `text` populated
    # Translation side
    translation_situation: str | None
    translation_target_text: str | None
    translation_primary_engine: str | None
    translation_check_engine: str | None
    # Open findings
    open_befunde: tuple[BefundDetail, ...]
    open_conflicts_count: int


async def segment_audit_detail(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    satz_uuid: _uuid.UUID,
) -> SegmentAuditDetail | None:
    """Build the per-segment detail panel. Returns None when the segment
    isn't part of `project_uuid` (caller surfaces as 404).
    """
    # Verify the segment belongs to this project via the Page join.
    result = await session.execute(
        select(Segment, Block, Page)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Segment.satz_uuid == satz_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(Segment.active.is_(True))
    )
    row = result.first()
    if row is None:
        return None
    seg, block, page = row

    # OCR-PO latest
    ocr_pos = await _latest_pos_for_segments(session, {satz_uuid}, POType.OCR)
    ocr_po = ocr_pos.get(satz_uuid)
    ocr_payload: dict[str, Any] = (ocr_po.payload or {}) if ocr_po else {}

    engines_raw = ocr_payload.get("engines") or []
    engines: list[EngineReading] = []
    have_text = False
    if isinstance(engines_raw, list):
        for entry in engines_raw:
            if not isinstance(entry, dict):
                continue
            text_val = entry.get("text")
            if isinstance(text_val, str):
                have_text = True
            engines.append(
                EngineReading(
                    engine=str(entry.get("engine", "")),
                    text=text_val if isinstance(text_val, str) else None,
                    text_chars=int(entry.get("text_chars", 0)),
                    confidence=_as_float_or_none(entry.get("confidence")),
                    error_class=(
                        entry.get("error_class")
                        if isinstance(entry.get("error_class"), str)
                        else None
                    ),
                )
            )

    # TRANSLATION-PO latest (for cross-check situation + target text)
    trans_pos = await _latest_pos_for_segments(session, {satz_uuid}, POType.TRANSLATION)
    trans_po = trans_pos.get(satz_uuid)
    trans_payload: dict[str, Any] = (trans_po.payload or {}) if trans_po else {}
    cross_check = trans_payload.get("cross_check") or {}
    situation = (
        cross_check.get("situation") if isinstance(cross_check.get("situation"), str) else None
    )
    primary_engine = (
        cross_check.get("primary_engine")
        if isinstance(cross_check.get("primary_engine"), str)
        else None
    )
    check_engine = (
        cross_check.get("check_engine")
        if isinstance(cross_check.get("check_engine"), str)
        else None
    )
    target_text = (
        trans_payload.get("translation_text")
        if isinstance(trans_payload.get("translation_text"), str)
        else None
    )

    # Open Befunde for this segment
    befund_q = await session.execute(
        select(Befund)
        .where(Befund.satz_uuid == satz_uuid)
        .where(Befund.aufloesungsstatus == "offen")
    )
    befunde = tuple(
        BefundDetail(
            befund_uuid=b.befund_uuid,
            regelkennung=b.regelkennung,
            schweregrad=b.schweregrad,
            verstossklasse=b.verstossklasse,
            detection_context=b.detection_context or {},
        )
        for b in befund_q.scalars()
    )

    # Open conflicts count
    conf_q = await session.execute(
        select(ConflictInstance)
        .where(ConflictInstance.satz_uuid == satz_uuid)
        .where(ConflictInstance.state == "offen")
    )
    open_conflicts_count = len(list(conf_q.scalars()))

    return SegmentAuditDetail(
        satz_uuid=satz_uuid,
        page_index=page.page_index,
        block_index=block.block_index,
        satz_index=seg.satz_index,
        current_text=seg.text_content,
        ocr_engine_agreement=(
            ocr_payload.get("engine_agreement")
            if isinstance(ocr_payload.get("engine_agreement"), str)
            else None
        ),
        ocr_confidence_score=_as_float_or_none(ocr_payload.get("confidence_score")),
        ocr_confidence_class=(
            ocr_payload.get("confidence_class")
            if isinstance(ocr_payload.get("confidence_class"), str)
            else None
        ),
        ocr_engines=tuple(engines),
        ocr_engines_have_text=have_text,
        translation_situation=situation,
        translation_target_text=target_text,
        translation_primary_engine=primary_engine,
        translation_check_engine=check_engine,
        open_befunde=befunde,
        open_conflicts_count=open_conflicts_count,
    )


def _as_float_or_none(value: Any) -> float | None:
    """Coerce JSON-loaded numerics to float, accepting both int and
    float; return None for everything else."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _build_item(
    segments: dict[_uuid.UUID, Segment],
    blocks: dict[_uuid.UUID, Block],
    pages: dict[_uuid.UUID, Page],
    project_uuid: _uuid.UUID,
    satz_uuid: _uuid.UUID,
    matched: AttentionFilter,
    detail: dict[str, Any],
) -> AttentionItem:
    seg = segments[satz_uuid]
    block = blocks.get(seg.block_uuid)
    if block is None:
        # Defensive: shouldn't happen given the project-segments join,
        # but produces a synthetic page_index = 0 row rather than crashing.
        return AttentionItem(
            project_uuid=project_uuid,
            page_uuid=_uuid.UUID(int=0),
            page_index=0,
            block_uuid=seg.block_uuid,
            block_index=0,
            satz_uuid=satz_uuid,
            satz_index=seg.satz_index,
            filter_matched=matched,
            detail=detail,
        )
    page = pages.get(block.page_uuid)
    page_index = page.page_index if page is not None else 0
    page_uuid = page.page_uuid if page is not None else _uuid.UUID(int=0)
    return AttentionItem(
        project_uuid=project_uuid,
        page_uuid=page_uuid,
        page_index=page_index,
        block_uuid=block.block_uuid,
        block_index=block.block_index,
        satz_uuid=satz_uuid,
        satz_index=seg.satz_index,
        filter_matched=matched,
        detail=detail,
    )
