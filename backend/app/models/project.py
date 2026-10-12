"""Projects owned by communities — what they are building and what they need."""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..db.session import Base
from .base import utcnow


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    community_id = Column(Integer, ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    # planned | active | completed | shelved
    status = Column(String(20), nullable=False, default="planned")
    needed_skills = Column(JSON, default=list)   # what collaborators should bring
    links = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    community = relationship("Community", back_populates="projects")
