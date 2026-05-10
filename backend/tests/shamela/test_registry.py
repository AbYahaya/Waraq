"""Phase 2E — registry sanity tests."""

from __future__ import annotations

import pytest

from waraq.hadith.consensus import KUTUB_AS_SITTA_LABELS
from waraq.shamela import OPENITI_TEXTS, get_text_spec
from waraq.shamela.adapter import _collection_label_for_kutub
from waraq.shamela.lookup import ShamelaHit


class TestRegistryShape:
    def test_lisan_and_taj_present_canonical(self) -> None:
        slugs = {t.text_slug for t in OPENITI_TEXTS}
        # §3.5 explicitly names these as "independently queryable".
        assert "lisan_al_arab" in slugs
        assert "taj_al_arus" in slugs

    def test_six_kutub_as_sitta_present(self) -> None:
        kutub = {t.text_slug for t in OPENITI_TEXTS if t.is_kutub_as_sitta}
        assert kutub == {
            "sahih_bukhari",
            "sahih_muslim",
            "sunan_abi_dawud",
            "jami_at_tirmidhi",
            "sunan_an_nasai",
            "sunan_ibn_majah",
        }

    def test_kutub_labels_match_consensus_engine_recognition(self) -> None:
        """Each Kutub-as-Sitta slug's adapter-label must be recognized
        by the consensus engine's `KUTUB_AS_SITTA_LABELS` set —
        otherwise the §4.16.3 Kutub preference is structurally
        unreachable from Shamela hits."""
        for spec in OPENITI_TEXTS:
            if not spec.is_kutub_as_sitta:
                continue
            hit = ShamelaHit(
                section_uuid="x",
                text_slug=spec.text_slug,
                title=spec.title,
                author=spec.author,
                is_kutub_as_sitta=True,
                text_type="hadith",
                section_index=1,
                section_path="",
                text_arabic="",
                metadata={},
            )
            label = _collection_label_for_kutub(hit)
            assert label.casefold() in KUTUB_AS_SITTA_LABELS, (
                f"{spec.text_slug} → label {label!r} is not in "
                f"KUTUB_AS_SITTA_LABELS — Kutub preference will not "
                f"trigger for this collection"
            )

    def test_get_text_spec_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="unknown text_slug"):
            get_text_spec("not_a_real_text")

    def test_every_spec_has_source_uri(self) -> None:
        for spec in OPENITI_TEXTS:
            assert spec.source_uri.startswith("https://")
            assert "openiti" in spec.source_uri.lower()

    def test_text_types_use_canonical_vocabulary(self) -> None:
        valid = {"lexicon", "hadith", "fiqh", "tafsir", "other"}
        for spec in OPENITI_TEXTS:
            assert spec.text_type in valid
