"""API v1 router assembly."""

from fastapi import APIRouter

<<<<<<< HEAD
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
=======
from . import auth, colleges, communities, events, health, users
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(colleges.router)
api_router.include_router(communities.router)
api_router.include_router(events.router)
<<<<<<< HEAD
api_router.include_router(matches.router)
api_router.include_router(discovery.router)
api_router.include_router(collaborations.router)
api_router.include_router(admin.router)
=======
>>>>>>> ed8fc0d44e0ce0f77ef9b664831c8d4dfa914647
