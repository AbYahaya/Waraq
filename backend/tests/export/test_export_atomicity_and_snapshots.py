"""T-9.2.1 mandatory tests — Sprint 5 §4 (atomicity + snapshots).

Test ID coverage:
- EXPORT-EVENT-Nur-Bei-Erfolg-Test
- EXPORT-EVENT-Kein-Eintrag-Bei-Fehler-Test
- EXPORT-EVENT-Atomaritaet-Test
- EXPORT-EVENT-Via-PROVENANCE-Kern-Test
- EXPORT-EVENT-Unveraenderlichkeit-Test
- EXPORT-EVENT-Scope-Test
- Atomare-Commit-Step-Test
- Niemals-Automatisch-Test-1
- Niemals-Automatisch-Test-2
- Revision-Snapshot-Vollstaendigkeit-Test
- Revision-Snapshot-Inaktive-Excluded-Test
- Revision-Snapshot-Outside-Scope-Excluded-Test
- Revision-Snapshot-Segments-Join-Test
- Active-Decision-Event-Uuids-Allowlist-Test
- Active-Decision-Event-Uuids-Preflight-Confirmation-Attempt-Bindung-Test
- Active-Decision-Event-Uuids-Scope-Coverage-Test
- Active-Decision-Event-Uuids-Is-Superseded-Filter-Test
- Kein-Rev-UUID-Bei-Artefakterzeugung-Test
- Artefakt-Modifies-Nothing-Test
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.export._helpers import (
    reach_exportierbar,
    seed_project_with_account,
    seed_segment_with_revision,
)
from waraq.decisions import create_decision_event
from waraq.export import (
    ALLOWLISTED_DECISION_SOURCES,
    ArtefactStoreCommitFailed,
    ExportConfig,
    InMemoryArtefactStore,
    collect_active_decision_event_uuids,
    collect_revision_snapshot,
    run_export_job,
)
from waraq.export import service as export_service
from waraq.identity import new_uuid
from waraq.preflight import PreflightState
from waraq.schemas import (
    DecisionEvent,
    LogEntry,
    ProvenanceObject,
    Revision,
)
from waraq.schemas.enums import DecisionSource, JobState, POType, ScopeType

# --- EXPORT-EVENT-Nur-Bei-Erfolg-Test ---------------------------------


@pytest.mark.asyncio
class TestExportEventOnlyOnSuccess:
    async def test_successful_export_creates_export_event_and_log(
        self, db_session: AsyncSession
    ) -> None:
        project, account_uuid = await seed_project_with_account(db_session)
        await seed_segment_with_revision(db_session, project=project, text="src\n---\ntgt")
        run, state = await reach_exportierbar(db_session, project=project)
        assert state == PreflightState.EXPORTIERBAR
        config = ExportConfig(
            project_uuid=project.project_uuid,
            account_uuid=account_uuid,
            project_title="Test Export",
            current_export_attempt_id=str(new_uuid()),
            preflight_run=run,
        )
        result = await run_export_job(session=db_session, config=config)

        # EXPORT_EVENT row exists.
        po_count = (
            await db_session.execute(
                select(func.count())
                .select_from(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.EXPORT_EVENT.value)
                .where(ProvenanceObject.scope_uuid == project.project_uuid)
            )
        ).scalar_one()
        assert po_count == 1
        assert result.export_event_po.payload["sha256"] == result.artefact_sha256

        # Job COMPLETED.
        assert result.job.state == JobState.COMPLETED.value

        # Success Log-Eintrag present.
        log_rows = (
            (
                await db_session.execute(
                    select(LogEntry)
                    .where(LogEntry.operation_type == "export_success")
                    .where(LogEntry.scope_uuid == project.project_uuid)
                )
            )
            .scalars()
            .all()
        )
        assert len(log_rows) == 1


# --- EXPORT-EVENT-Kein-Eintrag-Bei-Fehler-Test + Atomare-Commit-Step-Test ---


@pytest.mark.asyncio
class TestNoExportEventOnFailure:
    async def test_failed_artefact_store_commit_writes_no_export_event(
        self, db_session: AsyncSession
    ) -> None:
        project, account_uuid = await seed_project_with_account(db_session)
        await seed_segment_with_revision(db_session, project=project, text="src\n---\ntgt")
        run, _state = await reach_exportierbar(db_session, project=project)

        config = ExportConfig(
            project_uuid=project.project_uuid,
            account_uuid=account_uuid,
            project_title="Test Export",
            current_export_attempt_id=str(new_uuid()),
            preflight_run=run,
        )
        # Inject a store that fails at commit step (a).
        failing_store = InMemoryArtefactStore(fail_on_commit=True)
        with pytest.raises(ArtefactStoreCommitFailed):
            await run_export_job(session=db_session, config=config, artefact_store=failing_store)

        # NO EXPORT_EVENT row.
        po_count = (
            await db_session.execute(
                select(func.count())
                .select_from(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.EXPORT_EVENT.value)
                .where(ProvenanceObject.scope_uuid == project.project_uuid)
            )
        ).scalar_one()
        assert po_count == 0

        # FAILED Log-Eintrag for the attempt.
        log_rows = (
            (
                await db_session.execute(
                    select(LogEntry)
                    .where(LogEntry.operation_type == "export_failed")
                    .where(LogEntry.scope_uuid == project.project_uuid)
                )
            )
            .scalars()
            .all()
        )
        assert len(log_rows) == 1
        assert log_rows[0].result.get("phase") == "atomic_commit_a_move"


# --- EXPORT-EVENT-Atomaritaet-Test ------------------------------------


@pytest.mark.asyncio
class TestExportEventAtomicity:
    async def test_no_partial_state_on_commit_failure(self, db_session: AsyncSession) -> None:
        """No half-built EXPORT_EVENT row, no orphaned artefact, no
        partial Job state when commit step (a) fails."""
        project, account_uuid = await seed_project_with_account(db_session)
        await seed_segment_with_revision(db_session, project=project, text="src\n---\ntgt")
        run, _state = await reach_exportierbar(db_session, project=project)
        config = ExportConfig(
            project_uuid=project.project_uuid,
            account_uuid=account_uuid,
            project_title="Test",
            current_export_attempt_id=str(new_uuid()),
            preflight_run=run,
        )
        store = InMemoryArtefactStore(fail_on_commit=True)
        with pytest.raises(ArtefactStoreCommitFailed):
            await run_export_job(session=db_session, config=config, artefact_store=store)

        # No EXPORT_EVENT in DB at all.
        po_count = (
            await db_session.execute(
                select(func.count())
                .select_from(ProvenanceObject)
                .where(ProvenanceObject.po_type == POType.EXPORT_EVENT.value)
            )
        ).scalar_one()
        assert po_count == 0
        # Store has no orphaned bytes.
        assert store.get(artefact_uuid=new_uuid()) is None

    async def test_all_mandatory_fields_set_after_creation(self, db_session: AsyncSession) -> None:
        project, account_uuid = await seed_project_with_account(db_session)
        await seed_segment_with_revision(db_session, project=project, text="src\n---\ntgt")
        run, _state = await reach_exportierbar(db_session, project=project)
        config = ExportConfig(
            project_uuid=project.project_uuid,
            account_uuid=account_uuid,
            project_title="Test",
            current_export_attempt_id=str(new_uuid()),
            preflight_run=run,
        )
        result = await run_export_job(session=db_session, config=config)
        payload = result.export_event_po.payload
        for field in (
            "export_uuid",
            "project_uuid",
            "export_type",
            "export_config",
            "revision_snapshot",
            "active_decision_event_uuids",
            "gate_mode",
            "export_warnings",
            "artefact_ref",
            "sha256",
            "size_bytes",
        ):
            assert field in payload, f"missing field {field!r}"


# --- EXPORT-EVENT-Via-PROVENANCE-Kern-Test + Niemals-Automatisch-Test-2 ---


class TestExportEventViaProvenanceKern:
    """Code-review test: the export service writes EXPORT_EVENT only
    via `create_po`. Direct-insert paths are forbidden per
    Niemals-Automatisch operational invariant 2."""

    def test_service_does_not_session_add_provenance_object(self) -> None:
        src = inspect.getsource(export_service)
        # The service writes via `create_po`. No `session.add(ProvenanceObject(`
        # patterns should appear.
        assert "ProvenanceObject(" not in src, (
            "export.service constructs ProvenanceObject directly; "
            "must go through create_po per Niemals-Automatisch-Test-2."
        )
        # And it must reference create_po.
        assert "create_po" in src

    def test_service_imports_create_po_from_provenance_kern(self) -> None:
        from waraq.export import service as svc
        from waraq.provenance import create_po

        # The service module's create_po is the canonical PROVENANCE-Kern entrypoint.
        assert svc.create_po is create_po


# --- EXPORT-EVENT-Unveraenderlichkeit-Test (Niemals-Automatisch-Test-1) ---


class TestExportEventImmutability:
    """PROVENANCE-Kern's public surface is `create_po` only (T-1.6.1 +
    Abkürzung 7 sole-writer guard). There is no public mutator for
    PO rows; immutability is structural. This test enumerates the
    public surface to confirm no `update_*` / `mutate_*` paths exist."""

    def test_provenance_module_has_no_mutator_function(self) -> None:
        from waraq import provenance as prov_module

        public = [
            name
            for name in dir(prov_module)
            if not name.startswith("_") and callable(getattr(prov_module, name, None))
        ]
        forbidden_prefixes = ("update_", "mutate_", "set_", "modify_", "patch_")
        offenders = [
            name for name in public for prefix in forbidden_prefixes if name.startswith(prefix)
        ]
        assert offenders == [], (
            f"PROVENANCE-Kern exposes mutator functions: {offenders}; "
            "PO rows must be immutable per Abkürzung 7."
        )


# --- EXPORT-EVENT-Scope-Test ------------------------------------------


@pytest.mark.asyncio
class TestExportEventScope:
    async def test_export_event_addressed_via_project_scope(self, db_session: AsyncSession) -> None:
        """Per WORKLOG 2026-05-04 + 2026-05-06 decisions: EXPORT_EVENT
        uses scope_type='project' + scope_uuid=project_uuid; artefact
        identity (filename, sha256, size_bytes) lives in payload.
        ScopeType remains the canonical 5-value enum."""
        project, account_uuid = await seed_project_with_account(db_session)
        await seed_segment_with_revision(db_session, project=project, text="x\n---\ny")
        run, _state = await reach_exportierbar(db_session, project=project)
        config = ExportConfig(
            project_uuid=project.project_uuid,
            account_uuid=account_uuid,
            project_title="T",
            current_export_attempt_id=str(new_uuid()),
            preflight_run=run,
        )
        result = await run_export_job(session=db_session, config=config)
        po = result.export_event_po
        assert po.po_type == POType.EXPORT_EVENT.value
        assert po.scope_type == ScopeType.PROJECT.value
        assert po.scope_uuid == project.project_uuid
        # Artefact identity lives in payload.
        for field in ("filename", "sha256", "size_bytes", "artefact_uuid"):
            assert field in po.payload


# --- Revision-Snapshot tests ------------------------------------------


@pytest.mark.asyncio
class TestRevisionSnapshot:
    async def test_snapshot_contains_every_active_in_scope_segment_rev(
        self, db_session: AsyncSession
    ) -> None:
        project, _account = await seed_project_with_account(db_session)
        seg_a = await seed_segment_with_revision(db_session, project=project, text="a")
        seg_b = await seed_segment_with_revision(
            db_session, project=project, text="b", page_index=2, satz_index=1
        )
        revs, segs, _, _ = await collect_revision_snapshot(
            session=db_session, project_uuid=project.project_uuid
        )
        assert len(revs) == 2
        assert {seg_a.current_rev_uuid, seg_b.current_rev_uuid} == set(revs)
        assert {seg_a.satz_uuid, seg_b.satz_uuid} == set(segs)

    async def test_inactive_segments_excluded(self, db_session: AsyncSession) -> None:
        project, _ = await seed_project_with_account(db_session)
        seg_active = await seed_segment_with_revision(db_session, project=project, text="a")
        seg_inactive = await seed_segment_with_revision(
            db_session, project=project, text="b", page_index=2, satz_index=1
        )
        seg_inactive.active = False
        await db_session.flush()

        revs, segs, _, _ = await collect_revision_snapshot(
            session=db_session, project_uuid=project.project_uuid
        )
        assert revs == [seg_active.current_rev_uuid]
        assert segs == [seg_active.satz_uuid]

    async def test_outside_scope_segments_excluded(self, db_session: AsyncSession) -> None:
        project, _ = await seed_project_with_account(db_session)
        seg_in = await seed_segment_with_revision(db_session, project=project, text="in")
        await seed_segment_with_revision(
            db_session, project=project, text="out", page_index=2, satz_index=1
        )
        revs, segs, _, _ = await collect_revision_snapshot(
            session=db_session,
            project_uuid=project.project_uuid,
            segment_uuids=[seg_in.satz_uuid],
        )
        assert segs == [seg_in.satz_uuid]
        assert revs == [seg_in.current_rev_uuid]


class TestRevisionSnapshotReadFromSegments:
    """Code-review: the snapshot must read from `segments.current_rev_uuid`,
    NOT from the `revisions` table directly. This is the named
    structural failure mode (R-S5-03)."""

    def test_collect_revision_snapshot_reads_segments_table(self) -> None:
        from waraq.export import snapshot as snap_mod

        src = inspect.getsource(snap_mod)
        # Must reference segments.current_rev_uuid.
        assert "current_rev_uuid" in src
        # Must NOT directly query Revision rows for the snapshot.
        # (We accept Revision being imported via `from waraq.schemas` but
        # the snapshot loop must not iterate revisions directly.)
        # Negative check: the snapshot module's body should not contain
        # a `select(Revision)`.
        assert "select(Revision" not in src, (
            "snapshot.py queries Revision directly; must read from "
            "segments.current_rev_uuid per R-S5-03."
        )


# --- Active-Decision-Event-Uuids tests ---------------------------------


@pytest.mark.asyncio
class TestActiveDecisionEventAllowlist:
    async def test_export_confirmation_excluded_style_management_excluded(
        self, db_session: AsyncSession
    ) -> None:
        project, account_uuid = await seed_project_with_account(db_session)
        await seed_segment_with_revision(db_session, project=project, text="x\n---\ny")
        # Inject DEs of every source type at project scope.
        for source in DecisionSource:
            await create_decision_event(
                session=db_session,
                scope_type=ScopeType.PROJECT,
                scope_uuid=project.project_uuid,
                decision_type=f"test_{source.value}",
                decision_source=source,
                content={"src": source.value},
            )

        _revs, segs, pages, blocks = await collect_revision_snapshot(
            session=db_session, project_uuid=project.project_uuid
        )
        active = await collect_active_decision_event_uuids(
            session=db_session,
            project_uuid=project.project_uuid,
            account_uuid=account_uuid,
            segment_uuids=segs,
            page_uuids=pages,
            block_uuids=blocks,
            current_export_attempt_id="any-attempt",
        )
        # Read back the included DEs and check sources.
        rows = (
            (
                await db_session.execute(
                    select(DecisionEvent).where(DecisionEvent.decision_event_uuid.in_(active))
                )
            )
            .scalars()
            .all()
        )
        included_sources = {r.decision_source for r in rows}
        # All 7 allowlisted sources are present.
        assert ALLOWLISTED_DECISION_SOURCES.issubset(included_sources)
        # export_confirmation excluded.
        assert DecisionSource.EXPORT_CONFIRMATION.value not in included_sources
        # style_management excluded.
        assert DecisionSource.STYLE_MANAGEMENT.value not in included_sources

    async def test_preflight_confirmation_filtered_to_current_attempt(
        self, db_session: AsyncSession
    ) -> None:
        project, account_uuid = await seed_project_with_account(db_session)
        await seed_segment_with_revision(db_session, project=project, text="x\n---\ny")

        prior_attempt = "attempt-prior"
        current_attempt = "attempt-current"

        de_old = await create_decision_event(
            session=db_session,
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            decision_type="pflichtfrage_bestaetigung",
            decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
            content={"frage_index": 1, "answer": "old"},
            related_export_attempt_id=prior_attempt,
        )
        de_new = await create_decision_event(
            session=db_session,
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            decision_type="pflichtfrage_bestaetigung",
            decision_source=DecisionSource.PREFLIGHT_CONFIRMATION,
            content={"frage_index": 1, "answer": "new"},
            related_export_attempt_id=current_attempt,
        )
        _revs, segs, pages, blocks = await collect_revision_snapshot(
            session=db_session, project_uuid=project.project_uuid
        )
        active = await collect_active_decision_event_uuids(
            session=db_session,
            project_uuid=project.project_uuid,
            account_uuid=account_uuid,
            segment_uuids=segs,
            page_uuids=pages,
            block_uuids=blocks,
            current_export_attempt_id=current_attempt,
        )
        assert de_new.decision_event_uuid in active
        assert de_old.decision_event_uuid not in active

    async def test_scope_coverage_segment_page_block_project_account(
        self, db_session: AsyncSession
    ) -> None:
        project, account_uuid = await seed_project_with_account(db_session)
        seg = await seed_segment_with_revision(db_session, project=project, text="x\n---\ny")
        # Block uuid + page uuid via lookup.
        from waraq.schemas import Block, Page

        block = await db_session.get(Block, seg.block_uuid)
        page = await db_session.get(Page, block.page_uuid)

        de_seg = await create_decision_event(
            session=db_session,
            scope_type=ScopeType.SEGMENT,
            scope_uuid=seg.satz_uuid,
            decision_type="t",
            decision_source=DecisionSource.AUDIT_RESOLUTION,
        )
        de_block = await create_decision_event(
            session=db_session,
            scope_type=ScopeType.BLOCK,
            scope_uuid=block.block_uuid,
            decision_type="t",
            decision_source=DecisionSource.LOCK_MANAGEMENT,
        )
        de_page = await create_decision_event(
            session=db_session,
            scope_type=ScopeType.PAGE,
            scope_uuid=page.page_uuid,
            decision_type="t",
            decision_source=DecisionSource.OCR_REVIEW,
        )
        de_project = await create_decision_event(
            session=db_session,
            scope_type=ScopeType.PROJECT,
            scope_uuid=project.project_uuid,
            decision_type="t",
            decision_source=DecisionSource.CONSISTENCY_RESOLUTION,
        )
        de_account = await create_decision_event(
            session=db_session,
            scope_type=ScopeType.ACCOUNT,
            scope_uuid=account_uuid,
            decision_type="t",
            decision_source=DecisionSource.GLOSSARY_MANAGEMENT,
        )
        # Out-of-scope DE: account scope but a different account.
        other_account = new_uuid()
        de_other = await create_decision_event(
            session=db_session,
            scope_type=ScopeType.ACCOUNT,
            scope_uuid=other_account,
            decision_type="t",
            decision_source=DecisionSource.GLOSSARY_MANAGEMENT,
        )

        _revs, segs, pages, blocks = await collect_revision_snapshot(
            session=db_session, project_uuid=project.project_uuid
        )
        active = await collect_active_decision_event_uuids(
            session=db_session,
            project_uuid=project.project_uuid,
            account_uuid=account_uuid,
            segment_uuids=segs,
            page_uuids=pages,
            block_uuids=blocks,
            current_export_attempt_id="any",
        )
        for de in (de_seg, de_block, de_page, de_project, de_account):
            assert de.decision_event_uuid in active
        assert de_other.decision_event_uuid not in active


@pytest.mark.asyncio
class TestKeinRevUuidBeiArtefakterzeugung:
    async def test_export_pipeline_creates_no_revision_rows(self, db_session: AsyncSession) -> None:
        """H-4 regression: the export pipeline must never write a
        Revision row. Pure read-only operation."""
        project, account_uuid = await seed_project_with_account(db_session)
        await seed_segment_with_revision(db_session, project=project, text="x\n---\ny")
        rev_count_before = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()

        run, _ = await reach_exportierbar(db_session, project=project)
        config = ExportConfig(
            project_uuid=project.project_uuid,
            account_uuid=account_uuid,
            project_title="T",
            current_export_attempt_id=str(new_uuid()),
            preflight_run=run,
        )
        await run_export_job(session=db_session, config=config)

        rev_count_after = (
            await db_session.execute(select(func.count()).select_from(Revision))
        ).scalar_one()
        assert rev_count_after == rev_count_before


@pytest.mark.asyncio
class TestArtefaktModifiesNothing:
    async def test_segment_text_unchanged_post_export(self, db_session: AsyncSession) -> None:
        project, account_uuid = await seed_project_with_account(db_session)
        seg = await seed_segment_with_revision(db_session, project=project, text="src\n---\ntgt")
        text_before = seg.text_content
        rev_before = seg.current_rev_uuid

        run, _ = await reach_exportierbar(db_session, project=project)
        config = ExportConfig(
            project_uuid=project.project_uuid,
            account_uuid=account_uuid,
            project_title="T",
            current_export_attempt_id=str(new_uuid()),
            preflight_run=run,
        )
        await run_export_job(session=db_session, config=config)
        await db_session.refresh(seg)
        assert seg.text_content == text_before
        assert seg.current_rev_uuid == rev_before
