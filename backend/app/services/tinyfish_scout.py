"""TinyFish-powered Community Scout.

Workflow (per the product spec and docs.tinyfish.ai):
  1. Search  — several targeted queries via TinyFish Search API
               GET https://api.search.tinyfish.ai?query=…   (X-API-Key)
  2. Fetch   — clean page content via TinyFish Fetch API
               POST https://api.fetch.tinyfish.ai  {urls, format}
  3. Extract — normalize into a consistent community schema
  4. Validate & dedupe — compare against stored records, flag conflicts
  5. Return  — evidence-backed candidates ready for review/import

The Agent API (POST https://agent.tinyfish.ai/v1/automation/run-sse) is used
only when a target page requires browser-based interaction.

SECURITY: the browser NEVER calls TinyFish. The API key stays on this backend.

DEMO MODE: without TINYFISH_API_KEY the scout runs against a curated corpus and
labels every result as demo/seed — the extraction → validation → dedupe →
review pipeline is identical in both modes, and demo data is never presented
as live web discovery.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import core
from ..core.config import settings
from ..models import Community

logger = logging.getLogger("uniclyst.scout")

# The extraction instruction used with TinyFish Fetch / Agent results.
# Proposed application prompt — not a special TinyFish command.
EXTRACTION_PROMPT = """Find publicly accessible student organizations and student
communities relevant to the requested interests and colleges. For each candidate,
return: organization name, college/institution name, city, main interests and
technical skills, official organization URL, public event URLs, evidence excerpts
supporting the extracted details, source URL for each important claim, last-checked
timestamp, missing or conflicting information, and verification status.

Do not invent organizations, URLs, events, or contact details. Separate observed
facts from inferred information. If a detail cannot be verified from the accessible
source, return null or mark it as unconfirmed. Do not treat a social media follower
count as proof that an organization is active. Use structured JSON output where
supported, then validate it against your own schema before saving it."""


# ---------------------------------------------------------------------------
# TinyFish client — documented HTTP APIs only (verified against docs.tinyfish.ai)
# ---------------------------------------------------------------------------

class TinyFishError(Exception):
    """Raised when the TinyFish API cannot be reached or rejects a request."""


class TinyFishClient:
    """Thin client for TinyFish Search + Fetch (+ Agent for dynamic pages).

    Timeouts, bounded retries with backoff, and request logging are built in.
    No unrestricted crawling: callers submit explicit queries/URLs only.
    """

    def __init__(self, api_key: str | None = None, timeout: float | None = None,
                 max_retries: int | None = None):
        self.api_key = api_key if api_key is not None else settings.TINYFISH_API_KEY
        self.timeout = timeout if timeout is not None else settings.TINYFISH_TIMEOUT_SECONDS
        self.max_retries = max_retries if max_retries is not None else settings.TINYFISH_MAX_RETRIES

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict:
        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    def _request(self, method: str, url: str, **kwargs) -> dict:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                logger.info("tinyfish %s %s (attempt %d)", method, url, attempt + 1)
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.request(method, url, headers=self._headers(), **kwargs)
                if resp.status_code >= 500:
                    raise TinyFishError(f"TinyFish server error {resp.status_code}")
                if resp.status_code >= 400:
                    raise TinyFishError(f"TinyFish rejected request ({resp.status_code}): {resp.text[:200]}")
                return resp.json()
            except (httpx.HTTPError, TinyFishError) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(0.5 * (2 ** attempt))
        raise TinyFishError(f"TinyFish request failed after {self.max_retries + 1} attempts: {last_exc}")

    def search(self, query: str, location: str | None = None, page: int = 0) -> dict:
        """GET api.search.tinyfish.ai — ranked results with titles/snippets/URLs."""
        params: dict = {"query": query, "page": page}
        if location:
            params["location"] = location
        return self._request("GET", settings.TINYFISH_SEARCH_URL, params=params)

    def fetch(self, urls: list[str], fmt: str = "markdown", ttl: int | None = None) -> dict:
        """POST api.fetch.tinyfish.ai — extracted page content (up to 10 URLs)."""
        body: dict = {"urls": urls[:10], "format": fmt}
        if ttl is not None:
            body["ttl"] = ttl  # cache freshness preference (0 = live fetch)
        return self._request("POST", settings.TINYFISH_FETCH_URL, json=body)

    def agent_extract(self, url: str, goal: str) -> dict:
        """POST agent.tinyfish.ai/v1/automation/run-sse — goal-based browser
        workflow for pages that need interaction. Consumes the SSE stream and
        returns the COMPLETE event payload."""
        body = {"url": url, "goal": goal}
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                result: dict = {}
                with httpx.Client(timeout=self.timeout * 2) as client:
                    with client.stream(
                        "POST", settings.TINYFISH_AGENT_URL, headers=self._headers(), json=body
                    ) as resp:
                        if resp.status_code >= 400:
                            raise TinyFishError(f"Agent API error {resp.status_code}")
                        for line in resp.iter_lines():
                            if not line.startswith("data:"):
                                continue
                            payload = line[5:].strip()
                            if payload == "[DONE]":
                                break
                            import json

                            try:
                                event = json.loads(payload)
                            except ValueError:
                                continue
                            if event.get("type") == "COMPLETE":
                                result = event.get("result", {})
                return result
            except (httpx.HTTPError, TinyFishError) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(0.5 * (2 ** attempt))
        raise TinyFishError(f"Agent request failed: {last_exc}")


# ---------------------------------------------------------------------------
# Demo corpus — shaped like real Search + Fetch payloads so the downstream
# extraction/normalization pipeline is mode-agnostic. Clearly labeled demo data.
# ---------------------------------------------------------------------------

DEMO_PAGES = {
    "https://robotics.dtu.ac.in/": {
        "title": "Robotics Society, Delhi Technological University",
        "text": (
            "# Robotics Society — DTU\n"
            "The Robotics Society of Delhi Technological University builds autonomous robots, "
            "robo-soccer platforms and Arduino/IoT projects. We run the annual tech fest "
            "robotics challenge and welcome collaboration with AI and design clubs.\n"
            "Skills: ROS, Arduino, mechanical design, computer vision.\n"
            "Upcoming: RoboWars Qualifier — March 2027.\n"
            "Contact: robotics@dtu.ac.in"
        ),
    },
    "https://www.iiitd.ac.in/aims/": {
        "title": "AIMS — AI & ML Society, IIIT Delhi",
        "text": (
            "# AIMS — AI and Machine Learning Society at IIIT Delhi\n"
            "AIMS organizes study groups, paper reading circles and hackathons around "
            "machine learning, computer vision and data science. Our members have shipped "
            "vision pipelines for drone projects and host the Delhi NCR ML meetup.\n"
            "Skills: machine learning, computer vision, python, data science.\n"
            "Upcoming: NCR ML Meetup — April 2027."
        ),
    },
    "https://design.nsitonline.in/creative/": {
        "title": "Creative Studio, Netaji Subhas University of Technology",
        "text": (
            "# Creative Studio — NSUT\n"
            "Creative Studio is NSUT's design and media community: UI/UX, graphic design, "
            "photography and branding for campus events. We partner with technical clubs to "
            "design competition identities, posters and product UIs.\n"
            "Skills: ui/ux, graphic design, branding, photography.\n"
            "Not verified with the university registry yet — details from the club's own page."
        ),
    },
    "https://ecell.dtu.ac.in/": {
        "title": "Entrepreneurship Cell, Delhi Technological University",
        "text": (
            "# E-Cell DTU\n"
            "The Entrepreneurship Cell DTU runs the annual startup pitch competition "
            "E-Summit, mentorship circles and a student incubator. We frequently sponsor "
            "and co-host hackathons with technical societies across Delhi NCR.\n"
            "Skills: marketing, public relations, finance, event management.\n"
            "Upcoming: E-Summit 2027 — February 2027."
        ),
    },
    "https://cyber.jnu.ac.in/society/": {
        "title": "Cyber Security Society, Jawaharlal Nehru University",
        "text": (
            "# Cyber Security Society — JNU\n"
            "A student community for CTF practice, network security workshops and "
            "cryptography reading groups. Looking for engineering-college partners for a "
            "cross-campus CTF competition.\n"
            "Skills: cryptography, networking, linux.\n"
            "Found via a public workshop announcement page; last page update unclear."
        ),
    },
    "https://snu.edu.in/innovation/avishkar/": {
        "title": "Avishkar Innovation Club, Shiv Nadar University",
        "text": (
            "# Avishkar — Innovation & Prototyping Club, Shiv Nadar University\n"
            "Avishkar is a multidisciplinary innovation club working on hardware prototyping, "
            "IoT, embedded systems and social-impact projects. We have a workshop space with "
            "3D printers and want to co-build autonomous systems with partner colleges.\n"
            "Skills: iot, embedded, mechanical design, prototyping.\n"
            "Upcoming: Avishkar Innovation Challenge — May 2027."
        ),
    },
    "https://www.amity.edu/noida/aic/": {
        "title": "AI Community, Amity University Noida",
        "text": (
            "# AI Community — Amity University Noida\n"
            "The AI Community at Amity Noida hosts weekly sessions on deep learning and "
            "generative AI, and fields teams for national hackathons. We are interested in "
            "collaborating on autonomous robotics projects needing vision models.\n"
            "Skills: machine learning, deep learning, python, computer vision.\n"
            "Social page mentions 900+ followers; treat activity as unconfirmed."
        ),
    },
    "https://ggsipu.ac.in/aero/": {
        "title": "Aeronautical Society, GGSIPU (tentative page)",
        "text": (
            "# Aeronautical Society — Guru Gobind Singh Indraprastha University\n"
            "Student group for drone design and aeromodelling competitions. Page lists "
            "contact via an old Gmail address and references a 2024 event only.\n"
            "Skills: drones, embedded, mechanical design.\n"
            "Conflicting info: page footer says 2024 while the header advertises a 2025 fest."
        ),
    },
}

DEMO_SEARCH_RESULTS = {
    "robotics": ["https://robotics.dtu.ac.in/", "https://snu.edu.in/innovation/avishkar/"],
    "ai": ["https://www.iiitd.ac.in/aims/", "https://www.amity.edu/noida/aic/"],
    "machine learning": ["https://www.iiitd.ac.in/aims/", "https://www.amity.edu/noida/aic/"],
    "design": ["https://design.nsitonline.in/creative/"],
    "entrepreneur": ["https://ecell.dtu.ac.in/"],
    "cyber": ["https://cyber.jnu.ac.in/society/"],
    "innovation": ["https://snu.edu.in/innovation/avishkar/", "https://ecell.dtu.ac.in/"],
    "drone": ["https://ggsipu.ac.in/aero/"],
    "hackathon": ["https://ecell.dtu.ac.in/", "https://www.amity.edu/noida/aic/"],
    "event": ["https://robotics.dtu.ac.in/", "https://ecell.dtu.ac.in/"],
    "vision": ["https://www.iiitd.ac.in/aims/", "https://www.amity.edu/noida/aic/"],
}

INTEREST_VOCAB = [
    "robotics", "ai", "machine learning", "computer vision", "design", "ui/ux",
    "entrepreneurship", "cybersecurity", "iot", "embedded", "drones", "data science",
    "mechanical design", "marketing", "events", "event management", "prototyping",
    "cryptography", "deep learning", "python", "photography", "branding", "finance",
    "linux", "networking", "arduino", "ros", "generative ai", "hackathons", "startups",
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Evidence:
    source_url: str
    source_title: str
    evidence_excerpt: str
    confidence: float
    note: str = ""


@dataclass
class Candidate:
    organization_name: str
    college: str
    city: str
    interests: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    official_url: str | None = None
    event_names: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    confidence: float = 0.0
    verification_status: str = "discovered"
    missing_or_conflicting: str = ""
    dedupe_match_org_id: int | None = None

    def to_dict(self) -> dict:
        return {
            "organization_name": self.organization_name,
            "college": self.college,
            "city": self.city,
            "interests": self.interests,
            "skills": self.skills,
            "official_url": self.official_url,
            "event_names": self.event_names,
            "evidence": [vars(e) for e in self.evidence],
            "confidence": self.confidence,
            "verification_status": self.verification_status,
            "missing_or_conflicting": self.missing_or_conflicting,
            "dedupe_match_org_id": self.dedupe_match_org_id,
        }


# ---------------------------------------------------------------------------
# Extraction, confidence heuristics, validation & dedupe
# ---------------------------------------------------------------------------

def _extract_interests_skills(text: str) -> list[str]:
    low = text.lower()
    return [term for term in INTEREST_VOCAB if term in low]


def _extract_events(text: str) -> list[str]:
    events = []
    for line in text.splitlines():
        if "upcoming:" in line.lower():
            m = re.search(r"upcoming:\s*([^-—]+)", line, re.I)
            if m:
                events.append(m.group(1).strip())
    return events


def confidence_for(url: str, text: str) -> tuple[float, str]:
    """Transparent heuristic — NOT a calibrated probability.

    Official domains and structured pages earn more; social-media-only or
    self-declared-uncertain sources earn less. Displayed verbatim in the UI.
    """
    score, notes = 40.0, []
    domain = re.sub(r"^https?://(www\.)?", "", url).split("/")[0].lower()
    if domain.endswith((".ac.in", ".edu", ".ac.uk")) or ".edu." in domain:
        score += 30
        notes.append("official college domain (+30)")
    elif any(s in domain for s in ("instagram", "linkedin", "facebook", "x.com", "twitter")):
        score -= 15
        notes.append("social media source (−15)")
    else:
        notes.append("non-institutional domain (+0)")
    low = text.lower()
    if "skill" in low or "upcoming" in low:
        score += 12
        notes.append("structured details on page (+12)")
    if any(w in low for w in ("unverified", "unclear", "conflicting", "unconfirmed", "tentative")):
        score -= 12
        notes.append("page itself flags uncertainty (−12)")
    if "contact" in low or "@" in text:
        score += 8
        notes.append("contact info present (+8)")
    return round(min(95.0, max(5.0, score)), 1), ", ".join(notes)


def _college_from_text(text: str) -> str:
    patterns = [
        r"Delhi Technological University", r"IIIT Delhi", r"Netaji Subhas University of Technology",
        r"Jawaharlal Nehru University", r"Shiv Nadar University", r"Amity University[^,\n]*",
        r"Guru Gobind[^,\n]*", r"GGSIPU[^,\n]*",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(0).strip(" ,.-")
    m = re.search(r"([A-Z][A-Za-z&.\s]{3,60}(?:University|Institute)[^,\n#]*)", text)
    return m.group(1).strip() if m else "Unknown institution"


def _city_for(college: str, text: str) -> str:
    low = (college + " " + text).lower()
    for city in ("greater noida", "gurugram", "gurgaon", "ghaziabad", "faridabad", "noida", "delhi"):
        if city in low:
            return city.title()
    return "Delhi NCR"


def normalize_page(url: str, page: dict) -> Candidate:
    title = page.get("title", "")
    text = page.get("text", "")
    tags = _extract_interests_skills(text)
    name = title
    m = re.search(r"^#\s*(.+)$", text, re.M)
    if m:
        name = m.group(1).split(",")[0].split("—")[0].split("-")[0].strip()
    else:
        name = title.split(",")[0].split("—")[0].strip() or "Unknown organization"
    college = _college_from_text(title + " " + text)
    conf, conf_note = confidence_for(url, text)
    low = text.lower()
    missing = ""
    if "conflicting" in low:
        missing = "Source page contains conflicting dates/info — needs organizer confirmation"
    elif any(w in low for w in ("unverified", "unclear", "unconfirmed", "tentative")):
        missing = "Source flags some details as unconfirmed"
    elif "follower" in low:
        missing = "Social follower count is not evidence of activity — verify before trusting"
    evidence = Evidence(
        source_url=url,
        source_title=title,
        evidence_excerpt=text[:280].replace("\n", " "),
        confidence=conf,
        note=conf_note,
    )
    return Candidate(
        organization_name=name,
        college=college,
        city=_city_for(college, text),
        interests=tags,
        skills=tags,
        official_url=url,
        event_names=_extract_events(text),
        evidence=[evidence],
        confidence=conf,
        verification_status="discovered",  # NEVER auto-verified
        missing_or_conflicting=missing,
    )


def merge_candidates(candidates: list[Candidate]) -> list[Candidate]:
    """Merge multiple evidence sources describing the same organization."""
    merged: dict[str, Candidate] = {}
    for cand in candidates:
        key = re.sub(r"[^a-z0-9]", "", cand.organization_name.lower())[:24]
        if key in merged:
            base = merged[key]
            base.evidence.extend(cand.evidence)
            base.interests = sorted(set(base.interests) | set(cand.interests))
            base.skills = sorted(set(base.skills) | set(cand.skills))
            base.event_names = sorted(set(base.event_names) | set(cand.event_names))
            base.confidence = round(min(95.0, (base.confidence + cand.confidence) / 2 + 5), 1)
            if cand.missing_or_conflicting and cand.missing_or_conflicting not in base.missing_or_conflicting:
                base.missing_or_conflicting = (
                    base.missing_or_conflicting + " | " + cand.missing_or_conflicting
                ).strip(" |")
        else:
            merged[key] = cand
    return list(merged.values())


def dedupe(candidates: list[Candidate], db: Session) -> list[Candidate]:
    """Flag candidates that already exist in the network (fuzzy name match)."""
    existing = db.execute(
        select(Community.id, func.lower(Community.name))
    ).all()
    for cand in candidates:
        cname = re.sub(r"[^a-z0-9]", "", cand.organization_name.lower())
        for org_id, lname in existing:
            ename = re.sub(r"[^a-z0-9]", "", lname or "")
            if cname and ename and (cname in ename or ename in cname):
                cand.dedupe_match_org_id = org_id
                note = "Similar organization already exists in the network — importing would attach this evidence to it"
                cand.missing_or_conflicting = (
                    cand.missing_or_conflicting + " | " + note
                ).strip(" |") if cand.missing_or_conflicting else note
                break
    return candidates


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _build_queries(query: str, region: str, interests: list[str]) -> list[str]:
    """Several targeted queries beat one broad query."""
    base = [f"{query} student club {region}", f"{query} college society {region}"]
    for interest in interests[:3]:
        base.append(f"{interest} student organization {region} official site")
    return base


def run_scout(query: str, region: str, interests: list[str], db: Session) -> tuple[str, list[Candidate], int, list[str]]:
    """Execute the scout pipeline. Returns (mode, candidates, raw_count, notes)."""
    notes: list[str] = ["Extraction policy: " + EXTRACTION_PROMPT[:110] + "…"]
    client = TinyFishClient()
    pages: dict[str, dict] = {}
    raw_count = 0

    if client.enabled:
        mode = "live"
        try:
            for q in _build_queries(query, region, interests):
                data = client.search(q, location=region)
                results = data.get("results", [])
                raw_count += len(results)
                urls = [r["url"] for r in results[:4] if r.get("url")]
                if not urls:
                    continue
                fetched = client.fetch(urls, fmt="markdown", ttl=settings.TINYFISH_CACHE_TTL_SECONDS or None)
                for page in fetched.get("results", []):
                    pages[page["url"]] = {"title": page.get("title", ""), "text": page.get("text", "")}
                for err in fetched.get("errors", []):
                    notes.append(f"Fetch failed for {err.get('url')}: {err.get('error')}")
            notes.insert(0, f"LIVE mode (TinyFish): {raw_count} search hits, {len(pages)} pages fetched")
        except TinyFishError as exc:
            mode = "demo"
            notes.insert(0, f"TinyFish call failed ({exc}); falling back to demo corpus")
    else:
        mode = "demo"
        notes.insert(0, "DEMO MODE: no TINYFISH_API_KEY set — results come from the curated demo corpus, not the live web")

    if mode == "demo":
        keys = " ".join([query, region, *interests]).lower()
        urls = []
        for token, token_urls in DEMO_SEARCH_RESULTS.items():
            if token in keys:
                urls.extend(token_urls)
        if not urls:
            urls = list(DEMO_PAGES.keys())
        urls = list(dict.fromkeys(urls))
        raw_count = len(urls) * 2
        for u in urls:
            pages[u] = DEMO_PAGES[u]

    candidates = [normalize_page(url, page) for url, page in pages.items()]

    want = {i.strip().lower() for i in interests if i.strip()}
    if want:
        def relevant(c: Candidate) -> bool:
            tags = {t.lower() for t in c.interests} | {t.lower() for t in c.skills}
            return bool(tags & want) or any(w in " ".join(tags) for w in want)
        filtered = [c for c in candidates if relevant(c)]
        candidates = filtered or candidates

    candidates = merge_candidates(candidates)
    candidates = dedupe(candidates, db)
    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return mode, candidates, raw_count, notes
