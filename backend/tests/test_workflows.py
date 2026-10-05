import pytest
import json
from app.workflows.planner import WorkflowPlanner, WorkflowPlannerError
from app.workflows.orchestrator import WorkflowOrchestrator
from app.schemas.workflow import WorkflowPlan, WorkflowPlanStep
from app.integrations.llm_provider import BaseLLMProvider, LLMResponse
from app.database.session import SessionLocal, init_db
from app.models.entities import WorkflowModel, WorkflowStepModel
from unittest.mock import AsyncMock, MagicMock

class MockLLMProvider(BaseLLMProvider):
    def __init__(self, json_to_return):
        super().__init__()
        self.json_to_return = json_to_return
        
    async def chat(self, messages, **kwargs):
        return LLMResponse(content=json.dumps(self.json_to_return), tool_calls=[], model="mock", provider="mock")
        
    async def generate(self, prompt, **kwargs):
        pass
        
    async def list_models(self):
        return []
        
    async def is_available(self):
        return True
        
    async def check_model_status(self):
        return True

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    with SessionLocal() as db:
        db.query(WorkflowStepModel).delete()
        db.query(WorkflowModel).delete()
        db.commit()

@pytest.mark.asyncio
async def test_planner_valid_plan():
    from app.agents.calendar_agent import CalendarAgentRegistration
    from app.agents.registry import agent_registry
    if not agent_registry.get("calendar_agent"):
        agent_registry.register(CalendarAgentRegistration())
    from app.tools import tool_registry
    from app.tools.calendar.tools import CalendarListEventsTool
    if not tool_registry.get("calendar_list_events"):
        tool_registry.register(CalendarListEventsTool())

    llm = MockLLMProvider({
        "goal": "Test goal",
        "steps": [
            {
                "step_id": "step_1",
                "agent": "calendar_agent",
                "action": "list events",
                "tool_name": "calendar_list_events",
                "input_mapping": {"time_min": "tomorrow"},
                "depends_on": []
            }
        ]
    })
    planner = WorkflowPlanner(llm)
    plan = await planner.plan_workflow("Test goal")
    assert plan.goal == "Test goal"
    assert len(plan.steps) == 1
    assert plan.steps[0].tool_name == "calendar_list_events"

@pytest.mark.asyncio
async def test_planner_invalid_agent():
    llm = MockLLMProvider({
        "goal": "Test goal",
        "steps": [{"step_id": "step_1", "agent": "unknown_agent", "tool_name": "unknown_tool"}]
    })
    planner = WorkflowPlanner(llm)
    with pytest.raises(WorkflowPlannerError, match="Invalid agent"):
        await planner.plan_workflow("Test goal")

@pytest.mark.asyncio
async def test_planner_invalid_dependency():
    llm = MockLLMProvider({
        "goal": "Test goal",
        "steps": [
            {"step_id": "step_1", "agent": "calendar_agent", "tool_name": "calendar_list_events", "depends_on": ["step_2"]}
        ]
    })
    planner = WorkflowPlanner(llm)
    with pytest.raises(WorkflowPlannerError, match="Invalid dependency"):
        await planner.plan_workflow("Test goal")

@pytest.mark.asyncio
async def test_orchestrator_execution():
    from app.workflows.orchestrator import WorkflowOrchestrator
    from app.tools import tool_registry
    from app.tools.calendar.tools import CalendarListEventsTool
    
    if not tool_registry.get("calendar_list_events"):
        tool_registry.register(CalendarListEventsTool())

    orchestrator = WorkflowOrchestrator()
    orchestrator._synthesize_result = AsyncMock(return_value="Synthesis Done")
    
    plan = WorkflowPlan(
        goal="Test goal",
        steps=[
            WorkflowPlanStep(
                step_id="step_1",
                agent="calendar_agent",
                action="action",
                tool_name="calendar_list_events",
                input_mapping={"start_datetime": "2026-01-01T00:00:00Z", "end_datetime": "2026-01-02T00:00:00Z"},
                depends_on=[],
                requires_approval=False
            )
        ]
    )
    
    wf = orchestrator.create_workflow(plan)
    assert wf.status == "PENDING"
    
    await orchestrator.execute_workflow(wf.id)
    
    with SessionLocal() as db:
        wf_final = db.query(WorkflowModel).filter(WorkflowModel.id == wf.id).first()
        assert wf_final.status == "COMPLETED"
        assert wf_final.synthesis_result == "Synthesis Done"
        assert len(wf_final.steps) == 1
        assert wf_final.steps[0].status == "COMPLETED"

@pytest.mark.asyncio
async def test_orchestrator_approval_pause():
    from app.workflows.orchestrator import WorkflowOrchestrator
    from app.tools import tool_registry
    from app.tools.calendar.tools import CalendarCreateEventTool
    
    if not tool_registry.get("calendar_create_event"):
        tool_registry.register(CalendarCreateEventTool())

    orchestrator = WorkflowOrchestrator()
    orchestrator._synthesize_result = AsyncMock(return_value="Synthesis Done")
    
    plan = WorkflowPlan(
        goal="Create event",
        steps=[
            WorkflowPlanStep(
                step_id="step_1",
                agent="calendar_agent",
                action="action",
                tool_name="calendar_create_event", # Requires Level 2
                input_mapping={"title": "Test", "start_datetime": "2026-01-01T10:00:00Z", "end_datetime": "2026-01-01T11:00:00Z", "timezone": "UTC"},
                depends_on=[]
            )
        ]
    )
    
    wf = orchestrator.create_workflow(plan)
    await orchestrator.execute_workflow(wf.id)
    
    with SessionLocal() as db:
        wf_paused = db.query(WorkflowModel).filter(WorkflowModel.id == wf.id).first()
        assert wf_paused.status == "WAITING_APPROVAL"
        assert wf_paused.steps[0].status == "WAITING_APPROVAL"
        assert wf_paused.steps[0].approval_id is not None
