import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.database.session import SessionLocal
from app.models.entities import WorkflowModel, WorkflowStepModel
from app.schemas.workflow import WorkflowPlan
from app.tools import tool_registry
from app.services.approval_service import approval_service
from app.permissions.models import PermissionLevel
from app.integrations.llm_provider import LLMMessage
from app.orchestrator.orchestrator import orchestrator  # to use its llm for synthesis
from app.core.observability import log_execution_event

class WorkflowOrchestratorError(Exception):
    pass

class WorkflowOrchestrator:
    
    def create_workflow(self, plan: WorkflowPlan) -> WorkflowModel:
        with SessionLocal() as db:
            wf = WorkflowModel(
                name=plan.goal[:200],
                goal=plan.goal,
                status="PENDING"
            )
            db.add(wf)
            db.commit()
            
            for idx, s in enumerate(plan.steps):
                step = WorkflowStepModel(
                    workflow_id=wf.id,
                    step_id=s.step_id,
                    sequence=idx,
                    agent_name=s.agent,
                    tool_name=s.tool_name,
                    input_mapping_json=json.dumps(s.input_mapping),
                    depends_on_json=json.dumps(s.depends_on),
                    requires_approval=s.requires_approval,
                    on_failure=s.on_failure,
                    status="PENDING"
                )
                db.add(step)
            db.commit()
            db.refresh(wf)
            return wf

    async def execute_workflow(self, workflow_id: str):
        with SessionLocal() as db:
            wf = db.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
            if not wf:
                raise WorkflowOrchestratorError("Workflow not found")
            
            if wf.status not in ["PENDING", "RUNNING"]:
                return
                
            wf.status = "RUNNING"
            db.commit()

            steps = sorted(wf.steps, key=lambda x: x.sequence)
            context_outputs = {}
            
            for step in steps:
                if step.status == "COMPLETED":
                    context_outputs[step.step_id] = json.loads(step.output_json) if step.output_json else {}
                    continue
                elif step.status in ["FAILED", "CANCELLED"]:
                    continue # skip to end or evaluate failure logic

                # Check dependencies
                deps = json.loads(step.depends_on_json)
                skip_step = False
                for d in deps:
                    # if a dep failed, we might fail or skip
                    dep_step = next((x for x in steps if x.step_id == d), None)
                    if not dep_step or dep_step.status != "COMPLETED":
                        step.status = "FAILED"
                        step.error = f"Dependency {d} not completed"
                        db.commit()
                        if step.on_failure == "FAIL":
                            wf.status = "FAILED"
                            wf.error = f"Step {step.step_id} failed dependencies"
                            db.commit()
                            return
                        skip_step = True
                        break
                
                if skip_step:
                    continue

                step.status = "RUNNING"
                step.started_at = datetime.utcnow()
                db.commit()

                # Resolve inputs
                raw_inputs = json.loads(step.input_mapping_json)
                try:
                    resolved_inputs = self._resolve_inputs(raw_inputs, context_outputs)
                except Exception as e:
                    step.status = "FAILED"
                    step.error = f"Input resolution error: {e}"
                    db.commit()
                    if step.on_failure == "FAIL":
                        wf.status = "FAILED"
                        wf.error = step.error
                        db.commit()
                        return
                    continue

                # Get tool
                tool = tool_registry.get(step.tool_name)
                if not tool:
                    step.status = "FAILED"
                    step.error = f"Tool {step.tool_name} not found"
                    db.commit()
                    if step.on_failure == "FAIL":
                        wf.status = "FAILED"
                        db.commit()
                        return
                    continue
                    
                # Validate inputs
                is_valid, val_err = tool.validate_arguments(resolved_inputs)
                if not is_valid:
                    step.status = "FAILED"
                    step.error = f"Invalid inputs for {tool.name}: {val_err}"
                    db.commit()
                    if step.on_failure == "FAIL":
                        wf.status = "FAILED"
                        wf.error = step.error
                        db.commit()
                        return
                    continue
                    
                # Hit HITL trap if required
                if tool.permission_level >= PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT:
                    if not step.approval_id:
                        req = approval_service.create_request(
                            conversation_id=None,
                            tool_name=tool.name,
                            tool_description=tool.description,
                            permission_level=tool.permission_level,
                            action_description=f"Workflow step {step.step_id} action.",
                            arguments=resolved_inputs,
                            execution_context={"workflow_id": wf.id, "step_id": step.id}
                        )
                        step.approval_id = req.id
                        step.status = "WAITING_APPROVAL"
                        wf.status = "WAITING_APPROVAL"
                        db.commit()
                        return # Pause execution

                # Execute Tool
                try:
                    res = await tool.execute(**resolved_inputs)
                    
                    if res.success:
                        step.status = "COMPLETED"
                        step.output_json = json.dumps(res.output)
                        context_outputs[step.step_id] = res.output
                    else:
                        step.status = "FAILED"
                        step.error = res.error
                except Exception as e:
                    step.status = "FAILED"
                    step.error = str(e)
                    
                step.completed_at = datetime.utcnow()
                db.commit()
                
                duration_ms = (step.completed_at - step.started_at).total_seconds() * 1000
                log_execution_event(
                    event_type="workflow_step",
                    status="SUCCESS" if step.status == "COMPLETED" else "FAILED",
                    correlation_id=wf.id,
                    agent_name=step.agent_name,
                    tool_name=step.tool_name,
                    workflow_id=wf.id,
                    step_id=step.step_id,
                    duration_ms=duration_ms,
                    error_category="ToolExecutionError" if step.status == "FAILED" else None
                )
                
                if step.status == "FAILED" and step.on_failure == "FAIL":
                    wf.status = "FAILED"
                    wf.error = step.error
                    db.commit()
                    return

            # All steps finished successfully (or skipped gracefully)
            wf.status = "COMPLETED"
            wf.completed_at = datetime.utcnow()
            db.commit()
            
            # Synthesize
            try:
                synthesis = await self._synthesize_result(wf, steps)
                wf.synthesis_result = synthesis
                db.commit()
            except Exception:
                pass # Just ignore synthesis failure

    async def resume_step_after_approval(self, workflow_id: str, step_id: str, approved: bool, tool_result: Any = None, reason: str = None):
        with SessionLocal() as db:
            step = db.query(WorkflowStepModel).filter(WorkflowStepModel.id == step_id).first()
            if not step:
                return
            wf = db.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
            
            if wf and wf.status in ["CANCELLED", "FAILED"]:
                return
            
            if not approved:
                step.status = "FAILED"
                step.error = f"Approval rejected: {reason}"
                step.completed_at = datetime.utcnow()
                if step.on_failure == "FAIL":
                    wf.status = "FAILED"
                    wf.error = step.error
                db.commit()
                return

            if tool_result:
                if tool_result.success:
                    step.status = "COMPLETED"
                    step.output_json = json.dumps(tool_result.output)
                else:
                    step.status = "FAILED"
                    step.error = tool_result.error
                    if step.on_failure == "FAIL":
                        wf.status = "FAILED"
                        wf.error = step.error
            
            step.completed_at = datetime.utcnow()
            wf.status = "RUNNING"
            db.commit()
            
        # Resume remaining workflow
        await self.execute_workflow(workflow_id)

    def _resolve_inputs(self, mapping: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Resolves ${step_id.output.key} templates in the mapping."""
        resolved = {}
        pattern = re.compile(r"^\$\{([a-zA-Z0-9_-]+)\.output(\.[a-zA-Z0-9_.-]+)?\}$")
        
        for k, v in mapping.items():
            if isinstance(v, str):
                match = pattern.match(v)
                if match:
                    step_id = match.group(1)
                    path = match.group(2)
                    
                    if step_id not in context:
                        raise ValueError(f"Reference to missing step output: {step_id}")
                    
                    val = context[step_id]
                    if path:
                        keys = path.strip(".").split(".")
                        for pk in keys:
                            if isinstance(val, dict) and pk in val:
                                val = val[pk]
                            else:
                                val = None
                                break
                    resolved[k] = val
                else:
                    # just a string
                    resolved[k] = v
            elif isinstance(v, dict):
                resolved[k] = self._resolve_inputs(v, context)
            elif isinstance(v, list):
                resolved[k] = [self._resolve_inputs(i, context) if isinstance(i, dict) else i for i in v]
            else:
                resolved[k] = v
        return resolved

    async def _synthesize_result(self, wf: WorkflowModel, steps: List[WorkflowStepModel]) -> str:
        summary_payload = []
        for s in steps:
            summary_payload.append({
                "step": s.step_id,
                "action": s.tool_name,
                "status": s.status,
                "output": json.loads(s.output_json) if s.output_json else None
            })
            
        prompt = f"""You are the Workflow Synthesizer.
The user goal was: {wf.goal}
Here is the execution summary of the cross-agent workflow:
{json.dumps(summary_payload, indent=2)}

Provide a clear, natural final answer to the user based on these results.
Do not expose internal tool details, JSON, or step IDs. Just answer their goal.
"""
        msg = [LLMMessage(role="user", content=prompt)]
        res = await orchestrator.llm.chat(msg)
        return res.content

workflow_orchestrator = WorkflowOrchestrator()
