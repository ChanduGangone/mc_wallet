import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, signup_and_login


def _idem() -> str:
    return str(uuid.uuid4())


def _wallet_id(client: TestClient, access_token: str, currency: str) -> str:
    wallets = client.get("/wallets", headers=auth_headers(access_token)).json()
    for w in wallets:
        if w["currency"] == currency:
            return w["wallet_id"]
    raise AssertionError(f"no {currency} wallet found")


def test_fresh_user_has_no_transactions(client: TestClient) -> None:
    tokens = signup_and_login(client, "txnfresh@example.com")
    resp = client.get("/transactions", headers=auth_headers(tokens["access_token"]))
    assert resp.status_code == 200
    assert resp.json() == {"total": 0, "limit": 20, "offset": 0, "items": []}


def test_lists_own_credit_and_transfer_history(client: TestClient) -> None:
    sender = signup_and_login(client, "txnsender@example.com", default_currency="USD")
    receiver = signup_and_login(client, "txnreceiver@example.com", default_currency="USD")
    from_wallet = _wallet_id(client, sender["access_token"], "USD")

    client.post(
        f"/wallets/{from_wallet}/credit",
        headers={**auth_headers(sender["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 100, "currency": "USD"},
    )
    client.post(
        "/transfers",
        headers={**auth_headers(sender["access_token"]), "Idempotency-Key": _idem()},
        json={"from_wallet_id": from_wallet, "to_email": "txnreceiver@example.com", "amount": 30},
    )

    sender_resp = client.get("/transactions", headers=auth_headers(sender["access_token"]))
    assert sender_resp.status_code == 200
    sender_body = sender_resp.json()
    assert sender_body["total"] == 2
    types = {i["type"] for i in sender_body["items"]}
    assert types == {"credit", "transfer"}

    receiver_resp = client.get("/transactions", headers=auth_headers(receiver["access_token"]))
    receiver_body = receiver_resp.json()
    assert receiver_body["total"] == 1
    assert receiver_body["items"][0]["type"] == "transfer"


def test_filter_by_type(client: TestClient) -> None:
    tokens = signup_and_login(client, "txntype@example.com", default_currency="USD")
    wallet_id = _wallet_id(client, tokens["access_token"], "USD")
    client.post(
        f"/wallets/{wallet_id}/credit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 100, "currency": "USD"},
    )
    client.post(
        f"/wallets/{wallet_id}/debit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 10},
    )

    resp = client.get("/transactions?type=credit", headers=auth_headers(tokens["access_token"]))
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["type"] == "credit"


def test_filter_by_invalid_type(client: TestClient) -> None:
    tokens = signup_and_login(client, "txnbadtype@example.com")
    resp = client.get("/transactions?type=bogus", headers=auth_headers(tokens["access_token"]))
    assert resp.status_code == 422


def test_filter_by_currency(client: TestClient) -> None:
    tokens = signup_and_login(client, "txncur@example.com", default_currency="EUR")
    wallet_id = _wallet_id(client, tokens["access_token"], "EUR")
    client.post(
        f"/wallets/{wallet_id}/credit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 100, "currency": "INR"},
    )
    client.post(
        f"/wallets/{wallet_id}/credit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 50, "currency": "EUR"},
    )

    resp = client.get("/transactions?currency=INR", headers=auth_headers(tokens["access_token"]))
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["from_currency"] == "INR"


def test_filter_by_invalid_currency(client: TestClient) -> None:
    tokens = signup_and_login(client, "txnbadcur@example.com")
    resp = client.get("/transactions?currency=ZZZ", headers=auth_headers(tokens["access_token"]))
    assert resp.status_code == 422


def test_filter_by_date_range(client: TestClient) -> None:
    tokens = signup_and_login(client, "txndate@example.com", default_currency="USD")
    wallet_id = _wallet_id(client, tokens["access_token"], "USD")
    client.post(
        f"/wallets/{wallet_id}/credit",
        headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": _idem()},
        json={"amount": 100, "currency": "USD"},
    )

    today = date.today().isoformat()
    resp_today = client.get(
        f"/transactions?start_date={today}&end_date={today}", headers=auth_headers(tokens["access_token"])
    )
    assert resp_today.json()["total"] == 1

    past = (date.today() - timedelta(days=10)).isoformat()
    resp_past = client.get(
        f"/transactions?start_date={past}&end_date={past}", headers=auth_headers(tokens["access_token"])
    )
    assert resp_past.json()["total"] == 0


def test_pagination(client: TestClient) -> None:
    tokens = signup_and_login(client, "txnpage@example.com", default_currency="USD")
    wallet_id = _wallet_id(client, tokens["access_token"], "USD")
    for _ in range(7):
        client.post(
            f"/wallets/{wallet_id}/credit",
            headers={**auth_headers(tokens["access_token"]), "Idempotency-Key": _idem()},
            json={"amount": 1, "currency": "USD"},
        )

    page1 = client.get("/transactions?limit=3&offset=0", headers=auth_headers(tokens["access_token"])).json()
    page2 = client.get("/transactions?limit=3&offset=3", headers=auth_headers(tokens["access_token"])).json()

    assert page1["total"] == 7
    assert len(page1["items"]) == 3
    assert len(page2["items"]) == 3
    ids1 = {i["transaction_id"] for i in page1["items"]}
    ids2 = {i["transaction_id"] for i in page2["items"]}
    assert ids1.isdisjoint(ids2)


def test_limit_over_max_rejected(client: TestClient) -> None:
    tokens = signup_and_login(client, "txnlimit@example.com")
    resp = client.get("/transactions?limit=101", headers=auth_headers(tokens["access_token"]))
    assert resp.status_code == 422


def test_transactions_requires_auth(client: TestClient) -> None:
    resp = client.get("/transactions")
    assert resp.status_code == 401
