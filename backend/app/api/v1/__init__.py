"""API v1 router assembly."""

from fastapi import APIRouter

from . import auth, colleges, communities, events, health, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(colleges.router)
api_router.include_router(communities.router)
api_router.include_router(events.router)
