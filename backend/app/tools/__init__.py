"""Tools package exposing BaseTool, ToolResult, ToolRegistry, and standard tools."""

from app.tools.base import BaseTool, ToolResult
from app.tools.registry import ToolRegistry, tool_registry
from app.tools.system_info import SystemInfoTool
from app.tools.demo_action import DemoActionTool

# Ensure standard tools are registered on the global default tool_registry
if not tool_registry.get("get_system_info"):
    tool_registry.register(SystemInfoTool())

if not tool_registry.get("request_demo_action"):
    tool_registry.register(DemoActionTool())

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolRegistry",
    "tool_registry",
    "SystemInfoTool",
    "DemoActionTool",
]
