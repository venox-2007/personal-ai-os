"""Tool registry for registering and discovering available tools."""

from typing import Dict, List, Optional
from app.permissions.levels import PermissionLevel
from app.tools.base import BaseTool


class ToolRegistry:
    """Central registry for discovering, registering, and retrieving tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a new tool instance."""
        if tool.name in self._tools:
            raise ValueError(f"Tool with name '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool by its unique name."""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """List all registered tools."""
        return list(self._tools.values())

    def filter_by_permission(self, max_level: PermissionLevel) -> List[BaseTool]:
        """Return tools whose permission level is at or below the given threshold."""
        return [t for t in self._tools.values() if t.permission_level <= max_level]

    def clear(self) -> None:
        """Reset registry (primarily for testing)."""
        self._tools.clear()


# Global default instance
tool_registry = ToolRegistry()
