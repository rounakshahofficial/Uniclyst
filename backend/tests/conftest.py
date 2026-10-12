"""Test fixtures: isolated in-memory SQLite database per test."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AUTO_CREATE_TABLES"] = "0"
os.environ["AUTO_SEED"] = "0"
os.environ["JWT_SECRET"] = "test-secret-0123456789abcdef0123"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture()
def client():
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


<<<<<<< HEAD
def register(client: TestClient, username="alice", email=None, **extra):
    """Public registration — always creates a student account.

    `extra` is forwarded to the payload so tests can attempt illegal fields
    (e.g. role="reviewer") and assert they are rejected.
    """
=======
def register(client: TestClient, username="alice", role="organizer", email=None, **extra):
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
    payload = {
        "username": username,
        "email": email or f"{username}@example.com",
        "password": "supersecret1",
        "full_name": f"Test {username.title()}",
<<<<<<< HEAD
=======
        "role": role,
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
        **extra,
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


<<<<<<< HEAD
def make_admin(client: TestClient, db_session, username="root"):
    """Create a user and promote them to admin directly (operator-level action)."""
    from app.models import User

    data = register(client, username)
    user = db_session.get(User, data["user"]["id"])
    user.role = "admin"
    db_session.add(user)
    db_session.commit()
    return data


=======
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_college(client: TestClient, token: str, short="TST", name="Test Institute of Technology"):
    resp = client.post(
        "/api/v1/colleges",
        json={"name": name, "short_name": short, "city": "Delhi", "region": "Delhi NCR"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def make_community(client: TestClient, token: str, college_id: int, name="Test Robotics Club", **extra):
    payload = {
        "name": name,
        "college_id": college_id,
        "description": "A club that builds test robots.",
        "category": "Technical",
        "interests": ["robotics"],
        "skills": [
            {"name": "Arduino", "kind": "offers"},
            {"name": "Computer Vision", "kind": "seeks"},
        ],
        **extra,
    }
    resp = client.post("/api/v1/communities", json=payload, headers=auth_header(token))
    assert resp.status_code == 201, resp.text
    return resp.json()
