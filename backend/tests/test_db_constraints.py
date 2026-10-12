"""Database constraint tests: uniqueness and referential integrity."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models import Community, CommunityMember, Skill, User
from tests.conftest import auth_header, make_college, make_community, register


def test_duplicate_username_rejected(client, db_session):
    register(client, "alice")
    db_session.add(
        User(
            username="alice",
            email="different@example.com",
            password_hash=hash_password("x"),
            full_name="Dup",
            role="student",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_duplicate_community_membership_rejected(client, db_session):
<<<<<<< HEAD
    user = register(client, "olivia")
=======
    user = register(client, "olivia", role="organizer")
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
    college = make_college(client, user["access_token"])
    community = make_community(client, user["access_token"], college["id"])
    db_session.add(CommunityMember(community_id=community["id"], user_id=user["user"]["id"], role="member"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unique_skill_names(client, db_session):
    db_session.add(Skill(name="Python", category="Software"))
    db_session.commit()
    db_session.add(Skill(name="Python", category="Software"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_community_requires_existing_college(client):
<<<<<<< HEAD
    user = register(client, "olivia")
=======
    user = register(client, "olivia", role="organizer")
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
    resp = client.post(
        "/api/v1/communities",
        json={"name": "Ghost Club", "college_id": 999},
        headers=auth_header(user["access_token"]),
    )
    assert resp.status_code == 404


def test_delete_community_removes_membership(client, db_session):
<<<<<<< HEAD
    user = register(client, "olivia")
=======
    user = register(client, "olivia", role="organizer")
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
    college = make_college(client, user["access_token"])
    community = make_community(client, user["access_token"], college["id"])
    assert db_session.query(CommunityMember).count() == 1

    client.delete(f"/api/v1/communities/{community['id']}", headers=auth_header(user["access_token"]))
    assert db_session.query(Community).count() == 0
    assert db_session.query(CommunityMember).count() == 0
