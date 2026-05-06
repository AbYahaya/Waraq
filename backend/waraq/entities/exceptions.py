"""Exceptions for the §4.19 ENTITY service."""

from __future__ import annotations


class EntityError(Exception):
    """Base class for entity-service violations."""


class InvalidEntityCategory(EntityError):
    """A category outside the canonical 5-value taxonomy was supplied
    (per Dokument 1 §4.19). The DB CHECK constraint also enforces the
    enumeration, but raising here gives a caller-facing error before the
    constraint trips."""


class InvalidEntityScope(EntityError):
    """Scope kwargs (`project_uuid` / `account_uuid`) do not match the
    `binding_level` chosen at create or lookup time. Same shape as the
    glossary scope contract."""


class EntityLabelAlreadyExists(EntityError):
    """An entity with the same (category, canonical_label, scope) already
    exists. Per-category uniqueness is enforced at the application layer
    (the DB has only the binding-consistency check, not a unique index on
    category+label) so duplicate-name aliases can be modeled by adding
    secondary surface forms via metadata, not via duplicate rows."""
