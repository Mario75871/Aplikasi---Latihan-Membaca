"""Test Auth (D7)."""
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """TestClient tanpa AUTH_DISABLED (test auth middleware)."""
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    monkeypatch.setenv("DEMO_FALLBACK", "true")
    monkeypatch.setenv("DEMO_USERNAME", "guru@demo.com")
    monkeypatch.setenv("DEMO_PASSWORD", "demo123")

    import repository
    repository._repo = None

    import api.auth
    api.auth.reset_sessions()

    import main
    with TestClient(main.app) as c:
        yield c


def test_login_success(client):
    resp = client.post("/auth/login", json={"username": "guru@demo.com", "password": "demo123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["username"] == "guru@demo.com"


def test_login_wrong_password_401(client):
    resp = client.post("/auth/login", json={"username": "guru@demo.com", "password": "wrong"})
    assert resp.status_code == 401


def test_login_empty_422(client):
    resp = client.post("/auth/login", json={"username": "", "password": ""})
    assert resp.status_code == 422


def test_protected_endpoint_without_token_401(client):
    """Endpoint selain /health dan /auth/* butuh token."""
    resp = client.get("/students")
    assert resp.status_code == 401


def test_protected_endpoint_with_token_200(client):
    """Dengan token valid, endpoint bisa diakses."""
    login = client.post("/auth/login", json={"username": "guru@demo.com", "password": "demo123"})
    token = login.json()["token"]
    resp = client.get("/students", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_health_is_public(client):
    """Health tidak butuh token."""
    resp = client.get("/health")
    assert resp.status_code == 200


def test_logout(client):
    login = client.post("/auth/login", json={"username": "guru@demo.com", "password": "demo123"})
    token = login.json()["token"]
    resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    # Setelah logout, token tidak valid
    resp2 = client.get("/students", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 401
