"""Skills catalog."""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from ..db.session import Base


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False, unique=True, index=True)
    category = Column(String(80), nullable=False, default="General")

    community_skills = relationship("CommunitySkill", back_populates="skill", cascade="all, delete-orphan")
