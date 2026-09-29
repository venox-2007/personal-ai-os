"""Health check response schemas."""

from typing import Any, Dict
from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str = "0.1.0"
    environment: str
    components: Dict[str, ComponentHealth] = Field(default_factory=dict)
