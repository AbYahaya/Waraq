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

from fastapi import FastAPI

from waraq.api.routers import (
    admin_router,
    auth_router,
    conflicts_router,
    entities_router,
    export_router,
    glossary_router,
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
    toc_router,
    translation_router,
    uploads_router,
)


def create_app() -> FastAPI:
    """Application factory. Tests instantiate this; production servers use
    `waraq.api.main:app` (the module-level instance below)."""
    app = FastAPI(
        title="Waraq",
        description="Translation platform for classical Arabic Islamic texts",
        version="0.2.0",
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
    app.include_router(morphology_router.router)
    app.include_router(admin_router.router)
    # Phase 3 sub-batch D — difficulty + guided review.
    app.include_router(review_router.router)
    # Phase 3 sub-batch E — TOC handling.
    app.include_router(toc_router.router)
    # Phase 3 sub-batch F — notifications + idle-timeout support.
    app.include_router(notifications_router.router)
    return app


app = create_app()
