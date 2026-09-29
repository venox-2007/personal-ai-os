"""Base tool abstractions and execution result definitions."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, Field

from app.permissions.levels import PermissionLevel


class ToolResult(BaseModel):
    """Encapsulates the output or error from executing a tool."""

    success: bool
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """Abstract base class for all tools in Personal AI OS.

    Each tool must explicitly declare:
    - name: Unique identifier
    - description: Explains tool purpose to agents and users
    - permission_level: Security level (Level 0 through Level 3)
    - parameters_schema: JSON Schema or dict defining expected arguments
    """

    name: str
    description: str
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with validated arguments."""
        pass

    def requires_approval(self) -> bool:
        """Determines whether calling this tool requires user confirmation."""
        return self.permission_level.requires_approval_default

    def validate_arguments(self, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validates invocation arguments against parameters_schema."""
        if not isinstance(arguments, dict):
            return False, f"Arguments must be a JSON dictionary, got {type(arguments).__name__}"

        schema = self.parameters_schema or {}
        required_keys = schema.get("required", [])
        for key in required_keys:
            if key not in arguments:
                return False, f"Missing required parameter: '{key}'"

        return True, None

    def to_llm_tool_definition(self) -> Dict[str, Any]:
        """Converts tool declaration into OpenAI/Ollama compatible function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema if self.parameters_schema else {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serializes tool metadata for discovery and inspection."""
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "permission_label": self.permission_level.label,
            "requires_approval": self.requires_approval(),
            "parameters_schema": self.parameters_schema,
        }
