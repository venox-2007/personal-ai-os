"""Tests for BaseAgent and AgentRegistry."""

import pytest
from app.agents.base import BaseAgent, AgentRunResult
from app.agents.registry import AgentRegistry
from app.agents.activity import AgentActivityEvent, ActivityType, ActivityStatus


class SampleStudyAgent(BaseAgent):
    name = "study_agent"
    description = "Specialized agent for RAG notes, quizzes, and study planning."
    tools = ["retrieve_notes", "generate_quiz"]

    async def run(self, task: str, context=None) -> AgentRunResult:
        return AgentRunResult(
            agent_name=self.name,
            task=task,
            success=True,
            summary=f"Study plan created for: {task}",
        )


@pytest.mark.asyncio
async def test_agent_run():
    agent = SampleStudyAgent()
    assert agent.name == "study_agent"
    assert len(agent.tools) == 2

    result = await agent.run(task="Review CS fundamentals")
    assert result.success is True
    assert "Study plan created" in result.summary


def test_agent_registry():
    registry = AgentRegistry()
    agent = SampleStudyAgent()

    registry.register(agent)
    assert registry.get("study_agent") == agent
    assert len(registry.list_agents()) == 1

    # Duplicate check
    with pytest.raises(ValueError):
        registry.register(agent)

    registry.unregister("study_agent")
    assert registry.get("study_agent") is None


def test_agent_activity_event():
    event = AgentActivityEvent(
        agent="GmailAgent",
        activity_type=ActivityType.TOOL_STARTED,
        status=ActivityStatus.RUNNING,
        action="Searching unread emails",
    )
    serialized = event.to_dict()
    assert serialized["agent"] == "GmailAgent"
    assert serialized["activity_type"] == "tool_started"
    assert serialized["status"] == "running"
