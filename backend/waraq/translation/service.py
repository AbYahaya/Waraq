"""T-7.1.1 — Translation job machinery.

Per Sprint 2 §2:

- Job type `translation`. Job state machine consumes Sprint 0 T-2.1.1
  transitions: pending → running → paused | completed | failed.
- Checkpoint after every chunk. `resume_state` (the checkpoint payload)
  carries: chunk_index, current Segment satz_uuid, full upstream context
  buffer (rolling translated-segment window + accumulated terminology
  bindings + accumulated style anchors). Serialization is deterministic
  and round-trips through deserialization without information loss
  (T-REC-03).
- Before every Segment write, `lock_flag` is read **live** (not from a
  job-start batch fetch). Segments with `lock_flag ∈ {manual_local,
  manual_editorial}` are skipped — translation never overwrites locked
  Segments. This is how T-H1-01 / T-H1-02 are upheld at the translation
  layer. R-S2-04 is the named structural failure mode here.
- Skipped Segments are recorded in chunk metadata and surfaced in the
  job summary (`Translation-Job-Skipped-Segments-Reported-Test`).
- Resumption picks up at the last persisted checkpoint with the context
  buffer fully reconstructed.

DBB §B Abkürzung 5: there is **no auto-trigger** between the release gate
and translation start. `start_translation_job` requires that an
`uebersetzungsstart` Decision Event has already been written by the user
via `release_gate.start_translation` — otherwise it raises. The two
modules are coupled only through the Decision Event.

T-7.1.1 vs T-7.1.2 layering:
- This module produces translated chunks IN MEMORY plus checkpoints. It
  does NOT write Revision rows or TRANSLATION-PO rows. T-7.1.2 wires
  those persistence paths on top by accepting an `on_segment_translated`
  hook. With no hook, the job is a dry-run that just verifies the
  pipeline mechanics; with the hook installed by T-7.1.2 / T-7.2.1, it
  produces the full canonical artifact set per Segment.

Atomicity: caller owns the transaction. Each iteration's checkpoint is
flushed; commit/rollback is the caller's responsibility. Restart-survival
requires the caller to commit promptly after each chunk.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity.service import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.jobs import (
    complete_job,
    fail_job,
    read_latest_checkpoint,
    start_job,
    write_checkpoint,
)
from waraq.schemas import DecisionEvent, Job, Segment
from waraq.schemas.enums import JobState, ScopeType
from waraq.text_state import resolve_segment_source_text
from waraq.translation.chunk_context import ChunkContextResolver
from waraq.translation.exceptions import (
    TranslationJobCancelled,
    TranslationJobNotPending,
    TranslationJobUebersetzungsstartMissing,
)
from waraq.translation.line_protocol import is_pagination_or_marker_text
from waraq.translation.protected_passages import resolve_protected_translation

JOB_TYPE = "translation"


@dataclass(frozen=True, kw_only=True, slots=True)
class TranslationContext:
    """Upstream context buffer carried across chunks (and through resumption).

    Per Sprint 2 §2: serialization is deterministic and round-trips through
    deserialization without information loss. The persisted fields are all
    JSON-serializable primitives.

    Attributes:
        upstream_window: Rolling list of recently translated Segment outputs
            that condition the next translation. Bounded length is the
            caller's responsibility — typically the translator function
            keeps the last N entries.
        terminology_bindings: concept_id (str) → chosen rendering. Built up
            as translations resolve glossary entries (T-7.2.1 wires this).
        style_anchors: free list of style-anchor strings accumulated from
            confirmed user edits (placeholder for T-7.3.x style integration).
        chunk_brief: §3.6 per-chunk glossary + entity hits. Recomputed
            before each translator call from the project's glossary +
            entity tables; **transient** — excluded from
            `to_dict`/`from_dict` so checkpoints stay small and the brief
            re-resolves on resume against current registry state.
        protected_reference: transient protected-passage metadata
            (verified hadith stack / Qur'an reference source lines)
            carried only for the current chunk so the persistence hook
            can attach it to the translation provenance payload.
    """

    upstream_window: list[str] = field(default_factory=list)
    terminology_bindings: dict[str, str] = field(default_factory=dict)
    style_anchors: list[str] = field(default_factory=list)
    # Transient — see docstring. Default-None type-hinted as Any to avoid
    # a forward import cycle (chunk_context imports translation schemas).
    chunk_brief: Any = None
    # Transient page-level context so translators can see the full OCR
    # flow of the current page rather than only the isolated segment.
    page_context: Any = None
    # Transient §3.6 cross-check outcome. Set by the cross-check
    # orchestrator before the persistence hook reads it; never
    # checkpointed. The cross-check translator uses
    # `object.__setattr__` to write it on the same context object the
    # `_execute` loop holds (frozen-dataclass-bypass — deliberate, since
    # the alternative refactor would change the public Translator
    # signature).
    cross_check: Any = None
    # Transient protected reference metadata for the current chunk.
    protected_reference: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Deterministic JSON-serializable representation. Excludes
        transient fields (chunk_brief)."""
        return {
            "upstream_window": list(self.upstream_window),
            "terminology_bindings": dict(self.terminology_bindings),
            "style_anchors": list(self.style_anchors),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> TranslationContext:
        return cls(
            upstream_window=list(raw.get("upstream_window", [])),
            terminology_bindings=dict(raw.get("terminology_bindings", {})),
            style_anchors=list(raw.get("style_anchors", [])),
        )

    def with_translated(self, translated: str, *, window_size: int = 8) -> TranslationContext:
        """Return a new context with `translated` appended to the window.

        `window_size` is the cap on `upstream_window` length — older
        entries are dropped from the front. The default of 8 is a starting
        point, NOT canonical (Sprint 2 §B "Calibration values: ... all
        configurable, never pre-set"). Callers can override per call.
        """
        new_window = [*self.upstream_window, translated]
        if len(new_window) > window_size:
            new_window = new_window[-window_size:]
        return TranslationContext(
            upstream_window=new_window,
            terminology_bindings=dict(self.terminology_bindings),
            style_anchors=list(self.style_anchors),
            # Don't carry chunk_brief forward — it's per-chunk.
        )

    def with_chunk_brief(self, brief: Any) -> TranslationContext:
        """Return a new context with the given per-chunk brief attached.
        Used by `_execute` before each translator call. The brief is
        transient (not checkpointed)."""
        return TranslationContext(
            upstream_window=list(self.upstream_window),
            terminology_bindings=dict(self.terminology_bindings),
            style_anchors=list(self.style_anchors),
            chunk_brief=brief,
            page_context=self.page_context,
            cross_check=self.cross_check,
            protected_reference=self.protected_reference,
        )

    def with_page_context(self, page_context: Any) -> TranslationContext:
        """Return a new context with page-level OCR context attached.

        The page context is transient and is intentionally excluded from
        checkpoint serialization; it is recomputed on each chunk from the
        current page state so OCR/source edits are seen immediately.
        """
        return TranslationContext(
            upstream_window=list(self.upstream_window),
            terminology_bindings=dict(self.terminology_bindings),
            style_anchors=list(self.style_anchors),
            chunk_brief=self.chunk_brief,
            page_context=page_context,
            cross_check=self.cross_check,
            protected_reference=self.protected_reference,
        )

    def with_protected_reference(self, protected_reference: Any) -> TranslationContext:
        """Return a new context with protected-passage metadata attached.

        This remains transient so checkpoints stay slim; the data is
        recomputed when the chunk is resumed and is only meant for the
        downstream translation provenance payload.
        """
        return TranslationContext(
            upstream_window=list(self.upstream_window),
            terminology_bindings=dict(self.terminology_bindings),
            style_anchors=list(self.style_anchors),
            chunk_brief=self.chunk_brief,
            page_context=self.page_context,
            cross_check=self.cross_check,
            protected_reference=protected_reference,
        )


@dataclass(frozen=True, kw_only=True, slots=True)
class TranslatedChunk:
    """In-memory result of one Segment iteration.

    Skipped chunks have `output_text=None` and a non-empty `skip_reason`."""

    satz_uuid: _uuid.UUID
    input_text: str
    output_text: str | None
    skipped: bool
    skip_reason: str | None = None


@dataclass(frozen=True, kw_only=True, slots=True)
class SkippedSegment:
    """Audit-shape record of one skipped Segment, as surfaced in the job
    summary at completion (`Translation-Job-Skipped-Segments-Reported-Test`)."""

    satz_uuid: _uuid.UUID
    reason: str


@dataclass(frozen=True, kw_only=True, slots=True)
class TranslationJobResult:
    """Return value from `run_translation_job` / `resume_translation_job`."""

    job: Job
    chunks: list[TranslatedChunk] = field(default_factory=list)
    skipped: list[SkippedSegment] = field(default_factory=list)
    final_context: TranslationContext = field(default_factory=TranslationContext)


# A translator is an async callable taking (input_text, context) and
# returning the translated string. Engine identity is the caller's choice;
# this module does not assume a particular LLM.
Translator = Callable[[str, TranslationContext], Awaitable[str]]

# Optional per-segment hook. T-7.1.2 / T-7.2.1 use this to wire Revision +
# TRANSLATION-PO + RULE_BINDING-PO writes WITHOUT this module having to
# know about provenance schemas. The hook receives the live ORM Segment
# (already lock-checked, NOT locked) and the translator output. It runs
# inside the same transaction as the checkpoint, before the checkpoint
# is written, so any provenance write that succeeds is guaranteed to be
# checkpointed alongside the job state.
SegmentTranslatedHook = Callable[[AsyncSession, Segment, str, TranslationContext], Awaitable[None]]

# Optional hook fired when a segment is skipped due to lock_flag. T-7.2.1
# uses this to drive `detect_conflict` for any glossary surface forms that
# would have applied to the locked Segment — keeping the canonical
# "glossary vs lock → conflict_instance" route intact (DBB §B Abkürzung 6).
LockedSegmentSkipHook = Callable[[AsyncSession, Segment, TranslationContext], Awaitable[None]]


# --- internal helpers -----------------------------------------------------


async def _has_uebersetzungsstart_de(session: AsyncSession, *, project_uuid: _uuid.UUID) -> bool:
    """DBB §B Abkürzung 5 enforcement: translation can only start when the
    user has explicitly written an `uebersetzungsstart` Decision Event."""
    from sqlalchemy import func as _func

    result = await session.execute(
        select(_func.count())
        .select_from(DecisionEvent)
        .where(DecisionEvent.scope_type == ScopeType.PROJECT.value)
        .where(DecisionEvent.scope_uuid == project_uuid)
        .where(DecisionEvent.decision_type == "uebersetzungsstart")
    )
    return result.scalar_one() > 0


async def _live_get_segment(session: AsyncSession, *, satz_uuid: _uuid.UUID) -> Segment | None:
    """Re-fetch the Segment row by UUID. This is the LIVE-READ path that
    R-S2-04 protects: every Segment iteration reads `lock_flag` fresh,
    not from a job-start batch fetch."""
    result = await session.execute(select(Segment).where(Segment.satz_uuid == satz_uuid))
    return result.scalar_one_or_none()


async def _resolve_page_source_context(
    session: AsyncSession,
    *,
    segment: Segment,
) -> dict[str, Any] | None:
    """Build a transient page-level OCR context for the segment's page.

    This gives the translator the full OCR flow of the page, preserving
    surrounding context even though persistence and review still happen
    at the segment level.
    """
    from waraq.schemas import Block, Page

    row = (
        await session.execute(
            select(Block.page_uuid, Block.block_type, Segment.satz_index)
            .select_from(Segment)
            .join(Block, Block.block_uuid == Segment.block_uuid)
            .where(Segment.satz_uuid == segment.satz_uuid)
        )
    ).first()
    if row is None:
        return None

    page_uuid, block_type, satz_index = row
    page_rows = (
        await session.execute(
            select(Segment, Block.block_type, Page.page_index)
            .select_from(Segment)
            .join(Block, Block.block_uuid == Segment.block_uuid)
            .join(Page, Page.page_uuid == Block.page_uuid)
            .where(Page.page_uuid == page_uuid)
            .where(Segment.active.is_(True))
            .order_by(Block.block_index.asc(), Segment.satz_index.asc())
        )
    ).all()

    ordered_source_lines: list[str] = []
    current_index = 0
    for idx, (page_segment, _block_type, _page_index) in enumerate(page_rows):
        source_text = await resolve_segment_source_text(session=session, segment=page_segment)
        ordered_source_lines.append(source_text)
        if page_segment.satz_uuid == segment.satz_uuid:
            current_index = idx

    return {
        "page_uuid": str(page_uuid),
        "page_index": page_rows[0][2] if page_rows else None,
        "full_source_text": "\n".join(line for line in ordered_source_lines if line.strip()),
        "current_segment_index": current_index,
        "current_block_type": block_type,
        "current_satz_index": satz_index,
    }


# --- public API -----------------------------------------------------------


async def start_translation_job(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    segment_uuids: list[_uuid.UUID],
    initial_context: TranslationContext | None = None,
) -> Job:
    """Create a PENDING translation Job for `project_uuid` covering the
    ordered list of Segment UUIDs.

    Refuses creation if no `uebersetzungsstart` Decision Event exists for
    this project (DBB §B Abkürzung 5). The release-gate `start_translation`
    writes that DE; without it, this function raises
    `TranslationJobUebersetzungsstartMissing` and writes nothing.
    """
    if not await _has_uebersetzungsstart_de(session, project_uuid=project_uuid):
        raise TranslationJobUebersetzungsstartMissing(
            f"no uebersetzungsstart Decision Event found for project "
            f"{project_uuid}; user must call release_gate.start_translation "
            "before a translation job can be created."
        )

    ctx = initial_context if initial_context is not None else TranslationContext()
    job = Job(
        job_uuid=new_uuid(),
        job_type=JOB_TYPE,
        state=JobState.PENDING.value,
        project_uuid=project_uuid,
        payload={
            "segment_uuids": [str(u) for u in segment_uuids],
            "initial_context": ctx.to_dict(),
        },
    )
    session.add(job)
    await session.flush()
    return job


async def run_translation_job(
    *,
    session: AsyncSession,
    job: Job,
    translator: Translator,
    on_segment_translated: SegmentTranslatedHook | None = None,
    on_locked_segment_skip: LockedSegmentSkipHook | None = None,
    commit_per_chunk: bool = False,
) -> TranslationJobResult:
    """Execute a fresh translation Job from chunk_index 0.

    `commit_per_chunk=True` makes the loop commit after every iteration
    so progress is visible to other DB sessions in real time (the
    BackgroundTasks `/run` path uses this so the GET endpoint can poll
    `chunks_translated`). The default of False preserves the original
    "caller owns the transaction" contract for tests and resume paths.

    Job must be PENDING (`TranslationJobNotPending` otherwise — use
    `resume_translation_job` for paused/interrupted jobs)."""
    if job.state != JobState.PENDING.value:
        raise TranslationJobNotPending(
            f"run_translation_job requires PENDING; got {job.state!r}. "
            "Use resume_translation_job for non-PENDING starts."
        )
    return await _execute(
        session=session,
        job=job,
        translator=translator,
        on_segment_translated=on_segment_translated,
        on_locked_segment_skip=on_locked_segment_skip,
        resume_from_index=0,
        starting_context=None,
        commit_per_chunk=commit_per_chunk,
    )


async def resume_translation_job(
    *,
    session: AsyncSession,
    job: Job,
    translator: Translator,
    on_segment_translated: SegmentTranslatedHook | None = None,
    on_locked_segment_skip: LockedSegmentSkipHook | None = None,
    commit_per_chunk: bool = False,
) -> TranslationJobResult:
    """Continue a translation Job from its latest checkpoint.

    Reads the most recent Checkpoint row for the job; resumes at the
    chunk index it recorded with the context buffer it serialized. If no
    checkpoint exists, behaves like `run_translation_job` from index 0.
    Per T-REC-03: post-resumption translation matches uninterrupted
    translation byte-for-byte assuming a deterministic translator.
    """
    latest = await read_latest_checkpoint(session=session, job=job)
    if latest is None:
        # No prior progress — fresh start.
        return await _execute(
            session=session,
            job=job,
            translator=translator,
            on_segment_translated=on_segment_translated,
            on_locked_segment_skip=on_locked_segment_skip,
            resume_from_index=0,
            starting_context=None,
            commit_per_chunk=commit_per_chunk,
        )
    state = latest.payload
    chunk_index = int(state["chunk_index"])
    context = TranslationContext.from_dict(state["context"])
    return await _execute(
        session=session,
        job=job,
        translator=translator,
        on_segment_translated=on_segment_translated,
        on_locked_segment_skip=on_locked_segment_skip,
        resume_from_index=chunk_index,
        starting_context=context,
        commit_per_chunk=commit_per_chunk,
    )


# --- core execution loop -------------------------------------------------


async def _execute(
    *,
    session: AsyncSession,
    job: Job,
    translator: Translator,
    on_segment_translated: SegmentTranslatedHook | None,
    on_locked_segment_skip: LockedSegmentSkipHook | None = None,
    resume_from_index: int,
    starting_context: TranslationContext | None,
    commit_per_chunk: bool = False,
) -> TranslationJobResult:
    # Transition PENDING → RUNNING (idempotent through resume path; if
    # already RUNNING, no-op).
    if job.state == JobState.PENDING.value:
        await start_job(session=session, job=job)

    payload = job.payload
    segment_uuids = [_uuid.UUID(s) for s in payload["segment_uuids"]]
    # Stamp the total up-front so the GET endpoint can render a
    # meaningful progress bar before the first chunk lands.
    _write_progress(job, total=len(segment_uuids), translated=0, processed=resume_from_index)
    await session.flush()
    if commit_per_chunk:
        await session.commit()

    if starting_context is not None:
        context = starting_context
    else:
        context = TranslationContext.from_dict(payload.get("initial_context", {}))

    # §3.6 chunk-context resolver — pre-load the project's + account's
    # glossary + entities once per job, then resolve per-chunk briefs.
    # Skipped when the job has no project_uuid (defensive — shouldn't
    # happen for translation jobs, but the pattern keeps tests with
    # bare-bones job rows working).
    chunk_resolver: ChunkContextResolver | None = None
    project_uuid = job.project_uuid
    if project_uuid is not None:
        from waraq.schemas import Project

        project: Project | None = await session.get(Project, project_uuid)
        if project is not None:
            chunk_resolver = await ChunkContextResolver.for_project(
                session,
                project_uuid=project.project_uuid,
                account_uuid=project.account_uuid,
            )

    chunks: list[TranslatedChunk] = []
    skipped: list[SkippedSegment] = []

    try:
        for idx, satz_uuid in enumerate(segment_uuids):
            if idx < resume_from_index:
                continue

            # Cooperative cancel check. Re-read the latest committed
            # `payload.cancel_requested` between chunks so a cancel
            # written from the HTTP layer (separate session, separate
            # transaction) is seen here. Coarse-grained: at most one
            # in-flight chunk's worth of latency before we abort.
            if commit_per_chunk:
                await session.refresh(job, ["payload"])
            if job.payload.get("cancel_requested"):
                raise TranslationJobCancelled(f"Job {job.job_uuid} cancelled at chunk {idx}")

            # LIVE-READ — R-S2-04 protection. Each iteration re-fetches
            # the Segment from the DB so a lock applied mid-job is seen.
            segment = await _live_get_segment(session, satz_uuid=satz_uuid)
            if segment is None:
                # Segment was deleted (shouldn't normally happen — H-5
                # forbids deletion, only inactivation). Treat as skipped.
                reason = "segment_not_found"
                chunks.append(
                    TranslatedChunk(
                        satz_uuid=satz_uuid,
                        input_text="",
                        output_text=None,
                        skipped=True,
                        skip_reason=reason,
                    )
                )
                skipped.append(SkippedSegment(satz_uuid=satz_uuid, reason=reason))
                await _persist_chunk_checkpoint(
                    session=session,
                    job=job,
                    chunk_index=idx + 1,
                    context=context,
                    skipped_so_far=skipped,
                )
                _write_progress(
                    job,
                    total=len(segment_uuids),
                    translated=sum(1 for c in chunks if not c.skipped),
                    processed=idx + 1,
                )
                await session.flush()
                if commit_per_chunk:
                    await session.commit()
                continue

            if segment.lock_flag != LockFlag.NONE:
                reason = f"lock_flag={segment.lock_flag.value}"
                # T-7.2.1 hook fires here — for any glossary surface forms
                # that would have applied to the locked Segment, route via
                # detect_conflict (DBB §B Abkürzung 6: glossary never wins
                # silently against a lock).
                if on_locked_segment_skip is not None:
                    await on_locked_segment_skip(session, segment, context)
                chunks.append(
                    TranslatedChunk(
                        satz_uuid=satz_uuid,
                        input_text=await resolve_segment_source_text(
                            session=session,
                            segment=segment,
                        ),
                        output_text=None,
                        skipped=True,
                        skip_reason=reason,
                    )
                )
                skipped.append(SkippedSegment(satz_uuid=satz_uuid, reason=reason))
                await _persist_chunk_checkpoint(
                    session=session,
                    job=job,
                    chunk_index=idx + 1,
                    context=context,
                    skipped_so_far=skipped,
                )
                _write_progress(
                    job,
                    total=len(segment_uuids),
                    translated=sum(1 for c in chunks if not c.skipped),
                    processed=idx + 1,
                )
                await session.flush()
                if commit_per_chunk:
                    await session.commit()
                continue

            input_text = await resolve_segment_source_text(
                session=session,
                segment=segment,
            )
            page_context = await _resolve_page_source_context(session, segment=segment)
            # §3.6 — attach per-chunk glossary + entity brief before
            # calling the translator. Transient on context (not
            # checkpointed); resolved freshly each chunk.
            chunk_context = context.with_page_context(page_context)
            chunk_context = (
                chunk_context.with_chunk_brief(chunk_resolver.resolve(input_text))
                if chunk_resolver is not None
                else chunk_context
            )
            protected = (
                await resolve_protected_translation(
                    session=session,
                    project_uuid=project_uuid,
                    segment=segment,
                    source_text=input_text,
                )
                if project_uuid is not None
                else None
            )
            if protected is not None and protected.reference_payload is not None:
                chunk_context = chunk_context.with_protected_reference(protected.reference_payload)
            if protected is not None and protected.skip_reason is not None:
                reason = protected.skip_reason
                chunks.append(
                    TranslatedChunk(
                        satz_uuid=satz_uuid,
                        input_text=input_text,
                        output_text=None,
                        skipped=True,
                        skip_reason=reason,
                    )
                )
                skipped.append(SkippedSegment(satz_uuid=satz_uuid, reason=reason))
                await _persist_chunk_checkpoint(
                    session=session,
                    job=job,
                    chunk_index=idx + 1,
                    context=context,
                    skipped_so_far=skipped,
                )
                _write_progress(
                    job,
                    total=len(segment_uuids),
                    translated=sum(1 for c in chunks if not c.skipped),
                    processed=idx + 1,
                )
                await session.flush()
                if commit_per_chunk:
                    await session.commit()
                continue
            if protected is not None and protected.output_text is not None:
                output_text = protected.output_text
            elif is_pagination_or_marker_text(input_text):
                output_text = input_text
            else:
                try:
                    output_text = await translator(input_text, chunk_context)
                except Exception as exc:
                    reason = f"translation_failed:{type(exc).__name__}: {exc!s}"[:500]
                    chunks.append(
                        TranslatedChunk(
                            satz_uuid=satz_uuid,
                            input_text=input_text,
                            output_text=None,
                            skipped=True,
                            skip_reason=reason,
                        )
                    )
                    skipped.append(SkippedSegment(satz_uuid=satz_uuid, reason=reason))
                    await _persist_chunk_checkpoint(
                        session=session,
                        job=job,
                        chunk_index=idx + 1,
                        context=context,
                        skipped_so_far=skipped,
                    )
                    _write_progress(
                        job,
                        total=len(segment_uuids),
                        translated=sum(1 for c in chunks if not c.skipped),
                        processed=idx + 1,
                    )
                    await session.flush()
                    if commit_per_chunk:
                        await session.commit()
                    continue

            # T-7.1.2 / T-7.2.1 plug their writers in here. The hook runs
            # in the same transaction as the checkpoint; partial-failure
            # safety is the transaction's job (caller commits per chunk).
            # Pass `chunk_context` (not `context`) so the hook sees both
            # the chunk_brief (§3.6) and any cross_check outcome
            # attached by the cross-check orchestrator.
            if on_segment_translated is not None:
                await on_segment_translated(session, segment, output_text, chunk_context)

            chunks.append(
                TranslatedChunk(
                    satz_uuid=satz_uuid,
                    input_text=input_text,
                    output_text=output_text,
                    skipped=False,
                    skip_reason=None,
                )
            )
            context = context.with_translated(output_text)

            await _persist_chunk_checkpoint(
                session=session,
                job=job,
                chunk_index=idx + 1,
                context=context,
                skipped_so_far=skipped,
            )
            _write_progress(
                job,
                total=len(segment_uuids),
                translated=sum(1 for c in chunks if not c.skipped),
                processed=idx + 1,
            )
            await session.flush()
            if commit_per_chunk:
                await session.commit()
    except TranslationJobCancelled as exc:
        await fail_job(
            session=session,
            job=job,
            error={
                "error_class": type(exc).__name__,
                "repr": repr(exc),
                "phase": "user_cancelled",
            },
        )
        if commit_per_chunk:
            await session.commit()
        raise
    except Exception as exc:
        await fail_job(
            session=session,
            job=job,
            error={
                "error_class": type(exc).__name__,
                "repr": repr(exc),
                "phase": "translation_chunk_iteration",
            },
        )
        if commit_per_chunk:
            await session.commit()
        raise

    await complete_job(
        session=session,
        job=job,
        result={
            "chunks_total": len(segment_uuids),
            "chunks_translated": sum(1 for c in chunks if not c.skipped),
            "chunks_skipped": len(skipped),
            "skipped_segments": [
                {"satz_uuid": str(s.satz_uuid), "reason": s.reason} for s in skipped
            ],
            "final_context": context.to_dict(),
        },
    )
    return TranslationJobResult(job=job, chunks=chunks, skipped=skipped, final_context=context)


def _write_progress(job: Job, *, total: int, translated: int, processed: int) -> None:
    """Reassign `Job.payload` with progress counters merged in.

    JSONB columns don't track in-place dict mutation, so we always
    reassign the whole dict (preserving existing keys like
    `segment_uuids` and `cancel_requested`).
    """
    current = dict(job.payload or {})
    current["chunks_total"] = total
    current["chunks_translated"] = translated
    current["chunks_processed"] = processed
    job.payload = current


async def _persist_chunk_checkpoint(
    *,
    session: AsyncSession,
    job: Job,
    chunk_index: int,
    context: TranslationContext,
    skipped_so_far: list[SkippedSegment],
) -> None:
    """Per-chunk checkpoint. The full resume_state shape lives here so
    `resume_translation_job` only needs the latest checkpoint to rebuild
    state; nothing in the resume path reads from prior checkpoints."""
    await write_checkpoint(
        session=session,
        job=job,
        step=f"translation_chunk_{chunk_index}",
        payload={
            "chunk_index": chunk_index,
            "context": context.to_dict(),
            "skipped_so_far": [
                {"satz_uuid": str(s.satz_uuid), "reason": s.reason} for s in skipped_so_far
            ],
        },
    )
