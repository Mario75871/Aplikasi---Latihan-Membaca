"""Test rate limiting terintegrasi middleware (integrasi #4, D4)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("DEMO_FALLBACK", "true")
    # Jendela besar + limit kecil agar mudah memicu 429.
    monkeypatch.setenv("RATE_LIMIT_LOGIN_IP", "2")
    monkeypatch.setenv("RATE_LIMIT_LOGIN_WINDOW_SEC", "600")

    import repository
    repository._repo = None

    from services.rate_limit import get_limiter
    get_limiter().reset()

    import main
    with TestClient(main.app) as c:
        yield c

    get_limiter().reset()


def test_login_rate_limited_returns_429(client):
    body = {"username": "guru@demo.com", "password": "salah"}
    r1 = client.post("/auth/login", json=body)
    r2 = client.post("/auth/login", json=body)
    assert r1.status_code != 429
    assert r2.status_code != 429
    r3 = client.post("/auth/login", json=body)
    assert r3.status_code == 429
    assert "Retry-After" in r3.headers
    assert int(r3.headers["Retry-After"]) >= 1


def test_health_not_rate_limited(client):
    # /health tidak termasuk jalur yang dibatasi.
    for _ in range(5):
        assert client.get("/health").status_code == 200
