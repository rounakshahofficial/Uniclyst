"""Auth request/response schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="student", pattern=r"^(student|organizer|reviewer)$")
    college_id: int | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


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
