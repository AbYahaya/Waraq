"""FastAPI application entrypoint.

Run locally:
    cd backend
    .venv/bin/uvicorn waraq.api.main:app --reload

The app exposes:
- /health, /health/db (no auth)
- /auth/register, /auth/login (no auth)
- /auth/me                    (Bearer token)
- /projects (CRUD)            (Bearer token)
- /uploads/* (chunked upload) (Bearer token)
- /ocr/* (OCR jobs)           (Bearer token)
"""

from __future__ import annotations

from fastapi import FastAPI

from waraq.api.routers import (
    auth_router,
    health_router,
    ocr_router,
    projects_router,
    uploads_router,
)


def create_app() -> FastAPI:
    """Application factory. Tests instantiate this; production servers use
    `waraq.api.main:app` (the module-level instance below)."""
    app = FastAPI(
        title="Waraq",
        description="Translation platform for classical Arabic Islamic texts",
        version="0.1.0",
    )

    app.include_router(health_router.router)
    app.include_router(auth_router.router)
    app.include_router(projects_router.router)
    app.include_router(uploads_router.router)
    app.include_router(ocr_router.router)
    return app


app = create_app()
