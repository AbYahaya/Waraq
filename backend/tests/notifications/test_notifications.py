"""Phase 3 sub-batch F — notifications dispatch + preferences tests."""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.audit._helpers import seed_project
from tests.conftest import seed_account_uuid
from waraq.identity import new_uuid
from waraq.notifications import (
    EmailSender,
    get_or_create_preferences,
    list_notifications,
    mark_all_read,
    mark_read,
    notify,
    update_preferences,
)
from waraq.notifications.translation_failure_watcher import (
    NOTIFICATION_KIND,
    fire_translation_failure_notifications,
)
from waraq.schemas import Account, Job, Notification
from waraq.schemas.enums import JobState


@dataclass
class StubEmailSender:
    sent: list[tuple[str, str, str]] = field(default_factory=list)
    succeed: bool = True

    async def send(self, *, to_email: str, subject: str, body_text: str) -> bool:
        self.sent.append((to_email, subject, body_text))
        return self.succeed


def _conform_email_sender(s: StubEmailSender) -> EmailSender:
    return s


async def _seed_account(db_session: AsyncSession) -> Account:
    account_uuid = new_uuid()
    await seed_account_uuid(db_session, account_uuid)
    account = await db_session.get(Account, account_uuid)
    assert account is not None
    return account


@pytest.mark.asyncio
class TestPreferencesLazyCreate:
    async def test_get_creates_default_row(self, db_session: AsyncSession) -> None:
        account = await _seed_account(db_session)
        prefs = await get_or_create_preferences(
            session=db_session, account_uuid=account.account_uuid
        )
        assert prefs.email_notifications_enabled is True
        assert prefs.in_app_notifications_enabled is True

    async def test_update_patches_specified_fields(self, db_session: AsyncSession) -> None:
        account = await _seed_account(db_session)
        await get_or_create_preferences(session=db_session, account_uuid=account.account_uuid)
        prefs = await update_preferences(
            session=db_session,
            account_uuid=account.account_uuid,
            email_enabled=False,
        )
        assert prefs.email_notifications_enabled is False
        # in_app left at default
        assert prefs.in_app_notifications_enabled is True


@pytest.mark.asyncio
class TestNotifyDispatch:
    async def test_writes_in_app_row_and_emits_email(self, db_session: AsyncSession) -> None:
        account = await _seed_account(db_session)
        sender = StubEmailSender()
        n = await notify(
            session=db_session,
            account_uuid=account.account_uuid,
            kind="test_kind",
            title="Hello",
            body="World",
            email_sender=_conform_email_sender(sender),
        )
        assert n is not None
        assert n.title == "Hello"
        assert n.body == "World"
        assert n.email_sent_at is not None
        assert sender.sent == [(account.email, "Hello", "World")]

    async def test_email_send_failure_leaves_email_sent_at_null(
        self, db_session: AsyncSession
    ) -> None:
        account = await _seed_account(db_session)
        sender = StubEmailSender(succeed=False)
        n = await notify(
            session=db_session,
            account_uuid=account.account_uuid,
            kind="test_kind",
            title="X",
            body="Y",
            email_sender=_conform_email_sender(sender),
        )
        assert n is not None
        assert n.email_sent_at is None

    async def test_email_disabled_skips_email_writes_in_app(self, db_session: AsyncSession) -> None:
        account = await _seed_account(db_session)
        await update_preferences(
            session=db_session,
            account_uuid=account.account_uuid,
            email_enabled=False,
        )
        sender = StubEmailSender()
        n = await notify(
            session=db_session,
            account_uuid=account.account_uuid,
            kind="k",
            title="t",
            body="b",
            email_sender=_conform_email_sender(sender),
        )
        assert n is not None
        assert n.email_sent_at is None
        assert sender.sent == []

    async def test_in_app_disabled_skips_row_still_emails(self, db_session: AsyncSession) -> None:
        account = await _seed_account(db_session)
        await update_preferences(
            session=db_session,
            account_uuid=account.account_uuid,
            in_app_enabled=False,
        )
        sender = StubEmailSender()
        n = await notify(
            session=db_session,
            account_uuid=account.account_uuid,
            kind="k",
            title="t",
            body="b",
            email_sender=_conform_email_sender(sender),
        )
        # No in-app row = None return.
        assert n is None
        # Email channel still fired.
        assert len(sender.sent) == 1

    async def test_dedup_within_window_returns_none(self, db_session: AsyncSession) -> None:
        account = await _seed_account(db_session)
        sender = StubEmailSender()
        n1 = await notify(
            session=db_session,
            account_uuid=account.account_uuid,
            kind="k",
            title="t",
            body="b",
            email_sender=_conform_email_sender(sender),
        )
        assert n1 is not None
        n2 = await notify(
            session=db_session,
            account_uuid=account.account_uuid,
            kind="k",
            title="t",
            body="b",
            email_sender=_conform_email_sender(sender),
        )
        assert n2 is None
        # Email also did NOT re-fire.
        assert len(sender.sent) == 1


@pytest.mark.asyncio
class TestListAndRead:
    async def test_list_orders_newest_first(self, db_session: AsyncSession) -> None:
        account = await _seed_account(db_session)
        sender = StubEmailSender()
        for i in range(3):
            n = await notify(
                session=db_session,
                account_uuid=account.account_uuid,
                kind=f"k{i}",
                title=f"t{i}",
                body=f"b{i}",
                email_sender=_conform_email_sender(sender),
            )
            assert n is not None
            # Stagger created_at to make ordering deterministic in-tx.
            n.created_at = datetime.now(UTC) + timedelta(seconds=i)
            await db_session.flush()
        rows = await list_notifications(session=db_session, account_uuid=account.account_uuid)
        assert [r.kind for r in rows] == ["k2", "k1", "k0"]

    async def test_only_unread_filter(self, db_session: AsyncSession) -> None:
        account = await _seed_account(db_session)
        sender = StubEmailSender()
        n1 = await notify(
            session=db_session,
            account_uuid=account.account_uuid,
            kind="k1",
            title="t",
            body="b",
            email_sender=_conform_email_sender(sender),
        )
        assert n1 is not None
        await mark_read(
            session=db_session,
            account_uuid=account.account_uuid,
            notification_uuid=n1.notification_uuid,
        )
        rows = await list_notifications(
            session=db_session, account_uuid=account.account_uuid, only_unread=True
        )
        assert rows == []

    async def test_mark_read_unknown_returns_false(self, db_session: AsyncSession) -> None:
        account = await _seed_account(db_session)
        ok = await mark_read(
            session=db_session,
            account_uuid=account.account_uuid,
            notification_uuid=_uuid.uuid4(),
        )
        assert ok is False

    async def test_mark_all_read(self, db_session: AsyncSession) -> None:
        account = await _seed_account(db_session)
        sender = StubEmailSender()
        for i in range(3):
            await notify(
                session=db_session,
                account_uuid=account.account_uuid,
                kind=f"k{i}",
                title=f"t{i}",
                body=f"b{i}",
                email_sender=_conform_email_sender(sender),
            )
        n = await mark_all_read(session=db_session, account_uuid=account.account_uuid)
        assert n == 3
        unread = await list_notifications(
            session=db_session, account_uuid=account.account_uuid, only_unread=True
        )
        assert unread == []


@pytest.mark.asyncio
class TestTranslationFailureWatcher:
    async def _seed_failed_translation_job(
        self, db_session: AsyncSession, *, project, age: timedelta
    ) -> Job:
        job = Job(
            job_uuid=new_uuid(),
            job_type="translation",
            state=JobState.FAILED.value,
            project_uuid=project.project_uuid,
        )
        db_session.add(job)
        await db_session.flush()
        # Force created_at older than the §3.6 30-min cutoff.
        job.created_at = datetime.now(UTC) - age
        await db_session.flush()
        return job

    async def test_no_failed_jobs_no_notifications(self, db_session: AsyncSession) -> None:
        sender = StubEmailSender()
        fired = await fire_translation_failure_notifications(
            session=db_session, email_sender=_conform_email_sender(sender)
        )
        assert fired == []

    async def test_failure_within_window_does_not_trigger(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await self._seed_failed_translation_job(
            db_session, project=project, age=timedelta(minutes=10)
        )
        sender = StubEmailSender()
        fired = await fire_translation_failure_notifications(
            session=db_session, email_sender=_conform_email_sender(sender)
        )
        assert fired == []

    async def test_failure_past_30min_fires(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await self._seed_failed_translation_job(
            db_session, project=project, age=timedelta(minutes=45)
        )
        sender = StubEmailSender()
        fired = await fire_translation_failure_notifications(
            session=db_session, email_sender=_conform_email_sender(sender)
        )
        assert project.name in fired
        # The §3.6 in-app + email both fired.
        rows = await list_notifications(session=db_session, account_uuid=project.account_uuid)
        assert any(r.kind == NOTIFICATION_KIND for r in rows)

    async def test_dedup_across_watcher_runs(self, db_session: AsyncSession) -> None:
        project = await seed_project(db_session)
        await self._seed_failed_translation_job(
            db_session, project=project, age=timedelta(minutes=45)
        )
        sender = StubEmailSender()
        await fire_translation_failure_notifications(
            session=db_session, email_sender=_conform_email_sender(sender)
        )
        await fire_translation_failure_notifications(
            session=db_session, email_sender=_conform_email_sender(sender)
        )
        # Only ONE notification despite two watcher runs (1-hour dedup).
        n_count = (
            await db_session.execute(
                __import__("sqlalchemy")
                .select(__import__("sqlalchemy").func.count())
                .select_from(Notification)
                .where(Notification.account_uuid == project.account_uuid)
            )
        ).scalar_one()
        assert n_count == 1
