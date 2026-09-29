"""Base agent abstraction for Personal AI OS."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentRunResult(BaseModel):
    """Result of an agent task execution."""

    agent_name: str
    task: str
    success: bool
    summary: str
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class BaseAgent(ABC):
    """Abstract base class for all specialized and general agents.

    Each agent encapsulates:
    - name: Unique identifier for the agent
    - description: Purpose and specialization of the agent
    - tools: Names of registered tools accessible by this agent
    - run(): Asynchronous task execution method
    """

    name: str
    description: str
    tools: List[str] = []

    @abstractmethod
    async def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentRunResult:
        """Execute a task with optional contextual input."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Serializes agent metadata for registry listing and API responses."""
        return {
            "name": self.name,
            "description": self.description,
            "tools": self.tools,
        }
