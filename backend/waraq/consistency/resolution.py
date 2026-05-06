"""T-8.2.1 — Konsistenz-Befund resolution paths.

Per Sprint 4 §2:

- Resolution requires a Decision Event with `scope_type=project` and
  `decision_type=konsistenzgruppe_verbindlich`.
- `aufloesungsstatus` enum: `offen | aufgeloest | quittiert`.
  - `aufgeloest`: user accepted a canonical rendering; carries the
    Decision Event tied to the rendering choice.
  - `quittiert`: user acknowledged the finding without applying a
    rendering. Only available for `mittel`-class findings — `kritisch`
    and `hoch` cannot be quittiert (per Sprint 3 audit-quittierung
    discipline carried into consistency).

Both transitions stamp `resolved_at` + `resolution_decision_event_uuid`
atomically. The CHECK `ck_konsistenz_resolution_consistency` rejects
half-resolved rows at the DB layer.

The pre-resolution row is otherwise immutable after closing.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.consistency.exceptions import KonsistenzAlreadyClosed
from waraq.decisions import create_decision_event
from waraq.schemas import DecisionEvent, KonsistenzBefund
from waraq.schemas.enums import DecisionSource, ScopeType


class AufloesungsStatus(StrEnum):
    """ASCII transliteration of `auflösungsstatus` per Sprint 4 §2."""

    OFFEN = "offen"
    AUFGELOEST = "aufgeloest"
    QUITTIERT = "quittiert"


def _ensure_open(finding: KonsistenzBefund) -> None:
    if finding.aufloesungsstatus != AufloesungsStatus.OFFEN.value:
        raise KonsistenzAlreadyClosed(
            f"konsistenz_befund {finding.konsistenz_befund_uuid} already in "
            f"state {finding.aufloesungsstatus!r}; closed findings are immutable"
        )


async def resolve_konsistenz_befund(
    *,
    session: AsyncSession,
    finding: KonsistenzBefund,
    chosen_rendering: dict[str, Any],
    actor_uuid: _uuid.UUID | None = None,
    content: dict[str, Any] | None = None,
) -> DecisionEvent:
    """Path 1 — `konsistenzgruppe_verbindlich` resolution.

    User commits to a canonical rendering for the inconsistency group.
    Writes Decision Event with `decision_type=konsistenzgruppe_verbindlich`,
    `decision_source=consistency_resolution`, `scope_type=project`. The
    rendering itself is recorded in the DE content; it is NOT
    automatically applied to the affected Segments — that's a separate
    user action via the translation pipeline / glossary update.
    """
    _ensure_open(finding)

    de_content: dict[str, Any] = {
        "konsistenz_befund_uuid": str(finding.konsistenz_befund_uuid),
        "k_rule": finding.k_rule,
        "subject_type": finding.subject_type,
        "subject_key": finding.subject_key,
        "verstossklasse": finding.verstossklasse,
        "chosen_rendering": chosen_rendering,
        "betroffene_segment_count": len(finding.betroffene_segment_uuids),
    }
    if content:
        de_content.update(content)

    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=finding.project_uuid,
        decision_type="konsistenzgruppe_verbindlich",
        decision_source=DecisionSource.CONSISTENCY_RESOLUTION,
        actor_uuid=actor_uuid,
        content=de_content,
    )

    finding.aufloesungsstatus = AufloesungsStatus.AUFGELOEST.value
    finding.resolved_at = datetime.now(UTC)
    finding.resolution_decision_event_uuid = de.decision_event_uuid
    await session.flush()
    return de


async def quittiere_konsistenz_befund(
    *,
    session: AsyncSession,
    finding: KonsistenzBefund,
    actor_uuid: _uuid.UUID | None = None,
    content: dict[str, Any] | None = None,
) -> DecisionEvent:
    """Path 2 — `quittiert` (acknowledged without action).

    Available only for `mittel`-class findings (per Sprint 4 §2 / T-9.1.2:
    quittierte W-01-equivalents drop out of preflight gate evaluation).
    `kritisch` and `hoch` findings cannot be quittiert — they must be
    resolved with a chosen rendering.
    """
    _ensure_open(finding)
    if finding.verstossklasse != "mittel":
        raise ValueError(
            f"quittiere_konsistenz_befund: only `mittel`-class findings can "
            f"be quittiert; this finding is verstossklasse={finding.verstossklasse!r}. "
            "Use resolve_konsistenz_befund instead."
        )

    de_content: dict[str, Any] = {
        "konsistenz_befund_uuid": str(finding.konsistenz_befund_uuid),
        "k_rule": finding.k_rule,
        "subject_type": finding.subject_type,
        "subject_key": finding.subject_key,
        "verstossklasse": finding.verstossklasse,
        "action": "quittiert",
    }
    if content:
        de_content.update(content)

    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=finding.project_uuid,
        decision_type="konsistenzbefund_quittiert",
        decision_source=DecisionSource.CONSISTENCY_RESOLUTION,
        actor_uuid=actor_uuid,
        content=de_content,
    )

    finding.aufloesungsstatus = AufloesungsStatus.QUITTIERT.value
    finding.resolved_at = datetime.now(UTC)
    finding.resolution_decision_event_uuid = de.decision_event_uuid
    await session.flush()
    return de
