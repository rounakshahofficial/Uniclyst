"""Admin-only user administration.

Reviewer and admin roles are NEVER granted through public registration.
They can only be assigned here by an existing administrator (the demo `admin`
seed account provisions reviewers), or directly by an operator with DB access.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.errors import AppError
from ...core.security import require_role
from ...db.session import get_db
from ...models import User
from ...schemas import RoleUpdateRequest, UserOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users/{user_id}/role", response_model=UserOut)
def set_user_role(
    user_id: int,
    req: RoleUpdateRequest,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "not_found", "User not found")
    if user.id == admin.id and req.role != "admin":
        raise AppError(400, "bad_request", "Administrators cannot demote themselves")
    user.role = req.role
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(_admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.id)).all()
