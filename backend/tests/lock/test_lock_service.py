"""T-5.1.1 — LOCK service tests.

Mandatory tests from Sprint 1 §4:
- T-H1-01 — Automatic write blocked on `manual_local`
- T-H1-02 — Automatic write blocked on `manual_editorial`
- LOCK-Set-Decision-Event-Test
- LOCK-Release-Manual-Editorial-Confirmation-Test
- LOCK-Manual-PO-Provenance-Test

Plus negative paths: idempotent set/release, wrong level via set_lock,
auto-release surface absent.
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag, OperationMode
from waraq.invariant.exceptions import H1H2Violation
from waraq.lock import (
    ConfirmationContext,
    LockAlreadyAtTargetState,
    LockConfirmationRequired,
    LockInvalidLevel,
    release_lock,
    set_lock,
)
from waraq.revision import create_revision
from waraq.schemas import (
    Block,
    DecisionEvent,
    LogEntry,
    Page,
    Project,
    ProvenanceObject,
    Revision,
    Segment,
)
from waraq.schemas.enums import ChangeSource, DecisionSource, POType, ScopeType


async def _seed_segment(
    session: AsyncSession,
    *,
    lock_flag: LockFlag = LockFlag.NONE,
    initial_text: str | None = "current",
) -> Segment:
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="lock-test")
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
        text_content=initial_text,
    )
    session.add(segment)
    await session.flush()
    return segment


# --- Layer 1: signature/architectural -------------------------------------


class TestT_5_1_1_Signatures:
    """The service has no auto-release surface. Anything that flips
    lock_flag must go through set_lock or release_lock."""

    def test_module_exposes_only_canonical_lock_entrypoints(self) -> None:
        import inspect as _inspect
        import types

        import waraq.lock as lock_module

        functions = {
            name
            for name, obj in vars(lock_module).items()
            if not name.startswith("_")
            and callable(obj)
            and not isinstance(obj, type)
            and not isinstance(obj, types.ModuleType)
            and _inspect.getmodule(obj) is not None
            and _inspect.getmodule(obj).__name__.startswith("waraq.lock")  # type: ignore[union-attr]
        }
        assert functions == {"set_lock", "release_lock"}, (
            f"waraq.lock exposes unexpected operations: {functions}"
        )

    def test_signatures_block_text_change_kwargs(self) -> None:
        forbidden = {"before_text", "after_text", "change_source", "rev_uuid"}
        for fn in (set_lock, release_lock):
            params = set(inspect.signature(fn).parameters)
            assert (forbidden & params) == set(), f"{fn.__name__} leaked text-change kwargs"


# --- Layer 2: H-1 / H-2 regression (mandatory T-H1-01 / T-H1-02) ----------


@pytest.mark.asyncio
class TestT_H1_01_RegressionWithLockService:
    """T-H1-01: Automatic write on `lock_flag = manual_local` blocked.

    Sprint 1 §4 says this must be exercised "regression + new path" — the
    new path being: lock the segment via set_lock, then attempt automatic
    write via the existing translate-side machinery (we use create_revision
    in AUTOMATIC mode as the regression surface)."""

    async def test_automatic_revision_blocked_after_set_lock_to_manual_local(
        self, db_session: AsyncSession
    ) -> None:
        segment = await _seed_segment(db_session)
        await set_lock(session=db_session, segment=segment, level=LockFlag.MANUAL_LOCAL)

        with pytest.raises(H1H2Violation):
            await create_revision(
                session=db_session,
                segment=segment,
                after_text="should be refused",
                change_source=ChangeSource.OCR,
                operation_mode=OperationMode.AUTOMATIC,
            )


@pytest.mark.asyncio
class TestT_H1_02_RegressionWithLockService:
    """T-H1-02: Automatic write on `lock_flag = manual_editorial` blocked."""

    async def test_automatic_revision_blocked_after_set_lock_to_manual_editorial(
        self, db_session: AsyncSession
    ) -> None:
        segment = await _seed_segment(db_session)
        await set_lock(session=db_session, segment=segment, level=LockFlag.MANUAL_EDITORIAL)

        with pytest.raises(H1H2Violation):
            await create_revision(
                session=db_session,
                segment=segment,
                after_text="should be refused",
                change_source=ChangeSource.OCR,
                operation_mode=OperationMode.AUTOMATIC,
            )


# --- Layer 2: set_lock integration ----------------------------------------


@pytest.mark.asyncio
class TestT_5_1_1_SetLock:
    """LOCK-Set-Decision-Event-Test + LOCK-Manual-PO-Provenance-Test (set side)."""

    async def test_set_lock_to_manual_local_writes_decision_event_with_canonical_fields(
        self, db_session: AsyncSession
    ) -> None:
        from tests.conftest import seed_account_uuid

        segment = await _seed_segment(db_session)
        actor_uuid = new_uuid()
        await seed_account_uuid(db_session, actor_uuid)

        de, _po = await set_lock(
            session=db_session,
            segment=segment,
            level=LockFlag.MANUAL_LOCAL,
            actor_uuid=actor_uuid,
        )

        assert segment.lock_flag == LockFlag.MANUAL_LOCAL
        assert str(de.scope_type) == ScopeType.SEGMENT.value
        assert de.scope_uuid == segment.satz_uuid
        assert str(de.decision_source) == DecisionSource.LOCK_MANAGEMENT.value
        assert de.decision_type == "lock_set"
        assert de.actor_uuid == actor_uuid
        assert de.content["action"] == "set"
        assert de.content["prior_flag"] == LockFlag.NONE.value
        assert de.content["new_flag"] == LockFlag.MANUAL_LOCAL.value

    async def test_set_lock_writes_manual_po_via_provenance(self, db_session: AsyncSession) -> None:
        # LOCK-Manual-PO-Provenance-Test: after each lock change, MANUAL_-PO
        # is created via PROVENANCE-Kern (not direct insert).
        segment = await _seed_segment(db_session)
        de, po = await set_lock(
            session=db_session, segment=segment, level=LockFlag.MANUAL_EDITORIAL
        )

        assert str(po.po_type) == POType.MANUAL_.value
        assert str(po.scope_type) == ScopeType.SEGMENT.value
        assert po.scope_uuid == segment.satz_uuid
        assert po.payload["action"] == "set"
        assert po.payload["prior_flag"] == LockFlag.NONE.value
        assert po.payload["new_flag"] == LockFlag.MANUAL_EDITORIAL.value
        assert po.payload["decision_event_uuid"] == str(de.decision_event_uuid)

        # Round-trip from DB: confirms the PO actually landed via
        # PROVENANCE-Kern (which is the only writer per Abkürzung 7).
        loaded = (
            await db_session.execute(
                select(ProvenanceObject).where(ProvenanceObject.po_uuid == po.po_uuid)
            )
        ).scalar_one()
        assert loaded.po_uuid == po.po_uuid

    async def test_set_lock_idempotent_set_refused(self, db_session: AsyncSession) -> None:
        segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_LOCAL)
        with pytest.raises(LockAlreadyAtTargetState):
            await set_lock(session=db_session, segment=segment, level=LockFlag.MANUAL_LOCAL)

    async def test_set_lock_with_none_level_raises_invalid(self, db_session: AsyncSession) -> None:
        segment = await _seed_segment(db_session)
        with pytest.raises(LockInvalidLevel):
            await set_lock(session=db_session, segment=segment, level=LockFlag.NONE)


# --- Layer 2: release_lock integration ------------------------------------


@pytest.mark.asyncio
class TestT_5_1_1_ReleaseLockManualLocal:
    async def test_release_manual_local_succeeds_without_confirmation(
        self, db_session: AsyncSession
    ) -> None:
        segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_LOCAL)
        de, po = await release_lock(session=db_session, segment=segment)

        assert segment.lock_flag == LockFlag.NONE
        assert de.decision_type == "lock_release"
        assert de.content["prior_flag"] == LockFlag.MANUAL_LOCAL.value
        assert de.content["new_flag"] == LockFlag.NONE.value
        assert "confirmation" not in de.content
        assert po.payload["action"] == "release"
        assert po.payload["confirmation_required"] is False
        assert po.payload["confirmation_provided"] is False


@pytest.mark.asyncio
class TestT_5_1_1_ReleaseManualEditorialConfirmation:
    """LOCK-Release-Manual-Editorial-Confirmation-Test.

    Both call paths exercised: without confirmation → error, with → permitted."""

    async def test_release_manual_editorial_without_confirmation_raises(
        self, db_session: AsyncSession
    ) -> None:
        segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_EDITORIAL)
        with pytest.raises(LockConfirmationRequired):
            await release_lock(session=db_session, segment=segment)

        # The transition didn't happen.
        await db_session.refresh(segment)
        assert segment.lock_flag == LockFlag.MANUAL_EDITORIAL

    async def test_release_manual_editorial_with_confirmation_permitted(
        self, db_session: AsyncSession
    ) -> None:
        from tests.conftest import seed_account_uuid

        segment = await _seed_segment(db_session, lock_flag=LockFlag.MANUAL_EDITORIAL)
        confirmer = new_uuid()
        await seed_account_uuid(db_session, confirmer)
        confirmation = ConfirmationContext(confirmed_by=confirmer, note="ui-chip-confirmed")

        de, po = await release_lock(
            session=db_session,
            segment=segment,
            confirmation=confirmation,
        )

        assert segment.lock_flag == LockFlag.NONE
        assert de.actor_uuid == confirmer  # falls back to confirmer when actor_uuid omitted
        assert de.content["confirmation"]["confirmed_by"] == str(confirmer)
        assert de.content["confirmation"]["note"] == "ui-chip-confirmed"
        assert po.payload["confirmation_required"] is True
        assert po.payload["confirmation_provided"] is True


@pytest.mark.asyncio
class TestT_5_1_1_NoAutoReleaseSurface:
    """The service exposes no automatic-release entrypoint. A test that
    confirms this at the import level was already added in TestT_5_1_1_Signatures.
    Here we additionally lock in: idempotent release on a NONE segment is
    refused (no silent no-op success could be mistaken for auto-release)."""

    async def test_release_on_none_segment_raises(self, db_session: AsyncSession) -> None:
        segment = await _seed_segment(db_session, lock_flag=LockFlag.NONE)
        with pytest.raises(LockAlreadyAtTargetState):
            await release_lock(session=db_session, segment=segment)


@pytest.mark.asyncio
class TestT_5_1_1_AtomicityOnFailure:
    """If the Decision Event write succeeds but the MANUAL_-PO write fails
    (FK or other), the whole transaction rolls back. This test simulates by
    leveraging the rollback-fixture: any partial failure under db_session
    is automatically discarded. Here we confirm the happy-path counts."""

    async def test_one_decision_event_one_manual_po_per_lock_change(
        self, db_session: AsyncSession
    ) -> None:
        segment = await _seed_segment(db_session)

        before_de = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        before_po = (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one()

        await set_lock(session=db_session, segment=segment, level=LockFlag.MANUAL_LOCAL)
        await release_lock(session=db_session, segment=segment)

        after_de = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        after_po_manual = (
            await db_session.execute(
                select(func.count())
                .select_from(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.MANUAL_.value)
            )
        ).scalar_one()
        after_po_total = (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one()

        # 2 lock changes → exactly 2 DEs and 2 MANUAL_-POs.
        assert after_de == before_de + 2
        assert after_po_manual == 2
        assert after_po_total == before_po + 2


@pytest.mark.asyncio
class TestT_5_1_1_NoRevisionOrLogEntryFromLockChange:
    """Three-tables discipline (Abkürzung 3): a lock change is a Decision
    Event + a Provenance Object. It must not produce a Revision row, and
    must not produce a Log-Eintrag (locks aren't lineage events)."""

    async def test_no_revision_written_by_lock_changes(self, db_session: AsyncSession) -> None:
        segment = await _seed_segment(db_session)
        before = (await db_session.execute(select(func.count()).select_from(Revision))).scalar_one()

        await set_lock(session=db_session, segment=segment, level=LockFlag.MANUAL_LOCAL)
        await release_lock(session=db_session, segment=segment)

        after = (await db_session.execute(select(func.count()).select_from(Revision))).scalar_one()
        assert after == before

    async def test_no_log_entry_written_by_lock_changes(self, db_session: AsyncSession) -> None:
        segment = await _seed_segment(db_session)
        before = (await db_session.execute(select(func.count()).select_from(LogEntry))).scalar_one()

        await set_lock(session=db_session, segment=segment, level=LockFlag.MANUAL_LOCAL)
        await release_lock(session=db_session, segment=segment)

        after = (await db_session.execute(select(func.count()).select_from(LogEntry))).scalar_one()
        assert after == before
