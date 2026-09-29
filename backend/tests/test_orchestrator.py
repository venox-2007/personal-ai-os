"""Tests for the Central Orchestrator."""

import pytest
from app.orchestrator.orchestrator import Orchestrator
from app.agents.activity import ActivityType


@pytest.mark.asyncio
async def test_orchestrator_pipeline_flow():
    orchestrator = Orchestrator()
    conv_id, response, activities = await orchestrator.handle_message(
        message="What are my top tasks today?"
    )

    assert conv_id is not None
    assert len(response) > 0
    assert len(activities) >= 4

    types = [a.activity_type for a in activities]
    assert ActivityType.PLANNING in types
    assert ActivityType.REASONING in types
    assert ActivityType.AGENT_SELECTED in types
    assert ActivityType.COMPLETED in types
