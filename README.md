# Multi-Currency Wallet Platform

A full-stack wallet platform supporting account creation, multi-currency wallet
management, currency conversion, user-to-user transfers, and transaction history.

🚧 **Status:** Initial scaffold. Project structure is being set up. This README
will be updated as features land — see the checklist below for current progress.

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
- `docker-compose.yml` — local Postgres for development

## Getting Started

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
- [ ] Multi-currency wallet management
- [ ] Currency conversion
- [ ] User-to-user transfers
- [ ] Transaction history
- [ ] Dockerize (server, app, db, redis)
- [ ] CI/CD pipeline
