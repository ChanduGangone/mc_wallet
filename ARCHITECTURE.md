# Architecture

This document explains how the system is put together and why — the design decisions, data
flows, and trade-offs behind the Multi-Currency Wallet Platform. For setup/run/deploy instructions,
see [`README.md`](./README.md).

## 1. System Overview

```
┌──────────────┐      HTTPS/JSON       ┌──────────────────┐      SQL       ┌─────────────┐
│  Vue 3 SPA   │ ───────────────────▶  │  FastAPI backend │ ─────────────▶ │  PostgreSQL │
│ (Vuetify/    │ ◀───────────────────  │  (sync routes,    │ ◀───────────── │             │
│  Vuex)       │   JWT + refresh flow  │  SQLAlchemy 2.0)  │                └─────────────┘
└──────────────┘                       └─────────┬────────┘
                                                   │ daily sync (APScheduler)
                                                   ▼
                                       ┌───────────────────────┐
                                       │  frankfurter.dev       │
                                       │  (exchange rate API)   │
                                       └───────────────────────┘
```

- **Frontend**: Vue 3 SPA, talks to the backend exclusively over a JSON REST API via Axios. No
  server-side rendering, no direct DB access.
- **Backend**: FastAPI, synchronous route handlers (SQLAlchemy 2.0's sync engine + psycopg2), JWT
  auth, a single Postgres database for everything (users, wallets, transactions, exchange-rate
  snapshots, refresh tokens).
- **Exchange rates**: fetched from frankfurter.dev once daily by an in-process APScheduler job,
  persisted to Postgres — never called synchronously as part of a user request unless the cached
  rate has gone stale (see §4.3).

## 2. Domain Model

```
User ──1───< Wallet ──1───< Transaction (as from_wallet or to_wallet)
 │                                │
 └──1───< RefreshToken            └───< references ExchangeRateSnapshot (from_rate / to_rate)
```

| Entity | Purpose | Key design choices |
|---|---|---|
| **User** | Account identity | `default_currency` drives the wallet auto-created at signup and the fallback currency for transfers |
| **Wallet** | One balance in one currency | Unique on `(user_id, currency)` — a user can hold many currencies, never two wallets in the same one. `balance` is `Numeric(18,4)` with a `CHECK balance >= 0` |
| **Transaction** | An immutable ledger row for every credit/debit/transfer | Single-entry (not double-entry — see §6). Carries `from_wallet_id`/`to_wallet_id` (nullable — null `from` = pure credit, null `to` = pure debit), `amount`, `converted_amount`, and **two** snapshot references for auditability (see §4.2) |
| **ExchangeRateSnapshot** | One historical USD-relative rate for one currency | Never mutated; a new row is inserted on every refresh, so any past transaction's rate can always be reconstructed |
| **RefreshToken** | One login session | Stores a SHA-256 hash of the token, not the raw value; `revoked` flag; rotated on every use |

Currency codes are validated against a **hardcoded 20-code ISO 4217 subset**
(`server/app/core/currencies.py`), reused identically across signup, profile edit, wallet
credit/debit, and transfers — a single source of truth rather than four places that could drift.

## 3. Authentication & Security

- **Access tokens**: JWT, HS256, 15-minute expiry. Stateless — no DB lookup needed to validate one.
- **Refresh tokens**: opaque random strings (`secrets.token_urlsafe`), **not** JWTs. The raw token
  is only ever shown to the client once; the server stores a SHA-256 hash. **Rotated on every use**
  — refreshing invalidates the old token and issues a new one, so a stolen-and-replayed old refresh
  token is detectable (it'll already be revoked).
- **Passwords**: Argon2id (`argon2-cffi`, OWASP's current recommendation), never logged or returned.
- **Login enumeration protection**: wrong password and unknown email return the identical
  `401 {"detail": "Invalid email or password"}` — no signal about which field was wrong.
- **Photo upload validation**: the server never trusts the client's declared MIME type or filename
  extension — it sniffs the first bytes of the file against known magic numbers (JPEG/PNG/GIF/WEBP)
  before accepting it, and generates the stored filename server-side (no user input reaches the
  filesystem path, eliminating path traversal by construction).
- **CORS**: explicit allowlist (`CORS_ALLOWED_ORIGINS` env var), not `*` — required because
  `Authorization` and `Idempotency-Key` are non-"simple" headers that trigger preflight.
- **Known gap** (documented, not silently skipped): login/signup rate limiting isn't implemented —
  no Redis is wired up yet. See §8.

## 4. Currency Exchange — the core integration

### 4.1 Sync strategy

A single reusable function, `fetch_and_store_snapshot()`, calls
`GET https://api.frankfurter.dev/v1/latest?base=USD` and inserts **one new row per currency** into
`exchange_rate_snapshots` — never updates existing rows, so history is always intact. It's:

- Run **once daily** by an in-process APScheduler job (`core/scheduler.py`) — matches the
  provider's actual publish cadence; polling more often would just refetch identical numbers.
- Run **once on startup** if no snapshot exists for "today" (`ensure_todays_snapshot()`), so the
  system never boots with zero rate data after a fresh deploy.
- **All-or-nothing**: every currency's row is added in one DB transaction; any failure mid-fetch
  rolls back the whole batch rather than leaving a partial, inconsistent set of rates.

### 4.2 Conversion traceability

Every `Transaction` that involves a currency conversion stores **two** nullable foreign keys —
`from_rate_snapshot_id` and `to_rate_snapshot_id` — instead of just a single computed exchange
rate number. This means any historical transfer's exact conversion can be reconstructed and
audited later, not just trusted at face value:

- Same-currency operation → both refs null.
- One side is USD (the base currency) → only the *other* side's ref is set (USD's own "rate" is
  trivially 1.0, no snapshot row needed to represent it).
- Neither side is USD → both refs set; `cross_rate = to_rate / from_rate`, triangulating through USD.

This falls out of the code naturally: `get_latest_rate("USD")` always returns `snapshot_id=None` by
convention, so callers don't need special-case branching for "is this side the base currency" —
the nulling happens automatically depending on which currencies are involved.

### 4.3 Staleness handling (exchange provider downtime)

`get_latest_rate(currency)`:
1. Returns `(1.0, None)` immediately if `currency == "USD"` — no lookup needed.
2. Otherwise fetches the latest snapshot row. If it's missing or older than **36 hours** (one
   missed daily cycle + buffer), it triggers **one** synchronous on-demand refetch.
3. If that refetch also fails (provider is down), raises `ExchangeRateUnavailable` →
   the caller returns `503` — the system **never silently uses a stale rate or guesses**.

This is also the single biggest scale risk in the current design — see §7.4.

## 5. Money-Moving Endpoints

### 5.1 Credit / Debit (`POST /wallets/{id}/credit` / `/debit`)

- **Credit** accepts *any* currency and converts into the wallet's currency if different —
  depositing foreign cash into an account, essentially.
- **Debit** is native-currency-only, no conversion — you withdraw in the currency you hold.
- Both use a **single atomic SQL `UPDATE ... RETURNING`** for the balance change
  (`balance = balance + :amount`) rather than a Python read-modify-write. This is safe under
  concurrency without needing row locks: the arithmetic happens inside Postgres in one statement,
  so two concurrent credits can never "lose" one of them. Debit additionally guards
  `WHERE balance >= :amount` so "insufficient balance → reject, no write" is a single race-free
  round trip, not a check-then-act bug.

### 5.2 Transfers (`POST /transfers`) — the hard part

Transfers move money between **two** wallets, which is a fundamentally different concurrency
problem than credit/debit's single-row atomicity:

1. Resolve the sender's wallet (ownership check: 404/403).
2. Resolve the receiver by **email** (not a raw user ID — see the Trade-offs section in
   `README.md`), resolve/auto-create their wallet in the target currency.
3. Reject self-transfer to the *same* wallet (transferring to a different currency wallet of your
   own account is explicitly allowed).
4. **Lock both wallets** via two separate, sequential `SELECT ... FOR UPDATE` statements, always
   issued in **ascending wallet-ID order**. This is the deadlock-prevention mechanism: a single
   `SELECT ... WHERE id IN (a,b) ORDER BY id FOR UPDATE` does **not** guarantee Postgres actually
   acquires the row locks in that order (locking happens during the scan, sorting can happen
   after) — two transactions could then lock the same two rows in opposite order and deadlock.
   Two separate single-row locks, always smaller-ID-first, guarantee every transaction requests
   the shared locks in the same order, making a circular wait impossible.
5. Check balance, compute conversion (before touching any balance, so a rate-unavailable failure
   never leaves a half-applied debit), mutate both wallets in Python (safe now — the locks are
   held), insert the `Transaction` row, commit.
6. **Idempotency**: every money-moving request requires an `Idempotency-Key` header. A duplicate
   key returns the *original* transaction's result (200) instead of reprocessing; the fast-path
   check happens before any mutation, and a race between two concurrent requests with the same
   fresh key is resolved by catching the unique-constraint `IntegrityError` on insert and
   re-querying the winner — no double-processing under any interleaving.

### 5.3 A real bug this design caught

During development, a concurrency stress test (60+ simultaneous bidirectional transfers between
the same two wallets) found that **money was being created out of thin air** — balances didn't
conserve. Root cause: SQLAlchemy's identity map returned a **stale cached Python object** for a
wallet that had already been loaded earlier in the same request (via an unlocked ownership check),
even though the subsequent `SELECT ... FOR UPDATE` correctly acquired the database-level lock. The
lock was real; the in-memory object being mutated wasn't refreshed from it. Fixed with
`.execution_options(populate_existing=True)` on the locking query, forcing SQLAlchemy to overwrite
the cached object with the freshly-locked row's actual data.

The regression test that caught this — `server/tests/test_transfer_concurrency.py` — was verified
to actually catch the bug (not just pass vacuously) by temporarily reverting the fix and confirming
the test failed reliably across repeated runs before restoring it.

## 6. Deliberate Simplifications

Documented here as conscious choices, not oversights — see `README.md` for the full list:

- **Single-entry ledger.** Each `Transaction` row records one movement with `from`/`to` wallet
  references, rather than a full double-entry system with separate debit/credit journal lines per
  account. Sufficient for this scope; a production ledger handling real regulatory/audit
  requirements would want double-entry.
- **Local disk photo storage**, isolated behind one function (`core/uploads.py`) so it's a
  contained swap to S3 + pre-signed URLs later.
- **Offset/limit pagination** for transaction history, not cursor-based.

## 7. Testing Strategy

- **Real Postgres, not mocks** — a dedicated test database (`server/tests/docker-compose.yml`,
  separate container from dev), because this system leans on Postgres-specific behavior
  (`SELECT...FOR UPDATE`, CHECK/unique constraints, native UUID/Numeric types) that a fake DB
  can't faithfully exercise. This fidelity is exactly what caught the bug in §5.3 — a mocked DB
  would have hidden it, not caught it.
- **Mocked exchange-rate provider only** — the one genuinely external, non-deterministic dependency.
  Everything else (DB, auth, locking) is exercised for real.
- **58 tests** across auth, wallets, transfers (including the concurrency regression test),
  transaction history, and exchange rates. CI runs the full suite against a fresh Postgres service
  container on every push/PR.

## 8. Scale Design Note (500k users / 20k DAU / 100 TPS / exchange-provider-downtime)

*This section is a forward-looking design discussion, not implemented — the current deployment is
a single free-tier instance.*

### 8.1 The most urgent risk at this scale

`get_latest_rate()`'s on-demand refetch (§4.3) makes a **synchronous outbound HTTP call inside the
request path** with a 10-second timeout. If frankfurter.dev is down or slow during a traffic spike,
every conversion-requiring request that hits a stale rate blocks a worker thread for up to 10s
waiting on a dead third party. At 100 TPS this is a textbook cascading failure: threads pile up,
the pool exhausts, and *unrelated* requests (login, `GET /wallets`) start failing too — not just
the currency-conversion ones. **Fix**: refresh proactively and often enough (hourly, well inside
the 36h budget) that a request-time refetch essentially never fires; if it does, cut the timeout to
1-2s and fail fast; move the scheduled refresh itself into a proper task queue (Celery/Arq) with
retry+backoff instead of in-process APScheduler.

### 8.2 Scaling approach

100 TPS overall is achievable with a handful of stateless app replicas (3-6) behind a load
balancer — JWT auth already supports this with no sticky sessions needed. One structural blocker
must be fixed first: **APScheduler runs in-process**, so N replicas would each independently fire
the daily rate-refresh job. Fix: extract it into a single external cron/k8s CronJob, or wrap the
job body in a distributed (Postgres/Redis advisory) lock.

### 8.3 Database strategy

- **PgBouncer** (transaction-pooling mode) once running multiple app replicas, to avoid exhausting
  Postgres's connection limit.
- **Read replica** for `GET /wallets`, `GET /transactions`, `GET /exchange-rates/latest` — none
  need primary-freshness guarantees except immediately after the caller's own mutation.
- **Partition `transactions` by `created_at`** once it reaches tens of millions of rows — already
  indexed on that column in a way that supports this without a schema rewrite.
- **Purge `refresh_tokens`** periodically — revoked rows currently accumulate forever.
- Transfer's per-wallet row locking is fine at 100 TPS spread across many wallets; a single "hot"
  wallet (e.g. a popular merchant account) would become a queuing point — worth watching
  `pg_locks`/lock-wait p99 as a leading indicator, not something to pre-solve.

### 8.4 Caching

- **Exchange rates**: the highest-value cache candidate — read on every conversion, changes once a
  day. Cache in Redis with a TTL matching the staleness window.
- **Idempotency-key lookups**: cache as an optimization only; the DB unique constraint remains the
  actual correctness guarantee, never the cache alone.
- **Wallet balances: deliberately not cached** — this is a ledger; a stale balance read is a
  correctness bug, not a performance win. Solved via the read replica instead.

### 8.5 Async processing

Beyond the exchange-rate fix in §8.1: any genuinely slow operation (email/receipt notifications,
CSV export of transaction history) should go through a task queue rather than block a request.
None of that exists yet, but the idempotency-key mechanism already built into every money-moving
endpoint is exactly the right foundation for making queued/retried task executions safe.

### 8.6 Cost optimization

- Don't over-provision — 100 TPS with a 20k DAU diurnal pattern means real headroom to autoscale
  down overnight rather than sizing for 24/7 peak.
- **Local photo storage becomes a correctness problem, not just a documented limitation, the
  moment there's more than one app replica** — a photo uploaded via instance A is invisible via
  instance B. S3 + CloudFront is both cheaper at this scale and fixes that.
- frankfurter.dev is free and called once a day — a complete non-issue cost-wise.

### 8.7 Operational considerations

- **Rate limiting** (documented gap) must land before real exposure at 500k registered users.
- **Observability**: structured logging, tracing, and metrics don't exist yet — needed specifically
  to see the failure modes in §8.1/§8.3 before they page someone instead of showing up on a
  dashboard first.
- Extend `/health` to report exchange-rate staleness and scheduler liveness, turning "rates went
  stale" into a proactive alert instead of a wave of 503s.
- Strict backward-compatible ("expand/contract") Alembic migrations once multiple replicas exist,
  so a rolling deploy never runs against a half-migrated schema.
- Move secrets (`JWT_SECRET_KEY`, DB credentials) to a real secrets manager before production.

### 8.8 Detecting elevated 4XX/5XX rates

Not implemented, but the approach: track the ratio of 4xx/5xx responses to total responses over a
rolling window (e.g., 5 minutes) per endpoint, exported as a metric from the same place a request
logger would sit (middleware). Alert when that ratio crosses a threshold (e.g., 5xx rate > 1% or
a sudden multiple-of-baseline jump in 4xx on a specific endpoint, which often signals a client
bug/bad deploy rather than organic traffic). This is conceptually identical to the exchange-rate
staleness health check already built — a threshold-crossing check on a rolling metric — just
applied to HTTP status codes instead of rate-snapshot age.
