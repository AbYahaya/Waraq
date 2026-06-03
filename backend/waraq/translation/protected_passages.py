"""Protected-passage handling for translation.

Qur'an passages are resolved against the canonical reference carriers
before the general LLM path runs. Hadith passages are verified against
the reference stack first; when verification succeeds, the app may still
use the LLM translation path, but it keeps the verified source metadata
attached to the translation provenance.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.db.session import get_settings
from waraq.external.model_u import ModelUClassA, ModelUClassB
from waraq.hadith import HadithCandidateHit, Quellenrolle, run_full_hadith_verification
from waraq.hadith.citation_extract import extract_sunnah_lookup
from waraq.hadith.detection import looks_like_hadith
from waraq.hadith.dorar import DorarHadith
from waraq.hadith.dorar import search_via_api as dorar_search_via_api
from waraq.hadith.sunnah import SunnahApiKeyMissing, SunnahHadith
from waraq.hadith.sunnah import fetch_hadith as sunnah_fetch_hadith
from waraq.preflight.enums import HadithStellenTyp
from waraq.preflight.hadith import record_hadith_status
from waraq.quran import (
    ENGLISH_RWWAD_KEY,
    GERMAN_RWWAD_KEY,
    RecognitionResult,
    lookup_aya,
    lookup_translation_aya,
    parse_author_citation,
    recognize_quran_passage,
    record_recognized_passage,
)
from waraq.arabic import to_skeleton
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
    source_text_override: str | None = None
    output_replacements: dict[str, str] | None = None


_INLINE_QURAN_RE = re.compile(
    r"﴿(?P<ayah>[^﴾]{3,500})﴾(?P<citation>\s*[\[\(][^\]\)]{1,100}[\]\)])?"
)
_GUILLEMET_QURAN_RE = re.compile(r"«(?P<body>[^»\n]{3,700}?)(?P<close>»|\))")
_QURAN_QUOTE_SEPARATORS = ("—", "–", "-")


@dataclass(frozen=True, slots=True)
class _InlineQuranMatch:
    start: int
    end: int
    literal: str
    quoted_ayah: str
    citation: str


async def resolve_protected_translation(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    segment: Segment,
    source_text: str,
    target_language: str | None = None,
) -> ProtectedTranslationResult | None:
    text = source_text.strip()
    if not text:
        return None

    quran_result = await _resolve_quran_translation(
        session=session,
        project_uuid=project_uuid,
        segment=segment,
        source_text=text,
        target_language=target_language,
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
    target_language: str | None,
) -> ProtectedTranslationResult | None:
    translation_key = _quran_translation_key_for_target_language(target_language)
    inline_result = await _resolve_inline_quran_translations(
        session=session,
        project_uuid=project_uuid,
        segment=segment,
        source_text=source_text,
        translation_key=translation_key,
    )
    if inline_result is not None:
        return inline_result

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
        if existing.translation_key == translation_key:
            return ProtectedTranslationResult(
                output_text=existing.snapshot_translation_text,
                source_kind="quran",
                reference_payload=_build_quran_reference_payload_from_passage(existing),
            )
        # Older records may not know the requested target carrier. Do a fresh lookup
        # instead of reusing the wrong language.

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
            translation_key=translation_key,
            phase="translation",
        )
        if verse.text is None:
            return ProtectedTranslationResult(
                output_text=None,
                source_kind="quran",
                skip_reason="protected_quran_translation_not_available",
                reference_payload=_build_quran_reference_payload_from_recognition(
                    recognition=recognition,
                    translation_key=translation_key,
                    translation_source_version=None,
                ),
            )
        verse_texts.append(verse.text.strip())

    translation_text = "\n".join(text for text in verse_texts if text)
    if existing is None or existing.translation_key != translation_key:
        existing = (
            await session.execute(
                select(ProjectQuranPassage)
                .where(ProjectQuranPassage.project_uuid == project_uuid)
                .where(ProjectQuranPassage.satz_uuid == segment.satz_uuid)
                .where(ProjectQuranPassage.sura_index == recognition.sura_index)
                .where(ProjectQuranPassage.aya_index_start == recognition.aya_index_start)
                .where(ProjectQuranPassage.aya_index_end == recognition.aya_index_end)
                .where(ProjectQuranPassage.translation_key == translation_key)
                .where(ProjectQuranPassage.state != "rejected")
                .order_by(ProjectQuranPassage.detected_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing is None:
            await record_recognized_passage(
                session=session,
                project_uuid=project_uuid,
                satz_uuid=segment.satz_uuid,
                recognition=recognition,
                translation_text=translation_text,
                translation_key=translation_key,
                translation_source_version=None,
            )

    return ProtectedTranslationResult(
        output_text=translation_text,
        source_kind="quran",
        reference_payload=(
            _build_quran_reference_payload_from_passage(existing)
            if existing is not None and existing.translation_key == translation_key
            else _build_quran_reference_payload_from_recognition(
                recognition=recognition,
                translation_key=translation_key,
                translation_source_version=None,
            )
        ),
    )


async def _resolve_inline_quran_translations(
    *,
    session: AsyncSession,
    project_uuid: _uuid.UUID,
    segment: Segment,
    source_text: str,
    translation_key: str,
) -> ProtectedTranslationResult | None:
    matches = _collect_inline_quran_matches(source_text)
    if not matches:
        return None

    output_replacements: dict[str, str] = {}
    source_parts: list[str] = []
    last_end = 0
    payload_items: list[dict[str, Any]] = []
    matched_any = False

    for idx, match in enumerate(matches, start=1):
        source_parts.append(source_text[last_end : match.start])
        quoted_ayah = match.quoted_ayah
        citation = match.citation
        recognition = await _recognize_inline_quran_quote(
            session,
            quoted_ayah=quoted_ayah,
            citation=citation,
        )
        if not recognition.matched:
            source_parts.append(match.literal)
            last_end = match.end
            continue

        assert recognition.sura_index is not None
        assert recognition.aya_index_start is not None
        assert recognition.aya_index_end is not None

        verse_texts: list[str] = []
        for aya_index in range(recognition.aya_index_start, recognition.aya_index_end + 1):
            verse = await lookup_translation_aya(
                session,
                sura_index=recognition.sura_index,
                aya_index=aya_index,
                translation_key=translation_key,
                phase="translation",
            )
            if verse.text is None:
                return ProtectedTranslationResult(
                    output_text=None,
                    source_kind="quran",
                    skip_reason="protected_quran_translation_not_available",
                    reference_payload=_build_quran_reference_payload_from_recognition(
                        recognition=recognition,
                        translation_key=translation_key,
                        translation_source_version=None,
                    ),
                )
            verse_texts.append(verse.text.strip())

        translation_text = "\n".join(text for text in verse_texts if text)
        await record_recognized_passage(
            session=session,
            project_uuid=project_uuid,
            satz_uuid=segment.satz_uuid,
            recognition=recognition,
            translation_text=translation_text,
            translation_key=translation_key,
            translation_source_version=None,
        )

        placeholder = f"ZXPROTECTEDQURAN{idx:04d}ZX"
        replacement = f"﴿{translation_text}﴾"
        if citation:
            replacement = f"{replacement} {citation}"
        output_replacements[placeholder] = replacement
        source_parts.append(placeholder)
        payload_items.append(
            {
                "placeholder": placeholder,
                "replacement": replacement,
                "sura_index": recognition.sura_index,
                "aya_index_start": recognition.aya_index_start,
                "aya_index_end": recognition.aya_index_end,
                "author_citation": citation or None,
                "translation_key": translation_key,
            }
        )
        matched_any = True
        last_end = match.end

    source_parts.append(source_text[last_end:])
    if not matched_any:
        return None

    return ProtectedTranslationResult(
        output_text=None,
        source_kind="quran",
        reference_payload={
            "kind": "quran",
            "title": "Protected inline Qur'an references",
            "subtitle": f"{len(output_replacements)} protected inline passage(s)",
            "sources": [
                _format_quran_source_line(
                    label="Translation source",
                    source_name=translation_key,
                    source_version=None,
                )
            ],
            "inline_passages": payload_items,
        },
        source_text_override="".join(source_parts),
        output_replacements=output_replacements,
    )


def _collect_inline_quran_matches(source_text: str) -> list[_InlineQuranMatch]:
    matches: list[_InlineQuranMatch] = []
    occupied: list[tuple[int, int]] = []

    for match in _INLINE_QURAN_RE.finditer(source_text):
        item = _InlineQuranMatch(
            start=match.start(),
            end=match.end(),
            literal=match.group(0),
            quoted_ayah=match.group("ayah").strip(),
            citation=(match.group("citation") or "").strip(),
        )
        matches.append(item)
        occupied.append((item.start, item.end))

    for match in _GUILLEMET_QURAN_RE.finditer(source_text):
        if any(match.start() < end and match.end() > start for start, end in occupied):
            continue
        split = _split_quran_quote_with_citation(match.group("body"))
        if split is None:
            continue
        quoted_ayah, citation = split
        item = _InlineQuranMatch(
            start=match.start(),
            end=match.end(),
            literal=match.group(0),
            quoted_ayah=quoted_ayah,
            citation=citation,
        )
        matches.append(item)
        occupied.append((item.start, item.end))

    return sorted(matches, key=lambda item: item.start)


def _split_quran_quote_with_citation(body: str) -> tuple[str, str] | None:
    for separator in _QURAN_QUOTE_SEPARATORS:
        positions = [match.start() for match in re.finditer(re.escape(separator), body)]
        for pos in reversed(positions):
            quote = body[:pos].strip(" \t\r\n،؛:؟?\"'")
            citation = body[pos + len(separator) :].strip(" \t\r\n،؛:.?؟\"'")
            if len(quote) < 3:
                continue
            if parse_author_citation(citation) is not None:
                return quote, citation
    return None


async def _recognize_inline_quran_quote(
    session: AsyncSession,
    *,
    quoted_ayah: str,
    citation: str,
) -> RecognitionResult:
    recognition = await recognize_quran_passage(
        session,
        candidate_text=quoted_ayah,
    )
    if recognition.matched:
        return recognition

    parsed_citation = parse_author_citation(citation)
    if parsed_citation is None:
        return recognition
    sura_index, aya_index_start, aya_index_end = parsed_citation
    verses = []
    for aya_index in range(aya_index_start, aya_index_end + 1):
        verse = await lookup_aya(
            session,
            sura_index=sura_index,
            aya_index=aya_index,
        )
        if verse is None:
            return recognition
        verses.append(verse)
    if not verses:
        return recognition

    matched_text = " ".join(verse.text_vocalized for verse in verses)
    if not _quran_quote_matches_reference(quoted_ayah, matched_text):
        return recognition

    first = verses[0]
    return RecognitionResult(
        matched=True,
        confidence=0.9,
        sura_index=sura_index,
        aya_index_start=aya_index_start,
        aya_index_end=aya_index_end,
        ar_source_name=first.source_name,
        ar_source_version=first.source_version,
        matched_text_vocalized=matched_text,
    )


def _quran_quote_matches_reference(quoted_ayah: str, reference_text: str) -> bool:
    quoted = to_skeleton(quoted_ayah).replace(" ", "")
    reference = to_skeleton(reference_text).replace(" ", "")
    if not quoted or not reference:
        return False
    if quoted == reference or quoted in reference or reference in quoted:
        return True
    return SequenceMatcher(a=quoted, b=reference).ratio() >= 0.78


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
        await _ensure_hadith_status(
            session=session,
            project_uuid=project_uuid,
            segment=segment,
            stellen_typ=_stellen_typ_for_existing_hadith_aggregate(aggregate),
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
        if looks_like_hadith(source_text):
            await _ensure_hadith_status(
                session=session,
                project_uuid=project_uuid,
                segment=segment,
                stellen_typ=HadithStellenTyp.N_7,
            )
            return ProtectedTranslationResult(
                output_text=None,
                source_kind="hadith",
                skip_reason="hadith_external_verification_unavailable",
                reference_payload={
                    "kind": "hadith",
                    "title": "Hadith verification required",
                    "subtitle": "No external source candidate was available",
                    "sources": [],
                    "state": "unverified",
                    "hadith_stellen_typ": HadithStellenTyp.N_7.value,
                },
            )
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
        (
            await session.execute(
                select(HadithSingleSourceResult).where(
                    HadithSingleSourceResult.aggregate_uuid == outcome.run.aggregate_uuid
                )
            )
        )
        .scalars()
        .all()
    )
    if aggregate is None:
        return None
    await _ensure_hadith_status(
        session=session,
        project_uuid=project_uuid,
        segment=segment,
        stellen_typ=_stellen_typ_for_hadith_outcome(outcome=outcome, aggregate=aggregate),
    )
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
        "subtitle": _format_quran_range(
            passage.sura_index, passage.aya_index_start, passage.aya_index_end
        ),
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
    rows: Sequence[HadithSingleSourceResult],
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


def _quran_translation_key_for_target_language(target_language: str | None) -> str:
    """Select the protected Qur'an translation carrier for the target language.

    Existing translation jobs do not yet persist a project target language, so
    the current production default remains German. English is enabled as soon
    as callers pass an English target language.
    """
    if target_language and target_language.strip().casefold().startswith(("en", "english")):
        return ENGLISH_RWWAD_KEY
    return GERMAN_RWWAD_KEY


async def _gather_hadith_candidates(
    *,
    session: AsyncSession,
    query_text: str,
) -> list[HadithCandidateHit]:
    if not query_text.strip():
        return []

    candidates: list[HadithCandidateHit] = []
    sunnah_lookup = extract_sunnah_lookup(query_text)
    shamela_hits = await find_by_skeleton(
        session,
        candidate_text=query_text,
        only_kutub_as_sitta=True,
        limit=20,
    )
    candidates.extend(shamela_hits_to_consensus_candidates(shamela_hits))

    if not candidates and sunnah_lookup is None and not looks_like_hadith(query_text):
        return []

    settings = get_settings()
    if sunnah_lookup is not None:
        try:
            sunnah_hit = await sunnah_fetch_hadith(
                collection=sunnah_lookup.collection,
                hadith_number=sunnah_lookup.hadith_number,
                api_key=settings.sunnah_com_api_key,
            )
        except (SunnahApiKeyMissing, ModelUClassA, ModelUClassB):
            sunnah_hit = None
        if sunnah_hit is not None:
            candidates.append(_sunnah_to_candidate(sunnah_hit))

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


def _sunnah_to_candidate(hadith: SunnahHadith) -> HadithCandidateHit:
    grade_values: list[str] = []
    for grade in hadith.grades:
        value = grade.get("grade") if isinstance(grade, dict) else None
        if isinstance(value, str) and value.strip():
            grade_values.append(value.strip())
    return HadithCandidateHit(
        source_name="sunnah.com",
        quellen_rolle=Quellenrolle.PFLICHT,
        matn_arabic=hadith.matn_arabic,
        matn_vocalized=None,
        isnad_chain=[],
        collection_label=hadith.collection,
        hadith_number=hadith.hadith_number,
        authenticity_grade=", ".join(grade_values) if grade_values else None,
        raw_payload=dict(hadith.raw_payload),
    )


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
    return looks_like_hadith(text)


def _stellen_typ_for_hadith_outcome(
    *,
    outcome: Any,
    aggregate: HadithAggregateResult,
) -> HadithStellenTyp:
    if aggregate.vokalisierungs_konflikt or aggregate.vokalisierungsklasse == "V-2":
        return HadithStellenTyp.N_8
    if outcome.two_tier.extended_set_triggered:
        return HadithStellenTyp.N_2
    return HadithStellenTyp.N_1


def _stellen_typ_for_existing_hadith_aggregate(
    aggregate: HadithAggregateResult,
) -> HadithStellenTyp:
    if aggregate.vokalisierungs_konflikt or aggregate.vokalisierungsklasse == "V-2":
        return HadithStellenTyp.N_8
    return HadithStellenTyp.N_1


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
