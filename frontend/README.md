# Waraq Frontend

React 19 + Vite + TypeScript + Tailwind + shadcn-style components + TanStack Query + Zustand.

Built as the post-canonical product UI on top of the Waraq backend (`../backend`). M4 in `../MILESTONES.md`.

## Run

In one terminal, start the backend:

```sh
cd ../backend
.venv/bin/uvicorn waraq.api.main:app --reload
```

In another, start the frontend dev server:

```sh
npm install
npm run dev
```

Vite proxies `/api` to the backend. Override the local proxy target via `BACKEND_URL=...` env var (defaults to `http://127.0.0.1:8000`).

## Build

```sh
npm run build       # tsc -b && vite build → dist/
npm run preview     # serve the built dist/
```

For hosted frontend builds, set `VITE_API_URL=https://<backend>.fly.dev`.
Leave it empty for local development so requests go through Vite's `/api`
proxy.

## Toolchain

- **React 19** with the new JSX runtime
- **Vite 6** dev/build
- **TypeScript 5** strict + erasable-syntax-only
- **Tailwind 3.4** + PostCSS + Autoprefixer
- **TanStack Query 5** for server state (polling-based job state per the M4 stack decision)
- **Zustand 5** with `persist` for the auth token + current account
- **React Router 7** for routing
- **Radix UI** primitives + `class-variance-authority` for shadcn-style components in `src/components/ui/`

## Layout

```
src/
  main.tsx            entry
  App.tsx             routes + providers
  index.css           Tailwind layers + shadcn CSS variables
  lib/
    api.ts            typed fetch wrapper (auto-attaches bearer token)
    types.ts          backend Pydantic shapes mirrored
    utils.ts          cn() helper
  store/
    auth.ts           Zustand auth store (persisted)
  components/
    AppShell.tsx      authenticated app layout
    RequireAuth.tsx   route guard
    ui/               Button, Input, Label, Card
  pages/
    Login.tsx
    Register.tsx
    Dashboard.tsx     project list + create
    ProjectWorkspace.tsx  Day 3+
```
