from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://waraq:waraq@localhost:5432/waraq"
    redis_url: str = "redis://localhost:6379/0"
    # Local persistent path for uploaded source files. Per-upload layout:
    # {uploads_dir}/{project_uuid}/{job_uuid}/source<ext>. Gitignored.
    uploads_dir: str = "./uploads"
    # Google AI Studio API key. Empty default so unit tests don't require it;
    # the OCR service will raise with a clear error if a real call is attempted
    # without a key configured.
    google_ai_api_key: str = ""
    # Canonical Gemini model for the OCR main reading line per Dokument 1 §3.3.
    gemini_ocr_model: str = "gemini-2.5-pro"
    # JWT signing. Generate via `openssl rand -hex 32` for prod; the dev
    # default is a placeholder that is replaced at deploy time.
    jwt_secret: str = "dev-only-jwt-secret-replace-at-deploy"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60 * 24  # 24h


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


@lru_cache(maxsize=1)
def _engine():  # type: ignore[no-untyped-def]
    return create_async_engine(get_settings().database_url, future=True)


@lru_cache(maxsize=1)
def _sessionmaker():  # type: ignore[no-untyped-def]
    return async_sessionmaker(_engine(), class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with _sessionmaker()() as session:
        yield session
