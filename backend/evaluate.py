import asyncio
import json
import os
import sys
from typing import Dict, Any, List

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.orchestrator.orchestrator import orchestrator
from app.integrations.llm_provider import LLMResponse, ToolCall, ModelAvailabilityStatus
from app.models.entities import Base
from app.database.session import engine

def setup_db():
    Base.metadata.create_all(bind=engine)

class MockLLMProvider:
    def __init__(self, responses: List[LLMResponse]):
        self.responses = responses
        self.call_count = 0
        self.provider_name = "MockProvider"

    async def check_model_status(self, *args, **kwargs):
        return ModelAvailabilityStatus.AVAILABLE

    async def chat(self, *args, **kwargs) -> LLMResponse:
        if self.call_count < len(self.responses):
            res = self.responses[self.call_count]
            self.call_count += 1
            return res
        return LLMResponse(content="Mock default response", model="mock", provider="mock", usage={})

async def run_evaluation():
    print("Starting automated deterministic evaluation...")
    setup_db()
    passed = 0
    failed = 0

    # Test 1: Simple routing to tool
    print("\nTest 1: Tool Selection Routing")
    mock_responses = [
        LLMResponse(
            content="",
            model="mock",
            provider="mock",
            tool_calls=[
                ToolCall(id="tc1", name="get_system_info", arguments={})
            ],
            usage={}
        ),
        LLMResponse(
            content="System is operating normally.",
            model="mock",
            provider="mock",
            usage={}
        )
    ]
    orchestrator.llm = MockLLMProvider(mock_responses)
    conv_id, resp, activities, tools_called, status, _ = await orchestrator.handle_message("Check system info")
    print(f"DEBUG resp: {resp}")
    print(f"DEBUG tools_called: {tools_called}")
    
    if any(tc.get("name") == "get_system_info" for tc in tools_called):
        print("PASS: Correct tool selected")
        passed += 1
    else:
        print("FAIL: Tool not selected")
        failed += 1

    # Test 2: Workflow execution failure handling
    print("\nTest 2: Workflow Failure Isolation")
    from app.schemas.workflow import WorkflowPlan, WorkflowPlanStep
    from app.workflows.orchestrator import WorkflowOrchestrator
    
    wf_engine = WorkflowOrchestrator()
    plan = WorkflowPlan(
        goal="Test failure dependency",
        steps=[
            WorkflowPlanStep(
                step_id="step1",
                agent="Testing",
                action="Testing",
                tool_name="non_existent_tool",
                input_mapping={},
                depends_on=[],
                requires_approval=False,
                on_failure="FAIL"
            ),
            WorkflowPlanStep(
                step_id="step2",
                agent="Testing",
                action="Testing",
                tool_name="get_system_info",
                input_mapping={},
                depends_on=["step1"],
                requires_approval=False
            )
        ]
    )
    
    wf = wf_engine.create_workflow(plan)
    await wf_engine.execute_workflow(wf.id)
    
    from app.database.session import SessionLocal
    from app.models.entities import WorkflowModel, WorkflowStepModel
    with SessionLocal() as db:
        final_wf = db.query(WorkflowModel).filter(WorkflowModel.id == wf.id).first()
        s2 = db.query(WorkflowStepModel).filter(WorkflowStepModel.workflow_id == wf.id, WorkflowStepModel.step_id == "step2").first()
        
        if final_wf.status == "FAILED" and s2.status == "PENDING":
            print("PASS: Dependency failure correctly isolated step2")
            passed += 1
        else:
            print(f"FAIL: Workflow status {final_wf.status}, Step 2 status {s2.status}")
            failed += 1

    print("\n=== Evaluation Complete ===")
    print(f"Passed: {passed}, Failed: {failed}")
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_evaluation())
