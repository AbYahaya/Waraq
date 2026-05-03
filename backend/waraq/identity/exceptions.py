from __future__ import annotations


class IdentityError(Exception):
    pass


class UuidImmutabilityError(IdentityError):
    """H-5: an issued UUID was attempted to be changed."""

    def __init__(self, original: object, attempted: object) -> None:
        self.original = original
        self.attempted = attempted
        super().__init__(
            f"H-5 violation: UUID {original!r} cannot be mutated to {attempted!r}; "
            f"UUIDs are immutable once issued"
        )


class InactivationTargetError(IdentityError):
    """mark_inactive called on an object without an 'active' attribute."""

    def __init__(self, obj: object) -> None:
        self.obj = obj
        super().__init__(
            f"{type(obj).__name__} has no 'active' attribute; "
            f"mark_inactive requires an inactivatable target"
        )
