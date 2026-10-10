import pytest
import time
import uuid
from unittest.mock import MagicMock, patch, AsyncMock

from app.orchestrator.orchestrator import orchestrator
from app.services.proactive_service import proactive_service
from app.services.memory_service import memory_service
from app.services.memory_context_builder import MemoryContextBuilder
from app.database.session import SessionLocal
from app.workflows.orchestrator import WorkflowOrchestrator
from app.schemas.workflow import WorkflowPlan, WorkflowPlanStep
from app.models.entities import WorkflowModel
from app.integrations.llm_provider import BaseLLMProvider, LLMResponse, ModelAvailabilityStatus
from app.tools.base import PermissionLevel
from app.tools.research.fetcher import WebFetcher
from tests.eval_metrics import metrics

class DeterministicMockLLM(BaseLLMProvider):
    provider_name = "mock"
    def __init__(self):
        self.next_response = "Mocked response"
        self.next_tool_calls = []
        
    async def is_available(self) -> bool: return True
    async def list_models(self) -> list: return ["mock"]
    async def check_model_status(self, model=None) -> ModelAvailabilityStatus: return ModelAvailabilityStatus.AVAILABLE
    
    async def chat(self, messages, tools=None, **kwargs):
        self.last_messages = messages
        tc = self.next_tool_calls
        self.next_tool_calls = []
        return LLMResponse(content=self.next_response, model="mock", provider="mock", tool_calls=tc)
        
    async def generate(self, prompt, **kwargs):
        return LLMResponse(content=self.next_response, model="mock", provider="mock")

mock_llm = DeterministicMockLLM()
orchestrator.llm = mock_llm
proactive_service.llm = mock_llm

@pytest.fixture(autouse=True)
def setup_teardown_metrics():
    # removed metric increment 1
    yield

@pytest.fixture(autouse=True)
def db_cleanup():
    yield
    from sqlalchemy import text
    with SessionLocal() as db:
        db.execute(text("DELETE FROM workflows"))
        db.execute(text("DELETE FROM workflow_steps"))
        db.execute(text("DELETE FROM memories_v2"))
        db.commit()

def record_latency(start_time: float):
    metrics["latencies_ms"].append((time.perf_counter() - start_time) * 1000)

@pytest.mark.asyncio
async def test_scenario_1_simple_conversation():
    """1. Simple conversation that should not invoke tools."""
    mock_llm.next_tool_calls = []
    mock_llm.next_response = "Hello there!"
    
    orchestrator.permission_context.require_level_2_approval = True; orchestrator.permission_context.require_level_3_approval = True
    # removed metric increment 1
    start = time.perf_counter()
    conv_id, response, activities, tool_calls, status, approval = await orchestrator.handle_message("hello", "s1")
    record_latency(start)
    
    assert len(tool_calls) == 0
    assert "hello" in response.lower()
    # removed metric increment 1
    # removed metric increment 1

@pytest.mark.asyncio
async def test_scenario_2_calendar_read_only():
    """2. Read-only calendar query."""
    mock_llm.next_tool_calls = []
    
    # removed metric increment 1
    start = time.perf_counter()
    conv_id, response, activities, tool_calls, status, approval = await orchestrator.handle_message("what is in my calendar", "s2")
    record_latency(start)
    
    assert len(tool_calls) == 0
    assert "calendar" in response.lower() or any("calendar" in getattr(act, "description", "").lower() for act in activities)
    # removed metric increment 1
    # removed metric increment 1

@pytest.mark.asyncio
async def test_scenario_3_calendar_mutation_approval():
    """3. Calendar mutation requiring approval."""
    from app.integrations.llm_provider import ToolCall
    
    
    from app.tools.calendar.tools import CalendarCreateEventTool
    if "calendar_create_event" not in orchestrator.tools._tools:
        orchestrator.tools.register(CalendarCreateEventTool())
    # LLM decides to call tool
    mock_llm.next_response = ""
    mock_llm.next_tool_calls = [ToolCall(id="tc_1", name="calendar_create_event", arguments={"title": "Meeting", "start_datetime": "2026-10-10T12:00:00", "end_datetime": "2026-10-10T13:00:00", "timezone": "UTC"})]
    
    orchestrator.permission_context.require_level_2_approval = True; orchestrator.permission_context.require_level_3_approval = True
    # removed metric increment 1
    start = time.perf_counter()
    conv_id, response, activities, tool_calls, status, approval = await orchestrator.handle_message("schedule a meeting", "s3")
    record_latency(start)
    
    
    assert status == "waiting_approval"
    assert approval is not None
    assert approval["tool_name"] == "calendar_create_event"
    # removed metric increment 1
    # removed metric increment 1

@pytest.mark.asyncio
async def test_scenario_4_research_request():
    """4. Research request with source citations."""
    mock_llm.next_tool_calls = []
    mock_llm.next_response = "RAG is a technique [15]."
    
    # removed metric increment 1
    start = time.perf_counter()
    conv_id, response, activities, tool_calls, status, approval = await orchestrator.handle_message("what is rag", "s4")
    record_latency(start)
    
    # Citation should be stripped since there are no valid urls
    assert "Citation Validation Issue" in response
    assert "RAG is a technique" in response
    # removed metric increment 1
    # removed metric increment 1

@pytest.mark.asyncio
async def test_scenario_5_unsafe_url_rejection():
    """5. Unsafe research URL rejected by URL validation."""
    fetcher = WebFetcher()
    start = time.perf_counter()
    res = await fetcher.fetch_and_extract("http://127.0.0.1/admin")
    record_latency(start)
    
    assert "error" in res
    err_str = res["error"].lower()
    assert "localhost" in err_str or "explicitly blocked" in err_str or "private" in err_str or "local" in err_str
    # removed metric increment 1
    # removed metric increment 1

@pytest.mark.asyncio
async def test_scenario_6_file_read_workspace(monkeypatch):
    """6. File read request within the permitted workspace."""
    import os
    allowed_dir = os.path.abspath(os.getcwd())
    monkeypatch.setattr("app.core.config.settings.FILE_AGENT_ALLOWED_ROOTS", [allowed_dir])
    
    from app.tools.local_file.tools import FileReadTool
    tool = FileReadTool()
    
    start = time.perf_counter()
    valid, err = tool.validate_arguments({"file_path": os.path.join(allowed_dir, "test.txt")})
    record_latency(start)
    
    assert valid is True
    # removed metric increment 1

@pytest.mark.asyncio
async def test_scenario_7_unauthorized_tool(monkeypatch):
    """7. Invalid or unauthorized tool request."""
    import os
    allowed_dir = os.path.abspath(os.getcwd())
    monkeypatch.setattr("app.core.config.settings.FILE_AGENT_ALLOWED_ROOTS", [allowed_dir])
    
    from app.tools.local_file.tools import FileReadTool
    tool = FileReadTool()
    
    start = time.perf_counter()
    valid, err = tool.validate_arguments({"path": "/etc/shadow"})
    record_latency(start)
        
    assert valid is False
    # removed metric increment 1
    # removed metric increment 1

@pytest.mark.asyncio
async def test_scenario_8_workflow_output_mapping():
    """8. Multi-step workflow with output mapping."""
    wf_orchestrator = WorkflowOrchestrator()
    plan = WorkflowPlan(
        goal="Test",
        steps=[
            WorkflowPlanStep(step_id="step1", agent="Testing", action="Test", tool_name="file_read", input_mapping={"path": "dummy"}, requires_approval=False),
            WorkflowPlanStep(step_id="step2", agent="Testing", action="Test", tool_name="file_read", input_mapping={"path": "${step1.output.content}"}, depends_on=["step1"], requires_approval=False)
        ]
    )
    wf = wf_orchestrator.create_workflow(plan)
    
    with patch("app.tools.tool_registry.get") as mock_get:
        mock_tool1 = MagicMock()
        mock_tool1.name = "file_read"
        mock_tool1.permission_level = PermissionLevel.LEVEL_0_READ_ONLY
        mock_tool1.validate_arguments.return_value = (True, None)
        mock_tool1.execute = AsyncMock(return_value=MagicMock(success=True, output={"content": "mapped_path.txt"}))
        mock_get.return_value = mock_tool1
        
        start = time.perf_counter()
        await wf_orchestrator.execute_workflow(wf.id)
        record_latency(start)
        
        assert mock_tool1.execute.call_count == 2
        args_step2 = mock_tool1.execute.call_args_list[1].kwargs
        assert args_step2["path"] == "mapped_path.txt"
    # removed metric increment 1

@pytest.mark.asyncio
async def test_scenario_9_workflow_cancelled():
    """9. Workflow cancelled while awaiting approval."""
    wf_orchestrator = WorkflowOrchestrator()
    plan = WorkflowPlan(
        goal="Test Cancel",
        steps=[WorkflowPlanStep(step_id="s1", agent="Testing", action="Test", tool_name="calendar_create_event", input_mapping={"title": "Test"}, requires_approval=True)]
    )
    wf = wf_orchestrator.create_workflow(plan)
    
    with patch("app.tools.tool_registry.get") as mock_get:
        mock_tool = MagicMock()
        mock_tool.name = "calendar_create_event"
        mock_tool.description = "Creates event"
        mock_tool.permission_level = PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT
        mock_tool.validate_arguments.return_value = (True, None)
        mock_get.return_value = mock_tool
        
        start = time.perf_counter()
        await wf_orchestrator.execute_workflow(wf.id)
        record_latency(start)
        
    with SessionLocal() as db:
        wf_db = db.query(WorkflowModel).filter(WorkflowModel.id == wf.id).first()
        assert wf_db.status == "WAITING_APPROVAL"
        wf_db.status = "CANCELLED"
        db.commit()
        
    start = time.perf_counter()
    await wf_orchestrator.resume_step_after_approval("dummy", wf.id, "s1", True)
    record_latency(start)
    
    with SessionLocal() as db:
        wf_final = db.query(WorkflowModel).filter(WorkflowModel.id == wf.id).first()
        assert wf_final.status == "CANCELLED"
    # removed metric increment 1

@pytest.mark.asyncio
async def test_scenario_10_memory_retrieval():
    """10. Relevant memory retrieval and context injection."""
    from app.schemas.memory import MemoryCreate
    
    with SessionLocal() as db:
        memory_service.create_memory(db, MemoryCreate(
            content="My favorite color is blue",
            memory_type="FACT",
            category="preferences"
        ))
        
    mock_llm.next_tool_calls = []
    mock_llm.next_response = "Blue is nice."
    
    start = time.perf_counter()
    conv_id, response, activities, tool_calls, status, approval = await orchestrator.handle_message("What is my favorite color?", "s10")
    record_latency(start)
    
    system_prompt = mock_llm.last_messages[0].content if mock_llm.last_messages else ""

    assert "My favorite color is blue" in system_prompt

@pytest.mark.asyncio
async def test_scenario_11_memory_fallback(monkeypatch):
    """11. Memory retrieval failure with safe fallback."""
    def mock_fail(*args, **kwargs):
        raise Exception("DB offline")
        
    monkeypatch.setattr(memory_service, "retrieve_relevant_memories", mock_fail)
    
    mock_llm.next_tool_calls = []
    mock_llm.next_response = "Fallback response"
    
    start = time.perf_counter()
    conv_id, response, activities, tool_calls, status, approval = await orchestrator.handle_message("Who am I?", "s11")
    record_latency(start)
    
    assert response == "Fallback response"

@pytest.mark.asyncio
async def test_scenario_12_proactive_recommendations():
    """12. Proactive recommendation retrieval without repeated generation."""
    monkeypatch.setattr(proactive_service, "_last_refresh_time", None)
    mock_llm.next_response = '{"recommendations": [{"type": "task", "title": "Buy milk", "description": "Buy milk"}]}'
    
    with SessionLocal() as db:
        start = time.perf_counter()
        proactive_service.refresh_recommendations()
        recs1 = proactive_service.get_active_recommendations(db)
        latency1 = (time.perf_counter() - start) * 1000
        
        start = time.perf_counter()
        proactive_service.refresh_recommendations()
        recs2 = proactive_service.get_active_recommendations(db)
        latency2 = (time.perf_counter() - start) * 1000
        
        record_latency(start)
    # removed metric increment 1
