"""Auth routes: register, login, logout (token revocation)."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.errors import AppError
from ...core.security import (
    bearer_scheme,
    create_access_token,
    decode_token,
    get_current_user,
    hash_password,
    revoke_token,
    verify_password,
)
from ...db.session import get_db
from ...models import College, User
from ...schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
<<<<<<< HEAD
    """Public registration — always creates a `student` account.

    Role escalation is impossible here: the schema forbids a `role` field
    (see schemas/auth.py), and `user.role` is hardcoded to "student".
    """
=======
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
    existing = db.scalars(
        select(User).where((User.username == req.username) | (User.email == req.email))
    ).first()
    if existing:
        raise AppError(409, "already_exists", "Username or email already taken")
    if req.college_id is not None and db.get(College, req.college_id) is None:
        raise AppError(404, "not_found", "College not found")

    user = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
<<<<<<< HEAD
        role="student",  # SECURITY: never taken from client input
=======
        role=req.role,
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
        college_id=req.college_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token, _jti, _exp = create_access_token(user.id, user.username, user.role)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalars(select(User).where(User.username == req.username)).first()
    if user is None or not verify_password(req.password, user.password_hash):
        raise AppError(401, "invalid_credentials", "Invalid username or password")
    token, _jti, _exp = create_access_token(user.id, user.username, user.role)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke the presented access token (JWT denylist) so it cannot be reused."""
    if credentials is not None:
        try:
            payload = decode_token(credentials.credentials)
            revoke_token(db, payload)
        except Exception:  # noqa: BLE001 — logout must not fail on a bad token
            pass
    return None
