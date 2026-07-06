import uuid
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, signup_and_login


def _idem() -> str:
    return str(uuid.uuid4())


def _wallet_id(client: TestClient, access_token: str, currency: str = "USD") -> str:
    wallets = client.get("/wallets", headers=auth_headers(access_token)).json()
    for w in wallets:
        if w["currency"] == currency:
            return w["wallet_id"]
    raise AssertionError(f"no {currency} wallet found")


def _credit(client: TestClient, access_token: str, wallet_id: str, amount: float, currency: str) -> None:
    resp = client.post(
        f"/wallets/{wallet_id}/credit",
        headers={**auth_headers(access_token), "Idempotency-Key": _idem()},
        json={"amount": amount, "currency": currency},
    )
    assert resp.status_code == 200, resp.text


def test_transfer_same_currency(client: TestClient) -> None:
    sender = signup_and_login(client, "xfer1sender@example.com", default_currency="USD")
    receiver = signup_and_login(client, "xfer1receiver@example.com", default_currency="USD")
    from_wallet = _wallet_id(client, sender["access_token"], "USD")
    _credit(client, sender["access_token"], from_wallet, 100, "USD")

    resp = client.post(
        "/transfers",
        headers={**auth_headers(sender["access_token"]), "Idempotency-Key": _idem()},
        json={"from_wallet_id": from_wallet, "to_user_id": receiver["user_id"], "amount": 30},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["converted_amount"] == "30.0000"
    assert body["from_rate_snapshot_id"] is None
    assert body["to_rate_snapshot_id"] is None

    sender_bal = client.get("/wallets", headers=auth_headers(sender["access_token"])).json()[0]["balance"]
    receiver_bal = client.get("/wallets", headers=auth_headers(receiver["access_token"])).json()[0]["balance"]
    assert sender_bal == "70.0000"
    assert receiver_bal == "30.0000"


def test_transfer_cross_currency_math_and_snapshot_refs(client: TestClient) -> None:
    sender = signup_and_login(client, "xfer2sender@example.com", default_currency="EUR")
    receiver = signup_and_login(client, "xfer2receiver@example.com", default_currency="INR")
    from_wallet = _wallet_id(client, sender["access_token"], "EUR")
    _credit(client, sender["access_token"], from_wallet, 1000, "EUR")

    resp = client.post(
        "/transfers",
        headers={**auth_headers(sender["access_token"]), "Idempotency-Key": _idem()},
        json={"from_wallet_id": from_wallet, "to_user_id": receiver["user_id"], "amount": 100},
    )
    assert resp.status_code == 201
    body = resp.json()
    # fake rates: EUR=0.85, INR=83.0 -> cross_rate = INR_rate/EUR_rate
    expected = (Decimal("100") * Decimal("83.0") / Decimal("0.85")).quantize(Decimal("0.0001"))
    assert Decimal(body["converted_amount"]) == expected
    assert body["from_rate_snapshot_id"] is not None
    assert body["to_rate_snapshot_id"] is not None


def test_transfer_one_side_base_currency(client: TestClient) -> None:
    sender = signup_and_login(client, "xfer3sender@example.com", default_currency="USD")
    receiver = signup_and_login(client, "xfer3receiver@example.com", default_currency="EUR")
    from_wallet = _wallet_id(client, sender["access_token"], "USD")
    _credit(client, sender["access_token"], from_wallet, 100, "USD")

    resp = client.post(
        "/transfers",
        headers={**auth_headers(sender["access_token"]), "Idempotency-Key": _idem()},
        json={"from_wallet_id": from_wallet, "to_user_id": receiver["user_id"], "amount": 10},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["from_rate_snapshot_id"] is None  # USD is base
    assert body["to_rate_snapshot_id"] is not None


def test_transfer_auto_creates_receiver_wallet(client: TestClient) -> None:
    sender = signup_and_login(client, "xfer4sender@example.com", default_currency="USD")
    receiver = signup_and_login(client, "xfer4receiver@example.com", default_currency="USD")
    from_wallet = _wallet_id(client, sender["access_token"], "USD")
    _credit(client, sender["access_token"], from_wallet, 100, "USD")

    resp = client.post(
        "/transfers",
        headers={**auth_headers(sender["access_token"]), "Idempotency-Key": _idem()},
        json={"from_wallet_id": from_wallet, "to_user_id": receiver["user_id"], "to_currency": "GBP", "amount": 10},
    )
    assert resp.status_code == 201
    receiver_wallets = client.get("/wallets", headers=auth_headers(receiver["access_token"])).json()
    currencies = {w["currency"] for w in receiver_wallets}
    assert "GBP" in currencies


def test_transfer_to_own_different_currency_wallet_allowed(client: TestClient) -> None:
    user = signup_and_login(client, "xfer5@example.com", default_currency="USD")
    from_wallet = _wallet_id(client, user["access_token"], "USD")
    _credit(client, user["access_token"], from_wallet, 100, "USD")

    resp = client.post(
        "/transfers",
        headers={**auth_headers(user["access_token"]), "Idempotency-Key": _idem()},
        json={"from_wallet_id": from_wallet, "to_user_id": user["user_id"], "to_currency": "EUR", "amount": 10},
    )
    assert resp.status_code == 201


def test_transfer_self_same_wallet_rejected(client: TestClient) -> None:
    user = signup_and_login(client, "xfer6@example.com", default_currency="USD")
    from_wallet = _wallet_id(client, user["access_token"], "USD")
    _credit(client, user["access_token"], from_wallet, 100, "USD")

    resp = client.post(
        "/transfers",
        headers={**auth_headers(user["access_token"]), "Idempotency-Key": _idem()},
        json={"from_wallet_id": from_wallet, "to_user_id": user["user_id"], "to_currency": "USD", "amount": 10},
    )
    assert resp.status_code == 422


def test_transfer_insufficient_balance_no_write(client: TestClient) -> None:
    sender = signup_and_login(client, "xfer7sender@example.com", default_currency="USD")
    receiver = signup_and_login(client, "xfer7receiver@example.com", default_currency="USD")
    from_wallet = _wallet_id(client, sender["access_token"], "USD")

    resp = client.post(
        "/transfers",
        headers={**auth_headers(sender["access_token"]), "Idempotency-Key": _idem()},
        json={"from_wallet_id": from_wallet, "to_user_id": receiver["user_id"], "amount": 999999},
    )
    assert resp.status_code == 422

    sender_bal = client.get("/wallets", headers=auth_headers(sender["access_token"])).json()[0]["balance"]
    assert sender_bal == "0.0000"


def test_transfer_from_wallet_not_owned(client: TestClient) -> None:
    owner = signup_and_login(client, "xfer8owner@example.com", default_currency="USD")
    attacker = signup_and_login(client, "xfer8attacker@example.com", default_currency="USD")
    receiver = signup_and_login(client, "xfer8receiver@example.com", default_currency="USD")
    owner_wallet = _wallet_id(client, owner["access_token"], "USD")

    resp = client.post(
        "/transfers",
        headers={**auth_headers(attacker["access_token"]), "Idempotency-Key": _idem()},
        json={"from_wallet_id": owner_wallet, "to_user_id": receiver["user_id"], "amount": 1},
    )
    assert resp.status_code == 403


def test_transfer_from_wallet_not_found(client: TestClient) -> None:
    sender = signup_and_login(client, "xfer9sender@example.com", default_currency="USD")
    receiver = signup_and_login(client, "xfer9receiver@example.com", default_currency="USD")

    resp = client.post(
        "/transfers",
        headers={**auth_headers(sender["access_token"]), "Idempotency-Key": _idem()},
        json={"from_wallet_id": str(uuid.uuid4()), "to_user_id": receiver["user_id"], "amount": 1},
    )
    assert resp.status_code == 404


def test_transfer_to_user_not_found(client: TestClient) -> None:
    sender = signup_and_login(client, "xfer10sender@example.com", default_currency="USD")
    from_wallet = _wallet_id(client, sender["access_token"], "USD")

    resp = client.post(
        "/transfers",
        headers={**auth_headers(sender["access_token"]), "Idempotency-Key": _idem()},
        json={"from_wallet_id": from_wallet, "to_user_id": str(uuid.uuid4()), "amount": 1},
    )
    assert resp.status_code == 404


def test_transfer_idempotent_replay(client: TestClient) -> None:
    sender = signup_and_login(client, "xfer11sender@example.com", default_currency="USD")
    receiver = signup_and_login(client, "xfer11receiver@example.com", default_currency="USD")
    from_wallet = _wallet_id(client, sender["access_token"], "USD")
    _credit(client, sender["access_token"], from_wallet, 100, "USD")

    key = _idem()
    body_json = {"from_wallet_id": from_wallet, "to_user_id": receiver["user_id"], "amount": 20}

    first = client.post("/transfers", headers={**auth_headers(sender["access_token"]), "Idempotency-Key": key}, json=body_json)
    second = client.post("/transfers", headers={**auth_headers(sender["access_token"]), "Idempotency-Key": key}, json=body_json)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["transaction_id"] == second.json()["transaction_id"]

    sender_bal = client.get("/wallets", headers=auth_headers(sender["access_token"])).json()[0]["balance"]
    assert sender_bal == "80.0000"


def test_transfer_missing_idempotency_key(client: TestClient) -> None:
    sender = signup_and_login(client, "xfer12sender@example.com", default_currency="USD")
    receiver = signup_and_login(client, "xfer12receiver@example.com", default_currency="USD")
    from_wallet = _wallet_id(client, sender["access_token"], "USD")

    resp = client.post(
        "/transfers",
        headers=auth_headers(sender["access_token"]),
        json={"from_wallet_id": from_wallet, "to_user_id": receiver["user_id"], "amount": 1},
    )
    assert resp.status_code == 422
