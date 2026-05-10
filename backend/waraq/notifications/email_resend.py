"""Resend email-channel client.

Resend's HTTP API is a single POST to `https://api.resend.com/emails`
with `Authorization: Bearer <api_key>`. Body is `{from, to, subject,
html|text}`. We use plain text (`text` field) since notifications are
short-form alerts.

The `EmailSender` Protocol lets tests inject a deterministic stub
without monkeypatching.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

import httpx

from waraq.db.session import get_settings

_RESEND_ENDPOINT = "https://api.resend.com/emails"


class ResendSendError(Exception):
    """Raised on a non-2xx Resend response. Notification dispatch
    catches this and proceeds as "email channel unavailable" (in-app
    row is still written; `email_sent_at` stays NULL on the row)."""


class EmailSender(Protocol):
    """Protocol for the email-dispatch dependency.

    Returns True when the send succeeded (recipient was queued by the
    upstream provider), False otherwise. Implementations are expected
    to be best-effort — a failure does not raise to the caller; the
    notification service handles the channel-down case structurally.
    """

    async def send(
        self,
        *,
        to_email: str,
        subject: str,
        body_text: str,
    ) -> bool: ...


class ResendEmailSender:
    """Default `EmailSender` implementation backed by Resend's HTTP API.

    Constructor args carry the API key + sender so the same class is
    re-usable in tests with a different upstream.
    """

    def __init__(
        self,
        *,
        api_key: str,
        from_email: str,
        timeout: float = 10.0,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self._api_key = api_key
        self._from_email = from_email
        self._timeout = timeout
        self._client_factory = client_factory or (lambda: httpx.AsyncClient(timeout=timeout))

    async def send(
        self,
        *,
        to_email: str,
        subject: str,
        body_text: str,
    ) -> bool:
        if not self._api_key:
            return False
        async with self._client_factory() as client:
            try:
                resp = await client.post(
                    _RESEND_ENDPOINT,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": self._from_email,
                        "to": [to_email],
                        "subject": subject,
                        "text": body_text,
                    },
                )
            except httpx.HTTPError:
                return False
        return resp.is_success


class _DisabledEmailSender:
    """No-op `EmailSender` used when Resend isn't configured."""

    async def send(
        self,
        *,
        to_email: str,
        subject: str,
        body_text: str,
    ) -> bool:
        _ = to_email, subject, body_text
        return False


def make_default_email_sender() -> EmailSender:
    """Resolve the deployment's email sender from settings.

    Returns the no-op sender when `resend_api_key` is empty so callers
    always get a working `EmailSender` — the in-app channel still
    fires unconditionally; only the email send is gated on config.
    """
    settings = get_settings()
    if not settings.resend_api_key:
        return _DisabledEmailSender()
    return ResendEmailSender(
        api_key=settings.resend_api_key,
        from_email=settings.resend_from_email,
    )


# Silence unused-warning for re-exported aliases.
_ = Awaitable

__all__ = [
    "EmailSender",
    "ResendEmailSender",
    "ResendSendError",
    "make_default_email_sender",
]
