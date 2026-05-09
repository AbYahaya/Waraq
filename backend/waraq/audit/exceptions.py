"""Audit exceptions per Sprint 3 §2."""

from __future__ import annotations


class AuditError(Exception):
    """Base for AUDIT-module failures."""


class BefundDetectionImmutable(AuditError):
    """An attempt to mutate an immutable detection field
    (`regelkennung`, `verstossklasse`, `schweregrad`, `detected_at`)
    after the Befund has been created. Per Audit-Befund-Immutable-
    Detection-Test."""


class BefundAlreadyResolved(AuditError):
    """Attempted resolution / quittierung on an already-non-offen
    Befund. Resolution is a one-shot transition."""


class BefundNotResolvable(AuditError):
    """Attempted action that the Befund's current state forbids
    (e.g. quittiere on a `kritisch` finding — Audit-Quittierung-Nur-
    Mittel-Test)."""


class UnknownRegelkennung(AuditError):
    """A regelkennung was supplied that is not in the registered
    rule set."""
