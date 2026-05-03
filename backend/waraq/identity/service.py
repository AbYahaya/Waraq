from __future__ import annotations

import uuid as _uuid
from typing import Protocol, runtime_checkable

from waraq.identity.exceptions import InactivationTargetError, UuidImmutabilityError


@runtime_checkable
class _Inactivatable(Protocol):
    active: bool


def new_uuid() -> _uuid.UUID:
    """T-1.1.1: collision-free UUID via RFC 4122 v4 (cryptographically secure)."""
    return _uuid.uuid4()


def assert_immutable(original: _uuid.UUID, current: _uuid.UUID) -> None:
    """T-1.1.2 / H-5: raise if an issued UUID was changed.

    Wired into SQLAlchemy event listeners on UUID PK columns in T-1.3.x.
    """
    if original != current:
        raise UuidImmutabilityError(original=original, attempted=current)


def mark_inactive(obj: object) -> None:
    """T-1.1.2 / H-5: set active=False. Replaces deletion. UUID is preserved."""
    if not isinstance(obj, _Inactivatable):
        raise InactivationTargetError(obj)
    obj.active = False
