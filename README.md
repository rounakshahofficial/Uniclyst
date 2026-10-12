# Uniclyst — Connect Beyond Boundaries

An AI-powered inter-college collaboration platform for **AZINHACK 2026**. Uniclyst
connects student clubs, technical communities, and innovators across colleges —
so they can discover each other, find complementary skills, and turn a shared
interest into a real, tracked collaboration.

**Core differentiator:** intelligent cross-community collaboration — not a
college directory or an event board. Discovery → explainable matching →
collaboration request → acceptance → milestones, with every discovered fact
traced back to its source.

## Features (build roadmap)

| # | Feature | Status |
| --- | --- | --- |
| 1 | FastAPI backend, PostgreSQL/SQLite, Alembic, JWT auth, core community APIs | ✅ done |
| 2 | Explainable matching engine (`GET /api/v1/matches`, weights 25/35/25/10/5) | ✅ done |
| 3 | TinyFish Community Scout: discovery jobs, evidence, review & import | ✅ done |
| 4 | Collaboration workflow: proposals → accept/reject/withdraw → workspace + milestones | ✅ done |
| 5 | React + Vite + TypeScript + Tailwind frontend, connected to all APIs | ✅ done |
| 6 | Security hardening: registration role-escalation fix, admin-only role grants | ✅ done |

See [docs/architecture.md](docs/architecture.md) for the system design.

## Tech stack

- **Frontend**: React 18, Vite 5, TypeScript, Tailwind CSS, React Router, TanStack Query, React Hook Form + Zod
- **Backend**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PyJWT, Pytest
- **Database**: PostgreSQL 16 (Docker) / SQLite (zero-config local dev) — same SQLAlchemy models
- **Web intelligence**: [TinyFish](https://docs.tinyfish.ai/) Search + Fetch APIs (Agent API for dynamic pages), server-side only

## Quick start

### 1. Backend (works out of the box with SQLite)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

That's it — tables are created and demo data is seeded automatically on first
startup (controlled by `AUTO_CREATE_TABLES` / `AUTO_SEED`). Interactive API docs:
**http://localhost:8000/docs** · Health: **http://localhost:8000/api/v1/health**

### 2. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api to :8000)
```

### 3. With PostgreSQL (recommended for realistic deployments)

```bash
cp .env.example .env    # set POSTGRES_PASSWORD and JWT_SECRET — compose refuses to start without them
docker compose up --build
```

Compose runs migrations-first (`AUTO_CREATE_TABLES=0`, `AUTO_SEED=0` by default).
Seed demo data explicitly with `python -m app.db.seed` when you want it.

### 4. Run the tests

```bash
cd backend
.venv/bin/python -m pytest tests/ -q
```

**54 tests** cover auth (including the registration role-escalation regression),
authorization, community CRUD, search & filters, events, matching, TinyFish
discovery (mocked API responses), collaboration workflows, and DB constraints.

## Demo seed accounts

Seeded only when `AUTO_SEED=1` (dev/demo). Password: `demo123` (override with
`DEMO_PASSWORD`). All seed communities carry `is_demo = 1` and demo emails use
the reserved `demo.uniclyst.local` domain.

| Username | Role | Notes |
| --- | --- | --- |
| `aarav` | organizer | Robotics Society DTU — "needs computer vision" demo flow |
| `meera` | organizer | AIMS (IIIT-D) — AI/vision partner in the demo flow |
| `rohan` | organizer | Creative Studio NSUT |
| `student` | student | Generic student |
| `reviewer` | reviewer | Can promote `discovered → reviewed → verified` |
| `admin` | admin | Assigns reviewer/admin roles (`POST /api/v1/admin/users/{id}/role`) |

**Roles & security:** public registration *always* creates a `student` account —
the API rejects any attempt to set a role at signup (there is deliberately no
`role` field). A student becomes an `organizer` by creating a community
(controlled onboarding). `reviewer`/`admin` can only be granted by an existing
administrator. Community verification is reviewer-only.

## API overview (`/api/v1`)

| Method & path | Auth | Description |
| --- | --- | --- |
| `GET /health` | — | Status + DB connectivity (no secrets) |
| `POST /auth/register` · `POST /auth/login` · `POST /auth/logout` | — / bearer | JWT auth; registration is always `student`; logout revokes the token |
| `GET` `PATCH /users/me` | bearer | Profile & onboarding (interests, skills, goals, links) |
| `GET` `POST` `DELETE /users/me/saved[/{id}]` | bearer | Saved communities |
| `GET` `POST /colleges` | optional / bearer | Colleges with community counts |
| `GET /communities` | optional | Filter: `q, college_id, city, category, skill, interest, verification, sort` + pagination |
| `GET /communities/search?q=` | optional | Search name, description, college, skills |
| `POST /communities` | bearer | Create (auto `discovered`, creator becomes organizer) |
| `GET` `PATCH` `DELETE /communities/{id}` | optional / owner or reviewer | Profile, edit, delete |
| `POST /communities/{id}/join` · `DELETE /communities/{id}/leave` | bearer | Membership |
| `GET` `POST /events` | optional / organizer | Public events with source + freshness fields |
| `GET /matches` | optional | Explainable ranked partners: `community_id, goal, needed_skills, exclude, min_score` |
| `POST` `GET /discovery/jobs` · `GET /discovery/jobs/{id}` | bearer | Community Scout runs (live TinyFish or labelled demo mode) |
| `GET /discovery/sources` · `PATCH /discovery/sources/{id}` | bearer / reviewer | Evidence records; promotion to `verified` is reviewer-only |
| `POST /discovery/sources/{id}/import` | bearer | Approve an extracted record into the network (as `discovered`) |
| `POST /collaboration-requests` · `GET /collaboration-requests` | bearer | Proposals (organizers only; no duplicate pending) |
| `PATCH /collaboration-requests/{id}` | bearer | `accept` (recipient) · `reject` · `withdraw` (author/requester) |
| `GET /collaborations` · `GET /collaborations/{id}` | bearer | Shared workspace (participants only) |
| `PATCH /collaborations/{id}` · `POST …/milestones` · `PATCH /milestones/{id}` | bearer | Track milestones & completion |
| `POST /admin/users/{id}/role` · `GET /admin/users` | admin | Trusted role assignment |

Conventions:

- Errors: `{"error": {"code": "…", "message": "…", "details": …}}`
- Collections: `{"items": [...], "total", "page", "page_size", "pages"}`
- Permissions are enforced **on the backend**: verification status is
  reviewer-only, community edits are organizer/reviewer-only, deletes are
  creator/reviewer-only.

## Environment variables

Copy [.env.example](.env.example) → `.env`. Summary:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://…` or `sqlite:///…` |
| `JWT_SECRET` | Long random string (required in production) |
| `AUTO_CREATE_TABLES` / `AUTO_SEED` | Dev/demo conveniences — `0` in production |
| `DEMO_PASSWORD` | Password for documented seed accounts |
| `TINYFISH_API_KEY` | Optional — enables live Community Scout (step 4) |

**Never commit real API keys.** The TinyFish key is used exclusively on the
backend; it is never included in frontend code or responses.

## Matching engine (`services/matching.py`)

```
S = 0.25·I + 0.35·C + 0.25·G + 0.10·L + 0.05·A
```

Interest compatibility · complementary skill coverage · project goal alignment ·
geographic feasibility · profile completeness & freshness. Every recommendation
returns component scores **and** human-readable reasons plus honest uncertainty
notes. Missing data degrades gracefully (neutral baselines) instead of unfairly
penalizing thin profiles. Self-matches, duplicates, exclusions and a
minimum-relevance threshold are handled. These weights are a configurable
design choice — **not** a trained machine-learning model; semantic embeddings
can be added later if they measurably improve results.

## TinyFish integration

Workflow per [docs.tinyfish.ai](https://docs.tinyfish.ai/): several targeted
**Search** queries (`GET api.search.tinyfish.ai`) → **Fetch** page content
(`POST api.fetch.tinyfish.ai`) → normalize → validate/dedupe → store evidence
records (`discovery_sources`) for reviewer approval. **Agent**
(`agent.tinyfish.ai/v1/automation/run-sse`) only for pages that need browser
interaction. All calls happen on the backend — the API key never reaches the
browser. Without credentials the scout runs a clearly-labelled **demo mode**
(`origin=seed`) using a curated corpus — the extraction → validation → dedupe →
review pipeline is identical in both modes, and demo data is never presented as
live web discovery. Safeguards: timeouts, bounded retries, caching (`ttl`),
request logging, no unrestricted crawling, no invented facts, and social
follower counts are never treated as evidence of activity.

## Project structure

```
uniclyst/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # routes (health, auth, users, colleges, communities,
│   │   │                    #   events, matches, discovery, collaborations, admin)
│   │   ├── core/            # config, security (JWT + PBKDF2), error envelope
│   │   ├── db/              # engine/session, seed script
│   │   ├── models/          # SQLAlchemy ORM — 17 tables (Campus Opportunity Graph)
│   │   ├── repositories/    # queries & serialization
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/        # matching engine, TinyFish scout
│   │   └── main.py
│   ├── alembic/             # migrations (`alembic upgrade head`)
│   ├── tests/               # 54 pytest tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # React + Vite + TS + Tailwind
│   └── src/
│       ├── components/      # design system, layout, community cards
│       ├── pages/           # landing, auth, onboarding, dashboard, explore,
│       │                    #   community profile, matches, discovery, collaborations
│       ├── services/        # (lib/) typed API client
│       └── types/
├── docs/architecture.md
├── docker-compose.yml       # PostgreSQL 16 + API (env-managed secrets)
├── .env.example
└── README.md
```

## Hackathon demo script (target)

1. Robotics community (`aarav`) describes a project needing computer vision.
2. Community Scout discovers/loads source-backed info about AIMS (IIIT-D).
3. Matching recommends AIMS with an explanation and score breakdown.
4. `aarav` sends a collaboration proposal.
5. `meera` accepts — a shared workspace with milestones appears for both.
6. The evaluator inspects source records (`discovery_sources`) and `/docs`.

## License

MIT (hackathon submission).
