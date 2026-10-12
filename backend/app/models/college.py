"""Colleges / institutions."""

from sqlalchemy import Column, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from ..db.session import Base


class College(Base):
    __tablename__ = "colleges"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    short_name = Column(String(40), nullable=False, unique=True, index=True)
    city = Column(String(80), nullable=False, index=True)
    region = Column(String(80), nullable=False, default="Delhi NCR")
    country = Column(String(80), nullable=False, default="India")
    website = Column(String(255))
    lat = Column(Float)
    lng = Column(Float)
    description = Column(Text, default="")

    communities = relationship("Community", back_populates="college")
    users = relationship("User", back_populates="college")
