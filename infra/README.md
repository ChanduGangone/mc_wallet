# Infrastructure

Infra-as-code lives at each component's natural location rather than gathered under this folder —
moving it here would mean fixing relative Docker build contexts (`docker-compose.prod.yml`) and
manually repointing the **already-deployed** Render Blueprint to a new file path in their
dashboard, for a folder-naming technicality. This folder exists so the repository has an `infra/`
entry at the root, per the assignment's submission checklist. Here's where things actually are:

| File | Purpose |
|---|---|
| [`../docker-compose.yml`](../docker-compose.yml) | Postgres only — for native (non-containerized) backend/frontend dev |
| [`../docker-compose.prod.yml`](../docker-compose.prod.yml) | Full stack, all containerized: Postgres + backend + frontend |
| [`../server/Dockerfile`](../server/Dockerfile) | Backend image — runs Alembic migrations on startup, non-root user |
| [`../server/docker-entrypoint.sh`](../server/docker-entrypoint.sh) | Migration-then-serve entrypoint used by the backend image |
| [`../app/Dockerfile`](../app/Dockerfile) | Frontend image — multi-stage Vite build served via nginx (used for self-hosting; Render uses its own static-site build instead, see below) |
| [`../app/nginx.conf`](../app/nginx.conf) | SPA fallback routing for the nginx-served frontend image |
| [`../render.yaml`](../render.yaml) | Render Blueprint — provisions Postgres + backend + frontend for the public deployment |
| [`../server/tests/docker-compose.yml`](../server/tests/docker-compose.yml) | Dedicated, isolated Postgres for the test suite (see `../tests/README.md`) |
| [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml) | CI — runs the backend test suite + frontend build on every push/PR |

See [`../ARCHITECTURE.md`](../ARCHITECTURE.md) for the design rationale and
[`../README.md`](../README.md) for run/deploy instructions.
