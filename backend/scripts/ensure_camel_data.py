"""Best-effort CAMeL morphology DB bootstrap for deployed containers.

The CAMeL morphology database is large enough that downloading it inside
`docker build` can make Fly remote builders time out. This script runs in
the background at container startup instead: the web process starts
normally, and morphology becomes available once the DB is present.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def main() -> int:
    if os.environ.get("WARAQ_CAMEL_AUTO_DOWNLOAD", "1").lower() in {"0", "false", "no"}:
        return 0

    marker = (
        Path(os.environ.get("CAMELTOOLS_DATA", "/opt/camel_tools_data")) / ".waraq_msa_r13_ready"
    )
    if marker.exists():
        return 0

    try:
        from camel_tools.morphology.database import MorphologyDB

        MorphologyDB.builtin_db()
    except Exception:
        result = subprocess.run(
            ["camel_data", "-i", "morphology-db-msa-r13"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            return result.returncode

    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("ready\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
