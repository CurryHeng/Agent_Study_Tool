"""认证接口测试（通过 FastAPI TestClient，覆盖 register/login/refresh/logout/me）。"""
import uuid


def _creds():
    s = uuid.uuid4().hex[:10]
    return {"username": f"u{s}", "email": f"{s}@example.com", "password": "password123"}


def _register(client):
    creds = _creds()
    resp = client.post("/api/auth/register", json=creds)
    return creds, resp


# ── 健康检查 ──────────────────────────────────────────────
def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


# ── 注册 ─────────────────────────────────────────────────
def test_register_success(client):
    creds, resp = _register(client)
    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["username"] == creds["username"]
    assert data["user"]["email"] == creds["email"]
    assert data["access_token"]
    assert data["refresh_token"]


def test_register_duplicate_email(client):
    creds, _ = _register(client)
    resp = client.post("/api/auth/register", json=creds)
    assert resp.status_code == 409


def test_register_duplicate_username(client):
    creds, _ = _register(client)
    other = {**creds, "email": "another@example.com"}
    resp = client.post("/api/auth/register", json=other)
    assert resp.status_code == 409


def test_register_missing_fields(client):
    resp = client.post("/api/auth/register", json={"username": "x"})
    assert resp.status_code == 422


def test_register_short_password(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": "u1", "email": "u1@example.com", "password": "1234567"},
    )
    assert resp.status_code == 422


def test_register_bad_email(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": "u2", "email": "not-an-email", "password": "password123"},
    )
    assert resp.status_code == 422


# ── 登录 ─────────────────────────────────────────────────
def test_login_success(client):
    creds, _ = _register(client)
    resp = client.post(
        "/api/auth/login",
        json={"email": creds["email"], "password": creds["password"]},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]
    assert resp.json()["user"]["username"] == creds["username"]


def test_login_wrong_password(client):
    creds, _ = _register(client)
    resp = client.post(
        "/api/auth/login",
        json={"email": creds["email"], "password": "wrongpass123"},
    )
    assert resp.status_code == 401


def test_login_nonexistent_email(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "noone@example.com", "password": "whatever123"},
    )
    assert resp.status_code == 401


# ── me ───────────────────────────────────────────────────
def test_me_without_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_malformed_token(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


def test_me_with_valid_token(client):
    _, resp = _register(client)
    token = resp.json()["access_token"]
    resp2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert resp2.json()["email"]


# ── refresh（含轮换）──────────────────────────────────────
def test_refresh_success(client):
    _, resp = _register(client)
    refresh_token = resp.json()["refresh_token"]
    resp2 = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp2.status_code == 200
    assert resp2.json()["access_token"]
    assert resp2.json()["refresh_token"]


def test_refresh_rotates_and_invalidates_old(client):
    _, resp = _register(client)
    refresh1 = resp.json()["refresh_token"]
    resp2 = client.post("/api/auth/refresh", json={"refresh_token": refresh1})
    assert resp2.status_code == 200

    # 旧 refresh token 已被轮换作废
    resp3 = client.post("/api/auth/refresh", json={"refresh_token": refresh1})
    assert resp3.status_code == 401


def test_refresh_invalid_token(client):
    resp = client.post("/api/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401


# ── logout ───────────────────────────────────────────────
def test_logout(client):
    _, resp = _register(client)
    access = resp.json()["access_token"]
    refresh = resp.json()["refresh_token"]

    resp2 = client.post(
        "/api/auth/logout",
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp2.status_code == 200

    # 登出后 refresh token 已失效
    resp3 = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp3.status_code == 401
