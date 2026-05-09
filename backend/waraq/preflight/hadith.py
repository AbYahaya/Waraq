"""T-9.1.2 — Hadith-Verifikationsstatus group (Dokument 1 §4.16 + §4.7.5).

The Hadith-Verifikationsstatus group is an **eigene benannte Gruppe
innerhalb der Gate-Prüfungsschicht** — it does NOT occupy any P-Slot
or W-Slot (HG-S4-5). Implementation must keep this structural property
visible at the data-model level: the gate-evaluation result objects
emit Hadith findings as a separate group, never folded into a slot.

Class derivation (deterministic per §4.16.4):
    H-0 (review-internally tolerable):           N-1, N-3, N-9
    H-1 (logging-mandatory, warning-capable):    N-2, N-10
    H-2 (export-blocking until resolution):      N-4, N-5, N-6, N-7, N-8

H-2 resolution flows exclusively through the seven canonical action
types (§4.16.5) — none of them adds a new `decision_source`. The action
types map to existing `translation_pipeline` (2) or
`conflict_resolution` (5) values.

H-1 supports `go_with_warning` per §4.9 E-1: the user may proceed with
explicit warning-acknowledgement, which writes a Decision Event with
`decision_source=preflight_confirmation` per §4.10.

H-0 is review-internally tolerable; no gate-evaluation contribution.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.decisions import create_decision_event
from waraq.identity.service import new_uuid
from waraq.preflight.enums import HadithKlasse, HadithStellenTyp
from waraq.schemas import DecisionEvent, HadithPassageStatus
from waraq.schemas.enums import DecisionSource, ScopeType

# Per Dokument 1 §4.16.5 — the 7 canonized action types for H-2 resolution.
# Each maps to one of two existing decision_source values; no new values.
HADITH_ACTION_TYPES: dict[str, DecisionSource] = {
    "verifizierte_version_uebernehmen": DecisionSource.TRANSLATION_PIPELINE,
    "vollversion_statt_kurzversion": DecisionSource.TRANSLATION_PIPELINE,
    "autorenwortlaut_beibehalten": DecisionSource.CONFLICT_RESOLUTION,
    "quellenangabe_aendern_oder_nicht": DecisionSource.CONFLICT_RESOLUTION,
    "ohne_externe_verifikation_fortfahren": DecisionSource.CONFLICT_RESOLUTION,
    "passage_nicht_als_hadith_behandeln": DecisionSource.CONFLICT_RESOLUTION,
    "vokalisierungskonflikt_manuell_entscheiden": DecisionSource.CONFLICT_RESOLUTION,
}


_KLASSE_BY_TYP: dict[HadithStellenTyp, HadithKlasse] = {
    HadithStellenTyp.N_1: HadithKlasse.H_0,
    HadithStellenTyp.N_3: HadithKlasse.H_0,
    HadithStellenTyp.N_9: HadithKlasse.H_0,
    HadithStellenTyp.N_2: HadithKlasse.H_1,
    HadithStellenTyp.N_10: HadithKlasse.H_1,
    HadithStellenTyp.N_4: HadithKlasse.H_2,
    HadithStellenTyp.N_5: HadithKlasse.H_2,
    HadithStellenTyp.N_6: HadithKlasse.H_2,
    HadithStellenTyp.N_7: HadithKlasse.H_2,
    HadithStellenTyp.N_8: HadithKlasse.H_2,
}


def derive_hadith_klasse(stellen_typ: HadithStellenTyp | str) -> HadithKlasse:
    """Per §4.16.6: Hadith-Verifikationsklasse is deterministically
    derivable from passage type, never independently persisted.

    Accepts the StrEnum or its raw string. The fallback rule per
    §4.16.4 ("higher class or riskier state under ambiguity") is moot
    here — the table is total.
    """
    if isinstance(stellen_typ, str):
        stellen_typ = HadithStellenTyp(stellen_typ)
    return _KLASSE_BY_TYP[stellen_typ]


async def record_hadith_status(
    *,
    session: AsyncSession,
    satz_uuid: _uuid.UUID,
    project_uuid: _uuid.UUID,
    stellen_typ: HadithStellenTyp,
) -> HadithPassageStatus:
    """Record a fresh Hadith-Verifikationsstatus row (default `state=offen`).

    Used by the verification pipeline (full Schnittstelle 3 work parked
    in Block 3); v1.0 callers in Sprint 4 use this to seed test cases
    and to wire the manual-creation path from the future review UI.
    """
    row = HadithPassageStatus(
        hadith_status_uuid=new_uuid(),
        satz_uuid=satz_uuid,
        project_uuid=project_uuid,
        hadith_stellen_typ=stellen_typ.value,
    )
    session.add(row)
    await session.flush()
    return row


async def resolve_hadith_h2(
    *,
    session: AsyncSession,
    status: HadithPassageStatus,
    action_type: str,
    actor_uuid: _uuid.UUID | None = None,
    content: dict[str, Any] | None = None,
) -> DecisionEvent:
    """Path 1 — H-2 resolution via one of the 7 canonical action types.

    Refuses unknown action types. Marks the status `aufgeloest` with the
    Decision Event reference.
    """
    klasse = derive_hadith_klasse(status.hadith_stellen_typ)
    if klasse != HadithKlasse.H_2:
        raise ValueError(
            f"resolve_hadith_h2 expects H-2; passage is {klasse.value} "
            f"(stellen_typ={status.hadith_stellen_typ})"
        )
    if action_type not in HADITH_ACTION_TYPES:
        raise ValueError(
            f"action_type {action_type!r} is not one of the 7 canonical "
            f"§4.16.5 types: {sorted(HADITH_ACTION_TYPES)}"
        )
    if status.state != "offen":
        raise ValueError(
            f"hadith_passage_status {status.hadith_status_uuid} already in "
            f"state {status.state!r}; cannot re-resolve"
        )

    de_content: dict[str, Any] = {
        "hadith_status_uuid": str(status.hadith_status_uuid),
        "satz_uuid": str(status.satz_uuid),
        "stellen_typ": status.hadith_stellen_typ,
        "klasse": klasse.value,
        "action_type": action_type,
    }
    if content:
        de_content.update(content)

    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=status.project_uuid,
        decision_type=f"hadith_{action_type}",
        decision_source=HADITH_ACTION_TYPES[action_type],
        actor_uuid=actor_uuid,
        content=de_content,
    )

    status.state = "aufgeloest"
    status.resolved_at = datetime.now(UTC)
    status.resolution_decision_event_uuid = de.decision_event_uuid
    await session.flush()
    return de


async def go_with_warning_hadith(
    *,
    session: AsyncSession,
    status: HadithPassageStatus,
    actor_uuid: _uuid.UUID | None = None,
    content: dict[str, Any] | None = None,
) -> DecisionEvent:
    """Path 2 — H-1 `go_with_warning` confirmation per §4.9 E-1.

    Writes a Decision Event with `decision_source=preflight_confirmation`
    (§4.10). Marks the status `quittiert` so subsequent preflight
    evaluations no longer count this passage as an active warning gate.

    Refused on H-2 (must be resolved via action types) and H-0 (no
    warning to acknowledge).
    """
    klasse = derive_hadith_klasse(status.hadith_stellen_typ)
    if klasse != HadithKlasse.H_1:
        raise ValueError(
            f"go_with_warning_hadith expects H-1; passage is {klasse.value} "
            f"(stellen_typ={status.hadith_stellen_typ})"
        )
    if status.state != "offen":
        raise ValueError(
            f"hadith_passage_status {status.hadith_status_uuid} already in "
            f"state {status.state!r}; cannot re-acknowledge"
        )

    de_content: dict[str, Any] = {
        "hadith_status_uuid": str(status.hadith_status_uuid),
        "satz_uuid": str(status.satz_uuid),
        "stellen_typ": status.hadith_stellen_typ,
        "klasse": klasse.value,
        "action": "go_with_warning",
    }
    if content:
        de_content.update(content)

    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.PROJECT,
        scope_uuid=status.project_uuid,
        decision_type="hadith_go_with_warning",
        decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        actor_uuid=actor_uuid,
        content=de_content,
    )

    status.state = "quittiert"
    status.resolved_at = datetime.now(UTC)
    status.resolution_decision_event_uuid = de.decision_event_uuid
    await session.flush()
    return de
