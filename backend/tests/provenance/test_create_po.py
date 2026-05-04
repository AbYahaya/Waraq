"""T-1.6.1 — PROVENANCE-Kern create_po service tests.

Three layers:
1. Architectural — signature carries no `satz_uuid` kwarg (Abkürzung 2),
   only scope-based addressing. po_type and scope_type are required.
2. Integration — round-trip writes for all 7 PO types and the canonical
   EXPORT_EVENT addressing convention (scope_type=project + payload-based
   artefact identity).
3. Cross-table discipline — writing a PO must not produce any Revision,
   DecisionEvent, or LogEntry row.
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.identity import new_uuid
from waraq.provenance import create_po
from waraq.schemas import DecisionEvent, LogEntry, ProvenanceObject, Revision
from waraq.schemas.enums import POType, ScopeType

# --- Layer 1: signature-level architectural tests ------------------------


class TestT_1_6_1_SignatureDiscipline:
    """Abkürzung 2 starts at the signature: no `satz_uuid` kwarg, ever.
    All addressing flows through scope_type + scope_uuid."""

    def test_no_satz_uuid_kwarg(self) -> None:
        params = set(inspect.signature(create_po).parameters)
        assert "satz_uuid" not in params, (
            "create_po must not accept satz_uuid — addressing is scope_type + scope_uuid"
        )

    def test_required_canonical_kwargs_present(self) -> None:
        params = set(inspect.signature(create_po).parameters)
        required = {"po_type", "scope_type", "scope_uuid"}
        assert required <= params

    def test_no_decision_or_text_change_kwargs(self) -> None:
        # PROVENANCE-Kern is also not a decision writer or a text writer.
        params = set(inspect.signature(create_po).parameters)
        forbidden = {
            "decision_type",
            "decision_source",
            "before_text",
            "after_text",
            "change_source",
            "rev_uuid",
        }
        leaked = forbidden & params
        assert leaked == set(), f"create_po leaked foreign kwargs: {leaked}"


# --- Layer 2: integration ---------------------------------------------------


@pytest.mark.asyncio
class TestT_1_6_1_Integration:
    @pytest.mark.parametrize("po_type", list(POType))
    async def test_all_seven_po_types_round_trip(
        self, db_session: AsyncSession, po_type: POType
    ) -> None:
        """Every canonical PO type goes through the same single writer."""
        scope_uuid = new_uuid()
        # Pick a scope_type that matches the canonical scope per §5.3.
        # We use SEGMENT for most types and PROJECT for EXPORT_EVENT/PAGE for SCAN.
        scope_type = {
            POType.SCAN: ScopeType.PAGE,
            POType.EXPORT_EVENT: ScopeType.PROJECT,
        }.get(po_type, ScopeType.SEGMENT)

        po = await create_po(
            session=db_session,
            po_type=po_type,
            scope_type=scope_type,
            scope_uuid=scope_uuid,
            payload={"test": "data"},
        )

        loaded = (
            await db_session.execute(
                select(ProvenanceObject).where(ProvenanceObject.po_uuid == po.po_uuid)
            )
        ).scalar_one()
        assert str(loaded.po_type) == po_type.value
        assert str(loaded.scope_type) == scope_type.value
        assert loaded.scope_uuid == scope_uuid
        assert loaded.payload == {"test": "data"}

    async def test_payload_defaults_to_empty_dict(self, db_session: AsyncSession) -> None:
        po = await create_po(
            session=db_session,
            po_type=POType.SCAN,
            scope_type=ScopeType.PAGE,
            scope_uuid=new_uuid(),
        )
        assert po.payload == {}

    async def test_author_uuid_optional_for_system_authored_pos(
        self, db_session: AsyncSession
    ) -> None:
        # LINEAGE_EVENT-PO is canonically system-authored (CLAUDE.md §5.5).
        po = await create_po(
            session=db_session,
            po_type=POType.LINEAGE_EVENT,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=new_uuid(),
        )
        assert po.author_uuid is None

    async def test_po_uuid_unique_per_call(self, db_session: AsyncSession) -> None:
        scope_uuid = new_uuid()
        p1 = await create_po(
            session=db_session,
            po_type=POType.OCR,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=scope_uuid,
        )
        p2 = await create_po(
            session=db_session,
            po_type=POType.OCR,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=scope_uuid,
        )
        assert p1.po_uuid != p2.po_uuid

    async def test_export_event_canonical_addressing_convention(
        self, db_session: AsyncSession
    ) -> None:
        """EXPORT_EVENT canonically addressed via scope_type=PROJECT with
        artefact identity in payload (filename, format, sha256, size_bytes)."""
        from tests.conftest import seed_account_uuid

        project_uuid = new_uuid()
        author_uuid = new_uuid()
        await seed_account_uuid(db_session, author_uuid)

        artefact_payload = {
            "filename": "translation_2026-05-04.docx",
            "format": "docx",
            "sha256": "a" * 64,
            "size_bytes": 153_421,
        }

        po = await create_po(
            session=db_session,
            po_type=POType.EXPORT_EVENT,
            scope_type=ScopeType.PROJECT,
            scope_uuid=project_uuid,
            payload=artefact_payload,
            author_uuid=author_uuid,
        )

        loaded = (
            await db_session.execute(
                select(ProvenanceObject).where(ProvenanceObject.po_uuid == po.po_uuid)
            )
        ).scalar_one()
        assert str(loaded.po_type) == POType.EXPORT_EVENT.value
        assert str(loaded.scope_type) == ScopeType.PROJECT.value
        assert loaded.scope_uuid == project_uuid
        assert loaded.payload["filename"] == "translation_2026-05-04.docx"
        assert loaded.payload["format"] == "docx"
        assert loaded.payload["sha256"] == "a" * 64

    async def test_export_events_filterable_by_project(self, db_session: AsyncSession) -> None:
        """The canonical EXPORT_EVENT read path: 'all exports for project X'.
        Confirms scope_type='project' + scope_uuid suffices for this query."""
        project_a = new_uuid()
        project_b = new_uuid()

        for project in (project_a, project_a, project_b):
            await create_po(
                session=db_session,
                po_type=POType.EXPORT_EVENT,
                scope_type=ScopeType.PROJECT,
                scope_uuid=project,
                payload={"filename": "x.docx", "format": "docx"},
            )

        result = await db_session.execute(
            select(func.count())
            .select_from(ProvenanceObject)
            .where(
                ProvenanceObject.po_type == POType.EXPORT_EVENT.value,
                ProvenanceObject.scope_uuid == project_a,
            )
        )
        assert result.scalar_one() == 2


# --- Layer 3: cross-table discipline ---------------------------------------


@pytest.mark.asyncio
class TestT_1_6_1_CrossTableDiscipline:
    async def test_writing_po_does_not_create_other_event_rows(
        self, db_session: AsyncSession
    ) -> None:
        before_revisions = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()
        before_decisions = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        before_logs = (
            await db_session.execute(select(func.count()).select_from(LogEntry))
        ).scalar_one()

        await create_po(
            session=db_session,
            po_type=POType.LINEAGE_EVENT,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=new_uuid(),
            payload={"match_kind": "1to1"},
        )

        after_revisions = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()
        after_decisions = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        after_logs = (
            await db_session.execute(select(func.count()).select_from(LogEntry))
        ).scalar_one()

        assert after_revisions == before_revisions
        assert after_decisions == before_decisions
        assert after_logs == before_logs


# --- Layer 4: Abkürzung 7 — sole writer property -------------------------


class TestT_1_6_1_AbkurzungSeven_SoleWriter:
    """Abkürzung 7 says 'Upload-Handler writes SCAN-PO directly instead of
    through PROVENANCE-Kern' is a structural failure mode. We can't enforce
    'no other module ever writes to provenance_objects' at runtime, but we
    can lock in that the only PO-creation entrypoint exported from
    `waraq.provenance` is `create_po`.

    If anyone ships a `bulk_create_pos`, `_raw_insert_po`, or similar bypass
    later, this test fails first."""

    def test_provenance_module_exports_only_create_po(self) -> None:
        import waraq.provenance as prov_module

        public = {name for name in vars(prov_module) if not name.startswith("_")}
        # Module imports we tolerate (nested modules etc.). The contract is
        # about *PO-creation* entrypoints — only one is allowed.
        creators = {n for n in public if "create" in n.lower() or "insert" in n.lower()}
        assert creators == {"create_po"}, (
            f"waraq.provenance exposes more than one creation entrypoint: {creators}. "
            "PROVENANCE-Kern must be the sole writer (DBB Abkürzung 7)."
        )
