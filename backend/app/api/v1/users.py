"""User profile + onboarding + saved communities."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.errors import AppError
from ...core.security import get_current_user
from ...db.session import get_db
from ...models import College, Community, SavedCommunity, User
from ...repositories.communities import community_to_out, saved_community_ids
from ...schemas import CommunityOut, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(
    req: UserUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Onboarding: institution, interests, skills, goals, links."""
    if req.college_id is not None and db.get(College, req.college_id) is None:
        raise AppError(404, "not_found", "College not found")
    data = req.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(user, key, value)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me/saved", response_model=list[CommunityOut])
def list_saved(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Community)
        .join(SavedCommunity, SavedCommunity.community_id == Community.id)
        .where(SavedCommunity.user_id == user.id)
        .order_by(SavedCommunity.created_at.desc())
    ).scalars().all()
    saved = saved_community_ids(db, user.id)
    return [community_to_out(c, saved) for c in rows]


@router.post("/me/saved/{community_id}", status_code=201)
def save_community(
    community_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if db.get(Community, community_id) is None:
        raise AppError(404, "not_found", "Community not found")
    existing = db.scalars(
        select(SavedCommunity).where(
            SavedCommunity.user_id == user.id,
            SavedCommunity.community_id == community_id,
        )
    ).first()
    if existing is None:
        db.add(SavedCommunity(user_id=user.id, community_id=community_id))
        db.commit()
    return {"saved": True, "community_id": community_id}


@router.delete("/me/saved/{community_id}", status_code=204)
def unsave_community(
    community_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(SavedCommunity).where(
            SavedCommunity.user_id == user.id,
            SavedCommunity.community_id == community_id,
        )
    ).all()
    for row in rows:
        db.delete(row)
    db.commit()
    return None
