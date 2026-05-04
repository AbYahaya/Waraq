"""Sprint -0.5 — Account schema.

Per CLAUDE.md §2.4, the canonical column name is `account_uuid`. The class
is Python-named `Account` for ergonomic imports.

Tier-1 free / Tier-2 paid distinctions per Dokument 1 §2.3 are not modeled
here yet — only the identity + auth surface. A `tier` column will be added
when Tier-related quotas / lifecycle (inactivity Tier 1, expiry Tier 2)
land. For Sprint -0.5 the goal is auth scaffolding, not entitlements.

Identity object — H-5 inactivation applies (no deletion). Email is
case-folded at the service layer for uniqueness; the column stores whatever
casing the service writes (lowercased per service convention).
"""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from waraq.db.base import Base, TimestampMixin


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
