"""T-H7-01 — INVARIANT-Guard for H-7.

H-7: Musterkandidat (Stufe 2) → bestätigte Stilregel transition is only
permitted via the explicit user action bestätige_stilregel(musterkandidat_uuid).
No statistical threshold, no internal API path, no automatic promotion.
Full integration test lands with T-7.3.2 in Sprint 3.
"""

from __future__ import annotations

import pytest

from waraq.invariant import H7Violation, assert_no_auto_promotion


class TestT_H7_01_NoAutoPromotion:
    pytestmark = pytest.mark.h7

    def test_blocks_automatic_promotion_without_user_confirmation(self) -> None:
        with pytest.raises(H7Violation):
            assert_no_auto_promotion(
                is_automatic=True,
                via_user_confirmation=False,
            )

    def test_permits_user_confirmed_promotion(self) -> None:
        assert_no_auto_promotion(
            is_automatic=False,
            via_user_confirmation=True,
        )

    def test_blocks_when_automatic_even_if_user_confirmation_claimed(self) -> None:
        """Defensive: an automatic operation cannot 'borrow' a user confirmation."""
        with pytest.raises(H7Violation):
            assert_no_auto_promotion(
                is_automatic=True,
                via_user_confirmation=False,
            )
