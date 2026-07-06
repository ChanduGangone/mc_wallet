# AI Usage

This project was built with **Claude Code** (Claude Sonnet 5) as the implementation, testing, and
deployment tool for a design that was substantially specified up front. This document is precise
about that split — what was decided before implementation began, what AI proposed and the human
approved or redirected, and what AI implemented, tested, and verified.

## Tools Used

- **Claude Code** (Claude Sonnet 5) — implementation, testing, debugging, infrastructure, and
  documentation for the whole build: backend (FastAPI/SQLAlchemy/Alembic), frontend (Vue
  3/Vuetify/Vuex), the pytest suite, Docker, CI, and the Render deployment config.
- **Web search/fetch** for time-sensitive facts expensive to get wrong from memory — Render's
  actual current free-tier limits, and the exact Render Blueprint YAML schema — before writing
  the deployment config.

## Decisions Specified Up Front

Before implementation began, the human's prompts were explicit and clear about the core domain
design — the data model, the security requirements, and, notably, the two hardest correctness
properties in the system:

- **Row-locking strategy**: transfers lock both wallets via `SELECT ... FOR UPDATE`, in
  deterministic ascending-wallet-ID order, specifically to prevent deadlocks under concurrent
  transfers.
- **Conversion traceability**: every cross-currency transaction stores *two* exchange-rate
  snapshot references (`from_rate_snapshot_id`, `to_rate_snapshot_id`), not a single computed
  number, so any historical conversion can be reconstructed and audited later. The exact rule for
  when each reference is null (both null for same-currency, only one set when one side is the base
  currency, both set otherwise) was also specified by the human up front, not worked out by AI.

These were locked-in requirements, not something proposed during the AI-assisted build. Also
specified up front: the wallet-per-currency model, the auth token shapes (JWT access + rotating
opaque refresh tokens), the idempotency-key requirement on money-moving endpoints, the daily
exchange-rate refresh cadence, the 36-hour staleness threshold, and the frontend stack
(Vue 3/Vuetify/Vuex) — the human specified Vuex explicitly, overriding what would otherwise have
been AI's default recommendation (Pinia, more commonly recommended for new Vue 3 apps today). The
human's prompts also explicitly flagged a handful of genuinely open decisions (e.g., exact
currency-list scope, photo storage approach, refresh-token transport) to be resolved before
building each piece — those were resolved by choosing between AI-presented options with
trade-offs, not decided by AI alone.

## Where AI Implemented, and What It Found Along the Way

- **Turning the locking specification into a correct implementation.** The requirement was
  "lock both wallets in ascending order to prevent deadlocks." Arriving at the concrete
  implementation that actually delivers this guarantee took a back-and-forth discussion between
  the human and AI, not a unilateral AI discovery: a single
  `SELECT ... WHERE id IN (a,b) ORDER BY id FOR UPDATE` does **not** guarantee Postgres acquires
  the row locks in that order (locking happens during the scan; the sort can happen after), so the
  discussion converged on two separate, sequential single-row locks, always smaller-ID-first.
  Implementing this initially still had a bug: a concurrency stress test (60+ simultaneous
  bidirectional transfers) found that wallet balances weren't conserving. Root cause: SQLAlchemy's
  identity map was returning a stale cached `Wallet` object even after the correct database-level
  lock had been acquired. Fixed with `.execution_options(populate_existing=True)`, and the fix was
  verified to be real (not coincidental) by temporarily reverting it, confirming the same test
  failed reliably across repeated runs, then restoring it. This regression test
  (`server/tests/test_transfer_concurrency.py`) now runs in CI.
- **Implementing the snapshot-traceability rule**: the null rule itself (see above) was specified
  by the human, not discovered by AI. AI's contribution was an implementation where that behavior
  falls out automatically from how the rate-lookup function is structured, rather than needing
  explicit branching for each case.
- **Full implementation** of auth, wallets, exchange-rate sync, transfers, transaction history, the
  Vue/Vuetify/Vuex frontend, the 58-test pytest suite, Docker images, CI, and the Render deployment
  config — each verified for real (curl against a live server, actual concurrent load) rather than
  assumed correct from reading the code.
- **Catching infrastructure mistakes before reporting success**: a Docker healthcheck reporting
  "unhealthy" was root-caused to an IPv6/`localhost` resolution quirk inside Alpine Linux rather
  than accepted as-is; a Docker Compose project-name collision that briefly recreated the dev
  Postgres container was caught from anomalous log output, confirmed to have caused no data loss,
  and fixed at the root cause.

## Where AI Proposed and the Human Decided or Redirected

For the pieces without a pre-written specification — deployment platform and a handful of
implementation-level choices — AI proposed options with trade-offs, and the human made the call:

- **Test database isolation**: a stricter requirement (a fully separate, dedicated Postgres
  container for tests) than AI's initial proposal (reusing the dev container with a second
  database).
- **Deployment platform**: Render was chosen after AI researched and presented current free-tier
  trade-offs across platforms.
- **Transfer recipient identification**: AI's initial implementation identified recipients by raw
  user ID (a `user_uuid`); the human proposed switching to email-based lookup instead, for
  real-world usability, and AI named the trade-off (minor user-enumeration exposure, standard for
  this class of feature) before implementing the human's proposed change.

## Summary

The hardest correctness properties in this system — deadlock-safe locking and conversion
traceability, including the exact snapshot-null rule — were specified before AI implementation
began, as was the frontend stack. AI's contribution was turning those specifications into working,
tested code through direct discussion with the human (most notably arriving at the correct
Postgres locking mechanics together, then finding and fixing a real concurrency bug in that
implementation); and independently proposing, implementing, and verifying everything not covered
by a prior specification (deployment and CI), with the human deciding between options — and
overriding AI's proposals outright, as with recipient identification — at every fork that
mattered.

---

*This document was generated by an AI chat instance (Claude) based on a conversation with the
human developer reconstructing the build process, and was reviewed and corrected by the human for
accuracy.*
