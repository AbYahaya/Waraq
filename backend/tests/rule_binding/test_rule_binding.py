"""T-7.2.1 — RULE_BINDING tests.

Mandatory tests from Sprint 2 §4:
- RULE-BINDING-PO-Sauber-Test (clean apply on unlocked Segment)
- RULE-BINDING-Konflikt-Mit-Sperrflag-Conflict-Instance-Test (locked → conflict)
- RULE-BINDING-Lokale-Ausnahme-Provenance-Test (post-resolution PO carries
  ausnahme_flag + decision_event_uuid)
- RULE-BINDING-Lookup-Sole-Entrypoint-Test (no direct Concept queries)
- T-H2-01 (regression with new path)
- T-KE-01 (NO_ENTRY sentinel surfaces in pipeline)
- T-H6-01 (no silent resolution; regression)
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.conflicts import (
    ConflictType,
    ResolutionType,
    RuleSource,
    resolve_with_local_exception,
)
from waraq.glossary import BindingLevel, create_entry
from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.release_gate import start_translation
from waraq.rule_binding import (
    bind_glossary_to_segment,
    find_glossary_matches_in_segment,
    make_locked_segment_glossary_conflict_hook,
    make_translation_with_rule_binding_hook,
)
from waraq.schemas import (
    Block,
    ConflictInstance,
    Page,
    Project,
    ProvenanceObject,
    Segment,
)
from waraq.schemas.enums import OcrStatus, POType, ScopeType
from waraq.translation import (
    TranslationContext,
    run_translation_job,
    start_translation_job,
)


async def _seed(
    session: AsyncSession,
    *,
    text: str,
    lock: LockFlag = LockFlag.NONE,
) -> tuple[Project, Segment]:
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)
    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="rule-binding-test")
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
    segment = Segment(
        satz_uuid=new_uuid(),
        block_uuid=block.block_uuid,
        satz_index=1,
        lock_flag=lock,
        text_content=text,
    )
    session.add(segment)
    await session.flush()
    return project, segment


def _passthrough_translator():
    async def _t(text: str, ctx: TranslationContext) -> str:
        return f"DE: {text}"

    return _t


# --- find_glossary_matches_in_segment ---------------------------


@pytest.mark.asyncio
class TestFindGlossaryMatches:
    async def test_returns_match_for_known_surface_form(self, db_session: AsyncSession) -> None:
        project, segment = await _seed(db_session, text="ابن حجر العسقلاني wrote it")
        concept, _ = await create_entry(
            session=db_session,
            canonical_label="ابن حجر العسقلاني",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )
        matches = await find_glossary_matches_in_segment(
            session=db_session,
            segment=segment,
            project_uuid=project.project_uuid,
            candidate_surface_forms=["ابن حجر العسقلاني"],
        )
        assert len(matches) == 1
        assert matches[0].concept_id == concept.concept_id

    async def test_returns_empty_for_unmatched_form(self, db_session: AsyncSession) -> None:
        project, segment = await _seed(db_session, text="something else")
        await create_entry(
            session=db_session,
            canonical_label="nicht_im_text",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )
        matches = await find_glossary_matches_in_segment(
            session=db_session,
            segment=segment,
            project_uuid=project.project_uuid,
            candidate_surface_forms=["nicht_im_text"],
        )
        assert matches == []

    async def test_returns_empty_when_form_missing_from_glossary(
        self, db_session: AsyncSession
    ) -> None:
        # Surface in text but no glossary entry → NO_ENTRY → no match.
        project, segment = await _seed(db_session, text="containing al-Bukhari ref")
        matches = await find_glossary_matches_in_segment(
            session=db_session,
            segment=segment,
            project_uuid=project.project_uuid,
            candidate_surface_forms=["al-Bukhari"],
        )
        assert matches == []

    async def test_no_candidates_returns_empty(self, db_session: AsyncSession) -> None:
        project, segment = await _seed(db_session, text="x")
        matches = await find_glossary_matches_in_segment(
            session=db_session,
            segment=segment,
            project_uuid=project.project_uuid,
            candidate_surface_forms=None,
        )
        assert matches == []


# --- bind_glossary_to_segment: clean (unlocked) path ----------------


@pytest.mark.asyncio
class TestRuleBindingClean:
    """RULE-BINDING-PO-Sauber-Test."""

    async def test_unlocked_segment_writes_rule_binding_po(self, db_session: AsyncSession) -> None:
        project, segment = await _seed(db_session, text="al-Tirmidhi narrated")
        concept, _ = await create_entry(
            session=db_session,
            canonical_label="al-Tirmidhi",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )

        result = await bind_glossary_to_segment(
            session=db_session,
            segment=segment,
            project_uuid=project.project_uuid,
            candidate_surface_forms=["al-Tirmidhi"],
            application_context={"context": "main_text"},
        )

        assert len(result.applied) == 1
        assert result.conflicts == []
        applied = result.applied[0]
        assert applied.concept_id == concept.concept_id
        assert applied.surface_form == "al-Tirmidhi"
        assert applied.ausnahme_flag is False
        assert applied.decision_event_uuid is None

        # PO row exists with canonical payload.
        po = (
            await db_session.execute(
                select(ProvenanceObject).where(ProvenanceObject.po_uuid == applied.po_uuid)
            )
        ).scalar_one()
        assert str(po.po_type) == POType.RULE_BINDING.value
        assert str(po.scope_type) == ScopeType.SEGMENT.value
        assert po.scope_uuid == segment.satz_uuid
        assert po.payload["concept_id"] == str(concept.concept_id)
        assert po.payload["surface_form"] == "al-Tirmidhi"
        assert po.payload["ausnahme_flag"] is False
        assert po.payload["application_context"] == {"context": "main_text"}


# --- bind_glossary_to_segment: locked → conflict_instance --------


@pytest.mark.asyncio
class TestRuleBindingConflictWithLockedSegment:
    """RULE-BINDING-Konflikt-Mit-Sperrflag-Conflict-Instance-Test +
    T-H2-01 + T-H6-01.

    Glossary entry against a locked Segment → conflict_instance with
    state=offen; no silent application; no RULE_BINDING-PO."""

    async def test_locked_segment_creates_open_conflict_no_po(
        self, db_session: AsyncSession
    ) -> None:
        project, segment = await _seed(
            db_session, text="ابن حجر narrated", lock=LockFlag.MANUAL_EDITORIAL
        )
        await create_entry(
            session=db_session,
            canonical_label="ابن حجر",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )

        before_pos = (
            await db_session.execute(
                select(func.count())
                .select_from(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.RULE_BINDING.value)
            )
        ).scalar_one()

        result = await bind_glossary_to_segment(
            session=db_session,
            segment=segment,
            project_uuid=project.project_uuid,
            candidate_surface_forms=["ابن حجر"],
        )

        assert result.applied == []
        assert len(result.conflicts) == 1
        c = result.conflicts[0]

        # conflict_instance row landed.
        ci = (
            await db_session.execute(
                select(ConflictInstance).where(ConflictInstance.conflict_uuid == c.conflict_uuid)
            )
        ).scalar_one()
        assert ci.state == "offen"
        assert ci.satz_uuid == segment.satz_uuid
        assert ci.rule_source == RuleSource.GLOSSARY.value
        assert ci.conflict_type == ConflictType.GLOSSAR_VS_SPERRFLAG.value
        assert ci.context["concept_id"] == str(c.concept_id)

        # No RULE_BINDING-PO written.
        after_pos = (
            await db_session.execute(
                select(func.count())
                .select_from(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.RULE_BINDING.value)
            )
        ).scalar_one()
        assert after_pos == before_pos

        # Lock unchanged — silent overwrite refused (T-H6-01).
        assert segment.lock_flag == LockFlag.MANUAL_EDITORIAL


# --- lokale_ausnahme: subsequent bind carries ausnahme_flag -----


@pytest.mark.asyncio
class TestRuleBindingLokaleAusnahme:
    """RULE-BINDING-Lokale-Ausnahme-Provenance-Test.

    After a conflict_instance is resolved with `lokale_ausnahme`,
    subsequent translation passes (with the segment now unlocked) write
    a RULE_BINDING-PO that carries `ausnahme_flag=True` and the original
    resolution's decision_event_uuid."""

    async def test_post_resolution_po_carries_ausnahme_flag(self, db_session: AsyncSession) -> None:
        project, segment = await _seed(
            db_session, text="some surface form here", lock=LockFlag.MANUAL_LOCAL
        )
        concept, _ = await create_entry(
            session=db_session,
            canonical_label="some surface form",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )

        # First bind: locked → conflict.
        result1 = await bind_glossary_to_segment(
            session=db_session,
            segment=segment,
            project_uuid=project.project_uuid,
            candidate_surface_forms=["some surface form"],
        )
        assert len(result1.conflicts) == 1
        conflict_uuid = result1.conflicts[0].conflict_uuid

        # Resolve with lokale_ausnahme.
        ci = (
            await db_session.execute(
                select(ConflictInstance).where(ConflictInstance.conflict_uuid == conflict_uuid)
            )
        ).scalar_one()
        de = await resolve_with_local_exception(session=db_session, conflict=ci)
        assert ci.resolution_type == ResolutionType.LOKALE_AUSNAHME.value

        # Now unlock the segment (e.g., user released the lock as part of
        # accepting the exception flow). Subsequent bind writes a
        # RULE_BINDING-PO with ausnahme_flag=True referencing `de`.
        segment.lock_flag = LockFlag.NONE
        await db_session.flush()

        result2 = await bind_glossary_to_segment(
            session=db_session,
            segment=segment,
            project_uuid=project.project_uuid,
            candidate_surface_forms=["some surface form"],
        )
        assert len(result2.applied) == 1
        applied = result2.applied[0]
        assert applied.concept_id == concept.concept_id
        assert applied.ausnahme_flag is True
        assert applied.decision_event_uuid == de.decision_event_uuid

        po = (
            await db_session.execute(
                select(ProvenanceObject).where(ProvenanceObject.po_uuid == applied.po_uuid)
            )
        ).scalar_one()
        assert po.payload["ausnahme_flag"] is True
        assert po.payload["decision_event_uuid"] == str(de.decision_event_uuid)


# --- RULE-BINDING-Lookup-Sole-Entrypoint-Test ------------------


class TestRuleBindingLookupSoleEntrypoint:
    """R-S2-08: the rule_binding service routes glossary resolution
    through `glossary.lookup` (and `glossary.get_entry` for record
    detail). It does NOT import or query the `Concept` ORM directly.

    The structural absence of a `Concept` import is the canonical proof
    that no direct DB query exists. Combined with `lookup` returning the
    `NO_ENTRY` sentinel for misses, the surface-to-concept resolution
    path stays canonical (R-S2-08 + T-KE-01)."""

    def test_rule_binding_module_does_not_import_concept_orm(self) -> None:
        import importlib

        mod = importlib.import_module("waraq.rule_binding.service")
        names = set(vars(mod))
        assert "lookup" in names
        assert "get_entry" in names
        assert "Concept" not in names  # the ORM model itself

    def test_rule_binding_source_does_not_select_from_concepts_table(self) -> None:
        # The source must call lookup(...) / get_entry(...) but never
        # construct a `select(Concept)` or similar.
        import inspect

        from waraq.rule_binding import service

        source = inspect.getsource(service)
        # Hard-line: no `select(Concept` in the source. (We allow
        # `Concept.__table__` etc. if that ever became necessary, but
        # the v1.0 implementation must not.)
        assert "select(Concept" not in source
        assert "lookup(" in source


# --- T-KE-01: NO_ENTRY surfaces correctly via the bind path ------


@pytest.mark.asyncio
class TestRuleBindingHonorsNoEntrySentinel:
    """T-KE-01: glossary lookup integration in translation pipeline:
    explicit Konzept-ID for hits, `NO_ENTRY` for misses, never null. The
    rule_binding layer specifically discards `NO_ENTRY` matches without
    creating any binding row."""

    async def test_no_entry_match_does_not_write_anything(self, db_session: AsyncSession) -> None:
        project, segment = await _seed(db_session, text="al-Bukhari narrated x")
        # No glossary entry for "al-Bukhari" — lookup returns NO_ENTRY.
        before_pos = (
            await db_session.execute(
                select(func.count())
                .select_from(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.RULE_BINDING.value)
            )
        ).scalar_one()
        before_conflicts = (
            await db_session.execute(select(func.count()).select_from(ConflictInstance))
        ).scalar_one()

        result = await bind_glossary_to_segment(
            session=db_session,
            segment=segment,
            project_uuid=project.project_uuid,
            candidate_surface_forms=["al-Bukhari"],
        )
        assert result.applied == []
        assert result.conflicts == []

        after_pos = (
            await db_session.execute(
                select(func.count())
                .select_from(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.RULE_BINDING.value)
            )
        ).scalar_one()
        after_conflicts = (
            await db_session.execute(select(func.count()).select_from(ConflictInstance))
        ).scalar_one()
        assert after_pos == before_pos
        assert after_conflicts == before_conflicts


# --- Translation pipeline integration -----------------------------


@pytest.mark.asyncio
class TestTranslationPipelineRuleBindingIntegration:
    """End-to-end: a translation job wired with the composite
    rule_binding+persistence hook produces TRANSLATION-PO + Revision +
    RULE_BINDING-PO for unlocked segments with glossary matches; for
    locked segments, conflict_instance is created."""

    async def test_unlocked_segment_full_chain(self, db_session: AsyncSession) -> None:
        project, segment = await _seed(db_session, text="al-Bukhari narrated x")
        concept, _ = await create_entry(
            session=db_session,
            canonical_label="al-Bukhari",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )
        await start_translation(session=db_session, project_uuid=project.project_uuid)
        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[segment.satz_uuid],
        )

        composite_hook = make_translation_with_rule_binding_hook(
            engine_identifier="stub-engine",
            project_uuid=project.project_uuid,
            candidate_surface_forms=["al-Bukhari"],
        )
        await run_translation_job(
            session=db_session,
            job=job,
            translator=_passthrough_translator(),
            on_segment_translated=composite_hook,
        )

        # TRANSLATION-PO for the segment.
        translation_pos = list(
            (
                await db_session.execute(
                    select(ProvenanceObject)
                    .where(ProvenanceObject.scope_uuid == segment.satz_uuid)
                    .where(ProvenanceObject.po_type == POType.TRANSLATION.value)
                )
            ).scalars()
        )
        assert len(translation_pos) == 1

        # RULE_BINDING-PO for the al-Bukhari concept.
        rule_pos = list(
            (
                await db_session.execute(
                    select(ProvenanceObject)
                    .where(ProvenanceObject.scope_uuid == segment.satz_uuid)
                    .where(ProvenanceObject.po_type == POType.RULE_BINDING.value)
                )
            ).scalars()
        )
        assert len(rule_pos) == 1
        assert rule_pos[0].payload["concept_id"] == str(concept.concept_id)

    async def test_locked_segment_creates_conflict_via_skip_hook(
        self, db_session: AsyncSession
    ) -> None:
        project, segment = await _seed(
            db_session, text="al-Tirmidhi here", lock=LockFlag.MANUAL_LOCAL
        )
        await create_entry(
            session=db_session,
            canonical_label="al-Tirmidhi",
            language="ar",
            binding_level=BindingLevel.PROJECT,
            project_uuid=project.project_uuid,
        )
        await start_translation(session=db_session, project_uuid=project.project_uuid)
        job = await start_translation_job(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[segment.satz_uuid],
        )

        skip_hook = make_locked_segment_glossary_conflict_hook(
            project_uuid=project.project_uuid,
            candidate_surface_forms=["al-Tirmidhi"],
        )
        result = await run_translation_job(
            session=db_session,
            job=job,
            translator=_passthrough_translator(),
            on_locked_segment_skip=skip_hook,
        )

        assert len(result.skipped) == 1

        # conflict_instance landed with state=offen.
        conflicts = list(
            (
                await db_session.execute(
                    select(ConflictInstance).where(ConflictInstance.satz_uuid == segment.satz_uuid)
                )
            ).scalars()
        )
        assert len(conflicts) == 1
        assert conflicts[0].state == "offen"
        assert conflicts[0].rule_source == RuleSource.GLOSSARY.value
