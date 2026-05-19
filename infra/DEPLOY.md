# Waraq deploy — Fly.io

Initial deploy of the Waraq backend. Frontend deploy plan is captured
separately at the bottom (Cloudflare Pages or static-on-Fly).

## Prerequisites

- `flyctl` installed locally: `curl -L https://fly.io/install.sh | sh`
- `FLY_API_TOKEN` set (already present in `backend/.env`).
- Fly account with payment method on file (free tier OK for the small
  v1.0 footprint; managed Postgres has a small cost).

## Region — needs user decision before first deploy

For a Medina-based primary user + Swiss/EU collaborators:

| Region | Code | Tradeoff |
|---|---|---|
| Frankfurt | `fra` | Best EU reach; ~80–120ms KSA latency |
| Mumbai    | `bom` | Best KSA latency (~20–40ms); ~120ms EU |
| Paris     | `cdg` | Alternate EU |

Recommendation: **fra** unless KSA latency becomes a UX issue. Then
re-deploy to `bom` or use Fly's multi-region cloning.

Update `backend/fly.toml` `primary_region` once decided.

## First-time launch

```bash
cd backend
flyctl launch --copy-config --no-deploy        # picks app name + region from fly.toml
flyctl volumes create waraq_data --region fra --size 3 --no-encryption
flyctl postgres create --name waraq-db --region fra --vm-size shared-cpu-1x --volume-size 3
flyctl postgres attach waraq-db                # injects DATABASE_URL secret
```

## Secrets to set

`flyctl secrets set` writes into Fly's encrypted secret store; the
runtime sees them as env vars.

```bash
# Required for translation pipeline
flyctl secrets set OPENAI_API_KEY="sk-…"
# Required for OCR (canonical model is gemini-2.5-pro per Dokument 1
# §3.3; free-tier accounts must override to gemini-2.5-flash via env)
flyctl secrets set GOOGLE_AI_API_KEY="…"

# JWT signing secret — generate via `openssl rand -hex 32`
flyctl secrets set JWT_SECRET="$(openssl rand -hex 32)"

# Admin email allowlist (M4 admin-panel access). Comma-separated emails.
flyctl secrets set ADMIN_EMAILS="user@example.com"

# Browser origins allowed to call the API from a separately hosted
# frontend. Add the final Cloudflare Pages / preview URL after frontend
# deploy, comma-separated if there is more than one.
flyctl secrets set CORS_ORIGINS="https://<frontend>.pages.dev"

# Optional Hadith / Qurʾān API keys (for §4.16 / §4.15 enrichment;
# inert if missing).
flyctl secrets set SUNNAH_COM_API_KEY="…" \
                   DORAR_NET_API_KEY="…" \
                   HADEETHENC_API_KEY="…" \
                   QURANENC_API_KEY="…" \
                   RESEND_API_KEY="…"

# Free-tier Gemini override (skip if on paid Gemini)
flyctl secrets set GEMINI_OCR_MODEL=gemini-2.5-flash
```

`DATABASE_URL` is set automatically by `flyctl postgres attach`.

## Deploy

```bash
cd backend
flyctl deploy
```

The Dockerfile runs `alembic upgrade head` on startup, so migrations
apply automatically on first boot. Subsequent deploys re-apply any
new revisions.

## Smoke checks post-deploy

```bash
flyctl status
flyctl logs                                    # tail backend stdout
curl https://<app>.fly.dev/health              # should return 200
```

## Frontend

Two viable paths — pick one when ready:

### Option A — Cloudflare Pages (recommended)

```bash
cd frontend
npm run build                                  # produces dist/
# Configure Cloudflare Pages to build from frontend/ on push.
# Set VITE_API_URL=https://<backend>.fly.dev as an env var.
```

Pros: free, global CDN, instant rollback.
Cons: separate deploy; backend `CORS_ORIGINS` must include the Pages URL.

### Option B — Static-on-Fly (single domain)

Build the frontend, copy `dist/` into the backend image's static dir,
serve via FastAPI's `StaticFiles`. Single domain (no CORS) but ties
frontend deploys to backend deploys.

Recommendation: **A**. The backend now reads `CORS_ORIGINS`, and the
frontend build reads `VITE_API_URL`. Local dev still uses the Vite `/api`
proxy when `VITE_API_URL` is empty.

## What's NOT yet wired

- **veraPDF validation** (PDF print export). LibreOffice + Ghostscript
  are baked into the Docker image; veraPDF is not (Java app, ~100 MB).
  PDF print works without veraPDF — `X-Waraq-veraPDF-Valid: skipped`
  appears in the response header. Add veraPDF to the Dockerfile when
  strict PDF/X-1a validation becomes load-bearing.
- **Background workers**: Celery + Redis are pyproject deps but no
  worker is currently invoked. M5 OCR/translation runs synchronously
  in HTTP request scope. Add a separate Fly process group + Redis app
  if/when async backgrounding becomes load-bearing.
- **Backups**: Fly Postgres has snapshots but not point-in-time
  recovery on shared-cpu-1x. For v1.0 with low traffic this is fine;
  upgrade later.
