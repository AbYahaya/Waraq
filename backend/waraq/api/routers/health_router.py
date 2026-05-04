"""Health endpoints. No auth required."""

from __future__ import annotations

from fastapi import APIRouter
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
