"""T-7.3.2 — Promotion Stufe 3 (`bestätige_stilregel` / `verwerfe_musterkandidat`).

Per Sprint 3 §2:

- **`bestaetige_stilregel(musterkandidat_uuid)` is the ONLY code path
  from Stufe 2 (Musterkandidat) to bestätigte Stilregel.** No internal
  API, no automatic threshold, no statistical promotion. H-7 is
  load-bearing here (T-H7-01).
- Confirmation creates a Decision Event with `scope_type=project`,
  `decision_type=stilregel_bestaetigung`, `decision_source=style_management`.
- Confirmed Stilregel is a NEW entity (`bestaetigte_stilregeln` row),
  distinct from the Musterkandidat. Musterkandidat is marked
  `state='bestaetigt'`, retains its observation evidence.
- Confirmed Stilregel does NOT auto-apply to translation production
  this sprint (Promotion-Stufe3-Stilregel-Inert-In-Translation-Test).
- `verwerfe_musterkandidat(musterkandidat_uuid)` writes a Decision
  Event with `decision_type=musterkandidat_verworfen` and marks the
  candidate `state='verworfen'`. Verworfene Kandidaten cannot be
  re-confirmed without fresh observations.
- Lernquellen-Asymmetrie (R-S3-11): the source-class metadata of the
  underlying observations is preserved on the confirmed Stilregel.

The module exposes ONLY these two functions. No private "_promote_now"
helper, no class with a method that takes a kandidat — code review
must trace the only path through `bestaetige_stilregel`.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.decisions import create_decision_event
from waraq.identity.service import new_uuid
from waraq.promotion.exceptions import (
    KandidatAlreadyConsumed,
    KandidatNotInKandidatState,
    PromotionError,
)
from waraq.schemas import (
    BestaetigteStilregel,
    DecisionEvent,
    Musterkandidat,
    TranslationObservation,
)
from waraq.schemas.enums import DecisionSource, ScopeType


async def _aggregate_source_classes(
    *,
    session: AsyncSession,
    musterkandidat: Musterkandidat,
) -> list[str]:
    """Return the distinct source-class values from observations grouped
    under the kandidat's project + pattern_key (preserves Lernquellen-
    Asymmetrie metadata per R-S3-11)."""
    result = await session.execute(
        select(TranslationObservation.source_class)
        .where(TranslationObservation.project_uuid == musterkandidat.project_uuid)
        .where(TranslationObservation.pattern_key == musterkandidat.pattern_key)
        .distinct()
    )
    return sorted({row[0] for row in result.all()})


async def bestaetige_stilregel(
    *,
    session: AsyncSession,
    musterkandidat_uuid: _uuid.UUID,
    actor_uuid: _uuid.UUID | None = None,
    annotation: str | None = None,
    extra_content: dict[str, Any] | None = None,
) -> tuple[BestaetigteStilregel, DecisionEvent]:
    """Confirm a Musterkandidat into a bestätigte Stilregel.

    The ONLY transition function `kandidat → bestaetigt`. Refuses on
    any other current state of the candidate (T-H7-01 + R-S3-10).

    Returns `(BestaetigteStilregel, DecisionEvent)` already flushed.
    """
    kandidat = await session.get(Musterkandidat, musterkandidat_uuid)
    if kandidat is None:
        raise PromotionError(f"Musterkandidat {musterkandidat_uuid} not found")
    if kandidat.state != "kandidat":
        # Either already bestaetigt, or verworfen and not re-confirmable.
        raise KandidatNotInKandidatState(
            f"Musterkandidat {musterkandidat_uuid} is in state {kandidat.state!r}; "
            "only kandidaten can be confirmed. Verworfene Kandidaten require "
            "fresh observations to be considered again."
        )

    # Idempotence guard: a kandidat can only land in bestaetigte_stilregeln
    # once (UNIQUE FK). Belt-and-braces against double-confirm races.
    existing = await session.execute(
        select(func.count())
        .select_from(BestaetigteStilregel)
        .where(BestaetigteStilregel.musterkandidat_uuid == musterkandidat_uuid)
    )
    if existing.scalar_one() > 0:
        raise KandidatAlreadyConsumed(
            f"Musterkandidat {musterkandidat_uuid} already has a confirmed Stilregel"
        )

    source_classes = await _aggregate_source_classes(session=session, musterkandidat=kandidat)

    de_content: dict[str, Any] = {
        "musterkandidat_uuid": str(musterkandidat_uuid),
        "pattern_key": kandidat.pattern_key,
        "observation_count": kandidat.observation_count,
        "source_classes": source_classes,
        "annotation": annotation,
    }
    if extra_content:
        de_content.update(extra_content)

    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=kandidat.project_uuid,
        decision_type="stilregel_bestaetigung",
        decision_source=DecisionSource.STYLE_MANAGEMENT,
        actor_uuid=actor_uuid,
        content=de_content,
    )

    stilregel = BestaetigteStilregel(
        stilregel_uuid=new_uuid(),
        musterkandidat_uuid=musterkandidat_uuid,
        project_uuid=kandidat.project_uuid,
        confirmation_decision_event_uuid=de.decision_event_uuid,
        annotation=annotation,
        pattern_key=kandidat.pattern_key,
        source_classes=source_classes,
    )
    session.add(stilregel)

    # Mark the kandidat as consumed.
    kandidat.state = "bestaetigt"
    await session.flush()

    return stilregel, de


async def verwerfe_musterkandidat(
    *,
    session: AsyncSession,
    musterkandidat_uuid: _uuid.UUID,
    actor_uuid: _uuid.UUID | None = None,
    annotation: str | None = None,
    extra_content: dict[str, Any] | None = None,
) -> tuple[Musterkandidat, DecisionEvent]:
    """Reject a Musterkandidat (alternative to `bestaetige_stilregel`).

    Writes a Decision Event with `decision_type=musterkandidat_verworfen`,
    `decision_source=style_management`, then marks the kandidat
    `state='verworfen'`. Per R-S3-10, a verworfener Kandidat cannot be
    re-confirmed without fresh observations producing a new candidate.
    """
    kandidat = await session.get(Musterkandidat, musterkandidat_uuid)
    if kandidat is None:
        raise PromotionError(f"Musterkandidat {musterkandidat_uuid} not found")
    if kandidat.state != "kandidat":
        raise KandidatNotInKandidatState(
            f"Musterkandidat {musterkandidat_uuid} is in state {kandidat.state!r}; "
            "only kandidaten can be rejected."
        )

    de_content: dict[str, Any] = {
        "musterkandidat_uuid": str(musterkandidat_uuid),
        "pattern_key": kandidat.pattern_key,
        "observation_count": kandidat.observation_count,
        "annotation": annotation,
    }
    if extra_content:
        de_content.update(extra_content)
    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=kandidat.project_uuid,
        decision_type="musterkandidat_verworfen",
        decision_source=DecisionSource.STYLE_MANAGEMENT,
        actor_uuid=actor_uuid,
        content=de_content,
    )

    kandidat.state = "verworfen"
    await session.flush()
    return kandidat, de


async def list_bestaetigte_stilregeln(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> list[BestaetigteStilregel]:
    """List confirmed Stilregeln for a project. Read-only — does not
    apply rules to translation (Promotion-Stufe3-Stilregel-Inert-In-
    Translation-Test)."""
    result = await session.execute(
        select(BestaetigteStilregel)
        .where(BestaetigteStilregel.project_uuid == project_uuid)
        .where(BestaetigteStilregel.active.is_(True))
        .order_by(BestaetigteStilregel.created_at.desc())
    )
    return list(result.scalars())
