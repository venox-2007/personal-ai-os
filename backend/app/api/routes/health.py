"""Health check route."""

from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse, ComponentHealth
from app.integrations.ollama_provider import OllamaProvider
from app.integrations.llm_provider import ModelAvailabilityStatus
from app.agents.registry import agent_registry
from app.tools.registry import tool_registry

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Returns application health status and subcomponent readiness."""
    ollama = OllamaProvider()
    model_status = await ollama.check_model_status()

    if model_status == ModelAvailabilityStatus.AVAILABLE:
        llm_status_str = "online_model_ready"
    elif model_status == ModelAvailabilityStatus.MODEL_NOT_FOUND:
        llm_status_str = "online_model_missing"
    else:
        llm_status_str = "offline_or_unreachable"

    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version="0.1.0",
        environment=settings.APP_ENV,
        components={
            "api": ComponentHealth(status="healthy", details={"debug": settings.APP_DEBUG}),
            "database": ComponentHealth(status="healthy", details={"engine": "sqlite"}),
            "llm_provider": ComponentHealth(
                status=llm_status_str,
                details={
                    "provider": settings.DEFAULT_LLM_PROVIDER,
                    "base_url": settings.OLLAMA_BASE_URL,
                    "target_model": settings.OLLAMA_MODEL,
                    "model_status": model_status.value,
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
