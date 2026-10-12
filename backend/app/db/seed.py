"""Repeatable seed data — realistic but clearly fictional/demo-marked.

All seeded communities carry is_demo=1 and demo accounts use the reserved
demo domain `demo.uniclyst.local`. Seeded accounts (password: demo123 unless
DEMO_PASSWORD is overridden):

  aarav    — organizer, Robotics Society DTU
  meera    — organizer, AIMS (IIIT-D)
  rohan    — organizer, Creative Studio NSUT
  student  — generic student (Sana Ali)
  reviewer — platform reviewer (can promote verification status)

Usage:  python -m app.db.seed
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import hash_password
from ..core.config import settings
from .session import Base, SessionLocal, engine


def _dt(days: int = 0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


SKILL_CATEGORIES = {
    "ROS": "Robotics", "Arduino": "Robotics", "Mechanical Design": "Engineering",
    "Computer Vision": "AI", "Machine Learning": "AI", "Deep Learning": "AI",
    "Python": "Software", "Data Science": "AI", "UI/UX": "Design",
    "Graphic Design": "Design", "Branding": "Design", "Photography": "Design",
    "Marketing": "Business", "Public Relations": "Business", "Finance": "Business",
    "Event Management": "Business", "IoT": "Hardware", "Embedded": "Hardware",
    "Prototyping": "Hardware", "Drones": "Hardware", "Cryptography": "Security",
    "Networking": "Security", "Linux": "Security", "Flutter": "Software",
    "Web Development": "Software", "Figma": "Design", "Generative AI": "AI",
}


def seed(db: Session) -> None:
    from ..models import (
        Collaboration,
        CollaborationMember,
        CollaborationRequest,
        College,
        Community,
        CommunityMember,
        CommunitySkill,
        DiscoverySource,
        Event,
        Milestone,
        Project,
        Skill,
        User,
    )

    skills: dict[str, Skill] = {}
    for name, cat in SKILL_CATEGORIES.items():
        skill = Skill(name=name, category=cat)
        db.add(skill)
        skills[name] = skill
    db.flush()

    colleges = [
        College(name="Delhi Technological University", short_name="DTU", city="Delhi",
                region="Delhi NCR", website="https://dtu.ac.in", lat=28.7491, lng=77.1139,
                description="One of Delhi's largest engineering universities, known for its technical societies."),
        College(name="Indraprastha Institute of Information Technology Delhi", short_name="IIIT-D",
                city="Delhi", region="Delhi NCR", website="https://iiitd.ac.in", lat=28.5455, lng=77.2731,
                description="Research-focused institute with a strong AI, systems and design culture."),
        College(name="Netaji Subhas University of Technology", short_name="NSUT", city="Delhi",
                region="Delhi NCR", website="https://nsut.ac.in", lat=28.6091, lng=77.0365,
                description="Premier engineering university with an active creative and technical club scene."),
        College(name="Jamia Millia Islamia", short_name="JMI", city="Delhi",
                region="Delhi NCR", website="https://jmi.ac.in", lat=28.5616, lng=77.2816,
                description="Central university with diverse student communities."),
        College(name="Shiv Nadar University", short_name="SNU", city="Greater Noida",
                region="Delhi NCR", website="https://snu.edu.in", lat=28.5244, lng=77.5807,
                description="Interdisciplinary university with an innovation-first campus culture."),
        College(name="Amity University Noida", short_name="Amity", city="Noida",
                region="Delhi NCR", website="https://amity.edu", lat=28.5446, lng=77.3346,
                description="Large private university with many student-run technical communities."),
    ]
    db.add_all(colleges)
    db.flush()

    def community(name, slug, college, description, category, interests, offers, seeks,
                  status, conf, website, founded_note="", events=None, sources=None, projects=None):
        c = Community(
            name=name, slug=slug, college_id=college.id, description=description,
            category=category, interests=interests, verification_status=status,
            confidence=conf, website=website, is_demo=1,
            social_links={"note": founded_note} if founded_note else {},
            last_checked_at=_dt(-3),
        )
        db.add(c)
        db.flush()
        for s in offers:
            db.add(CommunitySkill(community_id=c.id, skill_id=skills[s].id, kind="offers"))
        for s in seeks:
            db.add(CommunitySkill(community_id=c.id, skill_id=skills[s].id, kind="seeks"))
        for ev in (events or []):
            db.add(Event(community_id=c.id, **ev))
        for src in (sources or []):
            db.add(DiscoverySource(community_id=c.id, origin="seed", **src))
        for p in (projects or []):
            db.add(Project(community_id=c.id, **p))
        return c

    def src(url, title, excerpt, status, conf, note=""):
        return dict(source_url=url, source_title=title, evidence_excerpt=excerpt,
                    review_status=status, confidence=conf, review_note=note)

    def ev(name, desc, days, city, url=None, online=0, category="Hackathon", listing="upcoming", conf=80.0):
        return dict(name=name, description=desc, category=category,
                    starts_at=_dt(days), ends_at=_dt(days + 1), city=city,
                    event_url=url, is_online=online, listing_status=listing, confidence=conf)

    robotics_dtu = community(
        "Robotics Society DTU", "robotics-society-dtu", colleges[0],
        "Builds autonomous robots, robo-soccer platforms and open-source hardware projects. "
        "Runs the annual robotics challenge at the DTU tech fest and seeks cross-college "
        "collaborators for a national competition.",
        "Technical", ["robotics", "iot"],
        ["ROS", "Arduino", "Mechanical Design", "Embedded"], ["Computer Vision", "UI/UX"],
        "verified", 88, "https://robotics.dtu.ac.in/",
        events=[
            ev("RoboWars Qualifier 2027", "Inter-college robot combat qualifier.", 45, "Delhi",
               "https://robotics.dtu.ac.in/rowars", category="Competition", conf=85),
            ev("Autonomous Systems Workshop", "Weekend workshop on ROS 2 navigation stacks.", 20, "Delhi",
               category="Workshop", conf=90),
        ],
        sources=[src("https://robotics.dtu.ac.in/", "Robotics Society — DTU official page",
                     "The Robotics Society of Delhi Technological University builds autonomous robots… "
                     "Skills: ROS, Arduino, mechanical design.", "verified", 88,
                     "Confirmed on official college domain by reviewer.")],
        projects=[dict(title="Autonomous Rover for RoboWars",
                       description="An arena rover with onboard perception and autonomous navigation.",
                       status="active", needed_skills=["Computer Vision", "Machine Learning"])],
    )

    aims_iiitd = community(
        "AIMS — AI & ML Society", "aims-iiitd", colleges[1],
        "AI and machine learning society: paper circles, hackathons and vision projects. "
        "Runs the Delhi NCR ML Meetup; has shipped computer-vision pipelines for drone projects.",
        "Technical", ["ai", "machine learning", "data science"],
        ["Machine Learning", "Computer Vision", "Python", "Data Science", "Deep Learning"],
        ["Drones", "Event Management"],
        "verified", 91, "https://www.iiitd.ac.in/aims/",
        events=[ev("NCR ML Meetup 2027", "Regional machine learning meetup with student talks.", 60, "Delhi",
                   "https://www.iiitd.ac.in/aims/meetup", category="Meetup", conf=88)],
        sources=[src("https://www.iiitd.ac.in/aims/", "AIMS — IIIT Delhi official society page",
                     "AIMS organizes study groups… Skills: machine learning, computer vision, python.",
                     "verified", 91, "Official institute subdomain.")],
        projects=[dict(title="Open Vision Toolkit",
                       description="Reusable perception modules for student robotics teams.",
                       status="active", needed_skills=["Drones"])],
    )

    creative_nsut = community(
        "Creative Studio NSUT", "creative-studio-nsut", colleges[2],
        "Design and media community: UI/UX, branding, photography and event identity design "
        "for campus and inter-college events.",
        "Cultural", ["design", "ui/ux", "photography"],
        ["UI/UX", "Graphic Design", "Branding", "Photography", "Figma"],
        ["Marketing", "Event Management"],
        "reviewed", 72, "https://design.nsitonline.in/creative/",
        sources=[src("https://design.nsitonline.in/creative/", "Creative Studio — NSUT club page",
                     "Creative Studio is NSUT's design and media community… Not verified with the "
                     "university registry yet.", "reviewed", 72,
                     "Self-published club page; reviewer confirmed existence via event posters.")],
    )

    ecell_dtu = community(
        "E-Cell DTU", "e-cell-dtu", colleges[0],
        "Entrepreneurship cell running E-Summit, pitch competitions, mentorship circles "
        "and sponsorships for student hackathons across Delhi NCR.",
        "Entrepreneurship", ["entrepreneurship", "events", "startups"],
        ["Marketing", "Public Relations", "Finance", "Event Management"],
        ["Graphic Design", "Web Development"],
        "verified", 85, "https://ecell.dtu.ac.in/",
        events=[ev("E-Summit 2027", "Annual startup summit with pitch competition.", 100, "Delhi",
                   "https://ecell.dtu.ac.in/esummit", category="Meetup", conf=90)],
        sources=[src("https://ecell.dtu.ac.in/", "E-Cell DTU official site",
                     "The Entrepreneurship Cell DTU runs the annual startup pitch competition E-Summit…",
                     "verified", 85, "Official college domain, updated recently.")],
    )

    cyber_jmi = community(
        "Cyber Security Society JMI", "cyber-security-society-jmi", colleges[3],
        "CTF practice, network security workshops and cryptography reading groups. "
        "Looking for engineering-college partners to run a cross-campus CTF.",
        "Technical", ["cybersecurity", "networking"],
        ["Cryptography", "Networking", "Linux"],
        ["Web Development", "Event Management"],
        "discovered", 54, None,
        sources=[src("https://www.jnu.ac.in/cyber/", "Cyber Security Society — workshop page",
                     "A student community for CTF practice… Found via a public workshop announcement "
                     "page; last page update unclear.", "discovered", 54,
                     "Page age unknown — freshness unconfirmed.")],
    )

    avishkar_snu = community(
        "Avishkar Innovation Club", "avishkar-snu", colleges[4],
        "Multidisciplinary innovation club: hardware prototyping, IoT, embedded systems "
        "and social-impact projects. Workshop space with 3D printers.",
        "Technical", ["innovation", "iot", "prototyping"],
        ["IoT", "Embedded", "Mechanical Design", "Prototyping", "Arduino"],
        ["Machine Learning", "Branding"],
        "reviewed", 74, "https://snu.edu.in/innovation/avishkar/",
        events=[ev("Avishkar Innovation Challenge 2027", "48-hour hardware prototyping challenge.",
                   75, "Greater Noida", category="Hackathon", conf=80)],
        sources=[src("https://snu.edu.in/innovation/avishkar/", "Avishkar — SNU innovation club",
                     "Avishkar is a multidisciplinary innovation club… Skills: iot, embedded, "
                     "mechanical design, prototyping.", "reviewed", 74, "University-hosted page.")],
    )

    ai_amity = community(
        "AI Community Amity", "ai-community-amity", colleges[5],
        "Weekly deep-learning and generative-AI sessions; fields teams for national hackathons. "
        "Interested in autonomous robotics projects that need vision models.",
        "Technical", ["ai", "machine learning", "hackathons"],
        ["Machine Learning", "Deep Learning", "Python", "Computer Vision", "Generative AI"],
        ["Drones"],
        "discovered", 61, "https://www.amity.edu/noida/aic/",
        sources=[src("https://www.amity.edu/noida/aic/", "AI Community — Amity Noida",
                     "The AI Community at Amity Noida hosts weekly sessions… Social page mentions "
                     "900+ followers; treat activity as unconfirmed.", "discovered", 61,
                     "Follower count is not evidence of activity.")],
    )

    aero_ipu = community(
        "Aeronautical Society GGSIPU", "aeronautical-society-ggsipu", colleges[3],
        "Drone design and aeromodelling competitions. Source page has conflicting dates "
        "and a stale contact address — needs organizer confirmation.",
        "Technical", ["drones", "robotics"],
        ["Drones", "Embedded", "Mechanical Design"],
        ["Computer Vision", "Marketing"],
        "discovered", 42, None,
        events=[ev("AeroModelling Jam", "Open aeromodelling demo day.", 120, "Delhi",
                   listing="uncertain", conf=35)],
        sources=[src("https://ggsipu.ac.in/aero/", "Aeronautical Society — GGSIPU (tentative)",
                     "Student group for drone design… Conflicting info: page footer says 2024 while "
                     "the header advertises a 2025 fest.", "discovered", 42, "Conflicting dates.")],
    )

    dsc_dtu = community(
        "Developer Student Club DTU", "dsc-dtu", colleges[0],
        "Google developer community: web, mobile and cloud study jams, plus an annual hackathon.",
        "Technical", ["software", "web", "mobile"],
        ["Web Development", "Flutter", "Python", "Event Management"],
        ["UI/UX"],
        "verified", 82, "https://dsc.dtu.ac.in/",
        events=[ev("Build for Bharat Hackathon", "48-hour product hackathon.", 55, "Delhi",
                   category="Hackathon", conf=85)],
        sources=[src("https://dsc.dtu.ac.in/", "DSC DTU official page",
                     "Developer Student Club DTU runs study jams and an annual hackathon.",
                     "verified", 82, "Verified by reviewer.")],
    )

    film_jmi = community(
        "Film & Media Society JMI", "film-society-jmi", colleges[3],
        "Photography walks, short-film production and campus media coverage.",
        "Cultural", ["photography", "media", "design"],
        ["Photography", "Graphic Design", "Branding"],
        ["Event Management"],
        "discovered", 50, None,
        sources=[src("https://jmi.ac.in/film/", "Film Society — JMI page",
                     "Photography walks, short-film production and campus media coverage.",
                     "discovered", 50, "Page mentions 45 members.")],
    )

    ds_snu = community(
        "Data Science Collective SNU", "ds-collective-snu", colleges[4],
        "Kaggle circles, analytics workshops and data-for-social-good projects.",
        "Technical", ["data science", "ai"],
        ["Data Science", "Python", "Machine Learning"],
        ["Finance"],
        "reviewed", 70, "https://snu.edu.in/dsc/",
        sources=[src("https://snu.edu.in/dsc/", "Data Science Collective — SNU",
                     "Kaggle circles, analytics workshops and data-for-social-good projects.",
                     "reviewed", 70, "University-hosted page.")],
    )

    robotech_amity = community(
        "RoboTech Amity", "robotech-amity", colleges[5],
        "Robotics club focused on line-followers, drone builds and hardware hackathons.",
        "Technical", ["robotics", "drones", "iot"],
        ["Arduino", "Mechanical Design", "Embedded", "IoT"],
        ["Computer Vision", "Machine Learning"],
        "reviewed", 68, "https://www.amity.edu/robotech/",
        events=[ev("Hardware Hack Night", "Overnight hardware build session.", 30, "Noida",
                   category="Hackathon", conf=75)],
        sources=[src("https://www.amity.edu/robotech/", "RoboTech Amity club page",
                     "Robotics club focused on line-followers, drone builds and hardware hackathons.",
                     "reviewed", 68, "Club page on university domain.")],
    )

    eclub_snu = community(
        "SNU Entrepreneurship Club", "entrep-snu", colleges[4],
        "Student founders' collective: idea jams, angel practice pitches and founder AMAs.",
        "Entrepreneurship", ["entrepreneurship", "startups"],
        ["Finance", "Marketing", "Public Relations"],
        ["Web Development"],
        "reviewed", 66, "https://snu.edu.in/eclub/",
        sources=[src("https://snu.edu.in/eclub/", "SNU E-Club",
                     "Student founders' collective: idea jams, angel practice pitches and founder AMAs.",
                     "reviewed", 66, "")],
    )

    # ---- Users (documented dev seed accounts) ----
    pw = hash_password(settings.DEMO_PASSWORD)
    users = [
        User(username="aarav", email="aarav@demo.uniclyst.local", password_hash=pw,
             full_name="Aarav Mehta", role="organizer", college_id=colleges[0].id,
             interests=["robotics", "iot"], skills=["Arduino", "ROS"],
             goals="Build an autonomous rover and find vision collaborators."),
        User(username="meera", email="meera@demo.uniclyst.local", password_hash=pw,
             full_name="Meera Iyer", role="organizer", college_id=colleges[1].id,
             interests=["ai", "machine learning"], skills=["Machine Learning", "Computer Vision"],
             goals="Apply vision models to real hardware projects."),
        User(username="rohan", email="rohan@demo.uniclyst.local", password_hash=pw,
             full_name="Rohan Kapoor", role="organizer", college_id=colleges[2].id,
             interests=["design", "ui/ux"], skills=["UI/UX", "Branding"],
             goals="Design identities for inter-college tech events."),
        User(username="student", email="student@demo.uniclyst.local", password_hash=pw,
             full_name="Sana Ali", role="student", college_id=colleges[3].id,
             interests=["cybersecurity"], skills=["Linux", "Networking"],
             goals="Join a CTF team and meet collaborators from other colleges."),
        User(username="reviewer", email="reviewer@demo.uniclyst.local", password_hash=pw,
             full_name="Platform Reviewer", role="reviewer"),
        User(username="admin", email="admin@demo.uniclyst.local", password_hash=pw,
             full_name="Platform Admin", role="admin"),
    ]
    db.add_all(users)
    db.flush()

    db.add_all([
        CommunityMember(community_id=robotics_dtu.id, user_id=users[0].id, role="organizer"),
        CommunityMember(community_id=aims_iiitd.id, user_id=users[1].id, role="organizer"),
        CommunityMember(community_id=creative_nsut.id, user_id=users[2].id, role="organizer"),
    ])

    # ---- One in-flight demo collaboration (clearly demo data) ----
    req = CollaborationRequest(
        requester_community_id=robotics_dtu.id, requester_user_id=users[0].id,
        recipient_community_id=aims_iiitd.id,
        title="Vision stack for autonomous rover",
        goal="Autonomous robot perception",
        message="DTU Robotics is building an autonomous rover for RoboWars and needs a computer-vision "
                "pipeline for arena perception. AIMS has shipped vision models for drones — let's "
                "co-build the perception module and co-host a workshop.",
        needed_skills=["Computer Vision", "Machine Learning"],
        proposed_timeline="8 weeks",
        status="accepted", responded_at=_dt(-5),
    )
    db.add(req)
    db.flush()
    collab = Collaboration(
        request_id=req.id, title=req.title, goal=req.goal, status="active",
        summary="Accepted demo collaboration between Robotics Society DTU and AIMS IIIT-D.",
    )
    db.add(collab)
    db.flush()
    db.add_all([
        CollaborationMember(collaboration_id=collab.id, user_id=users[0].id,
                            community_id=robotics_dtu.id, role="lead"),
        CollaborationMember(collaboration_id=collab.id, user_id=users[1].id,
                            community_id=aims_iiitd.id, role="lead"),
        Milestone(collaboration_id=collab.id, title="Working perception demo",
                  description="Onboard detector running on the rover.", due_date=_dt(30).date()),
        Milestone(collaboration_id=collab.id, title="RoboWars submission freeze",
                  due_date=_dt(40).date()),
    ])

    db.commit()


def seed_if_empty() -> None:
    from ..models import User

    db = SessionLocal()
    try:
        if db.scalars(select(User)).first() is None:
            seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    from ..models import User

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalars(select(User)).first() is not None:
            print("Database already seeded — skipping.")
        else:
            seed(db)
            print("Seed complete (demo data, password: %s)." % settings.DEMO_PASSWORD)
    finally:
        db.close()
