"""Communities (student clubs / organizations) and their relationships."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from ..db.session import Base
from .base import utcnow


class Community(Base):
    __tablename__ = "communities"
    __table_args__ = (UniqueConstraint("slug", name="uq_communities_slug"),)

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    slug = Column(String(220), nullable=False)
    college_id = Column(Integer, ForeignKey("colleges.id", ondelete="RESTRICT"), nullable=False, index=True)
    description = Column(Text, default="")
    category = Column(String(80), default="Technical")  # Technical|Cultural|Entrepreneurship|Research|Other
    interests = Column(JSON, default=list)
    website = Column(String(255))
    social_links = Column(JSON, default=dict)

    # Trust & activity signals (never auto-verified)
    verification_status = Column(String(20), default="discovered", index=True)  # discovered|reviewed|verified
    confidence = Column(Float, default=0.0)   # transparent 0-100 heuristic, not a probability
    last_checked_at = Column(DateTime, default=utcnow)
    is_demo = Column(Integer, default=0)      # 1 = clearly labeled seed/demo data

    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    college = relationship("College", back_populates="communities")
    members = relationship("CommunityMember", back_populates="community", cascade="all, delete-orphan")
    community_skills = relationship("CommunitySkill", back_populates="community", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="community", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="community", cascade="all, delete-orphan")
    sources = relationship("DiscoverySource", back_populates="community", cascade="all, delete-orphan")


class CommunityMember(Base):
    """Membership with a role. Distinct from the organization profile itself."""

    __tablename__ = "community_members"
    __table_args__ = (UniqueConstraint("user_id", "community_id", name="uq_community_member"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    community_id = Column(Integer, ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    # member | organizer | admin
    role = Column(String(20), nullable=False, default="member")
    joined_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="memberships")
    community = relationship("Community", back_populates="members")


class CommunitySkill(Base):
    """Many-to-many skills with intent: 'offers' (capability) or 'seeks' (looking for)."""

    __tablename__ = "community_skills"
    __table_args__ = (UniqueConstraint("community_id", "skill_id", "kind", name="uq_community_skill"),)

    id = Column(Integer, primary_key=True)
    community_id = Column(Integer, ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(10), nullable=False, default="offers")  # offers|seeks

    community = relationship("Community", back_populates="community_skills")
    skill = relationship("Skill", back_populates="community_skills")


class SavedCommunity(Base):
    __tablename__ = "saved_communities"
    __table_args__ = (UniqueConstraint("user_id", "community_id", name="uq_saved_community"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    community_id = Column(Integer, ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="saved_communities")
    community = relationship("Community")
