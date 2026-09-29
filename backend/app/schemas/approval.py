"""Schemas for approval endpoints and interactive authorization decisions."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.agents.activity import AgentActivityEvent


class ApprovalDecisionRequest(BaseModel):
    """Payload sent by the client when resolving an approval request."""

    reason: Optional[str] = Field(default=None, description="Optional user-provided reason or justification")


class ApprovalItemSchema(BaseModel):
    """Serialized summary of an approval request."""

    id: str
    tool_name: str
    tool_description: str = ""
    permission_level: int
    permission_label: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    action_description: str
    status: str
    created_at: str
    expires_at: str
    resolved_at: Optional[str] = None
    resolution_reason: Optional[str] = None
    conversation_id: Optional[str] = None


class ApprovalExecutionResponse(BaseModel):
    """Response returned after an approval decision resumes the agent execution flow."""

    approval_id: str
    status: str
    tool_name: str
    response: str
    activities: List[AgentActivityEvent] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    conversation_id: Optional[str] = None
