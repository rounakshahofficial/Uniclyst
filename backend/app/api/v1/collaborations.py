"""Collaboration workflow API.

Flow: proposal → accept | reject | withdraw → shared workspace + milestones.

Authorization (enforced here, not just in the frontend):
  - create:      user must organize (or lead) the requesting community
  - accept/reject: organizers of the recipient community
  - withdraw:    the requesting user or organizers of the requesting community
  - workspace:   only members of either side (participants) can view or modify

A partnership exists ONLY after acceptance — nothing is claimed before that.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ...core.errors import AppError
from ...core.security import get_current_user
from ...db.session import get_db
from ...models import (
    Collaboration,
    CollaborationMember,
    CollaborationRequest,
    Community,
    CommunityMember,
    Milestone,
    User,
)
from ...schemas.collaboration import (
    CollaborationMemberOut,
    CollaborationOut,
    CollaborationRequestAction,
    CollaborationRequestCreate,
    CollaborationRequestOut,
    CollaborationUpdate,
    MilestoneCreate,
    MilestoneOut,
    MilestoneUpdate,
)

router = APIRouter(tags=["collaborations"])


def _organizes(user: User, community_id: int, db: Session) -> bool:
    if user.role in ("admin", "reviewer"):
        return True
    m = db.scalars(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == user.id,
        )
    ).first()
    return m is not None and m.role in ("organizer", "admin")


def _request_out(req: CollaborationRequest, viewer: User, db: Session) -> CollaborationRequestOut:
    out = CollaborationRequestOut.model_validate(req)
    out.requester_community_name = req.requester_community.name if req.requester_community else None
    out.target_community_id = req.recipient_community_id
    out.target_community_name = req.recipient_community.name if req.recipient_community else None
    out.direction = "outgoing" if _organizes(viewer, req.requester_community_id, db) else "incoming"
    return out


def _can_view_request(user: User, req: CollaborationRequest, db: Session) -> bool:
    return _organizes(user, req.requester_community_id, db) or _organizes(user, req.recipient_community_id, db)


def _collab_out(collab: Collaboration) -> CollaborationOut:
    out = CollaborationOut.model_validate(collab)
    req = collab.request
    if req is not None:
        out.requester_community_id = req.requester_community_id
        out.target_community_id = req.recipient_community_id
        out.requester_community_name = req.requester_community.name if req.requester_community else None
        out.target_community_name = req.recipient_community.name if req.recipient_community else None
    out.members = []
    for m in collab.members:
        out.members.append(CollaborationMemberOut(
            user_id=m.user_id,
            username=m.user.username if m.user else "",
            full_name=m.user.full_name if m.user else "",
            community_id=m.community_id,
            community_name=m.community.name if m.community else None,
            role=m.role,
        ))
    out.milestones = sorted(
        [MilestoneOut.model_validate(ms) for ms in collab.milestones],
        key=lambda ms: (ms.order_index, ms.id),
    )
    return out


def _can_view_collab(user: User, collab: Collaboration, db: Session) -> bool:
    if any(m.user_id == user.id for m in collab.members):
        return True
    if collab.request is not None:
        return _can_view_request(user, collab.request, db)
    return False


# ---------------------------------------------------------------------------
# Collaboration requests
# ---------------------------------------------------------------------------

@router.post("/collaboration-requests", response_model=CollaborationRequestOut, status_code=201)
def create_request(
    req: CollaborationRequestCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.requester_community_id == req.target_community_id:
        raise AppError(422, "validation_error", "A community cannot collaborate with itself")
    requester = db.get(Community, req.requester_community_id)
    target = db.get(Community, req.target_community_id)
    if requester is None or target is None:
        raise AppError(404, "not_found", "Community not found")
    if not _organizes(user, req.requester_community_id, db):
        raise AppError(403, "forbidden", "Only organizers of the requesting community can send proposals")

    # No duplicate pending requests between the same pair
    pending = db.scalars(
        select(CollaborationRequest).where(
            CollaborationRequest.requester_community_id == req.requester_community_id,
            CollaborationRequest.recipient_community_id == req.target_community_id,
            CollaborationRequest.status == "pending",
        )
    ).first()
    if pending:
        raise AppError(409, "already_exists", "A pending proposal already exists between these communities")

    row = CollaborationRequest(
        requester_community_id=req.requester_community_id,
        requester_user_id=user.id,
        recipient_community_id=req.target_community_id,
        title=req.title,
        goal=req.goal,
        message=req.message,
        needed_skills=req.needed_skills,
        proposed_timeline=req.proposed_timeline,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _request_out(row, user, db)


@router.get("/collaboration-requests")
def list_requests(
    direction: str = Query("all", pattern=r"^(all|incoming|outgoing)$"),
    status: str | None = Query(None, pattern=r"^(pending|accepted|rejected|withdrawn)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.scalars(
        select(CollaborationRequest).order_by(CollaborationRequest.created_at.desc())
    ).all()
    items = []
    for row in rows:
        if not _can_view_request(user, row, db):
            continue
        out = _request_out(row, user, db)
        if direction != "all" and out.direction != direction:
            continue
        if status and out.status != status:
            continue
        items.append(out)
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 1, "pages": 1}


@router.get("/collaboration-requests/{request_id}", response_model=CollaborationRequestOut)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.get(CollaborationRequest, request_id)
    if row is None:
        raise AppError(404, "not_found", "Collaboration request not found")
    if not _can_view_request(user, row, db):
        raise AppError(403, "forbidden", "Only members of the involved communities can view this proposal")
    return _request_out(row, user, db)


@router.patch("/collaboration-requests/{request_id}", response_model=CollaborationRequestOut)
def act_on_request(
    request_id: int,
    action: CollaborationRequestAction,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.get(CollaborationRequest, request_id)
    if row is None:
        raise AppError(404, "not_found", "Collaboration request not found")
    if row.status != "pending":
        raise AppError(409, "conflict", f"Request is already {row.status}")

    if action.action in ("accept", "reject"):
        if not _organizes(user, row.recipient_community_id, db):
            raise AppError(403, "forbidden", "Only organizers of the recipient community can respond")
    elif action.action == "withdraw":
        is_author = row.requester_user_id == user.id
        if not (is_author or _organizes(user, row.requester_community_id, db)):
            raise AppError(403, "forbidden", "Only the author or requester-community organizers can withdraw")

    row.status = {"accept": "accepted", "reject": "rejected", "withdraw": "withdrawn"}[action.action]
    row.response_note = action.response_note
    row.responded_at = datetime.now(timezone.utc)
    db.add(row)

    if action.action == "accept":
        collab = Collaboration(
            request_id=row.id,
            title=row.title,
            goal=row.goal,
            status="active",
        )
        db.add(collab)
        db.flush()
        # Participants: the proposing user and the accepting user, on each side
        if row.requester_user_id:
            db.add(CollaborationMember(
                collaboration_id=collab.id, user_id=row.requester_user_id,
                community_id=row.requester_community_id, role="lead",
            ))
        db.add(CollaborationMember(
            collaboration_id=collab.id, user_id=user.id,
            community_id=row.recipient_community_id, role="lead",
        ))
        # Starter milestone so the workspace is actionable immediately
        db.add(Milestone(collaboration_id=collab.id, title="Kickoff: agree scope and roles",
                         description="Confirm the shared goal, responsibilities and timeline.",
                         order_index=0))

    db.commit()
    db.refresh(row)
    return _request_out(row, user, db)


# ---------------------------------------------------------------------------
# Collaboration workspaces
# ---------------------------------------------------------------------------

@router.get("/collaborations")
def list_collaborations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.scalars(select(Collaboration).order_by(Collaboration.started_at.desc())).all()
    items = [_collab_out(c) for c in rows if _can_view_collab(user, c, db)]
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 1, "pages": 1}


@router.get("/collaborations/{collaboration_id}", response_model=CollaborationOut)
def get_collaboration(
    collaboration_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    collab = db.get(Collaboration, collaboration_id)
    if collab is None:
        raise AppError(404, "not_found", "Collaboration not found")
    if not _can_view_collab(user, collab, db):
        raise AppError(403, "forbidden", "Only participants can view this workspace")
    return _collab_out(collab)


@router.patch("/collaborations/{collaboration_id}", response_model=CollaborationOut)
def update_collaboration(
    collaboration_id: int,
    req: CollaborationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    collab = db.get(Collaboration, collaboration_id)
    if collab is None:
        raise AppError(404, "not_found", "Collaboration not found")
    if not _can_view_collab(user, collab, db):
        raise AppError(403, "forbidden", "Only participants can update this workspace")
    collab.status = req.status
    if req.summary:
        collab.summary = req.summary
    if req.status == "completed":
        collab.completed_at = datetime.now(timezone.utc)
    db.add(collab)
    db.commit()
    db.refresh(collab)
    return _collab_out(collab)


@router.post("/collaborations/{collaboration_id}/milestones", response_model=MilestoneOut, status_code=201)
def add_milestone(
    collaboration_id: int,
    req: MilestoneCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    collab = db.get(Collaboration, collaboration_id)
    if collab is None:
        raise AppError(404, "not_found", "Collaboration not found")
    if not _can_view_collab(user, collab, db):
        raise AppError(403, "forbidden", "Only participants can add milestones")
    order_index = len(collab.milestones)
    ms = Milestone(collaboration_id=collaboration_id, title=req.title,
                   description=req.description, due_date=req.due_date, order_index=order_index)
    db.add(ms)
    db.commit()
    db.refresh(ms)
    return MilestoneOut.model_validate(ms)


@router.patch("/milestones/{milestone_id}", response_model=MilestoneOut)
def update_milestone(
    milestone_id: int,
    req: MilestoneUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ms = db.get(Milestone, milestone_id)
    if ms is None:
        raise AppError(404, "not_found", "Milestone not found")
    collab = db.get(Collaboration, ms.collaboration_id)
    if collab is None or not _can_view_collab(user, collab, db):
        raise AppError(403, "forbidden", "Only participants can update milestones")
    ms.status = req.status
    db.add(ms)
    db.commit()
    db.refresh(ms)
    return MilestoneOut.model_validate(ms)
