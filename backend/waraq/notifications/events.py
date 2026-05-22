"""Convenience helpers for actionable workflow notifications."""

from __future__ import annotations

import uuid as _uuid
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.notifications.service import notify
from waraq.schemas import Project

NotificationSeverity = Literal["info", "success", "warning", "error", "action_required"]


async def notify_project_event(
    *,
    session: AsyncSession,
    project: Project,
    kind: str,
    title: str,
    body: str,
    severity: NotificationSeverity = "info",
    target_url: str | None = None,
    action_label: str | None = None,
    page_uuid: _uuid.UUID | None = None,
    issue_uuid: _uuid.UUID | None = None,
    issue_kind: str | None = None,
) -> None:
    """Send one project-linked notification to the project owner."""
    await notify(
        session=session,
        account_uuid=project.account_uuid,
        kind=kind,
        title=title,
        body=body,
        severity=severity,
        target_url=target_url,
        action_label=action_label,
        project_uuid=project.project_uuid,
        page_uuid=page_uuid,
        issue_uuid=issue_uuid,
        issue_kind=issue_kind,
    )


def project_workspace_url(project_uuid: _uuid.UUID, page_uuid: _uuid.UUID | None = None) -> str:
    if page_uuid is not None:
        return f"/projects/{project_uuid}/pages/{page_uuid}"
    return f"/projects/{project_uuid}"


def project_audit_url(project_uuid: _uuid.UUID) -> str:
    return f"/projects/{project_uuid}/audit"


def page_dpi_url(project_uuid: _uuid.UUID, page_uuid: _uuid.UUID) -> str:
    return f"/projects/{project_uuid}/pages/{page_uuid}?panel=dpi"


__all__ = [
    "NotificationSeverity",
    "notify_project_event",
    "page_dpi_url",
    "project_audit_url",
    "project_workspace_url",
]
