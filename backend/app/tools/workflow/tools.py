from typing import Dict, Any, List
from app.tools.base import BaseTool, ToolResult, PermissionLevel
from app.workflows.planner import WorkflowPlanner
from app.workflows.orchestrator import workflow_orchestrator
from app.orchestrator.orchestrator import orchestrator # The main one to provide LLM to planner

class PlanAndExecuteWorkflowTool(BaseTool):
    name: str = "plan_and_execute_workflow"
    description: str = "Plan and execute a multi-step cross-agent workflow to accomplish a complex goal. Use this for complex multi-step tasks requiring multiple tools or synthesis."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY

    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "The complex goal to achieve."
            }
        },
        "required": ["goal"]
    }

    async def execute(self, **kwargs) -> ToolResult:
        goal = kwargs.get("goal")
        if not goal:
            return ToolResult(success=False, error="Goal is required.")
        
        try:
            planner = WorkflowPlanner(llm_provider=orchestrator.llm)
            plan = await planner.plan_workflow(goal)
            
            wf = workflow_orchestrator.create_workflow(plan)
            
            # Start execution asynchronously or await it? 
            # If we await it, the tool takes a long time. But we want the final synthesis.
            # However, if it hits a HITL trap, execute_workflow returns early.
            # So we should execute it, and return its status!
            await workflow_orchestrator.execute_workflow(wf.id)
            
            # Re-fetch wf state
            from app.database.session import SessionLocal
            from app.models.entities import WorkflowModel
            with SessionLocal() as db:
                current_wf = db.query(WorkflowModel).filter(WorkflowModel.id == wf.id).first()
                if current_wf.status == "WAITING_APPROVAL":
                    return ToolResult(
                        success=True, 
                        output=f"Workflow '{current_wf.name}' is paused waiting for human approval. The user will be prompted."
                    )
                elif current_wf.status == "COMPLETED":
                    return ToolResult(
                        success=True,
                        output=f"Workflow completed. Synthesis:\n{current_wf.synthesis_result}"
                    )
                elif current_wf.status == "FAILED":
                    return ToolResult(
                        success=False,
                        error=f"Workflow failed: {current_wf.error}"
                    )
                else:
                    return ToolResult(
                        success=True,
                        output=f"Workflow '{current_wf.name}' is in status: {current_wf.status}"
                    )
        except Exception as e:
            return ToolResult(success=False, error=f"Workflow planning or execution failed: {str(e)}")
