"""HTTP tests for /glossary and /entities."""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.asyncio
class TestGlossary:
    async def test_create_lookup_update_account_entry(self, auth_client: httpx.AsyncClient) -> None:
        # Create account-bound entry
        r = await auth_client.post(
            "/glossary/entries",
            json={
                "canonical_label": "Hadith",
                "language": "en",
                "binding_level": "account",
                "gloss": "Tradition",
            },
        )
        assert r.status_code == 201, r.text
        concept_id = r.json()["concept_id"]

        # Lookup hits
        r = await auth_client.post(
            "/glossary/lookup",
            json={
                "surface_form": "hadith"
            },  # account_uuid omitted → defaults inside service via account_uuid arg
        )
        # Without account_uuid, the service raises InvalidBindingScope → 400.
        assert r.status_code == 400

        # Provide account_uuid in lookup; need to fetch our own account_uuid first.
        me = (await auth_client.get("/auth/me")).json()
        r = await auth_client.post(
            "/glossary/lookup",
            json={"surface_form": "hadith", "account_uuid": me["account_uuid"]},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["found"] is True
        assert body["concept_id"] == concept_id

        # Update gloss
        r = await auth_client.patch(
            f"/glossary/entries/{concept_id}", json={"gloss": "Saying of the Prophet"}
        )
        assert r.status_code == 200
        assert r.json()["gloss"] == "Saying of the Prophet"

    async def test_create_project_bound_requires_project_uuid(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        r = await auth_client.post(
            "/glossary/entries",
            json={
                "canonical_label": "x",
                "language": "ar",
                "binding_level": "project",
            },
        )
        assert r.status_code == 400


@pytest.mark.asyncio
class TestEntities:
    async def test_create_and_list_entity(self, auth_client: httpx.AsyncClient) -> None:
        r = await auth_client.post(
            "/entities",
            json={
                "category": "scholar_or_person",
                "canonical_label": "Imam Bukhari",
                "language": "en",
                "binding_level": "account",
                "short_bio": "9th century hadith scholar",
            },
        )
        assert r.status_code == 201, r.text
        entity_id = r.json()["entity_id"]

        r = await auth_client.get("/entities")
        rows = r.json()
        assert any(row["entity_id"] == entity_id for row in rows)
