# Tests

The actual test suite lives at [`server/tests/`](../server/tests/), not in this folder — moving it
here would break `server/pytest.ini`'s `testpaths`, the `tests.conftest` import path used
throughout the suite, and the CI workflow, all of which assume the suite runs from `server/`.
This folder exists only so the repository has a `tests/` entry at the root, per the assignment's
submission checklist.

## Running the tests

```bash
cd server
docker compose -f tests/docker-compose.yml up -d   # dedicated test Postgres, port 5436, separate
                                                     # from the dev DB on port 5435
pytest -v
```

58 tests covering auth, wallets, transfers (including a concurrency regression test), transaction
history, and the exchange-rate debug endpoint — against a **real Postgres**, with only the
third-party exchange-rate provider mocked. See [`../ARCHITECTURE.md`](../ARCHITECTURE.md#7-testing-strategy)
for why.

CI (`.github/workflows/ci.yml`) runs the same suite on every push/PR against a fresh Postgres
service container, plus a frontend build check.
