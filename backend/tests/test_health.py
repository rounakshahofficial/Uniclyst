"""Health endpoint tests — must not leak sensitive details."""


def test_health_ok(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert "password" not in resp.text.lower()
    assert "secret" not in resp.text.lower()
    assert "key" not in resp.text.lower()


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["docs"] == "/docs"
