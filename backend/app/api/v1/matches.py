"""Explainable matching API.

GET /api/v1/matches?community_id=1&goal=...&needed_skills=Computer Vision,ML

Thin route: loads profiles from the DB and delegates ALL scoring to
app.services.matching (pure, unit-testable logic).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.errors import AppError
from ...core.security import get_optional_user
from ...db.session import get_db
from ...models import Community
from ...repositories.communities import community_to_out, get_community, saved_community_ids
from ...schemas import CommunityOut
from ...schemas.matching import FreshnessOut, MatchResponse, MatchResultOut, ScoreBreakdown
from ...services import matching

router = APIRouter(prefix="/matches", tags=["matching"])


@router.get("", response_model=MatchResponse)
def find_matches(
    community_id: int = Query(..., description="Your community — never matched to itself"),
    goal: str = Query("", description="What you want to build together"),
    needed_skills: str = Query("", description="Comma-separated skills the partner should bring"),
    project_id: int | None = Query(None, description="Use a project's goal/needed skills"),
    min_score: float = Query(15.0, ge=0, le=100),
    limit: int = Query(8, ge=1, le=25),
    exclude: str = Query("", description="Comma-separated community ids to exclude"),
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
):
    requester_row = get_community(db, community_id)
    if requester_row is None:
        raise AppError(404, "not_found", "Community not found")

    skills = [s.strip() for s in needed_skills.split(",") if s.strip()]
    resolved_goal = goal
    if project_id is not None:
        project = next((p for p in requester_row.projects if p.id == project_id), None)
        if project is None:
            raise AppError(404, "not_found", "Project not found on this community")
        resolved_goal = resolved_goal or project.description or project.title
        if not skills:
            skills = list(project.needed_skills or [])

    exclude_ids = [int(x) for x in exclude.split(",") if x.strip().isdigit()]
    requirements = matching.MatchRequirements(
        needed_skills=skills,
        goal=resolved_goal,
        exclude_ids=exclude_ids,
        min_score=min_score,
        limit=limit,
    )

    all_rows = db.scalars(
        select(Community).where(Community.id != community_id)
    ).all()
    # Re-load with eager relationships via get_community for serialization
    requester_profile = matching.profile_from_model(requester_row)
    candidate_rows = [get_community(db, c.id) for c in all_rows]
    candidate_profiles = [matching.profile_from_model(c) for c in candidate_rows if c is not None]

    ranked = matching.rank_matches(requester_profile, candidate_profiles, requirements)

    saved = saved_community_ids(db, user.id if user else None)
    by_id = {c.id: c for c in candidate_rows if c is not None}

    results = []
    for r in ranked:
        results.append(
            MatchResultOut(
                community=community_to_out(by_id[r.candidate.id], saved),
                score=ScoreBreakdown(**r.score.as_dict()),
                reasons=r.reasons,
                strongest_factors=r.strongest_factors,
                missing_skills=r.missing_skills,
                freshness=FreshnessOut(**r.freshness),
                uncertainty=r.uncertainty,
            )
        )

    return MatchResponse(
        requester=community_to_out(requester_row, saved),
        goal=resolved_goal,
        needed_skills=skills,
        formula=matching.FORMULA,
        weights=matching.DEFAULT_WEIGHTS,
        matches=results,
    )
