"""Phase 3 sub-batch B — manual-edit auto-normalize tests.

The §2.2 canon-rule auto-normalize must run on the manual-edit save
path so segment.text_content can never come to rest with leftover
violations. Idempotent w.r.t. translation-pipeline upstream normalize.

Tests drive the public `PUT /segments/{u}/text` endpoint through the
authenticated `auth_client` fixture (matches `tests/api/...` style).
"""

from __future__ import annotations

import httpx
import pytest

from tests.api._m4_fixtures import make_page_block_segment


@pytest.mark.asyncio
class TestManualEditAutoNormalize:
    async def _project_and_segment(self, auth_client: httpx.AsyncClient, *, text: str = "orig"):
        r = await auth_client.post("/projects", json={"name": "manual-edit-test"})
        assert r.status_code == 201
        project_uuid = r.json()["project_uuid"]
        f = await make_page_block_segment(project_uuid, text=text)
        return f

    async def test_arabic_indic_digit_silently_normalized(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        f = await self._project_and_segment(auth_client)
        r = await auth_client.put(
            f"/segments/{f.satz_uuid}/text",
            json={"after_text": "Page ٤٢ remix"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["text_content"] == "Page 42 remix"

    async def test_eastern_arabic_indic_normalized(self, auth_client: httpx.AsyncClient) -> None:
        f = await self._project_and_segment(auth_client)
        r = await auth_client.put(
            f"/segments/{f.satz_uuid}/text",
            json={"after_text": "Volume ۴۲"},
        )
        assert r.status_code == 200
        assert r.json()["text_content"] == "Volume 42"

    async def test_ei2_capital_k_normalized(self, auth_client: httpx.AsyncClient) -> None:
        f = await self._project_and_segment(auth_client)
        r = await auth_client.put(
            f"/segments/{f.satz_uuid}/text",
            json={"after_text": "Ḳur'an study"},
        )
        assert r.status_code == 200
        assert r.json()["text_content"] == "Qur'an study"

    async def test_ei2_dj_normalized(self, auth_client: httpx.AsyncClient) -> None:
        f = await self._project_and_segment(auth_client)
        r = await auth_client.put(
            f"/segments/{f.satz_uuid}/text",
            json={"after_text": "Djinn lore + DJINN + hadj"},
        )
        assert r.status_code == 200
        assert r.json()["text_content"] == "Jinn lore + JINN + haj"

    async def test_clean_text_unchanged(self, auth_client: httpx.AsyncClient) -> None:
        f = await self._project_and_segment(auth_client)
        r = await auth_client.put(
            f"/segments/{f.satz_uuid}/text",
            json={"after_text": "ordinary text 42 Qur'an"},
        )
        assert r.status_code == 200
        assert r.json()["text_content"] == "ordinary text 42 Qur'an"

    async def test_combined_violations_all_normalized(self, auth_client: httpx.AsyncClient) -> None:
        f = await self._project_and_segment(auth_client)
        r = await auth_client.put(
            f"/segments/{f.satz_uuid}/text",
            json={"after_text": "Ḳur'an page ٤٢, Djinn vol ۷"},
        )
        assert r.status_code == 200
        assert r.json()["text_content"] == "Qur'an page 42, Jinn vol 7"
