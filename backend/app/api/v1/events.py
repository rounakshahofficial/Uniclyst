"""Events API: public hackathons, workshops, competitions."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ...core.errors import AppError
from ...core.security import get_current_user, get_optional_user
from ...db.session import get_db
from ...models import Community, CommunityMember, Event, User
from ...schemas import EventCreate, EventOut, Page, make_page

router = APIRouter(prefix="/events", tags=["events"])


def _event_out(ev: Event) -> EventOut:
    out = EventOut.model_validate(ev)
    out.community_name = ev.community.name if ev.community else None
    return out


@router.get("", response_model=Page[EventOut])
def list_events(
    city: str | None = Query(None),
    community_id: int | None = Query(None),
    category: str | None = Query(None),
    upcoming_only: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User | None = Depends(get_optional_user),
):
    stmt = select(Event).options(selectinload(Event.community))
    if community_id:
        stmt = stmt.where(Event.community_id == community_id)
    if category:
        stmt = stmt.where(func.lower(Event.category) == category.lower())
    if upcoming_only:
        stmt = stmt.where(Event.starts_at >= datetime.now(timezone.utc))
    if city:
        stmt = stmt.where(func.lower(Event.city) == city.lower())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Event.starts_at).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return make_page([_event_out(e) for e in rows], total, page, page_size)


@router.post("", response_model=EventOut, status_code=201)
def create_event(
    req: EventCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    community = db.get(Community, req.community_id)
    if community is None:
        raise AppError(404, "not_found", "Community not found")
    membership = db.scalars(
        select(CommunityMember).where(
            CommunityMember.community_id == community.id,
            CommunityMember.user_id == user.id,
        )
    ).first()
    if user.role not in ("reviewer", "admin") and (
        membership is None or membership.role not in ("organizer", "admin")
    ):
        raise AppError(403, "forbidden", "Only community organizers can create events")
    now = datetime.now(timezone.utc)
    starts = req.starts_at if req.starts_at.tzinfo else req.starts_at.replace(tzinfo=timezone.utc)
    data = req.model_dump()
    data["is_online"] = 1 if req.is_online else 0
    data["listing_status"] = "past" if starts < now else "upcoming"
    data["confidence"] = 100.0  # organizer-entered data, not scraped
    ev = Event(**data)
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return _event_out(ev)
