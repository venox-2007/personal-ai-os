"""Tool discovery routes."""

from typing import Any, Dict, List
from fastapi import APIRouter
from app.tools.registry import tool_registry

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.get("", response_model=List[Dict[str, Any]])
async def list_registered_tools() -> List[Dict[str, Any]]:
    """Lists all registered tools and their declared permission levels."""
    return [tool.to_dict() for tool in tool_registry.list_tools()]
