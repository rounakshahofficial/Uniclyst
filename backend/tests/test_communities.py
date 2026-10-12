"""Community API tests: CRUD, search, filters, permissions, saved list."""

from tests.conftest import auth_header, make_college, make_community, register


def _setup(client):
<<<<<<< HEAD
    user = register(client, "olivia")
=======
    user = register(client, "olivia", role="organizer")
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
    college = make_college(client, user["access_token"])
    return user, college


def test_create_community_is_discovered_not_verified(client):
    user, college = _setup(client)
    community = make_community(client, user["access_token"], college["id"])
    assert community["verification_status"] == "discovered"
    assert community["is_demo"] == 0
    assert community["slug"] == "test-robotics-club"
    assert {s["name"] for s in community["skills"]} == {"Arduino", "Computer Vision"}
    assert community["members"][0]["role"] == "organizer"


def test_duplicate_slugs_get_suffix(client):
    user, college = _setup(client)
    first = make_community(client, user["access_token"], college["id"], name="Robotics Club")
    second = make_community(client, user["access_token"], college["id"], name="Robotics Club")
    assert first["slug"] == "robotics-club"
    assert second["slug"] == "robotics-club-2"


def test_search_by_name_and_skill(client):
    user, college = _setup(client)
    make_community(client, user["access_token"], college["id"], name="Robotics Club")
    make_community(client, user["access_token"], college["id"], name="Drama Society",
                   category="Cultural", interests=["theatre"],
                   skills=[{"name": "Photography", "kind": "offers"}])

    resp = client.get("/api/v1/communities/search?q=robotics")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()["items"]]
    assert names == ["Robotics Club"]

    resp = client.get("/api/v1/communities/search?skill=Photography")
    names = [c["name"] for c in resp.json()["items"]]
    assert names == ["Drama Society"]


def test_filters_and_pagination(client):
    user, college = _setup(client)
    for i in range(5):
        make_community(client, user["access_token"], college["id"], name=f"Club {i}")
    page1 = client.get("/api/v1/communities?page=1&page_size=2").json()
    assert page1["total"] == 5
    assert page1["pages"] == 3
    assert len(page1["items"]) == 2

    filtered = client.get(f"/api/v1/communities?college_id={college['id']}&category=Technical").json()
    assert filtered["total"] == 5

    none = client.get("/api/v1/communities?category=Cultural").json()
    assert none["total"] == 0


def test_update_permissions(client):
    owner, college = _setup(client)
    community = make_community(client, owner["access_token"], college["id"])

<<<<<<< HEAD
    outsider = register(client, "eve")
=======
    outsider = register(client, "eve", role="student")
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
    resp = client.patch(
        f"/api/v1/communities/{community['id']}",
        json={"description": "hacked"},
        headers=auth_header(outsider["access_token"]),
    )
    assert resp.status_code == 403

    resp = client.patch(
        f"/api/v1/communities/{community['id']}",
        json={"description": "new description"},
        headers=auth_header(owner["access_token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "new description"


<<<<<<< HEAD
def test_only_reviewer_can_set_verification(client, db_session):
=======
def test_only_reviewer_can_set_verification(client):
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
    owner, college = _setup(client)
    community = make_community(client, owner["access_token"], college["id"])

    resp = client.patch(
        f"/api/v1/communities/{community['id']}",
        json={"verification_status": "verified"},
        headers=auth_header(owner["access_token"]),
    )
    assert resp.status_code == 403

<<<<<<< HEAD
    # Reviewer role is granted ONLY by an admin (see test_auth.py)
    from tests.conftest import make_admin

    admin = make_admin(client, db_session, "root")
    reviewer = register(client, "ravi")
    client.post(
        f"/api/v1/admin/users/{reviewer['user']['id']}/role",
        json={"role": "reviewer"},
        headers=auth_header(admin["access_token"]),
    )
=======
    reviewer = register(client, "ravi", role="reviewer")
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
    resp = client.patch(
        f"/api/v1/communities/{community['id']}",
        json={"verification_status": "verified"},
        headers=auth_header(reviewer["access_token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["verification_status"] == "verified"


def test_delete_permissions(client):
    owner, college = _setup(client)
    community = make_community(client, owner["access_token"], college["id"])

<<<<<<< HEAD
    outsider = register(client, "mallory")
=======
    outsider = register(client, "mallory", role="student")
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
    resp = client.delete(
        f"/api/v1/communities/{community['id']}",
        headers=auth_header(outsider["access_token"]),
    )
    assert resp.status_code == 403

    resp = client.delete(
        f"/api/v1/communities/{community['id']}",
        headers=auth_header(owner["access_token"]),
    )
    assert resp.status_code == 204
    assert client.get(f"/api/v1/communities/{community['id']}").status_code == 404


def test_join_leave_and_saved(client):
    owner, college = _setup(client)
    community = make_community(client, owner["access_token"], college["id"])
<<<<<<< HEAD
    member = register(client, "mia")
=======
    member = register(client, "mia", role="student")
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
    headers = auth_header(member["access_token"])

    assert client.post(f"/api/v1/communities/{community['id']}/join", headers=headers).json()["joined"]
    again = client.post(f"/api/v1/communities/{community['id']}/join", headers=headers).json()
    assert again["already_member"] is True

    client.post(f"/api/v1/users/me/saved/{community['id']}", headers=headers)
    saved = client.get("/api/v1/users/me/saved", headers=headers).json()
    assert [c["id"] for c in saved] == [community["id"]]

    profile = client.get(f"/api/v1/communities/{community['id']}", headers=headers).json()
    assert profile["saved"] is True

    assert client.delete(f"/api/v1/communities/{community['id']}/leave", headers=headers).status_code == 204
    assert client.delete(f"/api/v1/users/me/saved/{community['id']}", headers=headers).status_code == 204
    assert client.get("/api/v1/users/me/saved", headers=headers).json() == []


def test_events_created_by_organizer_only(client):
    owner, college = _setup(client)
    community = make_community(client, owner["access_token"], college["id"])

<<<<<<< HEAD
    outsider = register(client, "noah")
=======
    outsider = register(client, "noah", role="student")
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
    resp = client.post(
        "/api/v1/events",
        json={"community_id": community["id"], "name": "Sneaky Fest", "starts_at": "2027-01-01T10:00:00Z"},
        headers=auth_header(outsider["access_token"]),
    )
    assert resp.status_code == 403

    resp = client.post(
        "/api/v1/events",
        json={"community_id": community["id"], "name": "Robot Fest", "starts_at": "2027-01-01T10:00:00Z"},
        headers=auth_header(owner["access_token"]),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["listing_status"] == "upcoming"
    assert body["community_name"] == "Test Robotics Club"


def test_onboarding_update(client):
<<<<<<< HEAD
    user = register(client, "zoe")
=======
    user = register(client, "zoe", role="student")
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
    headers = auth_header(user["access_token"])
    resp = client.patch(
        "/api/v1/users/me",
        json={"goals": "Find a design team", "interests": ["robotics"], "skills": ["Python"]},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["goals"] == "Find a design team"
