"""
api/v1/__init__.py — Central v1 API router.

All feature routers are registered here. This module is imported by main.py
which mounts everything under /api/v1.

Day 1 routes (Palash): auth, health
Day 2+ routes (rest of team): sessions, flows, mentor, comments, history, admin
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router

# Root v1 router — prefix applied by main.py's include_router call
v1_router = APIRouter()

# ── Auth ───────────────────────────────────────────────────────────────────────
v1_router.include_router(auth_router)

# ── Health (no prefix — mounted at root level) ─────────────────────────────────
# Health endpoints are also registered separately at root level in main.py
# so they work both as /health and /api/v1/health

# ── Day 2 routes — uncomment as teammates merge their branches ─────────────────
# from app.api.v1.sessions import router as sessions_router
# from app.api.v1.flows import router as flows_router
# from app.api.v1.history import router as history_router
# from app.api.v1.comments import router as comments_router
# from app.api.v1.mentor import router as mentor_router
# from app.api.v1.admin import router as admin_router
#
# v1_router.include_router(sessions_router)
# v1_router.include_router(flows_router)
# v1_router.include_router(history_router)
# v1_router.include_router(comments_router)
# v1_router.include_router(mentor_router)
# v1_router.include_router(admin_router)
