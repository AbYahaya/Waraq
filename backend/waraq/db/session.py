from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://waraq:waraq@localhost:5432/waraq"

    @field_validator("database_url", mode="after")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        """Normalize the SQLAlchemy URL scheme to `postgresql+asyncpg://`.

        Managed Postgres providers (Fly Postgres, Supabase, Neon) expose
        `DATABASE_URL` with a `postgres://` or `postgresql://` scheme.
        SQLAlchemy + asyncpg need the explicit `postgresql+asyncpg://`
        driver suffix; rewriting here keeps the runtime + alembic env in
        sync without per-deploy URL massaging.
        """
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://") :]
        if v.startswith("postgresql://") and "+asyncpg" not in v.split("://", 1)[0]:
            return "postgresql+asyncpg://" + v[len("postgresql://") :]
        return v

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
    # Canonical Gemini model for the §3.6 translation Check role.
    gemini_translation_model: str = "gemini-2.5-pro"
    # JWT signing. Generate via `openssl rand -hex 32` for prod; the dev
    # default is a placeholder that is replaced at deploy time.
    jwt_secret: str = "dev-only-jwt-secret-replace-at-deploy"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60 * 24  # 24h
    # Comma-separated email allowlist for admin-only HTTP endpoints. The
    # admin scope in M4 is just the accounts/projects panel (`is_admin`
    # is not a persisted column — admin is a deployment concern).
    admin_emails: str = ""
    # sunnah.com Hadith API key per §4.16.1 P-1. Free non-commercial
    # registration at sunnah.com/developers; sent as `X-API-Key` header.
    # Empty default so unit tests + sync runs without a key fail with a
    # clear `SunnahApiKeyMissing` rather than a 401 from the upstream.
    sunnah_com_api_key: str = ""
    # dorar.net Hadith endpoint per §4.16.1 P-3. dorar.net's public path
    # is keyless; the env slot is for future authenticated rollout +
    # local-test override.
    dorar_net_api_key: str = ""
    # dorar.net base URL — kept configurable since §3.5 declares
    # endpoints "fully unspecified – active work front". Default
    # placeholder; real endpoint per deployment.
    dorar_net_base_url: str = "https://dorar.net/dorar_api.json"


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
