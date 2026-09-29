"""Tests for BaseTool and ToolRegistry."""

import pytest
from app.tools.base import BaseTool, ToolResult
from app.tools.registry import ToolRegistry
from app.permissions.levels import PermissionLevel


class DummySafeTool(BaseTool):
    name = "dummy_search"
    description = "A dummy read-only search tool"
    permission_level = PermissionLevel.LEVEL_0_READ_ONLY

    async def execute(self, query: str = "") -> ToolResult:
        return ToolResult(success=True, output=f"Found results for: {query}")


class DummyDestructiveTool(BaseTool):
    name = "dummy_delete"
    description = "A dummy destructive deletion tool"
    permission_level = PermissionLevel.LEVEL_3_DESTRUCTIVE

    async def execute(self, target: str = "") -> ToolResult:
        return ToolResult(success=True, output=f"Deleted: {target}")


@pytest.mark.asyncio
async def test_tool_execution():
    tool = DummySafeTool()
    assert tool.permission_level == PermissionLevel.LEVEL_0_READ_ONLY
    assert tool.requires_approval() is False

    result = await tool.execute(query="test")
    assert result.success is True
    assert "Found results" in result.output


def test_tool_registry_management():
    registry = ToolRegistry()
    safe_tool = DummySafeTool()
    dest_tool = DummyDestructiveTool()

    registry.register(safe_tool)
    registry.register(dest_tool)

    assert registry.get("dummy_search") == safe_tool
    assert len(registry.list_tools()) == 2

    # Filter by permission
    safe_only = registry.filter_by_permission(PermissionLevel.LEVEL_0_READ_ONLY)
    assert len(safe_only) == 1
    assert safe_only[0].name == "dummy_search"

    # Duplicate registration check
    with pytest.raises(ValueError):
        registry.register(safe_tool)
