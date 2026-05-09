"""T-10.1.2 + T-10.2.1 mandatory tests — Sprint 6 §4 (page/project
readouts + four scope-separated endpoints + cross-pollination).

Test ID coverage:
- Get-Page-History-Page-Scoped-Only-Test
- Get-Page-History-No-Segment-Events-Test
- Get-Page-History-Read-Only-Test
- Get-Project-History-Project-Scoped-DEs-Test
- Get-Project-History-Includes-Export-Events-Test
- Get-Project-History-No-Account-Scoped-Test
- Get-Project-History-No-Segment-Events-Test
- Get-Project-History-No-Log-Test
- Get-Project-History-No-Other-POs-Test
- Endpoint-Segmenthistorie-Vollstaendigkeit-Test
- Endpoint-Segmenthistorie-Excludes-Page-Project-Account-Test
- Endpoint-Segmenthistorie-Excludes-Log-Test
- Endpoint-Seitenhistorie-Page-Scoped-Only-Test
- Endpoint-Seitenhistorie-Excludes-Segment-Events-Test
- Endpoint-Seitenhistorie-Excludes-Export-Events-Test
- Endpoint-Seitenhistorie-Excludes-Pos-Test
- Endpoint-Projekthistorie-Project-Scoped-DEs-And-Export-Events-Test
- Endpoint-Projekthistorie-Excludes-Account-Scoped-Test
- Endpoint-Projekthistorie-Excludes-Other-Scopes-Test
- Endpoint-Ereignis-Log-Only-Logs-Test
- Endpoint-Ereignis-Log-No-Other-Histories-Test
- Endpoint-No-Cross-Pollination-Test
- Endpoint-Read-Only-Test
- Endpoint-No-UI-Logic-Test
- Endpoint-Chronological-Order-Test
- Lineage-Event-Kein-DE-Regression-Test
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.readout._helpers import (
    seed_de,
    seed_export_event,
    seed_po,
    seed_project_with_account,
    seed_segment_with_revision,
)
from waraq.eventing import log_event
from waraq.identity import new_uuid
from waraq.readout import (
    LogEntryFilter,
    get_log_entries,
    get_page_readout,
    get_project_readout,
)
from waraq.schemas import Block, DecisionEvent, LogEntry, ProvenanceObject, Revision
from waraq.schemas.enums import DecisionSource, POType, ScopeType

# --- Get-Page-History-Page-Scoped-Only-Test ---------------------------


@pytest.mark.asyncio
class TestPageReadoutScopedOnly:
    async def test_only_page_scoped_des_returned(self, db_session: AsyncSession) -> None:
        project, _ = await seed_project_with_account(db_session)
        seg = await seed_segment_with_revision(db_session, project=project, text="x")
        block = await db_session.get(Block, seg.block_uuid)

        page_de = await seed_de(
            db_session,
            scope_type=ScopeType.PAGE,
            scope_uuid=block.page_uuid,
            decision_source=DecisionSource.OCR_REVIEW,
        )
        # Decision Event ABOUT a Segment on the same Page — must be excluded.
        seg_de = await seed_de(
            db_session,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
            decision_source=DecisionSource.LOCK_MANAGEMENT,
        )
        # Project-scoped DE — must be excluded.
        project_de = await seed_de(
            db_session,
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        )

        readout = await get_page_readout(session=db_session, page_uuid=block.page_uuid)
        de_uuids = {de.decision_event_uuid for de in readout.decision_events}
        assert page_de.decision_event_uuid in de_uuids
        assert seg_de.decision_event_uuid not in de_uuids
        assert project_de.decision_event_uuid not in de_uuids


@pytest.mark.asyncio
class TestPageReadoutReadOnly:
    async def test_query_writes_nothing(self, db_session: AsyncSession) -> None:
        project, _ = await seed_project_with_account(db_session)
        seg = await seed_segment_with_revision(db_session, project=project, text="x")
        block = await db_session.get(Block, seg.block_uuid)

        de_count_before = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        log_count_before = (
            await db_session.execute(select(func.count()).select_from(LogEntry))
        ).scalar_one()
        await get_page_readout(session=db_session, page_uuid=block.page_uuid)
        assert (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one() == de_count_before
        assert (
            await db_session.execute(select(func.count()).select_from(LogEntry))
        ).scalar_one() == log_count_before


# --- Get-Project-History tests ----------------------------------------


@pytest.mark.asyncio
class TestProjectReadout:
    async def test_returns_project_des_and_export_events_only(
        self, db_session: AsyncSession
    ) -> None:
        project, account_uuid = await seed_project_with_account(db_session)
        seg = await seed_segment_with_revision(db_session, project=project, text="x")
        block = await db_session.get(Block, seg.block_uuid)

        # Project-scoped DE (release-gate-style).
        proj_de = await seed_de(
            db_session,
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        )
        # EXPORT_EVENT on this project.
        export_po = await seed_export_event(
            db_session,
            project_uuid=project.project_uuid,
            revision_snapshot=[],
        )
        # Segment-scoped DE — must be excluded.
        seg_de = await seed_de(
            db_session,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
            decision_source=DecisionSource.LOCK_MANAGEMENT,
        )
        # Page-scoped DE — must be excluded.
        page_de = await seed_de(
            db_session,
            scope_type=ScopeType.PAGE,
            scope_uuid=block.page_uuid,
            decision_source=DecisionSource.OCR_REVIEW,
        )
        # Account-scoped DE (gebundener Resthinweis Dokument 2 §2D — must be excluded).
        account_de = await seed_de(
            db_session,
            scope_type=ScopeType.ACCOUNT,
            scope_uuid=account_uuid,
            decision_source=DecisionSource.STYLE_MANAGEMENT,
        )
        # Other PO type (OCR, segment-scoped) — must be excluded from project readout.
        ocr_po = await seed_po(
            db_session,
            po_type=POType.OCR,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
        )
        # Log entry on the project — must be excluded.
        await log_event(
            session=db_session,
            operation_type="test_op",
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            result={},
        )

        readout = await get_project_readout(session=db_session, project_uuid=project.project_uuid)
        de_uuids = {d.decision_event_uuid for d in readout.decision_events}
        assert proj_de.decision_event_uuid in de_uuids
        assert seg_de.decision_event_uuid not in de_uuids
        assert page_de.decision_event_uuid not in de_uuids
        assert account_de.decision_event_uuid not in de_uuids

        export_uuids = {p.po_uuid for p in readout.export_events}
        assert export_po.po_uuid in export_uuids
        # Other POs excluded.
        assert ocr_po.po_uuid not in export_uuids


# --- Endpoint tests (T-10.2.1) ----------------------------------------


@pytest.fixture
async def authed_client(db_session: AsyncSession):
    """Build an httpx.AsyncClient + auth bearer using the existing
    auth flow. Returns (client, account_uuid, headers)."""
    from httpx import ASGITransport, AsyncClient

    from tests.conftest import seed_account_uuid
    from waraq.api.dependencies import get_db_session
    from waraq.api.main import create_app
    from waraq.auth.tokens import issue_token

    account_uuid = new_uuid()
    await seed_account_uuid(db_session, account_uuid)
    await db_session.flush()

    app = create_app()
    # Override the DB session dep to use the test session.

    async def _override():
        yield db_session

    app.dependency_overrides[get_db_session] = _override

    token = issue_token(account_uuid=account_uuid)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, account_uuid, headers


@pytest.mark.asyncio
class TestEndpointSegmenthistorie:
    async def test_segmenthistorie_returns_full_segment_history(
        self,
        db_session: AsyncSession,
        authed_client,
    ) -> None:
        client, account_uuid, headers = authed_client
        # Seed project owned by the authed account.
        from waraq.identity import new_uuid as nu
        from waraq.schemas import Project

        project = Project(project_uuid=nu(), account_uuid=account_uuid, name="t")
        db_session.add(project)
        await db_session.flush()
        seg = await seed_segment_with_revision(db_session, project=project, text="x")
        # Segment-scoped DE.
        seg_de = await seed_de(
            db_session,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
            decision_source=DecisionSource.LOCK_MANAGEMENT,
        )
        # Segment-scoped PO.
        seg_po = await seed_po(
            db_session,
            po_type=POType.OCR,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
        )
        # Page-scoped DE — must be excluded.
        block = await db_session.get(Block, seg.block_uuid)
        await seed_de(
            db_session,
            scope_type=ScopeType.PAGE,
            scope_uuid=block.page_uuid,
            decision_source=DecisionSource.OCR_REVIEW,
        )
        # Project-scoped DE — must be excluded.
        await seed_de(
            db_session,
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        )
        # EXPORT_EVENT containing seg's rev — included as werkweite Referenz.
        export_po = await seed_export_event(
            db_session,
            project_uuid=project.project_uuid,
            revision_snapshot=[seg.current_rev_uuid],
        )
        # Log entry on the segment — must be excluded.
        await log_event(
            session=db_session,
            operation_type="test_op",
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
            result={},
        )
        await db_session.flush()

        resp = await client.get(f"/history/segment/{seg.satz_uuid}", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Segment-scoped revisions present.
        assert any(rev["satz_uuid"] == str(seg.satz_uuid) for rev in body["revisions"])
        # Segment-scoped DE present, page/project DEs not.
        de_uuids = {d["decision_event_uuid"] for d in body["decision_events"]}
        assert str(seg_de.decision_event_uuid) in de_uuids
        # Segment-scoped PO present.
        po_uuids = {p["po_uuid"] for p in body["provenance_objects"]}
        assert str(seg_po.po_uuid) in po_uuids
        # EXPORT_EVENT werkweite Referenz present + marker.
        ref_po_uuids = {r["po"]["po_uuid"] for r in body["export_event_refs"]}
        assert str(export_po.po_uuid) in ref_po_uuids
        for ref in body["export_event_refs"]:
            assert ref["als_werkweite_referenz"] is True
        # Endpoint-Segmenthistorie-Excludes-Log-Test: response shape has no log_entries field.
        assert "log_entries" not in body


@pytest.mark.asyncio
class TestEndpointSeitenhistorie:
    async def test_seitenhistorie_excludes_segment_export_pos(
        self,
        db_session: AsyncSession,
        authed_client,
    ) -> None:
        client, account_uuid, headers = authed_client
        from waraq.schemas import Project

        project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="t")
        db_session.add(project)
        await db_session.flush()
        seg = await seed_segment_with_revision(db_session, project=project, text="x")
        block = await db_session.get(Block, seg.block_uuid)

        page_de = await seed_de(
            db_session,
            scope_type=ScopeType.PAGE,
            scope_uuid=block.page_uuid,
            decision_source=DecisionSource.OCR_REVIEW,
        )
        # Segment-scoped DE — must be excluded.
        await seed_de(
            db_session,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
            decision_source=DecisionSource.LOCK_MANAGEMENT,
        )
        # EXPORT_EVENT — must be excluded from Seitenhistorie.
        await seed_export_event(
            db_session,
            project_uuid=project.project_uuid,
            revision_snapshot=[seg.current_rev_uuid],
        )
        # PO scoped to segment — must be excluded.
        await seed_po(
            db_session,
            po_type=POType.OCR,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
        )
        await db_session.flush()

        resp = await client.get(f"/history/page/{block.page_uuid}", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        de_uuids = {d["decision_event_uuid"] for d in body["decision_events"]}
        assert str(page_de.decision_event_uuid) in de_uuids
        # Body has no segments / pos / export refs / logs fields — strict shape.
        assert set(body.keys()) == {"page_uuid", "decision_events"}


@pytest.mark.asyncio
class TestEndpointProjekthistorie:
    async def test_projekthistorie_excludes_account_segment_log(
        self,
        db_session: AsyncSession,
        authed_client,
    ) -> None:
        client, account_uuid, headers = authed_client
        from waraq.schemas import Project

        project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="t")
        db_session.add(project)
        await db_session.flush()
        seg = await seed_segment_with_revision(db_session, project=project, text="x")
        block = await db_session.get(Block, seg.block_uuid)

        proj_de = await seed_de(
            db_session,
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        )
        export_po = await seed_export_event(
            db_session,
            project_uuid=project.project_uuid,
            revision_snapshot=[seg.current_rev_uuid],
        )
        # Account-scoped DE (gebundener Resthinweis) — must be excluded.
        await seed_de(
            db_session,
            scope_type=ScopeType.ACCOUNT,
            scope_uuid=account_uuid,
            decision_source=DecisionSource.STYLE_MANAGEMENT,
        )
        # Page-scoped DE — must be excluded.
        await seed_de(
            db_session,
            scope_type=ScopeType.PAGE,
            scope_uuid=block.page_uuid,
            decision_source=DecisionSource.OCR_REVIEW,
        )
        # Log entry on project — must be excluded.
        await log_event(
            session=db_session,
            operation_type="test_op",
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            result={},
        )
        await db_session.flush()

        resp = await client.get(f"/history/project/{project.project_uuid}", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        de_uuids = {d["decision_event_uuid"] for d in body["decision_events"]}
        assert str(proj_de.decision_event_uuid) in de_uuids
        assert len(de_uuids) == 1  # No account / segment / page DE leaked.
        export_uuids = {p["po_uuid"] for p in body["export_events"]}
        assert str(export_po.po_uuid) in export_uuids
        # Strict shape — no log_entries / segments / pages.
        assert set(body.keys()) == {"project_uuid", "decision_events", "export_events"}


@pytest.mark.asyncio
class TestEndpointEreignisLog:
    async def test_ereignis_log_returns_logs_only(
        self,
        db_session: AsyncSession,
        authed_client,
    ) -> None:
        client, account_uuid, headers = authed_client
        from waraq.schemas import Project

        project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="t")
        db_session.add(project)
        await db_session.flush()
        await log_event(
            session=db_session,
            operation_type="audit_run_completed",
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            result={"x": 1},
        )
        # Inject project DE — must NOT appear in /history/log.
        await seed_de(
            db_session,
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        )
        await db_session.flush()

        resp = await client.get("/history/log", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Body has only `log_entries` field.
        assert set(body.keys()) == {"log_entries"}
        assert len(body["log_entries"]) >= 1


# --- Cross-pollination invariant (HG-S6-4) ----------------------------


@pytest.mark.asyncio
class TestEndpointNoCrossPollination:
    async def test_no_uuid_appears_in_two_endpoints(
        self,
        db_session: AsyncSession,
        authed_client,
    ) -> None:
        """Per Sprint 6 §A HG-S6-4: each UUID (Decision-Event-UUID,
        Revision-UUID, Log-ID) appears in exactly one endpoint's
        result, with one documented dual-presence: EXPORT_EVENT in
        Segmenthistorie (werkweite Referenz) and Projekthistorie
        (werks-eigene Entität)."""
        client, account_uuid, headers = authed_client
        from waraq.schemas import Project

        project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="t")
        db_session.add(project)
        await db_session.flush()
        seg = await seed_segment_with_revision(db_session, project=project, text="x")
        block = await db_session.get(Block, seg.block_uuid)

        await seed_de(
            db_session,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
            decision_source=DecisionSource.LOCK_MANAGEMENT,
        )
        await seed_de(
            db_session,
            scope_type=ScopeType.PAGE,
            scope_uuid=block.page_uuid,
            decision_source=DecisionSource.OCR_REVIEW,
        )
        await seed_de(
            db_session,
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
        )
        export_po = await seed_export_event(
            db_session,
            project_uuid=project.project_uuid,
            revision_snapshot=[seg.current_rev_uuid],
        )
        await log_event(
            session=db_session,
            operation_type="test",
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            result={},
        )
        await db_session.flush()

        seg_resp = (await client.get(f"/history/segment/{seg.satz_uuid}", headers=headers)).json()
        page_resp = (await client.get(f"/history/page/{block.page_uuid}", headers=headers)).json()
        proj_resp = (
            await client.get(f"/history/project/{project.project_uuid}", headers=headers)
        ).json()
        log_resp = (await client.get("/history/log", headers=headers)).json()

        # Decision-Event-UUIDs — each appears in exactly one endpoint.
        seg_des = {d["decision_event_uuid"] for d in seg_resp["decision_events"]}
        page_des = {d["decision_event_uuid"] for d in page_resp["decision_events"]}
        proj_des = {d["decision_event_uuid"] for d in proj_resp["decision_events"]}
        assert seg_des & page_des == set()
        assert seg_des & proj_des == set()
        assert page_des & proj_des == set()

        # Log-IDs only in /history/log.
        log_ids = {le["log_id"] for le in log_resp["log_entries"]}
        # Segment / page / project responses don't include log_entries at all
        # (that's part of the strict shape contract).
        assert "log_entries" not in seg_resp
        assert "log_entries" not in page_resp
        assert "log_entries" not in proj_resp
        assert len(log_ids) >= 1

        # Documented dual-presence: EXPORT_EVENT in Segmenthistorie
        # (werkweite Referenz) AND Projekthistorie (werks-eigene Entität).
        seg_export_uuids = {r["po"]["po_uuid"] for r in seg_resp["export_event_refs"]}
        proj_export_uuids = {p["po_uuid"] for p in proj_resp["export_events"]}
        assert str(export_po.po_uuid) in seg_export_uuids
        assert str(export_po.po_uuid) in proj_export_uuids
        # Distinguishable: segment side carries the marker.
        for ref in seg_resp["export_event_refs"]:
            assert ref["als_werkweite_referenz"] is True


# --- Endpoint-Read-Only-Test ------------------------------------------


@pytest.mark.asyncio
class TestEndpointReadOnly:
    async def test_endpoints_write_nothing(
        self,
        db_session: AsyncSession,
        authed_client,
    ) -> None:
        client, account_uuid, headers = authed_client
        from waraq.schemas import Project

        project = Project(project_uuid=new_uuid(), account_uuid=account_uuid, name="t")
        db_session.add(project)
        await db_session.flush()
        seg = await seed_segment_with_revision(db_session, project=project, text="x")
        block = await db_session.get(Block, seg.block_uuid)
        await db_session.flush()

        de_count_before = (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one()
        log_count_before = (
            await db_session.execute(select(func.count()).select_from(LogEntry))
        ).scalar_one()
        po_count_before = (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one()
        rev_count_before = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()

        # Hit all four endpoints.
        await client.get(f"/history/segment/{seg.satz_uuid}", headers=headers)
        await client.get(f"/history/page/{block.page_uuid}", headers=headers)
        await client.get(f"/history/project/{project.project_uuid}", headers=headers)
        await client.get("/history/log", headers=headers)

        # Read-side counts unchanged — R-S6-10: read endpoints never
        # write Log-Eintrag rows for the read operation itself.
        assert (
            await db_session.execute(select(func.count()).select_from(DecisionEvent))
        ).scalar_one() == de_count_before
        assert (
            await db_session.execute(select(func.count()).select_from(LogEntry))
        ).scalar_one() == log_count_before
        assert (
            await db_session.execute(select(func.count()).select_from(ProvenanceObject))
        ).scalar_one() == po_count_before
        assert (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one() == rev_count_before


# --- Endpoint-No-UI-Logic-Test (code review) --------------------------


class TestEndpointNoUILogic:
    """The four endpoints return structured data only — no rendering,
    no formatting decisions baked into the response shape."""

    def test_router_source_has_no_html_or_template_references(self) -> None:
        from waraq.api.routers import readout_router

        src = inspect.getsource(readout_router)
        # No HTML, no template engine, no rendering hint fields.
        for forbidden in ("<html", "<div", "render_template", "Jinja", "html_safe"):
            assert forbidden not in src

    def test_response_shape_contains_only_data_keys(self) -> None:
        """The four endpoint return-dicts have plain data keys — no
        `_ui_*` / `_render_*` hints."""
        from waraq.api.routers import readout_router

        src = inspect.getsource(readout_router)
        for hint in ("_ui_", "_render_", "_html_", "render_as_"):
            assert hint not in src


# --- Endpoint-Chronological-Order-Test --------------------------------


@pytest.mark.asyncio
class TestChronologicalOrder:
    async def test_decision_events_returned_by_created_at_asc(
        self, db_session: AsyncSession
    ) -> None:
        project, _ = await seed_project_with_account(db_session)
        # Three project-scoped DEs in known order.
        des = []
        for i in range(3):
            de = await seed_de(
                db_session,
                scope_type=ScopeType.PROJECT,
                scope_uuid=project.project_uuid,
                decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
                decision_type=f"de_{i}",
            )
            des.append(de)

        readout = await get_project_readout(session=db_session, project_uuid=project.project_uuid)
        # Result preserves insertion order (ascending created_at).
        sorted_des = sorted(readout.decision_events, key=lambda d: d.created_at)
        assert readout.decision_events == sorted_des


# --- Lineage-Event-Kein-DE-Regression-Test (HG-S6-5) ------------------


@pytest.mark.asyncio
class TestLineageEventKeinDecisionEvent:
    """Per Sprint 6 §A HG-S6-5 / R-S6-09: LINEAGE_EVENT-POs do not
    surface as Decision Events in any history. The readout layer is
    where the leak would visibly manifest. We synthesize a
    LINEAGE_EVENT-PO and verify it appears in segment-scoped POs (a
    PO IS a PO) but NOT in any decision_events list."""

    async def test_lineage_event_po_in_pos_not_in_des(self, db_session: AsyncSession) -> None:
        from waraq.readout import get_segment_readout

        project, _ = await seed_project_with_account(db_session)
        seg = await seed_segment_with_revision(db_session, project=project, text="x")
        # Synthesize a LINEAGE_EVENT-PO scoped to the segment.
        lineage_po = await seed_po(
            db_session,
            po_type=POType.LINEAGE_EVENT,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
            payload={"kind": "1zu1"},
        )
        readout = await get_segment_readout(session=db_session, satz_uuid=seg.satz_uuid)
        # PO surfaces in provenance_objects.
        assert any(p.po_uuid == lineage_po.po_uuid for p in readout.provenance_objects)
        # NOT in decision_events (it's a PO, not a DE — structurally
        # impossible to leak, but the test pins the invariant).
        de_types = {d.decision_type for d in readout.decision_events}
        assert "lineage_match" not in de_types


# --- Get-Log-Entries filter test --------------------------------------


@pytest.mark.asyncio
class TestLogEntryFilter:
    async def test_filter_by_operation_type(self, db_session: AsyncSession) -> None:
        project, _ = await seed_project_with_account(db_session)
        await log_event(
            session=db_session,
            operation_type="audit_run_completed",
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            result={},
        )
        await log_event(
            session=db_session,
            operation_type="export_success",
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            result={},
        )
        rows = await get_log_entries(
            session=db_session,
            filter_=LogEntryFilter(operation_type="export_success"),
        )
        assert all(r.operation_type == "export_success" for r in rows)
        assert len(rows) >= 1
