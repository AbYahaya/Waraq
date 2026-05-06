"""Exceptions for the LOCK service (T-5.1.1)."""

from __future__ import annotations


class LockError(Exception):
    """Base class for LOCK service violations."""


class LockInvalidLevel(LockError):
    """`set_lock(level=...)` called with a level that is not a manual lock.

    `set_lock` only writes manual_local or manual_editorial; releasing back
    to none flows through `release_lock`. Calling `set_lock(level=NONE)`
    would silently substitute a release path, masking caller intent.
    """


class LockAlreadyAtTargetState(LockError):
    """`set_lock` called when the segment is already at the target level, or
    `release_lock` called on an already-unlocked segment.

    Idempotent state changes are refused so that every Decision Event +
    MANUAL_-PO pair corresponds to an actual flag transition. Audit-readers
    can rely on each lock-related Decision Event reflecting a real change.
    """


class LockConfirmationRequired(LockError):
    """`release_lock` called on a `manual_editorial` segment without a
    `ConfirmationContext`.

    Per Sprint 1 §2 / LOCK-Release-Manual-Editorial-Confirmation-Test:
    `manual_editorial → none` requires explicit user confirmation. Callers
    without that context fail. `manual_local → none` does NOT require
    confirmation.
    """
