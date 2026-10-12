"""Pydantic schemas for the Uniclyst API."""

from .auth import LoginRequest, RegisterRequest, TokenResponse, UserOut, UserUpdate
from .common import Page, make_page
from .community import (
    CollegeCreate,
    CollegeOut,
    CommunityCreate,
    CommunityMemberOut,
    CommunityOut,
    CommunityUpdate,
    DiscoverySourceOut,
    EventCreate,
    EventOut,
    ProjectOut,
    SkillAssignment,
    SkillOut,
)

__all__ = [
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserOut",
    "UserUpdate",
    "Page",
    "make_page",
    "CollegeCreate",
    "CollegeOut",
    "CommunityCreate",
    "CommunityMemberOut",
    "CommunityOut",
    "CommunityUpdate",
    "DiscoverySourceOut",
    "EventCreate",
    "EventOut",
    "ProjectOut",
    "SkillAssignment",
    "SkillOut",
]
