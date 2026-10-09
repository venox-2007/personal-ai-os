import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.orchestrator.orchestrator import Orchestrator
from app.agents.activity import ActivityType
from app.integrations.llm_provider import BaseLLMProvider, LLMResponse, ModelAvailabilityStatus
from datetime import datetime

class DummyTestLLM(BaseLLMProvider):
    provider_name = "dummy"
    async def is_available(self) -> bool: return True
    async def list_models(self) -> list: return ["dummy"]
    async def check_model_status(self, model=None) -> ModelAvailabilityStatus:
        return ModelAvailabilityStatus.AVAILABLE
    async def generate(self, prompt, **kwargs): return LLMResponse(content="dummy", model="dummy", provider="dummy")
    async def chat(self, messages, tools=None, **kwargs):
        return LLMResponse(content="Fallback LLM response", model="dummy", provider="dummy")

class OfflineTestLLM(DummyTestLLM):
    async def check_model_status(self, model=None) -> ModelAvailabilityStatus:
        return ModelAvailabilityStatus.PROVIDER_UNAVAILABLE

@pytest.fixture
def mock_calendar_service():
    with patch("app.services.calendar_service.calendar_service.get_upcoming_events") as mock_get:
        yield mock_get


@pytest.fixture
def orchestrator_mocked_memory():
    def _create(llm=None):
        llm = llm or DummyTestLLM()
        orch = Orchestrator(llm_provider=llm)
        orch.memory = MagicMock()
        orch.memory.conversation.add_message = AsyncMock()
        orch.memory.conversation.get_messages = AsyncMock(return_value=[])
        return orch
    return _create

@pytest.mark.asyncio
async def test_fast_path_empty_calendar_offline_llm(mock_calendar_service, orchestrator_mocked_memory):
    """4. The fast path must work when Ollama is unavailable."""
    mock_calendar_service.return_value = []
    orch = orchestrator_mocked_memory(llm=OfflineTestLLM())

    conv_id, response, activities, tool_calls, status, approval = await orch.handle_message(
        message="what is in my calendar"
    )

    assert "You have no upcoming events scheduled" in response
    assert status == "completed"
    
    # 6. Conversation messages must be persisted exactly once for user, once for assistant
    assert orch.memory.conversation.add_message.call_count == 2
    user_call = orch.memory.conversation.add_message.call_args_list[0]
    assistant_call = orch.memory.conversation.add_message.call_args_list[1]
    assert user_call.args[1] == "user"
    assert assistant_call.args[1] == "assistant"

@pytest.mark.asyncio
async def test_fast_path_formatting_timezone_aware(mock_calendar_service, orchestrator_mocked_memory):
    """5. Timezone-aware event formatting and empty-calendar responses must be correct."""
    from datetime import timezone
    mock_event = MagicMock()
    mock_event.title = "Project Sync"
    # Create timezone-aware datetime
    mock_event.start_datetime = datetime(2026, 11, 5, 15, 30, tzinfo=timezone.utc)
    
    mock_calendar_service.return_value = [mock_event]
    orch = orchestrator_mocked_memory()

    conv_id, response, activities, tool_calls, status, approval = await orch.handle_message(
        message="show my schedule"
    )

    assert "Here are your upcoming calendar events:" in response
    assert "Project Sync (2026-11-05 15:30)" in response
    assert status == "completed"

@pytest.mark.asyncio
async def test_fast_path_service_failure_fallback(mock_calendar_service, orchestrator_mocked_memory):
    """3. Calendar service failures must not be misreported as an empty calendar."""
    # Simulate DB/Service crash
    mock_calendar_service.side_effect = Exception("Database timeout")
    
    orch = orchestrator_mocked_memory()
    conv_id, response, activities, tool_calls, status, approval = await orch.handle_message(
        message="what is in my calendar"
    )

    # Should fall back to standard LLM, not "empty calendar"
    assert response == "Fallback LLM response"
    assert "Database timeout" not in response # The user sees the LLM's response, error is logged

@pytest.mark.asyncio
async def test_mixed_read_action_fallback(mock_calendar_service, orchestrator_mocked_memory):
    """1. Mixed read/action requests must never take the direct read-only path."""
    orch = orchestrator_mocked_memory()
    conv_id, response, activities, tool_calls, status, approval = await orch.handle_message(
        message="what is in my calendar and also create a meeting for tomorrow"
    )

    # Fast path should be skipped because of "create" and "meeting"
    mock_calendar_service.assert_not_called()
    assert response == "Fallback LLM response"

@pytest.mark.asyncio
async def test_mutation_fallback(mock_calendar_service, orchestrator_mocked_memory):
    """2. Mutation requests must continue through normal routing and preserve HITL approvals."""
    orch = orchestrator_mocked_memory()
    conv_id, response, activities, tool_calls, status, approval = await orch.handle_message(
        message="delete my next meeting"
    )

    # Fast path skipped due to "delete"
    mock_calendar_service.assert_not_called()
    assert response == "Fallback LLM response"

@pytest.mark.asyncio
async def test_ambiguous_phrase_fallback(mock_calendar_service, orchestrator_mocked_memory):
    """7. Unsupported or ambiguous phrases must fall back safely."""
    orch = orchestrator_mocked_memory()
    conv_id, response, activities, tool_calls, status, approval = await orch.handle_message(
        message="is my calendar free on friday?" # Not in the exact phrase list
    )

    # Fast path skipped due to no exact match
    mock_calendar_service.assert_not_called()
    assert response == "Fallback LLM response"
