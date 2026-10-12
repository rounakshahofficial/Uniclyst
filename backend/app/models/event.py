"""Public events: hackathons, workshops, competitions, open calls."""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..db.session import Base
from .base import utcnow


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    community_id = Column(Integer, ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    category = Column(String(80), default="Hackathon")  # Hackathon|Workshop|Competition|Meetup|Other
    starts_at = Column(DateTime, nullable=False, index=True)
    ends_at = Column(DateTime)
    city = Column(String(80))
    is_online = Column(Integer, default=0)
    event_url = Column(String(255))
    # Source tracking: where this listing came from and when we last saw it
    source_url = Column(String(500))
    last_checked_at = Column(DateTime, default=utcnow)
    # upcoming | past | uncertain  (uncertain = conflicting/missing dates on source)
    listing_status = Column(String(20), default="upcoming")
    confidence = Column(Float, default=0.0)

    community = relationship("Community", back_populates="events")
