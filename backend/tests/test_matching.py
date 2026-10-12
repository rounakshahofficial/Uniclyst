"""Matching engine tests: pure scoring logic + /api/v1/matches endpoint."""

from datetime import datetime, timedelta, timezone

from app.services import matching
from app.services.matching import (
    CommunityProfile,
    MatchRequirements,
    rank_matches,
    score_pair,
)
from tests.conftest import auth_header, make_college, make_community, register

DTU_ROBOTICS = CommunityProfile(
    id=1, name="Robotics Society DTU",
    interests=["robotics", "iot"],
    offered_skills=["ROS", "Arduino", "Mechanical Design", "Embedded"],
    sought_skills=["Computer Vision", "Machine Learning"],
    project_titles=["Autonomous Rover"],
    project_descriptions=["An arena rover with onboard perception"],
    city="Delhi", college_id=1, verification_status="verified", confidence=88,
    description="Builds autonomous robots", website="https://robotics.dtu.ac.in/",
    member_count=120, source_count=1,
    last_checked_at=datetime.now(timezone.utc) - timedelta(days=3),
)

IIITD_AI = CommunityProfile(
    id=2, name="AIMS — AI & ML Society",
    interests=["ai", "machine learning"],
    offered_skills=["Machine Learning", "Computer Vision", "Python"],
    city="Delhi", college_id=2, verification_status="verified", confidence=91,
    description="AI society", website="https://iiitd.ac.in/aims/",
    member_count=95, source_count=1,
    last_checked_at=datetime.now(timezone.utc) - timedelta(days=5),
)

SNU_HARDWARE = CommunityProfile(
    id=3, name="Avishkar Innovation Club",
    interests=["innovation", "iot"],
    offered_skills=["IoT", "Embedded", "Prototyping"],
    city="Greater Noida", college_id=3, verification_status="reviewed", confidence=74,
    description="Hardware prototyping", member_count=75, source_count=1,
    last_checked_at=datetime.now(timezone.utc) - timedelta(days=40),
)

THIN_CLUB = CommunityProfile(id=4, name="Mystery Club", city="Delhi")


def test_weights_sum_to_one():
    assert abs(sum(matching.DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9


def test_complementary_skills_dominate_the_score():
    """The AI club must out-rank the hardware club for a CV/ML-needing project."""
    req = MatchRequirements(needed_skills=["Computer Vision", "Machine Learning"],
                            goal="autonomous robot perception")
    results = rank_matches(DTU_ROBOTICS, [IIITD_AI, SNU_HARDWARE, THIN_CLUB], req)
    assert results[0].candidate.id == 2
    ai, hw = results[0], next(r for r in results if r.candidate.id == 3)
    assert ai.score.skills > 60
    assert ai.score.total > hw.score.total
    # Every recommendation explains itself
    assert all(len(r.reasons) == 5 for r in results)
    assert any("Computer Vision" in r for r in ai.reasons)


def test_interest_and_goal_produce_reasons():
    req = MatchRequirements(needed_skills=["Computer Vision"], goal="machine learning perception")
    result = score_pair(DTU_ROBOTICS, IIITD_AI, req)
    assert result.score.interest > 0
    assert "Interest compatibility" in result.reasons[0]
    assert result.strongest_factors
    assert result.freshness["verification_status"] == "verified"


def test_missing_data_is_not_punished_into_the_ground():
    req = MatchRequirements(needed_skills=["Computer Vision"], goal="robotics")
    thin = score_pair(DTU_ROBOTICS, THIN_CLUB, req)
    assert thin.score.skills >= 30  # neutral-ish, not zero
    assert thin.uncertainty is not None
    assert "Thin profile" in thin.uncertainty or "limited evidence" in thin.uncertainty


def test_neutral_baselines_without_requirements():
    bare = CommunityProfile(id=50, name="Bare Club", city="Delhi", college_id=1)
    req = MatchRequirements()
    result = score_pair(bare, IIITD_AI, req)
    assert result.score.skills == 55.0
    assert result.score.goal == 50.0
    # But declared 'seeks' skills are used as a fallback for requirements
    fallback = score_pair(DTU_ROBOTICS, IIITD_AI, MatchRequirements())
    assert fallback.score.skills == 100.0  # AIMS offers both skills DTU seeks


def test_geography_scores():
    nearby = CommunityProfile(id=9, name="X", interests=["robotics"], city="Noida")
    far = CommunityProfile(id=10, name="Y", interests=["robotics"], city="Mumbai")
    req = MatchRequirements()
    assert score_pair(DTU_ROBOTICS, nearby, req).score.geography == 75.0
    assert score_pair(DTU_ROBOTICS, far, req).score.geography == 30.0


def test_self_match_exclusion_duplicates_and_threshold():
    req = MatchRequirements(needed_skills=["Machine Learning"], min_score=0, exclude_ids=[3])
    results = rank_matches(DTU_ROBOTICS, [DTU_ROBOTICS, IIITD_AI, IIITD_AI, SNU_HARDWARE], req)
    ids = [r.candidate.id for r in results]
    assert 1 not in ids  # never match to self
    assert 3 not in ids  # honored exclusion
    assert ids.count(2) == 1  # duplicates removed

    high = MatchRequirements(needed_skills=["Machine Learning"], min_score=99.0)
    assert rank_matches(DTU_ROBOTICS, [THIN_CLUB], high) == []  # threshold filters


def test_missing_skill_reported():
    req = MatchRequirements(needed_skills=["Computer Vision", "Quantum Computing"])
    result = score_pair(DTU_ROBOTICS, SNU_HARDWARE, req)
    assert "Quantum Computing" in result.missing_skills
    assert result.uncertainty and "Quantum Computing" in result.uncertainty


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------

def _seed_pair(client):
    user = register(client, "olivia")
    college = make_college(client, user["access_token"], short="DTU2",
                           name="Demo Tech University")
    robotics = make_community(
        client, user["access_token"], college["id"],
        name="Robotics Club", interests=["robotics"],
        skills=[{"name": "Arduino", "kind": "offers"},
                {"name": "Computer Vision", "kind": "seeks"}],
    )
    ai_club = make_community(
        client, user["access_token"], college["id"],
        name="Vision AI Club", interests=["ai"],
        skills=[{"name": "Computer Vision", "kind": "offers"},
                {"name": "Machine Learning", "kind": "offers"}],
    )
    design_club = make_community(
        client, user["access_token"], college["id"],
        name="Design Society", category="Cultural", interests=["design"],
        skills=[{"name": "UI/UX", "kind": "offers"}],
    )
    return robotics, ai_club, design_club


def test_matches_endpoint_ranks_and_explains(client):
    robotics, ai_club, design_club = _seed_pair(client)
    resp = client.get(
        f"/api/v1/matches?community_id={robotics['id']}"
        "&goal=autonomous robot perception&needed_skills=Computer Vision,Machine Learning"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["formula"] == matching.FORMULA
    assert body["requester"]["id"] == robotics["id"]
    ids = [m["community"]["id"] for m in body["matches"]]
    assert robotics["id"] not in ids          # no self-match
    assert ids[0] == ai_club["id"]            # best fit first
    best = body["matches"][0]
    assert best["score"]["total"] > 30
    assert set(best["score"]) == {"interest", "skills", "goal", "geography", "profile", "total"}
    assert len(best["reasons"]) == 5
    assert best["freshness"]["verification_status"] == "discovered"
    # Design club should rank below the AI club
    assert best["score"]["total"] >= body["matches"][-1]["score"]["total"]


def test_matches_endpoint_excludes_and_unknown_community(client):
    robotics, ai_club, _ = _seed_pair(client)
    resp = client.get(
        f"/api/v1/matches?community_id={robotics['id']}&exclude={ai_club['id']}"
    )
    ids = [m["community"]["id"] for m in resp.json()["matches"]]
    assert ai_club["id"] not in ids

    resp = client.get("/api/v1/matches?community_id=9999")
    assert resp.status_code == 404
