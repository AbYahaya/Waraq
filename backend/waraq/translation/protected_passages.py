"""Protected-passage handling for translation.

Qur'an passages are resolved against the canonical reference carriers
before the general LLM path runs. Hadith passages are verified against
the reference stack first; when verification succeeds, the app may still
use the LLM translation path, but it keeps the verified source metadata
attached to the translation provenance.
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.db.session import get_settings
from waraq.hadith import HadithCandidateHit, Quellenrolle, run_full_hadith_verification
from waraq.hadith.dorar import DorarHadith, search_via_api as dorar_search_via_api
from waraq.preflight.enums import HadithStellenTyp
from waraq.preflight.hadith import record_hadith_status
from waraq.quran import (
    GERMAN_RWWAD_KEY,
    lookup_translation_aya,
    recognize_quran_passage,
    record_recognized_passage,
)
from waraq.schemas import (
    HadithAggregateResult,
    HadithPassageStatus,
    HadithSingleSourceResult,
    ProjectQuranPassage,
    Segment,
)
from waraq.shamela import find_by_skeleton, shamela_hits_to_consensus_candidates


@dataclass(frozen=True, slots=True)
class ProtectedTranslationResult:
    output_text: str | None
    source_kind: str
    skip_reason: str | None = None
    reference_payload: dict[str, Any] | None = None


async def resolve_protected_translation(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    segment: Segment,
    source_text: str,
) -> ProtectedTranslationResult | None:
    text = source_text.strip()
    if not text:
        return None

    quran_result = await _resolve_quran_translation(
        session=session,
        project_uuid=project_uuid,
        segment=segment,
        source_text=text,
    )
    if quran_result is not None:
        return quran_result

    hadith_result = await _resolve_hadith_translation(
        session=session,
        project_uuid=project_uuid,
        segment=segment,
        source_text=text,
    )
    return hadith_result


async def _resolve_quran_translation(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    segment: Segment,
    source_text: str,
) -> ProtectedTranslationResult | None:
    existing = (
        await session.execute(
            select(ProjectQuranPassage)
            .where(ProjectQuranPassage.project_uuid == project_uuid)
            .where(ProjectQuranPassage.satz_uuid == segment.satz_uuid)
            .where(ProjectQuranPassage.state != "rejected")
            .order_by(ProjectQuranPassage.detected_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None and existing.snapshot_translation_text:
        return ProtectedTranslationResult(
            output_text=existing.snapshot_translation_text,
            source_kind="quran",
            reference_payload=_build_quran_reference_payload_from_passage(existing),
        )

    recognition = await recognize_quran_passage(
        session,
        candidate_text=source_text,
    )
    if not recognition.matched:
        return None

    assert recognition.sura_index is not None
    assert recognition.aya_index_start is not None
    assert recognition.aya_index_end is not None

    verse_texts: list[str] = []
    for aya_index in range(recognition.aya_index_start, recognition.aya_index_end + 1):
        verse = await lookup_translation_aya(
            session,
            sura_index=recognition.sura_index,
            aya_index=aya_index,
            translation_key=GERMAN_RWWAD_KEY,
            phase="translation",
        )
        if verse.text is None:
            return ProtectedTranslationResult(
                output_text=None,
                source_kind="quran",
                skip_reason="protected_quran_translation_not_available",
                reference_payload=_build_quran_reference_payload_from_recognition(
                    recognition=recognition,
                    translation_key=GERMAN_RWWAD_KEY,
                    translation_source_version=None,
                ),
            )
        verse_texts.append(verse.text.strip())

    translation_text = "\n".join(text for text in verse_texts if text)
    if existing is None:
        await record_recognized_passage(
            session=session,
            project_uuid=project_uuid,
            satz_uuid=segment.satz_uuid,
            recognition=recognition,
            translation_text=translation_text,
            translation_key=GERMAN_RWWAD_KEY,
            translation_source_version=None,
        )

    return ProtectedTranslationResult(
        output_text=translation_text,
        source_kind="quran",
        reference_payload=(
            _build_quran_reference_payload_from_passage(existing)
            if existing is not None
            else _build_quran_reference_payload_from_recognition(
                recognition=recognition,
                translation_key=GERMAN_RWWAD_KEY,
                translation_source_version=None,
            )
        ),
    )


async def _resolve_hadith_translation(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    segment: Segment,
    source_text: str,
) -> ProtectedTranslationResult | None:
    aggregate = await _load_active_hadith_aggregate(
        session=session,
        segment=segment,
    )
    if aggregate is not None:
        existing_rows = await _load_hadith_single_source_rows_for_aggregate(
            session=session,
            aggregate_uuid=aggregate.aggregate_uuid,
        )
        return ProtectedTranslationResult(
            output_text=None,
            source_kind="hadith",
            reference_payload=_build_hadith_reference_payload(
                aggregate=aggregate,
                rows=existing_rows,
            ),
        )

    mandatory_hits = await _gather_hadith_candidates(session=session, query_text=source_text)
    if not mandatory_hits:
        return None

    outcome = await run_full_hadith_verification(
        session=session,
        project_uuid=project_uuid,
        satz_uuid=segment.satz_uuid,
        block_uuid=segment.block_uuid,
        ocr_rev_uuid=segment.current_rev_uuid,
        mandatory_hits=mandatory_hits,
        query=source_text,
        manually_trigger_extended=False,
    )
    if outcome.run is None:
        return None

    aggregate = await session.get(HadithAggregateResult, outcome.run.aggregate_uuid)
    hadith_rows = (
        await session.execute(
            select(HadithSingleSourceResult)
            .where(HadithSingleSourceResult.aggregate_uuid == outcome.run.aggregate_uuid)
        )
    ).scalars().all()
    if aggregate is None:
        return None
    return ProtectedTranslationResult(
        output_text=None,
        source_kind="hadith",
        reference_payload=_build_hadith_reference_payload(
            aggregate=aggregate,
            rows=hadith_rows,
        ),
    )


async def _load_active_hadith_aggregate(
    *,
    session: AsyncSession,
    segment: Segment,
) -> HadithAggregateResult | None:
    aggregate = (
        await session.execute(
            select(HadithAggregateResult)
            .where(HadithAggregateResult.satz_uuid == segment.satz_uuid)
            .where(HadithAggregateResult.is_aktiv.is_(True))
            .order_by(HadithAggregateResult.detected_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return aggregate


async def _load_hadith_single_source_rows_for_aggregate(
    *,
    session: AsyncSession,
    aggregate_uuid: _uuid.UUID,
) -> list[HadithSingleSourceResult]:
    return list(
        (
            await session.execute(
                select(HadithSingleSourceResult).where(
                    HadithSingleSourceResult.aggregate_uuid == aggregate_uuid
                )
            )
        ).scalars()
    )


def _build_quran_reference_payload_from_passage(
    passage: ProjectQuranPassage,
) -> dict[str, Any]:
    return {
        "kind": "quran",
        "title": "Qur'an reference",
        "subtitle": _format_quran_range(passage.sura_index, passage.aya_index_start, passage.aya_index_end),
        "sources": [
            _format_quran_source_line(
                label="Arabic source",
                source_name=passage.ar_source_name,
                source_version=passage.ar_source_version,
            ),
            _format_quran_source_line(
                label="Translation source",
                source_name=passage.translation_key or GERMAN_RWWAD_KEY,
                source_version=passage.translation_source_version,
            ),
        ],
        "sura_index": passage.sura_index,
        "aya_index_start": passage.aya_index_start,
        "aya_index_end": passage.aya_index_end,
        "state": passage.state,
    }


def _build_quran_reference_payload_from_recognition(
    *,
    recognition: Any,
    translation_key: str,
    translation_source_version: str | None,
) -> dict[str, Any]:
    assert recognition.sura_index is not None
    assert recognition.aya_index_start is not None
    assert recognition.aya_index_end is not None
    return {
        "kind": "quran",
        "title": "Qur'an reference",
        "subtitle": _format_quran_range(
            recognition.sura_index,
            recognition.aya_index_start,
            recognition.aya_index_end,
        ),
        "sources": [
            _format_quran_source_line(
                label="Arabic source",
                source_name=recognition.ar_source_name,
                source_version=recognition.ar_source_version,
            ),
            _format_quran_source_line(
                label="Translation source",
                source_name=translation_key,
                source_version=translation_source_version,
            ),
        ],
        "sura_index": recognition.sura_index,
        "aya_index_start": recognition.aya_index_start,
        "aya_index_end": recognition.aya_index_end,
        "state": "recognized",
    }


def _format_quran_range(sura_index: int, aya_index_start: int, aya_index_end: int) -> str:
    if aya_index_start == aya_index_end:
        return f"Surah {sura_index}, ayah {aya_index_start}"
    return f"Surah {sura_index}, ayahs {aya_index_start}-{aya_index_end}"


def _format_quran_source_line(
    *,
    label: str,
    source_name: str,
    source_version: str | None,
) -> str:
    if source_version:
        return f"{label}: {source_name} ({source_version})"
    return f"{label}: {source_name}"


def _build_hadith_reference_payload(
    *,
    aggregate: HadithAggregateResult,
    rows: list[HadithSingleSourceResult],
) -> dict[str, Any]:
    source_count = len(rows)
    source_label = "source" if source_count == 1 else "sources"
    subtitle_parts = [f"{source_count} verified {source_label}"]
    subtitle_parts.append(f"vocalization class {aggregate.vokalisierungsklasse}")
    if aggregate.vokalisierungs_konflikt:
        subtitle_parts.append("vocalization conflict detected")
    return {
        "kind": "hadith",
        "title": "Verified hadith sources",
        "subtitle": " • ".join(subtitle_parts),
        "sources": [_format_hadith_source_line(aggregate=aggregate, row=row) for row in rows],
        "aggregate_uuid": str(aggregate.aggregate_uuid),
        "vokalisierungsklasse": aggregate.vokalisierungsklasse,
        "vokalisierungs_konflikt": aggregate.vokalisierungs_konflikt,
    }


def _format_hadith_source_line(
    *,
    aggregate: HadithAggregateResult,
    row: HadithSingleSourceResult,
) -> str:
    headline = f"{row.source_name} ({row.quellen_rolle})"
    details: list[str] = []

    collection_label = _extract_hadith_collection_label(row)
    if collection_label:
        details.append(collection_label)

    locator = _extract_hadith_locator(row)
    if locator:
        details.append(locator)

    authenticity_grade = _extract_hadith_authenticity_grade(row)
    if authenticity_grade:
        details.append(f"grade: {authenticity_grade}")

    translation_languages = _extract_translation_languages(row)
    if translation_languages:
        details.append(f"site translations: {', '.join(translation_languages)}")

    if row.single_source_uuid == aggregate.reference_matn_source_uuid:
        details.append("reference matn")
    if row.single_source_uuid == aggregate.reference_vocalization_source_uuid:
        details.append("reference vocalization")

    if not details:
        return headline
    return f"{headline} — {'; '.join(details)}"


def _extract_hadith_collection_label(row: HadithSingleSourceResult) -> str | None:
    payload = row.raw_payload if isinstance(row.raw_payload, dict) else {}
    if row.source_name == "shamela":
        slug = _first_non_empty_str(payload, "text_slug")
        if slug:
            return _humanize_shamela_collection(slug)
    return _first_non_empty_str(payload, "collection", "book", "kitab")


def _extract_hadith_locator(row: HadithSingleSourceResult) -> str | None:
    payload = row.raw_payload if isinstance(row.raw_payload, dict) else {}
    if row.source_name == "sunnah.com":
        hadith_number = _first_non_empty_str(payload, "hadithNumber")
        if hadith_number:
            return f"hadith {hadith_number}"
    if row.source_name == "shamela":
        section_path = _first_non_empty_str(payload, "section_path", "hadith_number")
        if section_path:
            return f"section {section_path}"
    locator = _first_non_empty_str(payload, "page", "number", "rakm")
    if locator:
        return f"locator {locator}"
    return None


def _extract_hadith_authenticity_grade(row: HadithSingleSourceResult) -> str | None:
    payload = row.raw_payload if isinstance(row.raw_payload, dict) else {}
    grades = payload.get("grades")
    if isinstance(grades, list):
        values = [
            grade_value.strip()
            for entry in grades
            if isinstance(entry, dict)
            for grade_value in [_first_non_empty_str(entry, "grade")]
            if grade_value
        ]
        if values:
            return ", ".join(dict.fromkeys(values))
    return _first_non_empty_str(payload, "grade", "hokm", "judgment")


def _extract_translation_languages(row: HadithSingleSourceResult) -> list[str]:
    languages: list[str] = []
    for entry in row.website_uebersetzung:
        if not isinstance(entry, dict):
            continue
        lang = entry.get("lang")
        if isinstance(lang, str) and lang.strip():
            languages.append(lang.strip().upper())
    return list(dict.fromkeys(languages))


def _first_non_empty_str(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, int):
            return str(value)
    return None


def _humanize_shamela_collection(slug: str) -> str:
    mapping = {
        "sahih_bukhari": "Sahih al-Bukhari",
        "sahih_muslim": "Sahih Muslim",
        "sunan_abi_dawud": "Sunan Abi Dawud",
        "jami_at_tirmidhi": "Jami at-Tirmidhi",
        "sunan_an_nasai": "Sunan an-Nasa'i",
        "sunan_ibn_majah": "Sunan Ibn Majah",
    }
    return mapping.get(slug, slug.replace("_", " "))


async def _gather_hadith_candidates(
    *,
    session: AsyncSession,
    query_text: str,
) -> list[HadithCandidateHit]:
    if not query_text.strip():
        return []

    candidates: list[HadithCandidateHit] = []
    shamela_hits = await find_by_skeleton(
        session,
        candidate_text=query_text,
        only_kutub_as_sitta=True,
        limit=20,
    )
    candidates.extend(shamela_hits_to_consensus_candidates(shamela_hits))

    if not candidates and not _looks_like_hadith(query_text):
        return []

    settings = get_settings()
    try:
        dorar_hits = await dorar_search_via_api(
            query=query_text,
            base_url=settings.dorar_net_base_url,
            api_key=settings.dorar_net_api_key or None,
        )
    except Exception:
        dorar_hits = []
    candidates.extend(_dorar_to_candidates(dorar_hits))
    return candidates


def _dorar_to_candidates(hits: list[DorarHadith]) -> list[HadithCandidateHit]:
    return [
        HadithCandidateHit(
            source_name="dorar.net",
            quellen_rolle=Quellenrolle.PFLICHT,
            matn_arabic=hit.matn,
            matn_vocalized=None,
            isnad_chain=[hit.rawi] if hit.rawi else [],
            collection_label=hit.book or "",
            authenticity_grade=hit.grade,
            raw_payload=dict(hit.raw_payload),
        )
        for hit in hits
    ]


def _pick_preferred_hadith_translation(rows: list[HadithSingleSourceResult]) -> str | None:
    preferred_langs = ("de", "deu", "ger")
    for lang in preferred_langs:
        for row in rows:
            for entry in row.website_uebersetzung:
                if not isinstance(entry, dict):
                    continue
                entry_lang = entry.get("lang")
                text = entry.get("text")
                if (
                    isinstance(entry_lang, str)
                    and isinstance(text, str)
                    and text.strip()
                    and entry_lang.casefold() == lang
                ):
                    return text.strip()
    return None


def _looks_like_hadith(text: str) -> bool:
    lowered = text.strip()
    if not lowered:
        return False
    markers = (
        "قال رسول",
        "صلى الله عليه وسلم",
        "روى",
        "رواه",
        "حدثنا",
        "عن أبي",
        "عن عائشة",
        "عن ابن",
    )
    return any(marker in lowered for marker in markers)


async def _ensure_hadith_status(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    segment: Segment,
    stellen_typ: HadithStellenTyp,
) -> HadithPassageStatus:
    existing = (
        await session.execute(
            select(HadithPassageStatus)
            .where(HadithPassageStatus.satz_uuid == segment.satz_uuid)
            .where(HadithPassageStatus.project_uuid == project_uuid)
            .where(HadithPassageStatus.state == "offen")
            .where(HadithPassageStatus.active.is_(True))
            .order_by(HadithPassageStatus.detected_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    return await record_hadith_status(
        session=session,
        satz_uuid=segment.satz_uuid,
        project_uuid=project_uuid,
        stellen_typ=stellen_typ,
    )


__all__ = [
    "ProtectedTranslationResult",
    "resolve_protected_translation",
]
