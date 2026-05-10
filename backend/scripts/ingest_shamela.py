"""Shamela / OpenITI text ingest driver (Phase 2E).

Per Phase 2E / WORKLOG decision 2026-05-08: Shamela = OpenITI for v1.0.

Usage:
    cd backend
    set -a && source .env && set +a
    .venv/bin/python scripts/ingest_shamela.py <text-slug> <path-to-text-file> <source-version>
    .venv/bin/python scripts/ingest_shamela.py --list

`<text-slug>` must be one of the v1.0 OpenITI text identifiers:
    lisan_al_arab, taj_al_arus, qamus_al_muhit,
    sahih_bukhari, sahih_muslim, sunan_abi_dawud, jami_at_tirmidhi,
    sunan_an_nasai, sunan_ibn_majah, muwatta_malik

The text file follows the simple section-line format:
    # <heading>          (kitāb / bāb / lemma)
    | <text content>     (one or more lines per section)
    blank line           (section boundary)

OpenITI `.mARkdown` content can be massaged into this format with a
short pre-processor — that's deliberately a per-text task because
the upstream structures vary (lexicons differ from hadith collections).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from waraq.db.session import _engine, _sessionmaker
from waraq.shamela import OPENITI_TEXTS, ingest_text, parse_section_lines


async def _run(text_slug: str, text_path: Path, source_version: str) -> None:
    content = text_path.read_text(encoding="utf-8")
    sections = list(parse_section_lines(content))
    print(f"Parsed {len(sections)} sections from {text_path}")

    sessionmaker = _sessionmaker()
    try:
        async with sessionmaker() as session, session.begin():
            result = await ingest_text(
                session=session,
                text_slug=text_slug,
                source_version=source_version,
                sections=sections,
            )
        print(
            f"Ingest done — {text_slug}@{source_version}: "
            f"inserted={result.inserted_count}, "
            f"updated={result.updated_count}, "
            f"superseded={result.superseded_count}"
        )
    finally:
        await _engine().dispose()


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--list":
        print("v1.0 OpenITI text set:")
        for spec in OPENITI_TEXTS:
            badge = "[Kutub]" if spec.is_kutub_as_sitta else "       "
            print(
                f"  {badge} {spec.text_slug:<20} {spec.title_translit:<25} "
                f"({spec.text_type}) — {spec.source_uri}"
            )
        sys.exit(0)
    if len(sys.argv) < 4:
        print(
            "Usage: ingest_shamela.py <text-slug> <text-path> <source-version>",
            file=sys.stderr,
        )
        print("       ingest_shamela.py --list", file=sys.stderr)
        sys.exit(2)
    text_slug = sys.argv[1]
    text_path = Path(sys.argv[2])
    source_version = sys.argv[3]
    if not text_path.is_file():
        print(f"Error: {text_path} is not a file", file=sys.stderr)
        sys.exit(1)
    asyncio.run(_run(text_slug, text_path, source_version))


if __name__ == "__main__":
    main()
