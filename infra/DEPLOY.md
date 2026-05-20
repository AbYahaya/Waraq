# Waraq deploy — Fly.io

Initial deploy of the Waraq backend. Frontend deploy plan is captured
separately at the bottom (Vercel through GitHub or static-on-Fly).

## Current tester backend

- Backend app: `waraq-backend-yabdulrauf`
- Public URL: `https://waraq-backend-yabdulrauf.fly.dev`
- Region: `fra`
- Machine: `shared-cpu-1x`, `1gb`, autostop enabled
- Upload volume: `waraq_data`, 3 GB, mounted at `/data`
- Database app: `waraq-db-yabdulrauf` (Fly Postgres, unmanaged)
- Verified on 2026-05-20:
  - `/health` returned `{"status":"ok"}`
  - `/health/db` returned `{"status":"ok","db":"ok"}`

Pending:
- Set `CORS_ORIGINS` after the Vercel frontend URL is known.

## Prerequisites

- `flyctl` installed locally: `curl -L https://fly.io/install.sh | sh`
- Logged in locally with `flyctl auth login`.
- Fly account with billing enabled. Fly currently has no free tier; treat
  this as a small paid tester backend.
- `FLY_API_TOKEN` is only needed for GitHub Actions / CI deploys. It is
  not required for a manual `flyctl deploy` from your machine.

## Access token note

Do not put `FLY_API_TOKEN` in `backend/.env`; the app runtime does not need
Fly API access.

For local/manual deploys, use:

```bash
flyctl auth login
```

For GitHub Actions deploys, create a scoped deploy token after the Fly app
exists, then save it as a GitHub repository secret named `FLY_API_TOKEN`:

```bash
flyctl tokens create deploy -a <backend-app-name> --name github-deploy
```

## Region

For a Medina-based primary user + Swiss/EU collaborators:

| Region | Code | Tradeoff |
|---|---|---|
| Frankfurt | `fra` | Best EU reach; ~80–120ms KSA latency |
| Mumbai    | `bom` | Best KSA latency (~20–40ms); ~120ms EU |
| Paris     | `cdg` | Alternate EU |

Current tester deployment uses **fra**. Keep it unless KSA latency becomes a UX issue. Then
re-deploy to `bom` or use Fly's multi-region cloning.

## First-time launch

```bash
cd backend
flyctl launch --copy-config --no-deploy        # picks app name + region from fly.toml
flyctl volumes create waraq_data --region fra --size 3
flyctl postgres create --name waraq-db --region fra --vm-size shared-cpu-1x --volume-size 3
flyctl postgres attach waraq-db -a <backend-app-name>  # injects DATABASE_URL secret
```

For the current tester deployment, the created app names are
`waraq-backend-yabdulrauf` and `waraq-db-yabdulrauf`.

## Secrets to set

`flyctl secrets set` writes into Fly's encrypted secret store; the
runtime sees them as env vars.

```bash
# Required for translation pipeline
flyctl secrets set -a waraq-backend-yabdulrauf OPENAI_API_KEY="sk-…"
# Required for OCR (canonical model is gemini-2.5-pro per Dokument 1 §3.3)
flyctl secrets set -a waraq-backend-yabdulrauf GOOGLE_AI_API_KEY="…"

# JWT signing secret — generate via `openssl rand -hex 32`
flyctl secrets set -a waraq-backend-yabdulrauf JWT_SECRET="$(openssl rand -hex 32)"

# Admin email allowlist (M4 admin-panel access). Comma-separated emails.
flyctl secrets set -a waraq-backend-yabdulrauf ADMIN_EMAILS="user@example.com"

# Browser origins allowed to call the API from a separately hosted
# frontend. Add the final Vercel production / preview URL after frontend
# deploy, comma-separated if there is more than one.
flyctl secrets set -a waraq-backend-yabdulrauf CORS_ORIGINS="https://<frontend>.vercel.app"

# Optional Hadith / Qurʾān API keys (for §4.16 / §4.15 enrichment;
# inert if missing).
flyctl secrets set -a waraq-backend-yabdulrauf SUNNAH_COM_API_KEY="…" \
                   DORAR_NET_API_KEY="…" \
                   HADEETHENC_API_KEY="…" \
                   QURANENC_API_KEY="…" \
                   RESEND_API_KEY="…"

# Optional lower-cost Gemini override for constrained/test accounts
flyctl secrets set -a waraq-backend-yabdulrauf GEMINI_OCR_MODEL=gemini-2.5-flash
```

`DATABASE_URL` is set automatically by `flyctl postgres attach`.

Current tester deployment already has `DATABASE_URL`, `OPENAI_API_KEY`,
`GOOGLE_AI_API_KEY`, `JWT_SECRET`, and `ADMIN_EMAILS` set. Do not store
or commit the actual secret values.

## Deploy

```bash
cd backend
flyctl deploy -a waraq-backend-yabdulrauf
```

The Dockerfile runs `alembic upgrade head` on startup, so migrations
apply automatically on first boot. Subsequent deploys re-apply any
new revisions.

## Smoke checks post-deploy

```bash
flyctl status -a waraq-backend-yabdulrauf
flyctl logs -a waraq-backend-yabdulrauf        # tail backend stdout
curl https://waraq-backend-yabdulrauf.fly.dev/health
curl https://waraq-backend-yabdulrauf.fly.dev/health/db
```

If Fly reports `createRelease.release Timeout` after successfully pushing
an image, check `flyctl releases -a waraq-backend-yabdulrauf`. During the
initial deploy this happened twice while the image was already available.
The safe fallback used was:

```bash
flyctl machine update <machine-id> \
  -a waraq-backend-yabdulrauf \
  --image registry.fly.io/waraq-backend-yabdulrauf:<deployment-tag> \
  --yes
flyctl machine start <machine-id> -a waraq-backend-yabdulrauf
```

Only use this fallback after confirming the pushed image is the one you
want and the normal app release has not updated the machine.

## Frontend

Two viable paths — pick one when ready:

### Option A — Vercel through GitHub (recommended)

```bash
cd frontend
npm run build                                  # produces dist/
# Configure Vercel to build from frontend/ on push.
# Set VITE_API_URL=https://<backend>.fly.dev as an env var.
```

Pros: GitHub-native deploy previews, global CDN, simple rollback.
Cons: separate deploy; backend `CORS_ORIGINS` must include the Vercel production and preview origins you want testers to use.

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
