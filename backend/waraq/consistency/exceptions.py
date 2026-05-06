"""Exceptions for the CONSISTENCY engine (T-8.2.1)."""

from __future__ import annotations


class ConsistencyError(Exception):
    """Base class for consistency-engine violations."""


class KonsistenzAlreadyClosed(ConsistencyError):
    """A `resolve_*` / `quittiere_*` call was made against a finding whose
    `aufloesungsstatus` is no longer `offen`. Pre-resolution rows are
    immutable after closing (matches the conflict_instance pattern)."""
