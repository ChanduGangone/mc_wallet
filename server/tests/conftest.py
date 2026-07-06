import os

os.environ["DATABASE_URL"] = "postgresql://mc_wallet:mc_wallet@localhost:5436/mc_wallet_test"

# Only NOW is it safe to import anything from `app` — settings/engine/SessionLocal are
# constructed at import time from DATABASE_URL, so the env var must be set first.
from collections.abc import Iterator
from unittest.mock import patch

import psycopg2
import pytest
from fastapi.testclient import TestClient

import app.models  # noqa: F401  -- registers all tables on Base.metadata
from app.db.base import Base
from app.db.session import engine
from app.main import app as fastapi_app

TEST_DATABASE_URL = os.environ["DATABASE_URL"]

FAKE_FRANKFURTER_RESPONSE = {
    "amount": 1.0,
    "base": "USD",
    "date": "2026-01-01",
    "rates": {
        "EUR": 0.85, "GBP": 0.79, "INR": 83.0, "JPY": 150.0, "AUD": 1.52,
        "CAD": 1.36, "CHF": 0.88, "CNY": 7.20, "SGD": 1.34, "AED": 3.67,
        "ZAR": 18.50, "NZD": 1.64, "SEK": 10.40, "NOK": 10.60, "DKK": 6.33,
        "HKD": 7.82, "KRW": 1320.0, "MXN": 17.10, "BRL": 5.05,
    },
}


class _FakeFrankfurterResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload


@pytest.fixture(scope="session", autouse=True)
def _check_test_database_reachable() -> None:
    try:
        conn = psycopg2.connect(TEST_DATABASE_URL)
        conn.close()
    except psycopg2.OperationalError as e:
        pytest.exit(
            "Cannot reach the test database. Start it first with:\n"
            "  docker compose -f tests/docker-compose.yml up -d\n"
            f"Original error: {e}"
        )


@pytest.fixture(scope="session", autouse=True)
def _test_schema(_check_test_database_reachable) -> None:
    Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _mock_frankfurter() -> Iterator[None]:
    with patch(
        "app.core.exchange_rates.httpx.get",
        return_value=_FakeFrankfurterResponse(FAKE_FRANKFURTER_RESPONSE),
    ):
        yield


@pytest.fixture(scope="session")
def client(_mock_frankfurter, _test_schema) -> Iterator[TestClient]:
    with TestClient(fastapi_app) as c:
        yield c


@pytest.fixture(autouse=True)
def _truncate_between_tests(client) -> Iterator[None]:
    yield
    with engine.begin() as conn:
        conn.exec_driver_sql("TRUNCATE TABLE users, refresh_tokens, wallets, transactions CASCADE;")


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def signup_and_login(
    client: TestClient,
    email: str,
    password: str = "password123",
    default_currency: str | None = None,
    name: str | None = None,
) -> dict:
    signup_payload = {"email": email, "password": password}
    if default_currency is not None:
        signup_payload["default_currency"] = default_currency
    if name is not None:
        signup_payload["name"] = name

    signup_resp = client.post("/auth/signup", json=signup_payload)
    assert signup_resp.status_code == 201, signup_resp.text
    user_id = signup_resp.json()["user_id"]

    login_resp = client.post("/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200, login_resp.text
    tokens = login_resp.json()

    return {
        "user_id": user_id,
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
    }
