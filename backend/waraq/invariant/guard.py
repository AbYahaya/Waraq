from __future__ import annotations

import uuid as _uuid

from waraq.invariant.enums import LockFlag, OperationKind, OperationMode
from waraq.invariant.exceptions import (
    H1H2Violation,
    H4Violation,
    H6Violation,
    H7Violation,
)


def assert_no_auto_write_to_locked_segment(
    *,
    operation_mode: OperationMode,
    lock_flag: LockFlag,
    segment_id: _uuid.UUID,
) -> None:
    """T-1.2.1 — H-1, H-2.

    Block any automatic write to a segment with manual_local or manual_editorial
    lock_flag. Manual writes carrying explicit user-confirmation context are permitted.
    """
    if operation_mode is OperationMode.AUTOMATIC and lock_flag in {
        LockFlag.MANUAL_LOCAL,
        LockFlag.MANUAL_EDITORIAL,
    }:
        raise H1H2Violation(segment_id=segment_id, lock_flag=lock_flag)


def assert_no_revision_uuid_for_check(*, operation_kind: OperationKind) -> None:
    """T-1.2.2 — H-4.

    Revision-UUIDs are issued only on actual text changes. Check, dry-run,
    audit-pass, and OCR-check-pass operations never produce a revision-UUID.
    """
    if operation_kind is OperationKind.CHECK:
        raise H4Violation(operation_kind=operation_kind)


def assert_no_silent_conflict_resolution(
    *,
    has_lock_conflict: bool,
    via_conflict_instance: bool,
) -> None:
    """T-1.2.2 — H-6.

    A rule that wants to act on a locked segment must route through the
    conflict_instance pathway (T-5.1.2). Silent resolution is forbidden.
    """
    if has_lock_conflict and not via_conflict_instance:
        raise H6Violation()


def assert_no_auto_promotion(
    *,
    is_automatic: bool,
    via_user_confirmation: bool,
) -> None:
    """T-1.2.2 — H-7.

    The only path from Musterkandidat (Stufe 2) to bestätigte Stilregel is the
    explicit user action bestätige_stilregel(musterkandidat_uuid). No statistical
    threshold, no internal API, no automatic promotion.
    """
    if is_automatic and not via_user_confirmation:
        raise H7Violation()
