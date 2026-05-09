"""T-6.1.1 — Release gate tests.

Mandatory tests from Sprint 2 §4:
- Gate-Test-Blockiert-No-Go-Test
- Gate-Test-F06-QR-Blockierung-Test
- Gate-Test-Offene-Conflict-Instance-Blockierung-Test
- Gate-Test-Glossar-Orphan-Blockierung-Test  (vacuous-pass at v1.0; future
  expansion exercised when RULE_BINDING-PO orphans become possible)
- Gate-Test-Alles-Erfuellt-Uebersetzungsreif-Test
- Gate-Test-Mit-Warnung-Erfordert-Bestaetigung-Test
- Gate-Test-Kein-Auto-Translation-Start-Test (HG-S2-2 / DBB Abkürzung 5)
- Gate-Test-Live-State-Test
- Gate-Test-Log-Eintrag-Immer-Test
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.conflicts import (
    ConflictType,
    RuleSource,
    detect_conflict,
    resolve_with_local_exception,
)
from waraq.identity import new_uuid
from waraq.invariant.enums import LockFlag
from waraq.ocr.error_classes import OcrErrorClass
from waraq.ocr.review import (
    apply_findings_to_status,
    enter_in_review,
    make_default_severity_weights,
    record_ocr_error_instance,
    resolve_no_go_to_go,
    resolve_ocr_error_instance,
)
from waraq.release_gate import (
    GateNotInWarningState,
    GateNotReady,
    GateState,
    confirm_translation_with_warning,
    evaluate_gate,
    start_translation,
)
from waraq.schemas import Block, DecisionEvent, LogEntry, Page, Project, Segment
from waraq.schemas.enums import DecisionSource, OcrStatus, ScopeType


async def _seed_project_with_one_page(
    session: AsyncSession,
) -> tuple[Project, Page, Block, Segment]:
    """Project + page + block + segment chain with `ocr_status=GO` (clean
    state). Tests opt into degraded states by writing additional rows."""
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="release-gate-test")
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
        lock_flag=LockFlag.NONE,
        text_content="some text",
    )
    session.add(segment)
    await session.flush()
    return project, page, block, segment


# --- Mandatory: blocked-by-no-go --------------------------------------


@pytest.mark.asyncio
class TestGateBlockiertNoGo:
    """Gate-Test-Blockiert-No-Go-Test."""

    async def test_no_go_page_blocks_gate(self, db_session: AsyncSession) -> None:
        project, page, _, _ = await _seed_project_with_one_page(db_session)
        # Drive page to NO_GO via real review path.
        weights = make_default_severity_weights()
        await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_01,  # kritisch
        )
        await enter_in_review(session=db_session, page=page)
        await apply_findings_to_status(session=db_session, page=page, weights=weights)
        assert page.ocr_status == OcrStatus.NO_GO

        result = await evaluate_gate(session=db_session, project_uuid=project.project_uuid)

        assert result.state == GateState.BLOCKIERT
        assert any("ocr_status=no_go" in r for r in result.blocking_reasons)


# --- Mandatory: F-06-QR blocks ----------------------------------------


@pytest.mark.asyncio
class TestGateF06QRBlockierung:
    """Gate-Test-F06-QR-Blockierung-Test."""

    async def test_open_f_06_qr_blocks_gate(self, db_session: AsyncSession) -> None:
        project, page, _, _ = await _seed_project_with_one_page(db_session)
        # F-06-QR detection writer is M5; we insert directly to exercise
        # the gate read path. The CHECK constraint accepts F-06-QR after
        # migration 0012.
        await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_06_QR,
        )

        result = await evaluate_gate(session=db_session, project_uuid=project.project_uuid)
        assert result.state == GateState.BLOCKIERT
        assert any("F-06-QR" in r for r in result.blocking_reasons)

    async def test_resolved_f_06_qr_does_not_block(self, db_session: AsyncSession) -> None:
        project, page, _, _ = await _seed_project_with_one_page(db_session)
        instance = await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_06_QR,
        )
        await resolve_ocr_error_instance(session=db_session, instance=instance)

        result = await evaluate_gate(session=db_session, project_uuid=project.project_uuid)
        # No F-06-QR contribution; page is GO; clean.
        assert result.state == GateState.UEBERSETZUNGSREIF


# --- Mandatory: open conflict_instance blocks ------------------------


@pytest.mark.asyncio
class TestGateOffeneConflictInstance:
    """Gate-Test-Offene-Conflict-Instance-Blockierung-Test."""

    async def test_open_conflict_blocks_gate(self, db_session: AsyncSession) -> None:
        project, _, _, segment = await _seed_project_with_one_page(db_session)
        await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )

        result = await evaluate_gate(session=db_session, project_uuid=project.project_uuid)
        assert result.state == GateState.BLOCKIERT
        assert any("conflict_instance" in r for r in result.blocking_reasons)

    async def test_resolved_conflict_does_not_block(self, db_session: AsyncSession) -> None:
        project, _, _, segment = await _seed_project_with_one_page(db_session)
        conflict = await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )
        await resolve_with_local_exception(session=db_session, conflict=conflict)

        result = await evaluate_gate(session=db_session, project_uuid=project.project_uuid)
        assert result.state == GateState.UEBERSETZUNGSREIF


# --- Mandatory: glossary integrity (vacuous-pass at v1.0) ------------


@pytest.mark.asyncio
class TestGateGlossarOrphan:
    """Gate-Test-Glossar-Orphan-Blockierung-Test.

    At v1.0 schema there is no separate reference structure that could
    orphan against Concept. The gate condition is a structural pass:
    when no orphans exist (the only case currently possible), the gate
    does NOT block on this condition. The check exists so the gate is
    structurally complete; M5 RULE_BINDING-PO work extends the body."""

    async def test_clean_state_does_not_block_via_orphan(self, db_session: AsyncSession) -> None:
        project, _, _, _ = await _seed_project_with_one_page(db_session)
        result = await evaluate_gate(session=db_session, project_uuid=project.project_uuid)
        # Clean project: no orphan-blocking reason in the result.
        assert not any("orphan" in r.lower() for r in result.blocking_reasons)


# --- Mandatory: alles erfüllt → uebersetzungsreif --------------------


@pytest.mark.asyncio
class TestGateAllesErfuelltUebersetzungsreif:
    """Gate-Test-Alles-Erfuellt-Uebersetzungsreif-Test."""

    async def test_clean_project_reaches_uebersetzungsreif(self, db_session: AsyncSession) -> None:
        project, _, _, _ = await _seed_project_with_one_page(db_session)
        result = await evaluate_gate(session=db_session, project_uuid=project.project_uuid)
        assert result.state == GateState.UEBERSETZUNGSREIF
        assert result.blocking_reasons == []
        assert result.warnings == []


# --- Mandatory: warning requires confirmation ------------------------


@pytest.mark.asyncio
class TestGateMitWarnungErfordertBestaetigung:
    """Gate-Test-Mit-Warnung-Erfordert-Bestaetigung-Test (two cases)."""

    async def test_warning_without_confirmation_stays_blockiert(
        self, db_session: AsyncSession
    ) -> None:
        project, page, _, _ = await _seed_project_with_one_page(db_session)
        # Drive page to GO_WITH_WARNING via real review path.
        weights = make_default_severity_weights()
        await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_03,  # hoch in default weights
        )
        await enter_in_review(session=db_session, page=page)
        await apply_findings_to_status(session=db_session, page=page, weights=weights)
        assert page.ocr_status == OcrStatus.GO_WITH_WARNING

        result = await evaluate_gate(session=db_session, project_uuid=project.project_uuid)
        assert result.state == GateState.BLOCKIERT
        assert any(
            "freigabe_mit_warnung confirmation required" in r for r in result.blocking_reasons
        )

    async def test_warning_with_confirmation_yields_uebersetzbar_mit_warnung(
        self, db_session: AsyncSession
    ) -> None:
        project, page, _, _ = await _seed_project_with_one_page(db_session)
        weights = make_default_severity_weights()
        await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_03,
        )
        await enter_in_review(session=db_session, page=page)
        await apply_findings_to_status(session=db_session, page=page, weights=weights)

        de = await confirm_translation_with_warning(
            session=db_session, project_uuid=project.project_uuid
        )

        result = await evaluate_gate(session=db_session, project_uuid=project.project_uuid)
        assert result.state == GateState.UEBERSETZBAR_MIT_WARNUNG
        assert de.decision_type == "freigabe_mit_warnung"
        assert str(de.scope_type) == ScopeType.PROJECT.value
        assert de.scope_uuid == project.project_uuid
        assert str(de.decision_source) == DecisionSource.PREFLIGHT_CONFIRMATION.value

    async def test_confirm_refuses_when_uebersetzungsreif(self, db_session: AsyncSession) -> None:
        # Clean project — no warnings to confirm.
        project, _, _, _ = await _seed_project_with_one_page(db_session)
        with pytest.raises(GateNotInWarningState):
            await confirm_translation_with_warning(
                session=db_session, project_uuid=project.project_uuid
            )

    async def test_confirm_refuses_when_hard_blocked(self, db_session: AsyncSession) -> None:
        # Page in NO_GO — hard block, warnings confirmation irrelevant.
        project, page, _, _ = await _seed_project_with_one_page(db_session)
        weights = make_default_severity_weights()
        await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_01,
        )
        await enter_in_review(session=db_session, page=page)
        await apply_findings_to_status(session=db_session, page=page, weights=weights)

        with pytest.raises(GateNotInWarningState):
            await confirm_translation_with_warning(
                session=db_session, project_uuid=project.project_uuid
            )


# --- Mandatory: kein auto-translation-start (HG-S2-2 / Abkürzung 5) -


@pytest.mark.asyncio
class TestGateKeinAutoTranslationStart:
    """Gate-Test-Kein-Auto-Translation-Start-Test.

    Reaching uebersetzungsreif must NOT by itself create a translation
    Job or a `uebersetzungsstart` Decision Event. Only `start_translation`
    creates the DE."""

    async def test_evaluate_gate_creates_no_uebersetzungsstart_de(
        self, db_session: AsyncSession
    ) -> None:
        project, _, _, _ = await _seed_project_with_one_page(db_session)
        before = (
            await db_session.execute(
                select(func.count())
                .select_from(DecisionEvent)
                .where(DecisionEvent.decision_type == "uebersetzungsstart")
            )
        ).scalar_one()

        result = await evaluate_gate(session=db_session, project_uuid=project.project_uuid)
        assert result.state == GateState.UEBERSETZUNGSREIF

        after = (
            await db_session.execute(
                select(func.count())
                .select_from(DecisionEvent)
                .where(DecisionEvent.decision_type == "uebersetzungsstart")
            )
        ).scalar_one()
        assert after == before  # no auto-DE.

    async def test_start_translation_writes_uebersetzungsstart_de(
        self, db_session: AsyncSession
    ) -> None:
        project, _, _, _ = await _seed_project_with_one_page(db_session)
        de = await start_translation(session=db_session, project_uuid=project.project_uuid)
        assert de.decision_type == "uebersetzungsstart"
        assert str(de.decision_source) == DecisionSource.TRANSLATION_PIPELINE.value

    async def test_start_translation_refuses_when_blockiert(self, db_session: AsyncSession) -> None:
        project, page, _, _ = await _seed_project_with_one_page(db_session)
        weights = make_default_severity_weights()
        await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_01,
        )
        await enter_in_review(session=db_session, page=page)
        await apply_findings_to_status(session=db_session, page=page, weights=weights)

        with pytest.raises(GateNotReady):
            await start_translation(session=db_session, project_uuid=project.project_uuid)

    async def test_start_translation_permitted_after_warning_confirmation(
        self, db_session: AsyncSession
    ) -> None:
        project, page, _, _ = await _seed_project_with_one_page(db_session)
        weights = make_default_severity_weights()
        await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_03,
        )
        await enter_in_review(session=db_session, page=page)
        await apply_findings_to_status(session=db_session, page=page, weights=weights)

        await confirm_translation_with_warning(
            session=db_session, project_uuid=project.project_uuid
        )
        de = await start_translation(session=db_session, project_uuid=project.project_uuid)
        assert de.content["gate_state_at_start"] == GateState.UEBERSETZBAR_MIT_WARNUNG.value


# --- Mandatory: live state ------------------------------------------


@pytest.mark.asyncio
class TestGateLiveState:
    """Gate-Test-Live-State-Test.

    Two evaluations across a state-changing action read fresh state."""

    async def test_resolving_blocker_changes_gate_state(self, db_session: AsyncSession) -> None:
        project, _, _, segment = await _seed_project_with_one_page(db_session)
        conflict = await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )

        first = await evaluate_gate(session=db_session, project_uuid=project.project_uuid)
        assert first.state == GateState.BLOCKIERT

        await resolve_with_local_exception(session=db_session, conflict=conflict)

        second = await evaluate_gate(session=db_session, project_uuid=project.project_uuid)
        assert second.state == GateState.UEBERSETZUNGSREIF


# --- Mandatory: log-eintrag immer -----------------------------------


@pytest.mark.asyncio
class TestGateLogEintragImmer:
    """Gate-Test-Log-Eintrag-Immer-Test."""

    async def test_every_evaluation_writes_log_entry(self, db_session: AsyncSession) -> None:
        project, _page, _, segment = await _seed_project_with_one_page(db_session)

        # Three different outcomes.
        # 1. uebersetzungsreif (clean state)
        # 2. blockiert (open conflict)
        # 3. uebersetzungsreif again (conflict resolved)
        before = (
            await db_session.execute(
                select(func.count())
                .select_from(LogEntry)
                .where(LogEntry.operation_type == "release_gate_evaluated")
            )
        ).scalar_one()

        await evaluate_gate(session=db_session, project_uuid=project.project_uuid)

        conflict = await detect_conflict(
            session=db_session,
            segment=segment,
            rule_source=RuleSource.GLOSSARY,
            conflict_type=ConflictType.GLOSSAR_VS_SPERRFLAG,
        )
        await evaluate_gate(session=db_session, project_uuid=project.project_uuid)

        await resolve_with_local_exception(session=db_session, conflict=conflict)
        await evaluate_gate(session=db_session, project_uuid=project.project_uuid)

        after = (
            await db_session.execute(
                select(func.count())
                .select_from(LogEntry)
                .where(LogEntry.operation_type == "release_gate_evaluated")
            )
        ).scalar_one()
        assert after == before + 3


# --- Resolution flow: NO_GO → user resolution → uebersetzungsreif --


@pytest.mark.asyncio
class TestGateUnblocksAfterUserResolution:
    """End-to-end: a blocked gate clears after the user resolves all
    findings via the canonical user-action paths."""

    async def test_no_go_to_uebersetzungsreif_via_user_resolution(
        self, db_session: AsyncSession
    ) -> None:
        from tests.conftest import seed_account_uuid

        project, page, _, _ = await _seed_project_with_one_page(db_session)
        weights = make_default_severity_weights()
        instance = await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_01,
        )
        await enter_in_review(session=db_session, page=page)
        await apply_findings_to_status(session=db_session, page=page, weights=weights)

        # Gate blockiert.
        result = await evaluate_gate(session=db_session, project_uuid=project.project_uuid)
        assert result.state == GateState.BLOCKIERT

        # User resolves the underlying error and explicitly clears no_go.
        await resolve_ocr_error_instance(session=db_session, instance=instance)
        actor = new_uuid()
        await seed_account_uuid(db_session, actor)
        await resolve_no_go_to_go(session=db_session, page=page, actor_uuid=actor)

        # Gate now uebersetzungsreif.
        result = await evaluate_gate(session=db_session, project_uuid=project.project_uuid)
        assert result.state == GateState.UEBERSETZUNGSREIF


# --- Schema sanity ---------------------------------------------------


class TestGateSchemaSanity:
    def test_f_06_qr_in_canonical_enum(self) -> None:
        assert OcrErrorClass.F_06_QR.value == "F-06-QR"
