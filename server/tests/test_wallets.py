import uuid
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, signup_and_login


def _idem() -> str:
    return str(uuid.uuid4())


def test_get_wallets_lists_own_wallets(client: TestClient) -> None:
    tokens = signup_and_login(client, "gw1@example.com", default_currency="USD")
    resp = client.get("/wallets", headers=auth_headers(tokens["access_token"]))
    assert resp.status_code == 200
    wallets = resp.json()
    assert len(wallets) == 1
    assert wallets[0]["currency"] == "USD"


def test_get_wallets_requires_auth(client: TestClient) -> None:
    resp = client.get("/wallets")
    assert resp.status_code == 401


# --- credit ---


def test_credit_same_currency(client: TestClient) -> None:
    tokens = signup_and_login(client, "credit1@example.com", default_currency="USD")
    wallet_id = client.get("/wallets", headers=auth_headers(tokens["access_token"])).json()[0]["wallet_id"]

    resp = client.post(
        f"/wallets/{wallet_id}/credit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 100, "currency": "USD"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["new_balance"] == "100.0000"
    assert body["converted_amount"] == "100.0000"
    assert body["to_rate_snapshot_id"] is None


def test_credit_cross_currency_math(client: TestClient) -> None:
    tokens = signup_and_login(client, "credit2@example.com", default_currency="EUR")
    wallet_id = client.get("/wallets", headers=auth_headers(tokens["access_token"])).json()[0]["wallet_id"]

    # fake rates: EUR=0.85, INR=83.0 (USD-relative) -> cross_rate = 0.85/83.0
    resp = client.post(
        f"/wallets/{wallet_id}/credit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 1000, "currency": "INR"},
    )
    assert resp.status_code == 200
    body = resp.json()
    expected = (Decimal("1000") * Decimal("0.85") / Decimal("83.0")).quantize(Decimal("0.0001"))
    assert Decimal(body["converted_amount"]) == expected
    assert body["to_rate_snapshot_id"] is not None


def test_credit_invalid_currency(client: TestClient) -> None:
    tokens = signup_and_login(client, "credit3@example.com")
    wallet_id = client.get("/wallets", headers=auth_headers(tokens["access_token"])).json()[0]["wallet_id"]
    resp = client.post(
        f"/wallets/{wallet_id}/credit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 10, "currency": "ZZZ"},
    )
    assert resp.status_code == 422


def test_credit_non_positive_amount(client: TestClient) -> None:
    tokens = signup_and_login(client, "credit4@example.com")
    wallet_id = client.get("/wallets", headers=auth_headers(tokens["access_token"])).json()[0]["wallet_id"]
    resp = client.post(
        f"/wallets/{wallet_id}/credit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": -5, "currency": "USD"},
    )
    assert resp.status_code == 422


def test_credit_missing_idempotency_key(client: TestClient) -> None:
    tokens = signup_and_login(client, "credit5@example.com")
    wallet_id = client.get("/wallets", headers=auth_headers(tokens["access_token"])).json()[0]["wallet_id"]
    resp = client.post(
        f"/wallets/{wallet_id}/credit",
        headers=auth_headers(tokens["access_token"]),
        json={"amount": 10, "currency": "USD"},
    )
    assert resp.status_code == 422


def test_credit_not_owner(client: TestClient) -> None:
    owner = signup_and_login(client, "credit6owner@example.com")
    attacker = signup_and_login(client, "credit6attacker@example.com")
    wallet_id = client.get("/wallets", headers=auth_headers(owner["access_token"])).json()[0]["wallet_id"]
    resp = client.post(
        f"/wallets/{wallet_id}/credit",
        headers={**auth_headers(attacker["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 10, "currency": "USD"},
    )
    assert resp.status_code == 403


def test_credit_wallet_not_found(client: TestClient) -> None:
    tokens = signup_and_login(client, "credit7@example.com")
    resp = client.post(
        f"/wallets/{uuid.uuid4()}/credit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 10, "currency": "USD"},
    )
    assert resp.status_code == 404


def test_credit_idempotent_replay(client: TestClient) -> None:
    tokens = signup_and_login(client, "credit8@example.com")
    wallet_id = client.get("/wallets", headers=auth_headers(tokens["access_token"])).json()[0]["wallet_id"]
    key = _idem()
    body_json = {"amount": 50, "currency": "USD"}

    first = client.post(
        f"/wallets/{wallet_id}/credit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": key},
        json=body_json,
    )
    second = client.post(
        f"/wallets/{wallet_id}/credit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": key},
        json=body_json,
    )
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["transaction_id"] == second.json()["transaction_id"]

    balance_resp = client.get("/wallets", headers=auth_headers(tokens["access_token"]))
    assert balance_resp.json()[0]["balance"] == "50.0000"


# --- debit ---


def test_debit_happy_path(client: TestClient) -> None:
    tokens = signup_and_login(client, "debit1@example.com")
    wallet_id = client.get("/wallets", headers=auth_headers(tokens["access_token"])).json()[0]["wallet_id"]
    client.post(
        f"/wallets/{wallet_id}/credit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 100, "currency": "USD"},
    )
    resp = client.post(
        f"/wallets/{wallet_id}/debit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 40},
    )
    assert resp.status_code == 200
    assert resp.json()["new_balance"] == "60.0000"


def test_debit_insufficient_balance_no_write(client: TestClient) -> None:
    tokens = signup_and_login(client, "debit2@example.com")
    wallet_id = client.get("/wallets", headers=auth_headers(tokens["access_token"])).json()[0]["wallet_id"]

    resp = client.post(
        f"/wallets/{wallet_id}/debit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 999},
    )
    assert resp.status_code == 422

    balance_resp = client.get("/wallets", headers=auth_headers(tokens["access_token"]))
    assert balance_resp.json()[0]["balance"] == "0.0000"


def test_debit_idempotent_replay(client: TestClient) -> None:
    tokens = signup_and_login(client, "debit3@example.com")
    wallet_id = client.get("/wallets", headers=auth_headers(tokens["access_token"])).json()[0]["wallet_id"]
    client.post(
        f"/wallets/{wallet_id}/credit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 100, "currency": "USD"},
    )

    key = _idem()
    body_json = {"amount": 30}
    first = client.post(
        f"/wallets/{wallet_id}/debit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": key},
        json=body_json,
    )
    second = client.post(
        f"/wallets/{wallet_id}/debit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": key},
        json=body_json,
    )
    assert first.json()["transaction_id"] == second.json()["transaction_id"]

    balance_resp = client.get("/wallets", headers=auth_headers(tokens["access_token"]))
    assert balance_resp.json()[0]["balance"] == "70.0000"


def test_debit_not_owner(client: TestClient) -> None:
    owner = signup_and_login(client, "debit4owner@example.com")
    attacker = signup_and_login(client, "debit4attacker@example.com")
    wallet_id = client.get("/wallets", headers=auth_headers(owner["access_token"])).json()[0]["wallet_id"]
    resp = client.post(
        f"/wallets/{wallet_id}/debit",
        headers={**auth_headers(attacker["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 1},
    )
    assert resp.status_code == 403
