"""Agent inspection routes."""

from typing import Any, Dict, List
from fastapi import APIRouter
from app.agents.registry import agent_registry

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("", response_model=List[Dict[str, Any]])
async def list_registered_agents() -> List[Dict[str, Any]]:
    """Lists all registered agents in the system."""
    return [agent.to_dict() for agent in agent_registry.list_agents()]
