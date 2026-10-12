"""Community queries: filtering, full-text-ish search, serialization."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..models import Community, CommunitySkill, SavedCommunity
from ..schemas import (
    CommunityOut,
    CommunityMemberOut,
    DiscoverySourceOut,
    EventOut,
    ProjectOut,
    SkillAssignment,
)


def eager_options():
    return (
        selectinload(Community.college),
        selectinload(Community.members),
        selectinload(Community.community_skills).selectinload(CommunitySkill.skill),
        selectinload(Community.projects),
        selectinload(Community.events),
        selectinload(Community.sources),
    )


def get_community(db: Session, community_id: int) -> Community | None:
    return db.scalars(
        select(Community).options(*eager_options()).where(Community.id == community_id)
    ).first()


def search_communities(
    db: Session,
    *,
    q: str | None = None,
    college_id: int | None = None,
    city: str | None = None,
    category: str | None = None,
    skill: str | None = None,
    interest: str | None = None,
    verification: str | None = None,
    sort: str = "relevance",
    include_body: bool = True,
) -> list[Community]:
    stmt = select(Community).options(*eager_options())
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Community.name).like(like),
                func.lower(Community.description).like(like),
                func.lower(Community.category).like(like),
            )
        )
    if college_id:
        stmt = stmt.where(Community.college_id == college_id)
    if verification:
        stmt = stmt.where(Community.verification_status == verification)
    if category:
        stmt = stmt.where(func.lower(Community.category) == category.lower())

    if sort == "updated":
        stmt = stmt.order_by(Community.updated_at.desc())
    elif sort == "confidence":
        stmt = stmt.order_by(Community.confidence.desc())
    else:
        stmt = stmt.order_by(Community.name)

    rows = db.scalars(stmt).all()
    result = []
    for c in rows:
        if city and (not c.college or c.college.city.lower() != city.lower()):
            continue
        if interest:
            tags = [t.lower() for t in (c.interests or [])]
            if interest.lower() not in tags:
                continue
        if skill:
            names = [a.skill.name.lower() for a in c.community_skills]
            if skill.lower() not in names:
                continue
        if q and include_body:
            # Broader match: skill names too
            ql = q.lower()
            skill_names = [a.skill.name.lower() for a in c.community_skills]
            college_name = (c.college.name if c.college else "").lower()
            in_name_desc = ql in (c.name + " " + c.description + " " + c.category).lower()
            if not (in_name_desc or any(ql in s for s in skill_names) or ql in college_name):
                continue
        result.append(c)
    return result


def community_to_out(
    community: Community,
    saved_ids: set[int] | None = None,
) -> CommunityOut:
    out = CommunityOut.model_validate(community)
    out.college_name = community.college.name if community.college else None
    out.college_short = community.college.short_name if community.college else None
    out.city = community.college.city if community.college else None
    out.skills = [
        SkillAssignment(name=a.skill.name, kind=a.kind) for a in community.community_skills
    ]
    out.members = [
        CommunityMemberOut(
            user_id=m.user_id,
            username=m.user.username if m.user else "",
            full_name=m.user.full_name if m.user else "",
            role=m.role,
        )
        for m in community.members
    ]
    out.projects = [ProjectOut.model_validate(p) for p in community.projects]
    events = sorted(community.events, key=lambda e: e.starts_at)
    out.events = []
    for ev in events:
        e = EventOut.model_validate(ev)
        e.community_name = community.name
        out.events.append(e)
    out.sources = [DiscoverySourceOut.model_validate(s) for s in community.sources]
    out.saved = bool(saved_ids and community.id in saved_ids)
    return out


def saved_community_ids(db: Session, user_id: int | None) -> set[int]:
    if not user_id:
        return set()
    return set(
        db.scalars(
            select(SavedCommunity.community_id).where(SavedCommunity.user_id == user_id)
        ).all()
    )
