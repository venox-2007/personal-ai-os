"""System info inspection tool."""

import platform
from typing import Any, Dict
from app.core.config import settings
from app.permissions.levels import PermissionLevel
from app.tools.base import BaseTool, ToolResult
from app.integrations.ollama_provider import OllamaProvider


class SystemInfoTool(BaseTool):
    """Retrieves operational status and configuration of the Personal AI OS."""

    name: str = "get_system_info"
    description: str = (
        "Retrieve operational system information including application version, "
        "operating system platform, configured LLM provider, and local inference reachability."
    )
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "detailed": {
                "type": "boolean",
                "description": "Whether to include detailed OS platform statistics.",
                "default": False,
            }
        },
        "required": [],
    }

    async def execute(self, detailed: bool = False, **kwargs) -> ToolResult:
        """Executes system inspection."""
        ollama = OllamaProvider()
        ollama_reachable = await ollama.is_available()

        data: Dict[str, Any] = {
            "application": settings.APP_NAME,
            "version": "0.1.0",
            "environment": settings.APP_ENV,
            "status": "healthy",
            "llm_provider": {
                "provider": settings.DEFAULT_LLM_PROVIDER,
                "configured_model": settings.OLLAMA_MODEL,
                "base_url": settings.OLLAMA_BASE_URL,
                "is_reachable": ollama_reachable,
            },
        }

        if detailed:
            data["platform"] = {
                "system": platform.system(),
                "release": platform.release(),
                "python_version": platform.python_version(),
            }

        return ToolResult(
            success=True,
            output=data,
            metadata={"source": "system_info_tool"},
        )
