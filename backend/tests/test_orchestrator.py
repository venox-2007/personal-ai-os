"""Tests for the Central Orchestrator."""

import pytest
from app.orchestrator.orchestrator import Orchestrator
from app.agents.activity import ActivityType
from app.integrations.llm_provider import BaseLLMProvider, LLMResponse, ModelAvailabilityStatus


class DummyTestLLM(BaseLLMProvider):
    provider_name = "dummy"

    async def is_available(self) -> bool:
        return True

    async def list_models(self) -> list:
        return ["dummy"]

    async def check_model_status(self, model=None) -> ModelAvailabilityStatus:
        return ModelAvailabilityStatus.AVAILABLE

    async def generate(self, prompt, **kwargs):
        return LLMResponse(content="dummy", model="dummy", provider="dummy")

    async def chat(self, messages, tools=None, **kwargs):
        return LLMResponse(content="Orchestrated response", model="dummy", provider="dummy")


@pytest.mark.asyncio
async def test_orchestrator_pipeline_flow():
    mock_llm = DummyTestLLM()
    orchestrator = Orchestrator(llm_provider=mock_llm)
    conv_id, response, activities, tool_calls, status, approval = await orchestrator.handle_message(
        message="What are my top tasks today?"
    )

    assert conv_id is not None
    assert response == "Orchestrated response"
    assert status == "completed"
    assert len(activities) >= 2

    types = [a.activity_type for a in activities]
    assert ActivityType.PLANNING in types
    assert ActivityType.COMPLETED in types
