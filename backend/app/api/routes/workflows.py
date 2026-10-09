from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database.session import SessionLocal
from app.models.entities import WorkflowModel, WorkflowStepModel
from app.schemas.workflow import WorkflowResponse, WorkflowStepResponse, WorkflowPlan
from app.workflows.orchestrator import workflow_orchestrator
from app.workflows.planner import WorkflowPlanner
from app.orchestrator.orchestrator import orchestrator
from app.services.approval_service import approval_service

router = APIRouter(prefix="/workflows", tags=["Workflows"])

class WorkflowCreateRequest(BaseModel):
    goal: str

@router.post("", response_model=WorkflowResponse)
async def create_workflow_api(request: WorkflowCreateRequest):
    try:
        planner = WorkflowPlanner(llm_provider=orchestrator.llm)
        plan = await planner.plan_workflow(request.goal)
        wf = workflow_orchestrator.create_workflow(plan)
        # Execute asynchronously in background if needed, but for now we'll just return it and let the frontend poll
        # Actually, let's start it in background. FastAPI BackgroundTasks could be used, or just asyncio.create_task
        import asyncio
        asyncio.create_task(workflow_orchestrator.execute_workflow(wf.id))
        return _serialize_wf(wf)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[WorkflowResponse])
def list_workflows():
    with SessionLocal() as db:
        wfs = db.query(WorkflowModel).order_by(WorkflowModel.created_at.desc()).limit(50).all()
        return [_serialize_wf(w) for w in wfs]

@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: str):
    with SessionLocal() as db:
        wf = db.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        if not wf:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return _serialize_wf(wf)

@router.post("/{workflow_id}/cancel")
def cancel_workflow(workflow_id: str):
    with SessionLocal() as db:
        wf = db.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        if not wf:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if wf.status in ["PENDING", "RUNNING", "WAITING_APPROVAL"]:
            wf.status = "CANCELLED"
            
            # Ensure no unintended mutations run if approved later
            for step in wf.steps:
                print(f"STEP: {step.step_id} - {step.status} - {step.approval_id}")
                if step.status == "WAITING_APPROVAL" and step.approval_id:
                    print(f"Cancelling approval {step.approval_id}")
                    try:
                        approval_service.reject_request(step.approval_id, reason="Workflow cancelled")
                        print("Successfully rejected")
                    except Exception as e:
                        print(f"FAILED to reject: {e}")
                    step.status = "CANCELLED"
            
            db.commit()
            return {"message": "Cancelled"}
        else:
            raise HTTPException(status_code=400, detail="Cannot cancel in current state")

def _serialize_wf(wf: WorkflowModel) -> dict:
    return {
        "id": wf.id,
        "name": wf.name,
        "description": wf.description,
        "goal": wf.goal,
        "status": wf.status,
        "created_at": wf.created_at,
        "updated_at": wf.updated_at,
        "completed_at": wf.completed_at,
        "error": wf.error,
        "synthesis_result": wf.synthesis_result,
        "steps": [
            {
                "id": s.id,
                "step_id": s.step_id,
                "sequence": s.sequence,
                "agent_name": s.agent_name,
                "tool_name": s.tool_name,
                "input_mapping_json": s.input_mapping_json,
                "depends_on_json": s.depends_on_json,
                "status": s.status,
                "error": s.error,
                "started_at": s.started_at,
                "completed_at": s.completed_at,
                "requires_approval": s.requires_approval,
                "on_failure": s.on_failure,
                "output_json": s.output_json,
                "approval_id": s.approval_id,
            }
            for s in wf.steps
        ]
    }
