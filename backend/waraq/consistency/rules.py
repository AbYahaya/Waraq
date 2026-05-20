"""T-8.2.1 — K-rule real bodies (Sprint 4 §2 §A HG-S4-1).

Per Sprint 4 §A HG-S4-1: each K-rule reads only its **passende
Identitätstyp** records — never `surface_form` for equality. The seven
rules fall into two structural shapes:

A) **Concept- / entity-binding rules**: K-01, K-03, K-07.
   These read RULE_BINDING-PO rows whose payload carries `concept_id`
   (K-01, K-07) or `entity_id` (K-03), grouping bindings by that key.
   For each group spanning >=2 distinct Segments, the rule examines
   `applied_rendering` values from the PO payload. **Distinct
   applied_rendering values within one group → finding.**

B) **Identitätstyp-table rules**: K-02, K-04, K-05, K-06.
   Each reads its passende Identitätstyp scaffold table
   (formel_verzeichnis_eintraege, transliterations_muster_eintraege,
   quellen_identitaeten, strukturelle_schluessel). For each identity
   record, the rule scans Segments whose source-side text matches
   `source_pattern`; if some Segments use `expected_rendering` in the
   target while others diverge, a finding is emitted.

K-07 is structurally K-01 with cross-rule scope — for v1.0 it shares
the concept_id basis but additionally considers RULE_BINDING-POs whose
payload `application_context.rule` differs across the group (i.e., the
inconsistency is across rule applications, not within a single rule).

**Calibration values are never pre-set** (Sprint 4 §B). The detection
mechanism here is structural and deterministic — distinct rendering
values count as inconsistency, full stop. Severity weight tables and
detection thresholds remain configurable per project.

**Routing into preflight is computed at preflight evaluation, not
stored on the Konsistenz-Befund row** (Sprint 4 §2). All K-rules emit
findings with an initial `verstossklasse` reflecting the rule's own
severity baseline; preflight may upgrade to P-03 if the finding
simultaneously violates a Kritisch-Klasse per Dokument 1 §4.6.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.consistency.engine import (
    KConsistencyFinding,
    KRuleId,
    SubjectType,
    Verstossklasse,
    register_k_rule,
)
from waraq.schemas import (
    Concept,
    Entity,
    FormelVerzeichnisEintrag,
    ProvenanceObject,
    QuellenIdentitaet,
    Segment,
    StrukturellerSchluessel,
    TransliterationsMusterEintrag,
)
from waraq.schemas.enums import POType
from waraq.text_state import resolve_segment_text_state


async def _select_rule_binding_pos_for_project(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> list[ProvenanceObject]:
    """RULE_BINDING-POs scoped to Segments belonging to the project.

    Segment has no direct `project_uuid` column; the project linkage is
    Segment → Block → Page → Project. We join through to filter at SQL
    level rather than pulling cross-project rows into Python.
    """
    from waraq.schemas import Block, Page

    stmt = (
        select(ProvenanceObject)
        .join(Segment, Segment.satz_uuid == ProvenanceObject.scope_uuid)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(ProvenanceObject.po_type == POType.RULE_BINDING.value)
        .where(Page.project_uuid == project_uuid)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def _select_segments_for_project(
    *, session: AsyncSession, project_uuid: _uuid.UUID
) -> list[Segment]:
    from waraq.schemas import Block, Page

    result = await session.execute(
        select(Segment)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Page.project_uuid == project_uuid)
    )
    return list(result.scalars())


def _group_pos_by_key(
    pos: list[ProvenanceObject], payload_key: str
) -> dict[str, list[ProvenanceObject]]:
    groups: dict[str, list[ProvenanceObject]] = {}
    for po in pos:
        payload = po.payload or {}
        key_value = payload.get(payload_key)
        if not key_value:
            continue
        groups.setdefault(str(key_value), []).append(po)
    return groups


def _distinct_renderings(pos: list[ProvenanceObject]) -> set[str]:
    """The set of distinct `applied_rendering` values across the POs in
    a group. POs without `applied_rendering` are ignored — they predate
    the v1.0 binding extension and contribute neutrally.
    """
    out: set[str] = set()
    for po in pos:
        payload = po.payload or {}
        rendering = payload.get("applied_rendering")
        if isinstance(rendering, str) and rendering:
            out.add(rendering)
    return out


def _distinct_segments(pos: list[ProvenanceObject]) -> set[_uuid.UUID]:
    return {po.scope_uuid for po in pos}


# --- A) Concept-/entity-binding rules: K-01, K-03, K-07 ------------------


async def k_01_concept_terminology(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> Iterable[KConsistencyFinding]:
    """K-01 — terminological consistency by concept_id.

    Reads RULE_BINDING-POs in the project, groups by `concept_id` from
    payload. A group with >=2 segments and >=2 distinct
    `applied_rendering` values is a finding. **Surface form is never
    consulted for equality** (DBB §B Abkürzung 10).
    """
    pos = await _select_rule_binding_pos_for_project(session=session, project_uuid=project_uuid)
    groups = _group_pos_by_key(pos, "concept_id")

    findings: list[KConsistencyFinding] = []
    for concept_id_str, group in groups.items():
        seg_uuids = _distinct_segments(group)
        if len(seg_uuids) < 2:
            continue
        renderings = _distinct_renderings(group)
        if len(renderings) < 2:
            continue
        findings.append(
            KConsistencyFinding(
                k_rule=KRuleId.K_01,
                subject_key=concept_id_str,
                verstossklasse=Verstossklasse.MITTEL,
                betroffene_segment_uuids=sorted(seg_uuids, key=str),
                vorschlag={
                    "action": "use_canonical_rendering",
                    "candidates": sorted(renderings),
                    "subject_type": SubjectType.CONCEPT_ID.value,
                    "scope": "single_rule",
                },
            )
        )
    return findings


async def k_03_entity_consistency(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> Iterable[KConsistencyFinding]:
    """K-03 — entity consistency by entity_id.

    Same shape as K-01 but groups by `entity_id` from RULE_BINDING-PO
    payload. The Identitätstyp record (entities table) is the basis;
    string equality of `surface_form` is NOT consulted.
    """
    pos = await _select_rule_binding_pos_for_project(session=session, project_uuid=project_uuid)
    groups = _group_pos_by_key(pos, "entity_id")

    findings: list[KConsistencyFinding] = []
    for entity_id_str, group in groups.items():
        seg_uuids = _distinct_segments(group)
        if len(seg_uuids) < 2:
            continue
        renderings = _distinct_renderings(group)
        if len(renderings) < 2:
            continue
        findings.append(
            KConsistencyFinding(
                k_rule=KRuleId.K_03,
                subject_key=entity_id_str,
                verstossklasse=Verstossklasse.MITTEL,
                betroffene_segment_uuids=sorted(seg_uuids, key=str),
                vorschlag={
                    "action": "use_canonical_entity_rendering",
                    "candidates": sorted(renderings),
                    "subject_type": SubjectType.ENTITY_ID.value,
                },
            )
        )
    return findings


async def k_07_concept_cross_rule(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> Iterable[KConsistencyFinding]:
    """K-07 — cross-rule terminological consistency by concept_id.

    K-07 binds to the same Identitätstyp as K-01 (concept_id) but at
    cross-rule scope: the inconsistency must span at least two distinct
    rule applications. v1.0 reads `application_context.rule` from
    RULE_BINDING-PO payloads and emits findings only when the divergent
    renderings come from POs with at least two distinct rule labels.

    A K-07 finding is therefore a strict subset of what K-01 might emit
    — it specifically calls out cross-rule terminology drift.
    """
    pos = await _select_rule_binding_pos_for_project(session=session, project_uuid=project_uuid)
    groups = _group_pos_by_key(pos, "concept_id")

    findings: list[KConsistencyFinding] = []
    for concept_id_str, group in groups.items():
        seg_uuids = _distinct_segments(group)
        if len(seg_uuids) < 2:
            continue
        renderings = _distinct_renderings(group)
        if len(renderings) < 2:
            continue
        rule_labels: set[str] = set()
        for po in group:
            payload = po.payload or {}
            ctx = payload.get("application_context") or {}
            rule_label = ctx.get("rule") if isinstance(ctx, dict) else None
            if isinstance(rule_label, str) and rule_label:
                rule_labels.add(rule_label)
        if len(rule_labels) < 2:
            continue
        findings.append(
            KConsistencyFinding(
                k_rule=KRuleId.K_07,
                subject_key=concept_id_str,
                verstossklasse=Verstossklasse.MITTEL,
                betroffene_segment_uuids=sorted(seg_uuids, key=str),
                vorschlag={
                    "action": "harmonize_across_rules",
                    "candidates": sorted(renderings),
                    "rule_labels": sorted(rule_labels),
                    "subject_type": SubjectType.CONCEPT_ID.value,
                    "scope": "cross_rule",
                },
            )
        )
    return findings


# --- B) Identitätstyp-table rules: K-02, K-04, K-05, K-06 ----------------


_IdentityTable = (
    type[FormelVerzeichnisEintrag]
    | type[TransliterationsMusterEintrag]
    | type[QuellenIdentitaet]
    | type[StrukturellerSchluessel]
)


async def _scan_identity_table(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    rule_id: KRuleId,
    subject_type: SubjectType,
    identity_table: _IdentityTable,
) -> list[KConsistencyFinding]:
    """Shared scan loop for the four Identitätstyp-table rules.

    Each rule reads ONLY its own Identitätstyp records and the Segments'
    text — the structural Trennung HG-S4-1 demands. The function below
    is dispatched per rule; the per-rule public function passes its own
    table class so each public callable visibly binds to its
    Identitätstyp at the call site.
    """
    rows_result = await session.execute(
        select(identity_table)
        .where(identity_table.project_uuid == project_uuid)
        .where(identity_table.active.is_(True))
    )
    identity_rows: list[Any] = list(rows_result.scalars())
    if not identity_rows:
        return []

    segments = await _select_segments_for_project(session=session, project_uuid=project_uuid)

    findings: list[KConsistencyFinding] = []
    for ident in identity_rows:
        affected: list[_uuid.UUID] = []
        target_renderings: set[str] = set()
        any_match = False
        any_divergence = False
        for seg in segments:
            text_state = await resolve_segment_text_state(session=session, segment=seg)
            src, tgt = text_state.source_text, text_state.target_text
            if ident.source_pattern not in src:
                continue
            any_match = True
            affected.append(seg.satz_uuid)
            if ident.expected_rendering in tgt:
                target_renderings.add(ident.expected_rendering)
            else:
                any_divergence = True
                # Capture a short signature of what was used instead so
                # the resolver UI can display "saw X, expected Y".
                target_renderings.add(tgt.strip()[:80])
        if not any_match:
            continue
        if not any_divergence:
            continue
        if len(affected) < 2 and len(target_renderings) < 2:
            continue
        findings.append(
            KConsistencyFinding(
                k_rule=rule_id,
                subject_key=ident.identity_key,
                verstossklasse=Verstossklasse.MITTEL,
                betroffene_segment_uuids=sorted(affected, key=str),
                vorschlag={
                    "action": "use_expected_rendering",
                    "expected_rendering": ident.expected_rendering,
                    "observed_renderings": sorted(target_renderings),
                    "subject_type": subject_type.value,
                },
            )
        )
    return findings


async def k_02_formel_verzeichnis(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> Iterable[KConsistencyFinding]:
    """K-02 — formula and index consistency by formel_verzeichnis_id.

    Reads `formel_verzeichnis_eintraege`. Never delegates to concept_id.
    """
    return await _scan_identity_table(
        session=session,
        project_uuid=project_uuid,
        rule_id=KRuleId.K_02,
        subject_type=SubjectType.FORMEL_VERZEICHNIS_ID,
        identity_table=FormelVerzeichnisEintrag,
    )


async def k_04_transliterations_muster(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> Iterable[KConsistencyFinding]:
    """K-04 — transliteration consistency by transliterations_muster.

    Reads `transliterations_muster_eintraege`. Never delegates to
    concept_id.
    """
    return await _scan_identity_table(
        session=session,
        project_uuid=project_uuid,
        rule_id=KRuleId.K_04,
        subject_type=SubjectType.TRANSLITERATIONS_MUSTER,
        identity_table=TransliterationsMusterEintrag,
    )


async def k_05_source_identity(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> Iterable[KConsistencyFinding]:
    """K-05 — source-citation consistency by source_identity.

    Reads `quellen_identitaeten`. Never delegates to concept_id.
    """
    return await _scan_identity_table(
        session=session,
        project_uuid=project_uuid,
        rule_id=KRuleId.K_05,
        subject_type=SubjectType.SOURCE_IDENTITY,
        identity_table=QuellenIdentitaet,
    )


async def k_06_structural_key(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
) -> Iterable[KConsistencyFinding]:
    """K-06 — structural pattern consistency by structural_key.

    Reads `strukturelle_schluessel`. Never delegates to concept_id.
    """
    return await _scan_identity_table(
        session=session,
        project_uuid=project_uuid,
        rule_id=KRuleId.K_06,
        subject_type=SubjectType.STRUCTURAL_KEY,
        identity_table=StrukturellerSchluessel,
    )


# --- registration --------------------------------------------------------


def register_real_k_rules() -> None:
    """Replace stub bodies with real implementations.

    Idempotent — re-calling overwrites with the same real body. Call
    once at startup BEFORE `run_consistency_check` is invoked. The
    registry-level `K_RULE_SUBJECT_TYPE` mapping is unchanged: each
    real body still binds to its passende Identitätstyp.
    """
    register_k_rule(KRuleId.K_01, k_01_concept_terminology)
    register_k_rule(KRuleId.K_02, k_02_formel_verzeichnis)
    register_k_rule(KRuleId.K_03, k_03_entity_consistency)
    register_k_rule(KRuleId.K_04, k_04_transliterations_muster)
    register_k_rule(KRuleId.K_05, k_05_source_identity)
    register_k_rule(KRuleId.K_06, k_06_structural_key)
    register_k_rule(KRuleId.K_07, k_07_concept_cross_rule)


# Silence unused-import warnings for the symbols re-exported through __init__.
_: Any = (Concept, Entity, JSONB)


__all__ = [
    "k_01_concept_terminology",
    "k_02_formel_verzeichnis",
    "k_03_entity_consistency",
    "k_04_transliterations_muster",
    "k_05_source_identity",
    "k_06_structural_key",
    "k_07_concept_cross_rule",
    "register_real_k_rules",
]
