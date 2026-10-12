"""API v1 router assembly."""

from fastapi import APIRouter

from . import (
    admin,
    auth,
    colleges,
    communities,
    collaborations,
    discovery,
    events,
    health,
    matches,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(colleges.router)
api_router.include_router(communities.router)
api_router.include_router(events.router)
api_router.include_router(matches.router)
api_router.include_router(discovery.router)
api_router.include_router(collaborations.router)
api_router.include_router(admin.router)
