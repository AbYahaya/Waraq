"""T-7.1.2 — TRANSLATION-PO + revision-UUID-on-change tests.

Mandatory tests from Sprint 2 §4:
- TRANSLATION-PO-Anlage-Test (PO created on every translated Segment with
  canonical payload)
- TRANSLATION-PO-Identische-Ausgabe-Keine-Revision-Test (no Revision when
  output equals prior text)
- TRANSLATION-PO-Pruefung-Keine-Revision-Test (dry-run / check operation
  produces no Revision; H-4)
- TRANSLATION-PO-Provenance-Kern-Test (PO routed via PROVENANCE-Kern only)
- T-REC-04 (resume with different output → new revision-UUID; prior retained)
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.release_gate import start_translation
from waraq.schemas import Block, Page, Project, ProvenanceObject, Revision, Segment
from waraq.schemas.enums import OcrStatus, POType, ScopeType
from waraq.translation import (
    TranslationContext,
    make_translation_persistence_hook,
    run_translation_job,
    start_translation_job,
)


async def _seed_project_with_segments(
    session: AsyncSession, *, n: int = 2, initial_text: str = "input"
) -> tuple[Project, list[Segment]]:
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="trans-persist-test")
    session.add(project)
    await session.flush()

    page = Page(
        page_uuid=new_uuid(),
        project_uuid=project.project_uuid,
        page_index=1,
        ocr_status=OcrStatus.GO,
    )
    session.add(page)
    await session.flush()

    block = Block(
        block_uuid=new_uuid(),
        page_uuid=page.page_uuid,
        block_type="main_text",
        block_index=1,
    )
    session.add(block)
    await session.flush()

    segments: list[Segment] = []
    for i in range(n):
        seg = Segment(
            satz_uuid=new_uuid(),
            block_uuid=block.block_uuid,
            satz_index=i + 1,
            lock_flag=LockFlag.NONE,
            text_content=f"{initial_text}-{i}",
        )
        session.add(seg)
        segments.append(seg)
    await session.flush()
    return project, segments


def _stub_translator(prefix: str = "DE:"):
    async def _t(text: str, ctx: TranslationContext) -> str:
        return f"{prefix} {text}"

    return _t


def _identity_translator():
    """Returns input verbatim. Used to verify identical-output → no-Revision."""

    async def _t(text: str, ctx: TranslationContext) -> str:
        return text

    return _t


# --- TRANSLATION-PO-Anlage-Test ---------------------------------------


@pytest.mark.asyncio
class TestTranslationPoAnlage:
    async def test_translation_po_written_for_every_translated_segment(
        self, db_session: AsyncSession
    ) -> None:
        project, segments = await _seed_project_with_segments(db_session, n=3)
        await start_translation(session=db_session, project_uuid=project.project_uuid)
        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[s.satz_uuid for s in segments],
        )

        hook = make_translation_persistence_hook(engine_identifier="stub-engine-v1")
        await run_translation_job(
            session=db_session,
            job=job,
            translator=_stub_translator(),
            on_segment_translated=hook,
        )

        # One TRANSLATION-PO per Segment.
        translation_pos = list(
            (
                await db_session.execute(
                    select(ProvenanceObject)
                    .where(ProvenanceObject.po_type == POType.TRANSLATION.value)
                    .where(ProvenanceObject.scope_uuid.in_([s.satz_uuid for s in segments]))
                )
            ).scalars()
        )
        assert len(translation_pos) == len(segments)
        for po in translation_pos:
            assert str(po.scope_type) == ScopeType.SEGMENT.value
            assert po.payload["engine"] == "stub-engine-v1"
            assert "input" in po.payload
            assert "output" in po.payload
            assert "text_changed" in po.payload
            assert "rev_uuid" in po.payload
            assert "terminology_bindings" in po.payload
            assert "style_anchors" in po.payload

    async def test_text_change_yields_revision_uuid_on_po(self, db_session: AsyncSession) -> None:
        # Segment text "input-0" → translator emits "DE: input-0" (different).
        project, segments = await _seed_project_with_segments(db_session, n=1)
        await start_translation(session=db_session, project_uuid=project.project_uuid)
        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[segments[0].satz_uuid],
        )
        hook = make_translation_persistence_hook(engine_identifier="stub")
        await run_translation_job(
            session=db_session,
            job=job,
            translator=_stub_translator(),
            on_segment_translated=hook,
        )

        po = (
            await db_session.execute(
                select(ProvenanceObject).where(ProvenanceObject.scope_uuid == segments[0].satz_uuid)
            )
        ).scalar_one()
        assert po.payload["text_changed"] is True
        assert po.payload["rev_uuid"] is not None

        # Revision row really landed.
        revisions = list(
            (
                await db_session.execute(
                    select(Revision).where(Revision.satz_uuid == segments[0].satz_uuid)
                )
            ).scalars()
        )
        assert len(revisions) == 1
        assert str(revisions[0].rev_uuid) == po.payload["rev_uuid"]
        assert revisions[0].after_text == "DE: input-0"

    async def test_translation_po_payload_includes_terminology_and_style(
        self, db_session: AsyncSession
    ) -> None:
        # Provide non-empty terminology + style anchors via initial_context;
        # PO must record them on the payload.
        project, segments = await _seed_project_with_segments(db_session, n=1)
        await start_translation(session=db_session, project_uuid=project.project_uuid)
        ctx = TranslationContext(
            terminology_bindings={str(new_uuid()): "fixed-term"},
            style_anchors=["short", "literal"],
        )
        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[segments[0].satz_uuid],
            initial_context=ctx,
        )
        hook = make_translation_persistence_hook(engine_identifier="stub")
        await run_translation_job(
            session=db_session,
            job=job,
            translator=_stub_translator(),
            on_segment_translated=hook,
        )

        po = (
            await db_session.execute(
                select(ProvenanceObject).where(ProvenanceObject.scope_uuid == segments[0].satz_uuid)
            )
        ).scalar_one()
        # Terminology bindings list at the start; style anchors carried through.
        assert po.payload["terminology_bindings"] == ctx.terminology_bindings
        assert po.payload["style_anchors"] == ctx.style_anchors


# --- TRANSLATION-PO-Identische-Ausgabe-Keine-Revision-Test ----------


@pytest.mark.asyncio
class TestIdenticalOutputProducesNoRevision:
    """Sprint 2 §2 / R-S2-05: identical translation output → NO new
    Revision-UUID. Revisions table stays clean of no-op rows."""

    async def test_identical_output_writes_po_but_no_revision(
        self, db_session: AsyncSession
    ) -> None:
        project, segments = await _seed_project_with_segments(db_session, n=1)
        await start_translation(session=db_session, project_uuid=project.project_uuid)
        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[segments[0].satz_uuid],
        )
        hook = make_translation_persistence_hook(engine_identifier="stub")
        # Translator returns input verbatim: text_content == output.
        await run_translation_job(
            session=db_session,
            job=job,
            translator=_identity_translator(),
            on_segment_translated=hook,
        )

        # PO landed.
        po = (
            await db_session.execute(
                select(ProvenanceObject).where(ProvenanceObject.scope_uuid == segments[0].satz_uuid)
            )
        ).scalar_one()
        assert po.payload["text_changed"] is False
        assert po.payload["rev_uuid"] is None

        # Revision did NOT land.
        rev_count = (
            await db_session.execute(
                select(func.count())
                .select_from(Revision)
                .where(Revision.satz_uuid == segments[0].satz_uuid)
            )
        ).scalar_one()
        assert rev_count == 0


# --- TRANSLATION-PO-Pruefung-Keine-Revision-Test (H-4) -------------


@pytest.mark.asyncio
class TestDryRunProducesNoRevisionAndNoPO:
    """Sprint 2 §2: translation dry-run / check operation produces no
    Revision-UUID. We model "dry-run" as `run_translation_job` invoked
    WITHOUT the persistence hook — no Revision and no TRANSLATION-PO are
    written, the chunks just exist in memory. H-4 by construction."""

    async def test_dry_run_writes_no_revision_and_no_translation_po(
        self, db_session: AsyncSession
    ) -> None:
        project, segments = await _seed_project_with_segments(db_session, n=2)
        await start_translation(session=db_session, project_uuid=project.project_uuid)

        before_revs = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()
        before_translation_pos = (
            await db_session.execute(
                select(func.count())
                .select_from(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.TRANSLATION.value)
            )
        ).scalar_one()

        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[s.satz_uuid for s in segments],
        )
        # No on_segment_translated hook = dry-run mode.
        result = await run_translation_job(
            session=db_session, job=job, translator=_stub_translator()
        )

        # Chunks exist in memory.
        assert len(result.chunks) == 2
        assert all(c.output_text is not None for c in result.chunks)

        # Database is unchanged.
        after_revs = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()
        after_translation_pos = (
            await db_session.execute(
                select(func.count())
                .select_from(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.TRANSLATION.value)
            )
        ).scalar_one()
        assert after_revs == before_revs
        assert after_translation_pos == before_translation_pos


# --- TRANSLATION-PO-Provenance-Kern-Test --------------------------


class TestTranslationPoRoutedViaProvenanceKern:
    """Sprint 2 §2 / R-S2-06 / DBB §B Abkürzung 7: TRANSLATION-PO writes
    go through PROVENANCE-Kern's `create_po`, never via direct DB insert.

    The persistence module imports only `create_po` from
    `waraq.provenance` (and nothing internal); ad-hoc inserts would
    require importing the ORM `ProvenanceObject` model + a session
    write. The structural absence of those imports is the audit-time
    proof."""

    def test_persistence_module_imports_only_create_po(self) -> None:
        import importlib

        mod = importlib.import_module("waraq.translation.persistence")
        # Import set: must NOT include the ORM ProvenanceObject class.
        names = set(vars(mod))
        assert "create_po" in names
        assert "ProvenanceObject" not in names

    def test_persistence_source_does_not_construct_provenance_object(self) -> None:
        # Belt-and-braces: scan source for direct ProvenanceObject(...)
        # construction. The hook MUST go through create_po.
        import inspect

        from waraq.translation import persistence

        source = inspect.getsource(persistence)
        assert "ProvenanceObject(" not in source
        assert "create_po(" in source


# --- T-REC-04: resume with different output → new Revision -------


@pytest.mark.asyncio
class TestResumeWithDifferentOutputIssuesNewRevision:
    """T-REC-04: a second translation pass on the same Segment that
    produces different output issues a new Revision-UUID; the prior
    revision is NOT overwritten — both rows live in revision history."""

    async def test_two_translations_with_different_outputs_yield_two_revisions(
        self, db_session: AsyncSession
    ) -> None:
        project, segments = await _seed_project_with_segments(db_session, n=1)
        await start_translation(session=db_session, project_uuid=project.project_uuid)
        seg = segments[0]
        hook = make_translation_persistence_hook(engine_identifier="stub")

        # First pass: "DE-v1: input-0".
        job1 = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[seg.satz_uuid],
        )
        await run_translation_job(
            session=db_session,
            job=job1,
            translator=_stub_translator(prefix="DE-v1:"),
            on_segment_translated=hook,
        )
        first_rev_uuid = seg.current_rev_uuid
        assert first_rev_uuid is not None

        # Second pass with different translator: "DE-v2: input-0".
        # (Need another uebersetzungsstart DE — start_translation_job
        # checks for existence, not freshness; the existing one suffices.)
        job2 = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[seg.satz_uuid],
        )
        await run_translation_job(
            session=db_session,
            job=job2,
            translator=_stub_translator(prefix="DE-v2:"),
            on_segment_translated=hook,
        )
        second_rev_uuid = seg.current_rev_uuid
        assert second_rev_uuid is not None
        assert second_rev_uuid != first_rev_uuid

        # Both revisions in history — prior NOT overwritten.
        revisions = list(
            (
                await db_session.execute(
                    select(Revision)
                    .where(Revision.satz_uuid == seg.satz_uuid)
                    .order_by(Revision.created_at.asc())
                )
            ).scalars()
        )
        assert len(revisions) == 2
        # First pass takes the original input ("input-0") and produces v1.
        # Second pass takes the post-v1 text (the segment's current
        # text_content after create_revision) and produces v2 from it —
        # this is the canonical revision chain (each Revision's input is
        # the prior `text_content`).
        assert revisions[0].after_text == "DE-v1: input-0"
        assert revisions[1].after_text == "DE-v2: DE-v1: input-0"
        assert revisions[1].before_text == "DE-v1: input-0"


# --- Schema discipline: the Translation hook produces the right scope ---


@pytest.mark.asyncio
class TestTranslationPoScopeDiscipline:
    """TRANSLATION-PO is segment-scoped per CAB §5.3."""

    async def test_translation_po_scope_type_is_segment(self, db_session: AsyncSession) -> None:
        project, segments = await _seed_project_with_segments(db_session, n=1)
        await start_translation(session=db_session, project_uuid=project.project_uuid)
        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[segments[0].satz_uuid],
        )
        hook = make_translation_persistence_hook(engine_identifier="stub")
        await run_translation_job(
            session=db_session,
            job=job,
            translator=_stub_translator(),
            on_segment_translated=hook,
        )

        po = (
            await db_session.execute(
                select(ProvenanceObject).where(ProvenanceObject.scope_uuid == segments[0].satz_uuid)
            )
        ).scalar_one()
        assert str(po.scope_type) == ScopeType.SEGMENT.value
        assert po.scope_uuid == segments[0].satz_uuid
