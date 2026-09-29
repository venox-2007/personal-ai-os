"""Pydantic schemas for chat requests and responses."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field
from app.agents.activity import AgentActivityEvent


class ChatMessageSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(min_length=1, description="User prompt or instruction")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    activities: List[AgentActivityEvent] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = Field(default="completed", description="Status: completed, waiting_approval, or error")
    metadata: Dict[str, Any] = Field(default_factory=dict)
