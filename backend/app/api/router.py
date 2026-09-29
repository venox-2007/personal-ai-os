"""Main API router combining all sub-route endpoints."""

from fastapi import APIRouter
from app.api.routes.health import router as health_router
from app.api.routes.chat import router as chat_router
from app.api.routes.agents import router as agents_router
from app.api.routes.tools import router as tools_router
from app.api.routes.memory import router as memory_router
from app.api.routes.approvals import router as approvals_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(agents_router)
api_router.include_router(tools_router)
api_router.include_router(memory_router)
api_router.include_router(approvals_router)
