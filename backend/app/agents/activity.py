"""Agent activity event models for user observability and UI updates."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, Field


class ActivityType(str, Enum):
    PLANNING = "planning"
    AGENT_SELECTED = "agent_selected"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    REASONING = "reasoning"
    STATUS_MESSAGE = "status_message"
    APPROVAL_REQUIRED = "approval_required"
    ERROR = "error"
    COMPLETED = "completed"


class ActivityStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"


class AgentActivityEvent(BaseModel):
    """An observable step or event produced during agent execution."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent: str = Field(description="Name of the agent producing this event")
    activity_type: ActivityType
    status: ActivityStatus = ActivityStatus.SUCCESS
    action: str = Field(description="Short human-readable summary of the action")
    description: Optional[str] = Field(default=None, description="Detailed explanation or log output")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "agent": self.agent,
            "activity_type": self.activity_type.value,
            "status": self.status.value,
            "action": self.action,
            "description": self.description,
            "metadata": self.metadata,
        }
