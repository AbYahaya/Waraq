"""Phase 4 sub-batch J — POST /segments/{satz_uuid}/hadith/verify route."""

from __future__ import annotations

import uuid as _uuid
from typing import Any

import httpx
import pytest

from waraq.shamela import ingest_text, parse_section_lines

# Fixture: minimal Bukhari ingest that the P-2 path can match against.
_BUKHARI_FIXTURE = """\
# كتاب بدء الوحي
| إنما الأعمال بالنيات وإنما لكل امرئ ما نوى
"""


async def _project_with_segment(
    auth_client: httpx.AsyncClient, *, source_text: str
) -> tuple[_uuid.UUID, _uuid.UUID]:
    """Create a project + page + segment carrying `source_text` on the AR
    side. Returns (project_uuid, satz_uuid)."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from tests.conftest import _test_database_url
    from waraq.identity import new_uuid
    from waraq.invariant.enums import LockFlag
    from waraq.schemas import Block, Page, Segment

    r = await auth_client.post("/projects", json={"name": "hadith-verify-test"})
    project_uuid = _uuid.UUID(r.json()["project_uuid"])

    page_uuid = new_uuid()
    block_uuid = new_uuid()
    satz_uuid = new_uuid()

    engine = create_async_engine(_test_database_url(), future=True)
    sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with sm() as session, session.begin():
            session.add(Page(page_uuid=page_uuid, project_uuid=project_uuid, page_index=1))
            await session.flush()
            session.add(
                Block(
                    block_uuid=block_uuid,
                    page_uuid=page_uuid,
                    block_type="main_text",
                    block_index=0,
                )
            )
            await session.flush()
            session.add(
                Segment(
                    satz_uuid=satz_uuid,
                    block_uuid=block_uuid,
                    satz_index=0,
                    lock_flag=LockFlag.NONE,
                    text_content=f"{source_text}\n---\nGerman side",
                )
            )
            await session.flush()
            # Ingest Bukhari (Kutub-as-Sitta) so P-2 has something to find.
            await ingest_text(
                session=session,
                text_slug="sahih_bukhari",
                source_version="phase4j-test",
                sections=list(parse_section_lines(_BUKHARI_FIXTURE)),
            )
    finally:
        await engine.dispose()

    return project_uuid, satz_uuid


@pytest.mark.asyncio
class TestVerifyHappyPath:
    async def test_p2_only_path_persists_outcome(
        self,
        auth_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """No sunnah lookup + dorar API empty → only P-2 (Shamela) hits;
        run-summary still persisted because we have ≥ 1 candidate."""
        # Ensure neither sunnah nor dorar make real network calls.
        monkeypatch.delenv("SUNNAH_COM_API_KEY", raising=False)

        async def _no_dorar_hits(**_kwargs: Any) -> list[Any]:
            return []

        from waraq.api.routers import hadith_router as router_mod

        monkeypatch.setattr(router_mod, "dorar_search_via_api", _no_dorar_hits)

        _project_uuid, satz_uuid = await _project_with_segment(
            auth_client, source_text="إنما الأعمال بالنيات"
        )

        r = await auth_client.post(
            f"/segments/{satz_uuid}/hadith/verify",
            json={},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # P-2 hit Bukhari → at least one mandatory candidate.
        assert body["mandatory_count"] >= 1
        assert body["extended_count"] == 0
        # Skips include "no sunnah lookup address".
        assert "sunnah_no_lookup_address" in body["sources_skipped"]
        # Run was persisted.
        assert body["run"] is not None
        assert body["run"]["aggregate_uuid"]
        assert len(body["run"]["single_source_uuids"]) >= 1
        # Citations carry the canonical source name + Bukhari tag.
        assert any(c["source_name"] == "shamela" for c in body["citations"])

    async def test_no_candidates_no_persistence(
        self,
        auth_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Use a query string that will not skeleton-match the seeded
        # Bukhari fixture, plus dorar stubbed empty. No sunnah lookup.
        monkeypatch.delenv("SUNNAH_COM_API_KEY", raising=False)

        async def _no_dorar_hits(**_kwargs: Any) -> list[Any]:
            return []

        from waraq.api.routers import hadith_router as router_mod

        monkeypatch.setattr(router_mod, "dorar_search_via_api", _no_dorar_hits)

        _project_uuid, satz_uuid = await _project_with_segment(
            auth_client, source_text="نص لن يطابق أي مصدر بالمرة"
        )

        r = await auth_client.post(
            f"/segments/{satz_uuid}/hadith/verify",
            json={},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mandatory_count"] == 0
        assert body["extended_count"] == 0
        # No DB write happened.
        assert body["run"] is None


@pytest.mark.asyncio
class TestVerifyFailureModes:
    async def test_unknown_segment_returns_404(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.post(
            f"/segments/{_uuid.uuid4()}/hadith/verify",
            json={},
        )
        assert r.status_code == 404

    async def test_sunnah_apikey_missing_records_skip(
        self,
        auth_client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("SUNNAH_COM_API_KEY", raising=False)

        async def _no_dorar_hits(**_kwargs: Any) -> list[Any]:
            return []

        from waraq.api.routers import hadith_router as router_mod

        monkeypatch.setattr(router_mod, "dorar_search_via_api", _no_dorar_hits)

        _project_uuid, satz_uuid = await _project_with_segment(
            auth_client, source_text="إنما الأعمال بالنيات"
        )
        r = await auth_client.post(
            f"/segments/{satz_uuid}/hadith/verify",
            json={
                "sunnah_lookup": {
                    "collection": "bukhari",
                    "hadith_number": 1,
                },
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert "sunnah_api_key_missing" in body["sources_skipped"]


@pytest.mark.asyncio
class TestStage3OcrValidatorWiring:
    """Sub-batch J — page_runner now resolves production OCR validators
    automatically when API keys are set. Confirm graceful degradation
    when keys are absent."""

    async def test_resolver_returns_none_when_key_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from waraq.ocr import page_runner

        # Reset the cache so the resolver runs again.
        page_runner._OPENAI_OCR_VALIDATOR_RESOLVED = False
        page_runner._OPENAI_OCR_VALIDATOR_CACHE = None
        page_runner._GEMINI_OCR_VALIDATOR_RESOLVED = False
        page_runner._GEMINI_OCR_VALIDATOR_CACHE = None
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)

        assert page_runner._resolve_openai_ocr_validator() is None
        assert page_runner._resolve_gemini_ocr_validator() is None
