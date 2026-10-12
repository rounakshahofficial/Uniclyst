"""Collaboration workflow: requests -> accepted collaborations -> milestones.

A partnership exists only after the recipient explicitly accepts. The platform
never claims a collaboration before that happens.
"""

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from ..db.session import Base
from .base import utcnow


class CollaborationRequest(Base):
    __tablename__ = "collaboration_requests"

    id = Column(Integer, primary_key=True)
    requester_community_id = Column(
        Integer, ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requester_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    recipient_community_id = Column(
        Integer, ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(200), nullable=False)
    goal = Column(String(255), default="")
    message = Column(Text, default="")
    needed_skills = Column(JSON, default=list)
    proposed_timeline = Column(String(200), default="")
    # pending | accepted | rejected | withdrawn
    status = Column(String(20), nullable=False, default="pending", index=True)
    response_note = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow, index=True)
    responded_at = Column(DateTime)

    requester_community = relationship("Community", foreign_keys=[requester_community_id])
    recipient_community = relationship("Community", foreign_keys=[recipient_community_id])
    requester_user = relationship("User")
    collaboration = relationship("Collaboration", back_populates="request", uselist=False)


class Collaboration(Base):
    """Created only when a request is accepted. One per request."""

    __tablename__ = "collaborations"
    __table_args__ = (UniqueConstraint("request_id", name="uq_collaboration_request"),)

    id = Column(Integer, primary_key=True)
    request_id = Column(
        Integer, ForeignKey("collaboration_requests.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(200), nullable=False)
    goal = Column(String(255), default="")
    # active | completed | cancelled
    status = Column(String(20), nullable=False, default="active", index=True)
    summary = Column(Text, default="")
    started_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime)

    request = relationship("CollaborationRequest", back_populates="collaboration")
    members = relationship("CollaborationMember", back_populates="collaboration", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="collaboration", cascade="all, delete-orphan")


class CollaborationMember(Base):
    """Who participates in a collaboration, on which side."""

    __tablename__ = "collaboration_members"
    __table_args__ = (UniqueConstraint("collaboration_id", "user_id", name="uq_collaboration_member"),)

    id = Column(Integer, primary_key=True)
    collaboration_id = Column(
        Integer, ForeignKey("collaborations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    community_id = Column(Integer, ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    # lead | member
    role = Column(String(20), nullable=False, default="member")
    joined_at = Column(DateTime, default=utcnow)

    collaboration = relationship("Collaboration", back_populates="members")
    user = relationship("User")
    community = relationship("Community")


class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True)
    collaboration_id = Column(
        Integer, ForeignKey("collaborations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    due_date = Column(Date)
    # pending | reached
    status = Column(String(20), nullable=False, default="pending")
    order_index = Column(Integer, default=0)

    collaboration = relationship("Collaboration", back_populates="milestones")
