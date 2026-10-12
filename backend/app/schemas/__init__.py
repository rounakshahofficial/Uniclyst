"""Pydantic schemas for the Uniclyst API."""

<<<<<<< HEAD
from .auth import LoginRequest, RegisterRequest, RoleUpdateRequest, TokenResponse, UserOut, UserUpdate
=======
from .auth import LoginRequest, RegisterRequest, TokenResponse, UserOut, UserUpdate
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
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
<<<<<<< HEAD
    "RoleUpdateRequest",
=======
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
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
