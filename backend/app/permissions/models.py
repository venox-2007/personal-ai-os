"""Data structures for permissions and human-in-the-loop approval handling."""

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, Field

from app.core.config import settings
from app.permissions.levels import PermissionLevel


class ApprovalStatus(str, Enum):
    """Lifecycle statuses for approval requests."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalRequest(BaseModel):
    """Represents a request for human-in-the-loop confirmation before consequential action execution."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    tool_description: str = ""
    permission_level: PermissionLevel
    arguments: Dict[str, Any] = Field(default_factory=dict)
    action_description: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        + timedelta(seconds=getattr(settings, "APPROVAL_EXPIRY_SECONDS", 300))
    )
    resolved_at: Optional[datetime] = None
    resolution_reason: Optional[str] = None
    conversation_id: Optional[str] = None
    execution_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Preserved orchestrator execution context (messages, turn) to resume after decision",
    )

    @property
    def is_expired(self) -> bool:
        if self.status != ApprovalStatus.PENDING:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def requested_at(self) -> datetime:
        return self.created_at

    @property
    def parameters(self) -> Dict[str, Any]:
        return self.arguments

    def __init__(self, **data: Any):
        # Support parameters alias for arguments if provided
        if "parameters" in data and "arguments" not in data:
            data["arguments"] = data.pop("parameters")
        if "requested_at" in data and "created_at" not in data:
            data["created_at"] = data.pop("requested_at")
        super().__init__(**data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "tool_description": self.tool_description,
            "permission_level": self.permission_level.value,
            "permission_label": self.permission_level.label,
            "arguments": self.arguments,
            "action_description": self.action_description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_reason": self.resolution_reason,
            "conversation_id": self.conversation_id,
        }


class PermissionContext(BaseModel):
    """Contextual security evaluator for tools and actions."""

    require_level_2_approval: bool = True
    require_level_3_approval: bool = True

    def requires_approval(self, level: PermissionLevel) -> bool:
        if level == PermissionLevel.LEVEL_3_DESTRUCTIVE:
            return self.require_level_3_approval
        if level == PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT:
            return self.require_level_2_approval
        return False
