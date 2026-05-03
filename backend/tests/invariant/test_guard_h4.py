"""T-H4-01, T-H4-02 — INVARIANT-Guard for H-4.

H-4: revision-UUIDs only for actual text changes; never for check operations.
Decision Events and Revisions live in strictly separate tables (full enforcement
of T-H4-02 lands with T-1.4.2 in the REVISION service).
"""

from __future__ import annotations

import pytest

from waraq.invariant import (
    H4Violation,
    OperationKind,
    assert_no_revision_uuid_for_check,
)


class TestT_H4_01_NoRevisionUuidForCheck:
    pytestmark = pytest.mark.h4

    def test_blocks_revision_uuid_for_check_operation(self) -> None:
        with pytest.raises(H4Violation) as exc:
            assert_no_revision_uuid_for_check(operation_kind=OperationKind.CHECK)
        assert exc.value.operation_kind is OperationKind.CHECK

    def test_permits_revision_uuid_for_text_change(self) -> None:
        assert_no_revision_uuid_for_check(operation_kind=OperationKind.TEXT_CHANGE)


class TestT_H4_02_RevisionAndDecisionEventStrictlySeparate:
    """T-H4-02: full integration test lands with T-1.4.2 (create_decision_event).

    At Day 0 we verify the contract: the Guard distinguishes the two operation
    kinds and the OperationKind enum has exactly the two values we expect.
    """

    pytestmark = pytest.mark.h4

    def test_operation_kind_enum_has_exactly_check_and_text_change(self) -> None:
        assert {k.value for k in OperationKind} == {"check", "text_change"}
