"""Auth request/response schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
<<<<<<< HEAD
    """Public registration.

    SECURITY: there is deliberately no `role` field. Public registration ALWAYS
    creates a `student` account (`extra="forbid"` makes any attempt to smuggle
    a role — e.g. "reviewer" — fail validation). Reviewer/admin roles can only
    be assigned by an existing administrator via POST /api/v1/admin/users/{id}/role.
    The `organizer` platform role is granted through a controlled onboarding
    flow: a student who creates a community becomes an organizer.
    """

    model_config = ConfigDict(extra="forbid")

=======
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)
<<<<<<< HEAD
=======
    role: str = Field(default="student", pattern=r"^(student|organizer|reviewer)$")
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
    college_id: int | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


<<<<<<< HEAD
class RoleUpdateRequest(BaseModel):
    """Admin-only role assignment."""

    role: str = Field(pattern=r"^(student|organizer|reviewer|admin)$")


=======
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str
    role: str
    college_id: int | None = None
    bio: str = ""
    interests: list[str] = []
    skills: list[str] = []
    goals: str = ""
    links: dict = {}


class UserUpdate(BaseModel):
    full_name: str | None = None
    college_id: int | None = None
    bio: str | None = None
    interests: list[str] | None = None
    skills: list[str] | None = None
    goals: str | None = None
    links: dict | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
