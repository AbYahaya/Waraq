"""Sprint -0.5 — Account schema. Phase 5 sub-batch M adds admission-gate fields.

Per CLAUDE.md §2.4, the canonical column name is `account_uuid`. The class
is Python-named `Account` for ergonomic imports.

Tier-1 free / Tier-2 paid distinctions per Dokument 1 §2.3 are NOT modeled
here yet — only the identity + auth surface plus the **admission gate**.
The tier system + subscription expiry + inactivity-deletion + guest user
+ trash-purge (canon §2.3 rows 9–13) are deferred per the user's
2026-05-12 scope decision: implement application + admin approval first;
the tier system gets revisited "with time".

Sub-batch M (admission gate) adds:
- `approval_status` — `pending` for new registrations; `approved` after
  an admin acts (or auto-approved for emails in the `ADMIN_EMAILS` env).
- `approved_at` / `approved_by_account_uuid` — audit trail.
- `rejection_reason` — admin's free-form rejection note.

Identity object — H-5 inactivation applies (no deletion). Email is
case-folded at the service layer for uniqueness; the column stores whatever
casing the service writes (lowercased per service convention).
"""

from __future__ import annotations

import datetime as _dt
import uuid as _uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base, TimestampMixin
from waraq.schemas.enums import ApprovalStatus


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    account_uuid: Mapped[_uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    # Email is the human-readable login identifier. Lowercased by the auth
    # service before insert so uniqueness is case-insensitive in practice.
    # Length 320 = RFC 5321 max (64 local + @ + 255 domain).
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    # bcrypt hash. Length 60 is the standard bcrypt output (algorithm + cost
    # + salt + hash, all base64).
    password_hash: Mapped[str] = mapped_column(String(60), nullable=False)
    # Display name; optional. Real name policy is a product decision, not
    # an auth one.
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Phase 5 sub-batch M — admission gate. New registrations default
    # to `pending`; admin emails (from `ADMIN_EMAILS` env) auto-approve
    # at registration time (bootstrap rule). Login refuses non-approved
    # accounts; admin endpoints under /admin/admissions/* manage the
    # pending queue.
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        SAEnum(
            ApprovalStatus,
            name="approval_status",
            native_enum=False,
            length=16,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        server_default=ApprovalStatus.PENDING.value,
    )
    approved_at: Mapped[_dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_account_uuid: Mapped[_uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.account_uuid", ondelete="RESTRICT"),
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
