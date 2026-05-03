"""T-1.1.1 + T-1.1.2 — IDENTITY service tests.

Includes T-H5-01 and T-H5-02 from the Sprint-0 mandatory test list.
"""

from __future__ import annotations

import uuid

import pytest

from waraq.identity import (
    InactivationTargetError,
    UuidImmutabilityError,
    assert_immutable,
    mark_inactive,
    new_uuid,
)


class TestT_1_1_1_NewUuid:
    """T-1.1.1: collision-free, cryptographically-secure UUID generation."""

    def test_returns_uuid_instance(self) -> None:
        assert isinstance(new_uuid(), uuid.UUID)

    def test_is_v4_per_rfc4122(self) -> None:
        assert new_uuid().version == 4

    def test_consecutive_calls_produce_different_uuids(self) -> None:
        assert new_uuid() != new_uuid()

    def test_no_collisions_at_scale(self) -> None:
        sample = {new_uuid() for _ in range(10_000)}
        assert len(sample) == 10_000


class TestT_H5_01_UuidImmutability:
    """T-H5-01: UUID immutability under all mutation attempts."""

    pytestmark = pytest.mark.h5

    def test_assert_immutable_passes_when_unchanged(self) -> None:
        u = new_uuid()
        assert_immutable(original=u, current=u)

    def test_assert_immutable_raises_when_changed(self) -> None:
        original = new_uuid()
        attempted = new_uuid()
        with pytest.raises(UuidImmutabilityError) as exc:
            assert_immutable(original=original, current=attempted)
        assert exc.value.original == original
        assert exc.value.attempted == attempted

    def test_uuid_objects_themselves_are_immutable(self) -> None:
        u = new_uuid()
        with pytest.raises(TypeError):
            u.int = 0  # type: ignore[misc]


class TestT_H5_02_InactivationDoesNotDelete:
    """T-H5-02: mark_inactive sets active=False; record stays queryable."""

    pytestmark = pytest.mark.h5

    def test_mark_inactive_sets_active_false(self) -> None:
        class _Obj:
            active = True

        obj = _Obj()
        mark_inactive(obj)
        assert obj.active is False

    def test_mark_inactive_preserves_uuid(self) -> None:
        class _Obj:
            def __init__(self) -> None:
                self.uuid = new_uuid()
                self.active = True

        obj = _Obj()
        original_uuid = obj.uuid
        mark_inactive(obj)
        assert obj.uuid == original_uuid

    def test_mark_inactive_raises_on_object_without_active_attr(self) -> None:
        class _BadObj:
            pass

        with pytest.raises(InactivationTargetError):
            mark_inactive(_BadObj())
