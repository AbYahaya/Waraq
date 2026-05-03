"""T-H6-01 — INVARIANT-Guard for H-6.

H-6: rule-vs-lock conflicts must produce a persistent conflict_instance row
(state=offen). Silent resolution is forbidden by construction. Resolution paths
are exposed by T-5.1.2 in Sprint 1.
"""

from __future__ import annotations

import pytest

from waraq.invariant import H6Violation, assert_no_silent_conflict_resolution


class TestT_H6_01_NoSilentConflictResolution:
    pytestmark = pytest.mark.h6

    def test_blocks_silent_resolution_when_lock_conflict_present(self) -> None:
        with pytest.raises(H6Violation):
            assert_no_silent_conflict_resolution(
                has_lock_conflict=True,
                via_conflict_instance=False,
            )

    def test_permits_when_routed_through_conflict_instance(self) -> None:
        assert_no_silent_conflict_resolution(
            has_lock_conflict=True,
            via_conflict_instance=True,
        )

    def test_permits_when_no_conflict_present(self) -> None:
        assert_no_silent_conflict_resolution(
            has_lock_conflict=False,
            via_conflict_instance=False,
        )
