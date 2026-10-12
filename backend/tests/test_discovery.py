"""TinyFish Community Scout tests — mocked API responses, demo mode, review flow."""

import pytest

from app.core.config import settings
from app.services.tinyfish_scout import (
    DEMO_PAGES,
    TinyFishClient,
    confidence_for,
    dedupe,
    normalize_page,
    run_scout,
)
from tests.conftest import auth_header, make_college, make_community, register


# ---------------------------------------------------------------------------
# TinyFish client request formats (verified against docs.tinyfish.ai)
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


class FakeClient:
    """Captures requests so we can assert on the documented wire format."""

    calls = []

    def __init__(self, timeout=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def request(self, method, url, headers=None, **kwargs):
        FakeClient.calls.append({"method": method, "url": url, "headers": headers, **kwargs})
        if "search" in url:
            return FakeResponse({
                "query": "robotics clubs",
                "results": [
                    {"position": 1, "site_name": "dtu.ac.in", "title": "Robotics Society DTU",
                     "snippet": "autonomous robots…", "url": "https://robotics.dtu.ac.in/"},
                ],
                "total_results": 1, "page": 0,
            })
        return FakeResponse({
            "results": [{
                "url": "https://robotics.dtu.ac.in/", "final_url": "https://robotics.dtu.ac.in/",
                "title": "Robotics Society DTU", "description": "", "language": "en",
                "format": "markdown", "text": "# Robotics Society DTU\nSkills: ROS, Arduino.",
            }],
            "errors": [],
        })


def test_client_uses_documented_endpoints_and_auth(monkeypatch):
    monkeypatch.setattr("app.services.tinyfish_scout.httpx.Client", FakeClient)
    FakeClient.calls = []
    client = TinyFishClient(api_key="sk-test-key")
    assert client.enabled

    client.search("robotics clubs", location="Delhi NCR")
    search_call = FakeClient.calls[-1]
    assert search_call["method"] == "GET"
    assert search_call["url"] == settings.TINYFISH_SEARCH_URL == "https://api.search.tinyfish.ai"
    assert search_call["headers"]["X-API-Key"] == "sk-test-key"
    assert search_call["params"]["query"] == "robotics clubs"
    assert search_call["params"]["location"] == "Delhi NCR"

    client.fetch(["https://robotics.dtu.ac.in/"], fmt="markdown", ttl=3600)
    fetch_call = FakeClient.calls[-1]
    assert fetch_call["method"] == "POST"
    assert fetch_call["url"] == settings.TINYFISH_FETCH_URL == "https://api.fetch.tinyfish.ai"
    assert fetch_call["json"] == {"urls": ["https://robotics.dtu.ac.in/"], "format": "markdown", "ttl": 3600}


def test_client_disabled_without_key():
    assert not TinyFishClient(api_key="").enabled


# ---------------------------------------------------------------------------
# Extraction, evidence, confidence
# ---------------------------------------------------------------------------

def test_normalize_page_extracts_evidence_and_flags():
    page = DEMO_PAGES["https://ggsipu.ac.in/aero/"]
    cand = normalize_page("https://ggsipu.ac.in/aero/", page)
    assert cand.organization_name == "Aeronautical Society"
    assert cand.evidence and cand.evidence[0].source_url == "https://ggsipu.ac.in/aero/"
    assert cand.evidence[0].evidence_excerpt
    assert "conflicting" in cand.missing_or_conflicting.lower()
    assert cand.verification_status == "discovered"  # never auto-verified
    assert cand.confidence > 0


def test_confidence_official_domain_beats_social():
    official, _ = confidence_for("https://robotics.dtu.ac.in/", "Skills: ROS. Contact: x@dtu.ac.in")
    social, note = confidence_for("https://instagram.com/someclub", "900+ followers")
    assert official > social
    assert "social media" in note


def test_event_extraction():
    cand = normalize_page("https://robotics.dtu.ac.in/", DEMO_PAGES["https://robotics.dtu.ac.in/"])
    assert any("RoboWars" in e for e in cand.event_names)


# ---------------------------------------------------------------------------
# Demo mode (no credentials) — clearly labeled, identical pipeline
# ---------------------------------------------------------------------------

def test_demo_mode_job_end_to_end(client):
    user = register(client, "scout")
    resp = client.post(
        "/api/v1/discovery/jobs",
        json={"query": "robotics AI clubs", "region": "Delhi NCR", "interests": ["robotics", "ai"]},
        headers=auth_header(user["access_token"]),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["job"]["mode"] == "demo"
    assert body["job"]["status"] == "completed"
    assert any("DEMO MODE" in n for n in body["job"]["notes"])
    assert body["candidates"], "demo corpus should yield candidates"

    # Evidence rows persisted with timestamps + extraction payload
    sources = client.get(
        f"/api/v1/discovery/jobs/{body['job']['id']}", headers=auth_header(user["access_token"])
    ).json()["sources"]
    assert sources
    src = sources[0]
    assert src["source_url"]
    assert src["retrieved_at"] and src["last_checked_at"]
    assert src["review_status"] == "discovered"
    assert src["origin"] == "seed"  # demo data is labeled, not passed off as live


# ---------------------------------------------------------------------------
# Live mode with mocked TinyFish responses
# ---------------------------------------------------------------------------

def test_live_mode_job_with_mocked_api(client, monkeypatch):
    monkeypatch.setattr(settings, "TINYFISH_API_KEY", "sk-test-key")

    def fake_search(self, query, location=None, page=0):
        return {"query": query, "results": [
            {"position": 1, "site_name": "iiitd.ac.in", "title": "AIMS IIIT Delhi",
             "snippet": "AI and ML society", "url": "https://www.iiitd.ac.in/aims/"},
        ], "total_results": 1, "page": 0}

    def fake_fetch(self, urls, fmt="markdown", ttl=None):
        return {"results": [{
            "url": urls[0], "final_url": urls[0], "title": "AIMS IIIT Delhi",
            "language": "en", "format": "markdown",
            "text": "# AIMS — AI and Machine Learning Society at IIIT Delhi\n"
                    "Skills: machine learning, computer vision, python.\nUpcoming: NCR ML Meetup — April 2027.",
        }], "errors": []}

    monkeypatch.setattr(TinyFishClient, "search", fake_search)
    monkeypatch.setattr(TinyFishClient, "fetch", fake_fetch)

    user = register(client, "scout")
    resp = client.post(
        "/api/v1/discovery/jobs",
        json={"query": "machine learning societies", "region": "Delhi NCR", "interests": ["ai"]},
        headers=auth_header(user["access_token"]),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["job"]["mode"] == "live"
    assert body["candidates"]
    cand = body["candidates"][0]
    assert cand["organization_name"] == "AIMS"
    assert "machine learning" in cand["interests"]
    assert any("RoboWars" not in e for e in cand.get("event_names", []))

    sources = client.get("/api/v1/discovery/sources", headers=auth_header(user["access_token"])).json()
    assert sources["items"][0]["origin"] == "scout"


# ---------------------------------------------------------------------------
# Dedupe, review permissions, import
# ---------------------------------------------------------------------------

def test_dedupe_flags_existing_communities(client, db_session):
    from app.services.tinyfish_scout import Candidate

    user = register(client, "olivia")
    college = make_college(client, user["access_token"])
    existing = make_community(client, user["access_token"], college["id"], name="Robotics Society DTU")
    cand = Candidate(organization_name="Robotics Society", college="DTU", city="Delhi")
    dedupe([cand], db_session)
    assert cand.dedupe_match_org_id == existing["id"]


def test_review_permissions(client, db_session):
    from tests.conftest import make_admin

    user = register(client, "scout")
    headers = auth_header(user["access_token"])
    client.post(
        "/api/v1/discovery/jobs", json={"query": "robotics clubs", "region": "Delhi NCR"},
        headers=headers,
    )
    source_id = client.get("/api/v1/discovery/sources", headers=headers).json()["items"][0]["id"]

    # Ordinary user cannot change review status at all
    resp = client.patch(
        f"/api/v1/discovery/sources/{source_id}",
        json={"review_status": "reviewed"}, headers=headers,
    )
    assert resp.status_code == 403

    # Ordinary user cannot promote to verified
    resp = client.patch(
        f"/api/v1/discovery/sources/{source_id}",
        json={"review_status": "verified"}, headers=headers,
    )
    assert resp.status_code == 403

    # Admin can (trusted role, never obtainable at registration)
    admin = make_admin(client, db_session, "root")
    resp = client.patch(
        f"/api/v1/discovery/sources/{source_id}",
        json={"review_status": "verified", "review_note": "Confirmed on official domain"},
        headers=auth_header(admin["access_token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "verified"


def test_import_and_review_flow(client, db_session):
    from tests.conftest import make_admin

    scout_user = register(client, "scout")
    headers = auth_header(scout_user["access_token"])
    client.post(
        "/api/v1/discovery/jobs",
        json={"query": "cyber security", "region": "Delhi NCR", "interests": ["cybersecurity"]},
        headers=headers,
    )
    sources = client.get("/api/v1/discovery/sources", headers=headers).json()["items"]
    source = sources[0]
    assert source["extracted"].get("organization_name")  # payload persisted for review

    # Import as discovered — never verified
    resp = client.post(
        f"/api/v1/discovery/sources/{source['id']}/import", json={}, headers=headers,
    )
    assert resp.status_code == 201, resp.text
    community_id = resp.json()["community_id"]
    community = client.get(f"/api/v1/communities/{community_id}", headers=headers).json()
    assert community["verification_status"] == "discovered"
    assert community["name"]

    # The evidence row now points at the community
    detail = client.get("/api/v1/discovery/sources?review_status=discovered", headers=headers).json()
    assert detail["items"]

    # Reviewer promotes the source record
    admin = make_admin(client, db_session, "root")
    reviewer = register(client, "ravi")
    client.post(
        f"/api/v1/admin/users/{reviewer['user']['id']}/role",
        json={"role": "reviewer"}, headers=auth_header(admin["access_token"]),
    )
    resp = client.patch(
        f"/api/v1/discovery/sources/{source['id']}",
        json={"review_status": "reviewed", "review_note": "Checked against college site"},
        headers=auth_header(reviewer["access_token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "reviewed"
    assert resp.json()["review_note"] == "Checked against college site"
