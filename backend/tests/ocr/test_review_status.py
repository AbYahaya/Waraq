"""T-4.3.1 — OCR review status per page.

Five mandatory tests from Sprint 1 §4 plus aggregator-purity, state-machine,
and config-driven-severity coverage.

Mandatory (sprint plan):
- OCR-Review-Status-Kritisch-No-Go-Test
- OCR-Review-Status-Mittel-Go-With-Warning-Test
- OCR-Review-Status-Alle-Aufgeloest-Go-Test
- OCR-Review-Status-Schwellenwert-Konfigurations-Test
- OCR-Review-Status-Kein-Auto-Go-Test
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.ocr.error_classes import OcrErrorClass
from waraq.ocr.review import (
    SeverityWeights,
    apply_findings_to_status,
    derive_status_from_codes,
    enter_in_review,
    make_default_severity_weights,
    record_ocr_error_instance,
    resolve_no_go_to_go,
    resolve_ocr_error_instance,
)
from waraq.schemas import Block, DecisionEvent, OcrErrorInstance, Page, Project
from waraq.schemas.enums import (
    DecisionSource,
    OcrErrorState,
    OcrSeverity,
    OcrStatus,
    ScopeType,
)


async def _seed_page(session: AsyncSession) -> Page:
    """Insert account → project → page; return the page."""
    from tests.conftest import seed_account_uuid

    account_uuid = new_uuid()
    await seed_account_uuid(session, account_uuid)

    project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="ocr-review")
    session.add(project)
    await session.flush()

    page = Page(page_uuid=new_uuid(), project_uuid=project.project_uuid, page_index=1)
    session.add(page)
    await session.flush()
    return page


# --- Aggregator (pure) ----------------------------------------------------


class TestT_4_3_1_DerivedStatus:
    """`derive_status_from_codes` is pure: no DB, no side effects. Exercises
    all three derivable end-states."""

    def test_no_open_codes_yields_go(self) -> None:
        weights = make_default_severity_weights()
        assert derive_status_from_codes([], weights=weights) == OcrStatus.GO

    def test_any_kritisch_yields_no_go(self) -> None:
        # Build a config where F-01 is kritisch.
        weights = SeverityWeights(
            weights={
                OcrErrorClass.F_01: OcrSeverity.KRITISCH,
                OcrErrorClass.F_02: OcrSeverity.MITTEL,
                OcrErrorClass.F_03: OcrSeverity.MITTEL,
                OcrErrorClass.F_04: OcrSeverity.MITTEL,
                OcrErrorClass.F_05: OcrSeverity.MITTEL,
                OcrErrorClass.F_06: OcrSeverity.MITTEL,
                OcrErrorClass.F_07: OcrSeverity.MITTEL,
                OcrErrorClass.F_08: OcrSeverity.MITTEL,
                OcrErrorClass.F_09: OcrSeverity.MITTEL,
                OcrErrorClass.F_06_QR: OcrSeverity.MITTEL,
            }
        )
        # F-01 (kritisch) wins even with mittel companions.
        result = derive_status_from_codes([OcrErrorClass.F_01, OcrErrorClass.F_02], weights=weights)
        assert result == OcrStatus.NO_GO

    def test_only_hoch_or_mittel_yields_go_with_warning(self) -> None:
        weights = make_default_severity_weights()
        # F-04 is mittel in default weights. F-03 is hoch.
        result = derive_status_from_codes([OcrErrorClass.F_04, OcrErrorClass.F_03], weights=weights)
        assert result == OcrStatus.GO_WITH_WARNING

    def test_severity_weights_must_cover_all_codes(self) -> None:
        # R-S1-04: half-configured tables silently mis-aggregate. The
        # SeverityWeights constructor refuses partial mappings.
        with pytest.raises(ValueError, match="missing entries"):
            SeverityWeights(
                weights={OcrErrorClass.F_01: OcrSeverity.KRITISCH}  # missing F-02..F-09
            )


# --- Mandatory: configurable severity (R-S1-04) ---------------------------


class TestT_4_3_1_SchwellenwertKonfigurations:
    """OCR-Review-Status-Schwellenwert-Konfigurations-Test.

    Same input codes; flipping the config flips the derived status. If
    severities were hard-coded this test would be impossible to pass."""

    def test_same_codes_different_weights_yield_different_status(self) -> None:
        codes = [OcrErrorClass.F_06]

        all_mittel = SeverityWeights(weights=dict.fromkeys(OcrErrorClass, OcrSeverity.MITTEL))
        f06_kritisch = SeverityWeights(
            weights={
                **dict.fromkeys(OcrErrorClass, OcrSeverity.MITTEL),
                OcrErrorClass.F_06: OcrSeverity.KRITISCH,
            }
        )

        assert derive_status_from_codes(codes, weights=all_mittel) == OcrStatus.GO_WITH_WARNING
        assert derive_status_from_codes(codes, weights=f06_kritisch) == OcrStatus.NO_GO


# --- Mandatory: integration through the state machine --------------------


@pytest.mark.asyncio
class TestT_4_3_1_KritischNoGo:
    """OCR-Review-Status-Kritisch-No-Go-Test."""

    async def test_open_kritisch_drives_page_to_no_go(self, db_session: AsyncSession) -> None:
        page = await _seed_page(db_session)
        weights = make_default_severity_weights()
        # F-01 is kritisch in the default weights.
        await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_01,
        )

        await enter_in_review(session=db_session, page=page)
        result = await apply_findings_to_status(session=db_session, page=page, weights=weights)

        assert result == OcrStatus.NO_GO
        await db_session.refresh(page)
        assert page.ocr_status == OcrStatus.NO_GO


@pytest.mark.asyncio
class TestT_4_3_1_MittelGoWithWarning:
    """OCR-Review-Status-Mittel-Go-With-Warning-Test."""

    async def test_only_hoch_or_mittel_drives_page_to_go_with_warning(
        self, db_session: AsyncSession
    ) -> None:
        page = await _seed_page(db_session)
        weights = make_default_severity_weights()
        # F-04 is mittel; F-03 is hoch. No kritisch.
        await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_04,
        )
        await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_03,
        )

        await enter_in_review(session=db_session, page=page)
        result = await apply_findings_to_status(session=db_session, page=page, weights=weights)

        assert result == OcrStatus.GO_WITH_WARNING


@pytest.mark.asyncio
class TestT_4_3_1_KeinAutoGo:
    """OCR-Review-Status-Kein-Auto-Go-Test.

    Resolving every error instance does **not** flip the page from no_go to
    go. Only an explicit user-resolution Decision Event with scope_type=page
    can do that. R-S1-05 prevents the auto-go regression downstream."""

    async def test_resolving_all_errors_does_not_auto_clear_no_go(
        self, db_session: AsyncSession
    ) -> None:
        page = await _seed_page(db_session)
        weights = make_default_severity_weights()
        # Build a no-go state.
        instance = await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_01,  # kritisch
        )
        await enter_in_review(session=db_session, page=page)
        await apply_findings_to_status(session=db_session, page=page, weights=weights)
        assert page.ocr_status == OcrStatus.NO_GO

        # User resolves every error instance — but never issues a Decision Event.
        await resolve_ocr_error_instance(session=db_session, instance=instance)

        # Re-applying findings: derived would be GO, but the auto-go guard
        # refuses because the page had findings.
        await enter_in_review(session=db_session, page=page)
        result = await apply_findings_to_status(session=db_session, page=page, weights=weights)

        # Page stays in IN_REVIEW (not GO) — must route through resolve_no_go_to_go.
        assert result != OcrStatus.GO
        await db_session.refresh(page)
        assert page.ocr_status != OcrStatus.GO

    async def test_no_decision_event_written_during_findings_application(
        self, db_session: AsyncSession
    ) -> None:
        page = await _seed_page(db_session)
        weights = make_default_severity_weights()
        await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_01,
        )
        before = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()

        await enter_in_review(session=db_session, page=page)
        await apply_findings_to_status(session=db_session, page=page, weights=weights)

        after = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        assert after == before


@pytest.mark.asyncio
class TestT_4_3_1_AlleAufgeloestGo:
    """OCR-Review-Status-Alle-Aufgeloest-Go-Test.

    Full happy-path: errors → no_go → resolve every error → user issues the
    explicit resolution → page = go AND a Decision Event with
    scope_type=page exists."""

    async def test_full_resolution_yields_go_and_decision_event(
        self, db_session: AsyncSession
    ) -> None:
        from tests.conftest import seed_account_uuid

        page = await _seed_page(db_session)
        weights = make_default_severity_weights()

        instance = await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_01,
        )
        await enter_in_review(session=db_session, page=page)
        await apply_findings_to_status(session=db_session, page=page, weights=weights)
        await resolve_ocr_error_instance(session=db_session, instance=instance)

        actor_uuid = new_uuid()
        await seed_account_uuid(db_session, actor_uuid)

        de = await resolve_no_go_to_go(session=db_session, page=page, actor_uuid=actor_uuid)

        await db_session.refresh(page)
        assert page.ocr_status == OcrStatus.GO
        assert str(de.scope_type) == ScopeType.PAGE.value
        assert de.scope_uuid == page.page_uuid
        assert str(de.decision_source) == DecisionSource.OCR_REVIEW.value
        assert de.decision_type == "ocr_review_no_go_to_go"
        assert de.actor_uuid == actor_uuid

    async def test_resolve_no_go_to_go_refuses_when_open_errors_remain(
        self, db_session: AsyncSession
    ) -> None:
        page = await _seed_page(db_session)
        weights = make_default_severity_weights()
        await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_01,
        )
        await enter_in_review(session=db_session, page=page)
        await apply_findings_to_status(session=db_session, page=page, weights=weights)

        with pytest.raises(ValueError, match="unresolved error instances"):
            await resolve_no_go_to_go(session=db_session, page=page)

    async def test_resolve_no_go_to_go_refuses_from_non_no_go(
        self, db_session: AsyncSession
    ) -> None:
        page = await _seed_page(db_session)
        # Page is in AUSSTEHEND; never visited NO_GO.
        with pytest.raises(ValueError, match="requires page in NO_GO"):
            await resolve_no_go_to_go(session=db_session, page=page)


# --- Schema/migration discipline -----------------------------------------


class TestT_4_3_1_SchemaDiscipline:
    """Locks in the migration shape so future changes can't silently drift."""

    def test_pages_has_ocr_status_column_default_ausstehend(self) -> None:
        col = Page.__table__.columns["ocr_status"]
        assert col.nullable is False
        default_text = str(col.server_default.arg).strip("'\"")
        assert default_text == OcrStatus.AUSSTEHEND.value

    def test_ocr_error_instances_table_registered(self) -> None:
        from waraq.db.base import Base

        assert "ocr_error_instances" in Base.metadata.tables

    def test_ocr_error_instances_has_no_satz_uuid(self) -> None:
        # DBB Abkürzung 2 stays clean — error rows route via page_uuid.
        cols = OcrErrorInstance.__table__.columns
        assert "satz_uuid" not in cols
        assert "page_uuid" in cols
        assert cols["page_uuid"].nullable is False


# --- State-machine guard rails -------------------------------------------


@pytest.mark.asyncio
class TestT_4_3_1_StateMachineGuards:
    async def test_apply_findings_refuses_from_ausstehend(self, db_session: AsyncSession) -> None:
        page = await _seed_page(db_session)
        weights = make_default_severity_weights()
        with pytest.raises(ValueError, match="requires page in IN_REVIEW"):
            await apply_findings_to_status(session=db_session, page=page, weights=weights)

    async def test_enter_in_review_permits_re_entry_from_terminal_state(
        self, db_session: AsyncSession
    ) -> None:
        # Re-entry is canonical per Sprint 1 §2: "Re-entry into in_review is
        # permitted; transition logged via EVENTING."
        page = await _seed_page(db_session)
        weights = make_default_severity_weights()
        await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_01,
        )
        await enter_in_review(session=db_session, page=page)
        await apply_findings_to_status(session=db_session, page=page, weights=weights)
        assert page.ocr_status == OcrStatus.NO_GO

        # Re-entry from no_go.
        await enter_in_review(session=db_session, page=page)
        assert page.ocr_status == OcrStatus.IN_REVIEW

    async def test_resolve_ocr_error_instance_idempotent_refusal(
        self, db_session: AsyncSession
    ) -> None:
        page = await _seed_page(db_session)
        instance = await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            error_code=OcrErrorClass.F_01,
        )
        await resolve_ocr_error_instance(session=db_session, instance=instance)
        assert instance.state == OcrErrorState.AUFGELOEST.value

        with pytest.raises(ValueError, match="already aufgeloest"):
            await resolve_ocr_error_instance(session=db_session, instance=instance)


# --- Block-narrowed errors still aggregate at the page level -------------


@pytest.mark.asyncio
class TestT_4_3_1_BlockNarrowedErrors:
    async def test_block_scoped_error_still_drives_page_status(
        self, db_session: AsyncSession
    ) -> None:
        page = await _seed_page(db_session)
        block = Block(
            block_uuid=new_uuid(),
            page_uuid=page.page_uuid,
            block_type="main_text",
            block_index=1,
        )
        db_session.add(block)
        await db_session.flush()

        weights = make_default_severity_weights()
        await record_ocr_error_instance(
            session=db_session,
            page_uuid=page.page_uuid,
            block_uuid=block.block_uuid,
            error_code=OcrErrorClass.F_01,  # kritisch
        )

        await enter_in_review(session=db_session, page=page)
        result = await apply_findings_to_status(session=db_session, page=page, weights=weights)

        assert result == OcrStatus.NO_GO


# --- A passive Page (never any errors) auto-clears to GO -----------------


@pytest.mark.asyncio
class TestT_4_3_1_NoErrorsEverPath:
    """A page that never had any error_instance auto-clears to GO when
    apply_findings runs. This is the *only* GO path that doesn't require
    a Decision Event — and it's safe because the no-auto-go rule only
    forbids `no_go → go`, not `in_review → go` from a clean page."""

    async def test_clean_page_auto_clears_to_go(self, db_session: AsyncSession) -> None:
        page = await _seed_page(db_session)
        weights = make_default_severity_weights()
        await enter_in_review(session=db_session, page=page)
        result = await apply_findings_to_status(session=db_session, page=page, weights=weights)
        assert result == OcrStatus.GO
