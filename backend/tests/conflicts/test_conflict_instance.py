"""T-5.1.2 — CONFLICT-Erkennung tests.

Mandatory tests from Sprint 1 §4 (HG-S1-2 makes Persistenz + Server-Restart
unumgehbar):

- T-H2-01 — Terminology application against locked Segment → conflict_instance
  with state=offen
- T-H2-02 — Every transition offen → aufgeloest writes a Decision Event
- T-H6-01 — Three resolution options exposed; no fourth path
- Conflict-Instance-Persistenz-Test (DB row immediately after detection)
- **Conflict-Instance-Server-Restart-Test** (engine.dispose round-trip)
- Conflict-Instance-Drei-Aufloesungsoptionen-Test
- Conflict-Instance-Decision-Event-Bei-Aufloesung-Test
- Conflict-Instance-Kein-Decision-Event-Bei-Erkennung-Test

Also covers HG-S1-6 (`conflict_instance` is not a PO — service writes none).
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from waraq.conflicts import (
    ConflictAlreadyResolved,
    ConflictResolutionPathInvalid,
    ConflictState,
    ConflictType,
    ResolutionType,
    RuleSource,
    detect_conflict,
    get_open_conflicts_for_page,
    get_open_conflicts_for_project,
    get_open_conflicts_for_segment,
    resolve_with_glossary_change,
    resolve_with_local_exception,
    resolve_with_lock_release,
)
from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.lock import ConfirmationContext, LockConfirmationRequired, set_lock
from waraq.schemas import (
    Block,
    ConflictInstance,
    DecisionEvent,
    Page,
    Project,
    ProvenanceObject,
    Segment,
)
from waraq.schemas.enums import DecisionSource, POType, ScopeType


async def _seed_segment(
    session: AsyncSession,
    *,
    lock_flag: LockFlag = LockFlag.NONE,
) -> tuple[Project, Page, Block, Segment]:
    """Create a project → page → block → segment chain. Returns the chain so
    tests can pivot at any level (project_uuid, page_uuid, block_uuid)."""
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="conflict-test")
    session.add(project)
    await session.flush()

    page = Page(page_uuid=new_uuid(), project_uuid=project.project_uuid, page_index=1)
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
        lock_flag=lock_flag,
        text_content="locked content",
    )
    session.add(segment)
    await session.flush()
    return project, page, block, segment


# --- Layer 1: surface contract -------------------------------------------


class TestT_5_1_2_T_H6_01_ThreeResolutionPathsOnly:
    """T-H6-01: Three resolution options exposed; no fourth code path
    resolves a conflict_instance."""

    def test_module_exposes_exactly_three_resolution_paths(self) -> None:
        import inspect as _inspect
        import types

        import waraq.conflicts as conflicts_module

        functions = {
            name
            for name, obj in vars(conflicts_module).items()
            if not name.startswith("_")
            and callable(obj)
            and not isinstance(obj, type)
            and not isinstance(obj, types.ModuleType)
            and _inspect.getmodule(obj) is not None
            and _inspect.getmodule(obj).__name__.startswith("waraq.conflicts")  # type: ignore[union-attr]
            and "resolve" in name.lower()
        }
        assert functions == {
            "resolve_with_local_exception",
            "resolve_with_glossary_change",
            "resolve_with_lock_release",
        }, f"unexpected resolution surface: {functions}"

    def test_resolution_signatures_block_decision_event_uuid_kwarg(self) -> None:
        # Callers don't pass decision_event_uuid in — the resolution function
        # creates the DE itself. Allowing a caller-supplied uuid would let
        # someone "resolve" a conflict by referencing an arbitrary DE,
        # bypassing the H-2 audit-trail integrity.
        for fn in (
            resolve_with_local_exception,
            resolve_with_glossary_change,
            resolve_with_lock_release,
        ):
            params = set(inspect.signature(fn).parameters)
            assert "decision_event_uuid" not in params, (
                f"{fn.__name__} accepts caller-supplied decision_event_uuid"
            )


# --- Detection: T-H2-01 + Kein-DE-bei-Erkennung --------------------------


@pytest.mark.asyncio
class TestT_5_1_2_DetectionWritesOffenRow:
    """T-H2-01 + Conflict-Instance-Kein-Decision-Event-Bei-Erkennung-Test.

    Detection persists a conflict_instance row immediately, with state=offen,
    no decision_event_uuid, no resolution_type, no resolved_at."""

    async def test_terminology_against_locked_segment_creates_offen_row(
        self, db_session: AsyncSession
    ) -> None:
        _, _, _, segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_LOCAL)

        conflict = await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.TERMINOLOGY,
            conflict_type=ConflictType.TERMINOLOGIE_VS_SPERRFLAG,
            context={"attempted_text": "auto-overwrite"},
        )

        assert conflict.state == ConflictState.OFFEN.value
        assert conflict.satz_uuid == segment.satz_uuid
        assert conflict.rule_source == RuleSource.TERMINOLOGY.value
        assert conflict.conflict_type == ConflictType.TERMINOLOGIE_VS_SPERRFLAG.value
        assert conflict.decision_event_uuid is None
        assert conflict.resolution_type is None
        assert conflict.resolved_at is None
        assert conflict.context["attempted_text"] == "auto-overwrite"

    async def test_detection_writes_no_decision_event(self, db_session: AsyncSession) -> None:
        # Conflict-Instance-Kein-Decision-Event-Bei-Erkennung-Test.
        # Detect five conflicts; assert decision_events delta = 0.
        _, _, _, segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_LOCAL)
        before = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()

        for _ in range(5):
            await detect_conflict(
                session=db_session,
                segment=segment,
                rule_source=RuleSource.GLOSSARY,
                conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
            )

        after = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        assert after == before

    async def test_detection_writes_no_provenance_object(self, db_session: AsyncSession) -> None:
        # HG-S1-6: conflict_instance is NOT a PO. Detecting must not call
        # create_po (and therefore no PO row of any type is added).
        _, _, _, segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_LOCAL)
        before = (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one()

        await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )

        after = (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one()
        assert after == before


# --- Persistenz-Test (DB present immediately, not in memory) -------------


@pytest.mark.asyncio
class TestT_5_1_2_PersistenzTest:
    """Conflict-Instance-Persistenz-Test: row exists in the DB immediately
    after detection. Distinguished from the restart test below — this one
    checks the same session/connection sees the row, rejecting any in-memory
    cache shortcut."""

    async def test_row_visible_via_independent_query_after_detection(
        self, db_session: AsyncSession
    ) -> None:
        _, _, _, segment = await _seed_segment(db_session)

        conflict = await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )

        # Independent SELECT: forces a real DB read rather than ORM cache.
        result = await db_session.execute(
            select(ConflictInstance).where(ConflictInstance.conflict_uuid == conflict.conflict_uuid)
        )
        loaded = result.scalar_one()
        assert loaded.conflict_uuid == conflict.conflict_uuid
        assert loaded.state == ConflictState.OFFEN.value


# --- THE Server-Restart-Test (HG-S1-2, MANDATORY, NON-SKIPPABLE) ---------


@pytest.mark.asyncio
class TestT_5_1_2_ServerRestartTest:
    """**Conflict-Instance-Server-Restart-Test** — HG-S1-2 hard gate. The
    canonical pattern from T-2.1.2 checkpoint restart-survival: write +
    commit + engine.dispose() + fresh engine + read returns same row.

    DBB Abkürzung 11 / CLAUDE.md §5.6: failing this test means H-6
    enforcement collapses across restart boundaries; locked Segments become
    silently overwritable.

    The test cleans up its own data — does NOT use the rolling-back
    db_session fixture, because the whole point is to commit and survive
    teardown."""

    async def test_open_conflict_persists_across_engine_dispose(self) -> None:
        from tests.conftest import _test_database_url

        url = _test_database_url()

        # Phase A: seed + detect + commit + tear engine_a down.
        engine_a = create_async_engine(url, future=True)
        sm_a = async_sessionmaker(bind=engine_a, class_=AsyncSession, expire_on_commit=False)

        from tests.conftest import seed_account_uuid

        account_uuid = new_uuid()
        project_uuid = new_uuid()
        page_uuid = new_uuid()
        block_uuid = new_uuid()
        satz_uuid = new_uuid()
        conflict_uuid_marker: str

        try:
            async with sm_a() as session, session.begin():
                await seed_account_uuid(session, account_uuid)
                session.add(
                    Project(
                        project_uuid=project_uuid,
                        account_uuid=account_uuid,
                        name="restart-survival-test",
                    )
                )
                await session.flush()
                session.add(Page(page_uuid=page_uuid, project_uuid=project_uuid, page_index=1))
                await session.flush()
                session.add(
                    Block(
                        block_uuid=block_uuid,
                        page_uuid=page_uuid,
                        block_type="main_text",
                        block_index=1,
                    )
                )
                await session.flush()
                segment = Segment(
                    satz_uuid=satz_uuid,
                    block_uuid=block_uuid,
                    satz_index=1,
                    lock_flag=LockFlag.MANUAL_EDITORIAL,
                    text_content="locked content",
                )
                session.add(segment)
                await session.flush()

                conflict = await detect_conflict(
                    session=session,
                    segment=segment,
                    rule_source=RuleSource.TERMINOLOGY,
                    conflict_type=ConflictType.TERMINOLOGIE_VS_SPERRFLAG,
                    context={"attempted_text": "rule-overwrite"},
                )
                conflict_uuid_marker = str(conflict.conflict_uuid)
            # Detection committed.
        finally:
            await engine_a.dispose()

        # Phase B: brand-new engine, brand-new session — read it back.
        engine_b = create_async_engine(url, future=True)
        sm_b = async_sessionmaker(bind=engine_b, class_=AsyncSession, expire_on_commit=False)

        try:
            async with sm_b() as session:
                rows = await get_open_conflicts_for_segment(session=session, satz_uuid=satz_uuid)
                assert len(rows) == 1, (
                    "Abkürzung 11 violated: conflict_instance did not "
                    "survive engine teardown — H-6 enforcement collapses"
                )
                survivor = rows[0]
                assert str(survivor.conflict_uuid) == conflict_uuid_marker
                assert survivor.state == ConflictState.OFFEN.value
                assert survivor.rule_source == RuleSource.TERMINOLOGY.value
                assert survivor.conflict_type == ConflictType.TERMINOLOGIE_VS_SPERRFLAG.value
                assert survivor.decision_event_uuid is None
                assert survivor.context["attempted_text"] == "rule-overwrite"
        finally:
            await engine_b.dispose()

        # Phase C: cleanup so we don't pollute the dev DB.
        engine_c = create_async_engine(url, future=True)
        sm_c = async_sessionmaker(bind=engine_c, class_=AsyncSession, expire_on_commit=False)
        try:
            async with sm_c() as session, session.begin():
                await session.execute(
                    delete(ConflictInstance).where(ConflictInstance.satz_uuid == satz_uuid)
                )
                await session.execute(delete(Segment).where(Segment.satz_uuid == satz_uuid))
                await session.execute(delete(Block).where(Block.block_uuid == block_uuid))
                await session.execute(delete(Page).where(Page.page_uuid == page_uuid))
                await session.execute(delete(Project).where(Project.project_uuid == project_uuid))
                # Account cleanup:
                from waraq.schemas import Account

                await session.execute(delete(Account).where(Account.account_uuid == account_uuid))
        finally:
            await engine_c.dispose()


# --- T-H2-02 + Drei-Aufloesungsoptionen + Decision-Event-Bei-Aufloesung -


@pytest.mark.asyncio
class TestT_5_1_2_ResolutionPaths:
    """Conflict-Instance-Drei-Aufloesungsoptionen-Test: all three paths
    reachable. Each writes a Decision Event (T-H2-02 +
    Conflict-Instance-Decision-Event-Bei-Aufloesung-Test)."""

    async def test_resolve_with_local_exception(self, db_session: AsyncSession) -> None:
        _, _, _, segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_LOCAL)
        conflict = await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )

        de = await resolve_with_local_exception(
            session=db_session,
            conflict=conflict,
            content={"justification": "name is a project-specific exception"},
        )

        assert conflict.state == ConflictState.AUFGELOEST.value
        assert conflict.resolution_type == ResolutionType.LOKALE_AUSNAHME.value
        assert conflict.decision_event_uuid == de.decision_event_uuid
        assert conflict.resolved_at is not None
        # DE shape:
        assert str(de.scope_type) == ScopeType.SEGMENT.value
        assert de.scope_uuid == segment.satz_uuid
        assert str(de.decision_source) == DecisionSource.CONFLICT_RESOLUTION.value
        assert de.decision_type == "conflict_resolve_local_exception"
        assert de.content["justification"] == "name is a project-specific exception"
        # Lock state unchanged on lokale_ausnahme path.
        assert segment.lock_flag == LockFlag.MANUAL_LOCAL

    async def test_resolve_with_glossary_change(self, db_session: AsyncSession) -> None:
        _, _, _, segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_LOCAL)
        conflict = await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )
        new_concept_id = new_uuid()

        de = await resolve_with_glossary_change(
            session=db_session,
            conflict=conflict,
            new_concept_id=new_concept_id,
        )

        assert conflict.state == ConflictState.AUFGELOEST.value
        assert conflict.resolution_type == ResolutionType.GLOSSAR_ANPASSEN.value
        assert de.content["new_concept_id"] == str(new_concept_id)
        # Lock untouched on glossary path.
        assert segment.lock_flag == LockFlag.MANUAL_LOCAL

    async def test_resolve_with_lock_release_releases_and_writes_two_decision_events(
        self, db_session: AsyncSession
    ) -> None:
        from tests.conftest import seed_account_uuid

        _, _, _, segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_EDITORIAL)
        conflict = await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )
        confirmer = new_uuid()
        await seed_account_uuid(db_session, confirmer)

        before_de = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()

        conflict_de, lock_de = await resolve_with_lock_release(
            session=db_session,
            conflict=conflict,
            segment=segment,
            confirmation=ConfirmationContext(confirmed_by=confirmer),
        )

        after_de = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()

        # Two DEs: one for the conflict resolution, one for the lock release.
        assert after_de == before_de + 2
        assert segment.lock_flag == LockFlag.NONE
        assert conflict.state == ConflictState.AUFGELOEST.value
        assert conflict.resolution_type == ResolutionType.SPERRFLAG_AUFHEBEN.value
        assert str(conflict_de.decision_source) == DecisionSource.CONFLICT_RESOLUTION.value
        assert str(lock_de.decision_source) == DecisionSource.LOCK_MANAGEMENT.value
        assert conflict_de.content["lock_release_decision_event_uuid"] == str(
            lock_de.decision_event_uuid
        )

    async def test_resolve_with_lock_release_propagates_editorial_confirmation_rule(
        self, db_session: AsyncSession
    ) -> None:
        # If the segment is manual_editorial and no confirmation context is
        # supplied, the lock-release path raises before any conflict
        # mutation. The conflict stays offen.
        _, _, _, segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_EDITORIAL)
        conflict = await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )

        with pytest.raises(LockConfirmationRequired):
            await resolve_with_lock_release(
                session=db_session,
                conflict=conflict,
                segment=segment,
            )

        # Conflict untouched.
        await db_session.refresh(conflict)
        assert conflict.state == ConflictState.OFFEN.value
        assert conflict.decision_event_uuid is None

    async def test_resolve_with_lock_release_refuses_unlocked_segment(
        self, db_session: AsyncSession
    ) -> None:
        _, _, _, segment = await _seed_segment(db_session, lock_flag=LockFlag.NONE)
        conflict = await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.KONZEPT_VS_KONZEPT,
        )

        with pytest.raises(ConflictResolutionPathInvalid):
            await resolve_with_lock_release(session=db_session, conflict=conflict, segment=segment)


@pytest.mark.asyncio
class TestT_5_1_2_DEcisionEventOnlyAtResolution:
    """Conflict-Instance-Decision-Event-Bei-Aufloesung-Test.

    Detection: decision_event_uuid is null. Resolution: decision_event_uuid
    is set. The transition is atomic (CHECK constraint
    ck_conflict_resolution_consistency)."""

    async def test_de_uuid_null_at_detection_set_at_resolution(
        self, db_session: AsyncSession
    ) -> None:
        _, _, _, segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_LOCAL)
        conflict = await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )
        assert conflict.decision_event_uuid is None

        de = await resolve_with_local_exception(session=db_session, conflict=conflict)
        assert conflict.decision_event_uuid == de.decision_event_uuid


# --- Idempotency / second-resolution refusal ----------------------------


@pytest.mark.asyncio
class TestT_5_1_2_PostResolutionImmutability:
    """Sprint 1 §2: pre-resolution row is *not* mutated after resolution
    (other than the resolution-side fields). Calling resolve_* a second
    time on an aufgeloest row must raise."""

    async def test_second_resolution_raises(self, db_session: AsyncSession) -> None:
        _, _, _, segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_LOCAL)
        conflict = await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )
        await resolve_with_local_exception(session=db_session, conflict=conflict)

        with pytest.raises(ConflictAlreadyResolved):
            await resolve_with_local_exception(session=db_session, conflict=conflict)
        with pytest.raises(ConflictAlreadyResolved):
            await resolve_with_glossary_change(
                session=db_session, conflict=conflict, new_concept_id=new_uuid()
            )


# --- Query helpers (page / project scoping) -----------------------------


@pytest.mark.asyncio
class TestT_5_1_2_QueryHelpers:
    """Open conflicts queryable per Segment, Page, Project (Sprint 1 §2)."""

    async def test_query_per_page_includes_block_segment_descendants(
        self, db_session: AsyncSession
    ) -> None:
        _, page, _, segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_LOCAL)
        await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )

        rows = await get_open_conflicts_for_page(session=db_session, page_uuid=page.page_uuid)
        assert len(rows) == 1
        assert rows[0].satz_uuid == segment.satz_uuid

    async def test_query_per_project_includes_all_descendants(
        self, db_session: AsyncSession
    ) -> None:
        project, _, _, segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_LOCAL)
        await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )
        await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.TERMINOLOGY,
            conflict_type=ConflictType.TERMINOLOGIE_VS_SPERRFLAG,
        )

        rows = await get_open_conflicts_for_project(
            session=db_session, project_uuid=project.project_uuid
        )
        assert len(rows) == 2

    async def test_resolved_conflicts_not_returned(self, db_session: AsyncSession) -> None:
        _, _, _, segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_LOCAL)
        conflict = await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )
        await resolve_with_local_exception(session=db_session, conflict=conflict)

        rows = await get_open_conflicts_for_segment(session=db_session, satz_uuid=segment.satz_uuid)
        assert rows == []


# --- Glossar-Kein-Auto-Ueberschreiben-Gesperrt-Test (T-5.2.1 cross) ----


@pytest.mark.asyncio
class TestT_5_2_1_GlossarKeinAutoUeberschreibenGesperrt:
    """Glossar-Kein-Auto-Ueberschreiben-Gesperrt-Test.

    The integration seam: a glossary-vs-locked-segment collision MUST route
    through detect_conflict and produce an offen conflict_instance, never
    silently overwrite. Sprint 1 §B / DBB Abkürzung 6 names this exact
    failure mode."""

    async def test_glossary_application_against_locked_segment_creates_open_conflict(
        self, db_session: AsyncSession
    ) -> None:
        # Set up: a segment with a manual lock, simulating what an
        # automatic glossary-application caller would encounter.
        _, _, _, segment = await _seed_segment(db_session)
        await set_lock(session=db_session, segment=segment, level=LockFlag.MANUAL_EDITORIAL)

        # The application path (Sprint 2 T-7.2.1) MUST detect-and-route. We
        # simulate it directly: the integration is "any glossary application
        # on a locked segment → detect_conflict".
        conflict = await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
            context={"attempted_concept_id": str(new_uuid())},
        )

        # Conflict_instance is the visible artifact. The lock is unchanged
        # — silent overwrite was refused.
        assert conflict.state == ConflictState.OFFEN.value
        assert segment.lock_flag == LockFlag.MANUAL_EDITORIAL
        assert conflict.rule_source == RuleSource.GLOSSARY.value
        assert conflict.conflict_type == ConflictType.GLOSSAR_VS_SPERRFLAG.value


# --- Schema discipline ---------------------------------------------------


class TestT_5_1_2_SchemaDiscipline:
    def test_conflict_instances_table_registered(self) -> None:
        from waraq.db.base import Base

        assert "conflict_instances" in Base.metadata.tables

    def test_conflict_instances_has_satz_uuid_fk(self) -> None:
        col = ConflictInstance.__table__.columns["satz_uuid"]
        assert col.nullable is False
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert fk_targets == {"segments.satz_uuid"}

    def test_conflict_instances_has_decision_event_uuid_nullable_fk(self) -> None:
        col = ConflictInstance.__table__.columns["decision_event_uuid"]
        assert col.nullable is True
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert fk_targets == {"decision_events.decision_event_uuid"}

    def test_no_conflict_instance_po_type_in_canonical_enum(self) -> None:
        # HG-S1-6 surface check: POType must not have been extended to
        # include CONFLICT_INSTANCE. The conflict service's resolution path
        # also asserts (by construction) that no PO is written.
        assert "CONFLICT_INSTANCE" not in {p.name for p in POType}
        assert "conflict_instance" not in {p.value for p in POType}
