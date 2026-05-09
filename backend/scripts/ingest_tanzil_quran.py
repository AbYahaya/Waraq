"""Tanzil-Hafs Qurʾān → AR-Referenzbestand ingest driver.

Per Phase 2D / WORKLOG decision 2026-05-09.

Usage (one-shot, idempotent):
    cd backend
    set -a && source .env && set +a
    .venv/bin/python scripts/ingest_tanzil_quran.py <path-to-tanzil-text> <source-version>

The Tanzil pipe-delimited text file is the canonical Hafs/Uthmani
release downloaded by hand from tanzil.net (CC BY 3.0). Argument 2 is
the source-version label recorded with each row — re-running with the
same version is idempotent (texts get refreshed in place); running
with a different version inactivates the prior version's rows and
inserts fresh ones.

Example:
    .venv/bin/python scripts/ingest_tanzil_quran.py \\
        ~/Downloads/quran-uthmani.txt tanzil-1.1.0
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from waraq.db.session import _engine, _sessionmaker
from waraq.quran import (
    DEFAULT_TANZIL_HAFS_SOURCE_NAME,
    ingest_tanzil_quran,
    parse_tanzil_pipe_text,
)


async def _run(text_path: Path, source_version: str, source_name: str) -> None:
    content = text_path.read_text(encoding="utf-8")
    verses = list(parse_tanzil_pipe_text(content))
    print(f"Parsed {len(verses)} verses from {text_path}")

    sessionmaker = _sessionmaker()
    try:
        async with sessionmaker() as session, session.begin():
            result = await ingest_tanzil_quran(
                session=session,
                verses=verses,
                source_version=source_version,
                source_name=source_name,
            )
        print(
            f"Ingest done — inserted={result.inserted_count}, "
            f"superseded={result.superseded_count}, "
            f"source={result.source_name}@{result.source_version}"
        )
    finally:
        await _engine().dispose()


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: ingest_tanzil_quran.py <text-path> <source-version> "
            "[<source-name>]",
            file=sys.stderr,
        )
        sys.exit(2)
    text_path = Path(sys.argv[1])
    source_version = sys.argv[2]
    source_name = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_TANZIL_HAFS_SOURCE_NAME
    if not text_path.is_file():
        print(f"Error: {text_path} is not a file", file=sys.stderr)
        sys.exit(1)
    asyncio.run(_run(text_path, source_version, source_name))


if __name__ == "__main__":
    main()
