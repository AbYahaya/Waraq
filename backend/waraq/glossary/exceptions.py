"""Exceptions for the GLOSSARY service (T-5.2.1)."""

from __future__ import annotations


class GlossaryError(Exception):
    """Base class for glossary-service violations."""


class InvalidBindingScope(GlossaryError):
    """A glossary CRUD call was made with a scope inconsistent with the
    entry's `binding_level`.

    project-bound entries require `project_uuid`; account-bound entries
    require `account_uuid`. The CHECK constraint in the migration enforces
    the same shape at the DB level — this exception surfaces the violation
    with a clear caller-facing message before the constraint trips.
    """


class SurfaceFormAlreadyExists(GlossaryError):
    """`create_entry` called with a (surface_form, scope) pair that already
    has an active Concept. Glossary uniqueness is per-scope: the same
    surface form can resolve to different concepts under different binding
    scopes (e.g., a project override of an account-wide entry)."""
