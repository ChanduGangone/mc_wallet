from fastapi.testclient import TestClient

from tests.conftest import FAKE_FRANKFURTER_RESPONSE


def test_latest_rates_shape_and_values(client: TestClient) -> None:
    resp = client.get("/exchange-rates/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["base_currency"] == "USD"
    assert set(body["rates"].keys()) == set(FAKE_FRANKFURTER_RESPONSE["rates"].keys())
    assert float(body["rates"]["EUR"]) == FAKE_FRANKFURTER_RESPONSE["rates"]["EUR"]


def test_latest_rates_no_auth_required(client: TestClient) -> None:
    resp = client.get("/exchange-rates/latest")
    assert resp.status_code == 200
