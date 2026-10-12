"""College, skill, community, and event schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------- Colleges ----------

class CollegeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    short_name: str = Field(min_length=1, max_length=40)
    city: str
    region: str = "Delhi NCR"
    country: str = "India"
    website: str | None = None
    lat: float | None = None
    lng: float | None = None
    description: str = ""


class CollegeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_name: str
    city: str
    region: str
    country: str
    website: str | None = None
    lat: float | None = None
    lng: float | None = None
    description: str = ""
    community_count: int = 0


# ---------- Skills ----------

class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str


class SkillAssignment(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: str = Field(default="offers", pattern=r"^(offers|seeks)$")


# ---------- Communities ----------

class CommunityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    college_id: int
    description: str = ""
    category: str = Field(default="Technical", max_length=80)
    interests: list[str] = []
    skills: list[SkillAssignment] = []
    website: str | None = None
    social_links: dict = {}


class CommunityUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    interests: list[str] | None = None
    skills: list[SkillAssignment] | None = None
    website: str | None = None
    social_links: dict | None = None
    # reviewer-only
    verification_status: str | None = None


class CommunityMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str = ""
    full_name: str = ""
    role: str


class DiscoverySourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_url: str
    source_title: str
    evidence_excerpt: str
    retrieved_at: datetime
    last_checked_at: datetime
    review_status: str
    confidence: float
    review_note: str
    origin: str
<<<<<<< HEAD
    extracted: dict = {}
=======
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: str
    needed_skills: list[str] = []


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    community_id: int
    name: str
    description: str
    category: str
    starts_at: datetime
    ends_at: datetime | None = None
    city: str | None = None
    is_online: int = 0
    event_url: str | None = None
    source_url: str | None = None
    last_checked_at: datetime | None = None
    listing_status: str = "upcoming"
    confidence: float = 0.0
    community_name: str | None = None


class EventCreate(BaseModel):
    community_id: int
    name: str = Field(min_length=2, max_length=200)
    description: str = ""
    category: str = "Hackathon"
    starts_at: datetime
    ends_at: datetime | None = None
    city: str | None = None
    is_online: bool = False
    event_url: str | None = None


class CommunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    college_id: int
    college_name: str | None = None
    college_short: str | None = None
    city: str | None = None
    description: str
    category: str
    interests: list[str] = []
    website: str | None = None
    social_links: dict = {}
    verification_status: str
    confidence: float
    last_checked_at: datetime | None = None
    is_demo: int = 0
    created_by: int | None = None
    created_at: datetime | None = None
    skills: list[SkillAssignment] = []
    members: list[CommunityMemberOut] = []
    projects: list[ProjectOut] = []
    events: list[EventOut] = []
    sources: list[DiscoverySourceOut] = []
    saved: bool = False
