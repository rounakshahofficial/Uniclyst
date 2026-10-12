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
| 2 | React + Vite + TypeScript + Tailwind frontend (dashboard, explore, profiles, onboarding) | ⏳ next |
| 3 | Explainable matching engine (weighted, documented components + reasons) | ⏳ |
| 4 | TinyFish-powered Community Scout (Search → Fetch → evidence-backed review) | ⏳ |
| 5 | Collaboration requests, shared workspace, milestones | ⏳ |
| 6 | Full test pass, deployment, demo script | ⏳ |

See [docs/architecture.md](docs/architecture.md) for the system design.

## Tech stack

- **Frontend** *(step 2)*: React, Vite, TypeScript, Tailwind CSS, React Router, TanStack Query, React Hook Form + Zod, Leaflet + OpenStreetMap
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

### 2. With PostgreSQL (recommended for realistic deployments)

```bash
docker compose up --build        # postgres:16 + API on :8000
```

Or bring your own PostgreSQL and point `DATABASE_URL` at it (see `.env.example`).
Migrations-first workflow (instead of `AUTO_CREATE_TABLES`):

```bash
export AUTO_CREATE_TABLES=0 AUTO_SEED=0
alembic upgrade head
python -m app.db.seed            # optional demo data
```

### 3. Run the tests

```bash
cd backend
.venv/bin/python -m pytest tests/ -q
```

24 tests cover auth/authorization, community CRUD, search & filters, events,
saved lists, and DB constraints (uniqueness, cascades, referential integrity).

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

## API overview (`/api/v1`)

| Method & path | Auth | Description |
| --- | --- | --- |
| `GET /health` | — | Status + DB connectivity (no secrets) |
| `POST /auth/register` · `POST /auth/login` · `POST /auth/logout` | — / bearer | JWT auth; logout revokes the token |
| `GET` `PATCH /users/me` | bearer | Profile & onboarding (interests, skills, goals, links) |
| `GET` `POST /users/me/saved[/{id}]` | bearer | Saved communities |
| `GET` `POST /colleges` | optional / organizer+ | Colleges with community counts |
| `GET /communities` | optional | Filter: `q, college_id, city, category, skill, interest, verification, sort` + pagination |
| `GET /communities/search?q=` | optional | Search name, description, college, skills |
| `POST /communities` | bearer | Create (auto `discovered`, creator becomes organizer) |
| `GET` `PATCH` `DELETE /communities/{id}` | optional / owner or reviewer | Profile, edit, delete |
| `POST /communities/{id}/join` · `DELETE /communities/{id}/leave` | bearer | Membership |
| `GET` `POST /events` | optional / organizer | Public events with source + freshness fields |

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

## TinyFish integration (step 4 — documented for the build)

Workflow per [docs.tinyfish.ai](https://docs.tinyfish.ai/): several targeted
**Search** queries (`GET api.search.tinyfish.ai`) → **Fetch** page content
(`POST api.fetch.tinyfish.ai`) → normalize → validate/dedupe → store evidence
records (`discovery_sources`) for reviewer approval. **Agent**
(`agent.tinyfish.ai/v1/automation/run-sse`) only for pages that need browser
interaction. Without credentials the app runs a clearly-labelled **demo mode**
using seeded discovery data — the review pipeline stays identical.

## Project structure

```
uniclyst/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # route handlers (health, auth, users, colleges, communities, events)
│   │   ├── core/            # config, security (JWT + PBKDF2), error envelope
│   │   ├── db/              # engine/session, seed script
│   │   ├── models/          # SQLAlchemy ORM — 16 tables (Campus Opportunity Graph)
│   │   ├── repositories/    # queries & serialization
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/        # matching engine & TinyFish scout (steps 3–4)
│   │   └── main.py
│   ├── alembic/             # migrations (`alembic upgrade head`)
│   ├── tests/               # 24 pytest tests (auth, communities, constraints)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # React + Vite + TS + Tailwind (step 2)
├── docs/architecture.md
├── docker-compose.yml       # PostgreSQL 16 + API
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
