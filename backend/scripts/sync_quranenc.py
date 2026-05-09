"""quranenc.com → local fallback sync driver (Phase 2B).

Pulls every sura for one or more translation_keys (default: both
`german_rwwad` + `english_rwwad`) and writes them to the local
`quran_translation_verses` table under a fresh ISO-date source_version.

Run weekly via cron / systemd-timer / Celery beat — the canonical
"weekly automatic sync" of §4.15.1. Idempotent on same-day re-run.

Usage:
    cd backend
    set -a && source .env && set +a
    .venv/bin/python scripts/sync_quranenc.py [german_rwwad|english_rwwad|both]
"""

from __future__ import annotations

import asyncio
import sys

from waraq.db.session import _engine, _sessionmaker
from waraq.quran import (
    ENGLISH_RWWAD_KEY,
    GERMAN_RWWAD_KEY,
    sync_translation,
)


async def _run(keys: list[str]) -> None:
    sessionmaker = _sessionmaker()
    try:
        for key in keys:
            print(f"Syncing {key}...")
            async with sessionmaker() as session, session.begin():
                result = await sync_translation(
                    session=session,
                    translation_key=key,
                )
            print(
                f"  done — version={result.source_version}, "
                f"suras={result.suras_fetched}, "
                f"inserted={result.verses_inserted}, "
                f"updated={result.verses_updated}, "
                f"superseded={result.superseded_count}"
            )
    finally:
        await _engine().dispose()


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else "both"
    if arg == "both":
        keys = [GERMAN_RWWAD_KEY, ENGLISH_RWWAD_KEY]
    elif arg in (GERMAN_RWWAD_KEY, ENGLISH_RWWAD_KEY):
        keys = [arg]
    else:
        print(
            f"Usage: sync_quranenc.py [{GERMAN_RWWAD_KEY}|{ENGLISH_RWWAD_KEY}|both]",
            file=sys.stderr,
        )
        sys.exit(2)
    asyncio.run(_run(keys))


if __name__ == "__main__":
    main()
