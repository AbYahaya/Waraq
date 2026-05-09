"""Promotion module exceptions (Stufen 1-3)."""

from __future__ import annotations


class PromotionError(Exception):
    """Base for PROMOTION-module failures."""


class KandidatNotInKandidatState(PromotionError):
    """Attempted Stufe-3 action on a Musterkandidat that is no longer
    in the `kandidat` state — already bestaetigt or verworfen.

    Per R-S3-10: verworfene Kandidaten cannot be re-confirmed without
    fresh observations.
    """


class KandidatAlreadyConsumed(PromotionError):
    """A `bestaetigte_stilregeln` row already exists for this
    Musterkandidat. Belt-and-braces guard against double-confirm races
    (UNIQUE FK is the DB-level enforcement)."""
