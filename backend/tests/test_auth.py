"""Authentication and authorization tests.

Includes the security regression tests for the registration role-escalation
vulnerability: public registration must NEVER grant reviewer/admin privileges.
"""

from tests.conftest import auth_header, make_admin, make_college, register


def test_register_and_me(client):
    data = register(client, "alice")
    assert data["user"]["username"] == "alice"
    assert data["user"]["role"] == "student"
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
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# SECURITY: registration role-escalation regression tests
# ---------------------------------------------------------------------------

def test_register_with_reviewer_role_is_rejected(client):
    """Sending "role": "reviewer" at registration must fail validation."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": "mallory",
            "email": "mallory@example.com",
            "password": "supersecret1",
            "full_name": "Mallory",
            "role": "reviewer",
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "validation_error"
    # And no account exists afterwards
    login = client.post(
        "/api/v1/auth/login", json={"username": "mallory", "password": "supersecret1"}
    )
    assert login.status_code == 401


def test_register_with_admin_role_is_rejected(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": "mallory",
            "email": "mallory@example.com",
            "password": "supersecret1",
            "full_name": "Mallory",
            "role": "admin",
        },
    )
    assert resp.status_code == 422


def test_registered_user_cannot_use_reviewer_privileges(client):
    """Even after creating a community (organizer onboarding), verification
    promotion stays reviewer-only."""
    user = register(client, "alice")
    college = make_college(client, user["access_token"])
    resp = client.post(
        "/api/v1/communities",
        json={"name": "My Club", "college_id": college["id"]},
        headers=auth_header(user["access_token"]),
    )
    assert resp.status_code == 201
    community = resp.json()
    # Creator became a platform organizer through the controlled onboarding…
    me = client.get("/api/v1/users/me", headers=auth_header(user["access_token"])).json()
    assert me["role"] == "organizer"
    # …but still cannot promote a community to `verified`.
    attempt = client.patch(
        f"/api/v1/communities/{community['id']}",
        json={"verification_status": "verified"},
        headers=auth_header(user["access_token"]),
    )
    assert attempt.status_code == 403


def test_only_admin_can_assign_roles(client, db_session):
    admin = make_admin(client, db_session, "root")
    user = register(client, "alice")

    # A normal user cannot assign roles
    resp = client.post(
        f"/api/v1/admin/users/{user['user']['id']}/role",
        json={"role": "reviewer"},
        headers=auth_header(user["access_token"]),
    )
    assert resp.status_code == 403

    # Admin can — and this is the ONLY path to reviewer
    resp = client.post(
        f"/api/v1/admin/users/{user['user']['id']}/role",
        json={"role": "reviewer"},
        headers=auth_header(admin["access_token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "reviewer"


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


def test_college_creation_open_to_authenticated_users(client):
    student = register(client, "sam")
    resp = client.post(
        "/api/v1/colleges",
        json={"name": "X College", "short_name": "XC", "city": "Delhi"},
        headers=auth_header(student["access_token"]),
    )
    assert resp.status_code == 201
