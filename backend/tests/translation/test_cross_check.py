"""Tests for §3.6 Primary/Check cross-check orchestrator."""

from __future__ import annotations

import pytest

from waraq.translation.cross_check import (
    CrossCheckSituation,
    make_cross_checked_translator,
)
from waraq.translation.service import TranslationContext


def _make_translator(output: str):
    """Helper: build a translator that returns a fixed string."""

    async def _t(_text: str, _ctx: TranslationContext) -> str:
        return output

    return _t


def _make_failing_translator(exc: Exception):
    async def _t(_text: str, _ctx: TranslationContext) -> str:
        raise exc

    return _t


@pytest.mark.asyncio
class TestCrossCheckClassification:
    async def test_agreement_when_outputs_equal(self) -> None:
        primary = _make_translator("Im Namen Gottes")
        check = _make_translator("Im Namen Gottes")
        translator = make_cross_checked_translator(primary=primary, check=check)
        ctx = TranslationContext()
        out = await translator("بسم الله", ctx)
        assert out == "Im Namen Gottes"
        assert ctx.cross_check is not None
        assert ctx.cross_check.situation == CrossCheckSituation.AGREEMENT
        assert ctx.cross_check.primary_output == "Im Namen Gottes"
        assert ctx.cross_check.check_output == "Im Namen Gottes"
        assert ctx.cross_check.check_error is None

    async def test_agreement_ignores_whitespace_and_case(self) -> None:
        primary = _make_translator("Im Namen Gottes")
        check = _make_translator("im   namen   gottes")
        translator = make_cross_checked_translator(primary=primary, check=check)
        ctx = TranslationContext()
        await translator("بسم الله", ctx)
        # Whitespace + case differences are not substantive.
        assert ctx.cross_check.situation == CrossCheckSituation.AGREEMENT

    async def test_substantive_deviation_when_outputs_differ(self) -> None:
        primary = _make_translator("Im Namen Gottes, des Allerbarmers")
        check = _make_translator("Im Namen Allahs, des Gnädigen")
        translator = make_cross_checked_translator(primary=primary, check=check)
        ctx = TranslationContext()
        out = await translator("بسم الله الرحمن", ctx)
        # Primary is adopted as the canonical output (§3.6 default).
        assert out == "Im Namen Gottes, des Allerbarmers"
        # But the disagreement is recorded.
        assert ctx.cross_check.situation == CrossCheckSituation.SUBSTANTIVE_DEVIATION
        assert ctx.cross_check.check_output == "Im Namen Allahs, des Gnädigen"


@pytest.mark.asyncio
class TestCrossCheckFailureSemantics:
    async def test_primary_failure_propagates_no_silent_role_swap(self) -> None:
        """§3.6: 'If the primary path fails, the check path does not silently
        take over the primary role.'"""
        primary = _make_failing_translator(RuntimeError("primary down"))
        check = _make_translator("Check would have said this")
        translator = make_cross_checked_translator(primary=primary, check=check)
        ctx = TranslationContext()
        with pytest.raises(RuntimeError, match="primary down"):
            await translator("source", ctx)

    async def test_check_failure_returns_primary_marks_check_failed(self) -> None:
        """§3.6: 'If the check path fails, the primary output continues; the
        affected passages are considered not cross-checked and are logged
        accordingly.'"""
        primary = _make_translator("Primary output")
        check = _make_failing_translator(ConnectionError("gemini timeout"))
        translator = make_cross_checked_translator(primary=primary, check=check)
        ctx = TranslationContext()
        out = await translator("source", ctx)
        assert out == "Primary output"
        assert ctx.cross_check is not None
        assert ctx.cross_check.situation == CrossCheckSituation.CHECK_FAILED
        assert ctx.cross_check.check_output is None
        assert "ConnectionError" in (ctx.cross_check.check_error or "")
        assert "gemini timeout" in (ctx.cross_check.check_error or "")


@pytest.mark.asyncio
class TestCrossCheckEngineLabels:
    async def test_engine_labels_recorded_on_outcome(self) -> None:
        primary = _make_translator("X")
        check = _make_translator("X")
        translator = make_cross_checked_translator(
            primary=primary,
            check=check,
            primary_engine_label="openai/gpt-4o-2024-11-20",
            check_engine_label="google/gemini-2.5-pro-001",
        )
        ctx = TranslationContext()
        await translator("source", ctx)
        assert ctx.cross_check.primary_engine == "openai/gpt-4o-2024-11-20"
        assert ctx.cross_check.check_engine == "google/gemini-2.5-pro-001"


@pytest.mark.asyncio
class TestCrossCheckPersistenceHook:
    """Verifies the cross-check outcome lands on the TRANSLATION-PO via
    the persistence hook."""

    async def test_translation_po_records_cross_check_block(self) -> None:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.api._m4_fixtures import make_page_block_segment
        from tests.conftest import _test_database_url, seed_account_uuid
        from waraq.identity import new_uuid
        from waraq.invariant.enums import LockFlag
        from waraq.release_gate import start_translation
        from waraq.schemas import Project, ProvenanceObject
        from waraq.schemas.enums import POType
        from waraq.translation import (
            make_translation_persistence_hook,
            run_translation_job,
            start_translation_job,
        )

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        try:
            account_uuid = new_uuid()
            project_uuid = new_uuid()
            async with sm() as session, session.begin():
                await seed_account_uuid(session, account_uuid)
                session.add(Project(project_uuid=project_uuid, account_uuid=account_uuid, name="x"))
                await session.flush()

            seeded = await make_page_block_segment(str(project_uuid), text="بسم الله")

            async with sm() as session, session.begin():
                await start_translation(session=session, project_uuid=project_uuid)
                job = await start_translation_job(
                    session=session,
                    project_uuid=project_uuid,
                    segment_uuids=[seeded.satz_uuid],
                )
                cross_translator = make_cross_checked_translator(
                    primary=_make_translator("Im Namen Gottes"),
                    check=_make_translator("Im Namen Allahs"),
                    primary_engine_label="stub-primary",
                    check_engine_label="stub-check",
                )
                hook = make_translation_persistence_hook(
                    engine_identifier="stub-primary+stub-check"
                )
                await run_translation_job(
                    session=session,
                    job=job,
                    translator=cross_translator,
                    on_segment_translated=hook,
                )

            async with sm() as session:
                pos = list(
                    (
                        await session.execute(
                            select(ProvenanceObject)
                            .where(ProvenanceObject.scope_uuid == seeded.satz_uuid)
                            .where(ProvenanceObject.po_type == POType.TRANSLATION.value)
                        )
                    ).scalars()
                )
                assert len(pos) == 1
                payload = pos[0].payload or {}
                assert "cross_check" in payload
                cc = payload["cross_check"]
                assert cc["situation"] == "substantive_deviation"
                assert cc["primary_engine"] == "stub-primary"
                assert cc["check_engine"] == "stub-check"
                assert cc["primary_output"] == "Im Namen Gottes"
                assert cc["check_output"] == "Im Namen Allahs"
                assert cc["check_error"] is None
        finally:
            _ = LockFlag  # silence unused-import
            await engine.dispose()
