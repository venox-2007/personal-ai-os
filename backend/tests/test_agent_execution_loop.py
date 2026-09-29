"""Unit tests for the real agent tool-calling loop (Phase 2A).

All tests use a deterministic MockLLMProvider so they never depend on a running Ollama daemon.
"""

import json
from typing import Any, Dict, List, Optional
import pytest

from app.agents.activity import ActivityType, ActivityStatus
from app.integrations.llm_provider import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    ToolCall,
    ModelAvailabilityStatus,
)
from app.memory.storage import UnifiedMemoryManager
from app.orchestrator.orchestrator import Orchestrator
from app.permissions.levels import PermissionLevel
from app.permissions.models import PermissionContext
from app.tools.base import BaseTool, ToolResult
from app.tools.registry import ToolRegistry
from app.tools.system_info import SystemInfoTool


class MockLLMProvider(BaseLLMProvider):
    """Deterministic mock LLM provider for unit testing the agent loop."""

    provider_name: str = "mock_ollama"

    def __init__(
        self,
        responses: Optional[List[LLMResponse]] = None,
        model_status: ModelAvailabilityStatus = ModelAvailabilityStatus.AVAILABLE,
    ) -> None:
        self.responses: List[LLMResponse] = responses or []
        self.call_count: int = 0
        self.recorded_calls: List[Dict[str, Any]] = []
        self.status = model_status

    async def is_available(self) -> bool:
        return self.status != ModelAvailabilityStatus.PROVIDER_UNAVAILABLE

    async def list_models(self) -> List[str]:
        return ["mock-model:latest"] if self.status == ModelAvailabilityStatus.AVAILABLE else []

    async def check_model_status(self, model: Optional[str] = None) -> ModelAvailabilityStatus:
        return self.status

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        return LLMResponse(content="mock generated text", model="mock", provider=self.provider_name)

    async def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        self.recorded_calls.append({
            "messages": [m.model_dump() for m in messages],
            "tools": tools,
        })
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return LLMResponse(
            content="Fallback mock completion",
            model="mock",
            provider=self.provider_name,
        )


class ParameterizedTestTool(BaseTool):
    """Test tool requiring explicit parameters."""

    name = "parameterized_tool"
    description = "Test tool with required arguments."
    permission_level = PermissionLevel.LEVEL_0_READ_ONLY
    parameters_schema = {
        "type": "object",
        "properties": {"target_id": {"type": "string"}},
        "required": ["target_id"],
    }

    async def execute(self, target_id: str = "", **kwargs) -> ToolResult:
        return ToolResult(success=True, output={"target_id": target_id, "processed": True})


class HighPermissionTestTool(BaseTool):
    """Test tool requiring human approval (Level 2)."""

    name = "send_external_payload"
    description = "Modifies external systems; requires explicit human confirmation."
    permission_level = PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT
    parameters_schema = {"type": "object", "properties": {}, "required": []}

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, output={"dispatched": True})


@pytest.fixture
def clean_registry():
    registry = ToolRegistry()
    registry.register(SystemInfoTool())
    registry.register(ParameterizedTestTool())
    registry.register(HighPermissionTestTool())
    return registry


# 1. Direct LLM response without tool use
@pytest.mark.asyncio
async def test_direct_llm_response_without_tool_use(clean_registry):
    mock_llm = MockLLMProvider(
        responses=[
            LLMResponse(
                content="I am Personal AI OS. I can manage your workspace.",
                model="mock",
                provider="mock_ollama",
                tool_calls=[],
            )
        ]
    )
    orch = Orchestrator(tools=clean_registry, llm_provider=mock_llm)
    conv_id, response, activities, tools_executed, status, approval = await orch.handle_message(
        message="What can you do?"
    )

    assert status == "completed"
    assert response == "I am Personal AI OS. I can manage your workspace."
    assert len(tools_executed) == 0
    activity_types = [a.activity_type for a in activities]
    assert ActivityType.PLANNING in activity_types
    assert ActivityType.COMPLETED in activity_types


# 2, 3, 4, 5. LLM selecting get_system_info -> Execution -> Result passed back -> Final answer
@pytest.mark.asyncio
async def test_llm_selecting_get_system_info_and_execution(clean_registry):
    mock_llm = MockLLMProvider(
        responses=[
            # Turn 1: LLM decides to call get_system_info
            LLMResponse(
                content="",
                model="mock",
                provider="mock_ollama",
                tool_calls=[
                    ToolCall(name="get_system_info", arguments={"detailed": True})
                ],
            ),
            # Turn 2: LLM receives tool output and writes final response
            LLMResponse(
                content="Personal AI OS v0.1.0 is healthy and operational.",
                model="mock",
                provider="mock_ollama",
                tool_calls=[],
            ),
        ]
    )
    orch = Orchestrator(tools=clean_registry, llm_provider=mock_llm)
    conv_id, response, activities, tools_executed, status, approval = await orch.handle_message(
        message="Check system status please"
    )

    assert status == "completed"
    assert response == "Personal AI OS v0.1.0 is healthy and operational."
    assert len(tools_executed) == 1
    assert tools_executed[0]["name"] == "get_system_info"
    assert tools_executed[0]["success"] is True

    # Check that tool result was passed back to the LLM in Turn 2
    assert mock_llm.call_count == 2
    turn_2_messages = mock_llm.recorded_calls[1]["messages"]
    tool_messages = [m for m in turn_2_messages if m["role"] == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["name"] == "get_system_info"
    tool_output_json = json.loads(tool_messages[0]["content"])
    assert tool_output_json["status"] == "healthy"
    assert tool_output_json["application"] == "Personal AI OS"

    # Verify observable activity sequence
    act_types = [a.activity_type for a in activities]
    assert ActivityType.PLANNING in act_types
    assert ActivityType.AGENT_SELECTED in act_types
    assert ActivityType.TOOL_STARTED in act_types
    assert ActivityType.TOOL_COMPLETED in act_types
    assert ActivityType.COMPLETED in act_types


# 6. Unknown tool call handling
@pytest.mark.asyncio
async def test_unknown_tool_call_handling(clean_registry):
    mock_llm = MockLLMProvider(
        responses=[
            LLMResponse(
                content="",
                model="mock",
                provider="mock_ollama",
                tool_calls=[ToolCall(name="unregistered_mystery_tool", arguments={})],
            ),
            LLMResponse(
                content="I realized the tool was unavailable, so I am answering directly.",
                model="mock",
                provider="mock_ollama",
                tool_calls=[],
            ),
        ]
    )
    orch = Orchestrator(tools=clean_registry, llm_provider=mock_llm)
    conv_id, response, activities, tools_executed, status, approval = await orch.handle_message(
        message="Run mystery tool"
    )

    assert status == "completed"
    act_types = [a.activity_type for a in activities]
    assert ActivityType.ERROR in act_types
    # Verify the LLM was informed of the unknown tool error in Turn 2
    turn_2_messages = mock_llm.recorded_calls[1]["messages"]
    tool_err = [m for m in turn_2_messages if m["role"] == "tool"]
    assert len(tool_err) == 1
    assert "not registered" in tool_err[0]["content"]


# 7. Invalid tool arguments validation
@pytest.mark.asyncio
async def test_invalid_tool_arguments_validation(clean_registry):
    mock_llm = MockLLMProvider(
        responses=[
            # Missing required parameter "target_id"
            LLMResponse(
                content="",
                model="mock",
                provider="mock_ollama",
                tool_calls=[ToolCall(name="parameterized_tool", arguments={})],
            ),
            LLMResponse(
                content="I encountered an argument error.",
                model="mock",
                provider="mock_ollama",
                tool_calls=[],
            ),
        ]
    )
    orch = Orchestrator(tools=clean_registry, llm_provider=mock_llm)
    conv_id, response, activities, tools_executed, status, approval = await orch.handle_message(
        message="Execute parameterized tool without arguments"
    )

    assert status == "completed"
    act_types = [a.activity_type for a in activities]
    assert ActivityType.ERROR in act_types
    turn_2_messages = mock_llm.recorded_calls[1]["messages"]
    tool_err = [m for m in turn_2_messages if m["role"] == "tool"]
    assert "Missing required parameter: 'target_id'" in tool_err[0]["content"]


# 8 & 9. Permission check & Approval-required behavior
@pytest.mark.asyncio
async def test_approval_required_behavior(clean_registry):
    mock_llm = MockLLMProvider(
        responses=[
            LLMResponse(
                content="",
                model="mock",
                provider="mock_ollama",
                tool_calls=[ToolCall(name="send_external_payload", arguments={})],
            )
        ]
    )
    orch = Orchestrator(tools=clean_registry, llm_provider=mock_llm)
    conv_id, response, activities, tools_executed, status, approval = await orch.handle_message(
        message="Trigger external payload action"
    )

    assert status == "waiting_approval"
    assert "Action Requires Confirmation" in response
    assert len(tools_executed) == 0  # Crucial: Must NOT have executed!

    act_types = [a.activity_type for a in activities]
    assert ActivityType.APPROVAL_REQUIRED in act_types


# 10. Maximum tool iterations limit
@pytest.mark.asyncio
async def test_maximum_tool_iterations_limit(clean_registry):
    # Loop that continuously requests get_system_info
    continuous_responses = [
        LLMResponse(
            content="",
            model="mock",
            provider="mock_ollama",
            tool_calls=[ToolCall(name="get_system_info", arguments={})],
        )
        for _ in range(10)
    ]
    mock_llm = MockLLMProvider(responses=continuous_responses)
    orch = Orchestrator(
        tools=clean_registry,
        llm_provider=mock_llm,
        max_tool_iterations=3,
    )
    conv_id, response, activities, tools_executed, status, approval = await orch.handle_message(
        message="Keep looping"
    )

    assert status == "error"
    assert "limit of 3 tool execution iterations" in response
    assert len(tools_executed) == 3
    act_types = [a.activity_type for a in activities]
    assert ActivityType.ERROR in act_types


# 11. Ollama unavailable handling
@pytest.mark.asyncio
async def test_ollama_unavailable_handling(clean_registry):
    mock_llm = MockLLMProvider(
        model_status=ModelAvailabilityStatus.PROVIDER_UNAVAILABLE
    )
    orch = Orchestrator(tools=clean_registry, llm_provider=mock_llm)
    conv_id, response, activities, tools_executed, status, approval = await orch.handle_message(
        message="Hello while offline"
    )

    assert status == "error"
    assert "Local LLM Engine Offline" in response
    assert len(tools_executed) == 0
    act_types = [a.activity_type for a in activities]
    act_statuses = [a.status for a in activities]
    assert ActivityStatus.WARNING in act_statuses
    assert ActivityType.ERROR in act_types


# 12. Tool registry integration and tool schema definition
def test_tool_registry_to_llm_definitions(clean_registry):
    tools = clean_registry.list_tools()
    definitions = [t.to_llm_tool_definition() for t in tools]

    assert len(definitions) == 3
    names = [d["function"]["name"] for d in definitions]
    assert "get_system_info" in names
    assert "parameterized_tool" in names
    assert "send_external_payload" in names

    # Verify function schema structure
    for d in definitions:
        assert d["type"] == "function"
        assert "name" in d["function"]
        assert "description" in d["function"]
        assert "parameters" in d["function"]
