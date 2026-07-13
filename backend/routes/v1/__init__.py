"""
api/v1/__init__.py — Central v1 API router.

All feature routers are registered here. This module is imported by main.py
which mounts everything under /api/v1.

Day 1 routes (Palash): auth, health
Day 2 routes: sessions, flows, history
Day 3+ routes: comments, mentor, admin (registered below once implemented)
"""

from fastapi import APIRouter

from routes.v1.auth import router as auth_router
from routes.v1.health import router as health_router
from routes.v1.sessions import router as sessions_router
from routes.v1.flows import router as flows_router
from routes.v1.history import router as history_router
from routes.v1.admin import router as admin_router
from routes.v1.comments import router as comments_router
from routes.v1.mentor import router as mentor_router

v1_router = APIRouter()

v1_router.include_router(auth_router)
v1_router.include_router(sessions_router)
v1_router.include_router(flows_router)
v1_router.include_router(history_router)
v1_router.include_router(comments_router)
v1_router.include_router(mentor_router)
v1_router.include_router(admin_router, prefix="/admin")