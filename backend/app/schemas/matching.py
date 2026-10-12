"""Matching response schemas."""

from pydantic import BaseModel

from .community import CommunityOut


class ScoreBreakdown(BaseModel):
    interest: float
    skills: float
    goal: float
    geography: float
    profile: float
    total: float


class FreshnessOut(BaseModel):
    verification_status: str
    confidence: float
    source_count: int
    last_checked_at: str | None = None


class MatchResultOut(BaseModel):
    community: CommunityOut
    score: ScoreBreakdown
    reasons: list[str]
    strongest_factors: list[str]
    missing_skills: list[str] = []
    freshness: FreshnessOut
    uncertainty: str | None = None


class MatchResponse(BaseModel):
    requester: CommunityOut
    goal: str = ""
    needed_skills: list[str] = []
    formula: str
    weights: dict
    matches: list[MatchResultOut]
