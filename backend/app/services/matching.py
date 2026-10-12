"""Explainable collaboration matching engine.

Pure, testable scoring logic — deliberately independent of FastAPI and the ORM.

Score (configurable weights, each component normalized 0-100):

    S = 0.25·I + 0.35·C + 0.25·G + 0.10·L + 0.05·A

    I = interest compatibility          (shared / adjacent interest tags)
    C = complementary skill coverage    (partner offers what the project needs)
    G = project goal alignment          (goal text vs their capabilities/projects)
    L = geographic feasibility          (same city > nearby > remote-OK)
    A = profile completeness & freshness (verification, sources, last-checked)

These weights are an initial configurable design choice — NOT experimentally
validated and NOT a trained machine-learning model. Each recommendation
returns component scores plus human-readable reasons so users understand why
it was suggested. Missing data degrades gracefully (neutral baseline +
uncertainty note) instead of unfairly penalizing thin profiles.

Designed so semantic embeddings can be added later if they measurably help.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

DEFAULT_WEIGHTS = {
    "interest": 0.25,
    "skills": 0.35,
    "goal": 0.25,
    "geography": 0.10,
    "profile": 0.05,
}

FORMULA = "S = 0.25·I + 0.35·C + 0.25·G + 0.10·L + 0.05·A"

# Adjacent-capability hints give partial credit: we want partners who can build
# together, not clones. E.g. an "ai" need is partly covered by "computer vision".
ADJACENT_TAGS = {
    "robotics": {"mechanical design", "electronics", "iot", "hardware", "embedded", "drones", "arduino", "ros"},
    "ai": {"computer vision", "machine learning", "data science", "deep learning", "generative ai", "python"},
    "machine learning": {"ai", "data science", "deep learning", "computer vision", "python"},
    "computer vision": {"ai", "machine learning", "deep learning", "python"},
    "design": {"ui/ux", "graphic design", "branding", "photography", "figma"},
    "ui/ux": {"design", "graphic design", "figma"},
    "entrepreneurship": {"marketing", "finance", "public relations", "events", "event management", "startups"},
    "cybersecurity": {"networking", "linux", "cryptography", "security"},
    "iot": {"embedded", "arduino", "hardware", "prototyping", "robotics"},
    "drones": {"robotics", "embedded", "mechanical design"},
    "data science": {"machine learning", "python", "ai"},
}

NEARBY_CITY_PAIRS = {
    frozenset({"delhi", "noida"}),
    frozenset({"delhi", "greater noida"}),
    frozenset({"delhi", "gurugram"}),
    frozenset({"delhi", "gurgaon"}),
    frozenset({"delhi", "ghaziabad"}),
    frozenset({"delhi", "faridabad"}),
    frozenset({"noida", "greater noida"}),
    frozenset({"noida", "gurugram"}),
    frozenset({"noida", "gurgaon"}),
    frozenset({"noida", "ghaziabad"}),
    frozenset({"gurugram", "faridabad"}),
    frozenset({"gurgaon", "faridabad"}),
}


def _norm(s: str) -> str:
    return s.strip().lower()


def _tokens(text: str) -> set[str]:
    return {t for t in "".join(
        ch.lower() if ch.isalnum() else " " for ch in (text or "")
    ).split() if len(t) > 2}


# ---------------------------------------------------------------------------
# Input dataclasses — built from ORM rows (or dicts) by the caller
# ---------------------------------------------------------------------------

@dataclass
class CommunityProfile:
    id: int
    name: str
    interests: list[str] = field(default_factory=list)
    offered_skills: list[str] = field(default_factory=list)
    sought_skills: list[str] = field(default_factory=list)
    project_titles: list[str] = field(default_factory=list)
    project_descriptions: list[str] = field(default_factory=list)
    city: str | None = None
    college_id: int | None = None
    verification_status: str = "discovered"
    confidence: float = 0.0
    description: str = ""
    website: str | None = None
    has_social_links: bool = False
    member_count: int = 0
    source_count: int = 0
    last_checked_at: datetime | None = None


@dataclass
class MatchRequirements:
    """What the requester needs from a partner."""

    needed_skills: list[str] = field(default_factory=list)
    goal: str = ""
    exclude_ids: list[int] = field(default_factory=list)
    min_score: float = 15.0
    limit: int = 8


@dataclass
class ComponentScore:
    interest: float
    skills: float
    goal: float
    geography: float
    profile: float

    @property
    def total(self) -> float:
        w = DEFAULT_WEIGHTS
        return round(
            w["interest"] * self.interest
            + w["skills"] * self.skills
            + w["goal"] * self.goal
            + w["geography"] * self.geography
            + w["profile"] * self.profile,
            1,
        )

    def as_dict(self) -> dict:
        return {
            "interest": self.interest,
            "skills": self.skills,
            "goal": self.goal,
            "geography": self.geography,
            "profile": self.profile,
            "total": self.total,
        }


@dataclass
class MatchResult:
    candidate: CommunityProfile
    score: ComponentScore
    reasons: list[str]
    strongest_factors: list[str]
    missing_skills: list[str]
    freshness: dict
    uncertainty: str | None = None


# ---------------------------------------------------------------------------
# Component scorers — each returns (score 0-100, explanation fragment)
# ---------------------------------------------------------------------------

def interest_score(req: CommunityProfile, cand: CommunityProfile, requirements: MatchRequirements) -> tuple[float, str]:
    """I — interest compatibility (shared + adjacent tags)."""
    want = {_norm(t) for t in req.interests} | {_norm(s) for s in requirements.needed_skills}
    have = {_norm(t) for t in cand.interests}
    if not want:
        return 50.0, "no interests specified on your profile — neutral interest baseline"
    if not have:
        return 35.0, "candidate lists no interests yet (thin profile — not heavily penalized)"
    shared = want & have
    adjacent = sum(
        1 for t in want
        for hint in (ADJACENT_TAGS.get(t, set()) & have)
    )
    raw = (len(shared) + 0.35 * min(adjacent, 3)) / len(want)
    score = round(min(1.0, raw) * 100, 1)
    parts = []
    if shared:
        parts.append(f"shared interests: {', '.join(sorted(shared))}")
    if adjacent:
        parts.append(f"{adjacent} adjacent capability tag(s)")
    return score, ("; ".join(parts) if parts else "no overlapping interest tags")


def skills_score(req: CommunityProfile, cand: CommunityProfile, requirements: MatchRequirements) -> tuple[float, list[str], str]:
    """C — complementary skill coverage of the project's needs.

    Returns (score, missing skill DISPLAY names, explanation).
    """
    needed_display = [s for s in requirements.needed_skills if s.strip()]
    if not needed_display:
        # Fall back to what the requester explicitly seeks.
        needed_display = [s for s in req.sought_skills if s.strip()]
    needed = {_norm(s) for s in needed_display}
    # Preserve human-readable casing in all outputs
    offer_display = { _norm(s): s for s in cand.offered_skills }
    needed_name = { _norm(s): s for s in needed_display }
    offers = set(offer_display)
    if not needed:
        return 55.0, [], "no required skills specified — neutral skills baseline"
    if not offers:
        return 35.0, sorted(needed_name.values()), "candidate lists no offered skills yet (thin profile — not heavily penalized)"
    covered = needed & offers
    missing = sorted(needed - offers)
    partial = 0
    for m in missing:
        adjacent_needed = ADJACENT_TAGS.get(m, set())
        if offers & adjacent_needed:
            partial += 1
    raw = (len(covered) + 0.5 * partial) / len(needed)
    score = round(min(1.0, raw) * 100, 1)
    if covered:
        desc = f"covers {', '.join(sorted(offer_display[c] for c in covered))}"
        if partial:
            desc += f"; partial coverage on {partial} more via adjacent skills"
    else:
        desc = "none of the required skills listed directly"
    return score, [needed_name[m] for m in missing], desc


def goal_score(req: CommunityProfile, cand: CommunityProfile, requirements: MatchRequirements) -> tuple[float, str]:
    """G — project goal alignment: goal text vs their interests/skills/projects."""
    goal = (requirements.goal or "").strip()
    if not goal:
        return 50.0, "no project goal stated — neutral goal baseline"
    goal_tokens = _tokens(goal)
    cand_tokens = (
        {_norm(t) for t in cand.interests}
        | {_norm(s) for s in cand.offered_skills}
        | _tokens(" ".join(cand.project_titles + cand.project_descriptions))
    )
    if not cand_tokens:
        return 35.0, "candidate has little profile text to compare goals against"
    overlap = goal_tokens & cand_tokens
    # multi-word skill phrases in the goal count strongly
    phrase_hits = [
        s for s in cand.offered_skills + cand.interests
        if len(_norm(s)) > 4 and _norm(s) in _norm(goal)
    ]
    raw = (len(overlap) + 2 * len(phrase_hits)) / max(len(goal_tokens), 3)
    score = round(min(1.0, raw) * 100, 1)
    if phrase_hits or overlap:
        bits = []
        if phrase_hits:
            bits.append(f"goal mentions capabilities they list ({', '.join(sorted(set(phrase_hits)) or '—')})")
        if overlap:
            bits.append(f"shared goal vocabulary: {', '.join(sorted(overlap)[:5])}")
        return score, "; ".join(bits)
    return score, "limited overlap between your goal wording and their profile"


NCR_CITIES = {"delhi", "noida", "greater noida", "gurugram", "gurgaon", "ghaziabad", "faridabad"}


def geography_score(req: CommunityProfile, cand: CommunityProfile) -> tuple[float, str]:
    """L — travel feasibility."""
    if req.college_id is not None and req.college_id == cand.college_id:
        return 100.0, "same campus — zero travel friction"
    a, b = _norm(req.city or ""), _norm(cand.city or "")
    if not a or not b:
        return 50.0, "location unclear — neutral geography score"
    if a == b:
        return 90.0, f"same city ({req.city}) — easy to meet in person"
    if frozenset({a, b}) in NEARBY_CITY_PAIRS:
        return 75.0, f"nearby NCR hubs ({req.city} ↔ {cand.city}) — practical day travel"
    if a in NCR_CITIES and b in NCR_CITIES:
        return 65.0, f"within the National Capital Region ({req.city} ↔ {cand.city})"
    return 30.0, f"different regions ({req.city} ↔ {cand.city}) — remote-first collaboration fits best"


def profile_score(cand: CommunityProfile, now: datetime | None = None) -> tuple[float, str]:
    """A — profile completeness & freshness (trust and activity signals)."""
    now = now or datetime.now(timezone.utc)
    verify_pts = {"discovered": 35, "reviewed": 65, "verified": 90}
    v = verify_pts.get(cand.verification_status, 35)
    pts = v * 0.5
    notes = [f"verification: {cand.verification_status}"]
    if cand.description:
        pts += 10
    if cand.website:
        pts += 8
    if cand.has_social_links:
        pts += 4
    if cand.offered_skills:
        pts += 4
    if cand.source_count:
        pts += min(8, cand.source_count * 3)
        notes.append(f"{cand.source_count} source record(s)")
    if cand.last_checked_at:
        last = cand.last_checked_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        age_days = (now - last).days
        if age_days <= 30:
            pts += 12
            notes.append(f"checked {age_days}d ago (fresh)")
        elif age_days <= 90:
            pts += 6
            notes.append(f"checked {age_days}d ago")
        else:
            notes.append(f"last checked {age_days}d ago (stale)")
    score = round(min(100.0, pts), 1)
    return score, "; ".join(notes)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def score_pair(req: CommunityProfile, cand: CommunityProfile, requirements: MatchRequirements) -> MatchResult:
    i, i_reason = interest_score(req, cand, requirements)
    c, missing, c_reason = skills_score(req, cand, requirements)
    g, g_reason = goal_score(req, cand, requirements)
    l, l_reason = geography_score(req, cand)
    a, a_reason = profile_score(cand)

    score = ComponentScore(interest=i, skills=c, goal=g, geography=l, profile=a)
    components = {
        "interest": (i, i_reason),
        "skills": (c, c_reason),
        "goal": (g, g_reason),
        "geography": (l, l_reason),
        "profile": (a, a_reason),
    }
    strongest = [
        name for name, _ in sorted(components.items(), key=lambda kv: kv[1][0], reverse=True)[:2]
    ]
    reasons = [
        f"Interest compatibility ({i:.0f}/100): {i_reason}",
        f"Complementary skills ({c:.0f}/100): {c_reason}",
        f"Goal alignment ({g:.0f}/100): {g_reason}",
        f"Geography ({l:.0f}/100): {l_reason}",
        f"Profile & freshness ({a:.0f}/100): {a_reason}",
    ]

    # Uncertainty — surfaced honestly, never hidden
    uncertainty_bits = []
    if cand.verification_status == "discovered" and cand.confidence < 55:
        uncertainty_bits.append("This is a discovered (not yet verified) record with limited evidence — confirm details before relying on it.")
    if missing:
        uncertainty_bits.append(f"Not listed by this community: {', '.join(missing)}.")
    if not cand.offered_skills and not cand.interests:
        uncertainty_bits.append("Thin profile: scores are based on limited data and may improve once the community completes its profile.")

    freshness = {
        "verification_status": cand.verification_status,
        "confidence": cand.confidence,
        "source_count": cand.source_count,
        "last_checked_at": cand.last_checked_at.isoformat() if cand.last_checked_at else None,
    }
    return MatchResult(
        candidate=cand,
        score=score,
        reasons=reasons,
        strongest_factors=strongest,
        missing_skills=missing,
        freshness=freshness,
        uncertainty=" ".join(uncertainty_bits) if uncertainty_bits else None,
    )


def rank_matches(
    requester: CommunityProfile,
    candidates: list[CommunityProfile],
    requirements: MatchRequirements,
) -> list[MatchResult]:
    """Rank candidates for a requester. Handles exclusions, self-match removal,
    duplicate removal, and a minimum-relevance threshold."""
    results: list[MatchResult] = []
    seen: set[int] = set()
    exclude = set(requirements.exclude_ids) | {requester.id}
    for cand in candidates:
        if cand.id in exclude or cand.id in seen:
            continue
        seen.add(cand.id)
        result = score_pair(requester, cand, requirements)
        if result.score.total >= requirements.min_score:
            results.append(result)
    results.sort(key=lambda r: r.score.total, reverse=True)
    return results[: max(1, requirements.limit)]


# ---------------------------------------------------------------------------
# ORM adapter (thin; kept here so routes stay free of scoring logic)
# ---------------------------------------------------------------------------

def profile_from_model(community) -> CommunityProfile:
    """Build a CommunityProfile from an app.models.Community row."""
    from .matching import CommunityProfile  # noqa: F401 — self-reference clarity

    offered, sought = [], []
    for a in community.community_skills:
        (offered if a.kind == "offers" else sought).append(a.skill.name)
    return CommunityProfile(
        id=community.id,
        name=community.name,
        interests=list(community.interests or []),
        offered_skills=offered,
        sought_skills=sought,
        project_titles=[p.title for p in community.projects],
        project_descriptions=[p.description for p in community.projects if p.description],
        city=community.college.city if community.college else None,
        college_id=community.college_id,
        verification_status=community.verification_status,
        confidence=community.confidence or 0.0,
        description=community.description or "",
        website=community.website,
        has_social_links=bool(community.social_links),
        member_count=len(community.members),
        source_count=len(community.sources),
        last_checked_at=community.last_checked_at,
    )
