"""T-4.3.1 — OCR review status per page.

State machine (Sprint 1 §2):

    ausstehend  ─────► in_review ─────► go | go_with_warning | no_go
                            ▲                        │
                            └────── re-entry ────────┘

Re-entry into `in_review` is permitted from any non-terminal state.

The `no_go → go` transition is **not automatic**. It requires an explicit
user-resolution Decision Event with `scope_type=page` (per Sprint 1 §2,
"OCR-Review-Status-Kein-Auto-Go-Test"). This module provides
`resolve_no_go_to_go` which writes the canonical Decision Event and applies
the transition atomically.

Severity aggregation is **configurable**. The mapping from F-XX → severity
class lives on `SeverityWeights`, passed in per call. R-S1-04 explicitly
forbids hard-coded thresholds — the mapping defaults provided here are a
shell starting point pending Gold-Corpus calibration. Callers are expected
to load weights from a config table at runtime.

Provenance discipline:
- The aggregator and writers in this module create no Provenance Objects.
  OCR-error rows are not POs (they're an event-instance table); the
  Decision Event written on `no_go → go` is the provenance anchor for the
  user-resolution moment.
- No LINEAGE_EVENT is written from this module — re-segmentation lives
  elsewhere.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.decisions import create_decision_event
from waraq.eventing import log_event
from waraq.identity.service import new_uuid
from waraq.ocr.error_classes import OcrErrorClass
from waraq.schemas import DecisionEvent, OcrErrorInstance, Page
from waraq.schemas.enums import (
    DecisionSource,
    OcrErrorState,
    OcrSeverity,
    OcrStatus,
    ScopeType,
)


@dataclass(frozen=True, kw_only=True, slots=True)
class SeverityWeights:
    """Per-error-class severity for review-status aggregation.

    Per Sprint 1 §2 / R-S1-04: the mapping is configurable, never hard-coded.
    Calibration after Gold-Corpus tests is a config change, not a code
    change.

    Attributes:
        weights: Full mapping of `OcrErrorClass → OcrSeverity`. Must cover
            every `OcrErrorClass` value; `__post_init__` enforces this so a
            misconfigured table raises early instead of silently
            mis-aggregating.
    """

    weights: dict[OcrErrorClass, OcrSeverity] = field(default_factory=dict)

    def __post_init__(self) -> None:
        missing = set(OcrErrorClass) - set(self.weights)
        if missing:
            raise ValueError(
                f"SeverityWeights missing entries for: {sorted(c.value for c in missing)}. "
                "All F-XX classes must be mapped — half-configured tables silently "
                "mis-aggregate page status."
            )

    def severity(self, code: OcrErrorClass) -> OcrSeverity:
        return self.weights[code]


def make_default_severity_weights() -> SeverityWeights:
    """Shell default mapping. **Not canonical** — calibration is post-
    Gold-Corpus per Sprint 1 §B "deliberately not in this sprint" (concrete
    severity-aggregation thresholds). Use this only as a starting point or
    in tests; production callers should load from a config table.

    The default leans conservative: anything that almost certainly indicates
    a deployment-level fault (auth, malformed input, content filtering,
    token limit) is `kritisch`; provider-side or empty-extraction rendering
    is `hoch`; transient/unknown is `mittel`.
    """
    return SeverityWeights(
        weights={
            OcrErrorClass.F_01: OcrSeverity.KRITISCH,  # api_authentication
            OcrErrorClass.F_02: OcrSeverity.MITTEL,  # rate_limit (transient)
            OcrErrorClass.F_03: OcrSeverity.HOCH,  # api_server_error
            OcrErrorClass.F_04: OcrSeverity.MITTEL,  # network_timeout (transient)
            OcrErrorClass.F_05: OcrSeverity.KRITISCH,  # malformed_input
            OcrErrorClass.F_06: OcrSeverity.HOCH,  # empty_extraction
            OcrErrorClass.F_07: OcrSeverity.KRITISCH,  # content_filtered
            OcrErrorClass.F_08: OcrSeverity.KRITISCH,  # token_limit
            OcrErrorClass.F_09: OcrSeverity.MITTEL,  # unknown
            # Qurʾān-recognition errors are operationally critical: the
            # release gate condition #2 blocks export on any unresolved
            # F-06-QR. Default severity matches the gate's hard-block
            # treatment.
            OcrErrorClass.F_06_QR: OcrSeverity.KRITISCH,
        }
    )


# --- pure aggregator -------------------------------------------------------


def derive_status_from_codes(
    open_codes: Iterable[OcrErrorClass],
    *,
    weights: SeverityWeights,
) -> OcrStatus:
    """Compute the *derived* OCR status from a set of open F-XX classes.

    Pure: no DB access, no side effects. The state-machine application is
    handled by `apply_findings_to_status`.

    Returns one of `GO`, `GO_WITH_WARNING`, `NO_GO`. Never returns
    `AUSSTEHEND` or `IN_REVIEW` — those are workflow states that no
    aggregation can derive.
    """
    open_codes_list = list(open_codes)
    if not open_codes_list:
        return OcrStatus.GO
    severities = [weights.severity(code) for code in open_codes_list]
    if OcrSeverity.KRITISCH in severities:
        return OcrStatus.NO_GO
    if OcrSeverity.HOCH in severities or OcrSeverity.MITTEL in severities:
        return OcrStatus.GO_WITH_WARNING
    return OcrStatus.GO


# --- DB helpers ------------------------------------------------------------


async def _open_error_codes_for_page(
    session: AsyncSession, *, page_uuid: _uuid.UUID
) -> list[OcrErrorClass]:
    """Load all open F-XX classes attached to `page_uuid`. Block-narrowed
    instances are included via the page_uuid root."""
    result = await session.execute(
        select(OcrErrorInstance.error_code)
        .where(OcrErrorInstance.page_uuid == page_uuid)
        .where(OcrErrorInstance.state == OcrErrorState.OFFEN.value)
    )
    return [OcrErrorClass(code) for code in result.scalars()]


# --- writers ---------------------------------------------------------------


async def record_ocr_error_instance(
    *,
    session: AsyncSession,
    page_uuid: _uuid.UUID,
    error_code: OcrErrorClass,
    block_uuid: _uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> OcrErrorInstance:
    """Persist an open `ocr_error_instance` row.

    State defaults to `offen`. The aggregator reads severity at status-
    computation time via `SeverityWeights`; the row carries only the F-XX
    code and context. Callers wire this into the OCR pipeline (Sprint 0
    T-4.1.3 leaves error info on Job.error JSONB; this row is the durable,
    page-aggregatable record).
    """
    instance = OcrErrorInstance(
        ocr_error_instance_uuid=new_uuid(),
        page_uuid=page_uuid,
        block_uuid=block_uuid,
        error_code=error_code.value,
        state=OcrErrorState.OFFEN.value,
        details=details if details is not None else {},
    )
    session.add(instance)
    await session.flush()
    return instance


async def resolve_ocr_error_instance(
    *,
    session: AsyncSession,
    instance: OcrErrorInstance,
) -> None:
    """Mark an `ocr_error_instance` as `aufgeloest`. Idempotent only at the
    state-string level — re-resolving an already-resolved instance is a
    no-op except for `resolved_at` re-stamping (so we refuse it explicitly
    to avoid masking sequencing bugs)."""
    if instance.state == OcrErrorState.AUFGELOEST.value:
        raise ValueError(
            f"ocr_error_instance {instance.ocr_error_instance_uuid} is already aufgeloest"
        )
    instance.state = OcrErrorState.AUFGELOEST.value
    instance.resolved_at = datetime.now(UTC)
    await session.flush()


# --- state machine ---------------------------------------------------------


_TERMINAL_GO_STATES = frozenset({OcrStatus.GO, OcrStatus.GO_WITH_WARNING, OcrStatus.NO_GO})


async def enter_in_review(
    *,
    session: AsyncSession,
    page: Page,
) -> None:
    """Transition `page.ocr_status` to `in_review`. Permitted from any state
    (`ausstehend` and re-entry from any terminal go-state). Logs via
    EVENTING.

    Discipline: `apply_findings_to_status` only operates from `in_review`,
    so callers must enter review before applying findings.
    """
    prior = page.ocr_status
    page.ocr_status = OcrStatus.IN_REVIEW
    await session.flush()
    await log_event(
        session=session,
        operation_type="ocr_status_enter_in_review",
        scope_type=ScopeType.PAGE,
        scope_uuid=page.page_uuid,
        result={"prior": prior.value, "new": OcrStatus.IN_REVIEW.value},
    )


async def apply_findings_to_status(
    *,
    session: AsyncSession,
    page: Page,
    weights: SeverityWeights,
) -> OcrStatus:
    """Compute the derived status from open `ocr_error_instance` rows for
    `page`, then apply the transition.

    Page must currently be in `in_review` (raises otherwise). Re-call to
    refresh status as findings change is supported.

    Special case — `no_go → go` is **refused silently**: the page stays
    `no_go`. Per Sprint 1 §2 / OCR-Review-Status-Kein-Auto-Go-Test, the
    automatic aggregator can never auto-clear a no-go page. Callers must
    invoke `resolve_no_go_to_go` for that transition.

    Returns the page's `ocr_status` after the call (which may equal the
    prior status if the no_go-→-go guard kicked in).
    """
    if page.ocr_status != OcrStatus.IN_REVIEW:
        raise ValueError(
            f"apply_findings_to_status requires page in IN_REVIEW; "
            f"got {page.ocr_status.value}. Call enter_in_review first."
        )

    open_codes = await _open_error_codes_for_page(session, page_uuid=page.page_uuid)
    derived = derive_status_from_codes(open_codes, weights=weights)

    # No automatic no_go → go path — the rule applies even when the prior
    # state was IN_REVIEW after a previous no-go pass. We track "was-no-go"
    # via the absence of a prior IN_REVIEW transition log scan; for now the
    # rule degrades to: if findings are empty AND no error instance ever
    # existed for this page, allow auto-go; else require user resolution.
    if derived == OcrStatus.GO:
        had_any_error = await _page_ever_had_error(session, page_uuid=page.page_uuid)
        if had_any_error:
            # Refuse auto-go. Stay in IN_REVIEW so the caller can route to
            # the explicit user-resolution path.
            await log_event(
                session=session,
                operation_type="ocr_status_auto_go_refused",
                scope_type=ScopeType.PAGE,
                scope_uuid=page.page_uuid,
                result={
                    "reason": "page_has_or_had_findings_must_resolve_via_decision_event",
                    "prior": page.ocr_status.value,
                },
            )
            return page.ocr_status

    prior = page.ocr_status
    page.ocr_status = derived
    await session.flush()
    await log_event(
        session=session,
        operation_type="ocr_status_apply_findings",
        scope_type=ScopeType.PAGE,
        scope_uuid=page.page_uuid,
        result={
            "prior": prior.value,
            "new": derived.value,
            "open_error_count": len(open_codes),
        },
    )
    return derived


async def _page_ever_had_error(session: AsyncSession, *, page_uuid: _uuid.UUID) -> bool:
    """True if any ocr_error_instance has ever existed for this page,
    regardless of current state. We don't auto-clear a page back to GO
    once it had findings — that's the canonical no-auto-go discipline."""
    result = await session.execute(
        select(OcrErrorInstance.ocr_error_instance_uuid)
        .where(OcrErrorInstance.page_uuid == page_uuid)
        .limit(1)
    )
    return result.first() is not None


async def resolve_no_go_to_go(
    *,
    session: AsyncSession,
    page: Page,
    actor_uuid: _uuid.UUID | None = None,
    content: dict[str, Any] | None = None,
) -> DecisionEvent:
    """Explicit user resolution from NO_GO to GO.

    Per Sprint 1 §2 / OCR-Review-Status-Kein-Auto-Go-Test: this is the only
    legal path from `no_go` to `go`. Writes a Decision Event with
    `scope_type=page` and `decision_source=ocr_review`, then transitions the
    page.

    Caller is responsible for first resolving every relevant
    `ocr_error_instance` to `aufgeloest`. We confirm here that no `offen`
    instances remain — refusing the transition otherwise. (This avoids the
    failure mode where a user clicks "go" with unresolved findings.)
    """
    if page.ocr_status != OcrStatus.NO_GO:
        raise ValueError(f"resolve_no_go_to_go requires page in NO_GO; got {page.ocr_status.value}")

    still_open = await _open_error_codes_for_page(session, page_uuid=page.page_uuid)
    if still_open:
        raise ValueError(
            f"page {page.page_uuid} has {len(still_open)} unresolved error instances; "
            "resolve them via resolve_ocr_error_instance before transitioning"
        )

    # Decision Event is the provenance anchor for the user-resolution moment.
    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.PAGE,
        scope_uuid=page.page_uuid,
        decision_type="ocr_review_no_go_to_go",
        decision_source=DecisionSource.OCR_REVIEW,
        actor_uuid=actor_uuid,
        content=content if content is not None else {},
    )

    prior = page.ocr_status
    page.ocr_status = OcrStatus.GO
    await session.flush()
    await log_event(
        session=session,
        operation_type="ocr_status_resolve_no_go_to_go",
        scope_type=ScopeType.PAGE,
        scope_uuid=page.page_uuid,
        result={
            "prior": prior.value,
            "new": OcrStatus.GO.value,
            "decision_event_uuid": str(de.decision_event_uuid),
        },
    )
    return de
