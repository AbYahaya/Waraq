"""§4.15.3 + §4.15.5 — Project Qurʾān passage protection + 4-action mappings.

Per §4.15.3 protection: "Qurʾān passages already stored in projects
remain unchanged on changes to the Arabic Qurʾān reference collection
or to the local fallback copy of the translation. No automatic re-fetch,
no silent overwriting of existing project passages."

Implementation: passages are stored as **frozen snapshots** (the
`ProjectQuranPassage` row). Re-ingest of a fresher AR-Referenzbestand
or quranenc.com sync does NOT update existing rows — that's exactly
the structural property §4.15.3 requires. The `refresh_passage`
function is the only path that updates a passage to a fresher
collection version, and it requires an explicit user-initiated
Decision Event per §4.15.5 row 4.

§4.15.5 Qurʾān Passage Handling — decision_source Mapping (verbatim):

| Action                                                            | decision_source         |
|-------------------------------------------------------------------|-------------------------|
| Manual confirmation when confidence is below threshold            | translation_pipeline    |
| Correction of the Sura/Āya assignment                             | conflict_resolution     |
| Rejection as Qurʾān passage ("do not treat as Qurʾān")            | conflict_resolution     |
| Express user action to update an already stored Qurʾān passage    | translation_pipeline    |
| (following an update of the AR reference collection or the local  |                         |
|  fallback copy of the translation)                                |                         |

Automatic acceptance with confidence above threshold generates **no**
decision_event per the canon. No new decision_source values
(`decision_source` enum is unveränderlich per CLAUDE.md §5.9).

`record_recognized_passage` writes the snapshot for an
auto-recognized (above threshold) passage and does NOT emit a
Decision Event — that is the canonical "automatic acceptance"
behavior.
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.decisions import create_decision_event
from waraq.identity import new_uuid
from waraq.quran.recognition import RecognitionResult
from waraq.schemas import ArReferenzVerse, DecisionEvent, ProjectQuranPassage
from waraq.schemas.enums import DecisionSource, ScopeType


class ProjectPassageError(RuntimeError):
    """Common base for project-passage state-machine refusals."""


class PassageNotInExpectedState(ProjectPassageError):
    """Action attempted on a passage in the wrong lifecycle state."""


@dataclass(frozen=True, slots=True)
class RecordedPassage:
    """Outcome of recording a recognized passage. The Decision Event
    UUID is None for auto-accepted (above-threshold) passages per
    §4.15.5 ("Automatic acceptance with confidence above threshold
    generates no decision_event")."""

    passage: ProjectQuranPassage
    decision_event_uuid: _uuid.UUID | None


async def record_recognized_passage(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    satz_uuid: _uuid.UUID,
    recognition: RecognitionResult,
    translation_text: str | None = None,
    translation_key: str | None = None,
    translation_source_version: str | None = None,
    confidence_threshold: float = 0.85,
    actor_uuid: _uuid.UUID | None = None,
) -> RecordedPassage:
    """Snapshot a recognized passage onto the project.

    For auto-accepted passages (`confidence >= threshold`): writes
    the row with `state = "recognized"` and **no** Decision Event
    (per §4.15.5 canon).

    For below-threshold passages: writes the row with `state =
    "manually_confirmed"` AND a Decision Event with
    `decision_source = translation_pipeline` (§4.15.5 row 1: "Manual
    confirmation when confidence is below threshold"). Callers
    that wish to defer the manual-confirm decision (e.g., return a
    UI prompt instead of writing it immediately) should call
    `confirm_below_threshold` directly after recognition.

    Refuses to write when `recognition.matched is False`.
    """
    if not recognition.matched:
        raise ProjectPassageError("cannot record an unmatched recognition result")
    assert recognition.sura_index is not None
    assert recognition.aya_index_start is not None
    assert recognition.aya_index_end is not None

    above = recognition.above_threshold(confidence_threshold)
    state = "recognized" if above else "manually_confirmed"
    de_uuid: _uuid.UUID | None = None

    if not above:
        # §4.15.5 row 1 — translation_pipeline.
        de = await create_decision_event(
            session=session,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=satz_uuid,
            decision_type="quran_manual_confirmation_below_threshold",
            decision_source=DecisionSource.TRANSLATION_PIPELINE,
            actor_uuid=actor_uuid,
            content={
                "sura_index": recognition.sura_index,
                "aya_index_start": recognition.aya_index_start,
                "aya_index_end": recognition.aya_index_end,
                "confidence": recognition.confidence,
                "threshold": confidence_threshold,
            },
        )
        de_uuid = de.decision_event_uuid

    row = ProjectQuranPassage(
        passage_uuid=new_uuid(),
        project_uuid=project_uuid,
        satz_uuid=satz_uuid,
        sura_index=recognition.sura_index,
        aya_index_start=recognition.aya_index_start,
        aya_index_end=recognition.aya_index_end,
        snapshot_text_vocalized=recognition.matched_text_vocalized,
        snapshot_translation_text=translation_text,
        ar_source_name=recognition.ar_source_name,
        ar_source_version=recognition.ar_source_version,
        translation_key=translation_key,
        translation_source_version=translation_source_version,
        confidence=recognition.confidence,
        state=state,
        last_decision_event_uuid=de_uuid,
        last_state_change_at=datetime.now(UTC) if not above else None,
    )
    session.add(row)
    await session.flush()
    return RecordedPassage(passage=row, decision_event_uuid=de_uuid)


async def correct_sura_aya(
    *,
    session: AsyncSession,
    passage: ProjectQuranPassage,
    new_sura_index: int,
    new_aya_index_start: int,
    new_aya_index_end: int,
    actor_uuid: _uuid.UUID | None = None,
    note: str | None = None,
) -> DecisionEvent:
    """§4.15.5 row 2 — user corrects the sura/āya assignment.

    Looks up the corrected (sura, aya_start..end) range in the same
    AR-Referenzbestand source/version that the snapshot already
    references, refreshes the vocalized text + range fields, and
    writes a Decision Event with `decision_source=conflict_resolution`.

    Refuses on `state == "rejected"` (correcting a rejected passage
    requires re-recognizing first; this avoids accidentally
    resurrecting rejected passages without explicit user intent).
    """
    if passage.state == "rejected":
        raise PassageNotInExpectedState(
            f"cannot correct passage {passage.passage_uuid}: state=rejected"
        )
    if not (1 <= new_sura_index <= 114):
        raise ValueError("new_sura_index out of range 1..114")
    if new_aya_index_start < 1 or new_aya_index_end < new_aya_index_start:
        raise ValueError("invalid (aya_start, aya_end) range")

    # Resolve the new range against the same AR source the snapshot used.
    rows = list(
        (
            await session.execute(
                select(ArReferenzVerse)
                .where(ArReferenzVerse.source_name == passage.ar_source_name)
                .where(ArReferenzVerse.source_version == passage.ar_source_version)
                .where(ArReferenzVerse.sura_index == new_sura_index)
                .where(ArReferenzVerse.aya_index >= new_aya_index_start)
                .where(ArReferenzVerse.aya_index <= new_aya_index_end)
                .order_by(ArReferenzVerse.aya_index)
            )
        ).scalars()
    )
    if not rows or len(rows) != (new_aya_index_end - new_aya_index_start + 1):
        raise ValueError(
            f"corrected range {new_sura_index}:"
            f"{new_aya_index_start}-{new_aya_index_end} not present in "
            f"AR source {passage.ar_source_name}@{passage.ar_source_version}"
        )

    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=passage.satz_uuid,
        decision_type="quran_correct_sura_aya",
        decision_source=DecisionSource.CONFLICT_RESOLUTION,
        actor_uuid=actor_uuid,
        content={
            "passage_uuid": str(passage.passage_uuid),
            "old": {
                "sura_index": passage.sura_index,
                "aya_index_start": passage.aya_index_start,
                "aya_index_end": passage.aya_index_end,
            },
            "new": {
                "sura_index": new_sura_index,
                "aya_index_start": new_aya_index_start,
                "aya_index_end": new_aya_index_end,
            },
            "note": note,
        },
    )

    passage.sura_index = new_sura_index
    passage.aya_index_start = new_aya_index_start
    passage.aya_index_end = new_aya_index_end
    passage.snapshot_text_vocalized = " ".join(r.text_vocalized for r in rows)
    passage.state = "corrected"
    passage.last_decision_event_uuid = de.decision_event_uuid
    passage.last_state_change_at = datetime.now(UTC)
    await session.flush()
    return de


async def reject_as_quran(
    *,
    session: AsyncSession,
    passage: ProjectQuranPassage,
    actor_uuid: _uuid.UUID | None = None,
    note: str | None = None,
) -> DecisionEvent:
    """§4.15.5 row 3 — user says "do not treat as Qurʾān".

    Marks the passage `rejected` and writes a Decision Event with
    `decision_source=conflict_resolution`. Idempotent on already-
    rejected passages (raises `PassageNotInExpectedState`).
    """
    if passage.state == "rejected":
        raise PassageNotInExpectedState(f"passage {passage.passage_uuid} already rejected")

    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=passage.satz_uuid,
        decision_type="quran_reject_as_quran",
        decision_source=DecisionSource.CONFLICT_RESOLUTION,
        actor_uuid=actor_uuid,
        content={
            "passage_uuid": str(passage.passage_uuid),
            "previous_state": passage.state,
            "note": note,
        },
    )
    passage.state = "rejected"
    passage.last_decision_event_uuid = de.decision_event_uuid
    passage.last_state_change_at = datetime.now(UTC)
    await session.flush()
    return de


async def confirm_below_threshold(
    *,
    session: AsyncSession,
    passage: ProjectQuranPassage,
    actor_uuid: _uuid.UUID | None = None,
    note: str | None = None,
) -> DecisionEvent:
    """§4.15.5 row 1 — manual confirmation under threshold.

    Used when `record_recognized_passage` was called with `state =
    "recognized"` (above threshold) but the user later decides to
    explicitly confirm a borderline match. Or when a separate
    callsite recognized + stored a below-threshold passage in
    `recognized` state pending UI confirmation. Writes a Decision
    Event with `decision_source=translation_pipeline`.
    """
    if passage.state != "recognized":
        raise PassageNotInExpectedState(
            f"confirm_below_threshold expects state=recognized; "
            f"passage {passage.passage_uuid} is in state={passage.state}"
        )
    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=passage.satz_uuid,
        decision_type="quran_manual_confirmation",
        decision_source=DecisionSource.TRANSLATION_PIPELINE,
        actor_uuid=actor_uuid,
        content={
            "passage_uuid": str(passage.passage_uuid),
            "confidence": passage.confidence,
            "note": note,
        },
    )
    passage.state = "manually_confirmed"
    passage.last_decision_event_uuid = de.decision_event_uuid
    passage.last_state_change_at = datetime.now(UTC)
    await session.flush()
    return de


async def refresh_passage_from_collection(
    *,
    session: AsyncSession,
    passage: ProjectQuranPassage,
    new_ar_source_name: str | None = None,
    new_ar_source_version: str | None = None,
    new_translation_key: str | None = None,
    new_translation_source_version: str | None = None,
    new_translation_text: str | None = None,
    actor_uuid: _uuid.UUID | None = None,
    note: str | None = None,
) -> DecisionEvent:
    """§4.15.5 row 4 — express user action to update a stored passage
    after an AR-Referenzbestand or translation-fallback update.

    Writes a Decision Event with `decision_source=translation_pipeline`
    and (only on the user's explicit instruction!) refreshes the
    snapshot fields with the new collection version's text. Refuses
    on rejected passages.

    All `new_*` parameters are optional — pass exactly the fields the
    user wants refreshed; the rest stay frozen at the prior snapshot.
    The `(ar_source_name, ar_source_version)` pair and the AR text
    are looked up from the live `ArReferenzVerse` table when
    `new_ar_source_*` is given.
    """
    if passage.state == "rejected":
        raise PassageNotInExpectedState(f"cannot refresh rejected passage {passage.passage_uuid}")

    # Resolve the new AR text if the caller wants AR refreshed.
    new_ar_text: str | None = None
    if new_ar_source_name or new_ar_source_version:
        target_name = new_ar_source_name or passage.ar_source_name
        target_version = new_ar_source_version or passage.ar_source_version
        rows = list(
            (
                await session.execute(
                    select(ArReferenzVerse)
                    .where(ArReferenzVerse.source_name == target_name)
                    .where(ArReferenzVerse.source_version == target_version)
                    .where(ArReferenzVerse.sura_index == passage.sura_index)
                    .where(ArReferenzVerse.aya_index >= passage.aya_index_start)
                    .where(ArReferenzVerse.aya_index <= passage.aya_index_end)
                    .order_by(ArReferenzVerse.aya_index)
                )
            ).scalars()
        )
        expected = passage.aya_index_end - passage.aya_index_start + 1
        if len(rows) != expected:
            raise ValueError(
                f"AR source {target_name}@{target_version} does not carry "
                f"sura {passage.sura_index} ʾāyāt "
                f"{passage.aya_index_start}-{passage.aya_index_end}"
            )
        new_ar_text = " ".join(r.text_vocalized for r in rows)

    de_content: dict[str, Any] = {
        "passage_uuid": str(passage.passage_uuid),
        "old_ar_source": [passage.ar_source_name, passage.ar_source_version],
        "old_translation_source": [
            passage.translation_key,
            passage.translation_source_version,
        ],
        "note": note,
    }
    if new_ar_source_name or new_ar_source_version:
        de_content["new_ar_source"] = [
            new_ar_source_name or passage.ar_source_name,
            new_ar_source_version or passage.ar_source_version,
        ]
    if new_translation_key or new_translation_source_version or new_translation_text:
        de_content["new_translation_source"] = [
            new_translation_key or passage.translation_key,
            new_translation_source_version or passage.translation_source_version,
        ]

    de = await create_decision_event(
        session=session,
        scope_type=ScopeType.SEGMENT,
        scope_uuid=passage.satz_uuid,
        decision_type="quran_refresh_from_collection",
        decision_source=DecisionSource.TRANSLATION_PIPELINE,
        actor_uuid=actor_uuid,
        content=de_content,
    )

    if new_ar_source_name:
        passage.ar_source_name = new_ar_source_name
    if new_ar_source_version:
        passage.ar_source_version = new_ar_source_version
    if new_ar_text is not None:
        passage.snapshot_text_vocalized = new_ar_text
    if new_translation_key:
        passage.translation_key = new_translation_key
    if new_translation_source_version:
        passage.translation_source_version = new_translation_source_version
    if new_translation_text is not None:
        passage.snapshot_translation_text = new_translation_text
    passage.state = "refreshed"
    passage.last_decision_event_uuid = de.decision_event_uuid
    passage.last_state_change_at = datetime.now(UTC)
    await session.flush()
    return de


__all__ = [
    "PassageNotInExpectedState",
    "ProjectPassageError",
    "RecordedPassage",
    "confirm_below_threshold",
    "correct_sura_aya",
    "record_recognized_passage",
    "refresh_passage_from_collection",
    "reject_as_quran",
]
