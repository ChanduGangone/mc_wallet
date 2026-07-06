# Multi-Currency Wallet Platform

[![CI](https://github.com/ChanduGangone/mc_wallet/actions/workflows/ci.yml/badge.svg)](https://github.com/ChanduGangone/mc_wallet/actions/workflows/ci.yml)

A full-stack wallet platform: account creation, multi-currency wallets, currency conversion,
user-to-user transfers, and transaction history.

## Status

Core platform complete — auth, multi-currency wallets, transfers, transaction history, a Vue 3
frontend, a pytest integration suite, Docker, and CI are all built and verified end-to-end.

- [x] Account creation & authentication (JWT + rotating refresh tokens)
- [x] Multi-currency wallet management (credit/debit, idempotency-key protected)
- [x] Currency conversion (daily exchange-rate sync, staleness fallback, conversion traceability)
- [x] User-to-user transfers (by email, deadlock-safe two-wallet locking)
- [x] Transaction history (filters + pagination)
- [x] Test suite (58 pytest tests, dedicated Postgres, mocked exchange-rate provider)
- [x] Frontend (Vue 3 + Vuetify + Vuex)
- [x] Dockerized (server, app, db)
- [x] CI (GitHub Actions: backend tests + frontend build on every push/PR)
- [ ] CD (automated deploy on merge — deploys are currently manual via Render's dashboard)
- [x] Public deployment URL (see [Deployment](#deployment)) — https://mc-wallet-frontend.onrender.com/
- [ ] Structured logging / monitoring / alerting (see `ARCHITECTURE.md` for the intended approach)

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL
- **Frontend:** Vue 3, Vuetify, Vuex, vue-router, Axios
- **Auth:** JWT access tokens (15 min) + opaque, hashed, rotating refresh tokens
- **Exchange rates:** [frankfurter.dev](https://frankfurter.dev) (free, no API key), synced daily via APScheduler
- **Testing:** pytest, real Postgres (not mocked), mocked exchange-rate provider
- **Containerization:** Docker, docker-compose
- **CI/CD:** GitHub Actions (CI); Render Blueprint for deployment

## Project Structure

```
server/                       FastAPI backend
  app/
    api/routers/              auth, users, wallets, transfers, transactions, exchange_rates
    core/                     security, currencies, exchange_rates, uploads, scheduler
    models/                   SQLAlchemy models (User, Wallet, Transaction, ExchangeRateSnapshot, RefreshToken)
    schemas/                  Pydantic request/response schemas
  alembic/                    DB migrations
  tests/                      pytest suite + its own dedicated docker-compose.yml
  Dockerfile
app/                          Vue 3 frontend
  src/
    api/                      axios client + per-resource API modules
    store/                    Vuex modules (auth, wallets)
    views/, components/       screens and reusable UI pieces
  Dockerfile
docker-compose.yml            Postgres only — for native (non-containerized) dev
docker-compose.prod.yml       full stack, all containerized
render.yaml                   Render Blueprint (Postgres + backend + frontend)
```

## Setup & Run Steps

### Option A — Docker (fastest way to try it)

```bash
export JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
docker compose -f docker-compose.prod.yml up --build -d
```

`JWT_SECRET_KEY` is a required env var with no default — Compose fails fast with a clear message
if it's unset, rather than silently falling back to a known value.

Builds and starts all three services:
- **Postgres** — internal only, no host port exposed
- **Backend** — runs Alembic migrations automatically on startup, serves on `http://localhost:8000`
- **Frontend** — production Vite build served via nginx on `http://localhost:8080`

Open `http://localhost:8080` — signup, wallets, transfers, and history all work end-to-end.

```bash
docker compose -f docker-compose.prod.yml ps    # check health status
docker compose -f docker-compose.prod.yml down  # stop (data persists in named volumes)
```

> This compose file pins its own project name (`mc_wallet_prod`) so it never collides with the
> plain `docker-compose.yml` used for native dev below. If you're already running the native dev
> server on port 8000, stop it first — both bind the same host port.

### Option B — Native (for active development)

**1. Database**
```bash
docker compose up -d
docker compose ps   # wait until "healthy"
```
Runs on `localhost:5435` (not 5432, to avoid clashing with other local Postgres instances).

**2. Backend**
```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then set a real JWT_SECRET_KEY (see comment in the file)
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```
Verify: `curl http://localhost:8000/health` → `{"status":"ok","db":"connected"}`

**3. Frontend**
```bash
cd app
npm install
npm run dev
```

### Running the tests

```bash
cd server
docker compose -f tests/docker-compose.yml up -d   # dedicated test Postgres, port 5436
pytest -v
```

58 tests covering auth, wallets, transfers (including a concurrency regression test —
see [Known Limitations](#known-limitations) / `ARCHITECTURE.md`), transaction history, and the
exchange-rate debug endpoint. CI runs the same suite on every push/PR against a fresh Postgres
service container.

## API Overview

All endpoints except signup/login/refresh/logout and the exchange-rate debug endpoint require
`Authorization: Bearer <access_token>`. Money-moving endpoints additionally require an
`Idempotency-Key` header.

| Method & Path | Purpose |
|---|---|
| `POST /auth/signup` | Create account (auto-creates a wallet in `default_currency`) |
| `POST /auth/login` | Get access + refresh tokens |
| `POST /auth/refresh` | Rotate refresh token, get new access token |
| `POST /auth/logout` | Revoke a refresh token |
| `GET /users/me` / `PATCH /users/me` | View/edit profile (name, default currency, photo) |
| `GET /wallets` | List the caller's wallets |
| `POST /wallets/{id}/credit` | Deposit funds (any currency, converted if needed) |
| `POST /wallets/{id}/debit` | Withdraw funds (native currency only) |
| `POST /transfers` | Send money to another user by email, any currency pair |
| `GET /transactions` | Filtered, paginated transaction history |
| `GET /exchange-rates/latest` | Debug endpoint — current USD-relative rates |
| `GET /health` | DB connectivity check |

## Deployment

The repo includes a [`render.yaml`](./render.yaml) Blueprint that provisions Postgres, the backend,
and the frontend from one file.

1. Push this repo to GitHub.
2. In the Render dashboard: **New → Blueprint**, connect the repo. Render reads `render.yaml` and
   shows the three resources it will create (`mc-wallet-db`, `mc-wallet-backend`,
   `mc-wallet-frontend`). Click **Apply**.
3. `JWT_SECRET_KEY` is auto-generated by Render — nothing to set by hand for a first deploy.
4. Wait for all three services to deploy (the backend runs migrations automatically on startup).

**About the predicted URLs:** the frontend's `VITE_API_BASE_URL` (build-time) and the backend's
`CORS_ALLOWED_ORIGINS` need each other's public URL, but Render's Blueprint `fromService` only
exposes a service's *private*-network address, not its public `.onrender.com` URL. `render.yaml`
therefore hardcodes the *predicted* URLs from the exact service names in that file. This holds as
long as those names aren't already taken by someone else on Render — if Render appends a suffix
instead, update `CORS_ALLOWED_ORIGINS` (backend) and `VITE_API_BASE_URL` (frontend) in the
dashboard to match; both redeploy automatically on save.

**Public URL:** https://mc-wallet-frontend.onrender.com/ (backend: https://mc-wallet-backend.onrender.com)

**Demo accounts** (already have funded wallets — useful for trying transfers without signing up):

| Email | Password |
|---|---|
| `demo_user1@gmail.com` | `test1234` |
| `demo_user2@gmail.com` | `test12345` |

> Free-tier note: the backend cold-starts (~1 min) if it's been idle 15+ minutes, and the free
> Postgres expires 30 days after creation — see [Known Limitations](#known-limitations).

## Assumptions

- Exchange rates are USD-relative (frankfurter.dev's base currency); all cross-currency math
  triangulates through USD.
- Supported currencies are a fixed 20-code subset of ISO 4217 (`server/app/core/currencies.py`),
  not the full ISO 4217 list or a dynamic provider lookup.
- A transfer recipient is identified by the email of an *existing* account — there's no
  invite-a-new-user flow.
- One wallet per `(user, currency)` pair; a user can hold balances in multiple currencies
  simultaneously, but never two wallets in the same currency.
- The scale exercise (500k users / 100 TPS) is a forward-looking design discussion
  (see `ARCHITECTURE.md`), not a requirement the current single-instance deployment meets today.
- Exchange rates refresh once daily, matching the provider's actual publish cadence.

## Trade-offs

Deliberate engineering decisions, made for this project's time budget and scope — not oversights:

- **Single-entry `transactions` ledger**, not full double-entry accounting. Simpler and adequate
  here; a production ledger would want double-entry for stronger auditability.
- **Local disk photo storage**, not S3. Faster to build; the code isolates this behind one function
  (`core/uploads.py`) so swapping to S3 + pre-signed URLs later is a contained change.
- **JSON-body refresh tokens**, not httpOnly cookies. Simpler client integration; marginally more
  exposed to XSS than a cookie-based approach.
- **Hardcoded currency allowlist**, not a dynamic provider lookup. Predictable, no extra network
  dependency on every signup/profile-edit/transfer validation.
- **Offset/limit pagination**, not cursor-based, for transaction history. Simpler to implement and
  reason about; less efficient at very large offsets, not a concern at current scale.
- **Vuex over Pinia** for frontend state — an explicit choice for this project, despite Pinia being
  the more commonly recommended default for new Vue 3 apps today.
- **Render's native static-site hosting for the frontend in production**, vs. the Docker/nginx image
  used for self-hosting (`docker-compose.prod.yml`). Render's Blueprint spec has no mechanism to pass
  another service's URL as a Docker build ARG, so the static-site build path (which accepts plain
  build-time env vars) avoids fighting the platform. Both paths build from the same source.
- **Argon2 at default cost in tests too** — no test-only fast hasher, so the test suite exercises the
  exact same password-hashing code path as production, at the cost of ~50-100ms per signup in tests.
- **Single Postgres instance**, no read replica or partitioning yet — appropriate for current scale;
  deferred deliberately (see the scaling discussion in `ARCHITECTURE.md`).

## Known Limitations

- **Login/signup rate limiting is not implemented** — no Redis/limiter wired up yet. A real gap
  before real-world exposure at scale; documented rather than silently skipped.
- **No CD** — deploys are manually triggered via Render's dashboard (Apply on the Blueprint), not
  automatic on merge.
- **Render free tier constraints**: Postgres expires 30 days after creation (grace period to
  upgrade before deletion); the backend's free web service has no persistent disk, so uploaded
  profile photos won't survive a redeploy there specifically; free services cold-start (~1 min)
  after 15 minutes idle.
- **No structured logging / APM / alerting** — only basic Python `logging` calls and a
  DB-connectivity health check exist today. See `ARCHITECTURE.md` for the intended approach.
- **No email verification or password reset flow.**
- **`refresh_tokens` rows are never purged** — revoked/expired rows accumulate; needs a periodic
  cleanup job at scale.
- **No user directory/search** — the transfer flow requires knowing the recipient's exact email.
- A real concurrency bug was found and fixed during development (SQLAlchemy identity-map staleness
  under concurrent transfers) — the regression test that caught it lives at
  `server/tests/test_transfer_concurrency.py`, and the incident is documented in `ARCHITECTURE.md`.

## Further Reading

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — domain model, key design decisions, and the scale
  design note (500k users / 20k DAU / 100 TPS / exchange-provider-downtime scenario)
- [`AI_USAGE.md`](./AI_USAGE.md) — how AI tools were used during development
