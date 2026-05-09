"""T-7.3.1 — Promotion pipeline Stufen 1-2.

Per Sprint 2 §2:

- **Stufe 1 (Beobachtung)**: when a user manually corrects a translated
  Segment (Revision with `change_source = manual`), `record_observation`
  writes a `translation_observations` row. NOT a PO. NOT a Decision
  Event. (Promotion-Kein-Decision-Event-Bei-Beobachtung-Test.)

- **Stufe 2 (Musterkandidat)**: `aggregate_into_musterkandidaten` scans
  observations grouped by `pattern_key`; when count crosses a
  configurable threshold, registers/updates a `musterkandidaten` row in
  `state=kandidat`. Registration writes a Log-Eintrag via EVENTING.
  Does NOT write a Decision Event. Does NOT create a glossary entry.

- **Inert in translation production**: Musterkandidaten are NOT consumed
  by the translation pipeline. Only confirmed glossary entries
  (T-5.2.1) are. (Promotion-Kandidat-Inert-In-Translation-Test.)

- **No auto-promotion**: H-7. The state machine has only `kandidat`
  here; the transition to `bestaetigt` lives exclusively in T-7.3.2
  (Sprint 3) via an explicit `bestaetige_stilregel(musterkandidat_uuid)`
  user action. There is no transition function in this module from
  `kandidat` → `bestaetigt`. (T-H7-01.)

Threshold is **configurable**, never hard-coded (R-S2-10 /
Promotion-Schwellenwert-Konfigurations-Test). Callers pass it on
`aggregate_into_musterkandidaten`. The shipped default
(`DEFAULT_MUSTERKANDIDAT_THRESHOLD`) is a starting point only,
explicitly NOT canonical (Sprint 2 §B "Calibration values: ... all
configurable, never pre-set"); production callers should load from a
config table.

Lernquellen-Asymmetrie (Dokument 1 §4.13 / DBB §7.5): the 5 source-class
values are recorded on every observation but partitioning behaviour is
**not yet differentiated** — Sprint 3+ work refines this.
"""

from __future__ import annotations

import uuid as _uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.eventing import log_event
from waraq.identity.service import new_uuid
from waraq.schemas import Musterkandidat, Revision, Segment, TranslationObservation
from waraq.schemas.enums import ChangeSource, ScopeType


class SourceClass(StrEnum):
    """Per Dokument 1 §4.13 — 5 canonical learning-source classes (ASCII
    transliteration; canonical German with umlauts is the user-facing
    form, ASCII is the wire/DB form)."""

    BESTAETIGTE_REFERENZSAETZE = "bestaetigte_referenzsaetze"
    MANUELLE_NUTZERREGELN = "manuelle_nutzerregeln"
    AKZEPTIERTE_KI_VORSCHLAEGE = "akzeptierte_ki_vorschlaege"
    KORRIGIERTE_KI_VORSCHLAEGE = "korrigierte_ki_vorschlaege"
    IGNORIERTE_KI_VORSCHLAEGE = "ignorierte_ki_vorschlaege"


# Shell default — non-canonical, calibration is post-Gold-Corpus work.
# A meaningful threshold avoids registering after a single observation
# but stays low enough that test fixtures can hit it.
DEFAULT_MUSTERKANDIDAT_THRESHOLD: int = 3


# A bounded sample size to keep `Musterkandidat.sample_corrections`
# from unbounded growth. Not canonical; pragmatic.
_MAX_SAMPLES_PER_KANDIDAT: int = 8


def _normalize_pattern_key(source_text: str) -> str:
    """Simple v1.0 pattern key: casefold + collapse internal whitespace.
    Real partitioning per DBB §7.5 is later refinement; the canonical
    constraint is just that the key is deterministic."""
    return " ".join(source_text.casefold().split())


# --- Stufe 1: record_observation -----------------------------------


async def record_observation(
    *,
    session: AsyncSession,
    revision: Revision,
    segment: Segment,
    project_uuid: _uuid.UUID,
    prior_translation: str,
    user_correction: str,
    source_text: str | None = None,
    terminology_bindings: dict[str, Any] | None = None,
    source_class: SourceClass = SourceClass.MANUELLE_NUTZERREGELN,
) -> TranslationObservation:
    """Persist a Stufe 1 observation row.

    Refuses revisions whose `change_source` is not `manual` — observation
    by definition records USER corrections (Sprint 2 §2:
    "manual edit that produces a new revision via T-1.4.1 with
    `change_source = manual`").

    `source_text` represents the SEGMENT INPUT (typically Arabic source)
    that produced the engine's translation. When omitted, it defaults to
    `revision.before_text` — fine for single-correction observations,
    but cross-correction aggregation requires callers pass a shared
    canonical source string explicitly so `pattern_key` matches across
    observations of the same recurring phrase.
    """
    if revision.change_source != ChangeSource.MANUAL.value:
        raise ValueError(
            f"record_observation requires a Revision with change_source=manual; "
            f"got {revision.change_source!r}. Stufe 1 captures user corrections, "
            "not engine-produced revisions."
        )

    effective_source_text = source_text if source_text is not None else (revision.before_text or "")

    obs = TranslationObservation(
        observation_uuid=new_uuid(),
        revision_uuid=revision.rev_uuid,
        satz_uuid=segment.satz_uuid,
        project_uuid=project_uuid,
        source_text=effective_source_text,
        prior_translation=prior_translation,
        user_correction=user_correction,
        terminology_bindings=terminology_bindings if terminology_bindings is not None else {},
        source_class=source_class.value,
        pattern_key=_normalize_pattern_key(effective_source_text),
    )
    session.add(obs)
    await session.flush()
    return obs


# --- Stufe 2: aggregate_into_musterkandidaten ----------------------


async def aggregate_into_musterkandidaten(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    threshold: int = DEFAULT_MUSTERKANDIDAT_THRESHOLD,
) -> list[Musterkandidat]:
    """Scan observations for `project_uuid`; for every `pattern_key` whose
    observation count meets `threshold`, register or update a
    `musterkandidaten` row in `state=kandidat`. Returns the newly
    registered + updated rows.

    Does NOT consume Musterkandidaten in any translation pass. Does NOT
    create glossary entries. Does NOT write Decision Events. Writes one
    Log-Eintrag per registered/updated kandidat via EVENTING.

    Threshold is required by signature (default available, but callers
    can override per call — that's the configurability contract).
    """
    if threshold < 1:
        raise ValueError(f"threshold must be >= 1; got {threshold}")

    # Group observations by pattern_key, count rows.
    grouped = await session.execute(
        select(
            TranslationObservation.pattern_key,
            func.count().label("count"),
            func.min(TranslationObservation.created_at).label("first_at"),
            func.max(TranslationObservation.created_at).label("last_at"),
        )
        .where(TranslationObservation.project_uuid == project_uuid)
        .group_by(TranslationObservation.pattern_key)
        .having(func.count() >= threshold)
    )

    registered: list[Musterkandidat] = []
    for pattern_key, count, first_at, last_at in grouped:
        # Sample of user_corrections for this pattern (bounded).
        sample_rows = await session.execute(
            select(TranslationObservation.user_correction)
            .where(TranslationObservation.project_uuid == project_uuid)
            .where(TranslationObservation.pattern_key == pattern_key)
            .order_by(TranslationObservation.created_at.desc())
            .limit(_MAX_SAMPLES_PER_KANDIDAT)
        )
        samples = list(sample_rows.scalars())

        # Upsert: if a kandidat already exists for this (project,
        # pattern_key), update it; else insert.
        existing = await session.execute(
            select(Musterkandidat)
            .where(Musterkandidat.project_uuid == project_uuid)
            .where(Musterkandidat.pattern_key == pattern_key)
        )
        kandidat = existing.scalar_one_or_none()

        if kandidat is None:
            kandidat = Musterkandidat(
                musterkandidat_uuid=new_uuid(),
                project_uuid=project_uuid,
                pattern_key=pattern_key,
                observation_count=count,
                sample_corrections=samples,
                state="kandidat",
                first_observed_at=first_at,
                last_observed_at=last_at,
            )
            session.add(kandidat)
        else:
            kandidat.observation_count = count
            kandidat.sample_corrections = samples
            kandidat.last_observed_at = last_at

        await session.flush()

        await log_event(
            session=session,
            operation_type="musterkandidat_registered",
            scope_type=ScopeType.PROJECT,
            scope_uuid=project_uuid,
            result={
                "musterkandidat_uuid": str(kandidat.musterkandidat_uuid),
                "pattern_key": pattern_key,
                "observation_count": count,
            },
        )

        registered.append(kandidat)

    return registered


async def list_musterkandidaten(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> list[Musterkandidat]:
    """Read API for the future T-7.3.2 confirmation surface. Returns all
    Musterkandidaten for `project_uuid` ordered by observation_count
    descending."""
    result = await session.execute(
        select(Musterkandidat)
        .where(Musterkandidat.project_uuid == project_uuid)
        .order_by(Musterkandidat.observation_count.desc())
    )
    return list(result.scalars())
