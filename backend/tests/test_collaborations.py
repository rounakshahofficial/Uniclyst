"""Collaboration workflow tests: proposals, decisions, workspace, milestones."""

from tests.conftest import auth_header, make_college, make_community, register


def _setup_two_communities(client):
    """Two organizers, two communities on two colleges."""
    alice = register(client, "alice")
    college_a = make_college(client, alice["access_token"], short="CA", name="College A")
    community_a = make_community(client, alice["access_token"], college_a["id"], name="Robotics A")

    bob = register(client, "bob")
    college_b = make_college(client, bob["access_token"], short="CB", name="College B")
    community_b = make_community(client, bob["access_token"], college_b["id"], name="Vision B")
    return alice, community_a, bob, community_b


def _proposal(a_id, b_id, **extra):
    return {
        "requester_community_id": a_id,
        "target_community_id": b_id,
        "title": "Joint rover perception build",
        "goal": "Autonomous robot perception",
        "message": "Let's co-build the vision stack and run a workshop.",
        "needed_skills": ["Computer Vision"],
        "proposed_timeline": "8 weeks",
        **extra,
    }


def test_full_accept_flow_creates_workspace(client):
    alice, comm_a, bob, comm_b = _setup_two_communities(client)

    resp = client.post("/api/v1/collaboration-requests",
                       json=_proposal(comm_a["id"], comm_b["id"]),
                       headers=auth_header(alice["access_token"]))
    assert resp.status_code == 201, resp.text
    req = resp.json()
    assert req["status"] == "pending"

    # Bob accepts → collaboration + starter milestone
    resp = client.patch(
        f"/api/v1/collaboration-requests/{req['id']}",
        json={"action": "accept", "response_note": "Excited to build this"},
        headers=auth_header(bob["access_token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"

    collabs = client.get("/api/v1/collaborations", headers=auth_header(alice["access_token"])).json()
    assert collabs["total"] == 1
    collab = collabs["items"][0]
    assert collab["status"] == "active"
    assert collab["title"] == "Joint rover perception build"
    assert len(collab["members"]) == 2
    assert {m["user_id"] for m in collab["members"]} == {alice["user"]["id"], bob["user"]["id"]}
    assert any(ms["title"].startswith("Kickoff") for ms in collab["milestones"])

    # Both sides can see the same workspace
    for token in (alice["access_token"], bob["access_token"]):
        detail = client.get(f"/api/v1/collaborations/{collab['id']}",
                            headers=auth_header(token)).json()
        assert detail["requester_community_name"] == "Robotics A"
        assert detail["target_community_name"] == "Vision B"


def test_reject_and_withdraw(client):
    alice, comm_a, bob, comm_b = _setup_two_communities(client)

    req1 = client.post("/api/v1/collaboration-requests", json=_proposal(comm_a["id"], comm_b["id"]),
                       headers=auth_header(alice["access_token"])).json()
    resp = client.patch(f"/api/v1/collaboration-requests/{req1['id']}",
                        json={"action": "reject", "response_note": "Not this semester"},
                        headers=auth_header(bob["access_token"]))
    assert resp.json()["status"] == "rejected"
    assert resp.json()["response_note"] == "Not this semester"

    req2 = client.post("/api/v1/collaboration-requests", json=_proposal(comm_a["id"], comm_b["id"]),
                       headers=auth_header(alice["access_token"])).json()
    resp = client.patch(f"/api/v1/collaboration-requests/{req2['id']}",
                        json={"action": "withdraw"},
                        headers=auth_header(alice["access_token"]))
    assert resp.json()["status"] == "withdrawn"

    # No collaboration was created
    assert client.get("/api/v1/collaborations", headers=auth_header(alice["access_token"])).json()["total"] == 0


def test_authorization_on_every_action(client):
    alice, comm_a, bob, comm_b = _setup_two_communities(client)
    mallory = register(client, "mallory")
    req = client.post("/api/v1/collaboration-requests", json=_proposal(comm_a["id"], comm_b["id"]),
                      headers=auth_header(alice["access_token"])).json()

    # Outsider cannot view the proposal
    resp = client.get(f"/api/v1/collaboration-requests/{req['id']}",
                      headers=auth_header(mallory["access_token"]))
    assert resp.status_code == 403

    # Outsider cannot accept/withdraw
    for action in ("accept", "withdraw"):
        resp = client.patch(f"/api/v1/collaboration-requests/{req['id']}",
                            json={"action": action},
                            headers=auth_header(mallory["access_token"]))
        assert resp.status_code == 403

    # The author cannot accept their own proposal (recipient decides)
    resp = client.patch(f"/api/v1/collaboration-requests/{req['id']}",
                        json={"action": "accept"},
                        headers=auth_header(alice["access_token"]))
    assert resp.status_code == 403

    # Non-organizer members cannot send proposals for a community
    resp = client.post("/api/v1/collaboration-requests",
                       json=_proposal(comm_b["id"], comm_a["id"]),
                       headers=auth_header(mallory["access_token"]))
    assert resp.status_code == 403


def test_cannot_self_collaborate_or_duplicate(client):
    alice, comm_a, bob, comm_b = _setup_two_communities(client)

    resp = client.post("/api/v1/collaboration-requests",
                       json=_proposal(comm_a["id"], comm_a["id"]),
                       headers=auth_header(alice["access_token"]))
    assert resp.status_code == 422

    client.post("/api/v1/collaboration-requests", json=_proposal(comm_a["id"], comm_b["id"]),
                headers=auth_header(alice["access_token"]))
    resp = client.post("/api/v1/collaboration-requests", json=_proposal(comm_a["id"], comm_b["id"]),
                       headers=auth_header(alice["access_token"]))
    assert resp.status_code == 409

    # After a decision, a new proposal is allowed again
    req = client.get("/api/v1/collaboration-requests?direction=outgoing",
                     headers=auth_header(alice["access_token"])).json()["items"][0]
    client.patch(f"/api/v1/collaboration-requests/{req['id']}", json={"action": "reject"},
                 headers=auth_header(bob["access_token"]))
    resp = client.post("/api/v1/collaboration-requests", json=_proposal(comm_a["id"], comm_b["id"]),
                       headers=auth_header(alice["access_token"]))
    assert resp.status_code == 201


def test_double_decision_conflict(client):
    alice, comm_a, bob, comm_b = _setup_two_communities(client)
    req = client.post("/api/v1/collaboration-requests", json=_proposal(comm_a["id"], comm_b["id"]),
                      headers=auth_header(alice["access_token"])).json()
    client.patch(f"/api/v1/collaboration-requests/{req['id']}", json={"action": "accept"},
                 headers=auth_header(bob["access_token"]))
    resp = client.patch(f"/api/v1/collaboration-requests/{req['id']}", json={"action": "reject"},
                        headers=auth_header(bob["access_token"]))
    assert resp.status_code == 409


def test_milestones_and_completion(client):
    alice, comm_a, bob, comm_b = _setup_two_communities(client)
    req = client.post("/api/v1/collaboration-requests", json=_proposal(comm_a["id"], comm_b["id"]),
                      headers=auth_header(alice["access_token"])).json()
    client.patch(f"/api/v1/collaboration-requests/{req['id']}", json={"action": "accept"},
                 headers=auth_header(bob["access_token"]))
    collab = client.get("/api/v1/collaborations", headers=auth_header(alice["access_token"])).json()["items"][0]

    # Participants add and reach milestones
    resp = client.post(f"/api/v1/collaborations/{collab['id']}/milestones",
                       json={"title": "Working perception demo", "due_date": "2027-01-15"},
                       headers=auth_header(bob["access_token"]))
    assert resp.status_code == 201
    ms = resp.json()
    assert ms["status"] == "pending"

    resp = client.patch(f"/api/v1/milestones/{ms['id']}", json={"status": "reached"},
                        headers=auth_header(alice["access_token"]))
    assert resp.json()["status"] == "reached"

    # Outsider cannot touch the workspace
    mallory = register(client, "mallory")
    resp = client.post(f"/api/v1/collaborations/{collab['id']}/milestones",
                       json={"title": "Sabotage"}, headers=auth_header(mallory["access_token"]))
    assert resp.status_code == 403
    resp = client.get(f"/api/v1/collaborations/{collab['id']}",
                      headers=auth_header(mallory["access_token"]))
    assert resp.status_code == 403

    # Completion records outcome
    resp = client.patch(f"/api/v1/collaborations/{collab['id']}",
                        json={"status": "completed", "summary": "Demo shipped at the joint workshop"},
                        headers=auth_header(alice["access_token"]))
    assert resp.json()["status"] == "completed"
    assert resp.json()["completed_at"] is not None
    assert resp.json()["summary"] == "Demo shipped at the joint workshop"
