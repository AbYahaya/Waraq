"""Health endpoints. No auth required."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Any

from fastapi import APIRouter
from fastapi import Query
from sqlalchemy import text

from waraq.api.dependencies import DbSession

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
async def health_db(session: DbSession) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}


def _which(name: str) -> str | None:
    """Look up a system binary by name.

    Fly/Debian images can expose LibreOffice under non-PATH locations.
    We check a few common fallbacks so operators can confirm runtime
    capability from `/health/binaries` without SSH.
    """
    found = shutil.which(name)
    if found:
        return found
    fallbacks: dict[str, tuple[str, ...]] = {
        "soffice": (
            "/usr/bin/soffice",
            "/usr/lib/libreoffice/program/soffice",
            "/usr/lib/libreoffice/program/soffice.bin",
        ),
        "libreoffice": ("/usr/bin/libreoffice",),
        "gs": ("/usr/bin/gs",),
        "pdftoppm": ("/usr/bin/pdftoppm",),
    }
    for candidate in fallbacks.get(name, ()):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _version(args: list[str]) -> str | None:
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            timeout=2.0,
            check=False,
        )
    except Exception:
        return None
    out = (proc.stdout or proc.stderr).decode("utf-8", errors="replace").strip()
    if not out:
        return None
    return out.splitlines()[0][:200]


@router.get("/health/binaries")
async def health_binaries(verbose: bool = Query(False)) -> dict[str, Any]:
    """Report presence of system binaries required for OCR/PDF export.

    This endpoint is intentionally unauthenticated so deploy checks can
    validate the runtime image without SSH access.
    """
    soffice = _which("soffice") or _which("libreoffice")
    gs = _which("gs")
    pdftoppm = _which("pdftoppm")

    result: dict[str, Any] = {
        "status": "ok",
        "binaries": {
            "soffice": {"found": soffice is not None, "path": soffice},
            "gs": {"found": gs is not None, "path": gs},
            "pdftoppm": {"found": pdftoppm is not None, "path": pdftoppm},
        },
    }
    if verbose:
        result["binaries"]["soffice"]["version"] = _version([soffice, "--version"]) if soffice else None
        result["binaries"]["gs"]["version"] = _version([gs, "--version"]) if gs else None
        result["binaries"]["pdftoppm"]["version"] = (
            _version([pdftoppm, "-v"]) if pdftoppm else None
        )
        result["runtime"] = {"python": sys.version.split()[0], "uid": os.getuid()}
    return result
