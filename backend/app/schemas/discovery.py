"""Discovery (Community Scout) schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .community import DiscoverySourceOut, EventOut


class DiscoveryJobCreate(BaseModel):
    query: str = Field(min_length=3, max_length=400)
    region: str = Field(default="Delhi NCR", max_length=120)
    interests: list[str] = []


class DiscoveryJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    query: str
    region: str
    interests: list[str] = []
    status: str
    mode: str
    result_count: int
    error: str
    notes: list[str] = []
    created_by: int | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class DiscoveryJobDetail(DiscoveryJobOut):
    sources: list[DiscoverySourceOut] = []


class SourceReviewRequest(BaseModel):
    """Reviewer actions on an extracted record."""

    review_status: str = Field(pattern=r"^(discovered|reviewed|verified)$")
    review_note: str = ""


class SourceImportRequest(BaseModel):
    """Optional overrides when importing a discovered record as a community."""

    college_id: int | None = None  # link to an existing college instead of creating one
    name: str | None = None


class ScoutCandidateOut(BaseModel):
    """One extracted candidate as stored in DiscoverySource.extracted."""

    organization_name: str
    college: str
    city: str
    interests: list[str] = []
    skills: list[str] = []
    official_url: str | None = None
    event_names: list[str] = []
    confidence: float = 0.0
    verification_status: str = "discovered"
    missing_or_conflicting: str = ""
    dedupe_match_org_id: int | None = None


class ScoutRunResponse(BaseModel):
    """Result of running a scout job synchronously (MVP)."""

    job: DiscoveryJobOut
    candidates: list[ScoutCandidateOut]
