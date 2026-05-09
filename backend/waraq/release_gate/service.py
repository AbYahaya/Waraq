"""T-6.1.1 — Release gate / Freigabeschranke.

Per Sprint 2 §2: the gate evaluates five release conditions on every
invocation against live state (no caching) and returns one of three
canonical outcomes.

Five conditions per ITB D.2:

1. No page has `ocr_status = no_go` with unresolved kritisch-class
   `ocr_error_instance` rows.
2. F-06-QR error class (Qurʾān-recognition) has no unresolved instance
   anywhere in the project. The detection writer for F-06-QR ships in M5;
   the gate that *reads* for unresolved rows ships now (Sprint 2 §B
   "Qurʾān-Stellen-Ausklammerung remains canonical but inert here" —
   "inert" applies to the translation-side exclusion, not to the
   gate-side block check that explicitly belongs in T-6.1.1).
3. All open `conflict_instance` rows for the project are resolved.
4. Glossary integrity check passes.
5. Project metadata required for translation start is complete.

State machine: `nicht_erreichbar → freigabeschranken_pruefung →
übersetzungsreif | übersetzbar_mit_warnung | blockiert`.

`uebersetzungsreif` is a state, not an action. Translation is started
**only** by an explicit `start_translation` call that writes a
`uebersetzungsstart` Decision Event. DBB §B Abkürzung 5 names "release
gate auto-triggers translation start when last `ocr_status` flips to
`go`" as a named structural failure mode — this service has no such
auto-trigger surface.

`uebersetzbar_mit_warnung` requires a prior `freigabe_mit_warnung`
Decision Event (decision_source=preflight_confirmation per §4.10). Without
it, the gate evaluates as `blockiert` even when only warning-class issues
are present. Per Sprint 2 §2 / Gate-Test-Mit-Warnung-Erfordert-Bestaetigung-Test.

Every gate evaluation writes a Log-Eintrag via EVENTING regardless of
outcome. The Log-Eintrag is the persistent audit trail; the gate state
itself is computed live and not persisted as a column on Project.

Atomicity: caller owns the transaction. The service flushes; commit /
rollback is the caller's responsibility.
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
from waraq.eventing import log_event
from waraq.release_gate.exceptions import (
    GateNotInWarningState,
    GateNotReady,
)
from waraq.schemas import (
    Block,
    ConflictInstance,
    DecisionEvent,
    OcrErrorInstance,
    Page,
    Project,
)
from waraq.schemas.enums import (
    DecisionSource,
    OcrErrorState,
    OcrStatus,
    ScopeType,
)


class GateState(StrEnum):
    """Per Sprint 2 §2 — canonical gate outcomes plus the workflow markers.

    `NICHT_ERREICHBAR` and `FREIGABESCHRANKEN_PRUEFUNG` are workflow
    markers documented in the spec but produced only by transient states;
    `evaluate_gate` always returns one of the three terminal outcomes.
    """

    NICHT_ERREICHBAR = "nicht_erreichbar"
    FREIGABESCHRANKEN_PRUEFUNG = "freigabeschranken_pruefung"
    UEBERSETZUNGSREIF = "uebersetzungsreif"
    UEBERSETZBAR_MIT_WARNUNG = "uebersetzbar_mit_warnung"
    BLOCKIERT = "blockiert"


@dataclass(frozen=True, kw_only=True, slots=True)
class GateResult:
    """Outcome of a single `evaluate_gate` call.

    `blocking_reasons` and `warnings` are caller-facing diagnostic strings.
    `evaluated_at` is captured at the start of the evaluation so caller can
    correlate with their own clock.
    """

    project_uuid: _uuid.UUID
    state: GateState
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# --- internal: the five condition checks -------------------------------


async def _check_no_go_pages(session: AsyncSession, *, project_uuid: _uuid.UUID) -> list[str]:
    """Condition #1. Returns blocking reasons (one per offending page)."""
    result = await session.execute(
        select(Page.page_uuid, Page.page_index)
        .where(Page.project_uuid == project_uuid)
        .where(Page.ocr_status == OcrStatus.NO_GO.value)
    )
    return [
        f"page {page_uuid} (index {page_index}) has ocr_status=no_go"
        for page_uuid, page_index in result
    ]


async def _check_no_open_f_06_qr(session: AsyncSession, *, project_uuid: _uuid.UUID) -> list[str]:
    """Condition #2. F-06-QR is the Qurʾān-recognition class. Joining
    OcrErrorInstance → Page filters to errors on pages of this project."""
    result = await session.execute(
        select(func.count())
        .select_from(OcrErrorInstance)
        .join(Page, Page.page_uuid == OcrErrorInstance.page_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(OcrErrorInstance.error_code == "F-06-QR")
        .where(OcrErrorInstance.state == OcrErrorState.OFFEN.value)
    )
    count = result.scalar_one()
    if count > 0:
        return [f"{count} unresolved F-06-QR (Qurʾān-recognition) error(s) in project"]
    return []


async def _check_no_open_conflicts(session: AsyncSession, *, project_uuid: _uuid.UUID) -> list[str]:
    """Condition #3. Joins through Block → Page → Project to scope conflicts."""
    from waraq.schemas import Segment

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


async def _check_glossary_integrity(
    session: AsyncSession, *, project_uuid: _uuid.UUID
) -> list[str]:
    """Condition #4. Currently a structural-pass: with the v1.0 schema
    there is no separate "reference" table that could orphan against
    Concept. RULE_BINDING-PO rows (T-7.2.1) reference Konzept-IDs by UUID
    in JSONB payload — once those exist, this check would walk them and
    confirm referenced Concepts are still active.

    This stub is intentional and structural: the gate condition is
    canonical, and the read path needs to exist so it returns []
    deterministically when there are no orphans, including the future
    case where there could have been some. M5 / Sprint 5 work that
    exercises RULE_BINDING-PO at scale will extend this check.
    """
    return []


async def _check_project_metadata(session: AsyncSession, *, project_uuid: _uuid.UUID) -> list[str]:
    """Condition #5. Currently checks the project exists and is active.
    Future expansion (target_language, etc.) extends here; v1.0 schema
    only has `name` (NOT NULL by schema) and `account_uuid` (NOT NULL FK),
    so the only failure mode here is project not found / inactive."""
    result = await session.execute(
        select(Project.active).where(Project.project_uuid == project_uuid)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return [f"project {project_uuid} not found"]
    if row is False:
        return [f"project {project_uuid} is inactive"]
    return []


async def _collect_warnings(session: AsyncSession, *, project_uuid: _uuid.UUID) -> list[str]:
    """Non-blocking findings: pages with `ocr_status = go_with_warning`."""
    result = await session.execute(
        select(Page.page_uuid, Page.page_index)
        .where(Page.project_uuid == project_uuid)
        .where(Page.ocr_status == OcrStatus.GO_WITH_WARNING.value)
    )
    return [
        f"page {page_uuid} (index {page_index}) has ocr_status=go_with_warning"
        for page_uuid, page_index in result
    ]


async def _has_freigabe_mit_warnung_de(session: AsyncSession, *, project_uuid: _uuid.UUID) -> bool:
    """Look up a `freigabe_mit_warnung` Decision Event for this project.

    Per Sprint 2 §2: this DE is the user's "I accept the warnings" handle.
    Decision Events are append-only (no `active` flag); the gate treats
    the existence of any DE of this type as "confirmation present". A
    subsequent state-changing event is the user's responsibility to follow
    up on by re-confirming if they want the gate to clear again.
    """
    result = await session.execute(
        select(func.count())
        .select_from(DecisionEvent)
        .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
        .where(DecisionEvent.scope_uuid == project_uuid)
        .where(DecisionEvent.decision_type == "freigabe_mit_warnung")
    )
    return result.scalar_one() > 0


# --- public API ---------------------------------------------------------


async def evaluate_gate(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> GateResult:
    """Run all five conditions live and return a `GateResult`.

    Always writes a Log-Eintrag via EVENTING (Sprint 2 §2 /
    Gate-Test-Log-Eintrag-Immer-Test). Never caches a result. Never
    starts translation as a side effect (DBB §B Abkürzung 5).
    """
    evaluated_at = datetime.now(UTC)

    blocking: list[str] = []
    blocking.extend(await _check_no_go_pages(session, project_uuid=project_uuid))
    blocking.extend(await _check_no_open_f_06_qr(session, project_uuid=project_uuid))
    blocking.extend(await _check_no_open_conflicts(session, project_uuid=project_uuid))
    blocking.extend(await _check_glossary_integrity(session, project_uuid=project_uuid))
    blocking.extend(await _check_project_metadata(session, project_uuid=project_uuid))

    warnings = await _collect_warnings(session, project_uuid=project_uuid)

    if blocking:
        state = GateState.BLOCKIERT
    elif warnings:
        # Warnings present — confirmation required for uebersetzbar_mit_warnung.
        if await _has_freigabe_mit_warnung_de(session, project_uuid=project_uuid):
            state = GateState.UEBERSETZBAR_MIT_WARNUNG
        else:
            state = GateState.BLOCKIERT
            blocking = ["warnings present, freigabe_mit_warnung confirmation required"]
    else:
        state = GateState.UEBERSETZUNGSREIF

    await log_event(
        session=session,
        operation_type="release_gate_evaluated",
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        result={
            "state": state.value,
            "blocking_count": len(blocking),
            "warning_count": len(warnings),
        },
    )

    return GateResult(
        project_uuid=project_uuid,
        state=state,
        blocking_reasons=blocking,
        warnings=warnings,
        evaluated_at=evaluated_at,
    )


async def confirm_translation_with_warning(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    actor_uuid: _uuid.UUID | None = None,
    content: dict[str, Any] | None = None,
) -> DecisionEvent:
    """User-side confirmation that warnings are acceptable.

    Writes a Decision Event with `scope_type=project`,
    `decision_type=freigabe_mit_warnung`,
    `decision_source=preflight_confirmation` (per §4.10 — preflight-
    family confirmations route here even at the release-gate layer).

    Refuses the call when the gate is currently `uebersetzungsreif`
    (no warnings to confirm — would write a useless DE) or
    `blockiert` due to a hard violation (warnings confirmation is
    irrelevant — fix the blocker first).
    """
    result = await evaluate_gate(session=session, project_uuid=project_uuid)

    # Only meaningful when warnings exist AND no hard blockers exist.
    has_hard_blockers = result.state == GateState.BLOCKIERT and not (
        len(result.blocking_reasons) == 1
        and "freigabe_mit_warnung confirmation required" in result.blocking_reasons[0]
    )
    if has_hard_blockers:
        raise GateNotInWarningState(
            f"gate is BLOCKIERT by hard violations; resolve them first. "
            f"Reasons: {result.blocking_reasons}"
        )
    if result.state == GateState.UEBERSETZUNGSREIF:
        raise GateNotInWarningState("gate is UEBERSETZUNGSREIF; no warnings to confirm")

    de_content: dict[str, Any] = {
        "warnings_at_confirmation": result.warnings,
        "warning_count": len(result.warnings),
    }
    if content:
        de_content.update(content)

    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        decision_type="freigabe_mit_warnung",
        decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        actor_uuid=actor_uuid,
        content=de_content,
    )
    await log_event(
        session=session,
        operation_type="release_gate_warning_confirmed",
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        result={
            "decision_event_uuid": str(de.decision_event_uuid),
            "warning_count": len(result.warnings),
        },
    )
    return de


async def start_translation(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    actor_uuid: _uuid.UUID | None = None,
    content: dict[str, Any] | None = None,
) -> DecisionEvent:
    """User-side action that begins a translation run.

    Per Sprint 2 §2: this is the **only** way translation starts. The
    function writes a Decision Event with
    `decision_type=uebersetzungsstart` and `decision_source=
    translation_pipeline`. It does **not** create or run a translation
    Job — that's T-7.1.1's responsibility, which observes this DE.

    DBB §B Abkürzung 5: there is no automatic trigger from
    `uebersetzungsreif` to translation start. The two are decoupled by
    construction — the gate evaluator writes no DE of this type, and this
    function refuses to write one when the gate is BLOCKIERT.

    Refuses the call when the gate is BLOCKIERT.
    `uebersetzbar_mit_warnung` is acceptable (the user already confirmed
    the warnings via `confirm_translation_with_warning`).
    """
    result = await evaluate_gate(session=session, project_uuid=project_uuid)

    if result.state not in (
        GateState.UEBERSETZUNGSREIF,
        GateState.UEBERSETZBAR_MIT_WARNUNG,
    ):
        raise GateNotReady(
            f"gate is {result.state.value}; translation cannot start. "
            f"Blocking reasons: {result.blocking_reasons}"
        )

    de_content: dict[str, Any] = {
        "gate_state_at_start": result.state.value,
        "warnings_count": len(result.warnings),
    }
    if content:
        de_content.update(content)

    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        decision_type="uebersetzungsstart",
        decision_source=DecisionSource.TRANSLATION_PIPELINE,
        actor_uuid=actor_uuid,
        content=de_content,
    )
    await log_event(
        session=session,
        operation_type="release_gate_translation_started",
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        result={
            "decision_event_uuid": str(de.decision_event_uuid),
            "gate_state": result.state.value,
        },
    )
    return de
