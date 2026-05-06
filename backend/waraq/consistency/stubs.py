"""T-8.2.1 — Stub K-rule bodies for M2 closeout.

Each rule is a pass-through that returns no findings. The harness ships
this so downstream services (Sprint 4 preflight P-03 / W-02) can already
consume `KonsistenzBefund` rows; real bodies back-fill in M5 alongside
T-8.1.x audit infrastructure.

**Discipline guard**: each stub references its bound `subject_type` via
`K_RULE_SUBJECT_TYPE[rule_id]`. This keeps the per-rule subject_type
discipline visible at the stub level — the failure mode "K-02..K-06 get
pauschalisiert onto K-01's concept_id" (Sprint 4 §2 ticket-level risk)
must be impossible at the harness layer too. Real bodies will need to
read their bound identity-type's records, not surface_form text.

When you replace a stub, do NOT remove the `subject_type` reference. The
real body must still bind to the same SubjectType the registry expects.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from waraq.consistency.engine import (
    K_RULE_SUBJECT_TYPE,
    KConsistencyFinding,
    KRuleId,
    SubjectType,
    register_k_rule,
)


def _empty_stub(rule_id: KRuleId, expected_subject_type: SubjectType) -> object:
    """Build a stub check function for `rule_id`.

    Returns an async callable matching the `KRule` Protocol. The closure
    asserts on its first call that `K_RULE_SUBJECT_TYPE[rule_id]` is still
    the expected subject_type — defensive read against accidental drift
    if someone re-binds a K-rule to a different identity-type later.
    """

    async def _check(
        *,
        session: AsyncSession,
        project_uuid: _uuid.UUID,
    ) -> Iterable[KConsistencyFinding]:
        bound = K_RULE_SUBJECT_TYPE[rule_id]
        assert bound == expected_subject_type, (
            f"{rule_id.value} now binds to {bound.value} but stub expected "
            f"{expected_subject_type.value}. Re-bind requires updating both "
            "the K_RULE_SUBJECT_TYPE table and this stub."
        )
        # TODO(T-8.1.x back-fill, M5): real body — read records of type
        # `expected_subject_type` for this project, detect inconsistencies
        # between Identitätstyp and Segment renderings, emit findings.
        return []

    return _check


def register_stub_k_rules() -> None:
    """Register a no-op body for every K-rule.

    Call once at startup before any `run_consistency_check`. Idempotent —
    re-calling overwrites existing registrations with the stub.
    """
    for rule_id in KRuleId:
        register_k_rule(rule_id, _empty_stub(rule_id, K_RULE_SUBJECT_TYPE[rule_id]))  # type: ignore[arg-type]
