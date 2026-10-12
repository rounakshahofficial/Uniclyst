"""Colleges API."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.errors import AppError
from ...core.security import get_optional_user, require_role
from ...db.session import get_db
from ...models import College, Community, User
from ...schemas import CollegeCreate, CollegeOut, Page, make_page

router = APIRouter(prefix="/colleges", tags=["colleges"])


def _to_out(college: College, count: int = 0) -> CollegeOut:
    out = CollegeOut.model_validate(college)
    out.community_count = count
    return out


@router.get("", response_model=Page[CollegeOut])
def list_colleges(
    q: str | None = Query(None),
    city: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User | None = Depends(get_optional_user),
):
    counts = dict(
        db.execute(
            select(Community.college_id, func.count(Community.id)).group_by(Community.college_id)
        ).all()
    )
    stmt = select(College)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(College.name).like(like) | func.lower(College.short_name).like(like))
    if city:
        stmt = stmt.where(func.lower(College.city) == city.lower())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(College.name).offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = [_to_out(c, counts.get(c.id, 0)) for c in rows]
    return make_page(items, total, page, page_size)


@router.post("", response_model=CollegeOut, status_code=201)
def create_college(
    req: CollegeCreate,
    _user: User = Depends(require_role("organizer", "reviewer", "admin")),
    db: Session = Depends(get_db),
):
    existing = db.scalars(
        select(College).where(func.lower(College.short_name) == req.short_name.lower())
    ).first()
    if existing:
        raise AppError(409, "already_exists", "A college with this short name already exists")
    college = College(**req.model_dump())
    db.add(college)
    db.commit()
    db.refresh(college)
    return _to_out(college, 0)
