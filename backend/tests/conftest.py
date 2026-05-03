from __future__ import annotations

import pytest


@pytest.fixture
def fresh_segment_id():
    """Convenience: a new segment-uuid for guard tests that need an identifier."""
    from waraq.identity import new_uuid

    return new_uuid()
