from types import SimpleNamespace
from uuid import uuid4

from waraq.translation.protected_passages import (
    _build_hadith_reference_payload,
    _looks_like_hadith,
    _pick_preferred_hadith_translation,
    _quran_quote_matches_reference,
)
from waraq.translation.service import _apply_protected_output_replacements


def test_detects_common_hadith_markers() -> None:
    assert _looks_like_hadith("قال رسول الله صلى الله عليه وسلم")
    assert _looks_like_hadith("أن رسول الله ﷺ قال : «مَنْ حَفِظَ على أُمَّتِي أَرْبَعِينَ حَدِيثاً»")
    assert _looks_like_hadith("وفي رواية أبي الدرداء : وكنت له يوم القيامة شافعاً")
    assert not _looks_like_hadith("هذا شرح لغوي في باب الهمزة")


def test_quran_quote_similarity_tolerates_small_ocr_variants() -> None:
    quoted = (
        "قُلْ مَن يَرْزُقُكُم مِّنَ السَّمَاءِ وَالْأَرْضِ أَمَّن "
        "يَمْلِكُ السَّمْعَ وَالْأَبْصَرَ"
    )
    reference = (
        "قُلْ مَنْ يَرْزُقُكُمْ مِنَ السَّمَاءِ وَالْأَرْضِ أَمَّنْ "
        "يَمْلِكُ السَّمْعَ وَالْأَبْصَارَ"
    )
    assert _quran_quote_matches_reference(quoted, reference)


def test_protected_quran_replacement_is_canon_normalized() -> None:
    out = _apply_protected_output_replacements(
        "Allah sagte: ZXPROTECTEDQURAN0001ZX.",
        {
            "ZXPROTECTEDQURAN0001ZX": (
                "﴿Wahrlich, Allah vergibt nicht, dass Ihm Schirk beigesellt wird.﴾ "
                "[النساء: ٤٨]"
            )
        },
    )
    assert "[النساء: 48]" in out
    assert "٤٨" not in out


def test_prefers_german_hadith_translation_when_present() -> None:
    rows = [
        SimpleNamespace(
            website_uebersetzung=[
                {"lang": "en", "text": "English rendering"},
                {"lang": "de", "text": "Deutsche Fassung"},
            ]
        )
    ]
    assert _pick_preferred_hadith_translation(rows) == "Deutsche Fassung"


def test_returns_none_without_german_hadith_translation() -> None:
    rows = [
        SimpleNamespace(
            website_uebersetzung=[
                {"lang": "en", "text": "English rendering"},
            ]
        )
    ]
    assert _pick_preferred_hadith_translation(rows) is None


def test_builds_verified_hadith_reference_payload() -> None:
    winning_uuid = uuid4()
    payload = _build_hadith_reference_payload(
        aggregate=SimpleNamespace(
            aggregate_uuid=uuid4(),
            vokalisierungsklasse="V-1",
            vokalisierungs_konflikt=False,
            reference_matn_source_uuid=winning_uuid,
            reference_vocalization_source_uuid=None,
        ),
        rows=[
            SimpleNamespace(
                single_source_uuid=winning_uuid,
                source_name="sunnah.com",
                quellen_rolle="pflicht",
                raw_payload={
                    "collection": "bukhari",
                    "hadithNumber": "12",
                    "grades": [{"grade": "Sahih"}],
                },
                website_uebersetzung=[
                    {"lang": "en", "text": "English rendering"},
                    {"lang": "de", "text": "Deutsche Fassung"},
                ],
            )
        ],
    )

    assert payload["kind"] == "hadith"
    assert payload["title"] == "Verified hadith sources"
    assert "1 verified source" in payload["subtitle"]
    assert "vocalization class V-1" in payload["subtitle"]
    assert any("sunnah.com" in line for line in payload["sources"])
    assert any("hadith 12" in line for line in payload["sources"])
    assert any("reference matn" in line for line in payload["sources"])
