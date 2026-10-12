# Uniclyst — Architecture

> Connect Beyond Boundaries.
> An AI-powered inter-college collaboration platform: discovery, explainable
> matching, web-sourced community intelligence, and tracked collaborations.

## System overview

```
 Student / Club organizer / Reviewer
              │
              ▼
   React + Vite + TypeScript + Tailwind      (frontend/, Vite dev proxy → :8000)
              │  REST /api/v1  (JWT bearer)
              ▼
   FastAPI application                       (backend/app)
   ┌──────────────────────────────────────────────────────────┐
   │  api/v1/          route handlers (HTTP concerns only)    │
   │  repositories/    queries & serialization                │
   │  services/        matching engine, TinyFish scout        │
   │  core/            config, security (JWT/PBKDF2), errors  │
   │  models/          SQLAlchemy ORM (Campus Opportunity     │
   │                   Graph: colleges ↔ communities ↔        │
   │                   skills ↔ events ↔ collaborations)      │
   └──────────────────────────────────────────────────────────┘
              │                          │
              ▼                          ▼
   PostgreSQL (prod) / SQLite (dev)     TinyFish APIs (server-side only)
   via SQLAlchemy 2 + Alembic           Search · Fetch · Agent (as needed)
```

## Key decisions

| Decision | Rationale |
| --- | --- |
| **Backend-only external calls** | The TinyFish API key never reaches the browser. All scraping/extraction happens in `services/tinyfish_scout.py`. |
| **Demo mode without credentials** | Without `TINYFISH_API_KEY` the scout runs against a curated corpus and labels every result `mode: demo`. The extraction → validation → dedupe → review pipeline is identical in both modes. |
| **PostgreSQL + SQLAlchemy, no graph DB** | The Campus Opportunity Graph is a relational model (M2M tables + FKs). A dedicated graph database is unnecessary at MVP scale. |
| **JWT + revocation list** | Stateless auth with a `revoked_tokens` denylist so `POST /auth/logout` is real, not cosmetic. |
| **Human-gated verification** | Discovery never auto-verifies. Records move `discovered → reviewed → verified` only via reviewer action. Confidence scores are transparent heuristics, not probabilities. |
| **Explainable matching (no ML training)** | Weighted, normalized, testable components (see below). Designed so semantic embeddings can be added later *if* they measurably improve results. |

## Matching engine (`services/matching.py`, build step 3)

Configurable weights (initial design choice — not experimentally validated):

```
S = 0.25·I + 0.35·C + 0.25·G + 0.10·L + 0.05·A

I = interest compatibility          C = complementary skill coverage
G = project goal alignment          L = geographic feasibility
A = profile completeness & freshness
```

Every recommendation returns component scores **and** human-readable reasons
("Recommended because your robotics project needs computer vision expertise and
this community lists relevant AI/vision capabilities"). Missing data degrades
gracefully instead of unfairly penalizing thin profiles. Self-matches are
excluded; duplicates and below-threshold results are dropped.

## Community Scout (`services/tinyfish_scout.py`, build step 4)

1. **Search** — `GET https://api.search.tinyfish.ai?query=…` (several targeted queries, `X-API-Key` header)
2. **Fetch** — `POST https://api.fetch.tinyfish.ai` `{urls, format: "markdown"}`
3. **Agent** — `POST https://agent.tinyfish.ai/v1/automation/run-sse` only for dynamic pages
4. **Extract** — normalize to a fixed schema (name, college, city, interests, skills, URLs, events, evidence excerpts, timestamps, missing/conflicting info)
5. **Validate & dedupe** — normalized names/URLs vs stored records; flag conflicts
6. **Store** — `discovery_jobs` + `discovery_sources` rows with retrieval timestamps and `review_status = discovered`

Safeguards: timeouts, retry limits, response caching (`ttl`), request logging,
no unrestricted crawling, no invented facts, social-follower counts are never
treated as evidence of activity.

## Data model (16 tables)

- `users`, `colleges`, `skills` — core entities
- `communities`, `community_members`, `community_skills`, `projects`, `saved_communities` — community graph
- `events` — public listings with source URL + freshness
- `discovery_jobs`, `discovery_sources` — scout runs and evidence records
- `collaboration_requests`, `collaborations`, `collaboration_members`, `milestones` — the workflow
- `revoked_tokens` — JWT logout denylist

Relationships use explicit `ondelete` rules (CASCADE for owned rows, SET NULL
for evidence preservation, RESTRICT for colleges). Uniqueness constraints
prevent duplicate memberships, duplicate skills per community, duplicate
saves, and one collaboration per request.

## Error handling

All errors return a consistent envelope:

```json
{ "error": { "code": "forbidden", "message": "…", "details": … } }
```

Collection endpoints paginate with `{items, total, page, page_size, pages}`.

## Security

- PBKDF2-SHA256 password hashing (120k iterations, per-user salt)
- JWT access tokens (HS256), short expiry, server-side revocation on logout
- Role checks (`student | organizer | reviewer | admin`) enforced in the backend
- Secrets from environment variables only; `.env.example` holds placeholders
- Health endpoint reports status without leaking configuration

## Build status

| Phase | Scope | Status |
| --- | --- | --- |
| 1 | Repo, FastAPI, DB models, Alembic, auth, core community APIs, tests | **done** |
<<<<<<< HEAD
| 2 | Matching engine (`services/matching.py`, `GET /api/v1/matches`) + tests | **done** |
| 3 | TinyFish discovery pipeline (`services/tinyfish_scout.py`), review & import | **done** |
| 4 | Collaboration requests → workspace → milestones + tests | **done** |
| 5 | React + Vite + TS + Tailwind frontend, wired to live APIs | **done** |
| 6 | Security hardening (registration role-escalation fix, admin role grants) | **done** |
=======
| 2 | React + Vite + TS + Tailwind frontend | planned |
| 3 | Explainable matching engine + tests | planned |
| 4 | TinyFish discovery pipeline + review UI | planned |
| 5 | Collaboration requests → workspaces → milestones | planned |
| 6 | Full test pass, deployment, demo script | planned |
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
