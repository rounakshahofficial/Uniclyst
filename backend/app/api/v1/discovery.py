"""Discovery API: Community Scout jobs, evidence review, record import.

Endpoints (Discovery administration):
  POST   /api/v1/discovery/jobs              — start a discovery job (runs synchronously)
  GET    /api/v1/discovery/jobs              — list jobs
  GET    /api/v1/discovery/jobs/{id}         — job status + extracted records
  GET    /api/v1/discovery/sources           — evidence records (filter by status)
  PATCH  /api/v1/discovery/sources/{id}      — review: discovered → reviewed → verified (reviewer only)
  POST   /api/v1/discovery/sources/{id}/import — approve/correct an extracted record into the network

Safeguards: nothing imported is auto-verified; demo-mode results are labeled
origin=seed; evidence rows keep source URL + timestamps; reviewers control
promotion.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.errors import AppError
from ...core.security import get_current_user, require_role
from ...db.session import get_db
from ...models import (
    College,
    Community,
    CommunitySkill,
    DiscoveryJob,
    DiscoverySource,
    Skill,
    User,
)
from ...schemas import DiscoverySourceOut
from ...schemas.discovery import (
    DiscoveryJobCreate,
    DiscoveryJobDetail,
    DiscoveryJobOut,
    ScoutRunResponse,
    SourceImportRequest,
    SourceReviewRequest,
)
from ...services.tinyfish_scout import run_scout

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.post("/jobs", response_model=ScoutRunResponse, status_code=201)
def create_job(
    req: DiscoveryJobCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a discovery job. Runs the scout synchronously (MVP); the job row
    records mode (live/demo), timestamps, notes, and every extracted record."""
    job = DiscoveryJob(
        query=req.query,
        region=req.region,
        interests=req.interests,
        status="running",
        created_by=user.id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()

    try:
        mode, candidates, raw_count, notes = run_scout(req.query, req.region, req.interests, db)
    except Exception as exc:  # noqa: BLE001 — job must record failures, not crash
        job.status = "failed"
        job.error = str(exc)[:2000]
        job.finished_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()
        raise AppError(502, "scout_failed", f"Discovery job failed: {str(exc)[:200]}")

    job.mode = mode
    job.notes = notes
    job.result_count = len(candidates)
    job.status = "completed"
    job.finished_at = datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)
    for cand in candidates:
        db.add(DiscoverySource(
            job_id=job.id,
            community_id=cand.dedupe_match_org_id,
            source_url=cand.evidence[0].source_url if cand.evidence else "",
            source_title=cand.evidence[0].source_title if cand.evidence else "",
            evidence_excerpt=" | ".join(e.evidence_excerpt for e in cand.evidence),
            retrieved_at=now,
            last_checked_at=now,
            review_status="discovered",   # NEVER auto-verified
            confidence=cand.confidence,
            review_note=cand.missing_or_conflicting,
            origin="scout" if mode == "live" else "seed",  # demo data is labeled
            extracted=cand.to_dict(),
        ))
    db.add(job)
    db.commit()
    db.refresh(job)

    return ScoutRunResponse(
        job=DiscoveryJobOut.model_validate(job),
        candidates=[_candidate_out(c) for c in candidates],
    )


def _candidate_out(c) -> "ScoutCandidateOut":  # noqa: F821
    from ...schemas.discovery import ScoutCandidateOut

    return ScoutCandidateOut(
        organization_name=c.organization_name,
        college=c.college,
        city=c.city,
        interests=c.interests,
        skills=c.skills,
        official_url=c.official_url,
        event_names=c.event_names,
        confidence=c.confidence,
        verification_status=c.verification_status,
        missing_or_conflicting=c.missing_or_conflicting,
        dedupe_match_org_id=c.dedupe_match_org_id,
    )


@router.get("/jobs")
def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    total = db.scalar(select(func.count(DiscoveryJob.id))) or 0
    jobs = db.scalars(
        select(DiscoveryJob).order_by(DiscoveryJob.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    pages = (total + page_size - 1) // page_size or 1
    return {
        "items": [DiscoveryJobOut.model_validate(j) for j in jobs],
        "total": total, "page": page, "page_size": page_size, "pages": pages,
    }


@router.get("/jobs/{job_id}", response_model=DiscoveryJobDetail)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    job = db.get(DiscoveryJob, job_id)
    if job is None:
        raise AppError(404, "not_found", "Discovery job not found")
    detail = DiscoveryJobDetail.model_validate(job)
    detail.sources = [DiscoverySourceOut.model_validate(s) for s in job.sources]
    return detail


@router.get("/sources")
def list_sources(
    review_status: str | None = Query(None),
    job_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    stmt = select(DiscoverySource)
    if review_status:
        stmt = stmt.where(DiscoverySource.review_status == review_status)
    if job_id:
        stmt = stmt.where(DiscoverySource.job_id == job_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(DiscoverySource.retrieved_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    pages = (total + page_size - 1) // page_size or 1
    return {
        "items": [DiscoverySourceOut.model_validate(s) for s in rows],
        "total": total, "page": page, "page_size": page_size, "pages": pages,
    }


@router.patch("/sources/{source_id}", response_model=DiscoverySourceOut)
def review_source(
    source_id: int,
    req: SourceReviewRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Review an extracted record. Promotion to `verified` is reviewer/admin
    only — an accessible web page is never automatically verified truth."""
    source = db.get(DiscoverySource, source_id)
    if source is None:
        raise AppError(404, "not_found", "Discovery source not found")
    if req.review_status == "verified" and user.role not in ("reviewer", "admin"):
        raise AppError(403, "forbidden", "Only reviewers can promote a record to verified")
    if user.role not in ("reviewer", "admin") and req.review_status != source.review_status:
        raise AppError(403, "forbidden", "Only reviewers can change review status")
    source.review_status = req.review_status
    if req.review_note:
        source.review_note = req.review_note
    source.last_checked_at = datetime.now(timezone.utc)
    db.add(source)
    db.commit()
    db.refresh(source)
    return DiscoverySourceOut.model_validate(source)


@router.post("/sources/{source_id}/import", response_model=dict, status_code=201)
def import_source(
    source_id: int,
    req: SourceImportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve a discovered record into the network as a community.

    Creates (or attaches to) a community with verification_status='discovered'
    — importing evidence never makes a community verified.
    """
    source = db.get(DiscoverySource, source_id)
    if source is None:
        raise AppError(404, "not_found", "Discovery source not found")
    data = dict(source.extracted or {})
    if not data.get("organization_name"):
        raise AppError(422, "validation_error", "This source has no extracted record to import")

    name = req.name or data["organization_name"]

    # Attach evidence to an existing community when dedupe found one
    target_id = data.get("dedupe_match_org_id")
    if target_id and db.get(Community, target_id):
        source.community_id = target_id
        source.last_checked_at = datetime.now(timezone.utc)
        db.add(source)
        db.commit()
        return {"imported": True, "community_id": target_id, "mode": "attached_to_existing"}

    # Otherwise create a new community from the extracted record
    college_id = req.college_id
    if college_id is None:
        college_name = data.get("college") or "Unknown institution"
        college = db.scalars(
            select(College).where(func.lower(College.name) == college_name.lower())
        ).first()
        if college is None:
            college = College(
                name=college_name,
                short_name=(college_name[:35] or "UNK"),
                city=data.get("city") or "Delhi NCR",
                region="Delhi NCR",
            )
            db.add(college)
            db.flush()
        college_id = college.id
    elif db.get(College, college_id) is None:
        raise AppError(404, "not_found", "College not found")

    slug = "".join(ch if ch.isalnum() else "-" for ch in name.lower()).strip("-")[:220]
    base, slug_candidate, n = slug, slug, 2
    while db.scalars(select(Community).where(Community.slug == slug_candidate)).first():
        slug_candidate = f"{base}-{n}"
        n += 1

    community = Community(
        name=name,
        slug=slug_candidate,
        college_id=college_id,
        description=f"Discovered by Community Scout. Evidence: {source.source_url}",
        category="Technical",
        interests=data.get("interests") or [],
        website=data.get("official_url"),
        verification_status="discovered",   # imported evidence is NOT verification
        confidence=data.get("confidence") or 50.0,
        last_checked_at=datetime.now(timezone.utc),
        is_demo=1 if source.origin == "seed" else 0,
        created_by=user.id,
    )
    db.add(community)
    db.flush()
    for skill_name in (data.get("skills") or [])[:12]:
        skill = db.scalars(select(Skill).where(func.lower(Skill.name) == skill_name.lower())).first()
        if skill is None:
            skill = Skill(name=skill_name.title(), category="General")
            db.add(skill)
            db.flush()
        db.add(CommunitySkill(community_id=community.id, skill_id=skill.id, kind="offers"))
    source.community_id = community.id
    db.add(source)
    db.commit()
    return {"imported": True, "community_id": community.id, "mode": "created"}
