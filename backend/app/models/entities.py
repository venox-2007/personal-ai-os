"""Database models for Personal AI OS."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Integer,
    Boolean,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConversationModel(Base):
    """Stores user conversations with the Orchestrator."""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False, default="New Conversation")
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRunModel", back_populates="conversation", cascade="all, delete-orphan")


class MessageModel(Base):
    """Stores individual messages within a conversation."""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(32), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    metadata_json = Column(Text, nullable=True)

    conversation = relationship("ConversationModel", back_populates="messages")


class MemoryModel(Base):
    """Persistent storage for explicit, durable memories."""

    __tablename__ = "memories_v2"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    content = Column(Text, nullable=False)
    memory_type = Column(String(32), nullable=False)
    category = Column(String(64), nullable=True)
    source = Column(String(64), nullable=False, default="USER_EXPLICIT")
    importance = Column(Float, nullable=False, default=0.5)
    confidence = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    last_accessed_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, nullable=False, default=0)
    is_archived = Column(Boolean, nullable=False, default=False)
    metadata_json = Column(Text, nullable=True)


class AgentRunModel(Base):
    """Tracks execution lifecycles of orchestrator and specialized agent tasks."""

    __tablename__ = "agent_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    agent_name = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="running")  # running, completed, failed, paused
    input_task = Column(Text, nullable=False)
    output_summary = Column(Text, nullable=True)
    started_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    conversation = relationship("ConversationModel", back_populates="agent_runs")
    tool_executions = relationship("ToolExecutionModel", back_populates="agent_run", cascade="all, delete-orphan")
    approvals = relationship("ApprovalRequestModel", back_populates="agent_run", cascade="all, delete-orphan")


class ToolExecutionModel(Base):
    """Audit log of individual tool invocations and outcomes."""

    __tablename__ = "tool_executions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    tool_name = Column(String(64), nullable=False)
    permission_level = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="started")  # started, success, failed, rejected
    input_json = Column(Text, nullable=True)
    output_json = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=utc_now, nullable=False)

    agent_run = relationship("AgentRunModel", back_populates="tool_executions")


class ApprovalRequestModel(Base):
    """Human-in-the-loop pending and completed approvals."""

    __tablename__ = "approvals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    tool_name = Column(String(64), nullable=False)
    permission_level = Column(Integer, nullable=False)
    action_description = Column(Text, nullable=False)
    arguments_json = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="pending")  # pending, approved, rejected, expired, cancelled
    requested_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    decided_by = Column(String(64), nullable=True)
    resolution_reason = Column(Text, nullable=True)
    execution_context_json = Column(Text, nullable=True)

    agent_run = relationship("AgentRunModel", back_populates="approvals")


class SettingModel(Base):
    """Key-value system and user preferences."""

    __tablename__ = "settings"

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class CalendarEventModel(Base):
    """Local calendar event domain model."""

    __tablename__ = "calendar_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    all_day = Column(Boolean, default=False, nullable=False)
    timezone = Column(String(64), nullable=False, default="UTC")
    recurrence_rule = Column(String(255), nullable=True)
    status = Column(String(32), default="CONFIRMED", nullable=False)
    calendar_name = Column(String(128), default="Default", nullable=False)
    calendar_id = Column(String(128), default="default", nullable=False)
    ics_uid = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class WorkflowModel(Base):
    __tablename__ = "workflows"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    goal = Column(Text, nullable=False)
    status = Column(String(32), default="PENDING", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    synthesis_result = Column(Text, nullable=True)

    steps = relationship("WorkflowStepModel", back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowStepModel.sequence")

class WorkflowStepModel(Base):
    __tablename__ = "workflow_steps"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_id = Column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    step_id = Column(String(64), nullable=False)
    sequence = Column(Integer, nullable=False)
    agent_name = Column(String(64), nullable=False)
    tool_name = Column(String(64), nullable=False)
    input_mapping_json = Column(Text, nullable=False, default="{}")
    depends_on_json = Column(Text, nullable=False, default="[]")
    status = Column(String(32), default="PENDING", nullable=False)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    requires_approval = Column(Boolean, default=False, nullable=False)
    on_failure = Column(String(32), default="FAIL", nullable=False)
    output_json = Column(Text, nullable=True)
    approval_id = Column(String(36), nullable=True)

    workflow = relationship("WorkflowModel", back_populates="steps")

class RecommendationModel(Base):
    """Proactive recommendation model."""
    __tablename__ = "recommendations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    category = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    priority = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="active")  # active, dismissed, completed, expired
    deduplication_key = Column(String(255), nullable=False, unique=True, index=True)
    suggested_agent = Column(String(64), nullable=True)
    suggested_workflow_goal = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    due_at = Column(DateTime, nullable=True)
