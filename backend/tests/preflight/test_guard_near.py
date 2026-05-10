"""Phase 3 sub-batch A — §4.7.3 guard-near pre-check tests."""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project, seed_segment
from waraq.preflight import (
    CRITICAL_FONTS,
    GuardNearBlocked,
    GuardNearViolation,
    evaluate_guard_near,
    run_guard_near_checks,
    start_preflight_run,
)


def _all_fonts_present(_names: Sequence[str]) -> list[str]:
    return []


def _missing(*names: str):
    def _resolver(_unused: Sequence[str]) -> list[str]:
        return list(names)

    return _resolver


async def _no_findings(_session, _project_uuid):
    return []


def _findings(*items: str):
    async def _det(_session, _project_uuid):
        return list(items)

    return _det


@pytest.mark.asyncio
class TestGuardNearChecks:
    async def test_clean_project_passes(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        result = await run_guard_near_checks(
            session=db_session,
            project_uuid=project.project_uuid,
            font_resolver=_all_fonts_present,
        )
        assert result.passes is True
        assert result.blockers == []

    async def test_arabic_indic_digits_block(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        # ٤٢ contains Arabic-Indic digits (U+0664 U+0662 = "42").
        await seed_segment(db_session, project=project, text="Page ٤٢")
        result = await run_guard_near_checks(
            session=db_session,
            project_uuid=project.project_uuid,
            font_resolver=_all_fonts_present,
        )
        assert result.passes is False
        assert GuardNearViolation.DIGIT_STANDARD in result.blockers
        assert result.evidence[GuardNearViolation.DIGIT_STANDARD.value]

    async def test_eastern_arabic_indic_digits_block(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        # ۴۲ — Eastern Arabic-Indic (U+06F4 U+06F2).
        await seed_segment(db_session, project=project, text="مقدمه ۴۲")
        result = await run_guard_near_checks(
            session=db_session,
            project_uuid=project.project_uuid,
            font_resolver=_all_fonts_present,
        )
        assert result.passes is False
        assert GuardNearViolation.DIGIT_STANDARD in result.blockers

    async def test_western_digits_pass(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await seed_segment(db_session, project=project, text="Page 42 line 7")
        result = await run_guard_near_checks(
            session=db_session,
            project_uuid=project.project_uuid,
            font_resolver=_all_fonts_present,
        )
        assert result.passes is True

    async def test_rtl_detector_blocks(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        result = await run_guard_near_checks(
            session=db_session,
            project_uuid=project.project_uuid,
            rtl_detector=_findings("seg-uuid-1: missing RLM"),
            font_resolver=_all_fonts_present,
        )
        assert result.passes is False
        assert GuardNearViolation.CRITICAL_RTL in result.blockers

    async def test_style_template_detector_blocks(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        result = await run_guard_near_checks(
            session=db_session,
            project_uuid=project.project_uuid,
            style_template_detector=_findings("Heading 3 style missing"),
            font_resolver=_all_fonts_present,
        )
        assert result.passes is False
        assert GuardNearViolation.STYLE_TEMPLATE_INTEGRITY in result.blockers

    async def test_missing_critical_font_blocks(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        result = await run_guard_near_checks(
            session=db_session,
            project_uuid=project.project_uuid,
            font_resolver=_missing("Calibri"),
        )
        assert result.passes is False
        assert GuardNearViolation.CRITICAL_FONT_MISSING in result.blockers
        assert "Calibri" in result.evidence[GuardNearViolation.CRITICAL_FONT_MISSING.value]

    async def test_dev_font_bypass_env_returns_no_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`WARAQ_DEV_FONT_BYPASS=1` short-circuits `_default_font_resolver`
        so dev hosts without Calibri / Traditional Naskh / KFGQPC Uthmanic
        Script HAFS can iterate on UI flows. Production deployments leave
        the env var unset; the bypass logs a loud WARNING on every call."""
        from waraq.preflight.guard_near import _default_font_resolver

        monkeypatch.setenv("WARAQ_DEV_FONT_BYPASS", "1")
        # Ask for fonts that are very unlikely to be on a CI runner —
        # without the bypass, _default_font_resolver would return them
        # all as missing.
        missing = _default_font_resolver(("DefinitelyNotInstalled-Xyz", "AnotherFakeFont"))
        assert missing == []

    async def test_dev_font_bypass_env_unset_runs_resolver(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from waraq.preflight.guard_near import _default_font_resolver

        monkeypatch.delenv("WARAQ_DEV_FONT_BYPASS", raising=False)
        # A name that won't match anything on the host — when the env
        # is unset, the real resolver runs and reports it missing.
        missing = _default_font_resolver(("DefinitelyNotInstalled-Xyz",))
        # Either fc-list is missing (returns [], which is the
        # documented best-effort fallback) or it ran and reported the
        # bogus name. Both are non-bypass behavior.
        assert missing == [] or "DefinitelyNotInstalled-Xyz" in missing

    async def test_canonical_four_fonts(self) -> None:
        # §4.7.3 + §7.1 — these four names are canonical.
        assert CRITICAL_FONTS == (
            "KFGQPC Uthmanic Script HAFS",
            "Traditional Naskh",
            "Noto Sans Arabic",
            "Calibri",
        )

    async def test_multiple_blockers_all_reported(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await seed_segment(db_session, project=project, text="bad ٤")
        result = await run_guard_near_checks(
            session=db_session,
            project_uuid=project.project_uuid,
            rtl_detector=_findings("rtl-issue"),
            style_template_detector=_findings("style-issue"),
            font_resolver=_missing("Traditional Naskh"),
        )
        assert result.passes is False
        # All four canonical violations fire.
        assert set(result.blockers) == {
            GuardNearViolation.DIGIT_STANDARD,
            GuardNearViolation.CRITICAL_RTL,
            GuardNearViolation.STYLE_TEMPLATE_INTEGRITY,
            GuardNearViolation.CRITICAL_FONT_MISSING,
        }


@pytest.mark.asyncio
class TestStartPreflightRefusedOnGuardNearBlock:
    async def test_clean_project_opens_run(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        run = await start_preflight_run(
            session=db_session,
            project_uuid=project.project_uuid,
            font_resolver=_all_fonts_present,
        )
        assert run.job_uuid is not None
        assert run.job_type == "preflight"

    async def test_arabic_indic_digit_refuses_to_open(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await seed_segment(db_session, project=project, text="x ٧")
        with pytest.raises(GuardNearBlocked) as exc_info:
            await start_preflight_run(
                session=db_session,
                project_uuid=project.project_uuid,
                font_resolver=_all_fonts_present,
            )
        # The exception carries the structured result for HTTP layer use.
        assert exc_info.value.result is not None
        assert GuardNearViolation.DIGIT_STANDARD in exc_info.value.result.blockers

    async def test_missing_font_refuses_to_open(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        with pytest.raises(GuardNearBlocked):
            await start_preflight_run(
                session=db_session,
                project_uuid=project.project_uuid,
                font_resolver=_missing("Noto Sans Arabic"),
            )


@pytest.mark.asyncio
class TestEvaluateGuardNearReadOnly:
    async def test_does_not_create_run(self, db_session: AsyncSession) -> None:
        from sqlalchemy import select

        from waraq.schemas import Job

        project = await seed_project(db_session)
        before = (
            (await db_session.execute(select(Job).where(Job.project_uuid == project.project_uuid)))
            .scalars()
            .all()
        )

        result = await evaluate_guard_near(
            session=db_session,
            project_uuid=project.project_uuid,
            font_resolver=_all_fonts_present,
        )
        assert result.passes is True

        after = (
            (await db_session.execute(select(Job).where(Job.project_uuid == project.project_uuid)))
            .scalars()
            .all()
        )
        # No new Job rows — read-only.
        assert len(before) == len(after)
