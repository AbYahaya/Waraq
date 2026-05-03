"""T-H1-01, T-H1-02 — INVARIANT-Guard for H-1 and H-2.

Lock-flag protection: no automatic write to manually-locked segments.
"""

from __future__ import annotations

import pytest

from waraq.invariant import (
    H1H2Violation,
    LockFlag,
    OperationMode,
    assert_no_auto_write_to_locked_segment,
)


class TestT_H1_01_AutoWriteOnManualLocalBlocked:
    pytestmark = pytest.mark.h1

    def test_blocks_when_lock_is_manual_local(self, fresh_segment_id) -> None:
        with pytest.raises(H1H2Violation) as exc:
            assert_no_auto_write_to_locked_segment(
                operation_mode=OperationMode.AUTOMATIC,
                lock_flag=LockFlag.MANUAL_LOCAL,
                segment_id=fresh_segment_id,
            )
        assert exc.value.lock_flag is LockFlag.MANUAL_LOCAL

    def test_permits_when_manual_with_confirmation(self, fresh_segment_id) -> None:
        assert_no_auto_write_to_locked_segment(
            operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
            lock_flag=LockFlag.MANUAL_LOCAL,
            segment_id=fresh_segment_id,
        )

    def test_permits_when_lock_is_none(self, fresh_segment_id) -> None:
        assert_no_auto_write_to_locked_segment(
            operation_mode=OperationMode.AUTOMATIC,
            lock_flag=LockFlag.NONE,
            segment_id=fresh_segment_id,
        )


class TestT_H1_02_AutoWriteOnManualEditorialBlocked:
    pytestmark = pytest.mark.h2

    def test_blocks_when_lock_is_manual_editorial(self, fresh_segment_id) -> None:
        with pytest.raises(H1H2Violation) as exc:
            assert_no_auto_write_to_locked_segment(
                operation_mode=OperationMode.AUTOMATIC,
                lock_flag=LockFlag.MANUAL_EDITORIAL,
                segment_id=fresh_segment_id,
            )
        assert exc.value.lock_flag is LockFlag.MANUAL_EDITORIAL

    def test_permits_when_manual_with_confirmation(self, fresh_segment_id) -> None:
        assert_no_auto_write_to_locked_segment(
            operation_mode=OperationMode.MANUAL_WITH_CONFIRMATION,
            lock_flag=LockFlag.MANUAL_EDITORIAL,
            segment_id=fresh_segment_id,
        )


class TestGuardIsNotDeactivatable:
    """Per DBB §B Abkürzung 1: the Guard must not have any toggle."""

    def test_guard_function_has_no_enabled_kwarg(self) -> None:
        import inspect

        sig = inspect.signature(assert_no_auto_write_to_locked_segment)
        forbidden = {"enabled", "active", "skip", "bypass", "disable", "guard_enabled"}
        assert not (forbidden & set(sig.parameters)), (
            f"Guard signature has forbidden toggle params: {forbidden & set(sig.parameters)}"
        )
