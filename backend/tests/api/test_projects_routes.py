"""HTTP integration tests for /projects/*."""

from __future__ import annotations

import httpx
import pytest

from waraq.identity import new_uuid


@pytest.mark.asyncio
class TestProjectsCrud:
    async def test_create_and_get_project(self, auth_client: httpx.AsyncClient) -> None:
        # Create
        resp = await auth_client.post("/projects", json={"name": "Sahih Bukhari Vol 1"})
        assert resp.status_code == 201
        created = resp.json()
        assert created["name"] == "Sahih Bukhari Vol 1"
        assert created["active"] is True
        project_uuid = created["project_uuid"]

        # Get
        resp = await auth_client.get(f"/projects/{project_uuid}")
        assert resp.status_code == 200
        assert resp.json()["project_uuid"] == project_uuid

    async def test_list_returns_only_my_projects(self, auth_client: httpx.AsyncClient) -> None:
        await auth_client.post("/projects", json={"name": "Project A"})
        await auth_client.post("/projects", json={"name": "Project B"})

        resp = await auth_client.get("/projects")
        assert resp.status_code == 200
        names = sorted(p["name"] for p in resp.json())
        assert names == ["Project A", "Project B"]

    async def test_get_other_users_project_returns_404(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        # A random UUID that doesn't exist (or belongs to no one we know).
        resp = await auth_client.get(f"/projects/{new_uuid()}")
        assert resp.status_code == 404

    async def test_endpoints_require_auth(self, http_client: httpx.AsyncClient) -> None:
        resp = await http_client.post("/projects", json={"name": "x"})
        assert resp.status_code == 401
        resp = await http_client.get("/projects")
        assert resp.status_code == 401


# ---------------------------------------------------------------------
# Sub-batch P (out-of-phase, 2026-05-13) — project delete (inactivate)
# ---------------------------------------------------------------------


@pytest.mark.asyncio
class TestProjectDelete:
    """DELETE /projects/{u} inactivates the project per H-5 and
    cooperatively cancels any in-flight ocr_auto_run / translation jobs."""

    async def test_delete_returns_204_and_project_disappears(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        resp = await auth_client.post("/projects", json={"name": "to-delete"})
        project_uuid = resp.json()["project_uuid"]

        # Pre-condition: project is in the list.
        resp = await auth_client.get("/projects")
        assert any(p["project_uuid"] == project_uuid for p in resp.json())

        # Delete.
        resp = await auth_client.delete(f"/projects/{project_uuid}")
        assert resp.status_code == 204
        assert resp.content == b""

        # Post-condition: gone from list AND GET single returns 404.
        resp = await auth_client.get("/projects")
        assert all(p["project_uuid"] != project_uuid for p in resp.json())
        resp = await auth_client.get(f"/projects/{project_uuid}")
        assert resp.status_code == 404

    async def test_delete_unknown_project_returns_404(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        resp = await auth_client.delete(f"/projects/{new_uuid()}")
        assert resp.status_code == 404

    async def test_delete_other_users_project_returns_404(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        # Cross-account delete must look identical to "project doesn't
        # exist" — never leak existence (same pattern as the GET path).
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.conftest import _test_database_url
        from waraq.schemas import Account, Project

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        other_project_uuid = new_uuid()
        try:
            async with sm() as session, session.begin():
                acct = Account(
                    account_uuid=new_uuid(),
                    email=f"other-{new_uuid()}@waraq.test",
                    password_hash="x",
                    active=True,
                )
                session.add(acct)
                await session.flush()
                session.add(
                    Project(
                        project_uuid=other_project_uuid,
                        account_uuid=acct.account_uuid,
                        name="someone-elses",
                    )
                )
        finally:
            await engine.dispose()

        resp = await auth_client.delete(f"/projects/{other_project_uuid}")
        assert resp.status_code == 404

    async def test_delete_is_idempotent_via_404_after_first(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        """Once a project is inactivated, subsequent delete attempts hit
        the ownership helper's 404 — the service's own idempotency guard
        is defence-in-depth."""
        resp = await auth_client.post("/projects", json={"name": "double-delete"})
        project_uuid = resp.json()["project_uuid"]
        resp = await auth_client.delete(f"/projects/{project_uuid}")
        assert resp.status_code == 204
        resp = await auth_client.delete(f"/projects/{project_uuid}")
        assert resp.status_code == 404

    async def test_delete_cancels_in_flight_ocr_auto_run_job(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        """Cooperative cancel: any RUNNING/PENDING ocr_auto_run Job for
        the project gets `payload.cancel_requested=True` in the same
        transaction as the inactivation."""
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.conftest import _test_database_url
        from waraq.schemas import Job

        resp = await auth_client.post("/projects", json={"name": "with-job"})
        project_uuid = resp.json()["project_uuid"]

        # Seed a fake in-flight ocr_auto_run Job on this project.
        import uuid as _uuid

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        job_uuid = new_uuid()
        try:
            async with sm() as session, session.begin():
                session.add(
                    Job(
                        job_uuid=job_uuid,
                        job_type="ocr_auto_run",
                        state="running",
                        project_uuid=_uuid.UUID(project_uuid),
                        payload={
                            "total_pages": 5,
                            "processed_count": 1,
                            "cancel_requested": False,
                        },
                    )
                )
        finally:
            await engine.dispose()

        # Delete.
        resp = await auth_client.delete(f"/projects/{project_uuid}")
        assert resp.status_code == 204

        # The Job row got `cancel_requested=True`; state is unchanged
        # (the runner is the only writer that flips state — this is
        # cooperative cancel, not preemptive).
        engine2 = create_async_engine(_test_database_url(), future=True)
        sm2 = async_sessionmaker(bind=engine2, class_=AsyncSession, expire_on_commit=False)
        try:
            async with sm2() as session:
                refreshed = await session.get(Job, job_uuid)
                assert refreshed is not None
                assert (refreshed.payload or {})["cancel_requested"] is True
                assert refreshed.state == "running"  # runner hasn't reacted yet
        finally:
            await engine2.dispose()

    async def test_delete_makes_child_pages_unreachable(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        """Per the sub-batch P design ('no cascade'): child Page/Block/
        Segment rows stay active=True in the DB, but the tightened
        ownership helper rejects any chain rooted at an inactive
        project. Reachability proof via GET /pages/{u}."""
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.conftest import _test_database_url
        from waraq.schemas import Page

        resp = await auth_client.post("/projects", json={"name": "with-page"})
        project_uuid = resp.json()["project_uuid"]

        import uuid as _uuid

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        page_uuid = new_uuid()
        try:
            async with sm() as session, session.begin():
                session.add(
                    Page(
                        page_uuid=page_uuid,
                        project_uuid=_uuid.UUID(project_uuid),
                        page_index=1,
                    )
                )
        finally:
            await engine.dispose()

        # Pre-delete: page is reachable.
        resp = await auth_client.get(f"/pages/{page_uuid}")
        assert resp.status_code == 200

        # Delete the project.
        resp = await auth_client.delete(f"/projects/{project_uuid}")
        assert resp.status_code == 204

        # Post-delete: page 404s even though Page.active is still True
        # in the DB — the ownership helper rejects the chain.
        resp = await auth_client.get(f"/pages/{page_uuid}")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestDeleteProjectService:
    """Service-level coverage for `waraq.projects.delete_project` — flips
    Project.active, sets cancel_requested on in-flight jobs, idempotent."""

    async def test_service_flips_active_and_cancels(self) -> None:
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.conftest import _test_database_url
        from waraq.projects import delete_project
        from waraq.schemas import Account, Job, Project

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        acct_uuid = new_uuid()
        proj_uuid = new_uuid()
        job_uuid = new_uuid()
        try:
            async with sm() as session, session.begin():
                session.add(
                    Account(
                        account_uuid=acct_uuid,
                        email=f"svc-{new_uuid()}@waraq.test",
                        password_hash="x",
                        active=True,
                    )
                )
                await session.flush()
                session.add(
                    Project(
                        project_uuid=proj_uuid,
                        account_uuid=acct_uuid,
                        name="svc-test",
                    )
                )
                await session.flush()
                session.add(
                    Job(
                        job_uuid=job_uuid,
                        job_type="translation",
                        state="running",
                        project_uuid=proj_uuid,
                        payload={"cancel_requested": False, "x": 1},
                    )
                )
            async with sm() as session, session.begin():
                project = await session.get(Project, proj_uuid)
                assert project is not None
                await delete_project(session=session, project=project)
            # Verify in a fresh session.
            async with sm() as session:
                project = await session.get(Project, proj_uuid)
                assert project is not None
                assert project.active is False
                job = await session.get(Job, job_uuid)
                assert job is not None
                assert (job.payload or {})["cancel_requested"] is True
        finally:
            await engine.dispose()

    async def test_service_idempotent_on_inactive(self) -> None:
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from tests.conftest import _test_database_url
        from waraq.projects import delete_project
        from waraq.schemas import Account, Project

        engine = create_async_engine(_test_database_url(), future=True)
        sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        acct_uuid = new_uuid()
        proj_uuid = new_uuid()
        try:
            async with sm() as session, session.begin():
                session.add(
                    Account(
                        account_uuid=acct_uuid,
                        email=f"idemp-{new_uuid()}@waraq.test",
                        password_hash="x",
                        active=True,
                    )
                )
                await session.flush()
                session.add(
                    Project(
                        project_uuid=proj_uuid,
                        account_uuid=acct_uuid,
                        name="x",
                        active=False,  # already inactive
                    )
                )
            async with sm() as session, session.begin():
                project = await session.get(Project, proj_uuid)
                assert project is not None
                # Should be a no-op, no errors.
                returned = await delete_project(session=session, project=project)
                assert returned is project
                assert project.active is False
        finally:
            await engine.dispose()
