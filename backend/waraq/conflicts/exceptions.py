"""Exceptions for the CONFLICT-Erkennung service (T-5.1.2)."""

from __future__ import annotations


class ConflictError(Exception):
    """Base class for conflict-instance violations."""


class ConflictAlreadyResolved(ConflictError):
    """A resolve_with_* call was made against a conflict whose state is
    already `aufgeloest`. The pre-resolution row is canonically immutable
    after resolution (Sprint 1 §2: "the row is now historical evidence").
    """


class ConflictResolutionPathInvalid(ConflictError):
    """Attempted to resolve a conflict via a path that doesn't match its
    semantics. Example: calling `resolve_with_lock_release` against a
    `konzept_vs_konzept` conflict where there's no lock to release.
    """
