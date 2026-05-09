"""Phase 2B — translation sync + lookup tests.

Test fixtures use a distinct `_TEST_VERSION_*` source-version so they
don't collide with any production-style sync sitting in the same
database. All sync queries filter by source_version; lookup tests use
the new `source_version` parameter on `lookup_translation_aya`.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.quran import (
    GERMAN_RWWAD_KEY,
    QuranEncError,
    TranslationSource,
    lookup_translation_aya,
    sync_translation,
)
from waraq.schemas import QuranTranslationVerse

_TEST_VERSION_A = "phase2b-test-A"
_TEST_VERSION_B = "phase2b-test-B"


def _select_test_rows(*, version: str | None = None):
    stmt = select(QuranTranslationVerse).where(
        QuranTranslationVerse.translation_key == GERMAN_RWWAD_KEY
    )
    if version is not None:
        stmt = stmt.where(QuranTranslationVerse.source_version == version)
    else:
        # All versions starting with "phase2b-test-" — covers both
        # _TEST_VERSION_A and _TEST_VERSION_B in supersession tests.
        stmt = stmt.where(QuranTranslationVerse.source_version.like("phase2b-test-%"))
    return stmt


def _payload_for_sura(sura: int, *, lang_prefix: str = "DE") -> dict[str, object]:
    """Build a synthetic 2-verse sura payload."""
    return {
        "result": [
            {
                "sura": str(sura),
                "aya": "1",
                "arabic_text": "بِسْمِ ٱللَّهِ",
                "translation": f"{lang_prefix} sura {sura} aya 1",
                "footnotes": "",
            },
            {
                "sura": str(sura),
                "aya": "2",
                "arabic_text": "ٱلْحَمْدُ لِلَّهِ",
                "translation": f"{lang_prefix} sura {sura} aya 2",
                "footnotes": f"note for {sura}.2",
            },
        ]
    }


def _stub_fetcher_for(suras: list[int]):
    async def fetch(url: str) -> dict[str, object]:
        for sura in suras:
            if url.endswith(f"/{sura}"):
                return _payload_for_sura(sura)
        raise AssertionError(f"unexpected URL {url}")

    return fetch


# --- sync_translation -----------------------------------------------


@pytest.mark.asyncio
class TestSyncTranslation:
    async def test_initial_sync_inserts(self, db_session: AsyncSession) -> None:
        result = await sync_translation(
            session=db_session,
            translation_key=GERMAN_RWWAD_KEY,
            source_version=_TEST_VERSION_A,
            suras=[1, 2],
            fetcher=_stub_fetcher_for([1, 2]),
        )
        assert result.suras_fetched == 2
        assert result.verses_inserted == 4  # 2 suras × 2 verses each
        assert result.verses_updated == 0
        assert result.language == "de"

        rows = list(
            (await db_session.execute(_select_test_rows(version=_TEST_VERSION_A))).scalars()
        )
        assert len(rows) == 4
        assert all(r.language == "de" for r in rows)
        assert all(r.active for r in rows)

    async def test_same_version_re_sync_idempotent_when_unchanged(
        self, db_session: AsyncSession
    ) -> None:
        for _ in range(2):
            result = await sync_translation(
                session=db_session,
                translation_key=GERMAN_RWWAD_KEY,
                source_version=_TEST_VERSION_A,
                suras=[1],
                fetcher=_stub_fetcher_for([1]),
            )
        # Second run: nothing inserted, nothing updated.
        assert result.verses_inserted == 0
        assert result.verses_updated == 0

        rows = list(
            (await db_session.execute(_select_test_rows(version=_TEST_VERSION_A))).scalars()
        )
        assert len(rows) == 2

    async def test_same_version_with_changed_text_updates_in_place(
        self, db_session: AsyncSession
    ) -> None:
        await sync_translation(
            session=db_session,
            translation_key=GERMAN_RWWAD_KEY,
            source_version=_TEST_VERSION_A,
            suras=[1],
            fetcher=_stub_fetcher_for([1]),
        )

        async def changed(url: str) -> dict[str, object]:
            payload = _payload_for_sura(1)
            for entry in payload["result"]:  # type: ignore[union-attr]
                if isinstance(entry, dict) and entry.get("aya") == "1":
                    entry["translation"] = "DE sura 1 aya 1 — corrected"
            return payload

        result = await sync_translation(
            session=db_session,
            translation_key=GERMAN_RWWAD_KEY,
            source_version=_TEST_VERSION_A,
            suras=[1],
            fetcher=changed,
        )
        assert result.verses_inserted == 0
        assert result.verses_updated == 1

    async def test_new_version_supersedes_old(self, db_session: AsyncSession) -> None:
        await sync_translation(
            session=db_session,
            translation_key=GERMAN_RWWAD_KEY,
            source_version=_TEST_VERSION_A,
            suras=[1],
            fetcher=_stub_fetcher_for([1]),
        )
        result = await sync_translation(
            session=db_session,
            translation_key=GERMAN_RWWAD_KEY,
            source_version=_TEST_VERSION_B,
            suras=[1],
            fetcher=_stub_fetcher_for([1]),
        )
        assert result.verses_inserted == 2

        rows = list((await db_session.execute(_select_test_rows())).scalars())  # both A + B
        assert len(rows) == 4
        active = [r for r in rows if r.active]
        inactive = [r for r in rows if not r.active]
        assert len(active) == 2
        assert all(r.source_version == _TEST_VERSION_B for r in active)
        assert all(r.source_version == _TEST_VERSION_A for r in inactive)

    async def test_failed_sura_aborts_leaves_prior_active(self, db_session: AsyncSession) -> None:
        # Seed a successful prior sync.
        await sync_translation(
            session=db_session,
            translation_key=GERMAN_RWWAD_KEY,
            source_version=_TEST_VERSION_A,
            suras=[1],
            fetcher=_stub_fetcher_for([1]),
        )

        async def fail_fetcher(url: str) -> dict[str, object]:
            raise ValueError("simulated outage")

        with pytest.raises(QuranEncError):
            await sync_translation(
                session=db_session,
                translation_key=GERMAN_RWWAD_KEY,
                source_version=_TEST_VERSION_B,
                suras=[1],
                fetcher=fail_fetcher,
            )

        # The FAILED sync did not insert any new-version rows.
        new_version_rows = list(
            (await db_session.execute(_select_test_rows(version=_TEST_VERSION_B))).scalars()
        )
        assert new_version_rows == []


# --- lookup_translation_aya -----------------------------------------


@pytest.mark.asyncio
class TestLookupTranslationAya:
    async def test_translation_phase_uses_api_first(self, db_session: AsyncSession) -> None:
        # API stub answers; live data is irrelevant since API is hit first.
        result = await lookup_translation_aya(
            db_session,
            sura_index=1,
            aya_index=1,
            translation_key=GERMAN_RWWAD_KEY,
            phase="translation",
            fetcher=_stub_fetcher_for([1]),
        )
        assert result.source == TranslationSource.API_PRIMARY
        assert result.text == "DE sura 1 aya 1"

    async def test_translation_phase_falls_back_on_api_failure(
        self, db_session: AsyncSession
    ) -> None:
        # Seed local copy under a test version.
        await sync_translation(
            session=db_session,
            translation_key=GERMAN_RWWAD_KEY,
            source_version=_TEST_VERSION_A,
            suras=[1],
            fetcher=_stub_fetcher_for([1]),
        )

        async def api_down(url: str) -> dict[str, object]:
            raise ValueError("api outage")

        # Pin to test version so we hit the test row, not live data.
        result = await lookup_translation_aya(
            db_session,
            sura_index=1,
            aya_index=1,
            translation_key=GERMAN_RWWAD_KEY,
            phase="translation",
            fetcher=api_down,
            source_version=_TEST_VERSION_A,
        )
        assert result.source == TranslationSource.LOCAL_FALLBACK
        assert result.text == "DE sura 1 aya 1"

    async def test_ocr_phase_skips_api_entirely(self, db_session: AsyncSession) -> None:
        # Seed local copy.
        await sync_translation(
            session=db_session,
            translation_key=GERMAN_RWWAD_KEY,
            source_version=_TEST_VERSION_A,
            suras=[1],
            fetcher=_stub_fetcher_for([1]),
        )

        async def explode(url: str) -> dict[str, object]:
            raise AssertionError("API must not be hit during OCR phase")

        result = await lookup_translation_aya(
            db_session,
            sura_index=1,
            aya_index=1,
            translation_key=GERMAN_RWWAD_KEY,
            phase="ocr",
            fetcher=explode,
            source_version=_TEST_VERSION_A,
        )
        assert result.source == TranslationSource.LOCAL_FALLBACK
        assert result.text == "DE sura 1 aya 1"

    async def test_neither_api_nor_local_returns_not_found(self, db_session: AsyncSession) -> None:
        async def api_down(url: str) -> dict[str, object]:
            raise ValueError("api outage")

        # Pin to a test version that has nothing seeded → no fallback.
        result = await lookup_translation_aya(
            db_session,
            sura_index=1,
            aya_index=1,
            translation_key=GERMAN_RWWAD_KEY,
            phase="translation",
            fetcher=api_down,
            source_version=_TEST_VERSION_A,
        )
        assert result.source == TranslationSource.NOT_FOUND
        assert result.text is None

    async def test_inactive_local_row_not_returned(self, db_session: AsyncSession) -> None:
        # Initial sync.
        await sync_translation(
            session=db_session,
            translation_key=GERMAN_RWWAD_KEY,
            source_version=_TEST_VERSION_A,
            suras=[1],
            fetcher=_stub_fetcher_for([1]),
        )

        # New version supersedes — but only carry sura 1 aya 2.
        async def partial(url: str) -> dict[str, object]:
            return {
                "result": [
                    {
                        "sura": "1",
                        "aya": "2",
                        "arabic_text": "x",
                        "translation": "v2 only",
                        "footnotes": "",
                    }
                ]
            }

        await sync_translation(
            session=db_session,
            translation_key=GERMAN_RWWAD_KEY,
            source_version=_TEST_VERSION_B,
            suras=[1],
            fetcher=partial,
        )

        async def api_down(url: str) -> dict[str, object]:
            raise ValueError("api outage")

        # aya 1 in version A was inactivated by the version-B supersession;
        # version B did not include aya 1. With source_version pinned to
        # B, lookup falls through to NOT_FOUND.
        r1 = await lookup_translation_aya(
            db_session,
            sura_index=1,
            aya_index=1,
            translation_key=GERMAN_RWWAD_KEY,
            phase="ocr",
            fetcher=api_down,
            source_version=_TEST_VERSION_B,
        )
        assert r1.source == TranslationSource.NOT_FOUND

        # aya 2 has an active version-B row — found in fallback.
        r2 = await lookup_translation_aya(
            db_session,
            sura_index=1,
            aya_index=2,
            translation_key=GERMAN_RWWAD_KEY,
            phase="ocr",
            fetcher=api_down,
            source_version=_TEST_VERSION_B,
        )
        assert r2.source == TranslationSource.LOCAL_FALLBACK
        assert r2.text == "v2 only"
