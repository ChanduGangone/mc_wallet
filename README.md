# Multi-Currency Wallet Platform

[![CI](https://github.com/ChanduGangone/mc_wallet/actions/workflows/ci.yml/badge.svg)](https://github.com/ChanduGangone/mc_wallet/actions/workflows/ci.yml)

A full-stack wallet platform supporting account creation, multi-currency wallet
management, currency conversion, user-to-user transfers, and transaction history.

🚧 **Status:** Core platform complete — auth, multi-currency wallets, transfers,
transaction history, and a Vue 3 frontend are all built and tested. See the
checklist below for current progress.

## Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** Vue 3
- **Database:** PostgreSQL (via Docker)
- **Cache/Queue:** Redis (planned, for exchange rate caching)
- **Containerization:** Docker, docker-compose
- **CI/CD:** GitHub Actions (planned)

## Structure

- `server/` — FastAPI backend
- `app/` — Vue 3 frontend
- `docker-compose.yml` — local Postgres for native (non-containerized) development
- `server/tests/docker-compose.yml` — dedicated Postgres for the pytest suite
- `docker-compose.prod.yml` — full stack (Postgres + backend + frontend), all containerized

## Run everything with Docker (fastest way to try it)

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

This builds and starts all three services:

- **Postgres** — internal only, no host port exposed
- **Backend** — runs Alembic migrations automatically on startup, then serves on `http://localhost:8000`
- **Frontend** — production Vite build served via nginx on `http://localhost:8080`

Open `http://localhost:8080` in a browser — signup, wallets, transfers, and history all work end-to-end.

```bash
docker compose -f docker-compose.prod.yml ps    # check health status
docker compose -f docker-compose.prod.yml down  # stop and remove containers (data persists in named volumes)
```

**Note:** this compose file declares its own project name (`mc_wallet_prod`) specifically so it
never collides with the plain `docker-compose.yml` used for native dev below — running both by
accident (with the same default project name) previously caused the dev Postgres container to be
silently recreated. Don't remove the `name:` line at the top of `docker-compose.prod.yml`.

If you're already running the native dev server on port 8000 (see below), stop it first —
both bind the same host port.

## Getting Started (native, for active development)

### 1. Database (Postgres, via Docker)

```bash
docker compose up -d
docker compose ps   # wait until status is "healthy"
```

Runs on `localhost:5435` (not the default 5432, to avoid clashing with other
local Postgres instances). Data persists in a Docker volume across restarts.

To stop it:

```bash
docker compose down
```

### 2. Server (FastAPI)

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then set a real JWT_SECRET_KEY (see comment in the file)
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Verify it's up and can reach the database:

```bash
curl http://localhost:8000/health
# {"status":"ok","db":"connected"}
```

#### Auth & Profile API

Implements signup/login/refresh/logout and profile view/edit (`server/app/api/routers/auth.py`,
`server/app/api/routers/users.py`). Notes:

- Access tokens are short-lived JWTs (15 min); refresh tokens are opaque random strings, stored
  hashed in the DB, and rotated on every use.
- Login rate-limiting (brute-force protection) is intentionally **not implemented** — no Redis/limiter
  is wired up yet. Documented here as a known gap, not an oversight.
- Profile photos are stored on local disk under `server/uploads/` and served at `/uploads/<file>`.
  This is a dev-only shortcut — a production deployment should swap this for S3 + pre-signed URLs.
- Currency codes (`default_currency`) are validated against a hardcoded ISO 4217 subset in
  `server/app/core/currencies.py`, not a dynamic provider lookup.

### 3. App (Vue 3 + Vite)

```bash
cd app
npm install
npm run dev
```

## Roadmap

- [x] Project scaffold (server + app)
- [x] Account creation & authentication
- [x] Multi-currency wallet management (credit/debit, idempotency-key protected)
- [x] Currency conversion (daily exchange-rate sync, staleness fallback)
- [x] User-to-user transfers (by email, deadlock-safe two-wallet locking)
- [x] Transaction history (filters + pagination)
- [x] Test suite (pytest, dedicated Postgres, mocked exchange-rate provider)
- [x] Frontend (Vue 3 + Vuetify + Vuex)
- [x] Dockerize (server, app, db — `docker-compose.prod.yml`)
- [x] CI (GitHub Actions runs the backend test suite + frontend build on every push/PR)
- [ ] CD (automated deploy)
- [ ] Public deployment
- [ ] Structured logging / monitoring / alerting
