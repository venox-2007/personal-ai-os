"""Demonstration tool for testing the human-in-the-loop approval workflow."""

from typing import Any, Dict
from app.permissions.levels import PermissionLevel
from app.tools.base import BaseTool, ToolResult


class DemoActionTool(BaseTool):
    """Harmless test tool for exercising Level 2 Human-in-the-Loop approval.

    Explicitly labeled as a test tool that performs simulated external changes
    without contacting or modifying any real-world external systems.
    """

    name: str = "request_demo_action"
    description: str = (
        "Demonstration tool for testing human-in-the-loop security authorization. "
        "Simulates a Level 2 external side effect (e.g. sending a message or updating an external record). "
        "Requires explicit user confirmation before running."
    )
    permission_level: PermissionLevel = PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "action_title": {
                "type": "string",
                "description": "Short title describing the simulated action.",
            },
            "target": {
                "type": "string",
                "description": "Simulated target recipient or external resource.",
            },
            "payload": {
                "type": "string",
                "description": "Simulated payload or message body.",
            },
        },
        "required": ["action_title"],
    }

    async def execute(
        self,
        action_title: str = "Sample Action",
        target: str = "demo@example.com",
        payload: str = "",
        **kwargs,
    ) -> ToolResult:
        """Executes simulated external action safely."""
        return ToolResult(
            success=True,
            output={
                "status": "success",
                "simulated": True,
                "message": f"Simulated external action '{action_title}' executed safely after human authorization.",
                "target": target,
                "payload": payload,
            },
            metadata={"test_tool": True},
        )
