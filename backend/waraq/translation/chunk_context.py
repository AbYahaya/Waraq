"""§3.6 chunk-context resolver — glossary + entity hits per chunk.

Per Dokument 1 §3.6 ("Chunk and context rules"):

> "Each chunk contains: style core, glossary entries, entity database,
>  semantic summary."

The translation engine wraps this with `TranslationContext.upstream_window`
(semantic summary) and `style_anchors` (style core, post-stilfeature).
This module supplies the *glossary entries + entity database* slice.

Strategy: pre-fetch the project's + account's glossary (Concept rows)
and entity rows once per Job, cache in a `ChunkContextResolver`. For
each chunk, scan the source text for substring hits against canonical
labels, return the matched entries as a `ChunkBrief`.

Substring matching is the v1.0 simplification per Baseline Delivery
Plan §4 (calibration). Morphological-aware matching (CAMeL Tools) is a
Phase 4 follow-on; today's substring matcher is correct for fully-
vocalized canonical entries that appear verbatim in source (the common
case for glossary maintenance).

Read-only: no writes, no Decision Events. The resolver is invoked by
the translation `_execute` loop, never by HTTP directly.
"""

from __future__ import annotations

import re
import uuid as _uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.arabic import to_skeleton
from waraq.schemas import Concept, Entity

# §4.17 "no glossary hit" heuristic — module-level constants so they
# can be tuned in one place during Phase-7 calibration.
#
# Detection rule: an Arabic-word substring is an `UntrackedTermCandidate`
# when ALL of the following hold:
#   - It is purely Arabic-script (U+0600..U+06FF).
#   - Its skeleton (NFC + Tatweel + diacritic-strip + alif-collapse)
#     is at least `_UNTRACKED_TERM_MIN_SKELETON_LEN` characters.
#   - Its skeleton does NOT match the skeleton of any glossary or
#     entity canonical_label (otherwise the existing GlossaryHit /
#     EntityHit path already covers it).
#   - It is not in the small `_UNTRACKED_TERM_STOPWORDS` filter — a
#     tight allow-list of high-frequency function words whose
#     "looks technical" signal is misleading.
#
# We deliberately do NOT bound the candidate count here — the chunk
# brief surfaces every candidate. Per-call truncation lives at the
# prompt-construction site so the budget can vary by engine.
_ARABIC_WORD_RE_CTX = re.compile(r"[؀-ۿ]+")
_UNTRACKED_TERM_MIN_SKELETON_LEN: int = 4
_UNTRACKED_TERM_STOPWORDS: frozenset[str] = frozenset(
    {
        # Articles / particles the heuristic must not surface.
        "الذي",
        "التي",
        "الذين",
        "هذا",
        "هذه",
        "ذلك",
        "تلك",
        "هؤلاء",
        # Common verbs / prepositions / conjunctions.
        "كان",
        "كانت",
        "قال",
        "قالت",
        "قالوا",
        "أن",
        "إن",
        "أنت",
        "أنا",
        "نحن",
        "هم",
        "هي",
        "هو",
        "على",
        "إلى",
        "عن",
        "من",
        "في",
        "ما",
        "لا",
        "ثم",
        "بل",
        "لكن",
        "ولكن",
    }
)


@dataclass(frozen=True, kw_only=True, slots=True)
class GlossaryHit:
    """One glossary surface form found in a chunk's source text.

    `surface_form` is the Arabic substring that matched (from the
    Concept canonical_label). `gloss` is the canonical translation /
    rendering recorded on the Concept row. The translator MUST use
    `gloss` for `surface_form` per §4.12.1 Tier 1 (glossary precedence).

    `is_first_occurrence` carries the §4.17 technical-term first-vs-
    subsequent flag: `True` if this concept has not appeared in any
    prior TRANSLATION-PO for the project (and not in any earlier chunk
    of the current job). When `True`, the translator should emit the
    full first-occurrence form (gloss + parenthetical Arabic + footnote);
    when `False`, the gloss alone (subsequent uses).
    """

    concept_id: _uuid.UUID
    surface_form: str
    gloss: str
    binding_level: str  # "project" or "account"
    is_first_occurrence: bool = False


@dataclass(frozen=True, kw_only=True, slots=True)
class EntityHit:
    """One named entity surface form found in a chunk's source text."""

    entity_id: _uuid.UUID
    category: str  # one of the §4.19 5-value taxonomy
    surface_form: str
    canonical_label: str
    short_bio: str | None
    binding_level: str


@dataclass(frozen=True, kw_only=True, slots=True)
class UntrackedTermCandidate:
    """A source-text token flagged by the §4.17 "no glossary hit"
    heuristic — a word that LOOKS like it could be a technical term
    but is NOT present in the project's / account's glossary.

    The translator prompt forwards these to the LLM with the directive
    "if you treat any of these as a technical term, render with the
    §4.17 AI-footnote pattern (`gloss (Arabic) [Anm.: …; Source: AI]`)".

    The detection itself never flags terms as definitely-technical —
    that judgement stays with the LLM (canon-defensible: §2.2 "no
    silent winners", §4.17 "AI-generated footnote with [Source: AI]
    marker"). The heuristic just surfaces likely candidates so the
    LLM doesn't miss them.

    Attributes:
        surface_form: The Arabic substring as it appears in the
            source. Diacritics preserved.
        skeleton: Diacritic-stripped, Tatweel-stripped form (the
            uniqueness key).
    """

    surface_form: str
    skeleton: str


@dataclass(frozen=True, kw_only=True, slots=True)
class ChunkBrief:
    """The §3.6 per-chunk brief: glossary + entity hits relevant to a
    specific source-text chunk. Empty when the project has no glossary
    / entity entries or the chunk contains no matches.

    Carried as a transient field on `TranslationContext`; never
    serialized through job checkpoints (recomputed per chunk).
    """

    glossary_hits: list[GlossaryHit] = field(default_factory=list)
    entity_hits: list[EntityHit] = field(default_factory=list)
    untracked_term_candidates: list[UntrackedTermCandidate] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return (
            not self.glossary_hits and not self.entity_hits and not self.untracked_term_candidates
        )


class ChunkContextResolver:
    """Pre-loads project + account glossary and entity rows once, then
    resolves per-chunk briefs by substring matching against the source
    text.

    Lifetime: one resolver per translation Job execution. The job loop
    builds it once (after the first chunk lookup), reuses for every
    subsequent chunk.
    """

    def __init__(
        self,
        *,
        glossary: list[Concept],
        entities: list[Entity],
        previously_used_concept_ids: set[_uuid.UUID] | None = None,
    ) -> None:
        # Sort by canonical_label length descending so longer matches win
        # if shorter labels are substrings of longer ones (e.g., "إجماع"
        # vs "إجماع الأمة").
        self._glossary = sorted(glossary, key=lambda c: len(c.canonical_label), reverse=True)
        self._entities = sorted(entities, key=lambda e: len(e.canonical_label), reverse=True)
        # §4.17 first-occurrence tracking. Two sources of "already-used"
        # concept_ids:
        # 1. `previously_used` — concepts that appeared in *prior*
        #    TRANSLATION-PO rows for this project (loaded from DB at
        #    `for_project` build time). Survives Job restarts.
        # 2. `_seen_this_run` — concepts that have appeared in earlier
        #    chunks of the *current* run; mutates on every `resolve()`.
        # A hit is `is_first_occurrence=True` only when its concept_id
        # is in NEITHER set at the moment of resolution.
        self._previously_used: set[_uuid.UUID] = previously_used_concept_ids or set()
        self._seen_this_run: set[_uuid.UUID] = set()

    @classmethod
    async def for_project(
        cls,
        session: AsyncSession,
        *,
        project_uuid: _uuid.UUID,
        account_uuid: _uuid.UUID,
    ) -> ChunkContextResolver:
        """Build a resolver from the project's + account's active glossary
        and entity rows. Both project-scoped and account-scoped entries
        are pulled per §4.12.1 / §4.19 binding semantics.

        Also queries any prior TRANSLATION-PO rows for segments under
        this project to seed §4.17 first-occurrence tracking — concepts
        already used in earlier runs are correctly marked as
        non-first-occurrence on a re-translation.
        """
        glossary = list(
            (
                await session.execute(
                    select(Concept)
                    .where(Concept.active.is_(True))
                    .where(
                        (Concept.project_uuid == project_uuid)
                        | (Concept.account_uuid == account_uuid)
                    )
                )
            ).scalars()
        )
        entities = list(
            (
                await session.execute(
                    select(Entity)
                    .where(Entity.active.is_(True))
                    .where(
                        (Entity.project_uuid == project_uuid)
                        | (Entity.account_uuid == account_uuid)
                    )
                )
            ).scalars()
        )
        previously_used = await _query_used_concept_ids(session, project_uuid)
        return cls(
            glossary=glossary,
            entities=entities,
            previously_used_concept_ids=previously_used,
        )

    def _resolve_untracked_term_candidates(
        self,
        source_text: str,
        covered_skeletons: set[str],
    ) -> list[UntrackedTermCandidate]:
        """§4.17 "no glossary hit" detection.

        Scan the source for Arabic words whose skeleton is not already
        covered by a glossary / entity hit — those are the candidates
        the LLM may treat as technical terms via the AI-footnote
        pattern. Returns each unique surface form once (first
        occurrence wins). Order is source-position to preserve a
        deterministic prompt ordering."""
        seen_skeletons: set[str] = set(covered_skeletons)
        out: list[UntrackedTermCandidate] = []
        for match in _ARABIC_WORD_RE_CTX.finditer(source_text):
            word = match.group(0)
            if word in _UNTRACKED_TERM_STOPWORDS:
                continue
            skel = to_skeleton(word)
            if len(skel) < _UNTRACKED_TERM_MIN_SKELETON_LEN:
                continue
            if skel in seen_skeletons:
                continue
            seen_skeletons.add(skel)
            out.append(UntrackedTermCandidate(surface_form=word, skeleton=skel))
        return out

    def resolve(self, source_text: str) -> ChunkBrief:
        """Scan `source_text` for substring matches against every loaded
        glossary + entity canonical_label. Returns a brief with the
        matched entries; mutates internal state to track §4.17
        first-occurrence flags across the run.

        A label only matches if its canonical_label is a substring of
        `source_text` (verbatim). If the glossary entry has no `gloss`
        (translation), the hit is skipped — there is no rendering to
        enforce.
        """
        if not source_text:
            return ChunkBrief()

        glossary_hits: list[GlossaryHit] = []
        seen_concepts: set[_uuid.UUID] = set()
        for concept in self._glossary:
            if not concept.gloss:
                continue
            if concept.concept_id in seen_concepts:
                continue
            if concept.canonical_label and concept.canonical_label in source_text:
                is_first = (
                    concept.concept_id not in self._previously_used
                    and concept.concept_id not in self._seen_this_run
                )
                glossary_hits.append(
                    GlossaryHit(
                        concept_id=concept.concept_id,
                        surface_form=concept.canonical_label,
                        gloss=concept.gloss,
                        binding_level=concept.binding_level,
                        is_first_occurrence=is_first,
                    )
                )
                seen_concepts.add(concept.concept_id)
                self._seen_this_run.add(concept.concept_id)

        entity_hits: list[EntityHit] = []
        seen_entities: set[_uuid.UUID] = set()
        for entity in self._entities:
            if entity.entity_id in seen_entities:
                continue
            if entity.canonical_label and entity.canonical_label in source_text:
                entity_hits.append(
                    EntityHit(
                        entity_id=entity.entity_id,
                        category=entity.category,
                        surface_form=entity.canonical_label,
                        canonical_label=entity.canonical_label,
                        short_bio=entity.short_bio,
                        binding_level=entity.binding_level,
                    )
                )
                seen_entities.add(entity.entity_id)

        # §4.17 "no glossary hit" — flag any source word whose skeleton
        # isn't already covered by the glossary / entity matches above
        # so the translator prompt can route it through the AI-footnote
        # pattern. The set of "covered" skeletons is the join of all
        # glossary + entity surface skeletons.
        covered_skeletons: set[str] = set()
        for h in glossary_hits:
            sk = to_skeleton(h.surface_form)
            if sk:
                covered_skeletons.add(sk)
        for eh in entity_hits:
            sk = to_skeleton(eh.surface_form)
            if sk:
                covered_skeletons.add(sk)
        untracked = self._resolve_untracked_term_candidates(source_text, covered_skeletons)

        return ChunkBrief(
            glossary_hits=glossary_hits,
            entity_hits=entity_hits,
            untracked_term_candidates=untracked,
        )


async def _query_used_concept_ids(
    session: AsyncSession, project_uuid: _uuid.UUID
) -> set[_uuid.UUID]:
    """Return the set of `concept_id`s that appeared in any prior
    TRANSLATION-PO `payload.concept_ids_used` for segments under
    `project_uuid`. Used by `ChunkContextResolver.for_project` to seed
    §4.17 first-occurrence tracking across re-runs.

    Defensive parsing — any payload entries that aren't valid UUID
    strings are silently dropped (defense against schema drift; we
    treat the absence as "haven't used" which is the safer default for
    first-occurrence rendering).
    """
    from waraq.schemas import Block, Page, ProvenanceObject, Segment
    from waraq.schemas.enums import POType

    result = await session.execute(
        select(ProvenanceObject.payload)
        .join(Segment, Segment.satz_uuid == ProvenanceObject.scope_uuid)
        .join(Block, Block.block_uuid == Segment.block_uuid)
        .join(Page, Page.page_uuid == Block.page_uuid)
        .where(Page.project_uuid == project_uuid)
        .where(ProvenanceObject.po_type == POType.TRANSLATION.value)
    )
    used: set[_uuid.UUID] = set()
    for (payload,) in result:
        if not payload:
            continue
        for raw in payload.get("concept_ids_used", []):
            if not isinstance(raw, str):
                continue
            try:
                used.add(_uuid.UUID(raw))
            except ValueError:
                continue
    return used


__all__ = [
    "ChunkBrief",
    "ChunkContextResolver",
    "EntityHit",
    "GlossaryHit",
    "UntrackedTermCandidate",
]
