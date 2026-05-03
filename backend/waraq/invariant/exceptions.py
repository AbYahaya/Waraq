from __future__ import annotations

import uuid as _uuid

from waraq.invariant.enums import LockFlag, OperationKind


class GuardViolation(Exception):
    """Base for all INVARIANT-Guard violations.

    The Guard is non-deactivatable per DBB §B Abkürzung 1 and CAB §A.2.
    Catching GuardViolation to swallow it is itself a discipline failure —
    violations indicate the calling code is wrong by construction.
    """


class H1H2Violation(GuardViolation):
    """H-1, H-2: automatic write attempted on a manually-locked segment."""

    def __init__(self, *, segment_id: _uuid.UUID, lock_flag: LockFlag) -> None:
        self.segment_id = segment_id
        self.lock_flag = lock_flag
        super().__init__(
            f"H-1/H-2 violation: automatic write attempted on segment "
            f"{segment_id} with lock_flag={lock_flag.value}; "
            f"locked segments may only be written via explicit user-confirmation context"
        )


class H4Violation(GuardViolation):
    """H-4: revision-UUID requested for a non-text-change operation."""

    def __init__(self, *, operation_kind: OperationKind) -> None:
        self.operation_kind = operation_kind
        super().__init__(
            f"H-4 violation: revision-UUID requested for "
            f"operation_kind={operation_kind.value}; "
            f"revision-UUIDs are only issued for actual text changes"
        )


class H6Violation(GuardViolation):
    """H-6: rule-vs-lock conflict cannot be silently resolved."""

    def __init__(self) -> None:
        super().__init__(
            "H-6 violation: terminology/rule-vs-lock conflict cannot be silently resolved; "
            "must produce a persistent conflict_instance row with state=offen "
            "(resolution paths exposed by T-5.1.2 in Sprint 1)"
        )


class H7Violation(GuardViolation):
    """H-7: automatic promotion to bestätigte Stilregel attempted."""

    def __init__(self) -> None:
        super().__init__(
            "H-7 violation: Musterkandidat → bestätigte Stilregel transition is only "
            "permitted via explicit user action bestätige_stilregel(musterkandidat_uuid) "
            "(T-7.3.2 in Sprint 3)"
        )
