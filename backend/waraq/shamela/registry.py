"""Phase 2E v1.0 OpenITI text set + per-text metadata.

Per WORKLOG decision 2026-05-08: Shamela = OpenITI for v1.0. This
module enumerates the v1.0 corpus.

**Canonical floor** (§3.5 explicitly names):
  1. Lisān al-ʿArab (Ibn Manẓūr) — لسان العرب — major Arabic lexicon
  2. Tāj al-ʿArūs (al-Zabīdī) — تاج العروس — comprehensive lexicon

**Necessary for §4.16.3 consensus to function** (the 6 Kutub-as-Sitta
collections — without them the consensus engine's Kutub preference
is a no-op):
  3. Sahih al-Bukhari
  4. Sahih Muslim
  5. Sunan Abi Dawud
  6. Jami at-Tirmidhi
  7. Sunan an-Nasa'i
  8. Sunan Ibn Majah

**Supplementary** (v1.0 implementation choices — useful for the
user's Fiqh / classical-Islamic translation work; documented in
WORKLOG decisions, NOT canon amendments):
  9.  Muwaṭṭaʾ Mālik — موطأ مالك — early Hadith collection (Mālikī)
  10. al-Qāmūs al-Muḥīṭ (al-Fīrūzābādī) — القاموس المحيط — 3rd major lexicon
  11. Musnad Aḥmad — مسند أحمد — major Hadith collection beyond the Kutub-as-Sitta
  12. Sīrat Ibn Hishām — السيرة النبوية لابن هشام — most-cited Sīrah of the Prophet
  13. Tafsīr Ibn Kathīr — تفسير ابن كثير — most-accessible major Tafsir
  14. al-Mughnī (Ibn Qudāma) — المغني — major Ḥanbalī Fiqh (foundational)
  15. Bidāyat al-Mujtahid (Ibn Rushd) — بداية المجتهد — comparative Fiqh
  16. Zād al-Maʿād (Ibn al-Qayyim) — زاد المعاد — Sīrah + Fiqh + Hadith analysis

**v1.0 ≠ canonical "complete database"**. Canon §3.5 says Shamela is
a "complete database"; al-Maktaba al-Shāmila has ~7,000+ texts, OpenITI
has ~10,000. Our 16-text v1.0 set is a curated bootstrap covering
canonical floor + Kutub + supplementary high-value works for the
user's Fiqh translation use case. **The schema scales** — adding more
texts is a per-text re-ingest via `scripts/ingest_shamela.py`, not a
code change. Closing the v1.0 → canonical-completeness gap is
sustained scope work outside Phase 2.

`source_uri` is the canonical OpenITI GitHub URI. Users download the
text once via the CLI driver (`scripts/ingest_shamela.py`), then run
the ingest. No HTTP fetcher inside the running app — Shamela is
canonically a **local** source per §3.5.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OpenITITextSpec:
    """Static metadata for a v1.0 Shamela text.

    `text_slug` is the canonical identifier used as the join key
    between `shamela_registry` rows and `shamela_sections` rows. It
    is also exposed in API responses and in `HadithCandidateHit.source_name`
    when Shamela is the source — so don't change it lightly once
    ingested. `source_version` is the upstream OpenITI release tag
    (typically a date or git commit SHA).
    """

    text_slug: str
    title: str
    title_translit: str
    author: str
    text_type: str  # `lexicon` | `hadith` | `fiqh` | `tafsir` | `other`
    is_kutub_as_sitta: bool
    source_uri: str
    rationale: str  # Why this text is in the v1.0 set.


OPENITI_TEXTS: list[OpenITITextSpec] = [
    # --- Canonical floor (§3.5) ---
    OpenITITextSpec(
        text_slug="lisan_al_arab",
        title="لسان العرب",
        title_translit="Lisān al-ʿArab",
        author="ابن منظور (Ibn Manẓūr)",
        text_type="lexicon",
        is_kutub_as_sitta=False,
        source_uri="https://github.com/OpenITI/0700AH/tree/master/data/0711IbnManzur",
        rationale="§3.5 canonical: 'Lisān al-ʿArab (20+ volumes) treated within Shamela as independently queryable unit'.",
    ),
    OpenITITextSpec(
        text_slug="taj_al_arus",
        title="تاج العروس",
        title_translit="Tāj al-ʿArūs",
        author="مرتضى الزبيدي (al-Zabīdī)",
        text_type="lexicon",
        is_kutub_as_sitta=False,
        source_uri="https://github.com/OpenITI/1200AH/tree/master/data/1205Zabidi",
        rationale="§3.5 canonical: 'Tāj al-ʿArūs (40 volumes) treated within Shamela as independently queryable unit'.",
    ),
    # --- Kutub as-Sitta (necessary for §4.16.3 consensus) ---
    OpenITITextSpec(
        text_slug="sahih_bukhari",
        title="صحيح البخاري",
        title_translit="Sahih al-Bukhari",
        author="محمد بن إسماعيل البخاري (Bukhārī)",
        text_type="hadith",
        is_kutub_as_sitta=True,
        source_uri="https://github.com/OpenITI/0300AH/tree/master/data/0256Bukhari",
        rationale="Kutub-as-Sitta — required for §4.16.3 Kutub preference to apply.",
    ),
    OpenITITextSpec(
        text_slug="sahih_muslim",
        title="صحيح مسلم",
        title_translit="Sahih Muslim",
        author="مسلم بن الحجاج (Muslim ibn al-Ḥajjāj)",
        text_type="hadith",
        is_kutub_as_sitta=True,
        source_uri="https://github.com/OpenITI/0300AH/tree/master/data/0261Muslim",
        rationale="Kutub-as-Sitta.",
    ),
    OpenITITextSpec(
        text_slug="sunan_abi_dawud",
        title="سنن أبي داود",
        title_translit="Sunan Abi Dawud",
        author="أبو داود السجستاني (Abū Dāwūd al-Sijistānī)",
        text_type="hadith",
        is_kutub_as_sitta=True,
        source_uri="https://github.com/OpenITI/0300AH/tree/master/data/0275AbuDawudSijistani",
        rationale="Kutub-as-Sitta.",
    ),
    OpenITITextSpec(
        text_slug="jami_at_tirmidhi",
        title="جامع الترمذي",
        title_translit="Jami at-Tirmidhi",
        author="الترمذي (al-Tirmidhī)",
        text_type="hadith",
        is_kutub_as_sitta=True,
        source_uri="https://github.com/OpenITI/0300AH/tree/master/data/0279Tirmidhi",
        rationale="Kutub-as-Sitta.",
    ),
    OpenITITextSpec(
        text_slug="sunan_an_nasai",
        title="سنن النسائي",
        title_translit="Sunan an-Nasa'i",
        author="النسائي (al-Nasāʾī)",
        text_type="hadith",
        is_kutub_as_sitta=True,
        source_uri="https://github.com/OpenITI/0300AH/tree/master/data/0303Nasai",
        rationale="Kutub-as-Sitta.",
    ),
    OpenITITextSpec(
        text_slug="sunan_ibn_majah",
        title="سنن ابن ماجه",
        title_translit="Sunan Ibn Majah",
        author="ابن ماجه (Ibn Mājah)",
        text_type="hadith",
        is_kutub_as_sitta=True,
        source_uri="https://github.com/OpenITI/0300AH/tree/master/data/0273IbnMajah",
        rationale="Kutub-as-Sitta.",
    ),
    # --- Supplementary (v1.0 implementation choices) ---
    OpenITITextSpec(
        text_slug="muwatta_malik",
        title="موطأ مالك",
        title_translit="Muwaṭṭaʾ Mālik",
        author="مالك بن أنس (Mālik ibn Anas)",
        text_type="hadith",
        is_kutub_as_sitta=False,
        source_uri="https://github.com/OpenITI/0100AH/tree/master/data/0179MalikIbnAnas",
        rationale="Frequently cited early Hadith collection — important reference for the user's Fiqh translation work. v1.0 implementation choice.",
    ),
    OpenITITextSpec(
        text_slug="qamus_al_muhit",
        title="القاموس المحيط",
        title_translit="al-Qāmūs al-Muḥīṭ",
        author="الفيروزآبادي (al-Fīrūzābādī)",
        text_type="lexicon",
        is_kutub_as_sitta=False,
        source_uri="https://github.com/OpenITI/0800AH/tree/master/data/0817Firuzabadi",
        rationale="Third major classical Arabic lexicon (predecessor of Tāj al-ʿArūs) — complements Lisān + Tāj on lemma coverage. v1.0 implementation choice.",
    ),
    # --- Supplementary expansion (v1.0 closeout) ---
    OpenITITextSpec(
        text_slug="musnad_ahmad",
        title="مسند الإمام أحمد",
        title_translit="Musnad Ahmad",
        author="أحمد بن حنبل (Aḥmad ibn Ḥanbal)",
        text_type="hadith",
        is_kutub_as_sitta=False,
        source_uri="https://github.com/OpenITI/0300AH/tree/master/data/0241IbnHanbal",
        rationale="Largest extant Hadith collection (~28,000 hadiths) — frequently cited beyond the Kutub-as-Sitta. v1.0 implementation choice.",
    ),
    OpenITITextSpec(
        text_slug="sirat_ibn_hisham",
        title="السيرة النبوية لابن هشام",
        title_translit="Sirat Ibn Hisham",
        author="ابن هشام (Ibn Hishām)",
        text_type="other",
        is_kutub_as_sitta=False,
        source_uri="https://github.com/OpenITI/0300AH/tree/master/data/0218IbnHisham",
        rationale="Most-cited Sīrah of the Prophet — foundational source for biographical references in Fiqh + classical Islamic literature. v1.0 implementation choice.",
    ),
    OpenITITextSpec(
        text_slug="tafsir_ibn_kathir",
        title="تفسير ابن كثير",
        title_translit="Tafsīr Ibn Kathīr",
        author="ابن كثير (Ibn Kathīr)",
        text_type="tafsir",
        is_kutub_as_sitta=False,
        source_uri="https://github.com/OpenITI/0800AH/tree/master/data/0774IbnKathir",
        rationale="Most-accessible major Tafsīr work — frequent citation source in classical Islamic literature. v1.0 implementation choice.",
    ),
    OpenITITextSpec(
        text_slug="al_mughni",
        title="المغني",
        title_translit="al-Mughnī",
        author="ابن قدامة (Ibn Qudāma)",
        text_type="fiqh",
        is_kutub_as_sitta=False,
        source_uri="https://github.com/OpenITI/0700AH/tree/master/data/0620IbnQudamaMaqdisi",
        rationale="Foundational Ḥanbalī Fiqh encyclopedia — central reference for the user's Fiqh translation work. v1.0 implementation choice.",
    ),
    OpenITITextSpec(
        text_slug="bidayat_al_mujtahid",
        title="بداية المجتهد ونهاية المقتصد",
        title_translit="Bidāyat al-Mujtahid",
        author="ابن رشد الحفيد (Ibn Rushd al-Ḥafīd)",
        text_type="fiqh",
        is_kutub_as_sitta=False,
        source_uri="https://github.com/OpenITI/0700AH/tree/master/data/0595IbnRushdHafid",
        rationale="Comparative Fiqh across the four schools — exceptional value for translation work that needs to render cross-school positions. v1.0 implementation choice.",
    ),
    OpenITITextSpec(
        text_slug="zad_al_maad",
        title="زاد المعاد",
        title_translit="Zād al-Maʿād",
        author="ابن قيم الجوزية (Ibn al-Qayyim)",
        text_type="fiqh",
        is_kutub_as_sitta=False,
        source_uri="https://github.com/OpenITI/0800AH/tree/master/data/0751IbnQayyimAlJawziyya",
        rationale="Combines Sīrah + Fiqh + Hadith analysis — high citation density across all three. v1.0 implementation choice.",
    ),
]


_BY_SLUG: dict[str, OpenITITextSpec] = {t.text_slug: t for t in OPENITI_TEXTS}


def get_text_spec(text_slug: str) -> OpenITITextSpec:
    """Return the registry spec for `text_slug`. Raises KeyError when
    the slug isn't in the v1.0 set."""
    if text_slug not in _BY_SLUG:
        raise KeyError(f"unknown text_slug {text_slug!r}; v1.0 set: {sorted(_BY_SLUG)}")
    return _BY_SLUG[text_slug]


__all__ = ["OPENITI_TEXTS", "OpenITITextSpec", "get_text_spec"]
