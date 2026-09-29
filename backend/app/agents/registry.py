"""Agent registry for dynamic registration, discovery, and lookup."""

from typing import Dict, List, Optional
from app.agents.base import BaseAgent


class AgentRegistry:
    """Central registry where specialized agents register and can be discovered."""

    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent instance."""
        if agent.name in self._agents:
            raise ValueError(f"Agent '{agent.name}' is already registered.")
        self._agents[agent.name] = agent

    def get(self, name: str) -> Optional[BaseAgent]:
        """Lookup an agent by name."""
        return self._agents.get(name)

    def list_agents(self) -> List[BaseAgent]:
        """List all currently registered agents."""
        return list(self._agents.values())

    def unregister(self, name: str) -> None:
        """Unregister an agent by name."""
        self._agents.pop(name, None)

    def clear(self) -> None:
        """Clear all registered agents (primarily for testing)."""
        self._agents.clear()


# Global default instance
agent_registry = AgentRegistry()
