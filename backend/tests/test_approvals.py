"""Comprehensive tests for Phase 2B Human-in-the-Loop approval system.

Verifies approval lifecycle, security boundaries, orchestrator integration,
resumption execution, and API endpoints without requiring live Ollama.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import pytest
from fastapi.testclient import TestClient

from app.agents.activity import ActivityType, ActivityStatus
from app.integrations.llm_provider import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    ToolCall,
    ModelAvailabilityStatus,
)
from app.main import app
from app.orchestrator.orchestrator import Orchestrator
from app.permissions.levels import PermissionLevel
from app.permissions.models import PermissionContext, ApprovalStatus
from app.services.approval_service import (
    ApprovalService,
    ApprovalNotFoundError,
    ApprovalAlreadyResolvedError,
    ApprovalExpiredError,
)
from app.tools.base import BaseTool, ToolResult
from app.tools.registry import ToolRegistry


class CountingTestTool(BaseTool):
    """Tool that tracks how many times it was executed."""

    def __init__(self, name: str, level: PermissionLevel) -> None:
        self.name = name
        self.description = f"Counting tool for {name}"
        self.permission_level = level
        self.execution_count = 0
        self.parameters_schema = {"type": "object", "properties": {}, "required": []}

    async def execute(self, **kwargs) -> ToolResult:
        self.execution_count += 1
        return ToolResult(
            success=True,
            output={"executed": True, "count": self.execution_count},
        )


class MockApprovalLLM(BaseLLMProvider):
    """Mock LLM responding with tool calls or conversational completions."""

    provider_name = "mock_approval_llm"

    def __init__(self, responses: Optional[List[LLMResponse]] = None) -> None:
        self.responses: List[LLMResponse] = responses or []
        self.call_count = 0

    async def is_available(self) -> bool:
        return True

    async def list_models(self) -> List[str]:
        return ["mock:latest"]

    async def check_model_status(self, model=None) -> ModelAvailabilityStatus:
        return ModelAvailabilityStatus.AVAILABLE

    async def generate(self, prompt, **kwargs):
        return LLMResponse(content="generated", model="mock", provider=self.provider_name)

    async def chat(self, messages, tools=None, **kwargs):
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return LLMResponse(content="Default response", model="mock", provider=self.provider_name)


# 1 & 2. Level 0 and Level 1 tools execute without approval
@pytest.mark.asyncio
async def test_level_0_and_1_execute_without_approval():
    registry = ToolRegistry()
    tool_l0 = CountingTestTool("tool_l0", PermissionLevel.LEVEL_0_READ_ONLY)
    tool_l1 = CountingTestTool("tool_l1", PermissionLevel.LEVEL_1_LOW_IMPACT)
    registry.register(tool_l0)
    registry.register(tool_l1)

    mock_llm = MockApprovalLLM([
        LLMResponse(content="", model="mock", provider="mock", tool_calls=[ToolCall(name="tool_l0")]),
        LLMResponse(content="Finished l0", model="mock", provider="mock"),
    ])
    orch = Orchestrator(tools=registry, llm_provider=mock_llm)
    _, _, _, _, status, approval = await orch.handle_message("Run l0")

    assert status == "completed"
    assert approval is None
    assert tool_l0.execution_count == 1

    mock_llm_l1 = MockApprovalLLM([
        LLMResponse(content="", model="mock", provider="mock", tool_calls=[ToolCall(name="tool_l1")]),
        LLMResponse(content="Finished l1", model="mock", provider="mock"),
    ])
    orch_l1 = Orchestrator(tools=registry, llm_provider=mock_llm_l1)
    _, _, _, _, status_l1, approval_l1 = await orch_l1.handle_message("Run l1")

    assert status_l1 == "completed"
    assert approval_l1 is None
    assert tool_l1.execution_count == 1


# 3 & 4. Level 2 and Level 3 tools create approval request and halt
@pytest.mark.asyncio
async def test_level_2_and_3_create_approval_request_and_halt():
    registry = ToolRegistry()
    tool_l2 = CountingTestTool("tool_l2", PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT)
    tool_l3 = CountingTestTool("tool_l3", PermissionLevel.LEVEL_3_DESTRUCTIVE)
    registry.register(tool_l2)
    registry.register(tool_l3)

    svc = ApprovalService()

    # Test Level 2
    mock_llm_l2 = MockApprovalLLM([
        LLMResponse(content="", model="mock", provider="mock", tool_calls=[ToolCall(name="tool_l2")]),
    ])
    orch_l2 = Orchestrator(tools=registry, llm_provider=mock_llm_l2, approval_svc=svc)
    _, response, activities, tools_executed, status, approval = await orch_l2.handle_message("Run l2")

    assert status == "waiting_approval"
    assert approval is not None
    assert approval["tool_name"] == "tool_l2"
    assert approval["permission_level"] == 2
    assert tool_l2.execution_count == 0  # Crucial: did not execute!
    assert len(tools_executed) == 0

    # Test Level 3
    mock_llm_l3 = MockApprovalLLM([
        LLMResponse(content="", model="mock", provider="mock", tool_calls=[ToolCall(name="tool_l3")]),
    ])
    orch_l3 = Orchestrator(tools=registry, llm_provider=mock_llm_l3, approval_svc=svc)
    _, _, _, _, status_l3, approval_l3 = await orch_l3.handle_message("Run l3")

    assert status_l3 == "waiting_approval"
    assert approval_l3 is not None
    assert approval_l3["tool_name"] == "tool_l3"
    assert approval_l3["permission_level"] == 3
    assert tool_l3.execution_count == 0


# 5. Pending approval cannot execute the tool before user decision
@pytest.mark.asyncio
async def test_pending_approval_does_not_execute_tool():
    svc = ApprovalService()
    req = svc.create_request(
        tool_name="sensitive_action",
        permission_level=PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT,
        arguments={"key": "val"},
        action_description="Sensitive action",
    )
    assert req.status == ApprovalStatus.PENDING
    assert svc.get_request(req.id).status == ApprovalStatus.PENDING


# 6 & 7. Approve changes status to APPROVED and executes exactly once
@pytest.mark.asyncio
async def test_approve_executes_tool_exactly_once():
    registry = ToolRegistry()
    tool = CountingTestTool("consequential_tool", PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT)
    registry.register(tool)

    svc = ApprovalService()
    mock_llm = MockApprovalLLM([
        LLMResponse(content="", model="mock", provider="mock", tool_calls=[ToolCall(name="consequential_tool")]),
        LLMResponse(content="Action completed after approval.", model="mock", provider="mock"),
    ])
    orch = Orchestrator(tools=registry, llm_provider=mock_llm, approval_svc=svc)

    # Step 1: User request halts at waiting_approval
    _, _, _, _, status, approval = await orch.handle_message("Trigger action")
    assert status == "waiting_approval"
    assert tool.execution_count == 0

    # Step 2: User approves
    approval_id = approval["id"]
    conv_id, response, activities, tools_executed, final_status, resolved_req = await orch.resolve_and_resume(
        approval_id=approval_id,
        approved=True,
        reason="Looks safe to execute",
    )

    assert final_status == "completed"
    assert resolved_req.status == ApprovalStatus.APPROVED
    assert tool.execution_count == 1  # Executed exactly once!
    assert "Action completed after approval." in response

    # Step 3: Attempting to approve again raises ApprovalAlreadyResolvedError
    with pytest.raises(ApprovalAlreadyResolvedError):
        svc.approve_request(approval_id)

    # Tool count must remain strictly 1
    assert tool.execution_count == 1


# 8 & 9. Reject changes status to REJECTED and tool never executes
@pytest.mark.asyncio
async def test_reject_never_executes_tool():
    registry = ToolRegistry()
    tool = CountingTestTool("destructive_tool", PermissionLevel.LEVEL_3_DESTRUCTIVE)
    registry.register(tool)

    svc = ApprovalService()
    mock_llm = MockApprovalLLM([
        LLMResponse(content="", model="mock", provider="mock", tool_calls=[ToolCall(name="destructive_tool")]),
    ])
    orch = Orchestrator(tools=registry, llm_provider=mock_llm, approval_svc=svc)

    _, _, _, _, status, approval = await orch.handle_message("Delete files")
    assert status == "waiting_approval"

    approval_id = approval["id"]
    conv_id, response, activities, tools_executed, final_status, resolved_req = await orch.resolve_and_resume(
        approval_id=approval_id,
        approved=False,
        reason="Too risky",
    )

    assert final_status == "rejected"
    assert resolved_req.status == ApprovalStatus.REJECTED
    assert tool.execution_count == 0  # Must never execute!
    assert len(tools_executed) == 0
    assert "rejected the authorization request" in response

    # Attempting to reject again raises ApprovalAlreadyResolvedError
    with pytest.raises(ApprovalAlreadyResolvedError):
        svc.reject_request(approval_id)

    assert tool.execution_count == 0


# 10 & 11. Already resolved approval cannot be approved or rejected again
def test_already_resolved_approval_transitions():
    svc = ApprovalService()
    req = svc.create_request(
        tool_name="test_tool",
        permission_level=PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT,
        arguments={},
        action_description="Test action",
    )

    svc.approve_request(req.id)

    with pytest.raises(ApprovalAlreadyResolvedError):
        svc.approve_request(req.id)

    with pytest.raises(ApprovalAlreadyResolvedError):
        svc.reject_request(req.id)


# 12. Unknown approval ID returns proper error
def test_unknown_approval_id_error():
    svc = ApprovalService()
    with pytest.raises(ApprovalNotFoundError):
        svc.approve_request("non_existent_id")

    with pytest.raises(ApprovalNotFoundError):
        svc.reject_request("non_existent_id")


# 13. Expired approval cannot execute
def test_expired_approval_cannot_execute():
    svc = ApprovalService(expiry_seconds=1)
    req = svc.create_request(
        tool_name="test_tool",
        permission_level=PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT,
        arguments={},
        action_description="Expiring action",
        expires_in_seconds=-10,  # Expired in the past
    )

    # Calling get_request transitions status to EXPIRED
    fetched = svc.get_request(req.id)
    assert fetched.status == ApprovalStatus.EXPIRED

    with pytest.raises(ApprovalExpiredError):
        svc.approve_request(req.id)

    with pytest.raises(ApprovalExpiredError):
        svc.reject_request(req.id)


# 14. Approval cannot be used to execute a different tool
@pytest.mark.asyncio
async def test_approval_tool_tampering_protection():
    registry = ToolRegistry()
    safe_tool = CountingTestTool("safe_tool", PermissionLevel.LEVEL_0_READ_ONLY)
    registry.register(safe_tool)

    svc = ApprovalService()
    req = svc.create_request(
        tool_name="malicious_unregistered_tool",
        permission_level=PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT,
        arguments={},
        action_description="Tampered action",
    )

    orch = Orchestrator(tools=registry, approval_svc=svc)
    # The tool is not in registry, resolve_and_resume must fail safely
    conv_id, response, activities, tools_executed, status, resolved_req = await orch.resolve_and_resume(
        approval_id=req.id,
        approved=True,
    )

    assert status == "error"
    assert "is no longer registered" in response
    assert safe_tool.execution_count == 0


# 15. Approvals API endpoints verification
def test_approvals_api_endpoints(client: TestClient):
    # 1. Test GET /api/approvals list
    res = client.get("/api/approvals")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 2. Test GET /api/approvals/{id} with 404
    res_404 = client.get("/api/approvals/non_existent_id")
    assert res_404.status_code == 404

    # 3. Create a pending request directly via service
    from app.services.approval_service import approval_service
    req = approval_service.create_request(
        tool_name="get_system_info",
        permission_level=PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT,
        arguments={"detailed": False},
        action_description="Test API approval",
    )

    # Fetch through API
    res_get = client.get(f"/api/approvals/{req.id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == req.id
    assert res_get.json()["status"] == "pending"

    # Reject through API
    res_reject = client.post(f"/api/approvals/{req.id}/reject", json={"reason": "User said no"})
    assert res_reject.status_code == 200
    reject_data = res_reject.json()
    assert reject_data["status"] == "rejected"

    # Attempting to reject again returns 400
    res_reject_again = client.post(f"/api/approvals/{req.id}/reject", json={"reason": "Repeat"})
    assert res_reject_again.status_code == 400
