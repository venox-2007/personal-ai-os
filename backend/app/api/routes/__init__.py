"""API routes module."""

from app.api.routes.health import router as health_router
from app.api.routes.chat import router as chat_router
from app.api.routes.agents import router as agents_router
from app.api.routes.tools import router as tools_router
from app.api.routes.memory import router as memory_router

__all__ = [
    "health_router",
    "chat_router",
    "agents_router",
    "tools_router",
    "memory_router",
]
