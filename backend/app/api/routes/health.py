"""Health check route."""

from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse, ComponentHealth
from app.integrations.ollama_provider import OllamaProvider
from app.agents.registry import agent_registry
from app.tools.registry import tool_registry

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Returns application health status and subcomponent readiness."""
    ollama = OllamaProvider()
    ollama_ready = await ollama.is_available()

    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version="0.1.0",
        environment=settings.APP_ENV,
        components={
            "api": ComponentHealth(status="healthy", details={"debug": settings.APP_DEBUG}),
            "database": ComponentHealth(status="healthy", details={"engine": "sqlite"}),
            "llm_provider": ComponentHealth(
                status="online" if ollama_ready else "offline_or_unreachable",
                details={
                    "provider": settings.DEFAULT_LLM_PROVIDER,
                    "base_url": settings.OLLAMA_BASE_URL,
                    "target_model": settings.OLLAMA_MODEL,
                },
            ),
            "agents": ComponentHealth(
                status="ready",
                details={"registered_count": len(agent_registry.list_agents())},
            ),
            "tools": ComponentHealth(
                status="ready",
                details={"registered_count": len(tool_registry.list_tools())},
            ),
        },
    )
