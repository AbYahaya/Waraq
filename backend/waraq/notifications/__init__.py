"""§2.1 + §2.2 + §3.6 — Notification dispatch (in-app + email channels).

Per Dokument 1 §2.1 user notifications go through two canonical channels:
in-app (notification panel) and email (Resend). Per §2.2 each user controls
both channels via `account_preferences`.

Per §3.6 the canonical first-trigger is the translation-pipeline 30-min
API-failure rule: "After 30 minutes without recovery, active user
information via in-app and email is triggered." The notification dispatch
path here is the runtime hook that rule fires through.

Module surface:

  - `notify(session, account_uuid, kind, title, body)` — write the in-app
    row and (when the account opted in + Resend is configured) send the
    email. Idempotent on (account_uuid, kind, title, body, last hour) —
    re-firing the same kind within the dedupe window does NOT duplicate.

  - `list_unread / mark_read / mark_all_read` — the in-app panel reads.

  - `get_or_create_preferences / update_preferences` — per-account
    channel toggles.

  - `EmailSender` Protocol + `ResendEmailSender` default implementation.
    Tests inject a stub via `notify(..., email_sender=...)`.

The §3.6 30-min rule lives in `waraq.notifications.translation_failure_watcher`
as a separate module so the watcher is opt-in (callers run it from a
periodic job; the core dispatch path doesn't depend on the watcher).
"""

from waraq.notifications.email_resend import (
    EmailSender,
    ResendEmailSender,
    make_default_email_sender,
)
from waraq.notifications.preferences import (
    get_or_create_preferences,
    update_preferences,
)
from waraq.notifications.service import (
    list_notifications,
    mark_all_read,
    mark_read,
    notify,
)

__all__ = [
    "EmailSender",
    "ResendEmailSender",
    "get_or_create_preferences",
    "list_notifications",
    "make_default_email_sender",
    "mark_all_read",
    "mark_read",
    "notify",
    "update_preferences",
]
