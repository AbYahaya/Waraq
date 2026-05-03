# Waraq

Translation platform for classical Arabic Islamic texts → German (primary) and English.

## Repo layout

```
Waraq/
├── CLAUDE.md           — agent briefing + hard discipline rules
├── WORKLOG.md          — current project state (read first when resuming work)
├── MILESTONES.md       — client-agreed M1–M5 breakdown + canon mapping
├── docs/canon/         — canonical specification (frozen v1.0)
├── backend/            — Python 3.12 + FastAPI + Postgres + Celery
└── infra/              — docker-compose (Postgres 16 + Redis 7)
```

## Resuming work

If you're picking this up cold (new dev, new Claude session, post-context-loss):
read [WORKLOG.md](./WORKLOG.md) first. It tracks active milestone, last-completed
ticket, next ticket, blockers, and decisions made outside canon.

## Quickstart (local dev)

```bash
# 1. Bring up Postgres + Redis
docker compose -f infra/docker-compose.yml up -d

# 2. Backend setup
cd backend
python3 -m venv .venv --without-pip
.venv/bin/python -m ensurepip --upgrade   # or curl get-pip.py if ensurepip missing
.venv/bin/pip install -e ".[dev]"

# 3. Run the test suite
.venv/bin/pytest

# 4. Quality gate
.venv/bin/ruff check waraq tests
.venv/bin/ruff format --check waraq tests
.venv/bin/mypy waraq
```

## Discipline

Read [CLAUDE.md](./CLAUDE.md) before changing any code. The canon is in
[docs/canon/](./docs/canon/). The 11 `falsche Abkürzungen` in
[DBB §B](./docs/canon/de/delivery_backlog_baseline_v1_0.md) and the 21 entries
in [CAB §I.3](./docs/canon/de/core_architecture_baseline_v1_0.md) are
non-negotiable. The INVARIANT-Guard is non-deactivatable by construction; do
not add `enabled` flags or env-var toggles.

## Status

Milestone 1 in progress. Day 0 complete: foundation skeleton, IDENTITY service
(T-1.1.1, T-1.1.2), INVARIANT-Guard (T-1.2.1, T-1.2.2), all H-test family tests
(T-H1-01, T-H1-02, T-H4-01, T-H4-02, T-H5-01, T-H5-02, T-H6-01, T-H7-01) green.
