"""T-9.1.1 — Konfigurationsschicht (vier Pflichtfragen).

Per Sprint 4 §2:

> "Konfigurationsschicht — vier Pflichtfragen. Active confirmation
> required ... A saved Export-Profil may pre-fill Pflichtfragen but
> never replaces an active confirmation. The user must actively confirm
> at the time of export."

> "The Konfigurationsschicht does not occupy any P-Slot. Failure to
> actively confirm one or more Pflichtfragen produces preflight state
> `blockiert` with a distinct reason (Konfigurationsschicht
> unvollständig)."

The 4-count is canonical (`PFLICHTFRAGE_COUNT`). The questions
themselves are configurable per Dokument 2 §2.3 — keys passed in by
callers, opaque to this layer.

Each active confirmation creates a Decision Event with
`scope_type=project` and `decision_source=preflight_confirmation`
(§4.10), tagged with `related_export_attempt_id=<preflight_run_uuid>`
so the Konfigurationsschicht-evaluator can count "active confirmations
for the current run" without re-reading the entire history.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.decisions import create_decision_event
from waraq.identity.service import new_uuid
from waraq.preflight.exceptions import PreflightError
from waraq.preflight.pflichtfragen import validate_pflichtfrage_answer
from waraq.schemas import DecisionEvent, PflichtfrageProfil
from waraq.schemas.enums import DecisionSource, ScopeType

PFLICHTFRAGE_COUNT = 4
"""Per Sprint 4 §2 / Dokument 2 §2.3 — the four-count is canonical."""


async def save_export_profile_prefill(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    frage_index: int,
    frage_key: str,
    prefilled_answer: dict[str, Any],
) -> PflichtfrageProfil:
    """Persist a saved Export-Profil pre-fill for a Pflichtfrage.

    Storing a pre-fill is **not** an active confirmation. Per Sprint 4
    §2, "saved profile pre-fills but never replaces". The
    Konfigurationsschicht-evaluator never accepts a profile row as a
    confirmation; it requires a Decision Event with
    `decision_source=preflight_confirmation` AND
    `related_export_attempt_id=<current_run_uuid>`.

    Idempotent: re-calling for the same (project, frage_index)
    overwrites the pre-fill via the unique key.
    """
    if not (1 <= frage_index <= PFLICHTFRAGE_COUNT):
        raise PreflightError(f"frage_index must be in [1, {PFLICHTFRAGE_COUNT}]; got {frage_index}")

    # §4.7.2 — pre-fills must satisfy the canonical answer schema; a
    # malformed pre-fill should fail loudly here, not silently produce
    # a confirmation later that the evaluator counts.
    validated_prefill = validate_pflichtfrage_answer(
        frage_index=frage_index, frage_key=frage_key, answer=prefilled_answer
    )

    # Upsert by (project_uuid, frage_index) — the table has UNIQUE on that pair.
    from sqlalchemy import select

    existing_q = await session.execute(
        select(PflichtfrageProfil)
        .where(PflichtfrageProfil.project_uuid == project_uuid)
        .where(PflichtfrageProfil.frage_index == frage_index)
    )
    existing = existing_q.scalar_one_or_none()
    if existing is not None:
        existing.frage_key = frage_key
        existing.prefilled_answer = validated_prefill
        await session.flush()
        return existing

    row = PflichtfrageProfil(
        profil_uuid=new_uuid(),
        project_uuid=project_uuid,
        frage_index=frage_index,
        frage_key=frage_key,
        prefilled_answer=validated_prefill,
    )
    session.add(row)
    await session.flush()
    return row


async def confirm_pflichtfrage(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    preflight_run_uuid: _uuid.UUID,
    frage_index: int,
    frage_key: str,
    answer: dict[str, Any],
    actor_uuid: _uuid.UUID | None = None,
) -> DecisionEvent:
    """Active confirmation of one Pflichtfrage for the current preflight run.

    Writes a Decision Event with:
    - scope_type = project
    - decision_type = "pflichtfrage_bestaetigung"
    - decision_source = preflight_confirmation (§4.10)
    - related_export_attempt_id = str(preflight_run_uuid)

    The Konfigurationsschicht-evaluator counts these per run: a run with
    fewer than 4 distinct frage_indexes confirmed is `blockiert`
    (Konfigurationsschicht unvollständig — does NOT occupy P-Slot).
    """
    if not (1 <= frage_index <= PFLICHTFRAGE_COUNT):
        raise PreflightError(f"frage_index must be in [1, {PFLICHTFRAGE_COUNT}]; got {frage_index}")

    # §4.7.2 — only canonical-shape answers may become active confirmations.
    validated_answer = validate_pflichtfrage_answer(
        frage_index=frage_index, frage_key=frage_key, answer=answer
    )

    de_content: dict[str, Any] = {
        "frage_index": frage_index,
        "frage_key": frage_key,
        "answer": validated_answer,
        "preflight_run_uuid": str(preflight_run_uuid),
    }

    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=project_uuid,
        decision_type="pflichtfrage_bestaetigung",
        decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        actor_uuid=actor_uuid,
        content=de_content,
        related_export_attempt_id=str(preflight_run_uuid),
    )
    return de
