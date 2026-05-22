"""FastAPI application entrypoint.

Run locally:
    cd backend
    .venv/bin/uvicorn waraq.api.main:app --reload

The app exposes (M1 layer):
- /health, /health/db (no auth)
- /auth/register, /auth/login (no auth)
- /auth/me, /projects, /uploads/*, /ocr/* (Bearer token)

M4 expansion adds (Bearer token):
- /projects/{project_uuid}/pages, /pages/{page_uuid}/segments,
  /segments/{satz_uuid}, /segments/{satz_uuid}/text
- /segments/{satz_uuid}/lock (set / release)
- /glossary/lookup, /glossary/entries
- /entities, /entities/lookup
- /segments|pages|projects/{uuid}/conflicts, /conflicts/{uuid}/resolve/...
- /pages/{page_uuid}/ocr-review/{enter,findings,resolve-no-go}
- /segments|pages|projects/{uuid}/history
- /projects/{project_uuid}/release-gate, /confirm-warning, /start-translation
- /projects/{project_uuid}/translation-jobs, /translation-jobs/{job_uuid}
- /segments/{satz_uuid}/rule-binding
- /projects/{project_uuid}/promotion/{observations,aggregate,musterkandidaten}
- /projects/{project_uuid}/ocr-export/{gate,confirm,run}
- /ocr-export/artefacts/{po_uuid}
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from waraq.api.routers import (
    admin_router,
    admissions_router,
    audit_dashboard_router,
    auth_router,
    conflicts_router,
    diagnostics_router,
    entities_router,
    export_router,
    glossary_router,
    hadith_router,
    health_router,
    history_router,
    lock_router,
    morphology_router,
    notifications_router,
    ocr_export_router,
    ocr_review_router,
    ocr_router,
    pages_router,
    preflight_router,
    projects_router,
    promotion_router,
    readout_router,
    release_gate_router,
    review_router,
    rule_binding_router,
    segments_router,
    style_profile_router,
    toc_router,
    translation_router,
    uploads_router,
)

logger = logging.getLogger(__name__)


# Bound the lifespan reaper so a slow DB doesn't block app boot.
# Tight enough that the frontend doesn't see ECONNREFUSED for long;
# loose enough to cover a typical first-connection SSL handshake. If
# the reap can't finish in this window the poll-time self-heal in
# `get_ocr_job_status` will catch the same orphans on next poll.
_STARTUP_REAP_TIMEOUT_SECONDS: float = 5.0


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """App startup/shutdown.

    Startup: sweep orphan OCR auto-run Jobs (sub-batch O follow-up,
    2026-05-12). FastAPI BackgroundTasks die when the worker process
    dies, leaving Job rows stuck in RUNNING with no driver. The sweep
    fails any RUNNING/PENDING `ocr_auto_run` Job whose `updated_at` is
    older than the stale-heartbeat threshold, so a restart doesn't
    leave the UI staring at a zombie progress bar.

    The reap is wall-clock-bounded so a slow / unreachable DB can't
    keep the app socket bound-but-unresponsive for minutes (frontend
    sees ECONNREFUSED in that window). If the timeout fires, the
    poll-time self-heal in `get_ocr_job_status` will catch the same
    orphans on the next status poll.
    """
    # Import lazily so test fixtures that swap in alternative
    # sessionmakers (or skip DB entirely) aren't forced through a
    # module-level DB-touching import.
    from waraq.db.session import _sessionmaker
    from waraq.ocr.auto_run import reap_orphan_jobs

    async def _do_reap() -> None:
        async with _sessionmaker()() as session:
            reaped = await reap_orphan_jobs(session=session)
            await session.commit()
            if reaped:
                logger.info(
                    "ocr_auto_run.startup.reaped_orphans",
                    extra={
                        "count": len(reaped),
                        "job_uuids": [str(u) for u in reaped],
                    },
                )

    try:
        await asyncio.wait_for(_do_reap(), timeout=_STARTUP_REAP_TIMEOUT_SECONDS)
    except TimeoutError:
        # DB was slow on boot; not fatal. Poll-time self-heal still
        # reaps orphans whenever a client polls a status endpoint.
        logger.warning(
            "ocr_auto_run.startup.reap_timeout",
            extra={"timeout_s": _STARTUP_REAP_TIMEOUT_SECONDS},
        )
    except Exception:
        # A broken DB shouldn't prevent the app from booting at all —
        # /health/db will surface the underlying error.
        logger.exception("ocr_auto_run.startup.reap_failed")
    yield


def create_app() -> FastAPI:
    """Application factory. Tests instantiate this; production servers use
    `waraq.api.main:app` (the module-level instance below)."""
    app = FastAPI(
        title="Waraq",
        description="Translation platform for classical Arabic Islamic texts",
        version="0.2.0",
        lifespan=lifespan,
    )

    from waraq.db.session import get_settings

    cors_origins = [
        origin.strip() for origin in get_settings().cors_origins.split(",") if origin.strip()
    ]
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # M1 layer
    app.include_router(health_router.router)
    app.include_router(auth_router.router)
    app.include_router(projects_router.router)
    app.include_router(uploads_router.router)
    app.include_router(ocr_router.router)

    # M4 expansion
    app.include_router(pages_router.router)
    app.include_router(segments_router.router)
    app.include_router(lock_router.router)
    app.include_router(glossary_router.router)
    app.include_router(entities_router.router)
    app.include_router(conflicts_router.router)
    app.include_router(ocr_review_router.router)
    app.include_router(history_router.router)
    app.include_router(readout_router.router)
    app.include_router(export_router.router)
    app.include_router(release_gate_router.router)
    app.include_router(preflight_router.router)
    app.include_router(translation_router.router)
    app.include_router(rule_binding_router.router)
    app.include_router(promotion_router.router)
    app.include_router(ocr_export_router.router)
    app.include_router(style_profile_router.router)
    app.include_router(morphology_router.router)
    app.include_router(admin_router.router)
    # Phase 3 sub-batch D — difficulty + guided review.
    app.include_router(review_router.router)
    # Phase 3 sub-batch E — TOC handling.
    app.include_router(toc_router.router)
    # Phase 3 sub-batch F — notifications + idle-timeout support.
    app.include_router(notifications_router.router)
    # Phase 4 sub-batch J — §4.16 hadith verification HTTP route.
    app.include_router(hadith_router.router)
    # Phase 4 sub-batch J — diagnostic endpoints for the UI test surface.
    app.include_router(diagnostics_router.router)
    # Phase 5 sub-batch M — admin admission gate (simplified §2.3 row 8).
    app.include_router(admissions_router.router)
    # Sub-batch N (out-of-phase) — Project audit dashboard.
    app.include_router(audit_dashboard_router.router)
    return app


app = create_app()
