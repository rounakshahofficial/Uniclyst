"""User accounts and JWT revocation."""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from ..db.session import Base
from .base import utcnow


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),
                      UniqueConstraint("username", name="uq_users_username"))

    id = Column(Integer, primary_key=True)
    username = Column(String(64), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(120), nullable=False)
    # student | organizer | reviewer | admin
    role = Column(String(20), nullable=False, default="student", index=True)
    college_id = Column(Integer, ForeignKey("colleges.id", ondelete="SET NULL"), nullable=True)

    # Onboarding / personal profile (distinct from organization profiles)
    bio = Column(Text, default="")
    interests = Column(JSON, default=list)
    skills = Column(JSON, default=list)          # free-form skill tags
    goals = Column(Text, default="")             # project goals & collaboration preferences
    links = Column(JSON, default=dict)           # {"website": ..., "linkedin": ...}

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    college = relationship("College", back_populates="users")
    memberships = relationship("CommunityMember", back_populates="user", cascade="all, delete-orphan")
    saved_communities = relationship("SavedCommunity", back_populates="user", cascade="all, delete-orphan")


class RevokedToken(Base):
    """Logout denylist for stateless JWTs."""

    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True)
    jti = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, default=utcnow)
