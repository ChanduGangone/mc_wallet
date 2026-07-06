import struct
import zlib

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, signup_and_login


def _make_png_bytes() -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\x00\x00")
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


# --- signup ---


def test_signup_success(client: TestClient) -> None:
    resp = client.post(
        "/auth/signup",
        json={"email": "alice@example.com", "password": "password123", "name": "Alice"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert body["name"] == "Alice"
    assert body["default_currency"] == "USD"


def test_signup_duplicate_email(client: TestClient) -> None:
    payload = {"email": "dup@example.com", "password": "password123"}
    assert client.post("/auth/signup", json=payload).status_code == 201
    resp = client.post("/auth/signup", json=payload)
    assert resp.status_code == 409


def test_signup_short_password(client: TestClient) -> None:
    resp = client.post("/auth/signup", json={"email": "short@example.com", "password": "abc"})
    assert resp.status_code == 422


def test_signup_invalid_currency(client: TestClient) -> None:
    resp = client.post(
        "/auth/signup",
        json={"email": "cur@example.com", "password": "password123", "default_currency": "ZZZ"},
    )
    assert resp.status_code == 422


def test_signup_creates_default_wallet(client: TestClient) -> None:
    tokens = signup_and_login(client, "walletcheck@example.com", default_currency="EUR")
    resp = client.get("/wallets", headers=auth_headers(tokens["access_token"]))
    wallets = resp.json()
    assert len(wallets) == 1
    assert wallets[0]["currency"] == "EUR"
    assert wallets[0]["balance"] == "0.0000"


# --- login ---


def test_login_success(client: TestClient) -> None:
    client.post("/auth/signup", json={"email": "login@example.com", "password": "password123"})
    resp = client.post("/auth/login", json={"email": "login@example.com", "password": "password123"})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body and "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient) -> None:
    client.post("/auth/signup", json={"email": "wrongpw@example.com", "password": "password123"})
    resp = client.post("/auth/login", json={"email": "wrongpw@example.com", "password": "nope1234"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


def test_login_unknown_email_same_error_as_wrong_password(client: TestClient) -> None:
    resp = client.post("/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


# --- refresh / logout ---


def test_refresh_rotates_token(client: TestClient) -> None:
    tokens = signup_and_login(client, "refresh@example.com")
    resp = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # old refresh token is now rejected
    reuse_resp = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuse_resp.status_code == 401


def test_logout_revokes_refresh_token(client: TestClient) -> None:
    tokens = signup_and_login(client, "logout@example.com")
    logout_resp = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout_resp.status_code == 204

    refresh_resp = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_resp.status_code == 401


def test_logout_unknown_token_is_idempotent(client: TestClient) -> None:
    resp = client.post("/auth/logout", json={"refresh_token": "does-not-exist"})
    assert resp.status_code == 204


# --- profile ---


def test_get_me(client: TestClient) -> None:
    tokens = signup_and_login(client, "me@example.com", name="Me")
    resp = client.get("/users/me", headers=auth_headers(tokens["access_token"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@example.com"
    assert body["name"] == "Me"


def test_get_me_requires_auth(client: TestClient) -> None:
    resp = client.get("/users/me")
    assert resp.status_code == 401


def test_patch_me_name_and_currency(client: TestClient) -> None:
    tokens = signup_and_login(client, "patch@example.com")
    resp = client.patch(
        "/users/me",
        headers=auth_headers(tokens["access_token"]),
        data={"name": "New Name", "default_currency": "EUR"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "New Name"
    assert body["default_currency"] == "EUR"


def test_patch_me_invalid_currency(client: TestClient) -> None:
    tokens = signup_and_login(client, "patchbadcur@example.com")
    resp = client.patch(
        "/users/me",
        headers=auth_headers(tokens["access_token"]),
        data={"default_currency": "ZZZ"},
    )
    assert resp.status_code == 422


def test_patch_me_photo_upload(client: TestClient) -> None:
    tokens = signup_and_login(client, "photo@example.com")
    resp = client.patch(
        "/users/me",
        headers=auth_headers(tokens["access_token"]),
        files={"photo": ("test.png", _make_png_bytes(), "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json()["photo_url"].startswith("/uploads/")


def test_patch_me_photo_rejects_non_image(client: TestClient) -> None:
    tokens = signup_and_login(client, "badphoto@example.com")
    resp = client.patch(
        "/users/me",
        headers=auth_headers(tokens["access_token"]),
        files={"photo": ("fake.jpg", b"not an image", "image/jpeg")},
    )
    assert resp.status_code == 422


def test_patch_me_photo_and_photo_url_conflict(client: TestClient) -> None:
    tokens = signup_and_login(client, "conflict@example.com")
    resp = client.patch(
        "/users/me",
        headers=auth_headers(tokens["access_token"]),
        data={"photo_url": "http://example.com/x.png"},
        files={"photo": ("test.png", _make_png_bytes(), "image/png")},
    )
    assert resp.status_code == 422
