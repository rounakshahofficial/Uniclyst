"""Collaboration request and workspace schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CollaborationRequestCreate(BaseModel):
    requester_community_id: int
    target_community_id: int
    title: str = Field(min_length=3, max_length=200)
    goal: str = Field(default="", max_length=255)
    message: str = ""
    needed_skills: list[str] = []
    proposed_timeline: str = Field(default="", max_length=200)


class CollaborationRequestAction(BaseModel):
    """accept | reject | withdraw"""

    action: str = Field(pattern=r"^(accept|reject|withdraw)$")
    response_note: str = ""


class CollaborationRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requester_community_id: int
    target_community_id: int = 0  # mapped from recipient_community_id in the API layer
    requester_community_name: str | None = None
    target_community_name: str | None = None
    requester_user_id: int | None = None
    title: str
    goal: str
    message: str
    needed_skills: list[str] = []
    proposed_timeline: str
    status: str
    response_note: str
    created_at: datetime
    responded_at: datetime | None = None
    direction: str = "outgoing"  # from the viewer's perspective: outgoing|incoming


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = ""
    due_date: date | None = None


class MilestoneUpdate(BaseModel):
    status: str = Field(pattern=r"^(pending|reached)$")


class MilestoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collaboration_id: int
    title: str
    description: str
    due_date: date | None = None
    status: str
    order_index: int = 0


class CollaborationMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str = ""
    full_name: str = ""
    community_id: int
    community_name: str | None = None
    role: str


class CollaborationUpdate(BaseModel):
    status: str = Field(pattern=r"^(active|completed|cancelled)$")
    summary: str = ""


class CollaborationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    title: str
    goal: str
    status: str
    summary: str
    started_at: datetime
    completed_at: datetime | None = None
    requester_community_id: int | None = None
    target_community_id: int | None = None
    requester_community_name: str | None = None
    target_community_name: str | None = None
    members: list[CollaborationMemberOut] = []
    milestones: list[MilestoneOut] = []
