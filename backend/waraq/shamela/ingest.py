"""Phase 2E — OpenITI text ingest into the Shamela corpus tables.

OpenITI ships texts in `.mARkdown` format with section markers and
optional inline metadata. v1.0 ingest uses a **section-line** input
shape that's both OpenITI-compatible (after stripping mARkdown
markers) and forgiving for hand-curated subsets:

    # <heading>          — heading line (kitāb / bāb / lemma)
    | <text>             — section content line
    blank line           — section boundary

Lines starting with `#` open a new heading scope. Subsequent `|`
lines accumulate into the current section under that heading scope.
Blank lines separate sections within the same heading. A new `#`
heading closes the previous heading scope.

The parser strips OpenITI-specific inline markers (`@QB@`, `@QE@`,
`@HUB@`, etc.) — informational tags that aren't part of the matn
content. Skeleton derivation goes through `waraq.arabic.to_skeleton`
(same pipeline as AR-Referenzbestand), so OCR-stage Mode A
plausibility lookups against Shamela use the same skeleton
representation as Qurʾān recognition.

Re-ingest semantics mirror Phase 2D:
- Same `(text_slug, source_version)` repeat = idempotent.
- New `source_version` for the same slug = supersession (prior rows
  flip to `active=false`).
"""

from __future__ import annotations

import re
import uuid as _uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from waraq.arabic import to_skeleton
from waraq.identity import new_uuid
from waraq.schemas import ShamelaRegistry, ShamelaSection
from waraq.shamela.registry import OpenITITextSpec, get_text_spec

# OpenITI inline marker patterns we strip during ingest. These are
# structural annotations, not matn content. The strip keeps the v1.0
# matcher focused on Arabic letters.
_OPENITI_MARKERS = re.compile(
    r"@(?:QB|QE|HUB|HE|TQB|TQE|YQB|YQE|RWY|MILESTONE|FOOT|FOOTNOTE)@\d*",
)


@dataclass(frozen=True, slots=True)
class SectionRow:
    """One parsed section ready for ingest."""

    section_index: int
    section_path: str
    text_arabic: str
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ShamelaIngestResult:
    text_slug: str
    source_version: str
    inserted_count: int
    updated_count: int
    superseded_count: int


def parse_section_lines(content: str) -> Iterator[SectionRow]:
    """Parse a heading + section-line block into `SectionRow`s.

    See module docstring for the canonical input shape.
    """
    current_path = ""
    current_buffer: list[str] = []
    section_index = 0

    def _flush() -> SectionRow | None:
        nonlocal section_index, current_buffer
        if not current_buffer:
            return None
        joined = " ".join(line.strip() for line in current_buffer if line.strip())
        cleaned = _strip_openiti_markers(joined)
        current_buffer = []
        if not cleaned:
            return None
        section_index += 1
        return SectionRow(
            section_index=section_index,
            section_path=current_path,
            text_arabic=cleaned,
            metadata={},
        )

    for raw in content.splitlines():
        line = raw.rstrip()
        if not line:
            row = _flush()
            if row is not None:
                yield row
            continue
        if line.startswith("#"):
            row = _flush()
            if row is not None:
                yield row
            current_path = line.lstrip("#").strip()
            continue
        if line.startswith("|"):
            current_buffer.append(line.lstrip("|").strip())
            continue
        # Loose paragraph line — accept as content.
        current_buffer.append(line)

    row = _flush()
    if row is not None:
        yield row


def _strip_openiti_markers(text: str) -> str:
    cleaned = _OPENITI_MARKERS.sub("", text)
    # Collapse multiple spaces.
    return " ".join(cleaned.split())


async def register_text(
    *,
    session: AsyncSession,
    spec: OpenITITextSpec,
    source_version: str,
) -> ShamelaRegistry:
    """Upsert the registry row for `(spec.text_slug, source_version)`.

    Returns the existing or newly-created row. Re-running with the
    same `(slug, version)` is a no-op.
    """
    existing = await session.get(ShamelaRegistry, (spec.text_slug, source_version))
    if existing is not None:
        existing.title = spec.title
        existing.author = spec.author
        existing.source_uri = spec.source_uri
        existing.text_type = spec.text_type
        existing.is_kutub_as_sitta = spec.is_kutub_as_sitta
        existing.active = True
        await session.flush()
        return existing

    row = ShamelaRegistry(
        text_slug=spec.text_slug,
        source_version=source_version,
        title=spec.title,
        author=spec.author,
        source_uri=spec.source_uri,
        text_type=spec.text_type,
        is_kutub_as_sitta=spec.is_kutub_as_sitta,
        metadata_json={"title_translit": spec.title_translit, "rationale": spec.rationale},
    )
    session.add(row)
    await session.flush()
    return row


async def ingest_text(
    *,
    session: AsyncSession,
    text_slug: str,
    source_version: str,
    sections: Iterable[SectionRow],
) -> ShamelaIngestResult:
    """Ingest `sections` for `(text_slug, source_version)`.

    Looks up the canonical spec for the slug and ensures a registry
    row exists. Then walks the sections, derives `text_skeleton`,
    upserts each row by `(text_slug, source_version, section_index)`.

    Re-ingest with a new `source_version` for the same `text_slug`
    flips prior rows + the prior registry row to `active=false`
    (H-5 inactivation; no deletion).
    """
    spec = get_text_spec(text_slug)
    await register_text(session=session, spec=spec, source_version=source_version)

    # Step 1: deactivate prior-version registry + section rows of the same slug.
    superseded_registry: int = (
        cast(
            CursorResult[Any],
            await session.execute(
                update(ShamelaRegistry)
                .where(ShamelaRegistry.text_slug == text_slug)
                .where(ShamelaRegistry.source_version != source_version)
                .where(ShamelaRegistry.active.is_(True))
                .values(active=False)
            ),
        ).rowcount
        or 0
    )
    superseded_sections: int = (
        cast(
            CursorResult[Any],
            await session.execute(
                update(ShamelaSection)
                .where(ShamelaSection.text_slug == text_slug)
                .where(ShamelaSection.source_version != source_version)
                .where(ShamelaSection.active.is_(True))
                .values(active=False)
            ),
        ).rowcount
        or 0
    )

    # Step 2: in-process upsert against existing same-version sections.
    existing_q = await session.execute(
        select(ShamelaSection)
        .where(ShamelaSection.text_slug == text_slug)
        .where(ShamelaSection.source_version == source_version)
    )
    existing_by_index: dict[int, ShamelaSection] = {
        row.section_index: row for row in existing_q.scalars()
    }

    inserted = 0
    updated = 0
    seen_indices: set[int] = set()
    for sect in sections:
        if sect.section_index in seen_indices:
            raise ValueError(
                f"duplicate section_index {sect.section_index} in input for {text_slug!r}"
            )
        seen_indices.add(sect.section_index)
        skeleton = to_skeleton(sect.text_arabic)

        if (existing := existing_by_index.get(sect.section_index)) is not None:
            if (
                existing.text_arabic != sect.text_arabic
                or existing.section_path != sect.section_path
                or existing.metadata_json != sect.metadata
            ):
                existing.text_arabic = sect.text_arabic
                existing.text_skeleton = skeleton
                existing.section_path = sect.section_path
                existing.metadata_json = sect.metadata
                updated += 1
            existing.active = True
            continue

        session.add(
            ShamelaSection(
                section_uuid=_make_uuid(),
                text_slug=text_slug,
                source_version=source_version,
                section_index=sect.section_index,
                section_path=sect.section_path,
                text_arabic=sect.text_arabic,
                text_skeleton=skeleton,
                metadata_json=sect.metadata,
            )
        )
        inserted += 1

    await session.flush()
    return ShamelaIngestResult(
        text_slug=text_slug,
        source_version=source_version,
        inserted_count=inserted,
        updated_count=updated,
        superseded_count=superseded_registry + superseded_sections,
    )


def _make_uuid() -> _uuid.UUID:
    return new_uuid()


__all__ = [
    "SectionRow",
    "ShamelaIngestResult",
    "ingest_text",
    "parse_section_lines",
    "register_text",
]
