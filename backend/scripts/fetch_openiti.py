"""Phase 4 sub-batch B' — OpenITI fetcher + ingester.

Fetches a `.mARkdown` text from OpenITI's GitHub raw URLs, runs the
generic preprocessor, and ingests via the existing Phase-2E pipeline.

Usage:
    cd backend
    set -a && source .env && set +a
    .venv/bin/python scripts/fetch_openiti.py --slug sahih_bukhari --version 2024-canonical
    .venv/bin/python scripts/fetch_openiti.py --list

The per-slug raw URL is hard-coded in `_RAW_URLS` below. URLs were
probed manually against `api.github.com/repos/OpenITI/<repo>/contents/...`
on 2026-05-10 and are correct for the OpenITI repo state as of that
date. When OpenITI restructures (rare), this map is the single point
of update.

Two slugs known to ship `.completed` editions today: `sahih_bukhari`.
The other v1.0 canonical-floor texts are GitHub-API-rate-limit-blocked
on the dev host — re-run path-discovery against api.github.com once
the rate limit resets (1 h) or with a `GITHUB_TOKEN` env var.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import urllib.error
import urllib.request
from pathlib import Path

from waraq.db.session import _engine, _sessionmaker
from waraq.shamela import OPENITI_TEXTS, ingest_text, parse_section_lines
from waraq.shamela.openiti_markdown import openiti_markdown_to_section_lines

# Hardcoded raw-mARkdown URLs per text-slug. Keys must match
# `OpenITITextSpec.text_slug`. Value is the raw.githubusercontent.com URL
# of the `.mARkdown` (or `.completed`) edition we want to ingest.
#
# Probed + confirmed reachable (HTTP 200, ~5 MB) on 2026-05-10. The
# rest of the canonical-floor 9 are pending GitHub API access for
# path-discovery.
_RAW_URLS: dict[str, str] = {
    "sahih_bukhari": (
        "https://raw.githubusercontent.com/OpenITI/0275AH/master/data/"
        "0256Bukhari/0256Bukhari.Sahih/0256Bukhari.Sahih.JK000110-ara1.completed"
    ),
}


def _fetch(url: str) -> str:
    """GET the URL and return the body decoded as UTF-8.

    Bounded timeout so a stalled fetch surfaces fast.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "waraq-openiti-fetcher/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


async def _ingest(text_slug: str, source_version: str, content: str) -> None:
    """Run the preprocessing + ingest pipeline for one downloaded text."""
    section_line_text = openiti_markdown_to_section_lines(content)
    sections = list(parse_section_lines(section_line_text))
    print(f"  preprocessed → {len(sections)} sections")

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
            f"  ingest done: inserted={result.inserted_count}, "
            f"updated={result.updated_count}, "
            f"superseded={result.superseded_count}"
        )
    finally:
        await _engine().dispose()


def _list() -> None:
    """Print the v1.0 registry alongside known download paths."""
    print("v1.0 OpenITI registry (✓ = download URL hard-coded; * = pending):")
    for spec in OPENITI_TEXTS:
        marker = "✓" if spec.text_slug in _RAW_URLS else "*"
        kutub = " [Kutub]" if spec.is_kutub_as_sitta else ""
        print(f"  {marker} {spec.text_slug:<22} {spec.title_translit}{kutub}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", help="text_slug to fetch")
    parser.add_argument(
        "--version",
        default="2026-05-10-openiti",
        help="source_version string to record on shamela_registry rows",
    )
    parser.add_argument("--list", action="store_true", help="list known slugs")
    parser.add_argument(
        "--save-to",
        type=Path,
        default=None,
        help="optional: also write the raw mARkdown to this path",
    )
    args = parser.parse_args()

    if args.list or args.slug is None:
        _list()
        if args.slug is None:
            sys.exit(0)

    slug: str = args.slug
    if slug not in _RAW_URLS:
        print(
            f"Error: no download URL hard-coded for slug {slug!r}. Known: {sorted(_RAW_URLS)}",
            file=sys.stderr,
        )
        sys.exit(2)

    url = _RAW_URLS[slug]
    print(f"Fetching {slug} from {url} …")
    try:
        content = _fetch(url)
    except urllib.error.URLError as exc:
        print(f"Error: download failed — {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"  downloaded {len(content):,} chars")

    if args.save_to is not None:
        args.save_to.write_text(content, encoding="utf-8")
        print(f"  raw mARkdown saved to {args.save_to}")

    asyncio.run(_ingest(slug, args.version, content))


if __name__ == "__main__":
    main()
