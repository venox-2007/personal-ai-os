"""Data structures for permissions and approval handling."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import uuid

from app.permissions.levels import PermissionLevel


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequest(BaseModel):
    """Represents a request for human-in-the-loop confirmation before action execution."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    permission_level: PermissionLevel
    action_description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None
    reason: Optional[str] = None


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
