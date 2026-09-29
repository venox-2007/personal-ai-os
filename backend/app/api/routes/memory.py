"""Memory inspection routes."""

from typing import Any, Dict
from fastapi import APIRouter
from app.memory.storage import memory_manager

router = APIRouter(prefix="/memory", tags=["Memory"])


@router.get("/stats", response_model=Dict[str, Any])
async def get_memory_stats() -> Dict[str, Any]:
    """Returns statistics on active memory facets."""
    return await memory_manager.get_stats()
