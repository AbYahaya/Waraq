"""HTTP tests for the M5-closeout endpoints that complete the UI E2E flow:

- POST /translation-jobs/{job_uuid}/run        (with monkeypatched translator)
- POST /projects/{uuid}/preflight/runs         (open)
- POST /projects/{uuid}/preflight/runs/{u}/pflichtfragen
- POST /projects/{uuid}/preflight/runs/{u}/evaluate
- POST /projects/{uuid}/exports                (trigger run_export_job)

The translation-run endpoint requires `OPENAI_API_KEY`; the test
monkeypatches the OpenAI translator factory so no real API call is
made.
"""

from __future__ import annotations

import httpx
import pytest

from tests.api._m4_fixtures import make_page_block_segment


async def _stub_translator(text: str, ctx: object) -> str:
    _ = ctx
    return f"DE::{text}"


@pytest.mark.asyncio
class TestTranslationRun:
    async def test_run_completes_pending_job(
        self,
        auth_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from waraq.api.routers import translation_router as router_mod

        monkeypatch.setattr(router_mod, "make_openai_translator", lambda: _stub_translator)
        # Force Primary-only path: pretend Gemini key isn't set so the
        # router's `except GeminiTranslatorUnconfigured` branch is taken.
        # This avoids real Gemini calls during HTTP-route smoke tests.
        from waraq.translation.gemini_translator import GeminiTranslatorUnconfigured

        def _no_gemini() -> object:
            raise GeminiTranslatorUnconfigured("test: Gemini stubbed off")

        monkeypatch.setattr(router_mod, "make_gemini_translator", _no_gemini)

        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        f = await make_page_block_segment(project_uuid, text="بسم الله")
        # Write uebersetzungsstart DE so start_translation_job is allowed.
        await auth_client.post(f"/projects/{project_uuid}/release-gate/start-translation", json={})
        r = await auth_client.post(
            f"/projects/{project_uuid}/translation-jobs",
            json={"segment_uuids": [str(f.satz_uuid)]},
        )
        assert r.status_code == 201, r.text
        job_uuid = r.json()["job_uuid"]

        r = await auth_client.post(f"/translation-jobs/{job_uuid}/run")
        # /run is now async — returns 202 with state=pending; the
        # background task drives the loop and is awaited by the ASGI
        # transport before this call returns. A follow-up GET sees the
        # final state.
        assert r.status_code == 202, r.text
        r = await auth_client.get(f"/translation-jobs/{job_uuid}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["state"] == "completed"
        # Progress counters land in payload — UI uses these to render
        # the progress bar.
        assert body["payload"]["chunks_total"] == 1
        assert body["payload"]["chunks_translated"] == 1

    async def test_run_unknown_job_returns_404(self, auth_client: httpx.AsyncClient) -> None:
        from uuid import uuid4

        r = await auth_client.post(f"/translation-jobs/{uuid4()}/run")
        assert r.status_code == 404

    async def test_cancel_aborts_background_run(
        self,
        auth_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Cancel before /run starts the background task: the task sees
        cancel_requested=true on its first iteration, fails with
        phase=user_cancelled, and never calls the translator."""
        from waraq.api.routers import translation_router as router_mod

        translator_calls: list[str] = []

        async def _track(text: str, ctx: object) -> str:
            _ = ctx
            translator_calls.append(text)
            return f"DE::{text}"

        monkeypatch.setattr(router_mod, "make_openai_translator", lambda: _track)
        from waraq.translation.gemini_translator import GeminiTranslatorUnconfigured

        def _no_gemini() -> object:
            raise GeminiTranslatorUnconfigured("test: Gemini stubbed off")

        monkeypatch.setattr(router_mod, "make_gemini_translator", _no_gemini)

        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        f = await make_page_block_segment(project_uuid, text="بسم الله")
        await auth_client.post(f"/projects/{project_uuid}/release-gate/start-translation", json={})
        r = await auth_client.post(
            f"/projects/{project_uuid}/translation-jobs",
            json={"segment_uuids": [str(f.satz_uuid)]},
        )
        job_uuid = r.json()["job_uuid"]

        # Cancel BEFORE /run so the cancel flag is committed when the
        # background task picks the job up. The first iteration sees
        # the flag and aborts.
        r = await auth_client.post(f"/translation-jobs/{job_uuid}/cancel")
        assert r.status_code == 200
        assert r.json()["payload"]["cancel_requested"] is True

        r = await auth_client.post(f"/translation-jobs/{job_uuid}/run")
        assert r.status_code == 202

        r = await auth_client.get(f"/translation-jobs/{job_uuid}")
        body = r.json()
        assert body["state"] == "failed"
        assert body["error"]["phase"] == "user_cancelled"
        # The translator was never invoked — cancel was respected
        # before the first chunk's LLM round-trip.
        assert translator_calls == []

    async def test_run_without_openai_key_returns_503(
        self,
        auth_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from waraq.api.routers import translation_router as router_mod
        from waraq.translation.openai_translator import OpenAITranslatorUnconfigured

        def _raises() -> object:
            raise OpenAITranslatorUnconfigured("OPENAI_API_KEY not set")

        monkeypatch.setattr(router_mod, "make_openai_translator", _raises)

        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        f = await make_page_block_segment(project_uuid, text="بسم")
        await auth_client.post(f"/projects/{project_uuid}/release-gate/start-translation", json={})
        r = await auth_client.post(
            f"/projects/{project_uuid}/translation-jobs",
            json={"segment_uuids": [str(f.satz_uuid)]},
        )
        job_uuid = r.json()["job_uuid"]
        r = await auth_client.post(f"/translation-jobs/{job_uuid}/run")
        assert r.status_code == 503


@pytest.mark.asyncio
class TestPreflightRoutes:
    async def test_full_preflight_flow(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        # Open run.
        r = await auth_client.post(f"/projects/{project_uuid}/preflight/runs")
        assert r.status_code == 201, r.text
        run_uuid = r.json()["run_uuid"]

        # Confirm all 4 Pflichtfragen.
        from tests.preflight._helpers import canonical_pflichtfrage_payload

        for i in range(1, 5):
            key, ans = canonical_pflichtfrage_payload(i)
            r = await auth_client.post(
                f"/projects/{project_uuid}/preflight/runs/{run_uuid}/pflichtfragen",
                json={"frage_index": i, "frage_key": key, "answer": ans},
            )
            assert r.status_code == 201, r.text
            assert r.json()["frage_index"] == i

        # Evaluate.
        r = await auth_client.post(f"/projects/{project_uuid}/preflight/runs/{run_uuid}/evaluate")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["state"] in ("exportierbar", "exportierbar_mit_warnungen")
        assert body["konfigurationsschicht_complete"] is True
        assert body["pflichtfrage_active_count"] == 4

    async def test_preflight_evaluate_blocked_without_pflichtfragen(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        r = await auth_client.post(f"/projects/{project_uuid}/preflight/runs")
        run_uuid = r.json()["run_uuid"]
        r = await auth_client.post(f"/projects/{project_uuid}/preflight/runs/{run_uuid}/evaluate")
        assert r.status_code == 200
        body = r.json()
        assert body["state"] == "blockiert"
        assert "konfigurationsschicht_unvollstaendig" in body["blocking_reasons"]

    async def test_pflichtfrage_index_out_of_range_400(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        r = await auth_client.post(f"/projects/{project_uuid}/preflight/runs")
        run_uuid = r.json()["run_uuid"]
        r = await auth_client.post(
            f"/projects/{project_uuid}/preflight/runs/{run_uuid}/pflichtfragen",
            json={"frage_index": 0, "frage_key": "x", "answer": {}},
        )
        # Pydantic 422 (out of [1,4] range).
        assert r.status_code == 422


@pytest.mark.asyncio
class TestExportTriggerRoute:
    async def test_full_export_flow(
        self,
        auth_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from waraq.api.routers import translation_router as router_mod

        monkeypatch.setattr(router_mod, "make_openai_translator", lambda: _stub_translator)
        # Force Primary-only path: pretend Gemini key isn't set so the
        # router's `except GeminiTranslatorUnconfigured` branch is taken.
        # This avoids real Gemini calls during HTTP-route smoke tests.
        from waraq.translation.gemini_translator import GeminiTranslatorUnconfigured

        def _no_gemini() -> object:
            raise GeminiTranslatorUnconfigured("test: Gemini stubbed off")

        monkeypatch.setattr(router_mod, "make_gemini_translator", _no_gemini)

        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        f = await make_page_block_segment(project_uuid, text="بسم")

        # Translate so the segment has a German rendering.
        await auth_client.post(f"/projects/{project_uuid}/release-gate/start-translation", json={})
        r = await auth_client.post(
            f"/projects/{project_uuid}/translation-jobs",
            json={"segment_uuids": [str(f.satz_uuid)]},
        )
        job_uuid = r.json()["job_uuid"]
        r = await auth_client.post(f"/translation-jobs/{job_uuid}/run")
        # 202 + background task; verify completion via GET.
        assert r.status_code == 202
        r = await auth_client.get(f"/translation-jobs/{job_uuid}")
        assert r.json()["state"] == "completed"

        # Run preflight.
        from tests.preflight._helpers import canonical_pflichtfrage_payload

        r = await auth_client.post(f"/projects/{project_uuid}/preflight/runs")
        run_uuid = r.json()["run_uuid"]
        for i in range(1, 5):
            key, ans = canonical_pflichtfrage_payload(i)
            await auth_client.post(
                f"/projects/{project_uuid}/preflight/runs/{run_uuid}/pflichtfragen",
                json={"frage_index": i, "frage_key": key, "answer": ans},
            )
        r = await auth_client.post(f"/projects/{project_uuid}/preflight/runs/{run_uuid}/evaluate")
        assert r.json()["state"] in ("exportierbar", "exportierbar_mit_warnungen")

        # Trigger export.
        r = await auth_client.post(
            f"/projects/{project_uuid}/exports",
            json={
                "project_uuid": project_uuid,
                "project_title": "Test Project",
                "preflight_run_uuid": run_uuid,
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["job_state"] == "completed"
        po_uuid = body["export_event_po_uuid"]
        assert len(body["artefact_sha256"]) == 64

        # Download DOCX.
        r = await auth_client.get(f"/exports/artefacts/{po_uuid}")
        assert r.status_code == 200
        assert r.content[:2] == b"PK"  # DOCX is a zip

    async def test_export_unknown_preflight_run_404(self, auth_client: httpx.AsyncClient) -> None:
        from uuid import uuid4

        r = await auth_client.post("/projects", json={"name": "p"})
        project_uuid = r.json()["project_uuid"]
        r = await auth_client.post(
            f"/projects/{project_uuid}/exports",
            json={
                "project_uuid": project_uuid,
                "project_title": "X",
                "preflight_run_uuid": str(uuid4()),
            },
        )
        assert r.status_code == 404
