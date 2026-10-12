"""Authentication and authorization tests."""

from tests.conftest import auth_header, register


def test_register_and_me(client):
    data = register(client, "alice")
    assert data["user"]["username"] == "alice"
    assert data["access_token"]
    resp = client.get("/api/v1/users/me", headers=auth_header(data["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"


def test_register_duplicate_username(client):
    register(client, "alice")
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice",
            "email": "other@example.com",
            "password": "supersecret1",
            "full_name": "Alice Two",
            "role": "student",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "already_exists"


def test_register_validates_password_length(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": "bob",
            "email": "bob@example.com",
            "password": "short",
            "full_name": "Bob",
            "role": "student",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_login_wrong_password(client):
    register(client, "alice")
    resp = client.post(
        "/api/v1/auth/login", json={"username": "alice", "password": "wrongpassword"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_credentials"


def test_protected_route_requires_token(client):
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401


def test_logout_revokes_token(client):
    data = register(client, "alice")
    headers = auth_header(data["access_token"])
    assert client.get("/api/v1/users/me", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/users/me", headers=headers).status_code == 401


def test_reviewer_role_required_for_verification(client):
    student = register(client, "sam", role="student")
    college = client.post(
        "/api/v1/colleges",
        json={"name": "X College", "short_name": "XC", "city": "Delhi"},
        headers=auth_header(student["access_token"]),
    )
    assert college.status_code == 403  # students cannot create colleges

    organizer = register(client, "olivia", role="organizer")
    college = client.post(
        "/api/v1/colleges",
        json={"name": "X College", "short_name": "XC", "city": "Delhi"},
        headers=auth_header(organizer["access_token"]),
    )
    assert college.status_code == 201
