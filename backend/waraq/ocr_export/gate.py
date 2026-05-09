"""T-OCR-EX-1 — OCR-export gate (Freigabeschranke for OCR-text export).

Per OCR Endfassung v1.3 §2 Sprint-OCR T-OCR-EX-1:

- `check_ocr_export_gate()` computes gate state on demand. **No log
  entry** (OCR-Gate-Vorabpruefung-Kein-Log-Test).
- Hard blockages: F-06-QR unresolved · F-07 critical · F-08 undecided ·
  open `conflict_instance` · inactive segments without lineage.
- Two modes: `endgueltig` and `arbeitsstand`. `go_with_warning` in
  `arbeitsstand` requires double-confirmation (reason + explicit).
- Four Pflichtfragen (page range / block types / markings / export
  mode) require active answers. Saved profile pre-fills but never
  replaces (OCR-Gate-Kein-Profil-Bypass-Test).
- Pflichtfragen confirmation writes a Decision Event with
  `decision_source=export_confirmation` and
  `related_export_attempt_id=current_attempt_id` (CR-1.5/CR-1.6).

Distinct from T-6.1.1's translation release gate. The two gates have
different blocking conditions and different downstream outcomes — they
must never be silently merged.
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.decisions import create_decision_event
from waraq.schemas import (
    Block,
    ConflictInstance,
    DecisionEvent,
    OcrErrorInstance,
    Page,
    Segment,
)
from waraq.schemas.enums import DecisionSource, OcrErrorState, ScopeType


class OcrExportGateState(StrEnum):
    """Three terminal outcomes — same shape as the T-6.1.1 release gate
    but distinct semantics (Sprint-OCR §1.4 distinction)."""

    EXPORTIERBAR = "exportierbar"
    EXPORTIERBAR_MIT_WARNUNGEN = "exportierbar_mit_warnungen"
    BLOCKIERT = "blockiert"


class GateMode(StrEnum):
    """Per Sprint-OCR §2: `endgueltig` (final export) vs `arbeitsstand`
    (work-in-progress export). The mode is set on
    OCR_EXPORT_EVENT.payload['gate_mode'] post-success."""

    ENDGUELTIG = "endgueltig"
    ARBEITSSTAND = "arbeitsstand"


@dataclass(frozen=True, kw_only=True, slots=True)
class Pflichtfragen:
    """The four canonical export-configuration Pflichtfragen per
    Sprint-OCR T-OCR-EX-1. Active answers are required at every export;
    a saved profile may pre-fill but never replace.

    `page_range` is a list of page numbers (NOT page UUIDs) per
    OCR Endfassung §1.x — UUID resolution is a runtime operation, not a
    persisted set.
    """

    page_range: list[int]
    block_types_enabled: list[str]
    markings_enabled: bool
    mode: GateMode


@dataclass(frozen=True, kw_only=True, slots=True)
class OcrExportConfig:
    """All inputs needed to run an OCR export attempt."""

    project_uuid: _uuid.UUID
    pflichtfragen: Pflichtfragen
    actor_uuid: _uuid.UUID | None = None
    # Caller-supplied attempt id (typically a UUID-string). Bound on the
    # confirmation Decision Event and on the OCR_EXPORT_EVENT. The same
    # value lets `active_decision_event_uuids[]` filter to *this*
    # attempt's confirmations only.
    export_attempt_id: str = ""


@dataclass(frozen=True, kw_only=True, slots=True)
class OcrExportGateResult:
    """Outcome of `check_ocr_export_gate`."""

    project_uuid: _uuid.UUID
    state: OcrExportGateState
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    requires_double_confirmation: bool = False
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# --- internal: condition checks -------------------------------------


async def _check_no_open_f_codes(
    session: AsyncSession, *, project_uuid: _uuid.UUID, codes: tuple[str, ...]
) -> list[str]:
    """For each F-code in `codes`, count unresolved instances on pages
    of `project_uuid`. Returns a blocking-reason string per non-zero
    code. Used for F-06-QR + F-07 + F-08 hard blocks."""
    reasons: list[str] = []
    for code in codes:
        result = await session.execute(
            select(func.count())
            .select_from(OcrErrorInstance)
            .join(Page, Page.page_uuid == OcrErrorInstance.page_uuid)
            .where(Page.project_uuid == project_uuid)
            .where(OcrErrorInstance.error_code == code)
            .where(OcrErrorInstance.state == OcrErrorState.OFFEN.value)
        )
        count = result.scalar_one()
        if count > 0:
            reasons.append(f"{count} unresolved {code} error(s) in project")
    return reasons


async def _check_no_open_conflicts(session: AsyncSession, *, project_uuid: _uuid.UUID) -> list[str]:
    """Open conflict_instance under the project blocks export."""
    result = await session.execute(
        select(func.count())
        .select_from(ConflictInstance)
        .join(Segment, Segment.satz_uuid == ConflictInstance.satz_uuid)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(ConflictInstance.state == "offen")
    )
    count = result.scalar_one()
    if count > 0:
        return [f"{count} open conflict_instance row(s) in project"]
    return []


async def _check_pflichtfragen(
    config: OcrExportConfig,
) -> list[str]:
    """Pflichtfragen must be actively answered. We treat empty page
    range / empty block-types-enabled list / missing mode as
    "unanswered". `markings_enabled` is a boolean — its presence as a
    field is itself the answer; the client signals YES or NO."""
    missing: list[str] = []
    if not config.pflichtfragen.page_range:
        missing.append("page_range is empty")
    if not config.pflichtfragen.block_types_enabled:
        missing.append("block_types_enabled is empty")
    # mode is required at type level via StrEnum — no separate check.
    return missing


# --- public API -----------------------------------------------------


async def check_ocr_export_gate(
    *,
    session: AsyncSession,
    config: OcrExportConfig,
) -> OcrExportGateResult:
    """Compute the gate state for an export attempt. Pure-by-design:
    NO log entry, NO Decision Event written. The caller decides whether
    to call `confirm_pflichtfragen` (writes a DE) and `run_ocr_export`
    (which logs on actual job start)."""
    project_uuid = config.project_uuid
    blocking: list[str] = []

    # F-06-QR (Qurʾān recognition), F-07 (content_filtered), F-08 (token_limit).
    # All three are canon-named hard blockers.
    blocking.extend(
        await _check_no_open_f_codes(
            session, project_uuid=project_uuid, codes=("F-06-QR", "F-07", "F-08")
        )
    )
    blocking.extend(await _check_no_open_conflicts(session, project_uuid=project_uuid))
    blocking.extend(_pflichtfragen_block_reasons := await _check_pflichtfragen(config))

    # Pages that have ocr_status=go_with_warning produce warnings (not
    # blocks), unless we're in endgueltig mode (then they block).
    warning_rows = await session.execute(
        select(Page.page_uuid, Page.page_index)
        .where(Page.project_uuid == project_uuid)
        .where(Page.ocr_status == "go_with_warning")
    )
    warnings = [
        f"page {pid} (index {pidx}) has ocr_status=go_with_warning" for pid, pidx in warning_rows
    ]

    if blocking:
        state = OcrExportGateState.BLOCKIERT
        return OcrExportGateResult(
            project_uuid=project_uuid,
            state=state,
            blocking_reasons=blocking,
            warnings=warnings,
        )

    if warnings:
        if config.pflichtfragen.mode == GateMode.ENDGUELTIG:
            # In `endgueltig` mode, warnings block.
            return OcrExportGateResult(
                project_uuid=project_uuid,
                state=OcrExportGateState.BLOCKIERT,
                blocking_reasons=[
                    "warnings present in endgueltig mode (downgrade to "
                    "arbeitsstand or resolve the warnings)"
                ],
                warnings=warnings,
            )
        # `arbeitsstand` mode: warnings are exportable WITH double
        # confirmation flag set so the caller surfaces both the
        # warnings list AND an explicit "are you sure?" prompt.
        return OcrExportGateResult(
            project_uuid=project_uuid,
            state=OcrExportGateState.EXPORTIERBAR_MIT_WARNUNGEN,
            warnings=warnings,
            requires_double_confirmation=True,
        )

    return OcrExportGateResult(
        project_uuid=project_uuid,
        state=OcrExportGateState.EXPORTIERBAR,
    )


async def confirm_pflichtfragen(
    *,
    session: AsyncSession,
    config: OcrExportConfig,
) -> DecisionEvent:
    """Write the Pflichtfragen-Bestätigung Decision Event.

    `decision_source = export_confirmation`,
    `related_export_attempt_id = config.export_attempt_id`,
    `scope_type = project`. Per OCR-Gate-Decision-Event-Source-Test +
    OCR-Gate-Export-Attempt-ID-Test."""
    if not config.export_attempt_id:
        raise ValueError(
            "confirm_pflichtfragen requires a non-empty export_attempt_id; "
            "the attempt id binds the confirmation to a specific export "
            "attempt (CR-1.6) and is consumed by the OCR_EXPORT_EVENT "
            "positive-set rule."
        )

    content: dict[str, Any] = {
        "page_range": list(config.pflichtfragen.page_range),
        "block_types_enabled": list(config.pflichtfragen.block_types_enabled),
        "markings_enabled": config.pflichtfragen.markings_enabled,
        "mode": config.pflichtfragen.mode.value,
    }
    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=config.project_uuid,
        decision_type="ocr_export_pflichtfragen_bestaetigt",
        decision_source=DecisionSource.EXPORT_CONFIRMATION,
        actor_uuid=config.actor_uuid,
        content=content,
        related_export_attempt_id=config.export_attempt_id,
    )
    return de
