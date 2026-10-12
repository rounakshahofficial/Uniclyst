"""Web-discovery bookkeeping: evidence records and scout jobs.

Nothing discovered on the public web is automatically true. Every extracted
record keeps its source URL, retrieval timestamps, and an explicit review
status (discovered -> reviewed -> verified) promoted only by humans.
"""

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..db.session import Base
from .base import utcnow


class DiscoveryJob(Base):
    """One run of the Community Scout (user-triggered in the MVP)."""

    __tablename__ = "discovery_jobs"

    id = Column(Integer, primary_key=True)
    query = Column(String(400), nullable=False)
    region = Column(String(120), default="")
    interests = Column(JSON, default=list)
    # pending | running | completed | failed
    status = Column(String(20), nullable=False, default="pending", index=True)
    # live (TinyFish) | demo (seeded corpus)
    mode = Column(String(10), default="demo")
    result_count = Column(Integer, default=0)
    error = Column(Text, default="")
    notes = Column(JSON, default=list)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)

    sources = relationship("DiscoverySource", back_populates="job")


class DiscoverySource(Base):
    """Evidence record for a discovered community/event claim."""

    __tablename__ = "discovery_sources"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("discovery_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    # Evidence survives community deletion (SET NULL) so reviewers can audit it.
    community_id = Column(Integer, ForeignKey("communities.id", ondelete="SET NULL"), nullable=True, index=True)

    source_url = Column(String(500), nullable=False, index=True)
    source_title = Column(String(255), default="")
    evidence_excerpt = Column(Text, default="")
    retrieved_at = Column(DateTime, default=utcnow)
    last_checked_at = Column(DateTime, default=utcnow)

    # discovered | reviewed | verified — explicit human-gated promotion rules
    review_status = Column(String(20), default="discovered", index=True)
    confidence = Column(Float, default=0.0)  # transparent heuristic, NOT a calibrated probability
    review_note = Column(Text, default="")
    # scout (TinyFish) | seed (demo corpus) | manual
    origin = Column(String(20), default="scout")

    job = relationship("DiscoveryJob", back_populates="sources")
    community = relationship("Community", back_populates="sources")
