"""Phase 2B — quranenc.com client tests (no network)."""

from __future__ import annotations

import pytest

from waraq.quran.quranenc import (
    ENGLISH_RWWAD_KEY,
    GERMAN_RWWAD_KEY,
    QuranEncError,
    fetch_sura,
)


# Synthetic payload matching the public quranenc.com response shape.
def _sura_1_payload() -> dict[str, object]:
    return {
        "result": [
            {
                "sura": "1",
                "aya": "1",
                "arabic_text": "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
                "translation": "Im Namen Allahs, des Allerbarmers, des Barmherzigen.",
                "footnotes": "",
            },
            {
                "sura": "1",
                "aya": "2",
                "arabic_text": "ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ",
                "translation": "Alles Lob gebührt Allah, dem Herrn der Welten.",
                "footnotes": "Erläuterung 1.",
            },
        ]
    }


@pytest.mark.asyncio
class TestFetchSura:
    async def test_happy_path_parses_payload(self) -> None:
        captured: list[str] = []

        async def stub_fetch(url: str) -> dict[str, object]:
            captured.append(url)
            return _sura_1_payload()

        verses = await fetch_sura(
            translation_key=GERMAN_RWWAD_KEY,
            sura_index=1,
            fetcher=stub_fetch,
        )
        assert len(verses) == 2
        assert verses[0].sura_index == 1
        assert verses[0].aya_index == 1
        assert verses[0].translation.startswith("Im Namen Allahs")
        assert verses[1].footnotes == "Erläuterung 1."
        # URL was constructed canonically.
        assert captured[0].endswith(f"/translation/sura/{GERMAN_RWWAD_KEY}/1")

    async def test_unknown_translation_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="unknown translation_key"):
            await fetch_sura(translation_key="bogus_key", sura_index=1)

    async def test_sura_out_of_range_rejected(self) -> None:
        with pytest.raises(ValueError, match="canonical range"):
            await fetch_sura(translation_key=GERMAN_RWWAD_KEY, sura_index=200)
        with pytest.raises(ValueError, match="canonical range"):
            await fetch_sura(translation_key=GERMAN_RWWAD_KEY, sura_index=0)

    async def test_retry_then_succeed(self) -> None:
        attempts = {"n": 0}

        async def flaky(url: str) -> dict[str, object]:
            attempts["n"] += 1
            if attempts["n"] < 2:
                raise ValueError("simulated bad json")
            return _sura_1_payload()

        verses = await fetch_sura(
            translation_key=GERMAN_RWWAD_KEY,
            sura_index=1,
            fetcher=flaky,
            retry_delay_seconds=0.0,
        )
        assert attempts["n"] == 2
        assert len(verses) == 2

    async def test_exhausted_retries_raises(self) -> None:
        async def always_fail(url: str) -> dict[str, object]:
            raise ValueError("permanent failure")

        with pytest.raises(QuranEncError, match=r"quranenc\.com fetch failed"):
            await fetch_sura(
                translation_key=GERMAN_RWWAD_KEY,
                sura_index=1,
                fetcher=always_fail,
                retry_delay_seconds=0.0,
            )

    async def test_payload_missing_result_array(self) -> None:
        async def bad_shape(url: str) -> dict[str, object]:
            return {"oops": "no result key"}

        with pytest.raises(QuranEncError):
            await fetch_sura(
                translation_key=GERMAN_RWWAD_KEY,
                sura_index=1,
                fetcher=bad_shape,
                retry_delay_seconds=0.0,
            )

    async def test_response_sura_mismatch_rejected(self) -> None:
        async def wrong_sura(url: str) -> dict[str, object]:
            payload = _sura_1_payload()
            # Lie about the sura number on each entry.
            for entry in payload["result"]:  # type: ignore[union-attr]
                if isinstance(entry, dict):
                    entry["sura"] = "2"
            return payload

        with pytest.raises(QuranEncError):
            await fetch_sura(
                translation_key=GERMAN_RWWAD_KEY,
                sura_index=1,
                fetcher=wrong_sura,
                retry_delay_seconds=0.0,
            )

    async def test_english_rwwad_key_accepted(self) -> None:
        async def stub(url: str) -> dict[str, object]:
            payload = _sura_1_payload()
            for entry in payload["result"]:  # type: ignore[union-attr]
                if isinstance(entry, dict):
                    entry["translation"] = "In the name of Allah..."
            return payload

        verses = await fetch_sura(
            translation_key=ENGLISH_RWWAD_KEY,
            sura_index=1,
            fetcher=stub,
        )
        assert verses[0].translation.startswith("In the name of Allah")

    async def test_empty_footnotes_normalized_to_none(self) -> None:
        async def stub(url: str) -> dict[str, object]:
            return _sura_1_payload()

        verses = await fetch_sura(
            translation_key=GERMAN_RWWAD_KEY,
            sura_index=1,
            fetcher=stub,
        )
        # First entry's footnotes is "" → normalized to None.
        assert verses[0].footnotes is None
        # Second entry has real footnotes preserved.
        assert verses[1].footnotes == "Erläuterung 1."
