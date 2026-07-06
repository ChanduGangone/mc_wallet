import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, signup_and_login


def _wallet_id(client: TestClient, access_token: str, currency: str) -> str:
    wallets = client.get("/wallets", headers=auth_headers(access_token)).json()
    for w in wallets:
        if w["currency"] == currency:
            return w["wallet_id"]
    raise AssertionError(f"no {currency} wallet found")


def _transfer(client: TestClient, access_token: str, from_wallet: str, to_user_id: str, amount: int) -> tuple[int, str]:
    resp = client.post(
        "/transfers",
        headers={**auth_headers(access_token), "Idempotency-Key": str(uuid.uuid4())},
        json={"from_wallet_id": from_wallet, "to_user_id": to_user_id, "to_currency": "EUR", "amount": amount},
    )
    return resp.status_code, resp.text


def test_concurrent_bidirectional_transfers_conserve_balance_and_never_deadlock(client: TestClient) -> None:
    """Regression test for the Phase 5 bug: SQLAlchemy's identity map returned a stale
    cached Wallet object even after a SELECT...FOR UPDATE lock was acquired, because the
    object had already been loaded earlier in the same request via an unlocked db.get().
    Fixed via populate_existing=True in _lock_two_wallets(). Under concurrent bidirectional
    transfers between the same two wallets, that bug silently lost money; this test asserts
    balances are exactly conserved and no deadlock errors occur.
    """
    bob = signup_and_login(client, "concurrent_bob@example.com", default_currency="EUR")
    carol = signup_and_login(client, "concurrent_carol@example.com", default_currency="EUR")

    bob_wallet = _wallet_id(client, bob["access_token"], "EUR")
    carol_wallet = _wallet_id(client, carol["access_token"], "EUR")

    # Seed both wallets with plenty of balance so every single-unit transfer in either
    # direction can legitimately succeed regardless of interleaving order — the point of
    # this test is to catch lost updates / deadlocks, not incidentally-correct 422s from
    # one side starting at zero.
    for wallet, token in [(bob_wallet, bob["access_token"]), (carol_wallet, carol["access_token"])]:
        seed_resp = client.post(
            f"/wallets/{wallet}/credit",
            headers={**auth_headers(token), "Idempotency-Key": str(uuid.uuid4())},
            json={"amount": 1000, "currency": "EUR"},
        )
        assert seed_resp.status_code == 200

    n_each_direction = 25
    tasks = []
    for _ in range(n_each_direction):
        tasks.append((bob["access_token"], bob_wallet, carol["user_id"]))
        tasks.append((carol["access_token"], carol_wallet, bob["user_id"]))

    results = []
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(_transfer, client, token, wallet, to_user, 1) for token, wallet, to_user in tasks]
        for future in as_completed(futures):
            results.append(future.result())

    statuses = [status for status, _ in results]
    failures = [(status, body) for status, body in results if status != 201]
    assert not failures, f"expected all 201, got failures: {failures[:5]}"
    assert len(statuses) == n_each_direction * 2

    bob_balance = client.get("/wallets", headers=auth_headers(bob["access_token"])).json()[0]["balance"]
    carol_balance = client.get("/wallets", headers=auth_headers(carol["access_token"])).json()[0]["balance"]

    # Equal transfers in both directions net to zero change for both parties.
    assert bob_balance == "1000.0000"
    assert carol_balance == "1000.0000"
