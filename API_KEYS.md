# Waraq — External Service Credentials Checklist

Reference document for all API keys, tokens, and external service credentials
needed across M1–M5. Update the **Status** column as you obtain each.

This file is gitignored (local-only). Actual key values must NEVER live in this
file or any tracked file — they go in `backend/.env` (also gitignored).

For current project state see [WORKLOG.md](./WORKLOG.md). For milestone scope see
[MILESTONES.md](./MILESTONES.md).

---

## Critical for M1–M3 (block code progress)

| # | Service | Status | What it's for | Where to get | Env var name |
|---|---|---|---|---|---|
| 1 | **Google AI Studio API key** | ✅ obtained 2026-05-03 (free tier — rate-limit-bound) | Gemini 2.5 Pro Vision (OCR main reading line per [Dokument 1 §3.3](docs/canon/de/dokument_1.md)) + Gemini 2.5 Pro (translation parallel check per §3.6). **One key handles both.** | [aistudio.google.com](https://aistudio.google.com) → Get API key | `GOOGLE_AI_API_KEY` 
| 2 | **OpenAI API key** | ✅ obtained 2026-05-03 | GPT-4o (translation primary per §3.6) + Stage-3 OCR semantic consensus per §3.4 | [platform.openai.com](https://platform.openai.com) → API keys → Create new secret key | `OPENAI_API_KEY` |

**Budget caps to set immediately on each:**

- OpenAI: Hard monthly limit at `platform.openai.com/account/limits` → suggest **$100/month during dev**, raise as needed
- Google AI Studio: Billing alert in Google Cloud billing dashboard → suggest **$50/month during dev**

---

## Needed for M3 (OCR pipeline expansion)

| # | Service | Status | What it's for | Where to get | Env var name |
|---|---|---|---|---|---|
| 3 | **Google Cloud Vision** | ☐ pending | Additional OCR reading line (DOCUMENT_TEXT_DETECTION) per §3.3, esp. modern printed Arabic. **Different from Google AI Studio** — this is a GCP product. | [console.cloud.google.com](https://console.cloud.google.com) → create project → enable "Cloud Vision API" → create service account → download JSON key file | `GOOGLE_CLOUD_VISION_CREDENTIALS_JSON` (path) |

**Budget cap**: Set quota / spending alert at $30/month. Cloud Vision pricing is ~$1.50 per 1000 pages.

---

## Needed for M5 (Hadith + Qurʾān integration)

| # | Service | Status | What it's for | Where to get | Env var name |
|---|---|---|---|---|---|
| 4 | **sunnah.com API key** | ☐ pending | Hadith verification source P-1 (Pflichtquelle per [§4.16.1](docs/canon/de/dokument_1.md)) | [sunnah.com/developers](https://sunnah.com/developers) — request via form | `SUNNAH_COM_API_KEY` |
| 5 | **dorar.net API access** | ☐ pending | Hadith P-3 Pflichtquelle. API path primary, scraping only as fallback per [Dokument 2 §2.12 A-6](docs/canon/de/dokument_2.md) | [dorar.net](https://dorar.net) — check API docs / contact form | `DORAR_NET_API_KEY` (if applicable) |
| 6 | **hadeethenc.com (E-5)** | ☐ pending | E-5 in Sonderrolle per §4.16.2 — "deutsche Übersetzungsquelle / mehrsprachige Referenzquelle". Official Live-API + Bulk-Downloads. | hadeethenc.com developer/API page | `HADEETHENC_API_KEY` (if applicable) |
| 7 | **quranenc.com** | ☐ public API | Qurʾān translations (german_rwwad, english_rwwad) per §4.15 | Public API — most endpoints don't require a key | `QURANENC_API_KEY` (if applicable) |
| 8 | **AR-Referenzbestand source** | ☐ DECISION NEEDED | Arabic Qurʾān reference text + vocalization per §4.15.1. **Canonically open per Dokument 1 §4.15.1** — your decision. Default placeholder: [Tanzil project](http://tanzil.net) vocalized Hafs text. | tanzil.net — direct download (no key) | N/A — local file path |

---

## Needed for M5 (deployment / production)

| # | Service | Status | What it's for | Where to get | Env var name |
|---|---|---|---|---|---|
| 9 | **Fly.io API token** | ☐ pending | CI/CD deploy from GitHub Actions | [fly.io/user/personal_access_tokens](https://fly.io/user/personal_access_tokens) → Create token | `FLY_API_TOKEN` (GitHub secret) |
| 10 | **Transactional email** | ☐ pending | Account verification, expiry warnings (Tier 1 inactivity, Tier 2 expiry per Dokument 1 §2.3), notifications per §3.6 | Recommend **Resend** ([resend.com](https://resend.com)) — modern, $20/mo for 50K emails. Alt: Postmark, AWS SES. | `RESEND_API_KEY` (or equivalent) |
| 11 | **Domain registrar** | ☐ pending | Production URL | Recommend Cloudflare or Namecheap | N/A — DNS config |

---

## Recommended (not blocking)

| # | Service | Status | What for | Where | Env var name |
|---|---|---|---|---|---|
| 12 | **Sentry** | ☐ optional | Error tracking, exception monitoring | [sentry.io](https://sentry.io) — generous free tier | `SENTRY_DSN` |
| 13 | **GitHub PAT** (only if needed) | ☐ optional | Private repo CI/CD or cross-repo automation | github.com → Settings → Developer settings → Personal access tokens (fine-grained) | `GITHUB_TOKEN` (per workflow) |

---

## Things that DO NOT need external keys

These are either self-hosted (no key) or auto-managed by Fly (creds auto-injected):

| Component | Why no key |
|---|---|
| PostgreSQL | `fly postgres create` → `DATABASE_URL` auto-injected |
| Redis | `fly redis create` → `REDIS_URL` auto-injected |
| Tigris (S3-compatible storage) | `fly storage create` → `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_ENDPOINT_URL_S3` auto-injected |
| kraken, Real-ESRGAN, CAMeL Tools, Farasa, Mishkal, LayoutParser, DocTR | Open source, self-hosted |
| Shamela | Depends on data source — BOK files / OpenITI corpus need no keys |
| JWT signing | Generate locally: `openssl rand -hex 32` |
| bcrypt | Library, no service |

---

## Cost-control checklist (do this on day 1 for any key obtained)

- [ ] OpenAI: hard monthly limit set at `platform.openai.com/account/limits`
- [ ] Google AI Studio: billing alert set in Google Cloud Console
- [ ] Google Cloud Vision: project-level quota cap configured
- [ ] Per-account quota implemented in Waraq backend (Tier 1 free users get N pages/month)
- [ ] Per-book cost telemetry logged to Sentry / Postgres so cost-per-book is observable

---

## Local handling — `.env` file

When you obtain keys, they go in `backend/.env` (gitignored). The repo will
have a `backend/.env.example` (tracked) listing all variable names with empty
values, so anyone can see what's needed without seeing actual values.

Example shape (will be created when we wire the first key in):

```
# backend/.env
GOOGLE_AI_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_CLOUD_VISION_CREDENTIALS_JSON=/path/to/service-account.json
DATABASE_URL=postgres://...
REDIS_URL=redis://...
JWT_SECRET=...
# etc.
```

For Fly deployment, secrets go via `fly secrets set GOOGLE_AI_API_KEY=...`
and are encrypted at rest in Fly's vault. Never put real keys in `fly.toml`
or any tracked file.

---

## Priority working order

**Today / tomorrow** (blocks M1 OCR code):
1. Google AI Studio API key
2. OpenAI API key

**During M1–M2**:
3. Google Cloud Vision (GCP service account JSON)

**Mid-project (M3)**:
4. sunnah.com API key
5. dorar.net access verification
6. AR-Referenzbestand source decision

**Pre-launch (M5)**:
7. Fly.io deploy token
8. Resend (or equivalent email)
9. Domain
10. Sentry account

---

## Status legend

- ☐ pending — not yet obtained
- ☐ DECISION NEEDED — waiting on user choice (not just key acquisition)
- ☐ public API — no key required, just integration work
- ☐ optional — recommended but not blocking
- ✅ obtained — key is in `backend/.env` and tested
