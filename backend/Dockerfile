# syntax=docker/dockerfile:1.6
# Waraq backend production image.
#
# Two-stage build to keep the runtime image lean. The deps stage
# installs build tooling needed for asyncpg/psycopg2/Pillow; the
# runtime stage carries only the compiled wheels + system libs the
# app actually needs at runtime (libpq for asyncpg, fonts for
# Noto Naskh Arabic — needed once we wire LibreOffice for PDF print
# export).

# ---------- builder stage ----------
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build deps for native wheels (psycopg2, Pillow, etc.).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./

# Install into a venv we'll copy to the runtime stage. Using `pip
# install -e .` here lets editable mode work for dev; for production
# we install non-editable from the project dir.
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install .

# ---------- runtime stage ----------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    UPLOADS_DIR=/data/uploads

# Runtime libs:
# - libpq5: asyncpg / psycopg
# - fonts-noto-core: Noto Sans/Naskh Arabic for DOCX + PDF rendering
# - libreoffice-core + libreoffice-writer: PDF print export pipeline
#   (DOCX → PDF). Adds ~250 MB to the image but is load-bearing for
#   the M5 PDF print export endpoint.
# - ghostscript: PDF/X-1a post-processing for print-grade artefacts
# - curl + ca-certificates: healthcheck + outbound HTTPS to providers
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        fonts-noto-core \
        libreoffice-core \
        libreoffice-writer \
        ghostscript \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Bring over the prebuilt venv + project source.
COPY --from=builder /opt/venv /opt/venv
COPY . .

# Persistent data dir for uploads. Fly volumes / mounts attach here.
RUN mkdir -p /data/uploads

# Non-root user; writes go to /data which the volume mount owns.
RUN useradd -r -u 1000 -m -d /home/waraq waraq \
    && chown -R waraq:waraq /data /app
USER waraq

EXPOSE 8080

# On boot: run pending Alembic migrations, then start uvicorn. Fly
# handles process lifecycle; `--proxy-headers` lets FastAPI honor the
# X-Forwarded-* headers Fly's edge sets.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn waraq.api.main:app --host 0.0.0.0 --port 8080 --proxy-headers --forwarded-allow-ips '*'"]
