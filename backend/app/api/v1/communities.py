"""Communities API: search, profiles, CRUD, membership.

Permissions are enforced here on the backend (never only in the frontend):
  - create:      any authenticated user (organizer role gets organizer membership)
  - update:      community organizers/admins, platform reviewers, or the creator
  - verification_status: platform reviewers only
  - delete:      platform reviewers/admins or the creator
"""

import re

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.errors import AppError
from ...core.security import get_current_user, get_optional_user, require_role
from ...db.session import get_db
from ...models import College, Community, CommunityMember, CommunitySkill, SavedCommunity, Skill, User
from ...repositories.communities import (
    community_to_out,
    get_community,
    saved_community_ids,
    search_communities,
)
from ...schemas import CommunityCreate, CommunityOut, CommunityUpdate, Page, SkillAssignment, make_page

router = APIRouter(prefix="/communities", tags=["communities"])


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:220] or "community"


def _unique_slug(db: Session, name: str) -> str:
    base = _slugify(name)
    slug = base
    n = 2
    while db.scalars(select(Community).where(Community.slug == slug)).first():
        slug = f"{base}-{n}"
        n += 1
    return slug


def _set_skills(db: Session, community: Community, skills: list[SkillAssignment]) -> None:
    for existing in list(community.community_skills):
        db.delete(existing)
    db.flush()
    for s in skills:
        skill = db.scalars(select(Skill).where(func.lower(Skill.name) == s.name.lower())).first()
        if skill is None:
            skill = Skill(name=s.name.strip().title(), category="General")
            db.add(skill)
            db.flush()
        db.add(CommunitySkill(community_id=community.id, skill_id=skill.id, kind=s.kind))


def _can_manage(user: User, community: Community, db: Session) -> bool:
    if user.role in ("reviewer", "admin"):
        return True
    if community.created_by == user.id:
        return True
    membership = db.scalars(
        select(CommunityMember).where(
            CommunityMember.community_id == community.id,
            CommunityMember.user_id == user.id,
        )
    ).first()
    return membership is not None and membership.role in ("organizer", "admin")


@router.get("", response_model=Page[CommunityOut])
def list_communities(
    q: str | None = Query(None),
    college_id: int | None = Query(None),
    city: str | None = Query(None),
    category: str | None = Query(None),
    skill: str | None = Query(None),
    interest: str | None = Query(None),
    verification: str | None = Query(None),
    sort: str = Query("relevance", pattern=r"^(relevance|updated|confidence)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    rows = search_communities(
        db,
        q=q,
        college_id=college_id,
        city=city,
        category=category,
        skill=skill,
        interest=interest,
        verification=verification,
        sort=sort,
    )
    total = len(rows)
    window = rows[(page - 1) * page_size : page * page_size]
    saved = saved_community_ids(db, user.id if user else None)
    items = [community_to_out(c, saved) for c in window]
    return make_page(items, total, page, page_size)


@router.get("/search", response_model=Page[CommunityOut])
def search(
    q: str = Query("", min_length=0),
    city: str | None = Query(None),
    skill: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """Search across community name, description, college, and skills."""
    rows = search_communities(db, q=q or None, city=city, skill=skill, include_body=True)
    total = len(rows)
    window = rows[(page - 1) * page_size : page * page_size]
    saved = saved_community_ids(db, user.id if user else None)
    return make_page([community_to_out(c, saved) for c in window], total, page, page_size)


@router.post("", response_model=CommunityOut, status_code=201)
def create_community(
    req: CommunityCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if db.get(College, req.college_id) is None:
        raise AppError(404, "not_found", "College not found")
    community = Community(
        name=req.name,
        slug=_unique_slug(db, req.name),
        college_id=req.college_id,
        description=req.description,
        category=req.category,
        interests=req.interests,
        website=req.website,
        social_links=req.social_links,
        created_by=user.id,
        verification_status="discovered",  # never auto-verified
        confidence=45.0,
    )
    db.add(community)
    db.flush()
    _set_skills(db, community, req.skills)
    db.add(CommunityMember(community_id=community.id, user_id=user.id, role="organizer"))
    # Controlled organizer onboarding: a student who creates a community
    # becomes a platform organizer (still cannot grant roles to others).
    if user.role == "student":
        user.role = "organizer"
        db.add(user)
    db.commit()
    community = get_community(db, community.id)
    saved = saved_community_ids(db, user.id)
    return community_to_out(community, saved)


@router.get("/{community_id}", response_model=CommunityOut)
def get_community_profile(
    community_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    community = get_community(db, community_id)
    if community is None:
        raise AppError(404, "not_found", "Community not found")
    saved = saved_community_ids(db, user.id if user else None)
    return community_to_out(community, saved)


@router.patch("/{community_id}", response_model=CommunityOut)
def update_community(
    community_id: int,
    req: CommunityUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    community = get_community(db, community_id)
    if community is None:
        raise AppError(404, "not_found", "Community not found")
    if not _can_manage(user, community, db):
        raise AppError(403, "forbidden", "Only community organizers or reviewers can edit this profile")

    data = req.model_dump(exclude_unset=True)
    if "verification_status" in data:
        if user.role not in ("reviewer", "admin"):
            raise AppError(403, "forbidden", "Only reviewers can change verification status")
        if data["verification_status"] not in {"discovered", "reviewed", "verified"}:
            raise AppError(422, "validation_error", "Invalid verification status")
    if "skills" in data:
        _set_skills(db, community, req.skills or [])
        data.pop("skills")
    for key, value in data.items():
        setattr(community, key, value)
    db.add(community)
    db.commit()
    community = get_community(db, community_id)
    saved = saved_community_ids(db, user.id)
    return community_to_out(community, saved)


@router.delete("/{community_id}", status_code=204)
def delete_community(
    community_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    community = get_community(db, community_id)
    if community is None:
        raise AppError(404, "not_found", "Community not found")
    if user.role not in ("reviewer", "admin") and community.created_by != user.id:
        raise AppError(403, "forbidden", "Only the creator or a reviewer can delete this community")
    db.delete(community)
    db.commit()
    return None


# ---------- Membership ----------

@router.post("/{community_id}/join", status_code=201)
def join_community(
    community_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    community = db.get(Community, community_id)
    if community is None:
        raise AppError(404, "not_found", "Community not found")
    existing = db.scalars(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == user.id,
        )
    ).first()
    if existing:
        return {"joined": True, "role": existing.role, "already_member": True}
    db.add(CommunityMember(community_id=community_id, user_id=user.id, role="member"))
    db.commit()
    return {"joined": True, "role": "member", "already_member": False}


@router.delete("/{community_id}/leave", status_code=204)
def leave_community(
    community_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == user.id,
        )
    ).all()
    for row in rows:
        db.delete(row)
    db.commit()
    return None
